"""
화면 4 — 집중관리 대상 (위험학생 목록).

학생 목록이 **찾는 화면**이라면 여기는 **처리하는 화면**이다. 위험한 순서대로 줄을
세워 놓고 위에서부터 내려가며 접촉 상태를 남긴다. 그래서 이 화면에만 있는 것이
`상담 진행 상태` 다 — 앱이 유일하게 **쓰는** 데이터다.

상세 분석은 학생 목록의 `detail()` 을 그대로 부른다. 같은 학생을 두 화면에서 다르게
보여줄 이유가 없고, 한쪽만 고쳐지는 사고를 원천에서 막는다.
"""

from __future__ import annotations

from html import escape
from urllib.parse import quote

import streamlit as st

from components import student_detail, ui
from components.state import cached_roster, start_page
from components.theme import CATEGORY_COLORS, COLORS, RISK_COLORS
from rules.recommendation_rules import PRIORITY_LABELS
from services import followup
from services.predictor import RISK_CATEGORIES
from services.prediction_service import get_service

#: 필터 프리셋. 담당자가 실제로 쓰는 두 가지 폭이다.
#: 학생 목록 화면의 주소. `st.navigation` 이 파일명에서 만드는 경로와 같아야 한다.
STUDENT_PAGE_URL = "students"

#: 왼쪽이 기본값이다 — 담당자가 여는 순간 보이는 폭.
SCOPES: dict[str, tuple[str, ...]] = {
    "HIGH + MEDIUM": ("HIGH", "MEDIUM"),
    "HIGH 만": ("HIGH",),
}


def core_factor(row) -> str:
    """모델이 본 1순위 위험요인. 없으면 규칙 쪽 사유로 대신한다."""
    if row.result.top_factors:
        return row.result.top_factors[0].label
    if row.recommendation.matched:
        return row.recommendation.matched[0].rule.title
    return "—"


def action_tag(row) -> str:
    """권장 조치 태그 — `언제 · 어느 영역` 한 줄.

    조치 내용을 다 적으면 표가 읽히지 않는다. 담당자가 줄을 훑을 때 필요한 건
    **얼마나 급한가**와 **누구 일인가** 둘뿐이고, 나머지는 상세에서 본다.
    """
    if not row.recommendation.matched:
        return "모니터링"
    top = min(m.rule.priority for m in row.recommendation.matched)
    labels = row.recommendation.category_labels
    head = " · ".join(labels[:2])
    more = f" +{len(labels) - 2}" if len(labels) > 2 else ""
    return f"{PRIORITY_LABELS.get(top, '검토')} · {head}{more}"


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

service = get_service()
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
ui.section("우선 처리 명단", "행을 선택하면 상세 분석이 팝업으로 열립니다.")

import pandas as pd  # noqa: E402  (표를 만들 때만 필요하다)

listing = pd.DataFrame.from_records([
    {
        "학번": row.student.student_id,
        "중도탈락 확률(%)": row.result.dropout_percent,
        "등급": row.result.risk_level,
        "핵심 요인": core_factor(row),
        "권장 조치": action_tag(row),
        "상담 상태": (f"{followup.MARKS[followup.status_of(table, row.student.student_id)]} "
                  f"{followup.status_of(table, row.student.student_id)}"),
        "전공 계열": row.student.major_field,
    }
    for row in rows
])

event = st.dataframe(
    listing,
    hide_index=True,
    width="stretch",
    height=430,
    on_select="rerun",
    selection_mode="single-row",
    key="risk_table",
    column_config={
        "학번": st.column_config.TextColumn("학번", width="small"),
        "중도탈락 확률(%)": st.column_config.ProgressColumn(
            "확률", format="%.1f%%", min_value=0.0, max_value=100.0),
        "등급": st.column_config.TextColumn("등급", width="small"),
        "권장 조치": st.column_config.TextColumn(
            "권장 조치", help="언제 · 어느 영역. 구체적인 프로그램은 아래 상세에 있습니다."),
        "상담 상태": st.column_config.TextColumn(
            "상담 상태", help="학생을 선택하면 아래에서 바꿀 수 있습니다."),
    },
)

selected = list(getattr(event.selection, "rows", []) or [])
if not selected:
    ui.spacer(10)
    ui.empty_state(
        "학생을 선택하지 않았습니다",
        "위 표에서 한 명을 선택하면 조치·분석·What-if 와 상담 상태 기록이 열립니다.",
    )
    st.stop()

row = rows[selected[0]]
student_id = row.student.student_id

# ── 상담 진행 상태 — 이 앱이 유일하게 쓰는 데이터 ──────────────────────────
ui.section(f"{student_id} 처리", "상태를 바꾸면 이 기기에 바로 기록됩니다.")

current = followup.status_of(table, student_id)
status_col, link_col = st.columns([2.2, 1], gap="large")
with status_col:
    chosen = st.radio(
        "상담 진행 상태",
        options=list(followup.STATUSES),
        index=list(followup.STATUSES).index(current),
        horizontal=True,
        format_func=lambda s: f"{followup.MARKS[s]} {s}",
        key=f"status_{student_id}",
    )
    if chosen != current:
        followup.set_status(table, student_id, chosen)
        st.rerun()
with link_col:
    ui.spacer(24)
    st.link_button("학생 목록에서 열기 →",
                   f"{STUDENT_PAGE_URL}?student={quote(student_id)}", width="stretch")

ui.spacer(12)

# 학생 목록과 **같은 팝업**을 부른다. 두 곳에서 다르게 보여줄 이유가 없다.
if st.session_state.get("_risk_detail_open") != student_id:
    st.session_state["_risk_detail_open"] = student_id
    student_detail.open_modal(row, key="risk")

if st.button(f"{student_id} 상세 분석 열기", width="stretch", type="primary",
             key="reopen_risk_detail"):
    student_detail.open_modal(row, key="risk")

_KEEP = CATEGORY_COLORS  # 카테고리 색을 이 모듈 경유로도 얻게 남긴다.
