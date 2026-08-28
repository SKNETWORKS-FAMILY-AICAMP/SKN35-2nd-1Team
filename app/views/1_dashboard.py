"""
화면 2 — 대시보드.

목표는 하나다: **담당자가 아침에 열어서 오늘 누구를 먼저 확인해야 하는지 바로 아는 것.**

    Level 1  지금 조치가 필요한 규모 — 크게, 먼저 · 옆에 바로가기
    Level 2  그 위험이 어떤 성격인가 — 도넛 셋 + 순위 하나

어떤 그래프를 쓰는가 — 값의 성격이 정한다
    도넛      부분의 합이 전체일 때만. 조각 크기가 곧 비중이다.
              (위험등급 구성 · 부서별 업무량)
    세로 막대  항목이 적고(3~5개) 라벨이 짧을 때. 크기를 위아래로 바로 비교한다.
              (위험요인 카테고리)
    가로 막대  항목이 많거나 라벨이 길 때. 이름이 잘리지 않는다.
              (전공 계열 · 피처 중요도)

    피처 중요도처럼 **순위**인 값은 도넛에 넣지 않는다 — 조각 크기가 아무 뜻도
    없어지고 이름도 못 읽는다.

    막대와 도넛은 모두 0에서 실제 값까지 **차오르며** 등장한다. 값이 얼마나
    찼는지가 눈에 남게 하려는 것이고, 접근성 설정(모션 축소)에서는 꺼진다.
"""

from __future__ import annotations

import streamlit as st

from components import ui
from components.state import PAGE_RISK, PAGE_STUDENTS, cached_roster, start_page
from components.theme import CATEGORY_COLORS, CLASS_COLORS, COLORS, RISK_COLORS
from services import model_metrics
from services.predictor import RISK_CATEGORIES, RISK_LABELS_KO
from services.prediction_service import get_service

RISK_ORDER = ("HIGH", "MEDIUM", "LOW")

#: 전공 계열 도넛에 세울 조각 수. 더 넣으면 조각이 실처럼 얇아져 읽히지 않는다.
MAJOR_SLICES = 6


# ---------------------------------------------------------------------------
# 집계 — 화면이 쓰는 형태로만 만든다
# ---------------------------------------------------------------------------

def risk_rows(frame) -> list[dict]:
    counts = frame["위험등급"].value_counts()
    return [
        {"label": f"{level} · {RISK_LABELS_KO[level]}",
         "value": int(counts.get(level, 0)),
         "color": RISK_COLORS[level],
         "display": f"{int(counts.get(level, 0)):,}명"}
        for level in RISK_ORDER
    ]


def category_rows(frame) -> list[dict]:
    """학생마다 **1순위** 위험 하나로 집계. 부서별 대응 규모의 출발점이다."""
    counts = frame["주요 위험"].value_counts()
    rows = [
        {"label": label, "value": int(counts.get(label, 0)), "color": CATEGORY_COLORS[key],
         "display": f"{int(counts.get(label, 0)):,}명"}
        for key, label in RISK_CATEGORIES.items()
    ]
    none = int(counts.get("-", 0))
    if none:
        rows.append({"label": "해당 없음", "value": none, "color": COLORS["faint"],
                     "display": f"{none:,}명"})
    return sorted(rows, key=lambda r: r["value"], reverse=True)


def workload_rows(roster) -> list[dict]:
    """**발동한 규칙 건수** 기준 비중.

    위 카테고리 도넛이 '학생을 어디로 보낼까'라면 이쪽은 '어느 부서에 일이 몇 건
    쌓이는가'다. 한 학생이 학업·경제에 동시에 걸리면 양쪽에 각각 센다.
    """
    tally = {key: 0 for key in RISK_CATEGORIES}
    for row in roster.rows:
        for matched in row.recommendation.matched:
            tally[matched.category] = tally.get(matched.category, 0) + 1
    return sorted(
        ({"label": RISK_CATEGORIES[key], "value": value, "color": CATEGORY_COLORS[key],
          "display": f"{value:,}건"} for key, value in tally.items()),
        key=lambda r: r["value"], reverse=True,
    )


def major_rows(frame) -> list[dict]:
    """전공 계열별 **예측 Dropout 학생 수**의 분포. 범례에 그 계열의 비율을 함께 적는다.

    도넛은 '어디에 몰려 있나'(수)를 답하고, 범례의 비율은 '그 계열이 얼마나
    위험한가'(율)를 답한다. 율만으로 도넛을 그리면 조각 합이 전체가 아니라
    그림 자체가 거짓말이 된다.
    """
    dropout = frame[frame["예측(원본)"] == "Dropout"]
    counts = dropout["전공 계열"].value_counts()
    sizes = frame["전공 계열"].value_counts()

    palette = (COLORS["primary"], CATEGORY_COLORS["academic"], CATEGORY_COLORS["financial"],
               CATEGORY_COLORS["adaptation"], RISK_COLORS["MEDIUM"], RISK_COLORS["HIGH"])
    rows = []
    for index, (name, value) in enumerate(counts.head(MAJOR_SLICES).items()):
        rate = value / int(sizes.get(name, 1)) * 100
        rows.append({"label": name, "value": int(value),
                     "color": palette[index % len(palette)],
                     "display": f"{int(value):,}명 · 율 {rate:.0f}%"})
    rest = int(counts.iloc[MAJOR_SLICES:].sum()) if len(counts) > MAJOR_SLICES else 0
    if rest:
        rows.append({"label": "그 밖의 계열", "value": rest, "color": COLORS["faint"],
                     "display": f"{rest:,}명"})
    return rows


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

