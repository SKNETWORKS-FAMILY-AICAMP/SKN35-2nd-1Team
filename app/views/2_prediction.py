"""
화면 2 — 학생 1명의 위험 예측. 발표 데모의 핵심 화면이다.

입력이 32개나 되지만 **설문지처럼 보이면 실패다.** 그래서 한 줄로 늘어놓지 않고
네 묶음으로 나눠 탭에 넣는다 — 한 번에 보이는 것은 최대 9개다.

    학생 프로필 · 학업 기록 · 재정 상황 · 입학과 배경

결과는 이 화면의 climax 다. **얼마나 위험한가 → 왜 위험한가 → 무엇을 할 것인가**
순서로 읽히도록 계층을 준다.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from components import ui
from components.state import start_page
from components.theme import CATEGORY_COLORS, COLORS, RISK_COLORS
from rules import recommendation_rules as rules
from services.prediction_service import get_service
from utils.feature_mapping import UI_FIELDS, FieldSpec, StudentInput

WIDGET_PREFIX = "in_"

#: 입력 32개를 네 묶음으로. 값은 `feature_mapping` 의 group 이름들이다.
#  데이터 계약(FIELD_GROUPS)은 건드리지 않고 **화면에서만** 다시 묶는다.
TABS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("학생 프로필", "인구·사회 정보와 재학 형태", ("기본 정보",)),
    ("학업 기록", "1·2학기 수강과 성취 — 모델이 가장 크게 보는 신호", ("1학기 학업", "2학기 학업")),
    ("재정 상황", "등록금·채무·장학 — 재정위험점수의 재료", ("경제 정보",)),
    ("입학과 배경", "입학 경로와 가정 배경", ("입학 정보", "가정 배경")),
)

#: 발표 중 값을 하나씩 바꾸지 않도록 준비한 예시. **실제 학생이 아니라 예시 입력값이다.**
#  적지 않은 항목은 StudentInput 의 기본값이 그대로 쓰인다.
PRESETS: dict[str, dict[str, Any]] = {
    "HIGH · 복합 위험": dict(
        student_id="예시-HIGH", age_at_enrollment=30, gender=1, major_field="사회",
        attendance=0, displaced=1, admission_pathway="성인학습자 전형", application_order=3,
        admission_grade=118.0, tuition_fees_up_to_date=0, scholarship_holder=0, debtor=1,
        sem1_enrolled=6, sem1_approved=3, sem1_grade=10.8, sem1_without_evaluations=1,
        sem2_enrolled=6, sem2_approved=1, sem2_grade=7.9, sem2_without_evaluations=2,
    ),
    "MEDIUM · 학업 부진": dict(
        student_id="예시-MEDIUM", age_at_enrollment=20, gender=1, major_field="공학·IT",
        attendance=1, displaced=1, admission_pathway="일반전형", application_order=1,
        admission_grade=124.0, tuition_fees_up_to_date=1, scholarship_holder=0, debtor=0,
        sem1_enrolled=6, sem1_approved=4, sem1_grade=11.6, sem1_without_evaluations=0,
        sem2_enrolled=6, sem2_approved=2, sem2_grade=10.2, sem2_without_evaluations=1,
    ),
    "MEDIUM · 재정 위험": dict(
        student_id="예시-FIN", age_at_enrollment=21, gender=0, major_field="경영",
        attendance=1, displaced=0, admission_pathway="일반전형", application_order=0,
        admission_grade=131.0, tuition_fees_up_to_date=0, scholarship_holder=0, debtor=1,
        sem1_enrolled=6, sem1_approved=5, sem1_grade=13.1, sem1_without_evaluations=0,
        sem2_enrolled=6, sem2_approved=4, sem2_grade=12.4, sem2_without_evaluations=0,
    ),
    "LOW · 안정": dict(
        student_id="예시-LOW", age_at_enrollment=19, gender=0, major_field="보건",
        attendance=1, displaced=0, admission_pathway="일반전형", application_order=0,
        admission_grade=152.0, tuition_fees_up_to_date=1, scholarship_holder=1, debtor=0,
        sem1_enrolled=6, sem1_approved=6, sem1_grade=16.1, sem1_without_evaluations=0,
        sem2_enrolled=6, sem2_approved=6, sem2_grade=16.8, sem2_without_evaluations=0,
    ),
}


# ---------------------------------------------------------------------------
# 위젯
# ---------------------------------------------------------------------------

def _key(spec: FieldSpec) -> str:
    return f"{WIDGET_PREFIX}{spec.key}"


def apply_values(values: dict[str, Any]) -> None:
    for spec in UI_FIELDS:
        if spec.key in values:
            st.session_state[_key(spec)] = values[spec.key]
    st.session_state["prediction_student_id"] = str(values.get("student_id", "직접 입력"))


def init_defaults() -> None:
    """위젯 기본값을 session_state 에 한 번만 심는다.

    위젯에 value= 와 key= 를 동시에 주면 Streamlit 이 경고를 낸다. 값은 항상
    session_state 로만 관리하고 위젯은 key 만 받는다.
    """
    for spec in UI_FIELDS:
        st.session_state.setdefault(_key(spec), spec.default)
    st.session_state.setdefault("prediction_student_id", "직접 입력")


def consume_prefill() -> None:
    """'학생 목록'에서 보낸 학생이 있으면 위젯을 만들기 전에 반영한다."""
    student = st.session_state.pop("prefill_student", None)
    if student is None:
        return
    apply_values(student.to_ui_dict())
    st.session_state["prediction_last"] = student


def _render_field(spec: FieldSpec) -> Any:
    key = _key(spec)

    if spec.kind == "text_select":
        choices = list(spec.choices or ())
        if st.session_state.get(key) not in choices:
            st.session_state[key] = spec.default
        labels = spec.labels or {}
        return st.selectbox(spec.label, options=choices,
                            format_func=lambda v: labels.get(v, v),
                            key=key, help=spec.help or None)

    if spec.kind == "select":
        options = list(spec.options or {})
        if st.session_state.get(key) not in options:
            st.session_state[key] = spec.default
        return st.selectbox(spec.label, options=options,
                            format_func=lambda c: (spec.options or {}).get(c, str(c)),
                            key=key, help=spec.help or None)

    cast = type(spec.default)
    if spec.kind == "slider":
        st.session_state[key] = cast(
            min(max(st.session_state.get(key, spec.default), spec.minimum), spec.maximum)
        )
        return st.slider(spec.label, min_value=cast(spec.minimum), max_value=cast(spec.maximum),
                         step=cast(spec.step or 1),
                         format="%.1f" if cast is float else None,
                         key=key, help=spec.help or None)

    st.session_state[key] = int(
        min(max(st.session_state.get(key, spec.default), spec.minimum), spec.maximum)
    )
    return st.number_input(spec.label, min_value=int(spec.minimum), max_value=int(spec.maximum),
                           step=int(spec.step or 1), key=key, help=spec.help or None)


def _render_groups(groups: tuple[str, ...], columns: int = 3) -> dict[str, Any]:
    """한 탭 안의 필드들을 열로 흘려 넣는다. 세로로만 쌓으면 스크롤이 길어진다."""
    specs = [s for s in UI_FIELDS if s.group in groups]
    values: dict[str, Any] = {}
    cols = st.columns(columns, gap="large")
    per = -(-len(specs) // columns)                 # 올림 나눗셈
    for index, spec in enumerate(specs):
        with cols[min(index // per, columns - 1)]:
            values[spec.key] = _render_field(spec)
    return values


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

start_page(
    "학생 위험 예측",
    "학생 한 명의 정보를 입력하면 중도탈락 위험도와 위험요인, 그에 대응하는 "
    "교내 지원 프로그램을 함께 보여줍니다.",
    meta=(
        '<div class="ds-eyebrow">Inputs</div>'
        f'<div class="ds-sub" style="margin-top:4px">{len(UI_FIELDS)}개 입력 · 파생변수 5종 자동 계산</div>'
    ),
)

consume_prefill()
init_defaults()

service = get_service()
ui.prototype_banner(service)

# ── 프리셋 — 발표 중 원클릭 데모 ───────────────────────────────────────────
ui.section("예시 불러오기", "발표용으로 준비한 입력값입니다. 실제 학생 기록이 아닙니다.")

preset_cols = st.columns(len(PRESETS), gap="small")
for col, (name, values) in zip(preset_cols, PRESETS.items()):
    with col:
        if st.button(name, width="stretch", key=f"preset_{name}"):
            apply_values(values)
            st.rerun()

current_id = st.session_state.get("prediction_student_id", "직접 입력")
if current_id != "직접 입력":
    st.markdown(
        f'<div class="ds-caption" style="margin-top:2px">현재 불러온 예시 · '
        f'<b style="color:{COLORS["primary"]}">{current_id}</b> — '
        "아래에서 값을 바꾸면 그대로 다시 예측합니다.</div>",
        unsafe_allow_html=True,
    )

# ── 입력 ───────────────────────────────────────────────────────────────────
ui.section(
    "학생 정보",
    "팀 전처리(Model B)가 요구하는 입력입니다. 이수율·재정위험점수 등 파생변수 5종은 "
    "아래 값에서 자동 계산되므로 직접 입력하지 않습니다. 모든 항목에 기본값이 채워져 있습니다.",
)

with st.form("prediction_form", border=True):
    values: dict[str, Any] = {}
    tabs = st.tabs([f"{name}" for name, _, _ in TABS])
    for tab, (name, desc, groups) in zip(tabs, TABS):
        with tab:
            st.markdown(f'<div class="ds-caption" style="margin-bottom:10px">{desc}</div>',
                        unsafe_allow_html=True)
            values.update(_render_groups(groups))

    st.divider()
    submitted = st.form_submit_button("위험도 분석", type="primary", width="stretch")

if submitted:
    st.session_state["prediction_last"] = StudentInput(
        student_id=st.session_state.get("prediction_student_id", "직접 입력"), **values
    )

student = st.session_state.get("prediction_last")
if student is None:
    ui.spacer(16)
    ui.empty_state(
        "아직 분석하지 않았습니다",
        "위에서 예시를 불러오거나 값을 입력한 뒤 '위험도 분석' 을 누르면 결과가 여기에 나타납니다.",
    )
    st.stop()

for problem in student.validate():
    st.warning(problem)

try:
    result = service.predict(student)
except Exception as error:  # 예측기 교체 중 오류가 나도 앱은 살아 있어야 한다.
    ui.spacer(16)
    ui.empty_state("예측을 수행할 수 없습니다", str(error))
    st.stop()

recommendation = rules.evaluate(student, result)

# ── 결과 — 이 화면의 climax ────────────────────────────────────────────────
ui.section("분석 결과", f"대상 · {student.student_id}")
ui.result_panel(student, result, recommendation, show_summary=True)

ui.spacer(10)
ui.case_downloads(student, result, recommendation, key="prediction")

with st.expander("이 예측에 쓰인 파생변수 5종", expanded=False):
    st.markdown(
        f"""<table class="dt"><thead><tr>
              <th>파생변수</th><th>값</th><th>계산 방법</th></tr></thead><tbody>
            <tr><td class="ds-mono">sem1_approval_rate</td>
                <td class="num">{student.sem1_approval_rate:.3f}</td>
                <td>1학기 이수 ÷ 수강 (수강 0이면 0)</td></tr>
            <tr><td class="ds-mono">sem2_approval_rate</td>
                <td class="num">{student.sem2_approval_rate:.3f}</td>
                <td>2학기 이수 ÷ 수강 (수강 0이면 0)</td></tr>
            <tr><td class="ds-mono">grade_change</td>
                <td class="num">{student.grade_change:+.2f}</td>
                <td>2학기 평점 − 1학기 평점</td></tr>
            <tr><td class="ds-mono">zero_enrolled_1st_sem</td>
                <td class="num">{student.zero_enrolled_1st_sem}</td>
                <td>1학기 수강 과목 0 여부</td></tr>
            <tr><td class="ds-mono">financial_risk_score</td>
                <td class="num">{student.financial_risk_score} / 3</td>
                <td>등록금 미납 + 채무 + 장학금 미수혜</td></tr>
            </tbody></table>""",
        unsafe_allow_html=True,
    )
    st.caption(
        "계산 정의는 팀 전처리 노트북(notebooks/preprocess.ipynb)과 같습니다. "
        "정의를 바꾸려면 utils/feature_mapping.py 의 StudentInput 한 곳만 고칩니다."
    )

_KEEP = (CATEGORY_COLORS, RISK_COLORS)
