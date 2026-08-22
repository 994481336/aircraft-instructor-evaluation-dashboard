from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re
from typing import Any

import pandas as pd


FAMILY_AIRBUS = "空客"
FAMILY_BOEING = "波音"
FAMILY_DOMESTIC = "国产民机"
FAMILY_UNKNOWN = "未识别"

FAMILY_RULES = {
    FAMILY_AIRBUS: "rules/airbus.yaml",
    FAMILY_BOEING: "rules/boeing.yaml",
    FAMILY_DOMESTIC: "rules/domestic.yaml",
}

SUBJECT_NAMES = ["科目一", "科目二", "科目三", "科目四", "科目五", "科目六"]

META_ALIASES: dict[str, tuple[str, ...]] = {
    "提交时间": ("提交时间",),
    "填写ID": ("填写ID", "ID", "编号"),
    "被评估人姓名": ("被评估人姓名", "姓名", "被评估人"),
    "评估日期": ("评估日期", "日期"),
    "所属单位": ("所属单位", "单位"),
    "机型": ("机型", "飞机型号"),
    "技术等级": ("技术等级", "职务"),
    "总飞行时间": ("总飞行时间",),
    "本机型经历时间": ("本机型经历时间", "本机型飞行时间", "本机型经历"),
    "评估员姓名": ("评估员姓名", "评估员", "检查员"),
    "模拟机总分": ("教员双盲模拟机评估总得分", "模拟机评估总得分", "模拟机总得分"),
    "训前总分": ("教员双盲训前讲评总得分", "训前讲评总得分", "训前总得分"),
}


@dataclass
class ParsedBundle:
    summaries: pd.DataFrame
    ratings: pd.DataFrame
    deductions: pd.DataFrame
    sheet_columns: pd.DataFrame


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def key_text(value: Any) -> str:
    return re.sub(r"[\s_/／:：()（）\[\]【】\-—_]+", "", clean_text(value)).lower()


def to_number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = clean_text(value).replace("−", "-").replace("－", "-")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalize_model(model: Any, file_name: str = "") -> tuple[str, str]:
    text = f"{clean_text(model)} {clean_text(file_name)}".upper()
    compact = re.sub(r"[\s_-]+", "", text)
    if re.search(r"(?:^|[^A-Z])A\d{3}", text) or any(token in compact for token in ("A320", "A330", "A350")):
        return clean_text(model) or "未识别机型", FAMILY_AIRBUS
    if any(token in compact for token in ("B737", "B747", "B757", "B767", "B777", "B787")):
        return clean_text(model) or "未识别机型", FAMILY_BOEING
    if any(token in compact for token in ("C909", "C919", "ARJ21", "国产民机")):
        return clean_text(model) or "未识别机型", FAMILY_DOMESTIC
    if "空客" in text:
        return clean_text(model) or "空客", FAMILY_AIRBUS
    if "波音" in text:
        return clean_text(model) or "波音", FAMILY_BOEING
    if "国产" in text:
        return clean_text(model) or "国产民机", FAMILY_DOMESTIC
    return clean_text(model) or "未识别机型", FAMILY_UNKNOWN


def find_header_row(raw: pd.DataFrame) -> int | None:
    best_row: int | None = None
    best_score = 0
    aliases = tuple(alias for values in META_ALIASES.values() for alias in values)
    for row_idx in range(min(len(raw), 20)):
        values = [key_text(value) for value in raw.iloc[row_idx].tolist()]
        joined = "|".join(values)
        score = sum(1 for alias in aliases if key_text(alias) in joined)
        score += 4 if "被评估人姓名" in joined else 0
        score += 3 if "机型" in joined else 0
        if score > best_score:
            best_row = row_idx
            best_score = score
    return best_row if best_score >= 5 else None


def dedupe_headers(values: list[Any]) -> list[str]:
    counts: dict[str, int] = {}
    result: list[str] = []
    for idx, value in enumerate(values, start=1):
        base = clean_text(value) or f"未命名列_{idx}"
        counts[base] = counts.get(base, 0) + 1
        result.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    return result


