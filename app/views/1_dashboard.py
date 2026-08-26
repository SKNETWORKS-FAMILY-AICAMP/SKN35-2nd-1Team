"""
화면 1 — 대시보드.

목표는 하나다: **담당자가 아침에 열어서 오늘 누구를 먼저 확인해야 하는지 바로 아는 것.**
그래서 지표를 나열하지 않고 세 단으로 나눈다.

    Level 1  지금 조치가 필요한 규모   — 크게, 먼저
    Level 2  그 위험이 어떤 성격인가   — 차트 3개
    Level 3  그래서 이 학생부터        — 우선 확인 명단
"""

from __future__ import annotations

from html import escape
from urllib.parse import quote

import plotly.graph_objects as go
import streamlit as st

from components import ui
from components.state import PAGE_STUDENTS, cached_roster, start_page
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

RISK_ORDER = ("HIGH", "MEDIUM", "LOW")

#: 우선 명단에서 학생을 눌렀을 때 열 주소. st.navigation 이 붙이는 경로와 같아야 한다.
STUDENT_DETAIL_URL = "students"


# ---------------------------------------------------------------------------
# 차트 — 하나하나가 "그래서 뭘 봐야 하는가" 를 답해야 한다
# ---------------------------------------------------------------------------

def risk_composition(roster: Roster) -> go.Figure:
    """코호트 전체가 어떤 비율로 나뉘는가 — 막대 하나로 끝낸다.

    등급이 셋뿐이라 막대 세 개를 세우는 것보다 **하나의 띠**가 비율을 훨씬 빨리 읽힌다.
    """
    counts = roster.frame["위험등급"].value_counts()
    total = len(roster.frame) or 1
    fig = go.Figure()
    for level in RISK_ORDER:
        n = int(counts.get(level, 0))
        fig.add_bar(
            x=[n / total * 100], y=["risk"], orientation="h",
            marker=dict(color=RISK_COLORS[level], line=dict(width=0)),
            name=f"{level} · {RISK_LABELS_KO[level]}",
            text=f"{n}명", textposition="inside", insidetextanchor="middle",
            textfont=dict(color="#FFFFFF", size=12),
            hovertemplate=f"{level}: {n}명 (%{{x:.1f}}%)<extra></extra>",
        )
    fig.update_layout(barmode="stack", bargap=0.1)
    fig.update_xaxes(visible=False, range=[0, 100])
    fig.update_yaxes(visible=False)
    # plotly 범례는 이 높이에서 눌려 잘린다. 범례는 화면 아래에 배지로 따로 그린다.
    return style_figure(fig, height=54, show_legend=False, grid="none")


def category_rows(roster: Roster) -> list[dict]:
    """어떤 성격의 지원이 얼마나 필요한가 — 부서 배분의 근거."""
    counts = roster.frame["주요 위험"].value_counts()
    total = len(roster.frame) or 1
    items = []
    for key, label in RISK_CATEGORIES.items():
        n = int(counts.get(label, 0))
        items.append({"label": label, "value": n, "color": CATEGORY_COLORS[key],
                      "display": f"{n:,}명 · {n / total * 100:.0f}%"})
    if "-" in counts.index:
        n = int(counts.get("-", 0))
        items.append({"label": "해당 없음", "value": n, "color": COLORS["faint"],
                      "display": f"{n:,}명 · {n / total * 100:.0f}%"})
    return sorted(items, key=lambda r: r["value"], reverse=True)


def major_rows(roster: Roster) -> list[dict]:
    """어느 전공계열에 위험이 몰려 있는가 — 학과 단위 대응의 출발점."""
    grouped = (
        roster.frame.groupby("전공 계열")
        .agg(mean=("중도탈락 확률", "mean"), n=("중도탈락 확률", "size"))
        .sort_values("mean", ascending=False)
    )
    rows = []
    for name, row in grouped.iterrows():
        pct = row["mean"] * 100
        color = (
            RISK_COLORS["HIGH"] if pct >= 60
            else RISK_COLORS["MEDIUM"] if pct >= 30
            else COLORS["primary"]
        )
        rows.append({"label": name, "value": pct, "color": color,
                     "display": f"{pct:.0f}% · {int(row['n']):,}명"})
    return rows


