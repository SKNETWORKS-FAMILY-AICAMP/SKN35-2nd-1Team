"""화면 5 — 예비학생 예측.

명단에 없는 학생을 **손으로 넣어** 예측해 보는 화면이다. 원래는 학생 목록 아래
접혀 있었는데, 하는 일이 다르다 — 명단은 **있는 학생을 찾는 곳**이고 여기는
**없는 학생을 넣어 보는 곳**이다. 섞어 두면 명단 화면이 길어지기만 한다.

입력 항목과 검증은 `components/manual_input.py` 가 소유한다. 이 파일은 그 결과를
받아 예측하고 같은 결과 패널을 그릴 뿐이다.
"""

from __future__ import annotations

import streamlit as st

from components import manual_input, ui
from components.state import start_page
from rules import recommendation_rules as rules
from services.prediction_service import get_service

# 폼 값 준비는 **어떤 위젯보다 먼저** 끝내야 한다 (다른 화면에서 값을 보내올 수 있다).
manual_input.prepare()

service = get_service()

start_page(
    "예비학생 예측",
    # "명단에 없는 학생의 값을 직접 넣어 위험도와 지원 방향을 확인합니다.",
    # meta=(
    #     '<div class="ds-eyebrow">Manual</div>'
    #     '<div class="ds-sub" style="margin-top:4px">단일 학생 예측</div>'
    # ),
)

student = manual_input.render()

if student is not None:
    for problem in student.validate():
        st.warning(problem)
    try:
        result = service.predict(student)
    except Exception as error:   # 예측기 교체 중 오류가 나도 화면은 살아 있어야 한다.
        ui.empty_state("예측을 수행할 수 없습니다", str(error))
    else:
        recommendation = rules.evaluate(student, result)
        ui.spacer(12)
        ui.section("분석 결과", f"대상 · {student.student_id}")
        ui.result_panel(student, result, recommendation, show_summary=True)
        ui.spacer(10)
        ui.case_downloads(student, result, recommendation, key="manual")
