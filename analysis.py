from __future__ import annotations

from io import BytesIO

import pandas as pd


def subject_score_frame(ratings: pd.DataFrame, field: str = "模拟机科目得分") -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if field not in ratings.columns:
        return pd.DataFrame(columns=["姓名", "科目名称", "得分"])
    for _, row in ratings.iterrows():
        scores = row.get(field) or {}
        if not isinstance(scores, dict):
            continue
        for subject, score in scores.items():
            if score is not None and not pd.isna(score):
                rows.append({"记录ID": row.get("记录ID", ""), "姓名": row.get("姓名", ""), "所属单位": row.get("所属单位", ""), "机型类别": row.get("机型类别", ""), "科目名称": subject, "得分": float(score)})
    return pd.DataFrame(rows)


def summary_metrics(ratings: pd.DataFrame, deductions: pd.DataFrame) -> dict[str, float | int]:
    score = pd.to_numeric(ratings.get("模拟机总分", pd.Series(dtype=float)), errors="coerce")
    loss = pd.to_numeric(ratings.get("失分", pd.Series(dtype=float)), errors="coerce")
    return {
        "评估人数": int(ratings["姓名"].nunique()) if not ratings.empty and "姓名" in ratings else 0,
        "评分记录": len(ratings),
        "平均模拟机得分": float(score.mean()) if score.notna().any() else 0.0,
        "最高分": float(score.max()) if score.notna().any() else 0.0,
        "最低分": float(score.min()) if score.notna().any() else 0.0,
        "平均失分": float(loss.mean()) if loss.notna().any() else 0.0,
        "待复核": int((ratings.get("数据质量", pd.Series(dtype=str)) == "待复核").sum()),
        "扣分事件": int((pd.to_numeric(deductions.get("失分", pd.Series(dtype=float)), errors="coerce") > 0).sum()) if not deductions.empty else 0,
    }


def unit_summary(ratings: pd.DataFrame) -> pd.DataFrame:
    if ratings.empty:
        return pd.DataFrame(columns=["所属单位", "评估人数", "平均分", "最高分", "最低分", "平均失分"])
    data = ratings.copy()
    result = data.groupby("所属单位", dropna=False).agg(
        评估人数=("姓名", "nunique"),
        平均分=("模拟机总分", "mean"),
        最高分=("模拟机总分", "max"),
        最低分=("模拟机总分", "min"),
        平均失分=("失分", "mean"),
    ).reset_index()
    return result.sort_values("平均分", ascending=False)


def subject_summary(ratings: pd.DataFrame) -> pd.DataFrame:
    scores = subject_score_frame(ratings)
    if scores.empty:
        return pd.DataFrame(columns=["科目名称", "评估人数", "平均分", "最高分", "最低分"])
    return scores.groupby("科目名称", as_index=False).agg(评估人数=("得分", "count"), 平均分=("得分", "mean"), 最高分=("得分", "max"), 最低分=("得分", "min")).sort_values("平均分")


def top_deductions(deductions: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    if deductions.empty:
        return pd.DataFrame(columns=["科目名称", "评分项目", "扣分标准", "扣分次数", "总失分"])
    data = deductions.copy()
    data = data[pd.to_numeric(data["失分"], errors="coerce").fillna(0) > 0]
    if data.empty:
        return pd.DataFrame(columns=["科目名称", "评分项目", "扣分标准", "扣分次数", "总失分"])
    result = data.groupby(["科目名称", "评分项目", "扣分标准"], dropna=False).agg(扣分次数=("记录ID", "nunique"), 总失分=("失分", "sum")).reset_index()
    return result.sort_values(["总失分", "扣分次数"], ascending=False).head(limit)


def subject_loss(deductions: pd.DataFrame) -> pd.DataFrame:
    if deductions.empty:
        return pd.DataFrame(columns=["科目名称", "扣分次数", "总失分"])
    data = deductions[pd.to_numeric(deductions["失分"], errors="coerce").fillna(0) > 0]
    return data.groupby("科目名称", as_index=False).agg(扣分次数=("记录ID", "nunique"), 总失分=("失分", "sum")).sort_values("总失分", ascending=False)


def score_distribution(ratings: pd.DataFrame) -> pd.DataFrame:
    if ratings.empty:
        return pd.DataFrame(columns=["分数区间", "人数"])
    scores = pd.to_numeric(ratings["模拟机总分"], errors="coerce").dropna()
    bins = [-float("inf"), 79.99, 89.99, 94.99, 100.01, float("inf")]
    labels = ["<80", "80-89", "90-94", "95-100", ">100"]
    return scores.groupby(pd.cut(scores, bins=bins, labels=labels, right=True), observed=False).size().rename("人数").reset_index().rename(columns={"模拟机总分": "分数区间"})


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
