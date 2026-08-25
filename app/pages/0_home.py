"""화면 0 — 시작화면. 이 서비스가 무엇이고, 어떤 데이터로 만들어졌고, 어디까지 넓어지는가."""

from __future__ import annotations

import streamlit as st

from components import ui
from components.globe import render as render_globe
from components.state import PAGE_DASHBOARD, PAGE_PREDICTION, start_page
from components.theme import COLORS, RISK_COLORS
from services.prediction_service import get_service
from utils.schema import dropped_columns, final_feature_count, target_definition

start_page("")

# ---------------------------------------------------------------------------
# 히어로
# ---------------------------------------------------------------------------

st.markdown(
    """<div class="hero">
         <div class="eyebrow">SK네트웍스 FAMILY AI 캠프 · 2nd Team Project</div>
         <h1>대학생 중도탈락 위험 예측 및<br>맞춤 지원 시스템</h1>
         <p>학생지원 담당자·지도교수·학사관리자가 <b>중도탈락 위험이 높은 학생을 학기 중에 먼저 찾고</b>,
            그 학생의 위험요인에 대응하는 교내 지원 프로그램까지 연결하도록 만든 의사결정 보조 도구입니다.
            예측값 하나를 띄우고 끝내지 않고 <b>"왜 위험한가"</b> 와 <b>"그래서 무엇을 할 것인가"</b> 를 함께 답합니다.</p>
         <div class="flow">
           <span class="step">학생 정보</span><span class="arrow">→</span>
           <span class="step">중도탈락 위험 예측</span><span class="arrow">→</span>
           <span class="step">위험요인 분석</span><span class="arrow">→</span>
           <span class="step">규칙 기반 맞춤지원 추천</span>
         </div>
       </div>""",
    unsafe_allow_html=True,
)

st.write("")
ui.prototype_banner(get_service())

# ---------------------------------------------------------------------------
# 데이터 출처 + 지구본
# ---------------------------------------------------------------------------

ui.section("어떤 데이터로 만들었는가", "포르투갈 고등교육기관의 실제 학적·학업·재정 기록입니다.")

left, right = st.columns([1.15, 1], gap="large")

with left:
    st.markdown(
        f"""<div class="card">
              <div class="card-title">UCI — Predict Students' Dropout and Academic Success</div>
              <div class="card-sub">포르투갈 폴리테크닉 기관 · 학사 데이터베이스 기반 공개 데이터셋</div>
              <div style="margin-top:.9rem;font-size:.87rem;color:{COLORS['ink_soft']};line-height:1.75">
                입학 시점의 인구·사회·경제 정보와 1·2학기 학업 성과를 함께 담고 있어,
                <b>학기가 끝나는 시점마다</b> 위험 신호를 다시 계산할 수 있는 구조입니다.<br>
                본 시스템의 Target 정의는 팀 전처리 기준
                <code>{target_definition()}</code> 입니다.
              </div>
            </div>""",
        unsafe_allow_html=True,
    )
    st.write("")
    ui.kpi_grid(
        [
            ("데이터 규모", "4,424명", "학생 단위 레코드", COLORS["primary"]),
            ("원본 변수", "37개", "Target 포함", COLORS["ink"]),
            ("중도탈락 비율", "32.1%", "Non-Dropout 67.9%", RISK_COLORS["HIGH"]),
            (
                "모델 입력 피처",
                f"{final_feature_count() or 81}개",
                "범주 일반화 + 원-핫 인코딩 후",
                COLORS["primary"],
            ),
        ]
    )

with right:
    render_globe(height=330)

# ---------------------------------------------------------------------------
# 미래 확장 — 다른 나라에도 적용할 수 있는가
# ---------------------------------------------------------------------------

ui.section(
    "다른 나라에서도 쓸 수 있는가",
    "포르투갈 데이터로 만들었지만, 팀의 전처리 설계 자체가 이미 '옮겨 쓰기'를 염두에 둔 구조입니다.",
)

