"""
대학생 중도탈락 위험 예측 및 맞춤 지원 시스템 — Streamlit 진입점.

    실행:  streamlit run app/app.py

이 파일은 **전역 설정과 라우팅만** 한다. 화면 하나하나는 views/ 아래 독립된 파일이다.

    views/0_home.py        메인 (소개 · 핵심 수치 · 바로가기)
    views/1_dashboard.py   대시보드 (규모 → 성격, 도넛 넷)
    views/2_students.py    학생 목록 (좁히기 → 상세 → 직접 입력)
    views/3_risk_list.py   집중관리 대상 (우선 처리 명단 · 상담 진행 상태)

    components/  디자인 시스템(theme) · 공통 UI · 지구본 · 상태
    services/    예측 계층 (더미 ↔ 실제 모델 교체 지점)
    rules/       규칙 기반 지원 추천 엔진
    utils/       팀 전처리 스키마 매핑 · 실데이터 복원 · 더미 데이터

왜 `st.navigation` 인가
    Streamlit 은 views/ 폴더를 자동 멀티페이지로 인식해 라우팅을 가져가 버린다.
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
    PAGE_RISK,
    PAGE_STUDENTS,
    roster_size,
)
from components.theme import inject_css

st.set_page_config(
    page_title="Student Dropout Intelligence",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = [
    st.Page(PAGE_HOME, title="시작", icon=":material/home:", default=True),
    st.Page(PAGE_DASHBOARD, title="대시보드", icon=":material/monitoring:"),
    st.Page(PAGE_STUDENTS, title="학생 목록", icon=":material/table_rows:"),
    st.Page(PAGE_RISK, title="집중관리 대상", icon=":material/priority_high:"),
]


def _block_auto_translate() -> None:
    """브라우저 자동 번역을 막는다.

    화면에 영문(Student Dropout Intelligence, Prototype Mode …)과 한글이 섞여 있어서
    Chrome 이 페이지를 영어로 판정하고 한국어로 자동 번역해 버린다. 그러면
    **이미 한국어인 문장까지 다시 번역돼** "학생 목록" 이 "당신 목록" 이 되는 식으로 깨진다.
    발표 PC 에서 그대로 나면 손쓸 방법이 없으므로 문서 속성으로 미리 막는다.

    Streamlit 은 <script> 를 살균하므로 같은 오리진 iframe 에서 부모 문서를 고친다.
    실패해도 화면은 멀쩡하다 — 번역 차단만 안 될 뿐이다.
    """
    render_iframe = getattr(st, "iframe", None)
    if render_iframe is None:  # 구버전 대비
        from streamlit.components.v1 import html as render_iframe

    render_iframe(
        """
<script>
(function () {
  try {
    var doc = window.parent.document;
    doc.documentElement.lang = "ko";
    doc.documentElement.translate = false;
    doc.documentElement.classList.add("notranslate");
    var meta = doc.querySelector('meta[name="google"]');
    if (!meta) {
      meta = doc.createElement("meta");
      meta.name = "google";
      doc.head.appendChild(meta);
    }
    meta.content = "notranslate";
    // 사이드바 "접힘" 기억을 지운다. 표지에서는 사이드바를 만들지 않는데, 그걸 브라우저가
    // "사용자가 접었다"로 저장해 두면 **다른 화면에서도 계속 접힌 채로** 열린다.
    // 지우기만 한다 — 강제로 펼치면 사용자가 방금 접은 것까지 되돌려 버린다.
    var store = window.parent.localStorage;
    for (var i = store.length - 1; i >= 0; i--) {
      var name = store.key(i);
      if (name && name.indexOf("stSidebarCollapsed") === 0) store.removeItem(name);
    }
  } catch (e) { /* 다른 오리진이면 조용히 포기한다 */ }
})();
</script>
""",
        height=1,
    )


def _sidebar() -> None:
    """브랜드 · 화면 이동 · 명단 규모 한 줄.

    모드/전처리/출처 같은 개발 메모는 두지 않는다 — 쓰는 사람이 알아야 하는 것은
    지금 몇 명을 보고 있는가와 어디로 가는가뿐이다.
    """
    with st.sidebar:
        st.markdown(
            '<div class="sb-brand">'
            '<div class="n">Student Dropout Intelligence</div>'
            '<div class="s">SKN35 · 2ND TEAM PROJECT</div></div>',
            unsafe_allow_html=True,
        )
        for page in PAGES:
            st.page_link(page, label=page.title, icon=page.icon)

        size = roster_size()
        st.markdown(
            f'<div class="sb-foot"><div class="k">Students</div>'
            f'<div class="v">{size:,}명</div>'
            f'<div class="d">위험도 재계산 완료</div></div>',
            unsafe_allow_html=True,
        )


# st.navigation 을 진입점의 첫 출력으로 둔다 — 라우팅을 먼저 확정한 뒤 스타일을 넣는다.
# (화면 폴더 이름이 pages/ 가 아니라 views/ 인 이유는 README 1장 참고)
#
# position="hidden" 으로 두고 사이드바를 **직접** 그린다.
#     시작화면은 표지라서 사이드바가 없어야 하는데, `position` 은 어느 화면인지 알기
#     전에 정해야 하는 값이다. 네비게이션을 우리가 그리면 `navigation` 이 정해진 뒤에
#     "표지면 사이드바를 아예 만들지 않는다" 를 확정할 수 있다.
#     CSS 로 감추는 방법은 쓰지 않는다 — 감춘 사이드바를 Streamlit 이 접힘 상태로
#     기억해서 **다음 화면에서도 펼쳐지지 않는다.**
navigation = st.navigation(PAGES, position="hidden")
inject_css()
_block_auto_translate()
if navigation.title != "시작":
    _sidebar()
navigation.run()