def approval_scatter(roster: Roster) -> go.Figure:
    """모델이 가장 크게 보는 신호(2학기 이수율)와 위험의 관계.

    "왜 이 학생들이 위험한가" 를 한 장으로 설명하는 차트다.
    """
    frame = roster.frame
    fig = go.Figure(
        go.Scattergl(
            x=frame["2학기 이수율"], y=frame["중도탈락 확률(%)"],
            mode="markers",
            marker=dict(
                size=6, opacity=0.55,
                color=[RISK_COLORS[level] for level in frame["위험등급"]],
                line=dict(width=0),
            ),
            customdata=frame[["학생 ID", "전공 계열"]],
            hovertemplate="%{customdata[0]} · %{customdata[1]}<br>"
                          "2학기 이수율 %{x}% · 위험 %{y:.0f}%<extra></extra>",
        )
    )
    fig.update_xaxes(title=dict(text="2학기 이수율 (%)", font=dict(size=11)), range=[-4, 104])
    fig.update_yaxes(title=dict(text="중도탈락 확률 (%)", font=dict(size=11)), range=[-4, 104])
    return style_figure(fig, height=290, grid="y")


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

service = get_service()
roster = cached_roster()
frame = roster.frame

start_page(
    "위험 현황",
    "오늘 먼저 확인해야 할 학생을 찾는 화면입니다. 위험도가 높은 순서로 보고, "
    "그 학생의 위험요인에 맞는 교내 지원을 연결합니다.",
    meta=(
        f'<div class="ds-eyebrow">Roster</div>'
        f'<div class="ds-sub" style="margin-top:4px">{escape(roster.source)}</div>'
    ),
)

ui.prototype_banner(service)

total = len(frame)
counts = frame["위험등급"].value_counts()
high = int(counts.get("HIGH", 0))
medium = int(counts.get("MEDIUM", 0))
low = int(counts.get("LOW", 0))
focus = int((frame["집중관리"] == "●").sum())
predicted_dropout = int((frame["예측(원본)"] == "Dropout").sum())
watch = high + medium

# ── Level 1 — 지금 조치가 필요한 규모 ──────────────────────────────────────
ui.section("지금 조치가 필요한 규모", "이 화면에서 가장 먼저 읽어야 할 숫자입니다.")

hero_col, side_col = st.columns([1, 1.9], gap="medium")
with hero_col:
    ui.kpi_hero(
        "즉시 확인 대상 · HIGH",
        f"{high:,}",
        f"전체 {total:,}명 중 {high / total * 100:.1f}% · 중도탈락 확률 60% 이상",
        RISK_COLORS["HIGH"],
        unit="명",
        share=high / total if total else 0,
    )
with side_col:
    ui.kpi_row(
        [
            {"label": "집중관리 대상", "value": f"{focus:,}", "unit": "명",
             "caption": "서로 다른 영역의 위험이 겹친 학생",
             "accent": RISK_COLORS["HIGH"], "share": focus / total if total else 0},
            {"label": "관찰 필요 · HIGH+MEDIUM", "value": f"{watch / total * 100:.1f}" if total else "0",
             "unit": "%", "caption": f"{watch:,}명",
             "accent": RISK_COLORS["MEDIUM"], "share": watch / total if total else 0},
            {"label": "Dropout 예측", "value": f"{predicted_dropout:,}", "unit": "명",
             "caption": "확률 50% 이상",
             "accent": CLASS_COLORS["Dropout"],
             "share": predicted_dropout / total if total else 0},
        ],
        columns=3,
    )
    ui.spacer(6)
    ui.kpi_row(
        [
            {"label": "MEDIUM", "value": f"{medium:,}", "unit": "명",
             "caption": "정기 모니터링", "accent": RISK_COLORS["MEDIUM"]},
            {"label": "LOW", "value": f"{low:,}", "unit": "명",
             "caption": "학기 단위 확인", "accent": RISK_COLORS["LOW"]},
            {"label": "명단 규모", "value": f"{total:,}", "unit": "명",
             "caption": "실데이터" if roster.is_real else "합성 더미",
             "accent": COLORS["primary"]},
        ],
        columns=3,
    )

