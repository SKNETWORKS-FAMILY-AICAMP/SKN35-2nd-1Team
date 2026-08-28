"""
학생 한 명의 상세 분석 — **두 화면이 공유하는 단 하나의 구현.**

학생 목록(찾는 화면)과 집중관리 대상(처리하는 화면)이 같은 학생을 보여준다.
각자 그리면 한쪽만 고쳐지는 사고가 반드시 난다. 그래서 컴포넌트로 뺐다.
(화면 파일끼리는 import 할 수 없다 — 파일 이름이 숫자로 시작해서 모듈이 아니다.)

세로로 다 쌓으면 한 화면에 블록이 열 개를 넘어가고, 그러면 담당자가 매일 쓰는
**조치**가 근거·시뮬레이션에 묻힌다. 셋으로 접고 기본값을 조치로 둔다.
"""

from __future__ import annotations

import streamlit as st

from components import ui, whatif
from services.prediction_service import get_service


def render(row, *, key: str) -> None:
    """`RosterRow` 하나를 조치 / 위험 예측 분석 / What-if 세 탭으로."""
    tabs = st.tabs(["조치", "위험 예측 분석", "What-if"])
    suffix = f"{key}_{row.student.student_id}"

    with tabs[0]:
        ui.action_panel(row.student, row.result, row.recommendation)
        ui.spacer(14)
        ui.case_downloads(row.student, row.result, row.recommendation, key=suffix)

    with tabs[1]:
        ui.evidence_panel(row.student, row.result, row.recommendation)

    with tabs[2]:
        whatif.render(row.student, row.result, row.recommendation, get_service(),
                      key=suffix, show_heading=False)
