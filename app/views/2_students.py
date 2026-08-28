"""
화면 3 — 학생 목록. 수백~수천 명 중 위험학생을 빠르게 좁히는 운영 화면이다.

    좁힌다(툴바) → 고른다(표) → 본다(조치·분석·What-if) → 없으면 직접 넣는다

여기만 `st.dataframe` 을 쓴다. 명단이 수백 행이라 정렬·가상 스크롤이 필요하고,
그건 직접 그린 표로는 감당할 수 없다. 행 선택은 **한 번에 한 명**만 된다.

`직접 입력` 은 원래 독립 화면이었다. 명단에서 고르는 것과 손으로 넣는 것은
**입력 방법의 차이**일 뿐이고 결과 화면은 같으므로 이 화면 안으로 흡수했다.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from components import manual_input, student_detail, ui
from components.state import cached_export, cached_roster, send_to_form, start_page
from components.theme import COLORS, RISK_COLORS
from rules import recommendation_rules as rules
from services import case_sheet
from services.predictor import RISK_LABELS_KO, RISK_LEVELS
from services.prediction_service import get_service
from utils.feature_mapping import MAJOR_FIELDS

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
        "학생 ID": st.column_config.TextColumn("학번", width="small"),
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


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

# 직접 입력 폼의 값 준비는 **어떤 위젯보다 먼저** 끝내야 한다.
manual_input.prepare()

service = get_service()
roster = cached_roster()
frame = roster.frame

start_page(
    "학생 목록",
    "학번·전공·위험도로 좁힌 뒤 학생을 선택하면 아래에 위험 예측 분석과 지원 추천이 열립니다.",
    meta=(
        '<div class="ds-eyebrow">Roster</div>'
        f'<div class="ds-sub" style="margin-top:4px">{escape(roster.source)}</div>'
    ),
)

ui.prototype_banner(service)

# 대시보드·위험학생 목록에서 넘어온 경우 — ?student=S0068
requested = str(st.query_params.get("student") or "").strip()
if requested and st.session_state.get("_student_from_url") != requested:
    st.session_state["roster_search"] = requested
    st.session_state["_student_from_url"] = requested

# ── 상단 집계 ──────────────────────────────────────────────────────────────
counts = frame["위험등급"].value_counts()
ui.kpi_row(
    [
        {"label": "전체 학생", "value": f"{len(frame):,}", "unit": "명",
         "caption": "실데이터" if roster.is_real else "합성 더미", "accent": COLORS["primary"]},
        {"label": "HIGH", "value": f"{int(counts.get('HIGH', 0)):,}", "unit": "명",
         "caption": "즉시 확인 권장", "accent": RISK_COLORS["HIGH"]},
        {"label": "MEDIUM", "value": f"{int(counts.get('MEDIUM', 0)):,}", "unit": "명",
         "caption": "정기 모니터링", "accent": RISK_COLORS["MEDIUM"]},
        {"label": "LOW", "value": f"{int(counts.get('LOW', 0)):,}", "unit": "명",
         "caption": "학기 단위 확인", "accent": RISK_COLORS["LOW"]},
    ],
    columns=4,
)

# ── 툴바 ───────────────────────────────────────────────────────────────────
ui.spacer(12)
with st.container(border=True):
    t1, t2, t3, t4 = st.columns([1.1, 1.2, 1.2, 0.8], gap="medium")
    with t1:
        keyword = st.text_input("학번 검색", placeholder="학번 검색 (예: S0012)",
                                label_visibility="collapsed", key="roster_search")
    with t2:
        majors = st.multiselect(
            "전공 계열", options=list(MAJOR_FIELDS), default=[],
            label_visibility="collapsed", placeholder="전공 계열 전체",
        ) or list(MAJOR_FIELDS)
    with t3:
        # 기본값을 "전부 선택" 으로 두면 칩이 툴바를 두 줄로 밀어낸다.
        # 비어 있으면 전체로 본다 — 필터 UI 의 일반적인 약속이기도 하다.
        levels = st.multiselect(
            "위험도", options=list(RISK_LEVELS), default=[],
            format_func=lambda level: f"{level} · {RISK_LABELS_KO[level]}",
            label_visibility="collapsed", placeholder="위험도 전체",
        ) or list(RISK_LEVELS)
    with t4:
        focus_only = st.checkbox("집중관리만", key="roster_focus_only")

st.caption(
    "이름으로 검색하지 않는 이유: 원본이 익명 데이터라 **학생 이름이 존재하지 않습니다**. "
    "실제 학사 시스템에 붙일 때 학번 칸을 이름까지 받도록 늘리면 됩니다."
)

filtered = frame[frame["위험등급"].isin(levels) & frame["전공 계열"].isin(majors)]
if keyword.strip():
    filtered = filtered[filtered["학생 ID"].str.contains(keyword.strip(), case=False, na=False)]
if focus_only:
    filtered = filtered[filtered["집중관리"] == "●"]
filtered = filtered.sort_values("중도탈락 확률", ascending=False).reset_index(drop=True)

# ── 표 ─────────────────────────────────────────────────────────────────────
ui.section("명단", f"조회된 {len(filtered):,}명 · 행을 선택하면 아래에 분석이 열립니다.")

if filtered.empty:
    ui.empty_state(
        "조건에 맞는 학생이 없습니다",
        "위험도나 전공 필터를 넓히거나 검색어를 지워보세요.",
    )
else:
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

    summary_csv, actions_csv, action_count = cached_export(tuple(filtered["학생 ID"]))
    ui.spacer(8)
    export_left, export_right = st.columns(2, gap="small")
    with export_left:
        st.download_button(
            f"조회된 명단 요약 내려받기 (.csv · {len(filtered):,}명)",
            data=summary_csv, file_name=case_sheet.filename("roster_summary"),
            mime="text/csv", width="stretch", key="dl_roster_summary",
        )
    with export_right:
        st.download_button(
            f"조회된 명단 조치 목록 (.csv · {action_count:,}건)",
            data=actions_csv, file_name=case_sheet.filename("roster_actions"),
            mime="text/csv", width="stretch", disabled=action_count == 0,
            key="dl_roster_actions",
        )

    selected = list(getattr(event.selection, "rows", []) or [])
    if selected:
        student_id = str(filtered.iloc[selected[0]]["학생 ID"])
    elif requested and roster.by_id(requested) is not None:
        # 다른 화면에서 학생을 지정해 들어온 경우 — 한 번 더 클릭하게 만들지 않는다.
        student_id = requested
    else:
        student_id = ""

    if not student_id:
        ui.spacer(10)
        ui.empty_state(
            "학생을 선택하지 않았습니다",
            "표에서 한 명을 선택하면 위험 예측 분석·지원 추천·What-if 가 여기에 나타납니다.",
        )
    else:
        row = roster.by_id(student_id)
        if row is None:
            ui.empty_state("상세 정보를 찾지 못했습니다", f"학생 {student_id} 가 명단에 없습니다.")
        else:
            ui.section(f"{student_id} 위험 예측 분석")
            student_detail.render(row, key="detail")
            ui.spacer(10)
            if st.button("이 학생 값을 아래 직접 입력 폼으로 보내기",
                         key=f"send_{student_id}", width="stretch"):
                send_to_form(row.student)
                st.rerun()

# ── 직접 입력 (흡수된 예측 화면) ───────────────────────────────────────────
ui.spacer(18)
with st.expander("명단에 없는 학생 직접 입력해서 예측하기", expanded=False):
    st.caption(
        "팀 전처리(Model B)가 요구하는 입력 32개입니다. 이수율·재정위험점수 등 "
        "파생변수 5종은 아래 값에서 자동 계산되므로 직접 입력하지 않습니다."
    )
    student = manual_input.render()

    if student is not None:
        for problem in student.validate():
            st.warning(problem)
        try:
            result = service.predict(student)
        except Exception as error:   # 예측기 교체 중 오류가 나도 화면은 살아 있어야 한다.
            ui.empty_state("예측을 수행할 수 없습니다", str(error))
        else:
            recommendation = rules.evaluate(student, result)
            ui.spacer(12)
            ui.section("분석 결과", f"대상 · {student.student_id}")
            ui.result_panel(student, result, recommendation, show_summary=True)
            ui.spacer(10)
            ui.case_downloads(student, result, recommendation, key="manual")
