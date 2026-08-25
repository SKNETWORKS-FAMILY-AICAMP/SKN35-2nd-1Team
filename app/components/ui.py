"""
화면 공통 컴포넌트.

'학생 위험 예측' 화면과 '학생 목록'의 상세 패널은 완전히 같은 결과 화면을 쓴다.
같은 걸 두 번 그리지 않도록 여기서 한 번만 정의한다.
"""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from components.theme import (
    CATEGORY_COLORS,
    CLASS_COLORS,
    COLORS,
    FONT_STACK,
    PLOTLY_CONFIG,
    RISK_COLORS,
    RISK_SOFT,
)
from rules.recommendation_rules import RecommendationSet
from services.predictor import (
    EXPLANATION_DUMMY,
    RISK_LABELS_KO,
    RISK_THRESHOLDS,
    PredictionResult,
)
from services.prediction_service import PredictionService
from utils.feature_mapping import TARGET_CLASSES, TARGET_LABELS_KO, StudentInput

# ---------------------------------------------------------------------------
# 레이아웃 조각
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""<div class="page-head">
              <h1>{escape(title)}</h1>
              {f'<p>{escape(subtitle)}</p>' if subtitle else ''}
            </div>""",
        unsafe_allow_html=True,
    )


def section(title: str, desc: str = "") -> None:
    st.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
    if desc:
        st.markdown(f'<div class="section-desc">{escape(desc)}</div>', unsafe_allow_html=True)


def kpi_grid(items: list[tuple[str, str, str, str]]) -> None:
    """(라벨, 값, 캡션, 강조색) 목록을 카드 그리드로 그린다."""
    cards = "".join(
        f"""<div class="kpi-card" style="--accent:{accent}">
              <div class="kpi-label">{escape(label)}</div>
              <div class="kpi-value">{escape(value)}</div>
              <div class="kpi-caption">{escape(caption)}</div>
            </div>"""
        for label, value, caption, accent in items
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def risk_badge_html(level: str, large: bool = False) -> str:
    color = RISK_COLORS.get(level, COLORS["muted"])
    background = RISK_SOFT.get(level, COLORS["primary_soft"])
    label = RISK_LABELS_KO.get(level, level)
    size_class = " lg" if large else ""
    return (
        f'<span class="risk-badge{size_class}" style="background:{background};color:{color}">'
        f"{escape(level)} · 위험 {escape(label)}</span>"
    )


def banner(text_html: str, accent: str, background: str) -> None:
    st.markdown(
        f'<div class="banner" style="--accent:{accent};--bg:{background}">{text_html}</div>',
        unsafe_allow_html=True,
    )


def prototype_banner(service: PredictionService) -> None:
    """지금 화면의 숫자가 어디서 나왔는지 항상 밝힌다. 발표에서 오해를 막는 장치다."""
    if service.is_dummy:
        banner(
            "<b>프로토타입 모드</b> — 현재 화면의 예측값과 위험요인은 학습된 모델이 아니라 "
            "규칙 기반 <b>DummyPredictor</b> 가 만든 값입니다. 팀의 최종 모델이 "
            "<code>models/</code> 에 들어오면 화면 수정 없이 같은 자리에 실제 예측 결과가 표시됩니다.",
            COLORS["primary"],
            COLORS["primary_soft"],
        )
    else:
        banner(
            f"<b>실제 모델 연결됨</b> — {escape(service.model_label)}",
            RISK_COLORS["LOW"],
            RISK_SOFT["LOW"],
        )


# ---------------------------------------------------------------------------
# 예측 결과 표시
# ---------------------------------------------------------------------------

def dropout_gauge(result: PredictionResult, height: int = 220) -> go.Figure:
    """중도탈락 확률 게이지. 등급 경계(30% / 60%)를 배경 띠로 함께 보여준다."""
    medium, high = RISK_THRESHOLDS["MEDIUM"] * 100, RISK_THRESHOLDS["HIGH"] * 100
    color = RISK_COLORS.get(result.risk_level, COLORS["primary"])
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=result.dropout_percent,
            number={"suffix": "%", "font": {"size": 40, "color": color, "family": FONT_STACK}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickvals": [0, medium, high, 100],
                    "ticksuffix": "%",
                    "tickfont": {"size": 11, "color": COLORS["muted"], "family": FONT_STACK},
                },
                "bar": {"color": color, "thickness": 0.72},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, medium], "color": RISK_SOFT["LOW"]},
                    {"range": [medium, high], "color": RISK_SOFT["MEDIUM"]},
                    {"range": [high, 100], "color": RISK_SOFT["HIGH"]},
                ],
            },
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=40, r=40, t=12, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK),
    )
    return fig


def probability_bars(result: PredictionResult) -> None:
    """이진 확률 막대 (Dropout / Non-Dropout)."""
    rows = []
    for cls in TARGET_CLASSES:
        value = result.class_probabilities.get(cls, 0.0)
        color = CLASS_COLORS[cls]
        weight = "700" if cls == result.predicted_class else "600"
        rows.append(
            f"""<div class="prob-row">
                  <div class="prob-name" style="font-weight:{weight}">
                    {escape(TARGET_LABELS_KO[cls])}</div>
                  <div class="prob-track">
                    <div class="prob-fill" style="width:{value * 100:.1f}%;background:{color}"></div>
                  </div>
                  <div class="prob-value">{value * 100:.1f}%</div>
                </div>"""
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def factor_list(result: PredictionResult) -> None:
    """주요 위험요인 목록."""
    if not result.top_factors:
        st.markdown(
            '<div class="card-sub">기준선을 넘는 위험요인이 확인되지 않았습니다.</div>',
            unsafe_allow_html=True,
        )
        return

    blocks = []
    for rank, factor in enumerate(result.top_factors, start=1):
        color = CATEGORY_COLORS.get(factor.category, COLORS["primary"])
        width = max(factor.contribution * 100, 3)
        blocks.append(
            f"""<div class="factor">
                  <div class="factor-head">
                    <span class="factor-rank">{rank}</span>
                    <span class="factor-label">{escape(factor.label)}</span>
                    <span class="factor-chip" style="background:{color}1A;color:{color}">
                      {escape(factor.category_label)}</span>
                    <span style="margin-left:auto;font-size:.8rem;color:{COLORS['muted']};
                                 font-variant-numeric:tabular-nums">
                      {factor.contribution * 100:.0f}%</span>
                  </div>
                  <div class="factor-detail">{escape(factor.detail)}</div>
                  <div class="factor-track">
                    <div class="factor-fill" style="width:{width:.1f}%;background:{color}"></div>
                  </div>
                </div>"""
        )
    st.markdown("".join(blocks), unsafe_allow_html=True)

    if result.explanation_source == EXPLANATION_DUMMY:
        st.caption(
            "위 목록은 SHAP 분석 결과가 아니라 DummyPredictor 의 가중치를 그대로 풀어 쓴 "
            "프로토타입용 설명입니다. 백분율은 요인 간 상대 비중입니다."
        )
    else:
        st.caption(
            f"확률은 실제 모델 값이고, 위 설명의 출처는 {escape(result.explanation_source)} 입니다. "
            "SHAP explainer 가 연결되면 이 자리는 실제 기여도로 바뀝니다."
        )


def recommendation_block(recommendation: RecommendationSet) -> None:
    """규칙 기반 맞춤지원 추천."""
    if recommendation.is_priority_case:
        banner(
            f"<b>집중관리 우선 대상</b> — {escape(recommendation.priority_reason)}",
            RISK_COLORS["HIGH"],
            RISK_SOFT["HIGH"],
        )
        st.write("")

    if not recommendation.matched:
        st.markdown(
            '<div class="card"><div class="card-title">해당하는 지원 규칙 없음</div>'
            '<div class="card-sub">현재 입력값에서는 발동한 지원 규칙이 없습니다. '
            "정기 모니터링 대상으로만 유지합니다.</div></div>",
            unsafe_allow_html=True,
        )
    else:
        for matched in recommendation.matched:
            rule = matched.rule
            color = CATEGORY_COLORS.get(rule.category, COLORS["primary"])
            programs = "".join(
                f"""<div class="program">▸ {escape(p.name)}
                      <span class="owner">{escape(p.owner)}</span>
                      <span class="action">{escape(p.action)}</span></div>"""
                for p in rule.programs
            )
            feature = (
                f'<span class="rule-id">근거 피처 · {escape(rule.feature)}</span>'
                if rule.feature
                else ""
            )
            st.markdown(
                f"""<div class="rule-card" style="--accent:{color}">
                      <div class="rule-head">
                        <span class="factor-chip" style="background:{color}1A;color:{color}">
                          {escape(rule.category_label)}</span>
                        <span class="rule-title">{escape(rule.title)}</span>
                        <span class="rule-id">RULE {escape(rule.id)}</span>
                      </div>
                      <div class="rule-reason">{escape(matched.reason)}</div>
                      {programs}
                      <div style="margin-top:.45rem">{feature}</div>
                    </div>""",
                unsafe_allow_html=True,
            )

    st.markdown(
        f'<div class="disclaimer">{escape(recommendation.disclaimer)}</div>',
        unsafe_allow_html=True,
    )


def student_summary(student: StudentInput) -> None:
    """상세 화면 상단의 학생 요약 줄."""
    items = [
        ("학생 ID", student.student_id),
        ("전공 계열", student.major_field),
        ("입학 시 나이", f"{student.age_at_enrollment}세"),
        ("수업 시간대", "주간" if student.attendance == 1 else "야간"),
        ("2학기 이수율", f"{student.sem2_approval_rate:.0%}"),
        ("평균 성적", f"{student.average_grade:.1f} / 20"),
        ("성적 변화", f"{student.grade_change:+.1f}"),
        ("재정위험점수", f"{student.financial_risk_score} / 3"),
    ]
    cells = "".join(
        f"""<div><div class="kpi-label">{escape(label)}</div>
              <div style="font-size:.95rem;font-weight:600;color:{COLORS['ink']}">
                {escape(value)}</div></div>"""
        for label, value in items
    )
    st.markdown(
        f'<div class="card"><div style="display:grid;gap:.9rem;'
        f'grid-template-columns:repeat(auto-fit,minmax(120px,1fr))">{cells}</div></div>',
        unsafe_allow_html=True,
    )


def result_panel(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
    *,
    show_summary: bool = True,
) -> None:
    """예측 결과 전체 패널. 예측 화면과 목록 상세가 공유한다."""
    if show_summary:
        student_summary(student)
        st.write("")

    left, right = st.columns([1, 1.25], gap="large")

    with left:
        st.markdown(
            '<div class="card-title">중도탈락 위험도</div>'
            '<div class="card-sub">위험등급 경계: 30% 미만 LOW · 60% 이상 HIGH</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            dropout_gauge(result),
            width="stretch",
            config=PLOTLY_CONFIG,
            key=f"gauge_{student.student_id}_{result.dropout_percent}",
        )
        st.markdown(
            f'<div style="text-align:center;margin-top:-.6rem">'
            f"{risk_badge_html(result.risk_level, large=True)}</div>",
            unsafe_allow_html=True,
        )

    with right:
        predicted_ko = TARGET_LABELS_KO.get(result.predicted_class, result.predicted_class)
        st.markdown(
            f'<div class="card-title">예측 클래스 · {escape(predicted_ko)} '
            f'<span class="rule-id">({escape(result.predicted_class)})</span></div>'
            '<div class="card-sub">팀 전처리 정의 기준 이진 분류 (1=Dropout / 0=Non-Dropout)</div>',
            unsafe_allow_html=True,
        )
        st.write("")
        probability_bars(result)
        st.write("")
        st.markdown('<div class="card-title">주요 위험요인</div>', unsafe_allow_html=True)
        factor_list(result)

    section("맞춤 지원 추천", "규칙 엔진(rules/recommendation_rules.py)이 판정한 결과입니다.")
    recommendation_block(recommendation)
