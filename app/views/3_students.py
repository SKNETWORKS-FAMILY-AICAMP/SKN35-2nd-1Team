"""
화면 3 — 학생 목록. 수백~수천 명 중 위험학생을 빠르게 좁히는 운영 화면이다.

여기만 `st.dataframe` 을 쓴다. 명단이 수백 행이라 정렬·가상 스크롤이 필요하고,
그건 직접 그린 표로는 감당할 수 없다. 대신 필터를 한 줄 툴바로 압축하고
선택하면 아래에 상세가 열리는 **master-detail** 구조로 만든다.
"""

from __future__ import annotations

from html import escape

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
    "중도탈락 확률(%)",
    "위험등급",
    "주요 위험",
    "집중관리",
    "2학기 이수율",
    "평균 성적",
    "재정위험점수",
]


def column_config() -> dict:
    return {
        "학생 ID": st.column_config.TextColumn("학생", width="small"),
        "중도탈락 확률(%)": st.column_config.ProgressColumn(
            "중도탈락 확률", format="%.1f%%", min_value=0.0, max_value=100.0,
            help="현재는 DummyPredictor 가 산출한 값입니다.",
        ),
        "위험등급": st.column_config.TextColumn("등급", width="small"),
        "2학기 이수율": st.column_config.NumberColumn("2학기 이수율", format="%.0f%%"),
        "평균 성적": st.column_config.NumberColumn("평균 성적", format="%.1f",
                                               help="원본 0~20 기준"),
        "재정위험점수": st.column_config.NumberColumn(
            "재정위험", format="%d", help="0~3 · 등록금 미납 + 채무 + 장학금 미수혜"
        ),
        "집중관리": st.column_config.TextColumn("집중", width="small",
                                            help="서로 다른 영역의 위험이 겹친 학생"),
    }


service = get_service()
roster = cached_roster()
frame = roster.frame

start_page(
    "학생 목록",
    "위험등급·예측·집중관리로 좁힌 뒤 학생을 선택하면 아래에 상세 분석과 지원 추천이 열립니다.",
    meta=(
        '<div class="ds-eyebrow">Roster</div>'
        f'<div class="ds-sub" style="margin-top:4px">{escape(roster.source)}</div>'
    ),
)

ui.prototype_banner(service)

# ── 툴바 ───────────────────────────────────────────────────────────────────
with st.container(border=True):
    t1, t2, t3, t4 = st.columns([1.1, 1.2, 1.2, 0.8], gap="medium")
    with t1:
        keyword = st.text_input("학생 검색", placeholder="예: S0012", label_visibility="collapsed")
    with t2:
        # 기본값을 "전부 선택" 으로 두면 칩 3개가 툴바를 두 줄로 밀어낸다.
        # 비어 있으면 전체로 본다 — 필터 UI 의 일반적인 약속이기도 하다.
        levels = st.multiselect(
            "위험등급", options=list(RISK_LEVELS), default=[],
            format_func=lambda level: f"{level} · {RISK_LABELS_KO[level]}",
            label_visibility="collapsed", placeholder="위험등급 전체",
        ) or list(RISK_LEVELS)
    with t3:
        classes = st.multiselect(
            "예측", options=list(TARGET_CLASSES), default=[],
            format_func=lambda cls: TARGET_LABELS_KO[cls],
            label_visibility="collapsed", placeholder="예측 전체",
        ) or list(TARGET_CLASSES)
    with t4:
        focus_only = st.checkbox("집중관리만", value=False)

filtered = frame[frame["위험등급"].isin(levels) & frame["예측(원본)"].isin(classes)]
if keyword.strip():
    filtered = filtered[filtered["학생 ID"].str.contains(keyword.strip(), case=False, na=False)]
if focus_only:
    filtered = filtered[filtered["집중관리"] == "●"]
filtered = filtered.sort_values("중도탈락 확률", ascending=False).reset_index(drop=True)

# ── 요약 ───────────────────────────────────────────────────────────────────
counts = filtered["위험등급"].value_counts()
ui.spacer(10)
ui.kpi_row(
    [
        {"label": "조회된 학생", "value": f"{len(filtered):,}", "unit": "명",
         "caption": f"전체 {len(frame):,}명 중", "accent": COLORS["primary"],
         "share": len(filtered) / len(frame) if len(frame) else 0},
        {"label": "HIGH", "value": f"{int(counts.get('HIGH', 0)):,}", "unit": "명",
         "caption": "즉시 확인 권장", "accent": RISK_COLORS["HIGH"]},
        {"label": "MEDIUM", "value": f"{int(counts.get('MEDIUM', 0)):,}", "unit": "명",
         "caption": "정기 모니터링", "accent": RISK_COLORS["MEDIUM"]},
        {"label": "LOW", "value": f"{int(counts.get('LOW', 0)):,}", "unit": "명",
         "caption": "학기 단위 확인", "accent": RISK_COLORS["LOW"]},
    ],
    columns=4,
)

# ── 표 ─────────────────────────────────────────────────────────────────────
ui.section("명단", "행을 클릭하면 아래에 상세 분석이 열립니다.")

if filtered.empty:
    ui.empty_state(
        "조건에 맞는 학생이 없습니다",
        "위험등급이나 예측 필터를 넓히거나 검색어를 지워보세요.",
    )
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

selected = list(getattr(event.selection, "rows", []) or [])
if not selected:
    ui.spacer(10)
    ui.empty_state(
        "학생을 선택하지 않았습니다",
        "표에서 한 명을 클릭하면 위험도·위험요인·지원 추천이 여기에 나타납니다.",
    )
    st.stop()

student_id = str(filtered.iloc[selected[0]]["학생 ID"])
row = roster.by_id(student_id)
if row is None:
    ui.empty_state("상세 정보를 찾지 못했습니다", f"학생 {student_id} 가 명단에 없습니다.")
    st.stop()

ui.section(f"{student_id} 상세 분석")
ui.result_panel(row.student, row.result, row.recommendation)

ui.spacer(10)
if st.button("이 학생을 예측 화면으로 보내기", key=f"send_{student_id}", width="stretch"):
    send_to_prediction(row.student)
    st.switch_page(PAGE_PREDICTION)
