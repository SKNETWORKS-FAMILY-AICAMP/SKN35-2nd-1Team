"""화면 0 — 시작화면. 무엇을 하는 제품이고, 어떤 데이터로 만들었고, 어디까지 넓어지는가."""

from __future__ import annotations

from html import escape

import streamlit as st

from components import ui
from components.globe import render as render_globe
from components.state import PAGE_DASHBOARD, PAGE_PREDICTION, roster_source, start_page
from components.theme import CATEGORY_COLORS, COLORS, RISK_COLORS
from services.prediction_service import get_service
from utils.schema import dropped_columns, final_feature_count, target_definition

start_page("")

_, is_real = roster_source()

# ---------------------------------------------------------------------------
# 1. Hero — 첫 5초
# ---------------------------------------------------------------------------

# 지구본을 히어로 배경 위에 올린다. 데이터 출처가 어디인지 첫 화면에서 바로 읽히게 —
# 별도 섹션의 삽화로 두면 "장식" 이 되고, 여기 두면 "이 제품의 근거" 가 된다.
with st.container(key="hero", horizontal=True, gap="large", vertical_alignment="center"):
    with st.container(key="hero_text"):
        st.markdown(
            f"""<div class="hero">
      <div class="eyebrow">SKN35 · 2nd Team Project · Student Success Analytics</div>
      <h1>Student Dropout<br>Intelligence</h1>
      <div class="kr">대학생 중도탈락 위험 예측 및 맞춤 지원 시스템</div>
      <p>학업·경제·입학 배경 데이터를 기반으로 <b style="color:#EAF2FC">중도탈락 위험을 학기 중에 조기 식별</b>하고,
         그 학생의 위험요인에 대응하는 교내 지원 방향까지 제안합니다.
         예측값 하나를 띄우고 끝내지 않고 <b style="color:#EAF2FC">왜 위험한가</b>와
         <b style="color:#EAF2FC">그래서 무엇을 할 것인가</b>를 함께 답합니다.</p>
      <div class="hero-meta">
        <div class="item"><div class="k">Students</div><div class="v">4,424</div></div>
        <div class="item"><div class="k">Source</div><div class="v">UCI Dataset</div></div>
        <div class="item"><div class="k">Origin</div><div class="v">Portugal</div></div>
        <div class="item"><div class="k">Model</div><div class="v">Binary Risk</div></div>
        <div class="item"><div class="k">Features</div><div class="v">{final_feature_count() or 81}</div></div>
      </div>
    </div>""",
            unsafe_allow_html=True,
        )
    with st.container(key="hero_globe"):
        render_globe(height=420)

ui.spacer(20)
ui.prototype_banner(
    get_service(),
    source_note=(
        "명단 화면은 팀이 올린 전처리 데이터를 원래 값으로 되돌려 표시합니다."
        if is_real else ""
    ),
)

# ---------------------------------------------------------------------------
# 2. 파이프라인 — 이 제품이 무엇을 하는지 한 줄로
# ---------------------------------------------------------------------------

ui.section("어떻게 작동하는가", "네 단계가 이 시스템의 전부입니다.")

