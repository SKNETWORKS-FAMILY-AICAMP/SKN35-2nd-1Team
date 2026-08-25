"""화면 3 — 더미 학생 명단. 필터로 위험군을 좁히고, 한 명을 골라 상세를 본다."""

from __future__ import annotations

import streamlit as st

from components import ui
from components.state import PAGE_PREDICTION, cached_roster, send_to_prediction, start_page
from components.theme import COLORS, RISK_COLORS
from services.predictor import RISK_LABELS_KO, RISK_LEVELS
from services.prediction_service import get_service
from utils.feature_mapping import TARGET_CLASSES, TARGET_LABELS_KO

TABLE_COLUMNS = [
    "학생 ID",
    "전공 계열",
    "예측",
    "중도탈락 확률(%)",
    "위험등급",
    "주요 위험",
    "집중관리",
    "2학기 이수율",
    "평균 성적",
    "재정위험점수",
    "등록금 미납",
    "장학금",
]


def column_config() -> dict:
    return {
        "중도탈락 확률(%)": st.column_config.ProgressColumn(
            "중도탈락 확률", format="%.1f%%", min_value=0.0, max_value=100.0,
            help="현재는 DummyPredictor 가 산출한 값입니다.",
        ),
        "2학기 이수율": st.column_config.NumberColumn("2학기 이수율", format="%.0f%%"),
        "평균 성적": st.column_config.NumberColumn("평균 성적", format="%.1f", help="원본 0~20 기준"),
        "재정위험점수": st.column_config.NumberColumn(
            "재정위험", format="%d", help="0~3 · 등록금 미납 + 채무 + 장학금 미수혜"
        ),
        "집중관리": st.column_config.TextColumn(
            "집중관리", width="small", help="복합 위험요인이 확인된 학생"
        ),
        "등록금 미납": st.column_config.TextColumn("등록금", width="small"),
        "장학금": st.column_config.TextColumn("장학금", width="small"),
    }


start_page(
    "학생 목록",
    "더미 학생 전체의 예측 결과입니다. 위험등급·예측 클래스로 좁힌 뒤 학생을 선택하면 "
    "아래에 상세 분석과 지원 추천이 나타납니다.",
)

service = get_service()
ui.prototype_banner(service)

roster = cached_roster()
frame = roster.frame

# -- 필터 ---------------------------------------------------------------------
ui.section("필터")
col1, col2, col3, col4 = st.columns([1.2, 1.2, 1, 0.9], gap="medium")
with col1:
    levels = st.multiselect(
        "위험등급",
        options=list(RISK_LEVELS),
        default=list(RISK_LEVELS),
        format_func=lambda level: f"{level} · {RISK_LABELS_KO[level]}",
    )
with col2:
    classes = st.multiselect(
        "예측 클래스",
        options=list(TARGET_CLASSES),
        default=list(TARGET_CLASSES),
        format_func=lambda cls: TARGET_LABELS_KO[cls],
    )
with col3:
    keyword = st.text_input("학생 ID 검색", placeholder="예: S012")
with col4:
    priority_only = st.checkbox("집중관리 대상만", value=False)

filtered = frame[frame["위험등급"].isin(levels) & frame["예측(원본)"].isin(classes)]
if keyword.strip():
    filtered = filtered[filtered["학생 ID"].str.contains(keyword.strip(), case=False, na=False)]
if priority_only:
    filtered = filtered[filtered["집중관리"] == "●"]
filtered = filtered.sort_values("중도탈락 확률", ascending=False).reset_index(drop=True)

# -- 요약 ---------------------------------------------------------------------
counts = filtered["위험등급"].value_counts()
ui.kpi_grid(
    [
        ("조회된 학생", f"{len(filtered)}명", f"전체 {len(frame)}명 중", COLORS["primary"]),
        ("HIGH", f"{int(counts.get('HIGH', 0))}명", "즉시 확인 권장", RISK_COLORS["HIGH"]),
        ("MEDIUM", f"{int(counts.get('MEDIUM', 0))}명", "모니터링 대상", RISK_COLORS["MEDIUM"]),
        ("LOW", f"{int(counts.get('LOW', 0))}명", "정기 확인", RISK_COLORS["LOW"]),
    ]
)

# -- 표 -----------------------------------------------------------------------
ui.section("명단", "행을 클릭하면 아래에 상세 분석이 열립니다.")
if filtered.empty:
    st.info("조건에 맞는 학생이 없습니다. 필터를 넓혀보세요.")
    st.stop()

event = st.dataframe(
    filtered.loc[:, TABLE_COLUMNS],
    hide_index=True,
    width="stretch",
    height=420,
    on_select="rerun",
    selection_mode="single-row",
    column_config=column_config(),
    key="roster_table",
)

selected_rows = list(getattr(event.selection, "rows", []) or [])
if not selected_rows:
    st.caption("학생을 선택하지 않았습니다. 표에서 한 명을 클릭하세요.")
    st.stop()

student_id = str(filtered.iloc[selected_rows[0]]["학생 ID"])
row = roster.by_id(student_id)
if row is None:
    st.error(f"학생 {student_id} 의 상세 정보를 찾지 못했습니다.")
    st.stop()

ui.section(f"{student_id} 상세 분석")
ui.result_panel(row.student, row.result, row.recommendation)

if st.button("이 학생 정보를 예측 화면으로 보내기", key=f"send_{student_id}"):
    send_to_prediction(row.student)
    st.switch_page(PAGE_PREDICTION)