def read_first_valid_sheet(file_bytes: bytes) -> tuple[str, pd.DataFrame, int, list[str]]:
    excel = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
    best: tuple[str, pd.DataFrame, int, list[str]] | None = None
    for sheet in excel.sheet_names:
        raw = pd.read_excel(excel, sheet_name=sheet, header=None)
        if raw.dropna(how="all").empty:
            continue
        header_row = find_header_row(raw)
        if header_row is None:
            continue
        headers = dedupe_headers(raw.iloc[header_row].tolist())
        data = raw.iloc[header_row + 1 :].copy()
        data.columns = headers
        data = data.dropna(how="all").reset_index(drop=True)
        score = sum(1 for required in ("被评估人姓名", "机型", "所属单位") if find_column(headers, META_ALIASES[required]))
        candidate = (sheet, data, header_row, headers)
        if best is None or score > sum(1 for required in ("被评估人姓名", "机型", "所属单位") if find_column(best[3], META_ALIASES[required])):
            best = candidate
    if best is None:
        raise ValueError("没有找到包含有效表头的工作表。请确认 Excel 中包含被评估人、机型或单位字段。")
    return best


def find_column(columns: list[str] | pd.Index, aliases: tuple[str, ...]) -> str | None:
    normalized = {key_text(column): str(column) for column in columns}
    for alias in aliases:
        alias_key = key_text(alias)
        for column_key, original in normalized.items():
            if alias_key == column_key or alias_key in column_key:
                return original
    return None


def actual_start_index(headers: list[str]) -> int:
    for idx, header in enumerate(headers):
        if "训前讲评总得分" in key_text(header) or "教员双盲训前讲评总得分" in key_text(header):
            return idx + 1
    for idx, header in enumerate(headers):
        if key_text(header) in {"决策偏差", "喊话偏差"}:
            return idx
    return min(len(headers), 8)


def is_total_column(header: str) -> bool:
    return "单科总得分" in key_text(header)


def is_note_column(header: str) -> bool:
    return "备注" in clean_text(header)


def negative_parts(value: Any) -> list[float]:
    text = clean_text(value).replace("−", "-").replace("－", "-")
    if not text or "无异常" in text or "不扣分" in text:
        return []
    matches = re.findall(r"[-]\s*(\d+(?:\.\d+)?)\s*分", text)
    if not matches:
        matches = re.findall(r"扣\s*(\d+(?:\.\d+)?)\s*分", text)
    return [-float(match) for match in matches]


def positive_parts(value: Any) -> list[float]:
    text = clean_text(value).replace("＋", "+")
    return [float(match) for match in re.findall(r"\+\s*(\d+(?:\.\d+)?)\s*分", text)]


def subject_for_column(index: int, group_ends: list[int]) -> str:
    for subject_index, end in enumerate(group_ends):
        if index <= end:
            return SUBJECT_NAMES[min(subject_index, len(SUBJECT_NAMES) - 1)]
    return "综合考评"


