"""
화면 4 — 집중관리 대상 (위험학생 목록).

학생 목록이 **찾는 화면**이라면 여기는 **처리하는 화면**이다. 위험한 순서대로 줄을
세워 놓고 위에서부터 내려가며 접촉 상태를 남긴다. 그래서 이 화면에만 있는 것이
`상담 진행 상태` 다 — 앱이 유일하게 **쓰는** 데이터다.

상세 분석은 학생 목록의 `detail()` 을 그대로 부른다. 같은 학생을 두 화면에서 다르게
보여줄 이유가 없고, 한쪽만 고쳐지는 사고를 원천에서 막는다.
"""

from __future__ import annotations

import math
from html import escape
from urllib.parse import quote

import streamlit as st

from components import student_detail, ui
from components.state import cached_roster, start_page
from components.theme import CATEGORY_COLORS, COLORS, RISK_COLORS
from services import followup
from services.predictor import RISK_CATEGORIES

#: 필터 프리셋. 담당자가 실제로 쓰는 두 가지 폭이다.
#: 학생 목록 화면의 주소. `st.navigation` 이 파일명에서 만드는 경로와 같아야 한다.
STUDENT_PAGE_URL = "students"

#: 왼쪽이 기본값이다 — 담당자가 여는 순간 보이는 폭.
SCOPES: dict[str, tuple[str, ...]] = {
    "HIGH + MEDIUM": ("HIGH", "MEDIUM"),
    "HIGH 만": ("HIGH",),
}


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

roster = cached_roster()
table = followup.load()

start_page(
    "집중관리 대상",
    "위험이 높은 순서로 줄을 세운 처리 화면입니다.",
    meta=(
        '<div class="ds-eyebrow">Priority</div>'
        '<div class="ds-sub" style="margin-top:4px">확률 내림차순</div>'
    ),
)

# ── 필터 ───────────────────────────────────────────────────────────────────
# 범위는 라디오가 아니라 **분절 토글**이다. 선택지가 둘뿐이고 화면을 여는 순간
# 어느 폭으로 보고 있는지가 한눈에 읽혀야 하는 값이라, 눌린 상태가 보이는 편이 낫다.
with st.container(key="risk_filter", border=True):
    f1, f2, f3 = st.columns([1.3, 1.2, 1.2], gap="medium")
    with f1:
        scope = st.segmented_control(
            "범위", options=list(SCOPES), default=next(iter(SCOPES)),
            label_visibility="collapsed", key="risk_scope_seg",
        ) or next(iter(SCOPES))
    with f2:
        segments = st.multiselect(
            "세그먼트 · 위험 영역", options=list(RISK_CATEGORIES.values()), default=[],
            placeholder="전체",
        ) or list(RISK_CATEGORIES.values())
    with f3:
        statuses = st.multiselect(
            "상담 상태", options=list(followup.STATUSES), default=[],
            placeholder="전체",
        ) or list(followup.STATUSES)

levels = SCOPES[scope]
rows = [
    row for row in roster.rows
    if row.result.risk_level in levels
    and RISK_CATEGORIES.get(row.primary_category, "-") in segments
    and followup.status_of(table, row.student.student_id) in statuses
]
# 위험 확률 내림차순. 같은 확률이면 발동 규칙이 많은 학생이 먼저다 —
# 여러 영역이 동시에 무너진 학생이라 손이 더 많이 간다.
rows.sort(key=lambda r: (r.result.dropout_probability, len(r.recommendation.matched)),
          reverse=True)

# ── 집계 ───────────────────────────────────────────────────────────────────
ids = [row.student.student_id for row in rows]
tally = followup.counts(table, ids)
done = tally["상담완료"] + tally["종결"]

ui.spacer(10)
ui.kpi_row(
    [
        {"label": "대상 학생", "value": f"{len(rows):,}", "unit": "명",
         "caption": f"{scope} · 확률 내림차순", "accent": RISK_COLORS["HIGH"]},
        {"label": "미착수", "value": f"{tally['미착수']:,}", "unit": "명",
         "caption": "아직 접촉 전", "accent": COLORS["faint"],
         "share": tally["미착수"] / len(rows) if rows else 0},
        {"label": "진행 중", "value": f"{tally['연락함']:,}", "unit": "명",
         "caption": "연락함", "accent": RISK_COLORS["MEDIUM"]},
        {"label": "처리 완료", "value": f"{done:,}", "unit": "명",
         "caption": "상담완료 + 종결", "accent": RISK_COLORS["LOW"],
         "share": done / len(rows) if rows else 0},
    ],
    columns=4,
)

if not rows:
    ui.spacer(12)
    ui.empty_state(
        "조건에 맞는 학생이 없습니다",
        "범위를 HIGH + MEDIUM 으로 넓히거나 위험 영역·상담 상태 필터를 지워보세요.",
    )
    st.stop()

