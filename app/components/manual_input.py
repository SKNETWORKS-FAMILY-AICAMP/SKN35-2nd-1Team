"""
직접 입력 — 명단에 없는 학생을 손으로 넣어 예측한다.

원래 독립 화면(`학생 위험 예측`)이었던 것을 **학생 목록 안으로 흡수**했다.
같은 결과 화면을 두 곳에서 따로 그릴 이유가 없고, 화면 수가 늘면 "어디서 뭘 하는지"가
흐려지기 때문이다. 명단에서 고르는 것과 손으로 넣는 것은 **입력 방법의 차이**일 뿐이다.

입력이 32개나 되지만 **설문지처럼 보이면 실패다.** 그래서 네 묶음으로 나눠 탭에 넣는다 —
한 번에 보이는 것은 최대 9개다.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from components.theme import COLORS
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
# PRESETS: dict[str, dict[str, Any]] = {
#     "HIGH · 복합 위험": dict(
#         student_id="예시-HIGH", age_at_enrollment=30, gender=1, major_field="사회",
#         attendance=0, displaced=1, admission_pathway="성인학습자 전형", application_order=3,
#         admission_grade=118.0, tuition_fees_up_to_date=0, scholarship_holder=0, debtor=1,
#         sem1_enrolled=6, sem1_approved=3, sem1_grade=10.8, sem1_without_evaluations=1,
#         sem2_enrolled=6, sem2_approved=1, sem2_grade=7.9, sem2_without_evaluations=2,
#     ),
#     "MEDIUM · 학업 부진": dict(
#         student_id="예시-MEDIUM", age_at_enrollment=20, gender=1, major_field="공학·IT",
#         attendance=1, displaced=1, admission_pathway="일반전형", application_order=1,
#         admission_grade=124.0, tuition_fees_up_to_date=1, scholarship_holder=0, debtor=0,
#         sem1_enrolled=6, sem1_approved=4, sem1_grade=11.6, sem1_without_evaluations=0,
#         sem2_enrolled=6, sem2_approved=2, sem2_grade=10.2, sem2_without_evaluations=1,
#     ),
#     "MEDIUM · 재정 위험": dict(
#         student_id="예시-FIN", age_at_enrollment=21, gender=0, major_field="경영",
#         attendance=1, displaced=0, admission_pathway="일반전형", application_order=0,
#         admission_grade=131.0, tuition_fees_up_to_date=0, scholarship_holder=0, debtor=1,
#         sem1_enrolled=6, sem1_approved=5, sem1_grade=13.1, sem1_without_evaluations=0,
#         sem2_enrolled=6, sem2_approved=4, sem2_grade=12.4, sem2_without_evaluations=0,
#     ),
#     "LOW · 안정": dict(
#         student_id="예시-LOW", age_at_enrollment=19, gender=0, major_field="보건",
#         attendance=1, displaced=0, admission_pathway="일반전형", application_order=0,
#         admission_grade=152.0, tuition_fees_up_to_date=1, scholarship_holder=1, debtor=0,
#         sem1_enrolled=6, sem1_approved=6, sem1_grade=16.1, sem1_without_evaluations=0,
#         sem2_enrolled=6, sem2_approved=6, sem2_grade=16.8, sem2_without_evaluations=0,
#     ),
# }


def _key(spec: FieldSpec) -> str:
    return f"{WIDGET_PREFIX}{spec.key}"


def apply_values(values: dict[str, Any]) -> None:
    for spec in UI_FIELDS:
        if spec.key in values:
            st.session_state[_key(spec)] = values[spec.key]
    st.session_state["manual_student_id"] = str(values.get("student_id", "직접 입력"))


def prepare() -> None:
    """위젯을 만들기 **전에** 부른다.

    기본값 심기와 '명단에서 보낸 학생' 반영을 한 곳에서 끝낸다. 위젯이 생긴 뒤에
    session_state 를 건드리면 Streamlit 이 예외를 던지므로 순서가 계약이다.
    위젯에 `value=` 와 `key=` 를 같이 주면 경고가 나므로 값은 항상 session_state 로만 관리한다.
    """
    for spec in UI_FIELDS:
        st.session_state.setdefault(_key(spec), spec.default)
    st.session_state.setdefault("manual_student_id", "직접 입력")

    student = st.session_state.pop("prefill_student", None)
    if student is not None:
        apply_values(student.to_ui_dict())
        st.session_state["manual_last"] = student


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


def render() -> StudentInput | None:
    """예시 버튼 + 입력 폼. 분석을 누른 뒤라면 그 학생을 돌려준다.

    `prepare()` 가 이미 불려 있어야 한다 — 이 함수는 위젯을 만든다.
    """
    # st.markdown(
    #     '<div class="ds-caption">발표용으로 준비한 입력값입니다. 실제 학생 기록이 아닙니다.</div>',
    #     unsafe_allow_html=True,
    # )
    # preset_cols = st.columns(len(PRESETS), gap="small")
    # for col, (name, values) in zip(preset_cols, PRESETS.items()):
    #     with col:
    #         if st.button(name, width="stretch", key=f"preset_{name}"):
    #             apply_values(values)
    #             st.rerun()

    current_id = st.session_state.get("manual_student_id", "직접 입력")
    if current_id != "직접 입력":
        st.markdown(
            f'<div class="ds-caption" style="margin-top:2px">현재 불러온 값 · '
            f'<b style="color:{COLORS["primary"]}">{current_id}</b> — '
            "아래에서 바꾸면 그대로 다시 예측합니다.</div>",
            unsafe_allow_html=True,
        )

    with st.form("manual_form", border=True):
        values: dict[str, Any] = {}
        tabs = st.tabs([name for name, _, _ in TABS])
        for tab, (name, desc, groups) in zip(tabs, TABS):
            with tab:
                st.markdown(f'<div class="ds-caption" style="margin-bottom:10px">{desc}</div>',
                            unsafe_allow_html=True)
                values.update(_render_groups(groups))

        st.divider()
        submitted = st.form_submit_button("위험도 분석", type="primary", width="stretch")

    if submitted:
        st.session_state["manual_last"] = StudentInput(
            student_id=st.session_state.get("manual_student_id", "직접 입력"), **values
        )

    return st.session_state.get("manual_last")
