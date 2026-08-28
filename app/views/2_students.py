"""
화면 3 — 학생 목록. 수백~수천 명 중 위험학생을 빠르게 좁히는 운영 화면이다.

    좁힌다(툴바) → 연다(줄을 누른다) → 본다(조치·분석·What-if)

여기는 **있는 학생을 찾는 곳**이다. 명단에 없는 학생을 손으로 넣어 보는 일은
`views/4_manual.py` (예비학생 예측)가 가져갔다 — 하는 일이 다른데 한 화면에 겹쳐
두면 명단이 길어지기만 한다.

`st.dataframe` 을 쓰지 않고 줄을 직접 그린다. 행 선택을 켜면 체크박스 열이 따라
붙는데, 담당자가 하는 일은 고르는 게 아니라 **여는 것**이라 한 단계 군더더기다.
대신 한 번에 세우는 줄 수를 `PER_PAGE` 로 끊는다.
"""

from __future__ import annotations

import math
from html import escape

import streamlit as st

from components import student_detail, ui
from components.state import cached_export, cached_roster, start_page
from components.theme import RISK_COLORS
from services import case_sheet
from services.predictor import RISK_LABELS_KO, RISK_LEVELS
from utils.display_id import display_name, display_year
from utils.feature_mapping import MAJOR_FIELDS

# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

roster = cached_roster()
frame = roster.frame

start_page(
    "학생 목록",
    meta=(
        '<div class="ds-eyebrow">Students</div>'
        f'<div class="ds-sub" style="margin-top:4px">{len(frame):,}명</div>'
    ),
)

# 대시보드·위험학생 목록에서 넘어온 경우 — ?student=S0068
requested = str(st.query_params.get("student") or "").strip()
if requested and st.session_state.get("_student_from_url") != requested:
    st.session_state["roster_search"] = requested
    st.session_state["_student_from_url"] = requested

# ── 툴바 ───────────────────────────────────────────────────────────────────
# 위험도는 드롭다운이 아니라 **버튼 세 개**다. 값이 셋뿐이고 담당자가 가장 자주 만지는
# 필터라, 한 번 눌러서 켜고 끄는 편이 목록 두 번 여는 것보다 빠르다.
with st.container(key="roster_filter", border=True):
    t1, t2, t3 = st.columns([1.1, 1.2, 1.5], gap="medium")
    with t1:
        keyword = st.text_input("학번 검색", placeholder="학번 검색 (예: S0012)",
                                label_visibility="collapsed", key="roster_search")
    with t2:
        majors = st.multiselect(
            "전공 계열", options=list(MAJOR_FIELDS), default=[],
            label_visibility="collapsed", placeholder="전공 계열 전체",
        ) or list(MAJOR_FIELDS)
    with t3:
        # 아무것도 안 누르면 전체다 — 필터 UI 의 일반적인 약속이다.
        levels = st.pills(
            "위험도", options=list(RISK_LEVELS), selection_mode="multi", default=[],
            format_func=lambda level: f"{level} · {RISK_LABELS_KO[level]}",
            label_visibility="collapsed", key="roster_levels",
        ) or list(RISK_LEVELS)

filtered = frame[frame["위험등급"].isin(levels) & frame["전공 계열"].isin(majors)]
if keyword.strip():
    filtered = filtered[filtered["학생 ID"].str.contains(keyword.strip(), case=False, na=False)]
filtered = filtered.sort_values("중도탈락 확률", ascending=False).reset_index(drop=True)
# 원본(익명 데이터)에 없는 두 칸. 학번마다 **항상 같은 값**이 나온다 (utils/display_id.py).
filtered = filtered.assign(
    이름=filtered["학생 ID"].map(display_name),
    학년=filtered["학생 ID"].map(lambda sid: f"{display_year(sid)}학년"),
)

# ── 표 ─────────────────────────────────────────────────────────────────────
# `st.dataframe` 을 쓰지 않는다. 행 선택을 켜면 **체크박스 열**이 따라붙는데,
# 담당자가 하는 일은 고르는 게 아니라 **여는 것**이라 체크박스가 한 단계 군더더기다.
# 직접 그린 행에 투명 버튼을 덮어 어디를 눌러도 팝업이 열리게 한다.

#: 한 페이지에 세우는 줄 수. 화면에 한 번에 들어오는 만큼만 세운다.
PER_PAGE = 12

ui.section("명단", f"조회된 {len(filtered):,}명 · 행을 누르면 상세 분석이 열립니다.")
st.caption("이름·학년은 화면 예시용으로 만든 값입니다 — 원본은 익명 데이터라 두 값이 없습니다.")

if filtered.empty:
    ui.empty_state(
        "조건에 맞는 학생이 없습니다",
        "위험도나 전공 필터를 넓히거나 검색어를 지워보세요.",
    )
    st.stop()

pages = max(1, math.ceil(len(filtered) / PER_PAGE))
page = min(int(st.session_state.get("roster_page", 0)), pages - 1)
st.session_state["roster_page"] = page
window = filtered.iloc[page * PER_PAGE:(page + 1) * PER_PAGE]

st.markdown(
    '<div class="rt-head"><span>학번</span><span>이름</span><span>전공 계열</span>'
    '<span>학년</span><span class="g">등급</span></div>',
    unsafe_allow_html=True,
)

for record in window.to_dict("records"):
    sid = str(record["학생 ID"])
    level = record["위험등급"]
    with st.container(key=f"rt_row_{sid}"):
        st.markdown(
            f'<div class="rt-row"><span>{escape(sid)}</span>'
            f'<span class="nm">{escape(str(record["이름"]))}</span>'
            f'<span>{escape(str(record["전공 계열"]))}</span>'
            f'<span>{escape(str(record["학년"]))}</span>'
            f'<span class="g"><span class="lv" style="--c:{RISK_COLORS[level]}">'
            f'{escape(level)}</span></span></div>',
            unsafe_allow_html=True,
        )
        if st.button("상세 열기", key=f"rt_open_{sid}", width="stretch"):
            picked = roster.by_id(sid)
            if picked is not None:
                student_detail.open_modal(picked, key="detail")

if pages > 1:
    ui.spacer(4)
    with st.container(key="rt_pager", horizontal=True, gap="small",
                      horizontal_alignment="center"):
        if st.button("← 이전", key="rt_prev", disabled=page == 0):
            st.session_state["roster_page"] = page - 1
            st.rerun()
        st.markdown(f'<div class="rl-page">{page + 1} / {pages}</div>',
                    unsafe_allow_html=True)
        if st.button("다음 →", key="rt_next", disabled=page >= pages - 1):
            st.session_state["roster_page"] = page + 1
            st.rerun()

# 다른 화면에서 `?student=` 로 지정해 들어온 경우 — 한 번 더 클릭하게 만들지 않는다.
if requested and st.session_state.get("_detail_open") != requested:
    picked = roster.by_id(requested)
    if picked is not None:
        st.session_state["_detail_open"] = requested
        student_detail.open_modal(picked, key="detail")

# ── 내려받기 ───────────────────────────────────────────────────────────────
summary_csv, actions_csv, action_count = cached_export(tuple(filtered["학생 ID"]))
ui.spacer(10)
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