dropped = dropped_columns()
macro = [c for c in dropped if c in ("Unemployment rate", "Inflation rate", "GDP")]

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown(
        f"""<div class="port-card">
              <span class="tag">근거 1</span>
              <h4>국가·시점에 묶인 변수는 이미 뺐다</h4>
              <p>{', '.join(macro) if macro else '거시경제 변수 3종'} 은
                 특정 시점의 <b>포르투갈 경제 상황</b>이라 제거했습니다
                 (Target 과의 상관도 0.05 미만). 국적(Nacionality)도
                 97.5%가 포르투갈로 쏠려 정보 가치가 없어 제외했습니다.<br>
                 → 남은 변수는 <b>어느 나라 학생에게나 정의되는 값</b>입니다.</p>
            </div>""",
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """<div class="port-card">
              <span class="tag">근거 2</span>
              <h4>제도에 묶인 범주는 상위 개념으로 올렸다</h4>
              <p>포르투갈 제도에 종속된 세부 범주를 보편적으로 이해되는 상위 개념으로 재분류했습니다.<br>
                 · 학과 <b>17종 → 전공계열 10개</b><br>
                 · 입학전형 <b>18종 → 전형유형 8개</b><br>
                 · 이전 학력 <b>17종 → 학력수준 6단계</b><br>
                 → 다른 나라는 <b>자기 제도를 같은 상위 개념에 다시 매핑</b>하기만 하면 됩니다.</p>
            </div>""",
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """<div class="port-card">
              <span class="tag">근거 3</span>
              <h4>가장 강한 신호는 제도와 무관하다</h4>
              <p>예측력이 가장 높은 변수는 특수한 제도가 아니라
                 <b>어느 대학 행정 시스템에나 있는 값</b>입니다.<br>
                 · <code>sem2_approval_rate</code> (이수율) 상관 <b>-0.659</b><br>
                 · <code>sem1_approval_rate</code> 상관 <b>-0.591</b><br>
                 · <code>financial_risk_score</code> (재정위험) 상관 <b>+0.435</b><br>
                 → 학사·등록 데이터만 있으면 같은 신호를 만들 수 있습니다.</p>
            </div>""",
        unsafe_allow_html=True,
    )

st.write("")
st.markdown(
    '<div class="card-title">다른 나라에 적용하려면 이만큼의 데이터가 필요합니다</div>'
    '<div class="section-desc">아래 4종은 한국 대학의 학사종합정보시스템에도 대부분 이미 존재하는 항목입니다.</div>',
    unsafe_allow_html=True,
)

st.dataframe(
    {
        "필요 데이터": ["학적 정보", "학기별 학업 성과", "재정 상태", "입학 정보"],
        "구체 항목": [
            "입학 시 나이 · 성별 · 혼인상태 · 거주 이동 여부 · 특별지원 대상 여부",
            "학기별 수강/이수 과목 수 · 평균 성적 · 평가 응시 여부",
            "등록금 납부 상태 · 채무 보유 · 장학금 수혜",
            "전형 유형 · 지망 순위 · 입학 성적 · 이전 학력 수준",
        ],
        "이 시스템에서 만들어지는 신호": [
            "적응 위험 (야간·타지·만학)",
            "sem1/2_approval_rate · grade_change · zero_enrolled_1st_sem",
            "financial_risk_score (0~3)",
            "전공 적합도 · 학업 준비도",
        ],
        "한국 대학 보유 여부": ["보유", "보유", "보유", "보유"],
    },
    hide_index=True,
    width="stretch",
)

st.caption(
    "위 '한국 대학 보유 여부'는 일반적인 학사종합정보시스템의 표준 항목을 기준으로 한 판단이며, "
    "실제 도입 시에는 개별 대학의 데이터 보유 현황과 개인정보 처리 근거를 별도로 확인해야 합니다."
)

# ---------------------------------------------------------------------------
# 이동 버튼
# ---------------------------------------------------------------------------

ui.section("바로 보기")
go_dashboard, go_prediction = st.columns(2, gap="medium")
with go_dashboard:
    if st.button("전체 현황 대시보드 열기", width="stretch", type="primary"):
        st.switch_page(PAGE_DASHBOARD)
with go_prediction:
    if st.button("학생 한 명 예측해 보기", width="stretch"):
        st.switch_page(PAGE_PREDICTION)