# ── 명단 ───────────────────────────────────────────────────────────────────
# 표(dataframe) 대신 **카드**다. 담당자가 한 줄에서 알아야 하는 것은
# 확률 · 등급 · 무엇이 위험한가 · 지금 어디까지 갔는가 넷이고,
# 표의 격자보다 카드가 그 넷을 훨씬 빨리 읽힌다.

#: 한 페이지에 세우는 학생 수. 더 늘리면 스크롤로 카드를 "찾게" 된다.
PER_PAGE = 8

pages = max(1, math.ceil(len(rows) / PER_PAGE))
page = min(int(st.session_state.get("risk_page", 0)), pages - 1)
st.session_state["risk_page"] = page
window = rows[page * PER_PAGE:(page + 1) * PER_PAGE]

ui.section("우선 처리 명단", f"카드를 누르면 상세 분석이 팝업으로 열립니다 · 전체 {len(rows):,}명")


def status_control(picked) -> None:
    """팝업 맨 아래 — 상담 진행 상태. 화면 밖으로 뺐던 것을 여기로 들였다.

    명단 화면에 따로 두면 "학생을 고르고 → 아래로 내려가 상태를 바꾸는" 왕복이 생긴다.
    상세를 보는 자리에서 바로 남기는 것이 실제 상담 흐름과 같다.
    """
    sid = picked.student.student_id
    ui.spacer(10)
    st.markdown('<div class="dlg-status">상담 진행 상태</div>', unsafe_allow_html=True)
    with st.container(key="dlg_status"):
        chosen = st.segmented_control(
            "상담 진행 상태",
            options=list(followup.STATUSES),
            default=followup.status_of(table, sid),
            format_func=lambda s: f"{followup.MARKS[s]} {s}",
            label_visibility="collapsed",
            key=f"dlg_status_{sid}",
        )
    # 팝업 안에서 st.rerun() 을 부르면 팝업이 닫힌다. 기록만 하고 닫을 때 새로 그린다
    # (`st.dialog(on_dismiss="rerun")`).
    if chosen and chosen != followup.status_of(table, sid):
        followup.set_status(table, sid, chosen)
    st.caption(f"학생 목록에서 열기 → {STUDENT_PAGE_URL}?student={quote(sid)}")


for row in window:
    student = row.student
    sid = student.student_id
    level = row.result.risk_level
    percent = row.result.dropout_percent
    status = followup.status_of(table, sid)

    # 요인과 조치가 같은 말을 반복하면 카드가 시끄러워진다 — 겹치는 것은 한 번만.
    factors = [f.label for f in row.result.top_factors[:3]]
    if not factors:
        factors = [m.rule.title for m in row.recommendation.matched[:3]]
    seen = set(factors)
    actions = [m.rule.title for m in row.recommendation.matched
               if m.rule.title not in seen][:2]

    with st.container(key=f"rl_row_{sid}"):
        st.markdown(
            f"""<div class="rl-card">
      <div class="rl-ring" style="--p:{percent:.0f};--c:{RISK_COLORS[level]}">
        <span>{percent:.0f}%</span></div>
      <div class="rl-who">
        <div class="n">{escape(sid)}
          <span class="lv" style="--c:{RISK_COLORS[level]}">{level}</span></div>
        <div class="d">{escape(student.major_field)} ·
          {'주간' if student.attendance == 1 else '야간'}</div>
      </div>
      <div class="rl-tags">
        <div class="k">핵심 요인</div>
        <div class="t">{"".join(f'<span class="tag f">{escape(x)}</span>' for x in factors)}
          {"".join(f'<span class="tag a">{escape(x)}</span>' for x in actions)}</div>
      </div>
      <div class="rl-status">{ui.followup_pill_html(status)}</div>
    </div>""",
            unsafe_allow_html=True,
        )
        # 카드 전체를 덮는 투명 버튼. 카드가 곧 버튼이라 따로 "열기" 를 두지 않는다.
        if st.button("상세 열기", key=f"rl_open_{sid}", width="stretch"):
            student_detail.open_modal(row, key="risk", extra=status_control)

# ── 페이지 이동 ────────────────────────────────────────────────────────────
if pages > 1:
    ui.spacer(6)
    with st.container(key="rl_pager", horizontal=True, gap="small",
                      horizontal_alignment="center"):
        if st.button("← 이전", key="rl_prev", disabled=page == 0):
            st.session_state["risk_page"] = page - 1
            st.rerun()
        st.markdown(f'<div class="rl-page">{page + 1} / {pages}</div>',
                    unsafe_allow_html=True)
        if st.button("다음 →", key="rl_next", disabled=page >= pages - 1):
            st.session_state["risk_page"] = page + 1
            st.rerun()

st.caption("학생을 선택하면 예측 분석·맞춤 조치를 팝업으로 확인할 수 있습니다. "
           "상담 진행 상태도 팝업 안에서 바로 남깁니다.")

_KEEP = CATEGORY_COLORS  # 카테고리 색을 이 모듈 경유로도 얻게 남긴다.
