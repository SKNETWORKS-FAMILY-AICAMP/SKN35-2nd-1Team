"""
대학생 중도탈락 위험 예측 및 맞춤 지원 시스템 — Streamlit 진입점.

    실행:  streamlit run app/app.py

이 파일은 **전역 설정과 라우팅만** 한다. 화면 하나하나는 pages/ 아래 독립된 파일이다.

    pages/0_home.py        시작화면 (서비스 소개 · 데이터 출처 · 확장 가능성)
    pages/1_dashboard.py   전체 현황 대시보드
    pages/2_prediction.py  학생 1명 위험 예측
    pages/3_students.py    학생 목록 · 상세

    components/  화면 공통 UI·테마·지구본·상태
    services/    예측 계층 (더미 ↔ 실제 모델 교체 지점)
    rules/       규칙 기반 지원 추천 엔진
    utils/       팀 전처리 스키마 매핑 · 더미 데이터

왜 `st.navigation` 인가
    Streamlit 은 pages/ 폴더를 자동 멀티페이지로 인식해 라우팅을 가져가 버린다.
    `st.navigation` 을 쓰면 그 자동 동작 대신 **사이드바 구성과 화면 간 값 전달을
    직접 통제**하면서도, 화면마다 파일이 하나씩 분리된 구조를 그대로 얻는다.

현재 상태: 프로토타입(Dummy Mode). 학습된 모델은 아직 연결되지 않았다.
모델 연결 지점은 services/real_predictor.py 와
services/prediction_service.py 의 USE_REAL_MODEL 스위치 두 곳뿐이다.
"""

from __future__ import annotations

import streamlit as st

from components.state import (
    PAGE_DASHBOARD,
    PAGE_HOME,
    PAGE_PREDICTION,
    PAGE_STUDENTS,
)
from components.theme import COLORS
from services.prediction_service import get_service
from utils.schema import schema_available

st.set_page_config(
    page_title="중도탈락 위험 예측 시스템",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = [
    st.Page(PAGE_HOME, title="시작", icon=":material/home:", default=True),
    st.Page(PAGE_DASHBOARD, title="대시보드", icon=":material/dashboard:"),
    st.Page(PAGE_PREDICTION, title="학생 위험 예측", icon=":material/person_search:"),
    st.Page(PAGE_STUDENTS, title="학생 목록", icon=":material/list:"),
]


def _sidebar() -> None:
    """화면 이동 위젯 아래에 붙는 공통 정보. 숫자의 출처를 항상 사이드바에 남긴다."""
    with st.sidebar:
        st.divider()

        service = get_service()
        schema_line = (
            "팀 전처리 스키마 연결됨<br>(data/processed/feature_schema.json)"
            if schema_available()
            else "<b style='color:#C2453D'>스키마 파일 없음</b><br>"
            "data/processed/feature_schema.json 을 확인하세요"
        )
        st.markdown(
            f'<div style="font-size:.78rem;color:{COLORS["muted"]};line-height:1.7">'
            f'<b style="color:{COLORS["ink_soft"]}">예측기</b><br>{service.model_label}<br><br>'
            f'<b style="color:{COLORS["ink_soft"]}">전처리</b><br>{schema_line}<br><br>'
            f'<b style="color:{COLORS["ink_soft"]}">화면 데이터</b><br>'
            "UCI 데이터셋의 컬럼 구조를 따른 합성 더미 80명 (원본 데이터가 아님)</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption(
            "이 시스템은 위험요인에 대응하는 지원 프로그램을 연결할 뿐, "
            "중도탈락을 단정하거나 예방을 보장하지 않습니다."
        )


navigation = st.navigation(PAGES, position="sidebar")
_sidebar()
navigation.run()
