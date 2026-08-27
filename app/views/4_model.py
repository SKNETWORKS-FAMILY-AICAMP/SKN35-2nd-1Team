"""
화면 4 — 모델 성능.

이 화면은 두 가지를 한다.

    (A) 팀이 낸 학습 결과서(`reports/model_metrics.json`)를 그대로 보여준다.
    (B) 지금 앱에 연결된 모델을 **정답 라벨로 직접 채점**한다 — 임계값을 움직여 가며.

🔴 (B) 는 학습된 모델이 연결됐을 때만 그린다.
    더미 예측기의 확률로 혼동행렬을 그리면 없는 성능을 주장하는 것이 된다.
    프로토타입 모드에서는 무엇이 필요한지만 안내하고 숫자는 한 개도 내지 않는다.

이 화면이 파는 것은 숫자가 아니라 **운영 설계**다.
표본이 적고 클래스가 불균형한 상황에서 지표 하나를 자랑하는 대신, 놓친 학생과
헛걸음한 상담 사이의 교환을 임계값 슬라이더로 그 자리에서 보여준다.
"""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from components import ui
from components.state import cached_evaluation, cached_roster, start_page
from components.theme import (
    CLASS_COLORS,
    COLORS,
    PLOTLY_CONFIG,
    RISK_COLORS,
    style_figure,
)
from services import evaluation, model_metrics
from services.predictor import DECISION_THRESHOLD
from services.prediction_service import get_service

#: 운영 기본값. "놓치지 않는 것" 을 먼저 만족시키고 그 안에서 상담 규모를 줄인다.
DEFAULT_MIN_RECALL = 0.80

service = get_service()

start_page(
    "모델 성능",
    "학습 결과서와, 지금 연결된 모델이 실제 명단에서 어떻게 판정하는지를 함께 봅니다.",
    meta=(
        '<div class="ds-eyebrow">Model</div>'
        f'<div class="ds-sub" style="margin-top:4px">{escape(service.model_label)}</div>'
    ),
)

ui.prototype_banner(service)

# ---------------------------------------------------------------------------
# (A) 팀 학습 결과서
# ---------------------------------------------------------------------------

ui.section(
    "팀 학습 결과서",
    "모델링 담당자가 낸 값을 그대로 옮깁니다. 이 화면은 reports/ 를 읽기만 합니다.",
)

report = model_metrics.load()

if report is None:
    ui.empty_state(
        "학습 결과서가 아직 없습니다",
        "reports/model_metrics.json 을 아래 형식으로 넣으면 이 자리에 모델 비교표가 나타납니다. "
        "코드는 고치지 않아도 됩니다.",
    )
    with st.expander("팀에 전달할 파일 형식", expanded=False):
        st.code(model_metrics.SCHEMA_HINT, language="json")
        st.caption(
            "이름(name)만 있으면 읽습니다. 나머지 항목은 있는 것만 표에 채워지므로 "
            "일부만 채워 먼저 올려도 됩니다. 형식이 깨져도 앱은 죽지 않고 이 안내로 물러납니다."
        )
else:
    columns = [key for key in model_metrics.SCORE_KEYS
               if any(m.value(key) is not None for m in report.models)]
    header = "".join(f"<th>{escape(key)}</th>" for key in columns)
    body = []
    for model in report.models:
        chosen = model.name == (report.best.name if report.best else "")
        cells = "".join(
            f'<td class="num">{model.value(key):.3f}</td>' if model.value(key) is not None
            else '<td class="num">—</td>'
            for key in columns
        )
        body.append(
            f"<tr>"
            f'<td class="sid">{escape(model.name)}'
            f'{ui.neutral_pill_html("선택") if chosen else ""}</td>'
            f"<td>{escape(model.kind)}</td>{cells}"
            f'<td class="ds-caption">{escape(model.notes)}</td></tr>'
        )
    st.markdown(
        '<div class="card" style="padding:16px 8px">'
        f'<table class="dt"><thead><tr><th>모델</th><th>계열</th>{header}<th>메모</th>'
        f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True,
    )
    facts = [f"작성 {report.generated_at}" if report.generated_at else "",
             f"판정 임계값 {report.threshold:.2f}" if report.threshold is not None else "",
             " · ".join(f"{k} {v:,}" for k, v in report.dataset.items())]
    st.caption(" · ".join(part for part in facts if part) + f" · 출처 {report.source}")

    if report.feature_importance:
        ui.spacer(12)
        with st.container(border=True):
            st.markdown(
                '<div class="card-title">모델이 크게 본 변수</div>'
                '<div class="card-sub">학습 결과서에 담긴 값입니다. '
                "화면의 위험요인 설명과는 계산 방식이 다를 수 있습니다.</div>",
                unsafe_allow_html=True,
            )
            top = report.feature_importance[:10]
            ui.bar_chart(
                [{"label": name, "value": value, "color": COLORS["primary"],
                  "display": f"{value:.3f}"} for name, value in top],
                label_width=190,
            )

