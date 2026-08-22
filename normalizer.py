from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_loader import ParsedBundle


RATING_DEFAULTS = {
    "记录ID": "",
    "姓名": "",
    "评估日期": pd.NaT,
    "所属单位": "未识别单位",
    "机型": "未识别机型",
    "机型类别": "未识别",
    "技术等级": "未识别",
    "总飞行时间": pd.NA,
    "本机型经历时间": pd.NA,
    "评估员": "未识别评估员",
    "训前总分": pd.NA,
    "模拟机总分": pd.NA,
    "计算模拟机总分": pd.NA,
    "总扣分": 0.0,
    "失分": 0.0,
    "扣分项数量": 0,
    "风险等级": "低",
    "数据质量": "正常",
    "数据质量详情": "",
    "来源文件": "",
    "工作表": "",
}

DEDUCTION_DEFAULTS = {
    "记录ID": "",
    "姓名": "",
    "评估日期": pd.NaT,
    "所属单位": "未识别单位",
    "机型": "未识别机型",
    "机型类别": "未识别",
    "评估员": "未识别评估员",
    "科目名称": "未识别科目",
    "评分项目": "未识别评分项目",
    "扣分标准": "",
    "扣分值": 0.0,
    "失分": 0.0,
    "原始列": "",
    "原始列号": pd.NA,
    "来源文件": "",
    "规则状态": "待复核",
}


@dataclass
class NormalizedData:
    ratings: pd.DataFrame
    deductions: pd.DataFrame
    quality: pd.DataFrame
    summaries: pd.DataFrame
    sheet_columns: pd.DataFrame


def ensure_columns(df: pd.DataFrame, defaults: dict[str, object]) -> pd.DataFrame:
    data = df.copy()
    for column, default in defaults.items():
        if column not in data.columns:
            data[column] = default
    return data


def normalize(bundle: ParsedBundle) -> NormalizedData:
    ratings = ensure_columns(bundle.ratings, RATING_DEFAULTS)
    deductions = ensure_columns(bundle.deductions, DEDUCTION_DEFAULTS)
    ratings["评估日期"] = pd.to_datetime(ratings["评估日期"], errors="coerce")
    deductions["评估日期"] = pd.to_datetime(deductions["评估日期"], errors="coerce")
    for column in ("模拟机总分", "计算模拟机总分", "总扣分", "失分"):
        ratings[column] = pd.to_numeric(ratings[column], errors="coerce")
    deductions["扣分值"] = pd.to_numeric(deductions["扣分值"], errors="coerce").fillna(0.0)
    deductions["失分"] = pd.to_numeric(deductions["失分"], errors="coerce").fillna(deductions["扣分值"].abs())
    quality = ratings[["记录ID", "姓名", "来源文件", "机型", "数据质量", "数据质量详情"]].copy()
    quality = quality.rename(columns={"数据质量": "状态", "数据质量详情": "问题"})
    return NormalizedData(
        ratings=ratings,
        deductions=deductions,
        quality=quality,
        summaries=bundle.summaries.copy(),
        sheet_columns=bundle.sheet_columns.copy(),
    )
