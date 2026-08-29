"""화면 0 — 시작화면.

이 화면은 **한 장짜리 표지**다. 캠퍼스 사진과 지구본 위에 제품을 말하는 한 문장,
지금 규모를 말하는 숫자 셋, 갈 곳을 여는 버튼. 그 아래로는 아무것도 두지 않는다 —
설명은 각 화면이 자기 자리에서 한다.

사이드바는 이 화면에만 없다 — 표지에서 메뉴가 먼저 보이면 표지가 아니라 관리자
화면이다. 대신 **오른쪽 위에 이동 링크**를 둔다 (사이드바를 만들지 말지는 `app.py` 가 정한다).

지구본은 이제 콘텐츠 옆이 아니라 **배경**이다. 절대 위치로 오른쪽에 얹고 클릭은
통과시킨다 — 표지에서 만지는 물건이 아니라 분위기를 만드는 물건이기 때문이다.
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
from components.theme import RISK_COLORS, inject_hero_photo
from services.predictor import RISK_LABELS_KO

start_page("")
inject_hero_photo()

# 표지에 세울 숫자는 명단에서 바로 센다. 히어로 글자가 먼저 그려지고 나서 계산된다.
frame = cached_roster().frame
total = len(frame)
high = int((frame["위험등급"] == "HIGH").sum())
medium = int((frame["위험등급"] == "MEDIUM").sum())
low = int((frame["위험등급"] == "LOW").sum())
dropout = int((frame["예측(원본)"] == "Dropout").sum())


def segment(level: str, count: int) -> tuple[str, str]:
    """위험 구성 띠의 조각 하나 + 범례 한 줄. 색은 화면 전체가 쓰는 등급 색 그대로."""
    share = count / total * 100
    color = RISK_COLORS[level]
    bar = f'<span style="width:{share:.1f}%;background:{color}"></span>'
    legend = (f'<span class="l"><i style="background:{color}"></i>'
              f'{level} · {RISK_LABELS_KO[level]} <b>{count:,}명</b>'
              f'<em>{share:.1f}%</em></span>')
    return bar, legend


def chip(icon: str, value: str, label: str) -> str:
    """숫자 하나짜리 칩. 아이콘 · 값 · 이름 순으로만 읽히게 한다."""
    return (
        f'<div class="chip"><span class="i material-symbols-rounded">{icon}</span>'
        f'<span class="t"><span class="v">{value}</span>'
        f'<span class="k">{label}</span></span></div>'
    )


with st.container(key="hero"):
    # 지구본을 먼저 그린다 — 절대 위치라 순서가 화면에 영향을 주지 않고,
    # 뒤에 오는 글자들이 자연스럽게 그 위에 얹힌다.
    # 일부러 크게 잡는다. 오른쪽 끝에서 잘리는 편이 액자에 맞춰 줄인 것보다 낫다.
    with st.container(key="hero_globe"):
        render_globe(height=860)

    # ── 상단 바 — 브랜드 왼쪽, 이동 오른쪽 ────────────────────────────────
    brand_col, nav_col = st.columns([1, 1], vertical_alignment="center")
    with brand_col:
        st.markdown(
            """<div class="hero-brand">
      <span class="mark material-symbols-rounded">school</span>
      <span class="t"><span class="n">대학생 학업 지속 지원 시스템</span>
        <span class="s">중도탈락 예측 · 지원</span></span>
    </div>""",
            unsafe_allow_html=True,
        )
    with nav_col:
        with st.container(key="hero_nav", horizontal=True, gap="small",
                          horizontal_alignment="right"):
            st.page_link(PAGE_DASHBOARD, label="대시보드", icon=":material/monitoring:")
            st.page_link(PAGE_STUDENTS, label="학생 목록", icon=":material/table_rows:")
            st.page_link(PAGE_RISK, label="집중관리 대상", icon=":material/priority_high:")

    ui.spacer(24)

    # ── 표제 ──────────────────────────────────────────────────────────────
    st.markdown(
        f"""<div class="hero">
      <div class="hero-pills"><span class="hero-pill">
        <span class="i material-symbols-rounded">insights</span>
        학생 {total:,}명 · 위험도 재계산 완료</span></div>
      <h1>위험을 미리 찾고, <span class="hl">맞춤 지원</span>을 제안합니다</h1>
      <p class="hero-lead">학업·경제·입학 배경 데이터로 중도탈락 위험을
         <b>학기 중에 조기 식별</b>하고, 맞춤 지원을 제안합니다.</p>
    </div>""",
        unsafe_allow_html=True,
    )

    # ── 이동 버튼 ─────────────────────────────────────────────────────────
    with st.container(key="hero_cta", horizontal=True, gap="small"):
        if st.button("대시보드 바로가기", type="primary", key="home_dashboard",
                     icon=":material/space_dashboard:"):
            st.switch_page(PAGE_DASHBOARD)
        if st.button(f"집중관리 대상 확인 ({high:,})", key="home_risk",
                     icon=":material/notifications_active:"):
            st.switch_page(PAGE_RISK)

    ui.spacer(12)

    # ── 숫자 셋 ───────────────────────────────────────────────────────────
    st.markdown(
        f"""<div class="hero-chips">
      {chip("groups", f"{total:,}명", "전체 재학생")}
      {chip("percent", f"{dropout / total * 100:.1f}%", "예측 Dropout 비율")}
      {chip("crisis_alert", f"{high:,}명", "고위험 HIGH")}
    </div>""",
        unsafe_allow_html=True,
    )

    ui.spacer(12)

    # ── 위험 구성 한 줄 ───────────────────────────────────────────────────
    # 칩 셋이 "얼마나"를 말한다면 이 띠는 "어떻게 나뉘어 있는가"를 말한다.
    # 대시보드를 열기 전에 명단의 모양이 눈에 먼저 들어온다.
    bars, legends = zip(*(segment(level, count) for level, count in
                          (("HIGH", high), ("MEDIUM", medium), ("LOW", low))))
    st.markdown(
        f"""<div class="hero-split">
      <div class="hs-head">위험 구성<span class="n">전체 {total:,}명</span></div>
      <div class="hs-bar">{"".join(bars)}</div>
      <div class="hs-legend">{"".join(legends)}</div>
    </div>""",
        unsafe_allow_html=True,
    )

    ui.spacer(12)

    # ── 이 제품이 답하는 것 ───────────────────────────────────────────────
    with st.container(key="hero_card"):
        text_col, button_col = st.columns([1, 0.3], vertical_alignment="center")
        with text_col:
            st.markdown(
                """<div class="hc-title">예측값 하나에 그치지 않고,
        <b>“왜”</b>와 <b>“그래서 무엇을”</b>을 함께 답합니다</div>
      <div class="hc-desc">학생을 선택하면 위험 예측 분석과 그 학생의 위험요인에 대응하는
        맞춤 조치 제안, 그리고 이수율·성적·재정 상태를 조정해보는 What-if 시뮬레이션까지
        한 자리에서 확인할 수 있습니다.</div>""",
                unsafe_allow_html=True,
            )
        with button_col:
            if st.button("학생 분석 시작", key="home_students",
                         icon=":material/person_search:", width="stretch"):
                st.switch_page(PAGE_STUDENTS)
