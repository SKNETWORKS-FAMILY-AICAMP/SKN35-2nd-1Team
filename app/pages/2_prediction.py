"""화면 2 — 학생 1명의 정보를 입력해 중도탈락 위험을 확인한다."""

from __future__ import annotations

from typing import Any

import streamlit as st

from components import ui
from components.state import start_page
from rules import recommendation_rules as rules
from services.prediction_service import get_service
from utils.feature_mapping import (
    COLLAPSED_GROUPS,
    FIELD_GROUPS,
    UI_FIELDS,
    FieldSpec,
    StudentInput,
)

WIDGET_PREFIX = "in_"

#: 발표 중 값을 하나씩 바꾸지 않아도 되도록 준비한 예시 (더미 값이다).
#  적지 않은 항목은 StudentInput 의 기본값이 그대로 쓰인다.
PRESETS: dict[str, dict[str, Any]] = {
    "학업 위험 사례": dict(
        student_id="예시-A", age_at_enrollment=19, gender=1, major_field="공학·IT",
        attendance=1, displaced=1, admission_pathway="일반전형", application_order=1,
        admission_grade=118.0, tuition_fees_up_to_date=1, scholarship_holder=0, debtor=0,
        sem1_enrolled=6, sem1_approved=3, sem1_grade=10.4, sem1_without_evaluations=1,
        sem2_enrolled=6, sem2_approved=1, sem2_grade=8.2, sem2_without_evaluations=2,
    ),
    "경제 위험 사례": dict(
        student_id="예시-B", age_at_enrollment=21, gender=0, major_field="경영",
        attendance=1, displaced=0, admission_pathway="일반전형", application_order=0,
        admission_grade=131.0, tuition_fees_up_to_date=0, scholarship_holder=0, debtor=1,
        sem1_enrolled=6, sem1_approved=5, sem1_grade=13.1, sem1_without_evaluations=0,
        sem2_enrolled=6, sem2_approved=4, sem2_grade=12.4, sem2_without_evaluations=0,
    ),
    "복합 위험 사례": dict(
        student_id="예시-C", age_at_enrollment=30, gender=1, major_field="사회",
        attendance=0, displaced=1, admission_pathway="성인학습자 전형", application_order=3,
        admission_grade=118.0, tuition_fees_up_to_date=0, scholarship_holder=0, debtor=1,
        sem1_enrolled=6, sem1_approved=4, sem1_grade=11.2, sem1_without_evaluations=1,
        sem2_enrolled=6, sem2_approved=2, sem2_grade=8.6, sem2_without_evaluations=2,
    ),
    "안정 사례": dict(
        student_id="예시-D", age_at_enrollment=19, gender=0, major_field="보건",
        attendance=1, displaced=0, admission_pathway="일반전형", application_order=0,
        admission_grade=152.0, tuition_fees_up_to_date=1, scholarship_holder=1, debtor=0,
        sem1_enrolled=6, sem1_approved=6, sem1_grade=16.1, sem1_without_evaluations=0,
        sem2_enrolled=6, sem2_approved=6, sem2_grade=16.8, sem2_without_evaluations=0,
    ),
}


# ---------------------------------------------------------------------------
# 위젯
# ---------------------------------------------------------------------------

def _widget_key(spec: FieldSpec) -> str:
    return f"{WIDGET_PREFIX}{spec.key}"


def apply_values(values: dict[str, Any]) -> None:
    """입력 위젯의 값을 한 번에 채운다 (프리셋 / 목록에서 넘어온 학생)."""
    for spec in UI_FIELDS:
        if spec.key in values:
            st.session_state[_widget_key(spec)] = values[spec.key]
    st.session_state["prediction_student_id"] = str(values.get("student_id", "직접 입력"))


def init_defaults() -> None:
    """위젯 기본값을 session_state 에 한 번만 심는다.

    위젯에 value= 와 key= 를 동시에 주면 Streamlit 이 경고를 낸다. 값은 항상
    session_state 로만 관리하고 위젯은 key 만 받는다.
    """
    for spec in UI_FIELDS:
        st.session_state.setdefault(_widget_key(spec), spec.default)
    st.session_state.setdefault("prediction_student_id", "직접 입력")


def consume_prefill() -> None:
    """'학생 목록'에서 보낸 학생이 있으면 위젯을 만들기 전에 반영한다.

    이미 명단에서 본 학생이므로 입력값만 채우지 않고 결과까지 바로 띄운다.
    """
    student = st.session_state.pop("prefill_student", None)
    if student is None:
        return
    apply_values(student.to_ui_dict())
    st.session_state["prediction_last"] = student


def _render_field(spec: FieldSpec) -> Any:
    key = _widget_key(spec)

    if spec.kind == "text_select":
        choices = list(spec.choices or ())
        if st.session_state.get(key) not in choices:
            st.session_state[key] = spec.default
        labels = spec.labels or {}
        return st.selectbox(
            spec.label,
            options=choices,
            format_func=lambda value: labels.get(value, value),
            key=key,
            help=spec.help or None,
        )

    if spec.kind == "select":
        options = list(spec.options or {})
        if st.session_state.get(key) not in options:
            st.session_state[key] = spec.default
        return st.selectbox(
            spec.label,
            options=options,
            format_func=lambda code: (spec.options or {}).get(code, str(code)),
            key=key,
            help=spec.help or None,
        )

    cast = type(spec.default)
    if spec.kind == "slider":
        st.session_state[key] = cast(
            min(max(st.session_state.get(key, spec.default), spec.minimum), spec.maximum)
        )
        return st.slider(
            spec.label,
            min_value=cast(spec.minimum),
            max_value=cast(spec.maximum),
            step=cast(spec.step or 1),
            format="%.1f" if cast is float else None,
            key=key,
            help=spec.help or None,
        )

    st.session_state[key] = int(
        min(max(st.session_state.get(key, spec.default), spec.minimum), spec.maximum)
    )
    return st.number_input(
        spec.label,
        min_value=int(spec.minimum),
        max_value=int(spec.maximum),
        step=int(spec.step or 1),
        key=key,
        help=spec.help or None,
    )


