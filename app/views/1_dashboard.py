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
from components.state import PAGE_RISK, cached_roster, start_page
from components.theme import CATEGORY_COLORS, CLASS_COLORS, COLORS, RISK_COLORS
from services import model_metrics
from services.prediction_service import get_service
from services.predictor import RISK_CATEGORIES, RISK_LABELS_KO

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
    "중도탈락 위험 대시보드",
    "이번 학기 명단의 중도탈락 위험 예측 현황입니다.",
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

# ── 지금 규모 — 넷을 한 줄로 ───────────────────────────────────────────────
ui.kpi_row(
    [
        {"label": "전체 재학생", "value": f"{total:,}", "unit": "명",
         "caption": "명단 전체", "accent": COLORS["primary"], "icon": "groups"},
        {"label": "HIGH 위험", "value": f"{high:,}", "unit": "명",
         "caption": "즉시 개입 필요", "accent": RISK_COLORS["HIGH"], "icon": "crisis_alert"},
        {"label": "MEDIUM 위험", "value": f"{medium:,}", "unit": "명",
         "caption": "예방 지원 권장", "accent": RISK_COLORS["MEDIUM"], "icon": "target"},
        {"label": "예측 Dropout 비율",
         "value": f"{predicted_dropout / total * 100:.1f}" if total else "0", "unit": "%",
         "caption": f"{predicted_dropout:,}명 · 확률 50% 이상",
         "accent": CLASS_COLORS["Dropout"], "icon": "percent"},
    ],
    columns=4,
)

# ── 지금 움직여야 하는 이유 하나 ───────────────────────────────────────────
ui.spacer(12)
# 줄을 칸으로 나누면 경보가 화면 폭을 다 못 쓴다. 줄은 폭 전체로 두고 버튼을 그 **안에**
# 겹쳐 놓는다 (theme.py 가 이 컨테이너 안의 버튼만 절대 배치한다).
with st.container(key="dash_alert"):
    ui.alert_bar(
        f"즉시 개입 필요 학생 {high:,}명",
        "HIGH 위험 학생은 이번 주 안에 상담 배정을 권장합니다.",
    )
    if st.button("위험학생목록 보기", type="primary", key="go_risk",
                 icon=":material/list_alt:"):
        st.switch_page(PAGE_RISK)

# ── Level 2 — 그 위험이 어떤 성격인가 ──────────────────────────────────────
ui.section("위험의 성격", "무엇을 준비해야 하고, 어디에 몰려 있는가.")

c1, c2 = st.columns(2, gap="large")

with c1, st.container(border=True, key="dash_c1"):
    # 이 자리는 Feature Importance 다. 출처가 둘이고 **어느 쪽인지 반드시 밝힌다.**
    #   1) 팀 학습 결과서가 있으면 → 학습된 모델의 중요도
    #   2) 없으면 → 지금 화면의 확률을 만든 규칙식이 이 명단에서 실제로 쓴 비중
    # 2번은 명단 885명에 대해 항의 절댓값을 평균 낸 실측값이라 지어낸 수치가 아니다.
    # 다만 **학습된 모델의 중요도가 아니므로** 부제에서 그 사실을 그대로 적는다.
    report = model_metrics.load()
    model_importance = report.feature_importance if report is not None else []

    if model_importance:
        rows = [{"label": name, "value": value, "color": COLORS["primary"],
                 "display": f"{value:.3f}"}
                for name, value in model_importance[:8]]
        sub_text = "학습 결과서의 모델 중요도 — 순위라서 막대로 그립니다."
    else:
        profile = service.contribution_profile(row.student for row in roster.rows)
        rows = [{"label": name, "value": share, "color": COLORS["primary"],
                 "display": f"{share:.1%}"}
                for name, share in profile[:8]]
        sub_text = ("현재 예측기(규칙 기반)가 이 명단에서 실제로 반영한 비중입니다. "
                    "학습된 모델의 중요도가 아니며, 학습 결과서가 들어오면 그 값으로 바뀝니다.")

    st.markdown(
        '<div class="card-title">Feature Importance</div>'
        f'<div class="card-sub">{sub_text}</div>',
        unsafe_allow_html=True,
    )
    if rows:
        ui.bar_chart(rows, label_width=150)
    else:
        ui.donut(risk_rows(frame), center_value=f"{total:,}", center_label="전체 학생")

with c2, st.container(border=True, key="dash_c2"):
    st.markdown(
        '<div class="card-title">위험요인 카테고리</div>'
        '<div class="card-sub">학생마다 1순위 위험 하나로 집계 — 어느 부서로 보낼지의 기준.</div>',
        unsafe_allow_html=True,
    )
    # 왼쪽 도넛 카드와 높이를 맞춘다 — 나란히 놓인 카드가 서로 다른 키면 줄이 흔들린다.
    ui.column_chart(category_rows(frame), height=252)

ui.spacer(6)
c3, c4 = st.columns(2, gap="large")

with c3, st.container(border=True, key="dash_c3"):
    st.markdown(
        '<div class="card-title">전공계열별 Dropout 분포</div>'
        '<div class="card-sub">막대 옆의 <b>율</b>은 그 계열 안에서의 비율.</div>',
        unsafe_allow_html=True,
    )
    ui.bar_chart(major_rows(frame), label_width=132,
                 hint="막대를 가리키면 나머지는 옅어집니다.")

with c4, st.container(border=True, key="dash_c4"):
    st.markdown(
        '<div class="card-title">재정 · 학업 이슈 비중</div>'
        '<div class="card-sub">발동한 규칙 <b>건수</b> 기준 — 부서별 업무량.</div>',
        unsafe_allow_html=True,
    )
    workload = workload_rows(roster)
    ui.donut(workload, center_value=f"{sum(r['value'] for r in workload):,}",
             center_label="지원 연결 건")
