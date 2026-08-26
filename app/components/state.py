"""
화면 사이에서 공유하는 상태와 캐시.

멀티페이지에서는 페이지를 옮길 때마다 스크립트가 처음부터 다시 실행된다.
명단 885명 예측을 그때마다 다시 하면 화면 전환이 눈에 띄게 느려지므로 여기서 한 번만 계산한다.
"""

from __future__ import annotations

import streamlit as st

from components.theme import inject_css
from services.prediction_service import get_service
from services.roster import Roster, build_roster
from utils.feature_mapping import StudentInput

#: 화면 파일 경로 — st.switch_page 가 이 값을 쓴다. 파일을 옮기면 여기만 고친다.
PAGE_HOME = "pages/0_home.py"
PAGE_DASHBOARD = "pages/1_dashboard.py"
PAGE_PREDICTION = "pages/2_prediction.py"
PAGE_STUDENTS = "pages/3_students.py"


@st.cache_resource(show_spinner="학생 명단을 예측하는 중입니다…")
def cached_roster() -> Roster:
    """명단 전체 예측은 페이지를 옮길 때마다 다시 할 필요가 없다.

    `cache_resource` 인 이유: 예측기 인스턴스와 묶인 객체라 프로세스당 하나면 충분하다.
    **예측기를 바꿨을 때는** 앱을 재시작하거나 우측 상단 메뉴에서 Clear cache 를 쓴다 —
    캐시가 남아 옛 예측기의 결과를 계속 보여주면 안 되기 때문이다.
    """
    return build_roster(get_service())


def roster_source() -> tuple[str, bool]:
    """사이드바가 쓰는 (출처 문구, 실데이터 여부).

    명단 전체를 만들지 않고 파일 존재만 본다 — 사이드바 때문에 885명 예측이
    시작되면 첫 화면이 느려진다.
    """
    from utils.real_data import available_file

    path = available_file()
    if path is not None:
        return f"data/processed/{path.name}", True
    return "합성 더미 명단 (원본 데이터 아님)", False


def start_page(title: str, subtitle: str = "", meta: str = "") -> None:
    """모든 화면이 첫 줄에서 부른다. 스타일 주입 + 헤더를 한 번에 처리한다."""
    from components import ui

    inject_css()
    if title:
        ui.page_header(title, subtitle, meta)


def send_to_prediction(student: StudentInput) -> None:
    """'학생 목록'에서 고른 학생을 예측 화면으로 넘긴다.

    위젯 값을 직접 바꾸지 않고 요청만 남긴다 — 예측 화면이 자기 위젯을 만들기 전에
    이 값을 읽어서 반영한다. (위젯 생성 후 key 를 바꾸면 Streamlit 이 예외를 던진다.)
    """
    st.session_state["prefill_student"] = student
