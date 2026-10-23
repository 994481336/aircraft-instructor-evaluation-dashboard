from __future__ import annotations

"""Instructor dashboard statistics, independent of legacy analysis imports."""

from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import json
import re

import pandas as pd

from aircraft import canonical_model
from company import canonical_company


def with_person_identity(ratings: pd.DataFrame) -> pd.DataFrame:
    """Identify people within the selected scope, across aliases of one company.

    The export has evaluation IDs, not employee IDs. Company + normalized name
    is therefore the available identity; do not use the evaluation ID as a person.
    """
    data = ratings.copy()
    units = data.get("所属单位", pd.Series("未识别单位", index=data.index)).fillna("未识别单位")
    data["公司"] = units.map(canonical_company)
    names = data.get("姓名", pd.Series("", index=data.index)).fillna("").astype(str).str.strip()
    data["姓名"] = names
    data["人员标识"] = [
        json.dumps([company, re.sub(r"\s+", "", name) or f"未命名记录-{index}"], ensure_ascii=False)
        for index, (company, name) in enumerate(zip(data["公司"], names))
    ]
    return data


def person_score_frame(ratings: pd.DataFrame) -> pd.DataFrame:
    """One row per person; retain unrounded means and source record counts."""
    columns = ["人员标识", "公司", "姓名", "评分记录", "有效评分记录", "有效讲评记录", "模拟机总分", "训前总分", "失分"]
    if ratings.empty:
        return pd.DataFrame(columns=columns)
    data = with_person_identity(ratings)
    for column in ("模拟机总分", "训前总分", "失分"):
        data[column] = pd.to_numeric(data.get(column, pd.Series(index=data.index, dtype=float)), errors="coerce")
    return data.groupby("人员标识", sort=False, dropna=False).agg(
        公司=("公司", "first"), 姓名=("姓名", "first"),
        评分记录=("姓名", "size"), 有效评分记录=("模拟机总分", "count"),
        有效讲评记录=("训前总分", "count"),
        模拟机总分=("模拟机总分", "mean"), 训前总分=("训前总分", "mean"), 失分=("失分", "mean"),
    ).reset_index()[columns]


