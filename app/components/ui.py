"""
화면 공통 컴포넌트 — 디자인 시스템(`theme.py`)의 토큰만 써서 조립한 조각들.

화면 파일은 여기 있는 함수만 부른다. `st.markdown` 으로 HTML 을 직접 쓰지 않는다.
같은 의미(위험등급·카테고리·상태)는 어느 화면에서든 **같은 모양**으로 나와야 하기 때문이다.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from components.theme import (
    CATEGORY_COLORS,
    CLASS_COLORS,
    COLORS,
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


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 레이아웃
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = "", meta: str = "") -> None:
    """화면 상단. 오른쪽 `meta` 는 그 화면의 데이터 출처처럼 짧은 사실만 넣는다."""
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    right = f'<div class="meta">{meta}</div>' if meta else ""
    # 한 줄로 만든다 — HTML 문자열 안에 빈 줄이 있으면 마크다운이 블록을 끊어
    # 닫는 태그가 그대로 글자로 새어 나온다 (실제로 겪었다).
    _html(
        f'<div class="page-head"><div class="titles">'
        f"<h1>{escape(title)}</h1>{sub}</div>{right}</div>"
    )


def section(title: str, desc: str = "") -> None:
    tail = f'<div class="sec-desc">{escape(desc)}</div>' if desc else ""
    _html(
        f'<div class="sec"><div class="sec-row">'
        f'<span class="sec-title">{escape(title)}</span>'
        f'<span class="sec-rule"></span></div>{tail}</div>'
    )


def spacer(size: int = 8) -> None:
    _html(f'<div style="height:{size}px"></div>')


# ---------------------------------------------------------------------------
# 상태 표시 — 색만으로 구분하지 않는다 (항상 글자를 함께 쓴다)
# ---------------------------------------------------------------------------

def risk_pill_html(level: str, *, large: bool = False, with_label: bool = True) -> str:
    text = f"{level} · {RISK_LABELS_KO.get(level, level)}" if with_label else level
    return (
        f'<span class="pill pill-{escape(level)}{" lg" if large else ""}">'
        f'<span class="dot"></span>{escape(text)}</span>'
    )


def focus_pill_html(text: str = "집중관리") -> str:
    return f'<span class="pill pill-focus"><span class="dot"></span>{escape(text)}</span>'


def neutral_pill_html(text: str) -> str:
    return f'<span class="pill pill-neutral">{escape(text)}</span>'


def banner(
    mark: str, body_html: str, *, foreground: str, background: str, border: str
) -> None:
    _html(
        f'<div class="banner" style="--fg:{foreground};--bg:{background};--bd:{border}">'
        f'<span class="mark">{escape(mark)}</span><div>{body_html}</div></div>'
    )


def prototype_banner(service: PredictionService, *, source_note: str = "") -> None:
    """이 화면의 숫자가 어디서 나왔는지 항상 밝힌다. 발표에서 오해를 막는 장치다."""
    extra = f" {escape(source_note)}" if source_note else ""
    if service.is_dummy:
        banner(
            "Prototype Mode",
            "학습된 모델이 아직 연결되지 않았습니다. 화면의 확률과 위험요인은 규칙 기반 "
            "<b>DummyPredictor</b> 가 만든 값이며 <b>성능 수치를 주장하지 않습니다</b>. "
            f"팀 최종 모델이 <code>models/</code> 에 들어오면 화면 수정 없이 대체됩니다.{extra}",
            foreground=COLORS["primary"],
            background=COLORS["primary_soft"],
            border=COLORS["primary_line"],
        )
    else:
        banner(
            "Live Model",
            f"<b>{escape(service.model_label)}</b> 이 연결되어 실제 예측을 표시하고 있습니다.{extra}",
            foreground=RISK_COLORS["LOW"],
            background=RISK_SOFT["LOW"],
            border="#C5E3D7",
        )


def empty_state(title: str, desc: str = "") -> None:
    _html(
        f'<div class="empty"><div class="t">{escape(title)}</div>'
        f'{f"<div class=\'d\'>{escape(desc)}</div>" if desc else ""}</div>'
    )


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------

def kpi_hero(label: str, value: str, caption: str, accent: str, *, unit: str = "",
             share: float | None = None) -> None:
    """화면에서 가장 먼저 읽혀야 하는 지표 하나. 남발하면 계층이 사라진다."""
    bar = (
        f'<div class="kpi-bar"><span style="width:{max(min(share, 1.0), 0.0) * 100:.1f}%"></span></div>'
        if share is not None else ""
    )
    _html(
        f"""<div class="kpi-hero" style="--accent:{accent}">
              <div class="lab">{escape(label)}</div>
              <div class="val">{escape(value)}{f'<span class="unit">{escape(unit)}</span>' if unit else ''}</div>
              <div class="cap">{escape(caption)}</div>{bar}
            </div>"""
    )


def kpi_row(items: list[dict], columns: int = 4) -> None:
    """보조 지표. `{label, value, caption, accent, unit?, share?}` 목록."""
    cards = []
    for it in items:
        share = it.get("share")
        bar = (
            f'<div class="kpi-bar"><span style="width:{max(min(share, 1.0), 0.0) * 100:.1f}%"></span></div>'
            if share is not None else ""
        )
        unit = it.get("unit", "")
        cards.append(
            f"""<div class="kpi" style="--accent:{it.get('accent', COLORS['primary'])}">
                  <div class="lab">{escape(it['label'])}</div>
                  <div class="val">{escape(it['value'])}
                    {f'<span class="unit">{escape(unit)}</span>' if unit else ''}</div>
                  <div class="cap">{escape(it.get('caption', ''))}</div>{bar}
                </div>"""
        )
    _html(
        f'<div class="kpi-row" style="grid-template-columns:repeat({columns},1fr)">'
        f'{"".join(cards)}</div>'
    )


# ---------------------------------------------------------------------------
# 위험 미터 — 속도계 대신 "구간이 보이는" 가로 미터
# ---------------------------------------------------------------------------

def risk_meter(result: PredictionResult) -> None:
    """중도탈락 확률 + 등급 경계.

    속도계(gauge)를 쓰지 않는 이유: 바늘 각도는 값을 읽기 어렵고 자동차 계기판 인상을 준다.
    담당자가 알아야 하는 것은 **"이 학생이 어느 구간에 있는가"** 이므로 구간을 그대로 그린다.
    """
    medium = RISK_THRESHOLDS["MEDIUM"] * 100
    high = RISK_THRESHOLDS["HIGH"] * 100
    value = result.dropout_percent
    color = RISK_COLORS[result.risk_level]

    _html(
        f"""<div style="--accent:{color}">
          <div class="meter-val">
            <span class="n ds-num">{value:.1f}<span class="p">%</span></span>
            {risk_pill_html(result.risk_level, large=True)}
          </div>
          <div class="meter-cap">중도탈락 확률 · 등급 경계 {medium:.0f}% / {high:.0f}%</div>
          <div class="meter">
            <div class="track">
              <div class="zone" style="width:{medium}%;background:{RISK_COLORS['LOW']}"></div>
              <div class="zone" style="width:{high - medium}%;background:{RISK_COLORS['MEDIUM']}"></div>
              <div class="zone" style="width:{100 - high}%;background:{RISK_COLORS['HIGH']}"></div>
              <div class="mark" style="left:calc({value}% - 1.5px)"></div>
            </div>
            <div class="zones">
              <span style="color:{RISK_COLORS['LOW']}">LOW</span>
              <span style="color:{RISK_COLORS['MEDIUM']}">MEDIUM</span>
              <span style="color:{RISK_COLORS['HIGH']}">HIGH</span>
            </div>
            <div class="ticks"><span>0%</span><span>{medium:.0f}%</span>
              <span>{high:.0f}%</span><span>100%</span></div>
          </div>
        </div>"""
    )


def probability_split(result: PredictionResult) -> None:
    """이진 확률을 한 줄 막대로. 두 클래스뿐이라 파이차트를 쓸 이유가 없다."""
    p = result.dropout_probability * 100
    _html(
        f"""<div style="margin-top:12px">
          <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;background:#EDF1F6">
            <div style="width:{p:.1f}%;background:{CLASS_COLORS['Dropout']}"></div>
            <div style="width:{100 - p:.1f}%;background:{CLASS_COLORS['Non-Dropout']}"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:6px;
                      font-size:.72rem;font-weight:700;letter-spacing:.04em">
            <span style="color:{CLASS_COLORS['Dropout']}">
              {escape(TARGET_LABELS_KO['Dropout'])} {p:.1f}%</span>
            <span style="color:{CLASS_COLORS['Non-Dropout']}">
              {escape(TARGET_LABELS_KO['Non-Dropout'])} {100 - p:.1f}%</span>
          </div>
        </div>"""
    )


# ---------------------------------------------------------------------------
# 위험요인
# ---------------------------------------------------------------------------

def factor_list(result: PredictionResult) -> None:
    if not result.top_factors:
        _html('<div class="ds-sub">기준선을 넘는 위험요인이 확인되지 않았습니다.</div>')
        return

    blocks = []
    for factor in result.top_factors:
        color = CATEGORY_COLORS.get(factor.category, COLORS["primary"])
        width = max(factor.contribution * 100, 3)
        blocks.append(
            f"""<div class="factor">
                  <div class="factor-top">
                    <span class="factor-name">{escape(factor.label)}</span>
                    <span class="pill pill-neutral" style="color:{color};border-color:{color}33">
                      {escape(factor.category_label)}</span>
                    <span class="factor-pct ds-num">{factor.contribution * 100:.0f}%</span>
                  </div>
                  <div class="factor-detail">{escape(factor.detail)}</div>
                  <div class="factor-track">
                    <div class="factor-fill" style="width:{width:.1f}%;background:{color}"></div>
                  </div>
                </div>"""
        )
    _html("".join(blocks))

    if result.explanation_source == EXPLANATION_DUMMY:
        st.caption(
            "SHAP 분석 결과가 아니라 DummyPredictor 의 가중치를 그대로 풀어 쓴 프로토타입 설명입니다. "
            "백분율은 요인 간 상대 비중이며 모델 기여도가 아닙니다."
        )
    else:
        st.caption(
            f"확률은 실제 모델 값이고 설명의 출처는 {escape(result.explanation_source)} 입니다. "
            "SHAP explainer 가 연결되면 이 자리는 실제 기여도로 바뀝니다."
        )


# ---------------------------------------------------------------------------
# 지원 추천 — 이 프로젝트의 차별점이라 카드로 세워 보여준다
# ---------------------------------------------------------------------------

_PRIORITY_LABEL = {1: "즉시", 2: "이번 학기", 3: "모니터링"}


def support_cards(recommendation: RecommendationSet, *, columns: int = 3) -> None:
    if recommendation.is_priority_case:
        banner(
            "Priority",
            f"<b>집중관리 우선 대상</b> — {escape(recommendation.priority_reason)}",
            foreground=RISK_COLORS["HIGH"],
            background=RISK_SOFT["HIGH"],
            border="#F0CBC6",
        )
        spacer(12)

    if not recommendation.matched:
        empty_state(
            "발동한 지원 규칙 없음",
            "현재 입력값에서는 조건을 넘는 규칙이 없습니다. 정기 모니터링 대상으로만 유지합니다.",
        )
        _html(f'<div class="ds-caption" style="margin-top:12px">{escape(recommendation.disclaimer)}</div>')
        return

    matched = recommendation.matched
    for start in range(0, len(matched), columns):
        chunk = matched[start : start + columns]
        cols = st.columns(columns, gap="small")
        for col, m in zip(cols, chunk):
            rule = m.rule
            color = CATEGORY_COLORS.get(rule.category, COLORS["primary"])
            programs = "".join(
                f'<div class="act-prog">{escape(p.name)}'
                f'<span class="owner">{escape(p.owner)}</span>'
                f'<span class="todo">{escape(p.action)}</span></div>'
                for p in rule.programs
            )
            with col:
                _html(
                    f"""<div class="act" style="--accent:{color}">
                          <div class="act-head">
                            <span class="pill pill-neutral"
                                  style="color:{color};border-color:{color}33">
                              {escape(rule.category_label)}</span>
                            <span class="pill pill-neutral">
                              {escape(_PRIORITY_LABEL.get(rule.priority, '검토'))}</span>
                          </div>
                          <div class="act-title">{escape(rule.title)}</div>
                          <div class="act-reason">{escape(m.reason)}</div>
                          {programs}
                          <div class="act-feat">RULE {escape(rule.id)} · {escape(rule.feature)}</div>
                        </div>"""
                )
        if start + columns < len(matched):
            spacer(10)

    _html(f'<div class="ds-caption" style="margin-top:16px">{escape(recommendation.disclaimer)}</div>')


# ---------------------------------------------------------------------------
# 학생 요약 / 결과 패널
# ---------------------------------------------------------------------------

def student_summary(student: StudentInput) -> None:
    items = [
        ("학생 ID", student.student_id),
        ("전공 계열", student.major_field),
        ("입학 전형", student.admission_pathway),
        ("입학 시 나이", f"{student.age_at_enrollment}세"),
        ("수업 시간대", "주간" if student.attendance == 1 else "야간"),
        ("2학기 이수율", f"{student.sem2_approval_rate:.0%}"),
        ("평균 성적", f"{student.average_grade:.1f} / 20"),
        ("재정위험", f"{student.financial_risk_score} / 3"),
    ]
    cells = "".join(
        f'<div><div class="lab" style="font-size:.72rem;font-weight:700;letter-spacing:.09em;'
        f'text-transform:uppercase;color:{COLORS["muted"]}">{escape(k)}</div>'
        f'<div style="font-size:.92rem;font-weight:600;color:{COLORS["ink"]};margin-top:4px">'
        f"{escape(v)}</div></div>"
        for k, v in items
    )
    _html(
        '<div class="card"><div style="display:grid;gap:16px;'
        f'grid-template-columns:repeat(auto-fit,minmax(110px,1fr))">{cells}</div></div>'
    )


def result_panel(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
    *,
    show_summary: bool = True,
) -> None:
    """예측 결과 전체. 예측 화면과 목록 상세가 공유한다.

    왼쪽 **얼마나 위험한가** → 가운데 **왜 위험한가** → 아래 **그래서 무엇을 할 것인가**.
    이 순서가 이 제품이 하는 말 전부다.
    """
    if show_summary:
        student_summary(student)
        spacer(12)

    left, right = st.columns([1, 1.35], gap="large")

    # st.markdown 은 호출마다 독립된 블록이라 여는 태그와 닫는 태그를 따로 내보내면
    # 감싸지지 않는다. 위젯을 감싸야 할 때는 Streamlit 컨테이너를 쓰고 CSS 로 카드를 입힌다.
    with left, st.container(border=True):
        risk_meter(result)
        probability_split(result)

    with right, st.container(border=True):
        _html(
            '<div class="card-title">왜 이 학생이 위험한가</div>'
            '<div class="card-sub">기여도가 큰 순서입니다.</div>'
        )
        factor_list(result)

    section("무엇을 할 것인가", "규칙 엔진(rules/recommendation_rules.py)이 판정한 지원 연결입니다.")
    support_cards(recommendation)


# ---------------------------------------------------------------------------
# 우선 확인 명단 — 기본 dataframe 대신 직접 그린다
# ---------------------------------------------------------------------------

def priority_table(rows: list[dict]) -> None:
    """`{rank, sid, major, probability, level, category, focus}` 목록.

    `st.dataframe` 은 정렬·스크롤이 필요할 때 쓴다. 여기는 '먼저 볼 8명' 이라
    **읽히는 것**이 목적이므로 직접 그려서 위험 막대와 배지를 함께 보여준다.
    """
    if not rows:
        empty_state("표시할 학생이 없습니다.")
        return

    body = []
    for r in rows:
        color = RISK_COLORS[r["level"]]
        pct = r["probability"] * 100
        body.append(
            f"""<tr>
                  <td class="rank">{r['rank']:02d}</td>
                  <td class="sid">{escape(r['sid'])}</td>
                  <td>{escape(r['major'])}</td>
                  <td>
                    <div class="riskbar">
                      <span class="track"><span class="fill"
                        style="width:{pct:.0f}%;background:{color}"></span></span>
                      <span class="pct" style="color:{color}">{pct:.0f}%</span>
                    </div>
                  </td>
                  <td>{risk_pill_html(r['level'], with_label=False)}</td>
                  <td>{escape(r['category'])}</td>
                  <td>{focus_pill_html() if r['focus'] else ''}</td>
                </tr>"""
        )
    _html(
        '<div class="card" style="padding:16px 8px">'
        '<table class="dt"><thead><tr>'
        "<th></th><th>학생</th><th>전공 계열</th><th>중도탈락 확률</th>"
        "<th>등급</th><th>주요 위험</th><th></th>"
        f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    )


_KEEP = TARGET_CLASSES  # 화면이 클래스 순서를 이 모듈 경유로도 얻을 수 있게 남긴다.
