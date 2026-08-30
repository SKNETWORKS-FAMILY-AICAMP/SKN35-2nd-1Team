"""
학생 한 명의 상세 분석 — **두 화면이 공유하는 단 하나의 구현.**

학생 목록(찾는 화면)과 집중관리 대상(처리하는 화면)이 같은 학생을 보여준다.
각자 그리면 한쪽만 고쳐지는 사고가 반드시 난다. 그래서 컴포넌트로 뺐다.
(화면 파일끼리는 import 할 수 없다 — 파일 이름이 숫자로 시작해서 모듈이 아니다.)

세로로 다 쌓으면 한 화면에 블록이 열 개를 넘어가고, 그러면 담당자가 매일 쓰는
**조치**가 근거·시뮬레이션에 묻힌다. 셋으로 접고 기본값을 조치로 둔다.
"""

from __future__ import annotations

import streamlit as st

from components import ui, whatif
from components.theme import RISK_COLORS
from services import followup
from services.predictor import RISK_LABELS_KO
from services.prediction_service import get_service


def render(row, *, key: str) -> None:
    """`RosterRow` 하나를 조치 / 위험 예측 분석 / What-if 세 탭으로."""
    tabs = st.tabs(["조치", "위험 예측 분석", "What-if"])
    suffix = f"{key}_{row.student.student_id}"

    with tabs[0]:
        ui.action_panel(row.student, row.result, row.recommendation)
        ui.spacer(14)
        ui.case_downloads(row.student, row.result, row.recommendation, key=suffix)

    with tabs[1]:
        ui.evidence_panel(row.student, row.result, row.recommendation)

    with tabs[2]:
        whatif.render(row.student, row.result, row.recommendation, get_service(),
                      key=suffix, show_heading=False)


# ---------------------------------------------------------------------------
# 팝업 — 명단을 떠나지 않고 한 명을 들여다본다
# ---------------------------------------------------------------------------
#
# 왜 아래로 펼치지 않고 팝업인가
#     명단이 400px 짜리 표라, 학생을 고르면 상세는 **화면 밖 아래**에 열린다.
#     담당자는 스크롤을 내려 읽고 다시 올려 다음 학생을 고른다. 한 명 볼 때마다
#     그 왕복이 생긴다. 팝업은 표를 그대로 둔 채 위에 얹히므로 왕복이 없다.


# 팝업 안에서 상담 상태를 바꾸므로, 닫을 때 화면을 새로 그려 목록·집계에 반영한다.
@st.dialog("학생 상세 분석", width="large", on_dismiss="rerun")
def _modal(row, key: str, extra=None) -> None:
    student, result = row.student, row.result
    level = result.risk_level
    sid = student.student_id

    # 머리에 셋을 나란히 둔다 — 누구인가 · 지금 어디까지 갔는가 · 얼마나 위험한가.
    # 상담 상태를 팝업 맨 아래 두면 스크롤을 내려야 보여서 아무도 안 쓴다.
    who_col, status_col = st.columns([1.05, 1], vertical_alignment="center")
    with who_col:
        st.markdown(
            f"""<div class="dlg-head">
      <div class="who">
        <div class="avatar" style="--c:{RISK_COLORS[level]}">{sid[-2:]}</div>
        <div>
          <div class="nm">{sid}</div>
          <div class="sub">{student.major_field} · {result.dropout_percent:.1f}% 중도탈락 확률</div>
        </div>
      </div>
    </div>""",
            unsafe_allow_html=True,
        )
    with status_col:
        with st.container(key="dlg_head_bar", horizontal=True, gap="small",
                          horizontal_alignment="right", vertical_alignment="center"):
            table = followup.load()
            current = followup.status_of(table, sid)
            chosen = st.segmented_control(
                "상담 진행 상태",
                options=list(followup.STATUSES),
                default=current,
                format_func=lambda s: f"{followup.MARKS[s]} {s}",
                label_visibility="collapsed",
                key=f"dlg_status_{sid}",
            )
            # 팝업 안에서 st.rerun() 을 부르면 팝업이 닫힌다. 기록만 하고,
            # 닫을 때 화면을 새로 그린다(`on_dismiss="rerun"`).
            if chosen and chosen != current:
                followup.set_status(table, sid, chosen)
            st.markdown(
                f'<div class="lv" style="--c:{RISK_COLORS[level]}">'
                f'{level} · {RISK_LABELS_KO[level]}</div>',
                unsafe_allow_html=True,
            )

    render(row, key=key)
    if extra is not None:
        extra(row)


def open_modal(row, *, key: str, extra=None) -> None:
    """상세를 팝업으로 연다. `extra(row)` 는 팝업 맨 아래에 덧붙일 것이 있을 때."""
    _modal(row, key, extra)