def score_text(value: float | int | None) -> str:
    """Display source scores to one decimal using ordinary half-up rounding."""
    if value is None or pd.isna(value):
        return "-"
    return str(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def subject_score_frame(ratings: pd.DataFrame, field: str = "模拟机科目得分") -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if field not in ratings.columns:
        return pd.DataFrame(columns=["姓名", "科目名称", "得分"])
    for _, row in with_person_identity(ratings).iterrows():
        scores = row.get(field) or {}
        if not isinstance(scores, dict):
            continue
        for subject, score in scores.items():
            if score is not None and not pd.isna(score):
                rows.append({"记录ID": row.get("记录ID", ""), "人员标识": row["人员标识"], "公司": row["公司"], "姓名": row.get("姓名", ""), "所属单位": row.get("所属单位", ""), "机型类别": row.get("机型类别", ""), "科目名称": subject, "得分": float(score)})
    return pd.DataFrame(rows)


def summary_metrics(ratings: pd.DataFrame, deductions: pd.DataFrame, score_field: str = "模拟机总分") -> dict[str, float | int | None]:
    people = person_score_frame(ratings)
    score = pd.to_numeric(people[score_field], errors="coerce")
    simulator_score = pd.to_numeric(people["模拟机总分"], errors="coerce")
    loss = pd.to_numeric(people["失分"], errors="coerce")
    return {
        "评估人数": len(people),
        "有效评分人数": int(score.notna().sum()),
        "评分记录": len(ratings),
        "平均分": float(score.mean()) if score.notna().any() else None,
        "平均模拟机得分": float(simulator_score.mean()) if simulator_score.notna().any() else None,
        "最高分": float(score.max()) if score.notna().any() else None,
        "最低分": float(score.min()) if score.notna().any() else None,
        "平均失分": float(loss.mean()) if score_field == "模拟机总分" and loss.notna().any() else None,
        "待复核": int((ratings.get("数据质量", pd.Series(dtype=str)) == "待复核").sum()),
        "扣分事件": int((pd.to_numeric(deductions.get("失分", pd.Series(dtype=float)), errors="coerce") > 0).sum()) if score_field == "模拟机总分" and not deductions.empty else 0,
    }


def unit_summary(ratings: pd.DataFrame, score_field: str = "模拟机总分") -> pd.DataFrame:
    if ratings.empty:
        return pd.DataFrame(columns=["所属单位", "评估人数", "有效评分人数", "评分记录", "平均分", "最高分", "最低分", "平均失分"])
    people = [person_score_frame(part).assign(所属单位=unit) for unit, part in ratings.groupby("所属单位", dropna=False)]
    return _group_person_scores(pd.concat(people, ignore_index=True), "所属单位", score_field)


def _group_person_scores(people: pd.DataFrame, group: str, score_field: str = "模拟机总分") -> pd.DataFrame:
    result = people.groupby(group, dropna=False).agg(
        评估人数=("人员标识", "size"),
        有效评分人数=(score_field, "count"),
        评分记录=("评分记录", "sum"),
        平均分=(score_field, "mean"),
        最高分=(score_field, "max"),
        最低分=(score_field, "min"),
        平均失分=("失分", "mean"),
    ).reset_index()
    if score_field != "模拟机总分":
        result["平均失分"] = float("nan")
    return result.sort_values("平均分", ascending=False)


def company_summary(ratings: pd.DataFrame, score_field: str = "模拟机总分") -> pd.DataFrame:
    people = person_score_frame(ratings)
    if people.empty:
        return pd.DataFrame(columns=["公司", "评估人数", "有效评分人数", "评分记录", "平均分", "最高分", "最低分", "平均失分"])
    return _group_person_scores(people, "公司", score_field)


def type_briefing_segments(ratings: pd.DataFrame, mode: str = "按机型类别") -> list[tuple[str, pd.DataFrame]]:
    """Partition the selected records by manufacturer category or model."""
    if ratings.empty:
        return []
    data = ratings.copy()
    family = data.get("机型类别", pd.Series(index=data.index, dtype=str)).astype(str)
    if mode == "按具体机型":
        if "统计机型" not in data:
            models = data.get("机型", pd.Series(index=data.index, dtype=str))
            data["统计机型"] = [canonical_model(model, category) for model, category in zip(models, family)]
        return [(f"{index}、{model}", part.copy()) for index, (model, part) in enumerate(data.groupby("统计机型", sort=True), start=1)]
    groups = [
        ("一、国产民机", data[family.eq("国产民机")].copy()),
        ("二、空客机型", data[family.eq("空客")].copy()),
        ("三、波音机型", data[family.eq("波音")].copy()),
    ]
    other = data[~family.isin(["国产民机", "空客", "波音"])].copy()
    if not other.empty:
        groups.append(("四、未识别类别", other))
    return [(label, part) for label, part in groups if not part.empty]


def type_briefing(ratings: pd.DataFrame) -> pd.DataFrame:
    """Build the supporting summary table for manufacturer categories."""
    columns = [
        "机型范围", "评估人数", "评分记录", "平均模拟机得分", "平均训前讲评",
        "平均失分", "最高模拟机得分", "最低模拟机得分", "主要机型",
    ]
    if ratings.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for label, part in type_briefing_segments(ratings):
        display_label = label.split("、", 1)[-1]
        people = person_score_frame(part)
        sim = pd.to_numeric(people["模拟机总分"], errors="coerce")
        briefing = pd.to_numeric(people["训前总分"], errors="coerce")
        loss = pd.to_numeric(people["失分"], errors="coerce")
        rows.append({
            "机型范围": display_label,
            "评估人数": len(people),
            "评分记录": len(part),
            "平均模拟机得分": float(sim.mean()) if sim.notna().any() else None,
            "平均训前讲评": float(briefing.mean()) if briefing.notna().any() else None,
            "平均失分": float(loss.mean()) if loss.notna().any() else None,
            "最高模拟机得分": float(sim.max()) if sim.notna().any() else None,
            "最低模拟机得分": float(sim.min()) if sim.notna().any() else None,
            "主要机型": ", ".join(part["机型"].dropna().astype(str).value_counts().index.tolist()),
        })
    return pd.DataFrame(rows, columns=columns)


def subject_summary(ratings: pd.DataFrame, field: str = "模拟机科目得分") -> pd.DataFrame:
    scores = subject_score_frame(ratings, field)
    if scores.empty:
        return pd.DataFrame(columns=["科目名称", "评估人数", "平均分", "最高分", "最低分"])
    people = scores.groupby(["人员标识", "科目名称"], as_index=False)["得分"].mean()
    return people.groupby("科目名称", as_index=False).agg(评估人数=("得分", "count"), 平均分=("得分", "mean"), 最高分=("得分", "max"), 最低分=("得分", "min")).sort_values("平均分")


def top_deductions(deductions: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Rank projects after summing every deduction standard in each project."""
    columns = ["评分项目", "扣分次数", "总失分"]
    if deductions.empty:
        return pd.DataFrame(columns=columns)
    data = deductions.copy()
    data["失分"] = pd.to_numeric(data["失分"], errors="coerce").fillna(0)
    data = data[data["失分"] > 0]
    if data.empty:
        return pd.DataFrame(columns=columns)
    result = data.groupby("评分项目", dropna=False).agg(扣分次数=("记录ID", "nunique"), 总失分=("失分", "sum")).reset_index()
    return result.sort_values(["总失分", "扣分次数", "评分项目"], ascending=[False, False, True]).head(limit)


def subject_loss(deductions: pd.DataFrame) -> pd.DataFrame:
    if deductions.empty:
        return pd.DataFrame(columns=["科目名称", "扣分次数", "总失分"])
    data = deductions[pd.to_numeric(deductions["失分"], errors="coerce").fillna(0) > 0]
    return data.groupby("科目名称", as_index=False).agg(扣分次数=("记录ID", "nunique"), 总失分=("失分", "sum")).sort_values("总失分", ascending=False)


def score_distribution(ratings: pd.DataFrame, score_field: str = "模拟机总分") -> pd.DataFrame:
    if ratings.empty:
        return pd.DataFrame(columns=["分数区间", "评估人数"])
    scores = pd.to_numeric(person_score_frame(ratings)[score_field], errors="coerce").dropna()
    labels = ["<80", "80-89", "90-94", "95-100", ">100"]
    counts = [
        (scores < 80).sum(), ((scores >= 80) & (scores < 90)).sum(),
        ((scores >= 90) & (scores < 95)).sum(), ((scores >= 95) & (scores <= 100)).sum(),
        (scores > 100).sum(),
    ]
    return pd.DataFrame({"分数区间": labels, "评估人数": counts})


def risk_summary(ratings: pd.DataFrame, deductions: pd.DataFrame) -> pd.DataFrame:
    if deductions.empty:
        return pd.DataFrame(columns=["风险等级", "记录数", "总失分"])
    data = deductions[pd.to_numeric(deductions["失分"], errors="coerce").fillna(0) > 0].copy()
    if data.empty:
        return pd.DataFrame(columns=["风险等级", "记录数", "总失分"])
    data["风险等级"] = data["失分"].map(lambda value: "高" if value >= 5 else ("中" if value >= 2 else "低"))
    return data.groupby("风险等级", as_index=False).agg(记录数=("记录ID", "nunique"), 总失分=("失分", "sum"))


def xlsx_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name[:31], index=False)
    return output.getvalue()
