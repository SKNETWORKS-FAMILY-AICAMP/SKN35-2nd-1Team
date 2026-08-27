"""
What-if — 추천의 근거를 **말이 아니라 움직임으로** 보여주는 화면 조각.

값을 하나 움직이면 확률과 발동 규칙이 그 자리에서 다시 계산된다. "2학기 이수율이
낮아서 학습지원을 연결했다" 는 설명은, 이수율을 올렸을 때 **그 규칙이 실제로 빠지는
것**을 보여줄 때 비로소 증명된다.

이 파일이 하지 않는 것
    새 계산을 만들지 않는다. 학생 사본을 만들어 기존 `service.predict()` 와
    `rules.evaluate()` 를 한 번 더 부를 뿐이다. 시뮬레이션 전용 로직을 따로 두면
    화면과 예측이 갈라지고, 그 순간 What-if 는 아무것도 증명하지 못한다.

🔴 인과에 대하여
    이것은 **개입의 효과가 아니다.** 등록금을 완납시키면 위험이 내려간다는 그림은
    "완납한 학생들이 통계적으로 덜 이탈했다" 는 뜻이지 "완납시키면 이탈을 막는다" 가
    아니다. 규칙 엔진의 DISCLAIMER 가 추천의 인과를 부정한다면, 여기 WHATIF_NOTE 는
    시뮬레이션의 인과를 부정한다. 둘 다 필요하고, 둘 다 화면에 붙는다.
"""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from components import ui
from components.theme import COLORS, RISK_COLORS
from rules import recommendation_rules as rules
from services.predictor import PredictionResult
from services.prediction_service import PredictionService
from utils.feature_mapping import StudentInput

WHATIF_NOTE = (
    "<b>개입의 효과가 아닙니다.</b> 입력값이 달랐다면 모델이 어떤 확률을 냈을지, "
    "그리고 어떤 규칙이 발동했을지를 보여줍니다. 데이터가 말하는 것은 "
    "<b>상관</b>이지 인과가 아니므로, 지원 프로그램을 제공하면 이만큼 위험이 "
    "내려간다는 뜻으로 읽으면 안 됩니다."
)

#: 조작 대상. **화면 입력으로 바꿀 수 있고 지원 프로그램과 직접 이어지는 값**만 고른다.
#  나이·전형처럼 되돌릴 수 없는 값을 슬라이더로 만들면 시뮬레이션이 공상이 된다.
CONTROLS = ("sem2_approved", "sem2_grade", "tuition_fees_up_to_date", "scholarship_holder")


def _reset(prefix: str) -> None:
    for name in CONTROLS:
        st.session_state.pop(prefix + name, None)


def render(
    student: StudentInput,
    result: PredictionResult,
    recommendation: rules.RecommendationSet,
    service: PredictionService,
    *,
    key: str,
    show_heading: bool = True,
) -> None:
    """학생 1명의 What-if 패널.

    위젯 key 에 학생 ID 를 넣는다 — 다른 학생으로 옮겼을 때 앞 학생의 슬라이더 값이
    남아 있으면 **남의 값으로 시뮬레이션한 결과**를 보게 된다.
    """
    prefix = f"wi_{key}_"

    if show_heading:
        ui.section(
            "What-if — 값을 움직이면 추천이 어떻게 바뀌는가",
            "추천의 근거가 된 값을 직접 바꿔 보면, 그 규칙이 실제로 빠지는지 확인할 수 있습니다.",
        )
    ui.banner(
        "Simulation",
        WHATIF_NOTE,
        foreground=COLORS["primary"],
        background=COLORS["primary_soft"],
        border=COLORS["primary_line"],
    )
    ui.spacer(10)

    with st.container(border=True):
        col1, col2, col3 = st.columns([1.3, 1.3, 1.1], gap="large")
        with col1:
            approved = st.slider(
                "2학기 이수 과목 수",
                min_value=0,
                max_value=max(int(student.sem2_enrolled), 1),
                value=int(student.sem2_approved),
                key=prefix + "sem2_approved",
                help=f"현재 {student.sem2_approved}/{student.sem2_enrolled}과목 "
                     f"(이수율 {student.sem2_approval_rate:.0%})",
            )
        with col2:
            grade = st.slider(
                "2학기 평균 성적",
                min_value=0.0,
                max_value=20.0,
                value=float(student.sem2_grade),
                step=0.1,
                format="%.1f",
                key=prefix + "sem2_grade",
                help="원본 0~20 기준",
            )
        with col3:
            tuition = st.toggle(
                "등록금 완납",
                value=student.tuition_fees_up_to_date == 1,
                key=prefix + "tuition_fees_up_to_date",
            )
            scholarship = st.toggle(
                "장학금 수혜",
                value=student.scholarship_holder == 1,
                key=prefix + "scholarship_holder",
            )

    simulated = replace(
        student,
        sem2_approved=int(approved),
        sem2_grade=float(grade),
        tuition_fees_up_to_date=int(tuition),
        scholarship_holder=int(scholarship),
    )

    if simulated == student:
        ui.spacer(10)
        ui.empty_state(
            "아직 바꾼 값이 없습니다",
            "위 값을 움직이면 중도탈락 확률과 발동 규칙이 어떻게 달라지는지 여기에 나타납니다.",
        )
        return

    try:
        after = service.predict(simulated)
    except Exception as error:      # 예측기 교체 중이어도 상세 화면은 살아 있어야 한다.
        ui.spacer(10)
        ui.empty_state("시뮬레이션을 수행할 수 없습니다", str(error))
        return

    after_recommendation = rules.evaluate(simulated, after)

    ui.spacer(12)
    ui.whatif_delta(result, after, recommendation, after_recommendation)

    ui.spacer(8)
    if st.button("원래 값으로 되돌리기", key=prefix + "reset", width="stretch"):
        _reset(prefix)
        st.rerun()


_KEEP = RISK_COLORS  # 위험등급 색을 이 모듈 경유로도 얻을 수 있게 남긴다.
