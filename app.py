from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from analysis import score_distribution, subject_loss, subject_score_frame, summary_metrics, top_deductions, unit_summary, xlsx_bytes
from data_loader import FAMILY_RULES, parse_many
from normalizer import normalize


st.set_page_config(page_title="型别教员测试结果看板", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")


@st.cache_data(show_spinner=False)
def cached_parse(payload: tuple[tuple[str, bytes], ...]):
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
    return f"{float(value):.{digits}f}"


def score_chart(frame: pd.DataFrame, x: str, y: str, title: str, color: str | None = None, horizontal: bool = False):
    if frame.empty or x not in frame or y not in frame:
        return None
    if horizontal:
        fig = px.bar(frame, x=x, y=y, color=color, orientation="h", title=title, text_auto=".1f")
    else:
        fig = px.bar(frame, x=x, y=y, color=color, title=title, text_auto=".1f")
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=45, b=10), legend_title_text="", height=360)
    return fig


def main() -> None:
    inject_css()
    with st.sidebar:
        st.markdown("### 数据接入")
        uploaded = st.file_uploader("上传评估 Excel", type=["xlsx", "xls"], accept_multiple_files=True, help="支持一次上传多个导出文件。")
        st.markdown("---")
        st.caption("评分规则")
        st.caption("空客 / 波音 / 国产民机规则已结构化内置。正式合格线暂未启用。")

    render_hero(bool(uploaded))
    if not uploaded:
        empty_state()
        st.stop()

    payload = tuple((item.name, item.getvalue()) for item in uploaded)
    with st.spinner("正在解析 Excel、识别机型和扣分明细…"):
        data = normalize(cached_parse(payload))

    with st.sidebar:
        family_options = ["全部"] + sorted(data.ratings.get("机型类别", pd.Series(dtype=str)).dropna().unique().tolist())
        selected_family = st.selectbox("机型类别", family_options)
        working = data.ratings[data.ratings["机型类别"] == selected_family] if selected_family != "全部" else data.ratings
        unit_options = ["全部"] + sorted(working.get("所属单位", pd.Series(dtype=str)).dropna().unique().tolist())
        selected_unit = st.selectbox("所属单位", unit_options)
        role_options = ["全部"] + sorted(working.get("技术等级", pd.Series(dtype=str)).dropna().unique().tolist())
        selected_role = st.selectbox("技术等级", role_options)

    ratings = data.ratings.copy()
    deductions = data.deductions.copy()
    if selected_family != "全部":
        ratings = ratings[ratings["机型类别"] == selected_family]
        deductions = deductions[deductions["机型类别"] == selected_family]
    if selected_unit != "全部":
        ratings = ratings[ratings["所属单位"] == selected_unit]
        deductions = deductions[deductions["所属单位"] == selected_unit]
    if selected_role != "全部":
        ratings = ratings[ratings["技术等级"] == selected_role]
        deductions = deductions[deductions["技术等级"] == selected_role]

    metrics = summary_metrics(ratings, deductions)
    metric_cards([
        ("评估人数", str(metrics["评估人数"]), "当前筛选范围"),
        ("平均模拟机得分", fmt(metrics["平均模拟机得分"]), "表内总分"),
        ("最高分", fmt(metrics["最高分"]), "样本峰值"),
        ("最低分", fmt(metrics["最低分"]), "重点复盘对象"),
        ("平均失分", fmt(metrics["平均失分"]), "按人员计算"),
        ("待复核", str(metrics["待复核"]), "总分或文本异常"),
    ])

    tabs = st.tabs(["总览驾驶舱", "教员档案", "科目分析", "数据质量"])
    with tabs[0]:
        section("评分概览", "将训前讲评和模拟机表现分开呈现。")
        left, right = st.columns(2)
        with left:
            distribution = score_distribution(ratings)
            fig = score_chart(distribution, "人数", "分数区间", "得分分布", horizontal=True)
            if fig:
                st.plotly_chart(fig, width="stretch")
        with right:
            units = unit_summary(ratings)
            fig = score_chart(units, "平均分", "所属单位", "单位平均分", horizontal=True)
            if fig:
                st.plotly_chart(fig, width="stretch")

        section("科目平均分", "以 Excel 中的模拟机各科总得分为准。")
        subjects = subject_score_frame(ratings)
        if not subjects.empty:
            subject_avg = subjects.groupby("科目名称", as_index=False).agg(平均分=("得分", "mean"), 评估人数=("得分", "count"))
            fig = score_chart(subject_avg, "平均分", "科目名称", "各科目平均分", horizontal=True)
            if fig:
                st.plotly_chart(fig, width="stretch")
            st.dataframe(subject_avg.round(2), width="stretch", hide_index=True)
        else:
            st.warning("当前文件没有识别到数值型科目总分列。")

        section("高频扣分项", "按总失分排序，待复核项目会单独标记。")
        top = top_deductions(deductions, 10)
        if top.empty:
            st.success("当前筛选范围内没有可识别的扣分事件。")
        else:
            top["显示项"] = top["科目名称"] + " · " + top["评分项目"]
            fig = score_chart(top.sort_values("总失分"), "总失分", "显示项", "扣分项 TOP 10", horizontal=True)
            if fig:
                st.plotly_chart(fig, width="stretch")
            st.dataframe(top.drop(columns=["显示项"]).round(2), width="stretch", hide_index=True)

    with tabs[1]:
        section("教员个人档案", "选择人员查看经历、总分、科目分数与具体扣分。")
        if ratings.empty:
            st.info("当前筛选范围没有人员记录。")
        else:
            person_options = sorted(ratings["姓名"].dropna().unique().tolist())
            selected_person = st.selectbox("选择教员", person_options)
            person = ratings[ratings["姓名"] == selected_person].iloc[0]
            person_deductions = deductions[deductions["记录ID"] == person["记录ID"]]
            rule = load_rule(str(person.get("机型类别", "未识别")))
            st.caption(f"规则版本：{rule.get('version', '未知')} · 来源：{rule.get('source', '未指定')}")
            metric_cards([
                ("模拟机总分", fmt(person.get("模拟机总分")), "Excel 表内总分"),
                ("按扣分计算", fmt(person.get("计算模拟机总分")), "100 - 实际失分"),
                ("训前讲评", fmt(person.get("训前总分")), "独立评分体系"),
                ("总失分", fmt(person.get("失分")), "扣分项合计"),
            ])
            profile_fields = [
                ("姓名", person.get("姓名")), ("所属单位", person.get("所属单位")), ("机型", person.get("机型")),
                ("机型类别", person.get("机型类别")), ("技术等级", person.get("技术等级")), ("评估日期", person.get("评估日期")),
                ("评估员", person.get("评估员")), ("总飞行时间", fmt(person.get("总飞行时间"), 0)),
                ("本机型经历时间", fmt(person.get("本机型经历时间"), 0)), ("数据质量", person.get("数据质量详情") or "正常"),
            ]
            profile_html = "".join(f'<div class="profile-item"><div class="profile-label">{label}</div><div class="profile-value">{value if value is not None and not pd.isna(value) else "-"}</div></div>' for label, value in profile_fields)
            st.markdown(f'<div class="profile-grid">{profile_html}</div>', unsafe_allow_html=True)
            if person.get("数据质量") != "正常" or float(person.get("失分") or 0) > 0:
                st.markdown(f'<div class="risk-strip">复盘提示：该教员累计失分 {fmt(person.get("失分"))} 分。请结合下方扣分明细和科目表现安排讲评。</div>', unsafe_allow_html=True)
            person_scores = subject_score_frame(ratings[ratings["记录ID"] == person["记录ID"]])
            if not person_scores.empty:
                fig = px.bar(person_scores, x="科目名称", y="得分", title="个人模拟机各科得分", text_auto=".1f", color="科目名称")
                fig.update_layout(template="plotly_white", showlegend=False, height=360, margin=dict(l=10, r=10, t=45, b=10))
                st.plotly_chart(fig, width="stretch")
            if person_deductions.empty:
                st.success("该教员没有识别到扣分事件。")
            else:
                st.dataframe(person_deductions.drop(columns=["记录ID"], errors="ignore"), width="stretch", hide_index=True)

    with tabs[2]:
        section("科目分析", "查看不同科目的平均表现和失分结构。")
        loss = subject_loss(deductions)
        if loss.empty:
            st.info("当前没有扣分科目数据。")
        else:
            left, right = st.columns(2)
            with left:
                fig = score_chart(loss, "总失分", "科目名称", "各科目总失分", horizontal=True)
                if fig:
                    st.plotly_chart(fig, width="stretch")
            with right:
                subject_options = loss["科目名称"].tolist()
                selected_subject = st.selectbox("选择科目下钻", subject_options)
                detail = deductions[(deductions["科目名称"] == selected_subject) & (deductions["失分"] > 0)]
                detail = detail.groupby("评分项目", as_index=False).agg(扣分次数=("记录ID", "nunique"), 总失分=("失分", "sum")).sort_values("总失分", ascending=False)
                fig = score_chart(detail.head(10), "总失分", "评分项目", f"{selected_subject} 扣分项", horizontal=True)
                if fig:
                    st.plotly_chart(fig, width="stretch")
            st.dataframe(loss.round(2), width="stretch", hide_index=True)

    with tabs[3]:
        section("数据质量与规则状态", "所有不确定结果先标记为待复核，不阻断看板。")
        st.dataframe(data.summaries, width="stretch", hide_index=True)
        quality = data.quality.copy()
        if not quality.empty:
            st.dataframe(quality, width="stretch", hide_index=True)
        unresolved = deductions[deductions["规则状态"] == "待复核"] if not deductions.empty else pd.DataFrame()
        if not unresolved.empty:
            st.warning(f"发现 {len(unresolved)} 条未识别文本，请回到原始 Excel 核对。")
            st.dataframe(unresolved, width="stretch", hide_index=True)
        else:
            st.success("未发现未识别扣分文本。")
        st.download_button("下载标准化人员数据", data=ratings.drop(columns=["训前科目得分", "模拟机科目得分"], errors="ignore").to_csv(index=False).encode("utf-8-sig"), file_name="标准化人员数据.csv", mime="text/csv")
        st.download_button("下载扣分明细 Excel", data=xlsx_bytes({"人员数据": ratings.drop(columns=["训前科目得分", "模拟机科目得分"], errors="ignore"), "扣分明细": deductions, "数据质量": quality}), file_name="型别教员测试结果明细.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    main()
