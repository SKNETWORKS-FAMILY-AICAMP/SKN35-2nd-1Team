"""화면 1 — 대시보드. 담당자가 학교 전체 상황을 한눈에 본다."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from components import ui
from components.state import cached_roster, start_page
from components.theme import (
    CATEGORY_COLORS,
    CLASS_COLORS,
    COLORS,
    PLOTLY_CONFIG,
    RISK_COLORS,
    style_figure,
)
from services.predictor import RISK_CATEGORIES, RISK_LABELS_KO
from services.prediction_service import get_service
from services.roster import Roster
from utils.feature_mapping import TARGET_CLASSES, TARGET_LABELS_KO

RISK_ORDER = ("HIGH", "MEDIUM", "LOW")


def risk_distribution_chart(roster: Roster) -> go.Figure:
    counts = roster.frame["위험등급"].value_counts()
    values = [int(counts.get(level, 0)) for level in RISK_ORDER]
    labels = [f"{level} · {RISK_LABELS_KO[level]}" for level in RISK_ORDER]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=[RISK_COLORS[level] for level in RISK_ORDER],
            text=[f"{v}명" for v in values],
            textposition="outside",
            textfont=dict(size=12, color=COLORS["ink_soft"]),
            hovertemplate="%{y}: %{x}명<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["line"], range=[0, max(values) * 1.25 or 1])
    return style_figure(fig, height=230)


def class_distribution_chart(roster: Roster) -> go.Figure:
    counts = roster.frame["예측(원본)"].value_counts()
    values = [int(counts.get(cls, 0)) for cls in TARGET_CLASSES]
    fig = go.Figure(
        go.Pie(
            labels=[TARGET_LABELS_KO[c] for c in TARGET_CLASSES],
            values=values,
            hole=0.52,
            marker=dict(
                colors=[CLASS_COLORS[c] for c in TARGET_CLASSES],
                line=dict(color="#FFFFFF", width=2),
            ),
            textinfo="percent",
            # 기본값(auto)은 글자를 호를 따라 기울여서 발표 화면에서 읽기 어렵다.
            insidetextorientation="horizontal",
            textfont=dict(size=12, color="#FFFFFF"),
            hovertemplate="%{label}: %{value}명 (%{percent})<extra></extra>",
            sort=False,
        )
    )
    # 조각이 좁아도 라벨을 지우지 않는다 (숫자가 사라지면 설명을 못 한다).
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="show")
    return style_figure(fig, height=260, show_legend=True)


def category_distribution_chart(roster: Roster) -> go.Figure:
    """학생별 '주요 위험' 카테고리 분포."""
    counts = roster.frame["주요 위험"].value_counts()
    keys = list(RISK_CATEGORIES)
    labels = [RISK_CATEGORIES[k] for k in keys]
    values = [int(counts.get(label, 0)) for label in labels]
    if "-" in counts.index:
        labels.append("해당 없음")
        values.append(int(counts.get("-", 0)))
        keys.append("")
    colors = [CATEGORY_COLORS.get(k, COLORS["muted"]) for k in keys]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=[f"{v}명" for v in values],
            textposition="outside",
            textfont=dict(size=12, color=COLORS["ink_soft"]),
            hovertemplate="%{x}: %{y}명<extra></extra>",
        )
    )
    fig.update_yaxes(range=[0, max(values) * 1.25 or 1])
    return style_figure(fig, height=250)


def major_risk_chart(roster: Roster) -> go.Figure:
    """전공계열별 평균 중도탈락 확률. 팀 전처리의 Major_field 를 그대로 축으로 쓴다."""
    grouped = (
        roster.frame.groupby("전공 계열")["중도탈락 확률"]
        .agg(["mean", "count"])
        .sort_values("mean", ascending=True)
    )
    fig = go.Figure(
        go.Bar(
            x=(grouped["mean"] * 100).round(1),
            y=grouped.index,
            orientation="h",
            marker_color=COLORS["primary"],
            text=[f"{v:.0f}% ({n}명)" for v, n in zip(grouped["mean"] * 100, grouped["count"])],
            textposition="outside",
            textfont=dict(size=11, color=COLORS["ink_soft"]),
            hovertemplate="%{y}: 평균 %{x}%<extra></extra>",
        )
    )
    fig.update_xaxes(range=[0, 100], showgrid=True, gridcolor=COLORS["line"], ticksuffix="%")
    fig.update_yaxes(showgrid=False)
    return style_figure(fig, height=max(240, 26 * len(grouped)))


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

start_page(
    "대학생 중도탈락 위험 대시보드",
    "학생지원 담당자·지도교수·학사관리자를 위한 조기 확인 화면입니다. "
    "위험도가 높은 학생을 먼저 찾고, 그 학생의 위험요인에 맞는 교내 지원 프로그램을 연결합니다.",
)

service = get_service()
ui.prototype_banner(service)

roster = cached_roster()
frame = roster.frame
total = len(frame)
counts = frame["위험등급"].value_counts()
high = int(counts.get("HIGH", 0))
medium = int(counts.get("MEDIUM", 0))
low = int(counts.get("LOW", 0))
watch_ratio = (high + medium) / total * 100 if total else 0.0
priority = int((frame["집중관리"] == "●").sum())

ui.section("현황 요약", f"더미 학생 {total}명에 대한 예측 결과입니다.")
ui.kpi_grid(
    [
        ("전체 학생 수", f"{total}명", "프로토타입 더미 명단", COLORS["primary"]),
        ("HIGH 위험", f"{high}명", f"전체의 {high / total * 100:.1f}%" if total else "-",
         RISK_COLORS["HIGH"]),
        ("MEDIUM 위험", f"{medium}명", f"전체의 {medium / total * 100:.1f}%" if total else "-",
         RISK_COLORS["MEDIUM"]),
        ("LOW 위험", f"{low}명", f"전체의 {low / total * 100:.1f}%" if total else "-",
         RISK_COLORS["LOW"]),
        ("위험군 비율", f"{watch_ratio:.1f}%", "HIGH + MEDIUM 합계", COLORS["ink"]),
        ("집중관리 대상", f"{priority}명", "복합 위험요인 보유", RISK_COLORS["HIGH"]),
    ]
)

ui.section("분포", "발표에서 설명할 세 가지만 담았습니다.")
left, right = st.columns([1, 1], gap="large")
with left:
    st.markdown('<div class="card-title">위험등급 분포</div>', unsafe_allow_html=True)
    st.plotly_chart(risk_distribution_chart(roster), width="stretch",
                    config=PLOTLY_CONFIG, key="chart_risk")
with right:
    st.markdown('<div class="card-title">예측 클래스 분포</div>', unsafe_allow_html=True)
    st.plotly_chart(class_distribution_chart(roster), width="stretch",
                    config=PLOTLY_CONFIG, key="chart_class")

st.markdown('<div class="card-title">주요 위험요인 카테고리 분포</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">학생마다 가장 우선순위가 높은 위험 1개로 집계했습니다.</div>',
    unsafe_allow_html=True,
)
st.plotly_chart(category_distribution_chart(roster), width="stretch",
                config=PLOTLY_CONFIG, key="chart_category")

st.markdown('<div class="card-title">전공계열별 평균 중도탈락 확률</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">팀 전처리의 Major_field(10계열) 기준입니다. '
    "표본이 적은 계열은 값이 크게 흔들릴 수 있습니다.</div>",
    unsafe_allow_html=True,
)
st.plotly_chart(major_risk_chart(roster), width="stretch",
                config=PLOTLY_CONFIG, key="chart_major")

ui.section("우선 확인이 필요한 학생", "중도탈락 확률이 높은 순서입니다. 상세는 '학생 목록' 화면에서 봅니다.")
top = (
    frame.sort_values("중도탈락 확률", ascending=False)
    .head(8)
    .loc[:, ["학생 ID", "전공 계열", "예측", "중도탈락 확률(%)", "위험등급", "주요 위험", "집중관리"]]
)
st.dataframe(
    top,
    hide_index=True,
    width="stretch",
    column_config={
        "중도탈락 확률(%)": st.column_config.ProgressColumn(
            "중도탈락 확률", format="%.1f%%", min_value=0.0, max_value=100.0
        ),
        "집중관리": st.column_config.TextColumn("집중관리", width="small"),
    },
)