# ---------------------------------------------------------------------------
# (B) 연결된 모델을 정답 라벨로 채점
# ---------------------------------------------------------------------------

ui.section(
    "연결된 모델의 실제 판정",
    "명단 학생들의 정답 라벨과 지금 화면이 쓰는 확률을 맞춰 봅니다.",
)

if service.is_dummy:
    # 🔴 하드 게이트 — 학습되지 않은 값으로는 채점하지 않는다.
    ui.empty_state(
        "학습된 모델이 연결되지 않았습니다",
        "지금 화면의 확률은 학습되지 않은 규칙 기반 값이라 채점하지 않습니다. "
        "models/best_model.joblib 을 넣고 services/prediction_service.py 의 "
        "USE_REAL_MODEL 을 True 로 바꾸면 이 자리가 채워집니다.",
    )
    st.caption(
        "무엇으로 채점하는지: 명단 학생의 정답 라벨은 팀 전처리 CSV 에 이미 들어 있어, "
        "모델 파일 하나만 오면 추가 작업 없이 이 화면이 살아납니다."
    )
    st.stop()

roster = cached_roster()
labels, probabilities = cached_evaluation()

if not labels:
    ui.empty_state(
        "정답 라벨이 없습니다",
        "data/processed/ 의 전처리 CSV 에 target 열이 있어야 채점할 수 있습니다.",
    )
    st.stop()

matrices = evaluation.sweep(labels, probabilities)
auc = evaluation.roc_auc(labels, probabilities)
ap = evaluation.average_precision(matrices)
recommended = evaluation.best_threshold(matrices, minimum_recall=DEFAULT_MIN_RECALL)

threshold = st.slider(
    "판정 임계값 — 이 값 이상이면 '위험'으로 표시합니다",
    min_value=0.0, max_value=1.0,
    value=float(recommended.threshold if recommended else DECISION_THRESHOLD),
    step=0.01,
    key="model_threshold",
)
current = evaluation.confusion_at(labels, probabilities, threshold)
positives = current.tp + current.fn

ui.spacer(8)
hero_col, side_col = st.columns([1, 1.9], gap="medium")
with hero_col:
    ui.kpi_hero(
        "놓친 위험학생 · FN",
        f"{current.fn:,}",
        f"실제 중도탈락 {positives:,}명 중 {current.fn / positives * 100:.1f}% · "
        "이 화면에서 가장 비싼 오류입니다",
        RISK_COLORS["HIGH"],
        unit="명",
        share=current.fn / positives if positives else 0,
    )
with side_col:
    ui.kpi_row(
        [
            {"label": "재현율", "value": f"{current.recall * 100:.1f}", "unit": "%",
             "caption": "실제 이탈자 중 찾아낸 비율", "accent": RISK_COLORS["LOW"],
             "share": current.recall},
            {"label": "정밀도", "value": f"{current.precision * 100:.1f}", "unit": "%",
             "caption": "위험 표시 중 실제 이탈", "accent": COLORS["primary"],
             "share": current.precision},
            {"label": "상담 대상", "value": f"{current.flagged:,}", "unit": "명",
             "caption": f"전체 {current.total:,}명 중",
             "accent": CLASS_COLORS["Dropout"],
             "share": current.flagged / current.total if current.total else 0},
        ],
        columns=3,
    )
    ui.spacer(6)
    ui.kpi_row(
        [
            {"label": "ROC-AUC", "value": f"{auc:.3f}",
             "caption": "임계값과 무관한 순위 능력", "accent": COLORS["ink"]},
            {"label": "PR-AUC", "value": f"{ap:.3f}",
             "caption": "불균형에 정직한 지표", "accent": COLORS["ink"]},
            {"label": "전체 적중", "value": f"{current.accuracy * 100:.1f}", "unit": "%",
             "caption": "운영 지표로 쓰지 않습니다", "accent": COLORS["faint"]},
        ],
        columns=3,
    )

# ── 혼동행렬 + PR 곡선 ─────────────────────────────────────────────────────
ui.spacer(12)
left, right = st.columns([1, 1.15], gap="large")