service = get_service()
roster = cached_roster()
frame = roster.frame

start_page(
    "위험 현황",
    "오늘 먼저 확인해야 할 학생을 찾는 화면입니다.",
    meta=(
        '<div class="ds-eyebrow">Students</div>'
        f'<div class="ds-sub" style="margin-top:4px">{len(frame):,}명 · 위험도 재계산 완료</div>'
    ),
)

total = len(frame)
counts = frame["위험등급"].value_counts()
high = int(counts.get("HIGH", 0))
medium = int(counts.get("MEDIUM", 0))
predicted_dropout = int((frame["예측(원본)"] == "Dropout").sum())

# ── Level 1 — 지금 조치가 필요한 규모 ──────────────────────────────────────
ui.section("지금 조치가 필요한 규모", "이 화면에서 가장 먼저 읽어야 할 숫자입니다.")

hero_col, side_col = st.columns([1, 1.9], gap="medium")
with hero_col:
    ui.kpi_hero(
        "즉시 개입 필요 · HIGH",
        f"{high:,}",
        f"전체 {total:,}명 중 {high / total * 100:.1f}% · 중도탈락 확률 60% 이상",
        RISK_COLORS["HIGH"],
        unit="명",
        share=high / total if total else 0,
    )
    # 규모를 본 다음 할 일은 하나다 — 그 명단을 여는 것.
    if st.button("위험학생 목록 열기 →", width="stretch", type="primary", key="go_risk"):
        st.switch_page(PAGE_RISK)

with side_col:
    ui.kpi_row(
        [
            {"label": "전체 학생", "value": f"{total:,}", "unit": "명",
             "caption": "명단 전체",
             "accent": COLORS["primary"]},
            {"label": "MEDIUM", "value": f"{medium:,}", "unit": "명",
             "caption": "정기 모니터링", "accent": RISK_COLORS["MEDIUM"],
             "share": medium / total if total else 0},
            {"label": "예측 Dropout 비율", "value": f"{predicted_dropout / total * 100:.1f}" if total else "0",
             "unit": "%", "caption": f"{predicted_dropout:,}명 · 확률 50% 이상",
             "accent": CLASS_COLORS["Dropout"],
             "share": predicted_dropout / total if total else 0},
        ],
        columns=3,
    )

# ── Level 2 — 그 위험이 어떤 성격인가 ──────────────────────────────────────
ui.section("위험의 성격", "무엇을 준비해야 하고, 어디에 몰려 있는가.")

c1, c2 = st.columns(2, gap="large")

with c1, st.container(border=True):
    st.markdown(
        '<div class="card-title">위험등급 구성</div>'
        '<div class="card-sub">전체 명단이 어떤 비율로 나뉘는지.</div>',
        unsafe_allow_html=True,
    )
    ui.donut(risk_rows(frame), center_value=f"{total:,}", center_label="전체 학생")

with c2, st.container(border=True):
    st.markdown(
        '<div class="card-title">위험요인 카테고리</div>'
        '<div class="card-sub">학생마다 1순위 위험 하나로 집계 — 어느 부서로 보낼지의 기준.</div>',
        unsafe_allow_html=True,
    )
    # 왼쪽 도넛 카드와 높이를 맞춘다 — 나란히 놓인 카드가 서로 다른 키면 줄이 흔들린다.
    ui.column_chart(category_rows(frame), height=252)

ui.spacer(6)
c3, c4 = st.columns(2, gap="large")

with c3, st.container(border=True):
    st.markdown(
        '<div class="card-title">전공계열별 Dropout 분포</div>'
        '<div class="card-sub">막대 옆의 <b>율</b>은 그 계열 안에서의 비율.</div>',
        unsafe_allow_html=True,
    )
    ui.bar_chart(major_rows(frame), label_width=132,
                 hint="막대를 가리키면 나머지는 옅어집니다.")

with c4, st.container(border=True):
    st.markdown(
        '<div class="card-title">재정 · 학업 이슈 비중</div>'
        '<div class="card-sub">발동한 규칙 <b>건수</b> 기준 — 부서별 업무량.</div>',
        unsafe_allow_html=True,
    )
    workload = workload_rows(roster)
    ui.donut(workload, center_value=f"{sum(r['value'] for r in workload):,}",
             center_label="지원 연결 건")

# ── 피처 중요도 — 순위라 막대로 둔다 ───────────────────────────────────────
# 결과서가 없으면 카드 자체를 그리지 않는다. 빈 자리를 남겨 두면 미완성으로 읽힌다.
report = model_metrics.load()
if report is not None and report.feature_importance:
    ui.spacer(6)
    with st.container(border=True):
        st.markdown(
            '<div class="card-title">모델이 크게 본 변수</div>'
            '<div class="card-sub">순위라서 도넛이 아니라 막대로 그립니다.</div>',
            unsafe_allow_html=True,
        )
        ui.bar_chart(
            [{"label": name, "value": value, "color": COLORS["primary"],
              "display": f"{value:.3f}"}
             for name, value in report.feature_importance[:10]],
            label_width=190,
        )

ui.spacer(12)
if st.button("전체 학생 목록 보기", width="stretch", key="go_students"):
    st.switch_page(PAGE_STUDENTS)