def parse_workbook(file_bytes: bytes, file_name: str) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sheet_name, data, header_row, headers = read_first_valid_sheet(file_bytes)
    column_map = {field: find_column(headers, aliases) for field, aliases in META_ALIASES.items()}
    warnings: list[str] = []
    required = ("被评估人姓名", "评估日期", "所属单位", "机型", "评估员姓名")
    missing = [field for field in required if not column_map.get(field)]
    if missing:
        warnings.append(f"缺少字段：{', '.join(missing)}")

    start = actual_start_index(headers)
    total_indexes = [idx for idx, header in enumerate(headers) if is_total_column(header)]
    actual_total_indexes = [idx for idx in total_indexes if idx >= start]
    briefing_total_indexes = [idx for idx in total_indexes if idx < start]
    sim_total_idx = next((idx for idx, header in enumerate(headers) if "模拟机评估总得分" in key_text(header)), None)
    if sim_total_idx is None:
        sim_total_idx = len(headers)
    group_ends = actual_total_indexes or [sim_total_idx]

    rating_rows: list[dict[str, Any]] = []
    deduction_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    model_values: set[str] = set()

    for row_idx, row in data.iterrows():
        name = clean_text(row.get(column_map.get("被评估人姓名", ""), ""))
        if not name:
            continue
        model, family = normalize_model(row.get(column_map.get("机型", ""), ""), file_name)
        model_values.add(model)
        record_id = clean_text(row.get(column_map.get("填写ID", ""), "")) or f"{file_name}::{row_idx + header_row + 2}::{name}"
        date_value = row.get(column_map.get("评估日期", ""), "")
        parsed_date = pd.to_datetime(date_value, errors="coerce")
        unit = clean_text(row.get(column_map.get("所属单位", ""), "")) or "未识别单位"
        evaluator = clean_text(row.get(column_map.get("评估员姓名", ""), "")) or "未识别评估员"
        briefing_scores = {
            f"科目{i + 1}": to_number(row.iloc[col_idx])
            for i, col_idx in enumerate(briefing_total_indexes)
            if to_number(row.iloc[col_idx]) is not None
        }
        sim_scores = {
            f"科目{i + 1}": to_number(row.iloc[col_idx])
            for i, col_idx in enumerate(actual_total_indexes)
            if to_number(row.iloc[col_idx]) is not None
        }

        record_deductions: list[dict[str, Any]] = []
        unresolved: list[str] = []
        deduction_sum = 0.0
        for col_idx in range(start, min(sim_total_idx, len(headers))):
            header = headers[col_idx]
            if is_total_column(header) or is_note_column(header):
                continue
            value = row.iloc[col_idx]
            text = clean_text(value)
            if not text:
                continue
            parts = negative_parts(value)
            if parts:
                cell_deduction = sum(parts)
                deduction_sum += cell_deduction
                record_deductions.append(
                    {
                        "记录ID": record_id,
                        "姓名": name,
                        "评估日期": parsed_date,
                        "所属单位": unit,
                        "机型": model,
                        "机型类别": family,
                        "评估员": evaluator,
                        "科目名称": subject_for_column(col_idx, group_ends),
                        "评分项目": header,
                        "扣分标准": text,
                        "扣分值": cell_deduction,
                        "失分": abs(cell_deduction),
                        "原始列": header,
                        "原始列号": col_idx + 1,
                        "来源文件": file_name,
                        "规则状态": "已识别",
                    }
                )
            elif positive_parts(value):
                continue
            elif "无异常" not in text and "不扣分" not in text:
                unresolved.append(header)
                record_deductions.append(
                    {
                        "记录ID": record_id,
                        "姓名": name,
                        "评估日期": parsed_date,
                        "所属单位": unit,
                        "机型": model,
                        "机型类别": family,
                        "评估员": evaluator,
                        "科目名称": subject_for_column(col_idx, group_ends),
                        "评分项目": header,
                        "扣分标准": text,
                        "扣分值": 0.0,
                        "失分": 0.0,
                        "原始列": header,
                        "原始列号": col_idx + 1,
                        "来源文件": file_name,
                        "规则状态": "待复核",
                    }
                )

        source_sim_total = to_number(row.get(column_map.get("模拟机总分", ""), ""))
        computed_sim_total = 100.0 + deduction_sum
        row_flags: list[str] = []
        if unresolved:
            row_flags.append(f"未识别扣分文本：{', '.join(unresolved[:5])}")
        if source_sim_total is not None and abs(source_sim_total - computed_sim_total) > 0.01:
            row_flags.append(f"总分校验不一致：表内 {source_sim_total:g}，按扣分计算 {computed_sim_total:g}")
        if family == FAMILY_UNKNOWN:
            row_flags.append("未识别机型规则")
        if source_sim_total is None:
            row_flags.append("缺少模拟机总分")

        rating_rows.append(
            {
                "记录ID": record_id,
                "姓名": name,
                "评估日期": parsed_date,
                "所属单位": unit,
                "机型": model,
                "机型类别": family,
                "技术等级": clean_text(row.get(column_map.get("技术等级", ""), "")) or "未识别",
                "总飞行时间": to_number(row.get(column_map.get("总飞行时间", ""), "")),
                "本机型经历时间": to_number(row.get(column_map.get("本机型经历时间", ""), "")),
                "评估员": evaluator,
                "训前总分": to_number(row.get(column_map.get("训前总分", ""), "")),
                "训前科目得分": briefing_scores,
                "模拟机科目得分": sim_scores,
                "模拟机总分": source_sim_total,
                "计算模拟机总分": computed_sim_total,
                "总扣分": deduction_sum,
                "失分": abs(deduction_sum),
                "扣分项数量": sum(1 for item in record_deductions if item["失分"] > 0),
                "风险等级": "高" if abs(deduction_sum) >= 10 or unresolved else ("中" if abs(deduction_sum) > 0 else "低"),
                "数据质量": "待复核" if row_flags else "正常",
                "数据质量详情": "；".join(row_flags),
                "来源文件": file_name,
                "工作表": sheet_name,
            }
        )
        deduction_rows.extend(record_deductions)
        quality_rows.append(
            {
                "记录ID": record_id,
                "姓名": name,
                "来源文件": file_name,
                "机型": model,
                "状态": "待复核" if row_flags else "正常",
                "问题": "；".join(row_flags),
            }
        )

    ratings = pd.DataFrame(rating_rows)
    deductions = pd.DataFrame(deduction_rows)
    if deductions.empty:
        deductions = pd.DataFrame(columns=["记录ID", "姓名", "科目名称", "评分项目", "扣分标准", "扣分值", "失分", "规则状态"])
    if ratings.empty:
        ratings = pd.DataFrame(columns=["记录ID", "姓名", "机型类别", "模拟机总分", "数据质量"])
    quality = pd.DataFrame(quality_rows)
    if not quality.empty and warnings:
        quality["问题"] = quality["问题"].where(quality["问题"].astype(str).str.len() > 0, "；".join(warnings))
        quality["状态"] = "待复核"

    summary = {
        "文件名": file_name,
        "工作表": sheet_name,
        "表头行": header_row + 1,
        "机型": ", ".join(sorted(model_values)) or "未识别机型",
        "机型类别": ", ".join(sorted(set(ratings.get("机型类别", pd.Series(dtype=str)).dropna()))) or FAMILY_UNKNOWN,
        "评估人数": int(ratings["姓名"].nunique()) if not ratings.empty else 0,
        "评分记录": len(ratings),
        "扣分记录": int((deductions.get("失分", pd.Series(dtype=float)) > 0).sum()) if not deductions.empty else 0,
        "警告": "；".join(warnings),
    }
    sheet_columns = pd.DataFrame({"字段": headers, "位置": list(range(1, len(headers) + 1))})
    return summary, ratings, deductions, quality, sheet_columns


