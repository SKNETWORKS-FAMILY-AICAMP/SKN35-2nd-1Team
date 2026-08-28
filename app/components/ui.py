"""
화면 공통 컴포넌트 — 디자인 시스템(`theme.py`)의 토큰만 써서 조립한 조각들.

화면 파일은 여기 있는 함수만 부른다. `st.markdown` 으로 HTML 을 직접 쓰지 않는다.
같은 의미(위험등급·카테고리·상태)는 어느 화면에서든 **같은 모양**으로 나와야 하기 때문이다.
"""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from components.theme import (
    CATEGORY_COLORS,
    CLASS_COLORS,
    COLORS,
    PLOTLY_CONFIG,
    RISK_COLORS,
    RISK_SOFT,
    style_figure,
)
from rules.recommendation_rules import (
    PRIORITY_LABELS,
    Evidence,
    RecommendationSet,
    Rule,
    evidence_of,
)
from services import case_sheet
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
# 막대 차트 — Plotly 대신 직접 그린다
# ---------------------------------------------------------------------------

def bar_chart(
    rows: list[dict],
    *,
    label_width: int = 118,
    hint: str = "막대를 가리키면 나머지는 옅어집니다.",
) -> None:
    """가로 막대 목록. `{label, value, display, color}` 를 큰 값부터 넣는다.

    Plotly 를 쓰지 않는 이유: **가리킨 막대만 또렷하게** 만들려면 나머지를 눌러야 하는데,
    Plotly 막대에서는 JS 콜백 없이 못 한다. 직접 그리면 CSS 몇 줄이고,
    렌더 비용도 차트 하나만큼 줄어든다. 좌표가 필요한 그래프(산점도)만 Plotly 에 남긴다.
    """
    if not rows:
        empty_state("표시할 값이 없습니다.")
        return

    top = max((r["value"] for r in rows), default=0) or 1
    body = []
    for r in rows:
        width = max(r["value"] / top * 100, 1.5)
        body.append(
            f'<div class="row"><span class="lab">{escape(str(r["label"]))}</span>'
            f'<span class="track"><span class="fill" '
            f'style="width:{width:.1f}%;background:{r.get("color", COLORS["primary"])}"></span></span>'
            f'<span class="val">{escape(str(r["display"]))}</span></div>'
        )
    _html(
        f'<div class="bars" style="--labelw:{label_width}px">{"".join(body)}</div>'
        f'{f"<div class='bars-hint'>{escape(hint)}</div>" if hint else ""}'
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
# 도넛 — 전체 중 비중을 보여줄 때만 쓴다
# ---------------------------------------------------------------------------

def donut(
    rows: list[dict],
    *,
    center_value: str,
    center_label: str,
    key: str,
    height: int = 250,
) -> None:
    """`{label, value, color, display?}` 를 도넛 하나 + 아래 범례로 그린다.

    **비율(부분의 합이 전체)일 때만 쓴다.** 순위나 비율(rate)을 도넛에 넣으면
    조각 크기가 아무 뜻도 없게 된다 — 그런 값은 `bar_chart()` 가 맞다.

    범례를 직접 그리는 이유: Plotly 범례는 이 높이에서 눌려 잘린다(우선순위 표에서
    이미 겪었다). 직접 그리면 값·비율을 같이 적을 수 있어 읽기도 낫다.
    """
    rows = [r for r in rows if r.get("value", 0) > 0]
    if not rows:
        empty_state("표시할 값이 없습니다.")
        return

    total = sum(r["value"] for r in rows)
    figure = go.Figure(
        go.Pie(
            labels=[str(r["label"]) for r in rows],
            values=[r["value"] for r in rows],
            hole=0.68,
            sort=False,
            direction="clockwise",
            textinfo="none",
            marker=dict(
                colors=[r.get("color", COLORS["primary"]) for r in rows],
                line=dict(color=COLORS["surface"], width=2),
            ),
            hovertemplate="%{label}<br>%{value:,}명 · %{percent}<extra></extra>",
        )
    )
    figure.add_annotation(
        text=(f"<b style='font-size:1.6rem'>{escape(center_value)}</b><br>"
              f"<span style='font-size:.72rem'>{escape(center_label)}</span>"),
        showarrow=False, font=dict(color=COLORS["ink"]),
    )
    st.plotly_chart(
        style_figure(figure, height=height, show_legend=False, grid="none"),
        width="stretch", config=PLOTLY_CONFIG, key=key,
    )

    items = "".join(
        f'<div class="dn-item"><span class="sw" style="background:{r.get("color", COLORS["primary"])}"></span>'
        f'<span class="lb">{escape(str(r["label"]))}</span>'
        f'<span class="vl ds-num">{escape(str(r.get("display", f"{r["value"]:,}명")))}</span>'
        f'<span class="pc ds-num">{r["value"] / total * 100:.0f}%</span></div>'
        for r in rows
    )
    _html(f'<div class="dn-legend">{items}</div>')


# ---------------------------------------------------------------------------
# 상담 진행 상태
# ---------------------------------------------------------------------------

#: 단계별 색. 진행될수록 진해진다 — 색만으로 구분하지 않게 기호를 항상 함께 쓴다.
FOLLOWUP_COLORS: dict[str, str] = {
    "미착수": COLORS["faint"],
    "연락함": COLORS["medium"] if "medium" in COLORS else RISK_COLORS["MEDIUM"],
    "상담완료": COLORS["primary"],
    "종결": RISK_COLORS["LOW"],
}


def followup_pill_html(status: str) -> str:
    from services import followup

    color = FOLLOWUP_COLORS.get(status, COLORS["faint"])
    mark = followup.MARKS.get(status, "○")
    return (
        f'<span class="pill pill-neutral" style="color:{color};border-color:{color}33">'
        f"{escape(mark)} {escape(status)}</span>"
    )

# ---------------------------------------------------------------------------
# 위험요인
# ---------------------------------------------------------------------------

def _rule_ids_by_factor(recommendation: RecommendationSet | None) -> dict[str, list[str]]:
    """모델 위험요인 key → 그 요인에 대응해 **발동한** 규칙 ID 목록.

    `Rule.factor_keys` 가 `dummy_predictor._Term.key` 와 같은 이름을 쓰기 때문에
    두 블록(왜 위험한가 / 무엇을 할 것인가)을 이 사전 하나로 이을 수 있다.
    """
    mapping: dict[str, list[str]] = {}
    if recommendation is None:
        return mapping
    for m in recommendation.matched:
        for key in m.rule.factor_keys:
            mapping.setdefault(key, []).append(m.rule.id)
    return mapping


def factor_list(result: PredictionResult,
                recommendation: RecommendationSet | None = None) -> None:
    if not result.top_factors:
        _html('<div class="ds-sub">기준선을 넘는 위험요인이 확인되지 않았습니다.</div>')
        return

    linked = _rule_ids_by_factor(recommendation)

    blocks = []
    for factor in result.top_factors:
        color = CATEGORY_COLORS.get(factor.category, COLORS["primary"])
        width = max(factor.contribution * 100, 3)
        ids = linked.get(factor.key, [])
        rule_link = (
            f'<span class="factor-rule">→ RULE {escape(" · ".join(ids))}</span>' if ids else ""
        )
        blocks.append(
            f"""<div class="factor">
                  <div class="factor-top">
                    <span class="factor-name">{escape(factor.label)}</span>
                    <span class="pill pill-neutral" style="color:{color};border-color:{color}33">
                      {escape(factor.category_label)}</span>
                    <span class="factor-pct ds-num">{factor.contribution * 100:.0f}%</span>
                  </div>
                  <div class="factor-detail">{escape(factor.detail)}{rule_link}</div>
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
# 근거 미터 — "기준을 넘었다" 가 아니라 "얼마나 넘었는가"
# ---------------------------------------------------------------------------

def evidence_bar_html(evidence: Evidence, accent: str) -> str:
    """규칙 임계값 대비 학생 값의 위치. 위험 구간을 띠로 칠하고 두 표식을 세운다.

    막대를 왼쪽부터 채우지 않는 이유: 규칙에 따라 **큰 쪽이 위험한 것**(하락폭·재정위험)과
    **작은 쪽이 위험한 것**(이수율·성적)이 섞여 있어서, 채움 길이는 위험의 크기를
    뜻하지 못한다. 위험한 쪽을 띠로 칠하면 방향과 무관하게 같은 그림으로 읽힌다.
    """
    thr = evidence.ratio(evidence.threshold) * 100
    val = evidence.ratio(evidence.value) * 100

    if evidence.worse == "below":
        danger = f"left:0;width:{thr:.1f}%"
        foot_note = f"{evidence.threshold_text} 미만이면 발동"
    else:
        danger = f"left:{thr:.1f}%;width:{100 - thr:.1f}%"
        foot_note = f"{evidence.threshold_text} 이상이면 발동"

    return (
        f'<div class="ev" style="--accent:{accent}">'
        f'<div class="ev-top"><span class="ev-lab">{escape(evidence.label)}</span>'
        f'<span class="ev-val ds-num">{escape(evidence.value_text)}</span>'
        f'<span class="ev-thr ds-num">기준 {escape(evidence.threshold_text)}</span></div>'
        f'<div class="ev-track">'
        f'<span class="ev-danger" style="{danger}"></span>'
        f'<span class="ev-thrmark" style="left:calc({thr:.1f}% - 1px)"></span>'
        f'<span class="ev-mark" style="left:calc({val:.1f}% - 1.5px)"></span>'
        f"</div>"
        f'<div class="ev-foot"><span>{evidence.minimum:g}{escape(evidence.unit)}</span>'
        f"<span>{escape(foot_note)}</span>"
        f'<span>{evidence.maximum:g}{escape(evidence.unit)}</span></div></div>'
    )


# ---------------------------------------------------------------------------
# 규칙 판정 트레이스 — 안 나온 추천도 설명한다
# ---------------------------------------------------------------------------

def rule_trace(recommendation: RecommendationSet, student: StudentInput) -> None:
    """규칙 12개 전부의 판정. 발동한 것과 발동하지 않은 것을 한 표에 놓는다.

    **"왜 이 추천은 안 나왔나" 에 답할 수 없으면 추천의 근거도 절반만 설명한 것이다.**
    미발동 규칙도 같은 `evidence_of()` 를 써서 학생 값과 기준을 그대로 보여준다.
    """
    def row(rule: Rule, evidence: Evidence | None, fired: bool) -> str:
        color = CATEGORY_COLORS.get(rule.category, COLORS["primary"])
        if evidence is not None:
            value_cell = escape(evidence.value_text)
            sign = "&lt;" if evidence.worse == "below" else "≥"
            threshold_cell = f"{sign} {escape(evidence.threshold_text)}"
        else:
            value_cell = "—"
            threshold_cell = "해당 여부"
        mark = (
            f'<span class="fired" style="color:{RISK_COLORS["HIGH"]}">● 발동</span>'
            if fired else "<span>○</span>"
        )
        return (
            f'<tr class="{"" if fired else "quiet"}">'
            f'<td class="rid">{escape(rule.id)}</td>'
            f"<td>{escape(rule.title)}</td>"
            f'<td style="color:{color if fired else COLORS["faint"]}">'
            f"{escape(rule.category_label)}</td>"
            f'<td class="num">{value_cell}</td>'
            f'<td class="num">{threshold_cell}</td>'
            f"<td>{mark}</td></tr>"
        )

    body = [row(m.rule, m.evidence, True) for m in recommendation.matched]
    body += [row(rule, evidence_of(rule, student), False) for rule in recommendation.unmatched]

    _html(
        '<div class="card" style="padding:16px 8px">'
        '<table class="dt"><thead><tr>'
        "<th>규칙</th><th>판정 내용</th><th>영역</th>"
        "<th>이 학생 값</th><th>발동 기준</th><th>판정</th>"
        f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    )
    st.caption(
        f"규칙 {len(recommendation.matched) + len(recommendation.unmatched)}개 전부의 판정입니다. "
        "발동하지 않은 규칙도 같은 기준으로 평가했으며, 어떤 규칙도 학생 데이터에 없는 "
        "사정(가정환경·심리상태 등)을 추측하지 않습니다."
    )


# ---------------------------------------------------------------------------
# 지원 추천 — 이 프로젝트의 차별점이라 카드로 세워 보여준다
# ---------------------------------------------------------------------------

_PRIORITY_LABEL = PRIORITY_LABELS   # 규칙 모듈이 소유한다 (파일 출력과 같은 말을 쓰려고)


def support_cards(recommendation: RecommendationSet, *,
                  result: PredictionResult | None = None, columns: int = 3) -> None:
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

    # 규칙마다 카드를 하나씩 세우면 복합 위험 학생에서 10장이 넘어가고,
    # 그러면 "무엇부터 하라는 것인가" 가 사라진다. **대응 영역 단위로 묶는다** —
    # 담당 부서가 나뉘는 단위가 곧 카테고리이므로 실무 단위와도 맞는다.
    grouped: dict[str, list] = {}
    for m in recommendation.matched:
        grouped.setdefault(m.rule.category, []).append(m)

    cols = st.columns(max(len(grouped), 1), gap="small")
    for col, (category, items) in zip(cols, grouped.items()):
        color = CATEGORY_COLORS.get(category, COLORS["primary"])
        label = items[0].rule.category_label
        top_priority = min(m.rule.priority for m in items)

        blocks = []
        for m in items:
            programs = "".join(
                f'<div class="act-prog">{escape(p.name)}'
                f'<span class="owner">{escape(p.owner)}</span>'
                f'<span class="todo">{escape(p.action)}</span></div>'
                for p in m.rule.programs
            )
            # 사유 문장 아래에 수치 근거를 그린다. 값 비교가 없는 규칙은 그 사실을 밝힌다.
            if m.evidence is not None:
                evidence_html = evidence_bar_html(m.evidence, color)
            else:
                evidence_html = (
                    '<div class="ev-none">해당·미해당으로 판정하는 규칙입니다 (기준값 없음).</div>'
                )
            # 이 규칙이 어떤 **모델 위험요인**에 대응하는지 — 두 블록을 잇는 연결선이다.
            factor_note = ""
            if result is not None:
                linked = [f for f in result.top_factors if f.key in m.rule.factor_keys]
                if linked:
                    top = max(linked, key=lambda f: f.contribution)
                    factor_note = (
                        f" · 모델 요인 {escape(top.label)} {top.contribution * 100:.0f}%"
                    )
            blocks.append(
                f'<div class="act-item"><div class="act-title">{escape(m.rule.title)}</div>'
                f'<div class="act-reason">{escape(m.reason)}</div>{evidence_html}{programs}'
                f'<div class="act-feat">RULE {escape(m.rule.id)} · '
                f"{escape(m.rule.feature)}{factor_note}</div></div>"
            )

        with col:
            _html(
                f'<div class="act" style="--accent:{color}">'
                f'<div class="act-head">'
                f'<span class="pill pill-neutral" style="color:{color};border-color:{color}33">'
                f"{escape(label)}</span>"
                f'<span class="pill pill-neutral">'
                f"{escape(_PRIORITY_LABEL.get(top_priority, '검토'))}</span>"
                f'<span class="ds-caption" style="margin-left:auto">'
                f"{len(items)}건</span></div>"
                f'{"".join(blocks)}</div>'
            )

    _html(f'<div class="ds-caption" style="margin-top:16px">{escape(recommendation.disclaimer)}</div>')


# ---------------------------------------------------------------------------
# 상담 카드 — 화면에서 바로 읽고 그대로 캡처해 쓰는 한 장
# ---------------------------------------------------------------------------

#: 카드에 세우는 조치 개수. 더 넣으면 "무엇부터 하라는 것인가" 가 다시 흐려진다.
CARD_STEPS = 3


def report_card(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
) -> None:
    """학생 1명의 상담 카드.

    상세 분석 전체를 한 장으로 줄인 것이다. 담당자가 실제로 필요한 것은
    **누구를 · 얼마나 급하게 · 무엇부터** 세 가지뿐이고, 나머지(근거·시뮬레이션)는
    설명을 요구받았을 때 펼치면 된다. 그래서 이 카드가 상세 화면의 첫 블록이다.

    카드는 캡처되어 화면 밖으로 나간다. 그래서 출처와 면책을 카드 안에 넣는다 —
    `case_sheet` 가 파일에 같은 것을 넣는 이유와 같다.
    """
    accent = RISK_COLORS[result.risk_level]
    soft = RISK_SOFT[result.risk_level]

    attendance = "주간" if student.attendance == 1 else "야간"
    facts = (
        ("2학기 이수율", f"{student.sem2_approval_rate:.0%}"),
        ("평균 성적", f"{student.average_grade:.1f} / 20"),
        ("재정위험", f"{student.financial_risk_score} / 3"),
    )

    programs = recommendation.programs        # 규칙 우선순위 순 · 중복 제거된 목록
    steps = []
    for index, program in enumerate(programs[:CARD_STEPS], start=1):
        steps.append(
            f'<div class="rc-step"><span class="i">{index}</span><div>'
            f'<span class="t">{escape(program.name)}</span>'
            f'<span class="o">{escape(program.owner)}</span>'
            f'<span class="d">{escape(program.action)}</span></div></div>'
        )
    if not steps:
        steps.append(
            '<div class="rc-more">조건을 넘는 규칙이 없습니다. 정기 모니터링 대상으로 유지합니다.</div>'
        )
    remaining = len(programs) - CARD_STEPS
    more = (
        f'<div class="rc-more">외 {remaining}건은 아래 &lsquo;무엇을 할 것인가&rsquo; 에 있습니다.</div>'
        if remaining > 0 else ""
    )

    stats = "".join(
        f'<div><div class="k">{escape(k)}</div><div class="v">{escape(v)}</div></div>'
        for k, v in facts
    )

    source = "프로토타입 예측" if result.is_dummy else f"{result.model_name} v{result.model_version}"

    _html(
        f'<div class="rc" style="--accent:{accent};--accent-soft:{soft};--accent-line:{accent}33">'
        f'<div class="rc-band">{risk_pill_html(result.risk_level)}'
        f'{focus_pill_html() if recommendation.is_priority_case else ""}'
        f'<span class="who">발동 규칙 {len(recommendation.matched)}건 · '
        f"연계 부서 {len({p.owner for p in programs})}곳</span></div>"
        f'<div class="rc-body">'
        f'<div class="rc-id">{escape(student.student_id)}</div>'
        f'<div class="rc-sub">{escape(student.major_field)} · {attendance} · '
        f"{escape(student.admission_pathway)}</div>"
        f'<div class="rc-prob"><span class="n">{result.dropout_percent:.1f}'
        f'<span class="p">%</span></span><span class="l">중도탈락 확률</span></div>'
        f'<div class="rc-bar"><span style="width:{result.dropout_percent:.1f}%"></span></div>'
        f'<div class="rc-stats">{stats}</div>'
        f'<div class="rc-todo"><div class="k">지금 할 일</div>{"".join(steps)}{more}</div>'
        f"</div>"
        f'<div class="rc-foot">{escape(source)} · 이 카드는 위험요인에 대응하는 교내 지원을 '
        f"연결한 것이며, 중도탈락을 단정하거나 예방을 보장하지 않습니다. 최종 판단은 담당자가 합니다.</div>"
        f"</div>"
    )

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


def risk_and_factors(
    result: PredictionResult,
    recommendation: RecommendationSet | None = None,
) -> None:
    """**얼마나 위험한가** + **왜 위험한가** 두 칸.

    두 화면(예측 · 목록 상세)이 이 블록을 같은 모양으로 쓴다. 예측 화면은 한 흐름으로
    읽고 상세 화면은 '근거' 탭 안에 넣는데, **모양이 갈리면 같은 것을 두 번 배우게 된다.**
    """
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
        factor_list(result, recommendation)


def trace_expander(
    student: StudentInput, recommendation: RecommendationSet, *, expanded: bool = False
) -> None:
    with st.expander(
        f"규칙 판정 전체 보기 · 발동 {len(recommendation.matched)}건 / "
        f"미발동 {len(recommendation.unmatched)}건",
        expanded=expanded,
    ):
        rule_trace(recommendation, student)


def action_panel(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
) -> None:
    """**조치** — 담당자가 실제로 들고 나가는 것만.

    운영 화면에서는 이 탭이 기본값이다. 담당자에게 필요한 건 누구를 · 얼마나 급하게 ·
    무엇부터이고, 근거는 설명을 요구받았을 때 옆 탭에서 펼치면 된다.
    """
    report_card(student, result, recommendation)
    spacer(16)
    section("무엇을 할 것인가", "규칙 엔진(rules/recommendation_rules.py)이 판정한 지원 연결입니다.")
    support_cards(recommendation, result=result)


def evidence_panel(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
) -> None:
    """**근거** — "왜 그렇게 판단했나" 를 요구받았을 때 여는 것."""
    with st.expander("학생 기본 정보 전체", expanded=False):
        student_summary(student)
    spacer(8)
    risk_and_factors(result, recommendation)
    spacer(10)
    trace_expander(student, recommendation, expanded=True)


def result_panel(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
    *,
    show_summary: bool = True,
) -> None:
    """예측 결과를 **한 흐름으로** 읽는 구성. 예측 화면이 쓴다.

    왼쪽 **얼마나 위험한가** → 가운데 **왜 위험한가** → 아래 **그래서 무엇을 할 것인가**.
    이 순서가 이 제품이 하는 말 전부라, 처음 보는 사람에게 설명할 때는 이대로 간다.
    (매일 쓰는 담당자 화면은 순서가 다르다 — `action_panel` 참조.)
    """
    if show_summary:
        report_card(student, result, recommendation)
        spacer(12)
        with st.expander("학생 기본 정보 전체", expanded=False):
            student_summary(student)
        spacer(4)

    risk_and_factors(result, recommendation)

    section("무엇을 할 것인가", "규칙 엔진(rules/recommendation_rules.py)이 판정한 지원 연결입니다.")
    support_cards(recommendation, result=result)

    trace_expander(student, recommendation)


# ---------------------------------------------------------------------------
# 우선 확인 명단 — 기본 dataframe 대신 직접 그린다
# ---------------------------------------------------------------------------

def priority_table(rows: list[dict]) -> None:
    """`{rank, sid, major, probability, level, category, rules, focus}` 목록.

    `st.dataframe` 은 정렬·스크롤이 필요할 때 쓴다. 여기는 '먼저 볼 8명' 이라
    **읽히는 것**이 목적이므로 직접 그려서 위험 막대와 배지를 함께 보여준다.

    확률만으로는 위쪽이 갈리지 않는다 — 위험 점수가 이미 최대치인 학생이 수백 명이라
    상위권 확률이 서로 붙는다. 그래서 **발동한 규칙 수**를 함께 보여주고 동점을 그것으로
    가른다. 규칙이 많이 걸린 학생일수록 여러 영역이 동시에 무너진 학생이다.
    """
    if not rows:
        empty_state("표시할 학생이 없습니다.")
        return

    body = []
    for r in rows:
        color = RISK_COLORS[r["level"]]
        pct = r["probability"] * 100
        # 학생 ID 를 링크로 만들고 CSS 로 그 링크를 줄 전체로 늘린다.
        # 진짜 <a> 라 클릭·키보드·새 탭이 모두 브라우저 기본 동작으로 처리된다.
        link = r.get("href")
        sid_cell = (
            f'<a class="rowlink" href="{escape(link)}">{escape(r["sid"])}</a>'
            if link else escape(r["sid"])
        )
        body.append(
            f"""<tr>
                  <td class="rank">{r['rank']:02d}</td>
                  <td class="sid">{sid_cell}</td>
                  <td>{escape(r['major'])}</td>
                  <td>
                    <div class="riskbar">
                      <span class="track"><span class="fill"
                        style="width:{pct:.0f}%;background:{color}"></span></span>
                      <span class="pct" style="color:{color}">{pct:.1f}%</span>
                    </div>
                  </td>
                  <td>{risk_pill_html(r['level'], with_label=False)}</td>
                  <td>{escape(r['category'])}</td>
                  <td class="num">{r.get('rules', 0)}건</td>
                  <td>{focus_pill_html() if r['focus'] else ''}</td>
                  <td class="go">상세 →</td>
                </tr>"""
        )
    _html(
        '<div class="card" style="padding:16px 8px">'
        '<table class="dt"><thead><tr>'
        "<th></th><th>학생</th><th>전공 계열</th><th>중도탈락 확률</th>"
        "<th>등급</th><th>주요 위험</th><th>발동 규칙</th><th></th><th></th>"
        f'</tr></thead><tbody>{"".join(body)}</tbody></table>'
        '<div class="bars-hint" style="padding:0 12px">'
        "줄을 가리키면 나머지가 옅어지고, 클릭하면 그 학생의 상세 분석으로 이동합니다.</div></div>"
    )


def whatif_delta(
    before: PredictionResult,
    after: PredictionResult,
    before_recommendation: RecommendationSet,
    after_recommendation: RecommendationSet,
) -> None:
    """현재 → 시뮬레이션 비교. **빠진 규칙 목록이 이 블록의 결론이다.**

    확률이 내려간 것만 보여주면 "숫자가 움직였다" 로 끝난다. 어떤 추천이 사라졌는지를
    함께 적어야 "그 값 때문에 그 추천이 나왔다" 가 증명된다.
    """
    delta = after.dropout_percent - before.dropout_percent
    accent = RISK_COLORS[after.risk_level]
    sign = "+" if delta > 0 else ""

    fired_before = {m.rule.id: m.rule.title for m in before_recommendation.matched}
    fired_after = {m.rule.id: m.rule.title for m in after_recommendation.matched}
    dropped = [(rid, title) for rid, title in fired_before.items() if rid not in fired_after]
    added = [(rid, title) for rid, title in fired_after.items() if rid not in fired_before]

    def rule_line(label: str, items: list[tuple[str, str]], color: str) -> str:
        if not items:
            return f'<div><span class="tag">{escape(label)}</span> 없음</div>'
        body = " · ".join(f"{escape(rid)} {escape(title)}" for rid, title in items)
        return (
            f'<div><span class="tag" style="color:{color}">{escape(label)}</span> {body}</div>'
        )

    _html(
        f'<div class="wi" style="--accent:{accent}">'
        f'<div class="wi-row">'
        f'<div class="wi-side"><div class="k">현재</div>'
        f'<div class="v ds-num">{before.dropout_percent:.1f}<span class="p">%</span></div>'
        f"{risk_pill_html(before.risk_level)}"
        f'<div class="d">발동 규칙 {len(before_recommendation.matched)}건</div></div>'
        f'<div class="wi-arrow">→</div>'
        f'<div class="wi-side after"><div class="k">시뮬레이션</div>'
        f'<div class="v ds-num">{after.dropout_percent:.1f}<span class="p">%</span></div>'
        f"{risk_pill_html(after.risk_level)}"
        f'<div class="d">발동 규칙 {len(after_recommendation.matched)}건</div></div>'
        f'<div class="wi-delta">{sign}{delta:.1f}%p'
        f'<span class="c">{escape(before.risk_level)} → {escape(after.risk_level)}</span></div>'
        f"</div>"
        f'<div class="wi-rules">'
        + rule_line("빠진 추천", dropped, RISK_COLORS["LOW"])
        + rule_line("새로 발동", added, RISK_COLORS["HIGH"])
        + "</div></div>"
    )

    # 확률이 표시상 그대로인데 규칙만 바뀌면 화면이 고장난 것처럼 읽힌다.
    # 왜 안 움직였는지를 밝힌다 — 예측기가 더미냐 아니냐에 따라 이유가 다르다.
    if abs(delta) < 0.05 and (dropped or added):
        if after.is_dummy:
            st.caption(
                "확률 표시는 반올림해서 그대로입니다 — 프로토타입 예측기가 양 끝의 과장된 확신을 "
                "눌러 두기 때문에 높은 구간에서는 확률이 잘 움직이지 않습니다. "
                "**이 시뮬레이션의 결과는 발동 규칙의 변화입니다.**"
            )
        else:
            st.caption(
                "확률은 거의 움직이지 않았지만 발동 규칙이 바뀌었습니다 — 이 값은 모델의 판단보다 "
                "규칙의 기준선에 더 가까이 있었다는 뜻입니다."
            )


# ---------------------------------------------------------------------------
# 내려받기 — 화면에서 본 것을 담당자 손에 남긴다
# ---------------------------------------------------------------------------

def case_downloads(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
    *,
    key: str,
) -> None:
    """학생 1명의 상담 카드(.txt) + 조치 목록(.csv).

    파일 이름은 **ASCII 로만** 만든다. 발표 PC 브라우저가 한글 파일명을 어떻게 처리하는지에
    데모를 걸지 않는다 — 내용은 어차피 한국어다.
    """
    left, right = st.columns(2, gap="small")
    with left:
        st.download_button(
            "상담 카드 내려받기 (.txt)",
            data=case_sheet.build_text(student, result, recommendation).encode("utf-8-sig"),
            file_name=case_sheet.filename("case_sheet", student.student_id, extension="txt"),
            mime="text/plain",
            width="stretch",
            key=f"dl_text_{key}",
        )
    with right:
        rows = case_sheet.action_rows(student, result, recommendation)
        st.download_button(
            f"조치 목록 내려받기 (.csv · {len(rows)}건)",
            data=case_sheet.to_csv(rows, case_sheet.ACTION_FIELDS),
            file_name=case_sheet.filename("actions", student.student_id),
            mime="text/csv",
            width="stretch",
            disabled=not rows,
            key=f"dl_actions_{key}",
        )
    st.caption(
        "내려받은 파일에도 면책 문구와 예측 출처가 함께 적힙니다 — "
        "화면 배너는 파일을 따라가지 않기 때문입니다."
    )


_KEEP = TARGET_CLASSES  # 화면이 클래스 순서를 이 모듈 경유로도 얻을 수 있게 남긴다.
