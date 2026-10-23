from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from analysis import company_summary, person_score_frame, score_distribution, score_text, subject_loss, subject_score_frame, subject_summary, summary_metrics, top_deductions, type_briefing_segments, unit_summary, with_person_identity, xlsx_bytes
from company import canonical_company
from data_loader import FAMILY_RULES, parse_many
from normalizer import normalize


st.set_page_config(page_title="型别教员测试结果看板", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

PARSER_CACHE_VERSION = "2026-10-11-reordered-deductions-v7"


@st.cache_data(show_spinner=False)
def cached_parse(payload: tuple[tuple[str, bytes], ...], parser_version: str):
    return parse_many(list(payload))


@st.cache_data(show_spinner=False)
def load_rule(family: str) -> dict[str, Any]:
    path = Path(__file__).parent / FAMILY_RULES.get(family, "")
    if not path.exists():
        return {"model_family": family, "version": "未知", "subjects": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


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
        .profile-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin: 12px 0 16px; }
        .profile-item { border: 1px solid rgba(84,115,150,.14); border-radius: 12px; background: rgba(255,255,255,.76); padding: 11px 12px; min-height: 66px; }
        .profile-label { color: var(--muted); font-size: 11px; margin-bottom: 5px; }
        .profile-value { color: var(--ink); font-weight: 650; font-size: 14px; overflow-wrap: anywhere; }
        .risk-strip { border-radius: 12px; padding: 10px 13px; background: #fff6e9; border: 1px solid #f3d29f; color: #87520f; font-size: 13px; margin: 10px 0 14px; }
        .brief-title { color: var(--ink); font-size: 31px; font-weight: 780; margin: 10px 0 24px; }
        .brief-section-title { color: var(--ink); font-size: 24px; font-weight: 740; margin: 24px 0 8px; }
        .brief-lead { color: var(--ink); font-size: 20px; font-weight: 600; margin: 0 0 18px; }
        .brief-lead strong { font-size: 27px; font-weight: 780; }
        @media (max-width: 1100px) { .profile-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
        @media (max-width: 720px) { .profile-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
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
              <div class="small-note">01 上传文件<br>02 检查字段和评分口径<br>03 查看总览、个人档案和科目风险<br>04 下载标准化明细</div>
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

    tabs = st.tabs(["机型简报", "总览驾驶舱", "教员档案", "科目分析"])
    with tabs[0]:
        if selected_company == "全部公司":
            company_label = "全部公司"
        elif selected_company == "自定义范围":
            company_label = "自定义单位范围"
        elif set(selected_units) != set(suggested_units):
            company_label = f"{selected_company}（自选范围）"
        else:
            company_label = selected_company
        st.markdown(f'<div class="brief-title">{escape(company_label)}型别教员技能评估简报</div>', unsafe_allow_html=True)
        segments = type_briefing_segments(ratings, display_mode)
        if not segments:
            st.info("当前选择范围内没有评分记录。")
        else:
            if display_mode == "按具体机型" and ratings["统计机型"].str.contains("机型未明确", regex=False).any():
                st.caption("部分原表记录只填写了机型类别，已单列为“机型未明确”，未推断具体型号。")
            st.caption("先计算每位教员的平均分，再计算公司或单位平均分；得分分布按个人均分统计，每人只计一次。")
            with st.expander("统计口径"):
                st.write("统计范围为当前上传并筛选后的记录。同一公司内按姓名归并，不同公司的同名人员分开统计；原表没有人员唯一编号，同一公司内的重名人员需先在源数据中区分。缺失分数不按0分计入，均分计算过程中不提前四舍五入。不同批次或时间段请分别上传相应数据。")
            if selected_company != "全部公司":
                st.caption("本次纳入的原表单位名称：" + "、".join(selected_units))
            for segment_index, (section_title, segment) in enumerate(segments):
                segment_metrics = summary_metrics(segment, pd.DataFrame())
                st.markdown(f'<div class="brief-section-title">{escape(section_title)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="brief-lead">评估 <strong>{segment_metrics["评估人数"]}</strong> 人，评分记录 <strong>{segment_metrics["评分记录"]}</strong> 条，人员平均分 <strong>{score_text(segment_metrics["平均模拟机得分"])}</strong></div>', unsafe_allow_html=True)
                if segment_metrics["有效评分人数"] < segment_metrics["评估人数"]:
                    st.caption(f'均分与得分分布仅计入有有效分数的 {segment_metrics["有效评分人数"]} 人。')
                left, right = st.columns(2)
                with left:
                    distribution = score_distribution(segment)
                    fig = score_chart(distribution, "评估人数", "分数区间", "个人均分分布", horizontal=True)
                    if fig:
                        st.plotly_chart(fig, width="stretch", key=f"brief_score_distribution_{display_mode}_{segment_index}")
                with right:
                    unit_scores = unit_summary(segment)
                    if selected_company == "全部公司":
                        unit_scores = company_summary(segment)
                        chart_name = "公司平均分"
                        axis_name = "公司"
                    else:
                        chart_name = "原表单位平均分"
                        axis_name = "所属单位"
                    fig = score_chart(unit_scores, "平均分", axis_name, chart_name, horizontal=True)
                    if fig:
                        fig.update_layout(height=max(360, min(900, len(unit_scores) * 38 + 90)))
                        st.plotly_chart(fig, width="stretch", key=f"brief_unit_average_{display_mode}_{segment_index}")
                st.divider()

    with tabs[1]:
        metrics = summary_metrics(ratings, deductions)
        metric_cards([
            ("评估人数", str(metrics["评估人数"]), "当前筛选范围"),
            ("评分记录", str(metrics["评分记录"]), "同一人可有多条"),
            ("人员平均分", fmt(metrics["平均模拟机得分"]), f'先算个人均分，计入 {metrics["有效评分人数"]} 人'),
            ("最高个人均分", fmt(metrics["最高分"]), "按个人均分比较"),
            ("最低个人均分", fmt(metrics["最低分"]), "按个人均分比较"),
            ("人均失分", fmt(metrics["平均失分"]), "先算个人平均失分"),
        ])
        with st.expander("人员均分明细"):
            person_table = person_score_frame(ratings).drop(columns=["人员标识"]).rename(columns={
                "模拟机总分": "个人模拟机均分", "训前总分": "个人训前讲评均分", "失分": "个人平均失分",
            })
            st.dataframe(person_table.round(2), width="stretch", hide_index=True)
        section("评分概览", "将训前讲评和模拟机表现分开呈现。")
        left, right = st.columns(2)
        with left:
            distribution = score_distribution(ratings)
            fig = score_chart(distribution, "评估人数", "分数区间", "个人均分分布", horizontal=True)
            if fig:
                st.plotly_chart(fig, width="stretch", key="overview_score_distribution")
        with right:
            units = company_summary(ratings)
            fig = score_chart(units, "平均分", "公司", "公司平均分", horizontal=True)
            if fig:
                st.plotly_chart(fig, width="stretch", key="overview_unit_average")

        section("科目平均分", "先算每人的科目平均分，再计算总体平均分。")
        subject_avg = subject_summary(ratings)
        if not subject_avg.empty:
            fig = score_chart(subject_avg, "平均分", "科目名称", "各科目平均分", horizontal=True)
            if fig:
                st.plotly_chart(fig, width="stretch", key="overview_subject_average")
            st.dataframe(subject_avg.round(2), width="stretch", hide_index=True)
        else:
            st.warning("当前文件没有识别到数值型科目总分列。")

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
            st.dataframe(file_summary[[column for column in summary_columns if column in file_summary.columns]], width="stretch", hide_index=True)

    with tabs[2]:
        section("教员个人档案", "查看个人均分，并保留每次评估的原始得分与扣分。")
        if ratings.empty:
            st.info("当前筛选范围没有人员记录。")
        else:
            people = person_score_frame(ratings).set_index("人员标识")
            person_options = people.sort_values(["姓名", "公司"]).index.tolist()
            selected_person = st.selectbox("选择教员", person_options, format_func=lambda key: f'{people.loc[key, "姓名"]} · {people.loc[key, "公司"]}')
            person_average = people.loc[selected_person]
            identified = with_person_identity(ratings)
            person_rows = identified[identified["人员标识"] == selected_person]
            metric_cards([
                ("个人模拟机均分", fmt(person_average["模拟机总分"]), f'{int(person_average["有效评分记录"])} 条有效评分'),
                ("个人训前讲评均分", fmt(person_average["训前总分"]), "独立评分体系"),
                ("个人平均失分", fmt(person_average["失分"]), f'共 {int(person_average["评分记录"])} 条评估记录'),
            ])
            average_subjects = subject_score_frame(person_rows)
            if not average_subjects.empty:
                average_subjects = average_subjects.groupby("科目名称", as_index=False)["得分"].mean()
                fig = score_chart(average_subjects, "科目名称", "得分", "个人模拟机各科平均分")
                if fig:
                    st.plotly_chart(fig, width="stretch", key="personal_subject_averages")
            record_index = st.selectbox(
                "查看原始评分记录", person_rows.index.tolist(),
                format_func=lambda index: f'{person_rows.loc[index, "评估日期"]} · {person_rows.loc[index, "评估员"]} · 编号 {person_rows.loc[index, "记录ID"]}',
            )
            person = person_rows.loc[record_index]
            person_deductions = deductions[
                (deductions["记录ID"] == person["记录ID"])
                & (deductions["来源文件"] == person["来源文件"])
                & (deductions["姓名"] == person["姓名"])
                & (deductions["所属单位"] == person["所属单位"])
            ]
            rule = load_rule(str(person.get("机型类别", "未识别")))
            st.caption(f"规则版本：{rule.get('version', '未知')} · 来源：{rule.get('source', '未指定')}")
            metric_cards([
                ("本次模拟机得分", fmt(person.get("模拟机总分")), "所选原始记录"),
                ("本次训前讲评", fmt(person.get("训前总分")), "所选原始记录"),
                ("本次失分", fmt(person.get("失分")), "所选记录扣分项合计"),
            ])
            profile_fields = [
                ("姓名", person.get("姓名")), ("所属单位", person.get("所属单位")), ("机型", person.get("机型")),
                ("机型类别", person.get("机型类别")), ("技术等级", person.get("技术等级")), ("评估日期", person.get("评估日期")),
                ("评估员", person.get("评估员")), ("总飞行时间", fmt(person.get("总飞行时间"), 0)),
                ("本机型经历时间", fmt(person.get("本机型经历时间"), 0)),
            ]
            profile_html = "".join(f'<div class="profile-item"><div class="profile-label">{label}</div><div class="profile-value">{value if value is not None and not pd.isna(value) else "-"}</div></div>' for label, value in profile_fields)
            st.markdown(f'<div class="profile-grid">{profile_html}</div>', unsafe_allow_html=True)
            if float(person.get("失分") or 0) > 0:
                st.markdown(f'<div class="risk-strip">本次评估失分 {fmt(person.get("失分"))} 分，具体扣分见下方明细。</div>', unsafe_allow_html=True)
            person_scores = subject_score_frame(person_rows.loc[[record_index]])
            if not person_scores.empty:
                fig = px.bar(person_scores, x="科目名称", y="得分", title="本次模拟机各科得分", text_auto=".1f", color="科目名称")
                fig.update_layout(template="plotly_white", showlegend=False, height=360, margin=dict(l=10, r=10, t=45, b=10))
                st.plotly_chart(fig, width="stretch", key="personal_subject_scores")
            if person_deductions.empty:
                st.info("本次评估未识别到扣分事件。")
            else:
                st.dataframe(person_deductions.drop(columns=["记录ID"], errors="ignore"), width="stretch", hide_index=True)

    with tabs[3]:
        section("科目分析", "查看不同科目的平均表现和失分结构。")
        loss = subject_loss(deductions)
        if loss.empty:
            st.info("当前没有扣分科目数据。")
        else:
            left, right = st.columns(2)
            with left:
                fig = score_chart(loss, "总失分", "科目名称", "各科目总失分", horizontal=True)
                if fig:
                    st.plotly_chart(fig, width="stretch", key="subject_total_loss")
            with right:
                subject_options = loss["科目名称"].tolist()
                selected_subject = st.selectbox("选择科目下钻", subject_options)
                detail = deductions[(deductions["科目名称"] == selected_subject) & (deductions["失分"] > 0)]
                detail = detail.groupby("评分项目", as_index=False).agg(扣分次数=("记录ID", "nunique"), 总失分=("失分", "sum")).sort_values("总失分", ascending=False)
                fig = score_chart(detail.head(10), "总失分", "评分项目", f"{selected_subject} 扣分项", horizontal=True)
                if fig:
                    st.plotly_chart(fig, width="stretch", key="subject_detail")
            st.dataframe(loss.round(2), width="stretch", hide_index=True)

        st.download_button("下载标准化人员数据", data=ratings.drop(columns=["训前科目得分", "模拟机科目得分"], errors="ignore").to_csv(index=False).encode("utf-8-sig"), file_name="标准化人员数据.csv", mime="text/csv")
        st.download_button("下载扣分明细 Excel", data=xlsx_bytes({"人员数据": ratings.drop(columns=["训前科目得分", "模拟机科目得分"], errors="ignore"), "扣分明细": deductions}), file_name="型别教员测试结果明细.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    main()