with left, st.container(border=True):
    st.markdown(
        '<div class="card-title">이 임계값에서의 판정</div>'
        f'<div class="card-sub">임계값 {threshold:.2f} 기준 · 세로가 실제, 가로가 예측입니다.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""<div class="card" style="margin-top:12px"><table class="dt">
          <thead><tr><th></th><th>위험 표시</th><th>표시 안 함</th></tr></thead>
          <tbody>
            <tr><td class="sid">실제 이탈</td>
                <td class="num" style="color:{RISK_COLORS['LOW']};font-weight:700">
                  {current.tp:,}</td>
                <td class="num" style="color:{RISK_COLORS['HIGH']};font-weight:700">
                  {current.fn:,} <span class="ds-caption">놓침</span></td></tr>
            <tr><td class="sid">실제 잔류</td>
                <td class="num" style="color:{RISK_COLORS['MEDIUM']}">
                  {current.fp:,} <span class="ds-caption">헛걸음</span></td>
                <td class="num">{current.tn:,}</td></tr>
          </tbody></table></div>""",
        unsafe_allow_html=True,
    )
    st.caption(
        f"임계값을 내리면 놓침({current.fn:,}명)이 줄고 헛걸음({current.fp:,}명)이 늘어납니다. "
        "어느 쪽을 감수할지가 이 시스템의 운영 결정입니다."
    )

with right, st.container(border=True):
    st.markdown(
        '<div class="card-title">재현율과 정밀도의 교환</div>'
        '<div class="card-sub">지금 임계값의 위치를 점으로 표시했습니다.</div>',
        unsafe_allow_html=True,
    )
    points = evaluation.pr_points(matrices)
    figure = go.Figure()
    figure.add_scatter(
        x=[recall for recall, _ in points], y=[precision for _, precision in points],
        mode="lines", line=dict(color=COLORS["primary"], width=2),
        hovertemplate="재현율 %{x:.2f} · 정밀도 %{y:.2f}<extra></extra>",
    )
    figure.add_scatter(
        x=[current.recall], y=[current.precision], mode="markers",
        marker=dict(size=11, color=RISK_COLORS["HIGH"], line=dict(width=0)),
        hovertemplate=f"임계값 {threshold:.2f}<extra></extra>",
    )
    base_rate = positives / current.total if current.total else 0
    figure.add_hline(y=base_rate, line=dict(color=COLORS["faint"], width=1, dash="dot"))
    figure.update_xaxes(title=dict(text="재현율", font=dict(size=11)), range=[0, 1.02])
    figure.update_yaxes(title=dict(text="정밀도", font=dict(size=11)), range=[0, 1.02])
    st.plotly_chart(style_figure(figure, height=300, grid="y"),
                    width="stretch", config=PLOTLY_CONFIG, key="c_pr")
    st.caption(
        f"점선은 아무 판정 없이 맞힐 확률({base_rate:.0%})입니다. 곡선이 그 위에 있는 만큼이 "
        "모델이 더한 값입니다."
    )

# ---------------------------------------------------------------------------
# (C) 그래서 임계값을 어떻게 정했는가
# ---------------------------------------------------------------------------

ui.section("임계값을 어떻게 정하는가", "이 시스템이 성능이 아니라 운영을 설계했다는 자리입니다.")

if recommended is not None:
    st.markdown(
        f"""<div class="card card-lg">
          <div class="ds-eyebrow">운영 권고</div>
          <div class="ds-h2" style="margin-top:8px">임계값 {recommended.threshold:.2f}</div>
          <div class="ds-body" style="margin-top:14px;max-width:88ch">
            놓친 학생은 지원을 아예 받지 못하고, 헛걸음한 상담은 담당자 시간만 씁니다.
            <b>두 오류의 값이 다르므로</b> 하나의 지표를 최대화하지 않고
            <b>재현율 {DEFAULT_MIN_RECALL:.0%} 이상</b>을 먼저 만족시킨 뒤,
            그 안에서 상담 대상이 가장 적은 지점을 고릅니다.
          </div>
          <div class="ds-sub" style="margin-top:14px">
            이 지점에서 실제 이탈자 {recommended.tp:,}명을 찾아내고 {recommended.fn:,}명을 놓치며,
            상담 대상은 {recommended.flagged:,}명 (전체의
            {recommended.flagged / recommended.total * 100:.0f}%) 입니다.
          </div>
        </div>""",
        unsafe_allow_html=True,
    )
else:
    ui.empty_state(
        f"재현율 {DEFAULT_MIN_RECALL:.0%} 를 만족하는 임계값이 없습니다",
        "모델이 실제 이탈자를 충분히 찾아내지 못하고 있습니다. 재학습이나 재표본이 필요합니다.",
    )

ui.spacer(12)
st.caption(
    f"채점 대상은 {roster.source} 입니다. 학습에 쓰이지 않은 분할인지는 팀 전처리 기준을 따릅니다. "
    "표본이 적을수록 이 값들은 크게 흔들리므로, 지표 하나의 소수점보다 "
    "임계값을 옮겼을 때 상담 규모가 어떻게 변하는지를 보십시오."
)