st.markdown(
    f"""<div class="flow">
      <div class="step" style="--accent:{COLORS['primary']}">
        <div class="n">01</div><div class="k">Data</div>
        <div class="t">학적 · 학업 · 재정</div>
        <div class="d">포르투갈 고등교육기관 학생 4,424명의 입학 시점 정보와
          1·2학기 학업 성과.</div>
      </div>
      <div class="step" style="--accent:{CATEGORY_COLORS['adaptation']}">
        <div class="n">02</div><div class="k">Model</div>
        <div class="t">범주 일반화 + 파생변수</div>
        <div class="d">제도 종속 범주를 상위 개념으로 묶고 이수율·재정위험 등
          파생변수 5종을 더해 {final_feature_count() or 81}개 피처로.</div>
      </div>
      <div class="step" style="--accent:{RISK_COLORS['HIGH']}">
        <div class="n">03</div><div class="k">Risk Signal</div>
        <div class="t">중도탈락 확률 + 위험요인</div>
        <div class="d">{escape(target_definition())} 기준 이진 예측.
          확률만이 아니라 무엇이 위험을 올렸는지 함께 낸다.</div>
      </div>
      <div class="step" style="--accent:{RISK_COLORS['LOW']}">
        <div class="n">04</div><div class="k">Support Action</div>
        <div class="t">규칙 기반 지원 연결</div>
        <div class="d">학업·경제·진로적응 12개 규칙이 위험요인에 대응하는
          교내 프로그램을 연결한다. LLM 을 쓰지 않는다.</div>
      </div>
    </div>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 3. 데이터 출처 + 지구본
# ---------------------------------------------------------------------------

ui.section("어떤 데이터로 만들었는가", "포르투갈 고등교육기관의 실제 학적·학업·재정 기록입니다.")

st.markdown(
    f"""<div class="card card-lg">
          <div class="ds-eyebrow">Training data</div>
          <div class="ds-h2" style="margin-top:8px">
            UCI — Predict Students' Dropout and Academic Success</div>
          <div class="ds-sub" style="margin-top:6px">
            포르투갈 폴리테크닉 기관 · 학사 데이터베이스 기반 공개 데이터셋</div>
          <div class="ds-body" style="margin-top:16px;max-width:88ch">
            입학 시점의 인구·사회·경제 정보와 1·2학기 학업 성과를 함께 담고 있어,
            <b>학기가 끝나는 시점마다</b> 위험 신호를 다시 계산할 수 있는 구조입니다.
          </div>
          <div class="ds-caption" style="margin-top:14px">
            Target 정의 · <span class="ds-mono">{escape(target_definition())}</span>
          </div>
        </div>""",
    unsafe_allow_html=True,
)
ui.spacer(12)
ui.kpi_row(
    [
        {"label": "Students", "value": "4,424", "caption": "학생 단위 레코드",
         "accent": COLORS["primary"]},
        {"label": "Raw variables", "value": "37", "caption": "Target 포함",
         "accent": COLORS["ink"]},
        {"label": "Dropout rate", "value": "32.1", "unit": "%",
         "caption": "Non-Dropout 67.9%", "accent": RISK_COLORS["HIGH"], "share": 0.321},
        {"label": "Model features", "value": f"{final_feature_count() or 81}",
         "caption": "일반화 + 인코딩 후", "accent": CATEGORY_COLORS["adaptation"]},
    ],
    columns=4,
)

# ---------------------------------------------------------------------------
# 4. 이식성 — 프로덕트 전략처럼
# ---------------------------------------------------------------------------

ui.section(
    "Designed for localization",
    "지금 모델을 다른 나라에 그대로 쓰는 것이 아닙니다. 같은 상위 Feature Schema 를 두고 "
    "각국 데이터를 매핑한 뒤 현지 데이터로 재학습하는 구조입니다.",
)

chain_col, why_col = st.columns([1, 1.15], gap="large")

with chain_col:
    st.markdown(
        """<div class="chain">
          <div class="node"><span class="i">01</span>
            <span class="t">Portugal-specific raw categories</span>
            <span class="d">학과 17 · 전형 18 · 학력 17</span></div>
          <div class="arrow">↓</div>
          <div class="node"><span class="i">02</span>
            <span class="t">Generalized academic schema</span>
            <span class="d">계열 10 · 전형 8 · 학력 6</span></div>
          <div class="arrow">↓</div>
          <div class="node"><span class="i">03</span>
            <span class="t">Local university mapping</span>
            <span class="d">각국 제도를 같은 상위 개념에</span></div>
          <div class="arrow">↓</div>
          <div class="node"><span class="i">04</span>
            <span class="t">Local retraining</span>
            <span class="d">현지 데이터로 재학습</span></div>
        </div>""",
        unsafe_allow_html=True,
    )

with why_col:
    macro = [c for c in dropped_columns() if c in ("Unemployment rate", "Inflation rate", "GDP")]
    st.markdown(
        f"""<div class="card card-lg" style="height:100%">
          <div class="ds-eyebrow">왜 옮겨 쓸 수 있는가</div>
          <div style="margin-top:14px">
            <div class="ds-h3">국가·시점에 묶인 변수는 이미 뺐다</div>
            <div class="ds-sub" style="margin-top:6px">
              {escape(', '.join(macro) if macro else '거시경제 변수 3종')} 은 특정 시점의
              포르투갈 경제 상황이라 제거했습니다 (Target 과의 상관 0.05 미만).
              국적도 97.5%가 포르투갈로 쏠려 제외했습니다.</div>
          </div>
          <div style="margin-top:18px;padding-top:18px;border-top:1px solid {COLORS['line_soft']}">
            <div class="ds-h3">가장 강한 신호는 제도와 무관하다</div>
            <div class="ds-sub" style="margin-top:8px">
              <span class="ds-mono">sem2_approval_rate</span> 상관 <b>−0.659</b><br>
              <span class="ds-mono">sem1_approval_rate</span> 상관 <b>−0.591</b><br>
              <span class="ds-mono">financial_risk_score</span> 상관 <b>+0.435</b><br>
              <span style="display:inline-block;margin-top:8px">
                이수율과 재정 상태는 <b>어느 대학 행정 시스템에나 있는 값</b>입니다.</span>
            </div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

ui.spacer(18)
st.markdown('<div class="ds-eyebrow">필요 데이터 체크리스트</div>', unsafe_allow_html=True)
ui.spacer(8)

_CHECKLIST = [
    ("Student registry", "학적 정보", "나이 · 성별 · 혼인상태 · 거주 이동 · 특별지원 대상", "적응 위험"),
    ("Academic performance", "학기별 학업 성과", "수강/이수 과목 수 · 평균 성적 · 평가 응시",
     "sem1/2_approval_rate · grade_change"),
    ("Tuition & payment", "등록금 납부", "납부 상태 · 미납 여부", "financial_risk_score"),
    ("Scholarship & debt", "장학·채무", "장학금 수혜 · 채무 보유", "financial_risk_score"),
    ("Admission information", "입학 정보", "전형 유형 · 지망 순위 · 입학 성적 · 이전 학력",
     "전공 적합도 · 학업 준비도"),
]

rows = "".join(
    f"""<tr>
          <td style="width:34px;color:{RISK_COLORS['LOW']};font-weight:700">✓</td>
          <td><span class="ds-mono" style="color:{COLORS['muted']}">{escape(en)}</span><br>
              <span style="font-weight:600;color:{COLORS['ink']}">{escape(ko)}</span></td>
          <td class="ds-sub">{escape(items)}</td>
          <td class="ds-caption" style="color:{COLORS['primary']}">{escape(signal)}</td>
        </tr>"""
    for en, ko, items, signal in _CHECKLIST
)
st.markdown(
    f"""<div class="card" style="padding:16px 8px">
      <table class="dt"><thead><tr>
        <th></th><th>필요 데이터</th><th>구체 항목</th><th>만들어지는 신호</th>
      </tr></thead><tbody>{rows}</tbody></table></div>""",
    unsafe_allow_html=True,
)
st.caption(
    "위 항목은 일반적인 학사종합정보시스템의 표준 항목을 기준으로 정리한 것이며, "
    "실제 도입 시에는 개별 대학의 데이터 보유 현황과 개인정보 처리 근거를 별도로 확인해야 합니다."
)

# ---------------------------------------------------------------------------
# 5. 이동
# ---------------------------------------------------------------------------

ui.section("바로 보기")
go_dashboard, go_prediction = st.columns(2, gap="medium")
with go_dashboard:
    if st.button("전체 현황 대시보드", width="stretch", type="primary"):
        st.switch_page(PAGE_DASHBOARD)
with go_prediction:
    if st.button("학생 한 명 예측해 보기", width="stretch"):
        st.switch_page(PAGE_PREDICTION)