def parse_many(files: list[tuple[str, bytes]]) -> ParsedBundle:
    summaries: list[dict[str, Any]] = []
    ratings: list[pd.DataFrame] = []
    deductions: list[pd.DataFrame] = []
    quality_frames: list[pd.DataFrame] = []
    columns: list[pd.DataFrame] = []
    for file_name, file_bytes in files:
        try:
            summary, file_ratings, file_deductions, quality, sheet_columns = parse_workbook(file_bytes, file_name)
        except Exception as exc:
            summaries.append({"文件名": file_name, "状态": "失败", "警告": str(exc), "评估人数": 0, "评分记录": 0, "扣分记录": 0})
            continue
        summaries.append({**summary, "状态": "待复核" if summary.get("警告") else "正常"})
        ratings.append(file_ratings)
        deductions.append(file_deductions)
        if not quality.empty:
            quality_frames.append(quality)
        sheet_columns.insert(0, "来源文件", file_name)
        columns.append(sheet_columns)
    return ParsedBundle(
        summaries=pd.DataFrame(summaries),
        ratings=pd.concat(ratings, ignore_index=True) if ratings else pd.DataFrame(),
        deductions=pd.concat(deductions, ignore_index=True) if deductions else pd.DataFrame(),
        sheet_columns=pd.concat(columns, ignore_index=True) if columns else pd.DataFrame(),
    )