def _render_group(group: str, *, with_title: bool = True) -> dict[str, Any]:
    if with_title:
        st.markdown(f'<div class="card-title">{group}</div>', unsafe_allow_html=True)
    values: dict[str, Any] = {}
    for spec in UI_FIELDS:
        if spec.group == group:
            values[spec.key] = _render_field(spec)
    return values


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

start_page(
    "학생 위험 예측",
    "학생 한 명의 정보를 입력하면 중도탈락 위험도와 위험요인, 그에 대응하는 "
    "교내 지원 프로그램을 함께 보여줍니다.",
)

consume_prefill()
init_defaults()

service = get_service()
ui.prototype_banner(service)

# -- 예시 불러오기 (폼 밖: 누르면 즉시 값이 채워져야 한다) ----------------------
ui.section("예시 불러오기", "발표 중 값을 하나씩 바꾸지 않도록 준비한 더미 입력값입니다.")
preset_columns = st.columns(len(PRESETS))
for column, (name, preset_values) in zip(preset_columns, PRESETS.items()):
    with column:
        if st.button(name, width="stretch", key=f"preset_{name}"):
            apply_values(preset_values)
            st.rerun()

# -- 입력 폼 ------------------------------------------------------------------
ui.section(
    "학생 정보 입력",
    f"팀 전처리(Model B)가 요구하는 입력 {len(UI_FIELDS)}개입니다. "
    "이수율·재정위험점수 등 파생변수 5종은 아래 값에서 자동으로 계산되므로 직접 입력하지 않습니다. "
    "모든 항목에 기본값이 채워져 있어, 바꾸고 싶은 값만 손대면 됩니다.",
)

with st.form("prediction_form", border=True):
    values: dict[str, Any] = {}

    top = st.columns(3, gap="large")
    for column, group in zip(top, ("기본 정보", "입학 정보", "경제 정보")):
        with column:
            values.update(_render_group(group))

    st.divider()
    bottom = st.columns(2, gap="large")
    for column, group in zip(bottom, ("1학기 학업", "2학기 학업")):
        with column:
            values.update(_render_group(group))

    st.divider()
    for group in FIELD_GROUPS:
        if group not in COLLAPSED_GROUPS:
            continue
        with st.expander(f"{group} — 모델은 쓰지만 담당자가 매번 바꿀 값은 아닙니다", expanded=False):
            columns = st.columns(2, gap="large")
            specs = [s for s in UI_FIELDS if s.group == group]
            for index, spec in enumerate(specs):
                with columns[index % 2]:
                    values[spec.key] = _render_field(spec)

    st.write("")
    submitted = st.form_submit_button("분석하기", type="primary", width="stretch")

if submitted:
    st.session_state["prediction_last"] = StudentInput(
        student_id=st.session_state.get("prediction_student_id", "직접 입력"),
        **values,
    )

student = st.session_state.get("prediction_last")
if student is None:
    st.info("학생 정보를 입력하고 **분석하기** 를 누르면 예측 결과가 여기에 표시됩니다.")
    st.stop()

for problem in student.validate():
    st.warning(problem)

try:
    result = service.predict(student)
except Exception as error:  # 예측기 교체 중 오류가 나도 앱은 살아 있어야 한다.
    st.error(f"예측에 실패했습니다: {error}")
    st.stop()

recommendation = rules.evaluate(student, result)

ui.section("예측 결과", f"대상: {student.student_id}")
ui.result_panel(student, result, recommendation, show_summary=True)

with st.expander("이 예측에 쓰인 파생변수 5종 보기", expanded=False):
    st.dataframe(
        {
            "파생변수": [
                "sem1_approval_rate",
                "sem2_approval_rate",
                "grade_change",
                "zero_enrolled_1st_sem",
                "financial_risk_score",
            ],
            "값": [
                f"{student.sem1_approval_rate:.3f}",
                f"{student.sem2_approval_rate:.3f}",
                f"{student.grade_change:+.1f}",
                str(student.zero_enrolled_1st_sem),
                f"{student.financial_risk_score} / 3",
            ],
            "계산 방법": [
                "1학기 이수 ÷ 수강 (수강 0이면 0)",
                "2학기 이수 ÷ 수강 (수강 0이면 0)",
                "2학기 평점 − 1학기 평점",
                "1학기 수강 과목 0 여부",
                "등록금 미납 + 채무 + 장학금 미수혜",
            ],
        },
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "계산 정의는 팀 전처리 노트북(notebooks/preprocess.ipynb)과 같습니다. "
        "정의를 바꾸려면 utils/feature_mapping.py 의 StudentInput 한 곳만 고칩니다."
    )
