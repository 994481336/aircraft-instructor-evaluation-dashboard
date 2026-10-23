from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from statistics_runtime import load_statistics
from company import canonical_company
from data_loader import parse_many
from normalizer import normalize


statistics = load_statistics()
company_summary = statistics.company_summary
person_score_frame = statistics.person_score_frame
score_distribution = statistics.score_distribution
score_text = statistics.score_text
subject_summary = statistics.subject_summary
summary_metrics = statistics.summary_metrics
top_deductions = statistics.top_deductions
type_briefing_segments = statistics.type_briefing_segments
unit_summary = statistics.unit_summary
xlsx_bytes = statistics.xlsx_bytes


st.set_page_config(page_title="型别教员测试结果看板", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

PARSER_CACHE_VERSION = "2026-10-11-reordered-deductions-v7"


@st.cache_data(show_spinner=False)
def cached_parse(payload: tuple[tuple[str, bytes], ...], parser_version: str):
    return parse_many(list(payload))


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#10223d; --muted:#60708a; --blue:#1d5fd0; --cyan:#20a8c9; --orange:#ef8d31; --red:#cf3f50; }
        .stApp { background: linear-gradient(135deg, #f5f8fc 0%, #eef3f9 48%, #e8f1f4 100%); color: var(--ink); }
        [data-testid="stSidebar"] { background: #10223d; min-width: 278px; max-width: 278px; }
        [data-testid="stSidebar"][aria-expanded="true"] { width: 278px; }
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #d6e4f7 !important; }
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] label { color: #f5f8ff !important; }
        [data-testid="stSidebar"] [data-baseweb="select"] { background: #f6f9fd; border: 1px solid #d9e4f2; border-radius: 11px; min-height: 42px; }
        [data-testid="stSidebar"] [data-baseweb="select"] * { color: #10223d !important; }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section { background: #f6f9fd; border: 1px solid #d9e4f2; border-radius: 13px; padding: 12px; }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] * { color: #10223d !important; }
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small { color: #60708a !important; }
        [data-testid="stSidebar"] hr { border-color: rgba(224, 237, 252, .18); }
        .hero { padding: 24px 28px; border-radius: 22px; background: linear-gradient(120deg, #10223d, #154f81 68%, #1e8498); color: white; margin-bottom: 18px; box-shadow: 0 14px 34px rgba(16,34,61,.16); }
        .hero-kicker { font-size: 12px; letter-spacing: .14em; text-transform: uppercase; opacity: .74; }
        .hero-title { font-size: 30px; font-weight: 750; margin-top: 5px; }
        .hero-sub { font-size: 14px; opacity: .84; margin-top: 5px; }
        .metric { border: 1px solid rgba(84,115,150,.16); border-radius: 16px; background: rgba(255,255,255,.84); padding: 15px 16px; box-shadow: 0 6px 18px rgba(32,63,95,.06); min-height: 102px; }
        .metric-label { color: var(--muted); font-size: 12px; }
        .metric-value { color: var(--ink); font-size: 27px; font-weight: 760; margin: 5px 0 2px; }
        .metric-help { color: var(--muted); font-size: 11px; }
        .section-title { color: var(--ink); font-size: 18px; font-weight: 720; margin: 7px 0 10px; }
        .section-note { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
        .quality-ok { color: #147b55; font-weight: 700; }
        .quality-warn { color: #b06a13; font-weight: 700; }
        .small-note { color: var(--muted); font-size: 12px; line-height: 1.6; }
        .brief-title { color: var(--ink); font-size: 31px; font-weight: 780; margin: 10px 0 24px; }
        .brief-section-title { color: var(--ink); font-size: 24px; font-weight: 740; margin: 24px 0 8px; }
        .brief-lead { color: var(--ink); font-size: 20px; font-weight: 600; margin: 0 0 18px; }
        .brief-lead strong { font-size: 27px; font-weight: 780; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(has_data: bool) -> None:
    status = "已接入数据" if has_data else "等待上传 Excel"
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">FLIGHT INSTRUCTOR EVALUATION / DATA WORKBENCH</div>
          <div class="hero-title">型别教员测试结果看板</div>
          <div class="hero-sub">{status} · 空客 / 波音 / 国产民机 · 当前会话内解析，不持久化保存上传文件</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_cards(metrics: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value, note) in zip(cols, metrics):
        with col:
            st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-help">{note}</div></div>', unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    st.markdown(f'<div class="section-title">{title}</div><div class="section-note">{note}</div>', unsafe_allow_html=True)


def empty_state() -> None:
    left, right = st.columns([1.2, 1])
    with left:
        section("从 Excel 开始", "上传导出的教员测试数据，应用会自动识别有效工作表和机型。")
        st.info("请从左侧上传一个或多个 .xlsx 文件。真实数据只在当前会话中解析，不会写入项目文件。")
    with right:
        st.markdown(
            """
            <div class="metric">
              <div class="metric-label">处理流程</div>
              <div class="small-note">01 上传文件<br>02 选择模拟机或训前讲评<br>03 查看机型简报与总览<br>04 下载原始评分和人员均分</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def fmt(value: Any, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    if digits == 1:
        return score_text(value)
    return f"{float(value):.{digits}f}"


def score_chart(frame: pd.DataFrame, x: str, y: str, title: str, color: str | None = None, horizontal: bool = False):
    if frame.empty or x not in frame or y not in frame:
        return None
    label_format = ".0f" if x in {"评分记录数", "评估人数"} or y in {"评分记录数", "评估人数"} else ".1f"
    if horizontal:
        fig = px.bar(frame, x=x, y=y, color=color, orientation="h", title=title, text_auto=label_format)
    else:
        fig = px.bar(frame, x=x, y=y, color=color, title=title, text_auto=label_format)
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=45, b=10), legend_title_text="", height=360)
    if x in {"评分记录数", "评估人数"}:
        fig.update_xaxes(dtick=1)
    return fig


def main() -> None:
    inject_css()
    with st.sidebar:
        st.markdown("### 数据接入")
        uploaded = st.file_uploader("上传评估 Excel", type=["xlsx", "xls"], accept_multiple_files=True, help="支持一次上传多个导出文件。")
        st.markdown("---")

    render_hero(bool(uploaded))
    if not uploaded:
        empty_state()
        st.stop()

    payload = tuple((item.name, item.getvalue()) for item in uploaded)
    with st.spinner("正在解析 Excel、识别机型和扣分明细…"):
        data = normalize(cached_parse(payload, PARSER_CACHE_VERSION))

    with st.sidebar:
        analysis_kind = st.radio("分析内容", ["模拟机表现", "训前讲评"])
        display_mode = st.radio("展示模式", ["按机型类别", "按具体机型"])
        family_options = ["全部"] + sorted(data.ratings.get("机型类别", pd.Series(dtype=str)).dropna().unique().tolist())
        selected_family = st.selectbox("机型类别", family_options)
        working = data.ratings[data.ratings["机型类别"] == selected_family] if selected_family != "全部" else data.ratings
        raw_unit_counts = working.get("所属单位", pd.Series(dtype=str)).dropna().astype(str).value_counts()
        raw_units = sorted(raw_unit_counts.index.tolist())
        companies = sorted({canonical_company(name) for name in raw_units})
        selected_company = st.selectbox("公司", ["全部公司", *companies, "自定义范围"])
        selected_units = raw_units
        if selected_company != "全部公司":
            suggested_units = [name for name in raw_units if canonical_company(name) == selected_company] if selected_company != "自定义范围" else []
            selected_units = st.multiselect(
                "纳入的原表单位名称",
                options=raw_units,
                default=suggested_units,
                format_func=lambda name: f"{name}（{raw_unit_counts[name]}条）",
                key=f"brief_units_{selected_family}_{selected_company}",
            )
            st.caption("已自动勾选识别出的名称，可手动增删；本次选择只在当前会话生效。")
            working = working[working["所属单位"].isin(selected_units)]
        selected_model = "全部"
        if display_mode == "按具体机型":
            model_options = ["全部"] + sorted(working["统计机型"].dropna().unique().tolist())
            selected_model = st.selectbox("具体机型", model_options)
            if selected_model != "全部":
                working = working[working["统计机型"] == selected_model]
        role_options = ["全部"] + sorted(working.get("技术等级", pd.Series(dtype=str)).dropna().unique().tolist())
        selected_role = st.selectbox("技术等级", role_options)

    ratings = data.ratings.copy()
    deductions = data.deductions.copy()
    if selected_family != "全部":
        ratings = ratings[ratings["机型类别"] == selected_family]
        deductions = deductions[deductions["机型类别"] == selected_family]
    if selected_company != "全部公司":
        ratings = ratings[ratings["所属单位"].isin(selected_units)]
        deductions = deductions[deductions["所属单位"].isin(selected_units)]
    if selected_model != "全部":
        ratings = ratings[ratings["统计机型"] == selected_model]
        deductions = deductions[deductions["统计机型"] == selected_model]
    if selected_role != "全部":
        ratings = ratings[ratings["技术等级"] == selected_role]
        deductions = deductions[deductions["记录ID"].isin(ratings["记录ID"])]

    is_briefing = analysis_kind == "训前讲评"
    score_field = "训前总分" if is_briefing else "模拟机总分"
    subject_field = "训前科目得分" if is_briefing else "模拟机科目得分"
    short_label = "讲评" if is_briefing else "模拟机"
    mode_key = "briefing" if is_briefing else "simulator"
    st.markdown(f"### 当前分析：{analysis_kind}")
    tabs = st.tabs(["机型简报", "总览驾驶舱"])
    with tabs[0]:
        if selected_company == "全部公司":
            company_label = "全部公司"
        elif selected_company == "自定义范围":
            company_label = "自定义单位范围"
        elif set(selected_units) != set(suggested_units):
            company_label = f"{selected_company}（自选范围）"
        else:
            company_label = selected_company
        st.markdown(f'<div class="brief-title">{escape(company_label)}型别教员{analysis_kind}评估简报</div>', unsafe_allow_html=True)
        segments = type_briefing_segments(ratings, display_mode)
        if not segments:
            st.info("当前选择范围内没有评分记录。")
        else:
            if display_mode == "按具体机型" and ratings["统计机型"].str.contains("机型未明确", regex=False).any():
                st.caption("部分原表记录只填写了机型类别，已单列为“机型未明确”，未推断具体型号。")
            if selected_company != "全部公司":
                st.caption("本次纳入的原表单位名称：" + "、".join(selected_units))
            for segment_index, (section_title, segment) in enumerate(segments):
                segment_metrics = summary_metrics(segment, pd.DataFrame(), score_field)
                st.markdown(f'<div class="brief-section-title">{escape(section_title)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="brief-lead">评估 <strong>{segment_metrics["评估人数"]}</strong> 人，评分记录 <strong>{segment_metrics["评分记录"]}</strong> 条，{short_label}人员平均分 <strong>{score_text(segment_metrics["平均分"])}</strong></div>', unsafe_allow_html=True)
                if segment_metrics["有效评分人数"] < segment_metrics["评估人数"]:
                    st.caption(f'均分与得分分布仅计入有有效分数的 {segment_metrics["有效评分人数"]} 人。')
                if segment_metrics["有效评分人数"] == 0:
                    st.info(f"当前范围没有有效的{analysis_kind}总分，不使用另一套分数替代。")
                    continue
                left, right = st.columns(2)
                with left:
                    distribution = score_distribution(segment, score_field)
                    fig = score_chart(distribution, "评估人数", "分数区间", f"{short_label}个人均分分布", horizontal=True)
                    if fig:
                        st.plotly_chart(fig, width="stretch", key=f"brief_score_distribution_{mode_key}_{display_mode}_{segment_index}")
                with right:
                    unit_scores = unit_summary(segment, score_field)
                    if selected_company == "全部公司":
                        unit_scores = company_summary(segment, score_field)
                        chart_name = f"{short_label}公司平均分"
                        axis_name = "公司"
                    else:
                        chart_name = f"{short_label}原表单位平均分"
                        axis_name = "所属单位"
                    fig = score_chart(unit_scores, "平均分", axis_name, chart_name, horizontal=True)
                    if fig:
                        fig.update_layout(height=max(360, min(900, len(unit_scores) * 38 + 90)))
                        st.plotly_chart(fig, width="stretch", key=f"brief_unit_average_{mode_key}_{display_mode}_{segment_index}")
                st.divider()

    with tabs[1]:
        metrics = summary_metrics(ratings, deductions, score_field)
        metric_cards([
            ("评估人数", str(metrics["评估人数"]), "当前筛选范围"),
            ("评分记录", str(metrics["评分记录"]), "同一人可有多条"),
            ("人员平均分", fmt(metrics["平均分"]), f'先算个人均分，计入 {metrics["有效评分人数"]} 人'),
            ("最高个人均分", fmt(metrics["最高分"]), "按个人均分比较"),
            ("最低个人均分", fmt(metrics["最低分"]), "按个人均分比较"),
            ("有效评分人数", str(metrics["有效评分人数"]), "无分数人员不计入均分") if is_briefing else ("人均失分", fmt(metrics["平均失分"]), "先算个人平均失分"),
        ])
        with st.expander("人员均分明细"):
            person_columns = ["公司", "姓名", "评分记录", "有效讲评记录" if is_briefing else "有效评分记录", score_field]
            if not is_briefing:
                person_columns.append("失分")
            person_table = person_score_frame(ratings)[person_columns].rename(columns={
                score_field: f"个人{short_label}均分", "有效讲评记录": "有效评分记录", "失分": "个人平均失分",
            })
            st.dataframe(person_table.round(2), width="stretch", hide_index=True)
        section(f"{analysis_kind}评分概览", "先算个人均分，再算公司均分。")
        if metrics["有效评分人数"]:
            left, right = st.columns(2)
            with left:
                distribution = score_distribution(ratings, score_field)
                fig = score_chart(distribution, "评估人数", "分数区间", f"{short_label}个人均分分布", horizontal=True)
                if fig:
                    st.plotly_chart(fig, width="stretch", key=f"overview_score_distribution_{mode_key}")
            with right:
                units = company_summary(ratings, score_field)
                fig = score_chart(units, "平均分", "公司", f"{short_label}公司平均分", horizontal=True)
                if fig:
                    st.plotly_chart(fig, width="stretch", key=f"overview_unit_average_{mode_key}")
        else:
            st.info(f"当前范围没有有效的{analysis_kind}总分，不使用另一套分数替代。")

        section(f"{short_label}科目平均分", "先算每人的科目平均分，再计算总体平均分。")
        subject_avg = subject_summary(ratings, subject_field)
        if not subject_avg.empty:
            fig = score_chart(subject_avg, "平均分", "科目名称", f"{short_label}各科目平均分", horizontal=True)
            if fig:
                st.plotly_chart(fig, width="stretch", key=f"overview_subject_average_{mode_key}")
            st.dataframe(subject_avg.round(2), width="stretch", hide_index=True)
        else:
            st.info(f"当前筛选范围没有可用的{short_label}科目分数，不使用另一套分数替代。")

        if not is_briefing:
            section("扣分项目 TOP 10", "合并同一项目的所有扣分情况，按累计失分排序。")
            top = top_deductions(deductions, 10)
            if top.empty:
                st.info("当前筛选范围内未识别到扣分事件。")
            else:
                project_summary = top.rename(columns={"扣分次数": "扣分记录数", "总失分": "累计失分"})
                plot_data = project_summary.sort_values("累计失分")
                fig = score_chart(plot_data, "累计失分", "评分项目", "各项目累计失分", horizontal=True)
                if fig:
                    fig.update_layout(barmode="group", height=max(360, len(top) * 42 + 80))
                    fig.update_traces(
                        customdata=plot_data[["扣分记录数"]].to_numpy(),
                        hovertemplate="%{y}<br>累计失分：%{x:.1f} 分<br>扣分记录数：%{customdata[0]}<extra></extra>",
                    )
                    st.plotly_chart(fig, width="stretch", key="overview_top_deductions")
                st.dataframe(project_summary.round(2), width="stretch", hide_index=True)
                with st.expander("具体扣分情况"):
                    detail = deductions[deductions["评分项目"].isin(top["评分项目"]) & (deductions["失分"] > 0)]
                    detail = detail.groupby(["评分项目", "扣分标准"], dropna=False).agg(
                        扣分记录数=("记录ID", "nunique"), 累计失分=("失分", "sum"),
                    ).reset_index().sort_values(["评分项目", "累计失分"], ascending=[True, False])
                    st.dataframe(detail.round(2), width="stretch", hide_index=True)

        with st.expander("文件读取概况"):
            file_summary = data.summaries.copy()
            summary_columns = ["文件名", "工作表", "机型类别", "评估人数", "评分记录", "扣分记录", "状态", "警告"]
            if is_briefing:
                summary_columns.remove("扣分记录")
            st.dataframe(file_summary[[column for column in summary_columns if column in file_summary.columns]], width="stretch", hide_index=True)

        common_fields = ["记录ID", "姓名", "所属单位", "机型", "机型类别", "统计机型", "技术等级", "评估日期", "评估员", "来源文件"]
        record_table = ratings.reindex(columns=common_fields + [score_field]).copy()
        raw_subjects = ratings.get(subject_field, pd.Series(index=ratings.index, dtype=object)).map(
            lambda value: value if isinstance(value, dict) else {}
        )
        subject_names = sorted({name for values in raw_subjects for name in values})
        for name in subject_names:
            record_table[f"{short_label}·{name}"] = raw_subjects.map(lambda values: values.get(name))
        person_export = person_score_frame(ratings)[person_columns].rename(columns={
            score_field: f"个人{short_label}均分", "有效讲评记录": "有效评分记录", "失分": "个人平均失分",
        })
        with st.expander("原始评分记录"):
            st.dataframe(record_table, width="stretch", hide_index=True)
        st.download_button(
            f"下载{short_label}原始评分 CSV", data=record_table.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{short_label}原始评分.csv", mime="text/csv", key=f"raw_download_{mode_key}",
        )
        export_sheets = {"原始评分记录": record_table, "人员均分": person_export, "科目均分": subject_avg}
        if not is_briefing:
            export_sheets["扣分明细"] = deductions
        st.download_button(
            f"下载{short_label}分析明细 Excel", data=xlsx_bytes(export_sheets),
            file_name=f"{short_label}分析明细.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"detail_download_{mode_key}",
        )

if __name__ == "__main__":
    main()