ui.spacer(18)
st.plotly_chart(risk_composition(roster), width="stretch",
                config=PLOTLY_CONFIG, key="c_comp")
st.markdown(
    '<div style="display:flex;gap:10px;margin-top:-6px">'
    + "".join(
        ui.risk_pill_html(level) + f'<span class="ds-caption ds-num">'
        f'{int(counts.get(level, 0)):,}명 · {int(counts.get(level, 0)) / total * 100:.1f}%</span>'
        for level in RISK_ORDER
    )
    + "</div>",
    unsafe_allow_html=True,
)

# ── Level 2 — 그 위험이 어떤 성격인가 ──────────────────────────────────────
ui.section("위험의 성격", "무엇을 준비해야 하고, 어디에 몰려 있는가.")

c1, c2 = st.columns([1, 1], gap="large")
with c1, st.container(border=True):
    st.markdown(
        '<div class="card-title">주요 위험요인 카테고리</div>'
        '<div class="card-sub">학생마다 우선순위가 가장 높은 위험 1개로 집계했습니다. '
        "부서별 대응 규모를 여기서 잡습니다.</div>",
        unsafe_allow_html=True,
    )
    ui.bar_chart(category_rows(roster), label_width=92)
with c2, st.container(border=True):
    st.markdown(
        '<div class="card-title">2학기 이수율과 위험</div>'
        '<div class="card-sub">모델이 가장 크게 보는 신호입니다. '
        "왼쪽 아래로 갈수록 이수율이 낮고 위험이 높습니다.</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(approval_scatter(roster), width="stretch",
                    config=PLOTLY_CONFIG, key="c_scatter")

ui.spacer(6)
with st.container(border=True):
    st.markdown(
        '<div class="card-title">전공계열별 평균 중도탈락 확률</div>'
        '<div class="card-sub">팀 전처리의 Major_field(10계열) 기준입니다. '
        "표본이 적은 계열은 값이 크게 흔들릴 수 있으니 인원 수를 함께 봅니다.</div>",
        unsafe_allow_html=True,
    )
    ui.bar_chart(major_rows(roster), label_width=110)

# ── Level 3 — 그래서 이 학생부터 ───────────────────────────────────────────
ui.section("먼저 확인할 학생", "중도탈락 확률이 높은 순서입니다.")

# 확률만으로 정렬하면 위쪽이 서로 붙는다 (위험 점수가 최대치인 학생이 수백 명이다).
# **발동 규칙 수**로 동점을 가른다 — 여러 영역이 동시에 무너진 학생이 먼저다.
rule_counts = {row.student.student_id: len(row.recommendation.matched) for row in roster.rows}
# 확률을 그대로 정렬 키로 쓰면 소수점 여섯째 자리에서 갈려 동점이 성립하지 않는다.
# 화면에 보이는 자리수(0.1%)로 반올림해서 묶어야 규칙 수가 실제로 순위를 가른다.
ordered = (
    frame.assign(
        발동규칙=frame["학생 ID"].map(rule_counts),
        표시확률=frame["중도탈락 확률"].round(3),
    )
    .sort_values(["표시확률", "발동규칙"], ascending=[False, False])
    .head(8)
)
ui.priority_table(
    [
        {
            "rank": i + 1,
            "sid": row["학생 ID"],
            "major": row["전공 계열"],
            "probability": float(row["중도탈락 확률"]),
            "level": row["위험등급"],
            "category": row["주요 위험"],
            "rules": int(row["발동규칙"]),
            "focus": row["집중관리"] == "●",
            # 학생 목록 화면이 이 값을 읽어 바로 상세를 연다.
            "href": f"{STUDENT_DETAIL_URL}?student={quote(str(row['학생 ID']))}",
        }
        for i, (_, row) in enumerate(ordered.iterrows())
    ]
)

ui.spacer(12)
if st.button("전체 명단에서 더 보기", width="stretch"):
    st.switch_page(PAGE_STUDENTS)
