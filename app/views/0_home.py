"""화면 0 — 시작화면.

이 화면은 **한 장짜리 표지**다. 캠퍼스 사진 한 장 위에 제품을 말하는 한 문장,
지금 규모를 말하는 카드 두 장, 갈 곳을 여는 버튼 셋. 그 아래로는 아무것도 두지 않는다 —
설명은 각 화면이 자기 자리에서 한다.

사이드바는 이 화면에만 없다 — 표지에서 메뉴가 먼저 보이면 표지가 아니라 관리자
화면이다. 사이드바를 만들지 말지는 진입점(`app.py`)이 정한다.
"""

from __future__ import annotations

import streamlit as st

from components import ui
from components.globe import render as render_globe
from components.state import (
    PAGE_DASHBOARD,
    PAGE_RISK,
    PAGE_STUDENTS,
    cached_roster,
    start_page,
)
from components.theme import inject_hero_photo

start_page("")
inject_hero_photo()

# 표지에 세울 숫자는 명단에서 바로 센다. 히어로 글자가 먼저 그려지고 나서 계산된다.
frame = cached_roster().frame
total = len(frame)
high = int((frame["위험등급"] == "HIGH").sum())
dropout = int((frame["예측(원본)"] == "Dropout").sum())

with st.container(key="hero"):
    # 왼쪽에 문장, 오른쪽에 지구본. 지구본은 "이 데이터가 어디서 왔는가"를
    # 한 장면으로 답한다 — 사진 위에 비치는 유리구슬로 얹는다.
    text_col, globe_col = st.columns([1.15, 0.85], gap="large")

    with text_col:
        st.markdown(
            f"""<div class="hero">
      <div class="brand">Student Dropout Intelligence · SKN35 2nd Team Project</div>
      <div class="hero-pills"><span class="hero-pill"><span class="dot"></span>
        학생 {total:,}명 · 위험도 재계산 완료</span></div>
      <h1>대학생 중도탈락<br>위험 예측 시스템</h1>
      <p class="hero-lead">학업·경제·입학 배경 데이터로 중도탈락 위험을
         <b style="color:#EAF2FC">학기 중에 조기 식별</b>하고, 그 학생의 위험요인에 대응하는
         교내 지원 방향까지 제안합니다. 예측값 하나를 띄우고 끝내지 않고
         <b style="color:#EAF2FC">왜 위험한가</b>와
         <b style="color:#EAF2FC">그래서 무엇을 할 것인가</b>를 함께 답합니다.</p>
    </div>""",
            unsafe_allow_html=True,
        )
        with st.container(key="hero_cta", horizontal=True, gap="small"):
            if st.button("대시보드 열기", type="primary", key="home_dashboard"):
                st.switch_page(PAGE_DASHBOARD)
            if st.button("학생 목록 보기", key="home_students"):
                st.switch_page(PAGE_STUDENTS)

    with globe_col:
        render_globe(height=430)

    ui.spacer(22)

    # 카드 두 장은 **같은 구조**로 만든다 — 설명 + 버튼 하나.
    # 구조가 같아야 높이가 저절로 맞고, 둘 다 누르면 화면이 넘어간다.
    card_col, alert_col = st.columns([1, 1.5], gap="medium")
    with card_col:
        with st.container(key="hero_stat"):
            st.markdown(
                f"""<div class="g-lab">전체 학생 수</div>
            <div class="g-val">{total:,}<span class="u">명</span></div>
            <div class="g-cap">이번 학기 재학생 명단</div>
            <div class="g-split">
              <div><div class="k">고위험 HIGH</div><div class="v">{high:,}명</div></div>
              <div><div class="k">예측 Dropout</div>
                <div class="v">{dropout / total * 100:.1f}%</div></div>
            </div>""",
                unsafe_allow_html=True,
            )
            if st.button("학생 목록 열기", key="home_students_card"):
                st.switch_page(PAGE_STUDENTS)

    with alert_col:
        with st.container(key="hero_alert"):
            st.markdown(
                f"""<div class="g-head">
              <div class="g-ico">!</div>
              <div class="g-title">지금 확인이 필요한 학생</div>
            </div>
            <div class="g-body">중도탈락 확률 60% 이상인 <b>HIGH 등급 {high:,}명</b>이 명단에 있습니다.
              위험도 순으로 줄을 세운 화면에서 위험요인 · 권장 조치 · 상담 진행 상태까지
              한 자리에서 남길 수 있습니다.</div>""",
                unsafe_allow_html=True,
            )
            if st.button(f"고위험군 관리 ({high:,})", key="home_risk"):
                st.switch_page(PAGE_RISK)
