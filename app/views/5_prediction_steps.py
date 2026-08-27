"""
화면 B — 단계형(위저드) 위험 예측.

**같은 일을 하는 화면이 둘이다.** `2_prediction.py`(A · 한 화면)와 이 파일(B · 단계형)은
같은 예측기·같은 규칙 엔진 위에서 **입력을 받는 방식만** 다르다. 팀원이 둘 다 써 보고
어느 쪽으로 갈지 정하기 위한 것이므로, 정하고 나면 **한쪽은 지운다.**
둘 다 남기면 화면이 늘어나 지금 줄이려는 복잡도가 도로 커진다.

왜 이 흐름을 시도하는가
    입력 32개를 한 화면에 늘어놓으면 **설문지**가 된다. 탭으로 나눠도 "어디까지 했지"
    가 없다. 단계로 끊으면 한 번에 묻는 건 6~9개고, 진행 막대가 남은 양을 알려준다.

    그리고 단계마다 **방금 넣은 값에서 바로 알아낸 것**을 배지로 쌓아 준다.
    이게 이 흐름의 핵심이다 — 사용자가 값을 넣을 때마다 모델이 근거를 모으는 과정이
    눈에 보이고, 마지막 결과가 갑자기 튀어나온 숫자가 아니게 된다.

한계도 분명하다
    매일 쓰는 담당자에게는 4번 클릭이 낭비다. 그래서 이 흐름은 **처음 보는 사람**
    (심사위원·발표 청중·신규 담당자)의 경로이고, 매일 쓰는 경로는 학생 목록 쪽이다.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from components import ui
from components.ab import ab_notice
from components.theme import CATEGORY_COLORS, COLORS, RISK_COLORS, inject_css
from rules import recommendation_rules as rules
from services.prediction_service import get_service
from utils.feature_mapping import UI_FIELDS, FieldSpec, StudentInput

STEP_KEY = "wz_step"
#: 입력값을 담는 **평범한 dict**. 위젯 key 에 담지 않는 이유가 이 프로토타입의 핵심 교훈이다.
DATA_KEY = "wz_data"

#: 단계 정의 — (제목, 한 줄 설명, 묶을 그룹들)
#  마지막 단계에서 결과를 내므로 입력 단계는 넷이다.
STEPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("학생은 누구인가", "인구·사회 정보와 재학 형태를 확인합니다.", ("기본 정보",)),
    ("학업은 어땠나", "1·2학기 수강과 성취 — 모델이 가장 크게 보는 신호입니다.",
     ("1학기 학업", "2학기 학업")),
    ("경제 사정은 어떤가", "등록금·채무·장학 — 재정위험점수의 재료입니다.", ("경제 정보",)),
    ("어떻게 입학했나", "입학 경로와 가정 배경을 확인합니다.", ("입학 정보", "가정 배경")),
)
LAST = len(STEPS)          # 결과 단계의 인덱스

PRESET_HIGH: dict[str, Any] = dict(
    student_id="예시-HIGH", age_at_enrollment=30, gender=1, major_field="사회",
    attendance=0, displaced=1, admission_pathway="성인학습자 전형", application_order=3,
    admission_grade=118.0, tuition_fees_up_to_date=0, scholarship_holder=0, debtor=1,
    sem1_enrolled=6, sem1_approved=3, sem1_grade=10.8, sem1_without_evaluations=1,
    sem2_enrolled=6, sem2_approved=1, sem2_grade=7.9, sem2_without_evaluations=2,
)


# ---------------------------------------------------------------------------
# 이 화면 전용 스타일 — A/B 중 하나를 지울 때 같이 지워지도록 여기에 둔다
# ---------------------------------------------------------------------------

st.markdown(
    f"""<style>
  .wz-rail {{ display: flex; align-items: flex-start; gap: 0; margin: 8px 0 4px; }}
  .wz-node {{ flex: 1; text-align: center; position: relative; }}
  .wz-node .dot {{
    width: 30px; height: 30px; border-radius: 50%; margin: 0 auto 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: .78rem; font-weight: 800; background: #EDF1F6; color: {COLORS['faint']};
    border: 2px solid #EDF1F6; transition: all .2s ease; position: relative; z-index: 1;
  }}
  .wz-node .t {{ font-size: .74rem; font-weight: 700; color: {COLORS['faint']}; }}
  /* 노드 사이를 잇는 선 — 지나온 구간만 색이 찬다 */
  .wz-node::before {{
    content: ""; position: absolute; top: 15px; left: -50%; width: 100%;
    height: 2px; background: #EDF1F6;
  }}
  .wz-node:first-child::before {{ display: none; }}
  .wz-node.done::before, .wz-node.now::before {{ background: {COLORS['primary']}; }}
  .wz-node.done .dot {{
    background: {COLORS['primary']}; border-color: {COLORS['primary']}; color: #FFFFFF;
  }}
  .wz-node.done .t {{ color: {COLORS['muted']}; }}
  .wz-node.now .dot {{
    background: #FFFFFF; border-color: {COLORS['primary']}; color: {COLORS['primary']};
    box-shadow: 0 0 0 5px {COLORS['primary_soft']};
  }}
  .wz-node.now .t {{ color: {COLORS['primary']}; }}

  .wz-step {{
    font-size: .72rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase;
    color: {COLORS['primary']};
  }}
  .wz-title {{
    font-size: 1.72rem; font-weight: 800; letter-spacing: -.02em;
    color: {COLORS['ink']}; margin-top: 6px;
  }}
  .wz-desc {{ font-size: .9rem; color: {COLORS['muted']}; margin-top: 6px; }}

  /* 단계마다 쌓이는 "알아낸 것" — 이 흐름의 보상이다 */
  .wz-found {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .wz-chip {{
    display: inline-flex; align-items: center; gap: 7px;
    border: 1px solid var(--c, {COLORS['line']}); border-radius: 999px;
    background: #FFFFFF; padding: 7px 13px 7px 10px;
    font-size: .8rem; font-weight: 600; color: {COLORS['ink']};
  }}
  .wz-chip .m {{
    width: 16px; height: 16px; border-radius: 50%; background: var(--c);
    color: #FFFFFF; font-size: .6rem; font-weight: 800;
    display: flex; align-items: center; justify-content: center;
  }}
  .wz-chip .k {{ color: {COLORS['muted']}; font-weight: 700; }}
  .wz-empty {{ font-size: .8rem; color: {COLORS['faint']}; }}
</style>""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# 상태
# ---------------------------------------------------------------------------

def key_of(spec: FieldSpec) -> str:
    return f"wz_{spec.key}"


def init_state() -> None:
    """입력값의 주인은 `wz_data` 라는 평범한 dict 이고, 위젯 key 는 그 사본이다.

    🔴 **Streamlit 은 이번 실행에서 그려지지 않은 위젯의 session_state 를 버린다.**
    단계형 화면에서는 1단계 위젯이 2단계에서 사라지므로, 값을 위젯 key 에만 두면
    다음 단계로 넘어가는 순간 1단계 입력이 **에러 없이** 기본값으로 되돌아간다
    (실제로 겪었다 — 전공 '사회' 가 '경영' 으로 돌아가 있었다).

    그래서 매 실행 첫머리에, **위젯을 만들기 전에** 양방향으로 맞춘다.

        위젯 key 가 있으면  → 사용자가 바꾼 값이므로 저장소로 회수한다
        위젯 key 가 없으면  → 버려진 것이므로 저장소에서 복원한다

    위젯을 만든 뒤에 session_state 를 건드리면 예외가 나므로, 예시 채우기는
    '요청' 으로만 남기고 다음 실행의 이 지점에서 반영한다.
    """
    data = st.session_state.setdefault(DATA_KEY, {})
    for spec in UI_FIELDS:
        data.setdefault(spec.key, spec.default)
    st.session_state.setdefault(STEP_KEY, 0)
    st.session_state.setdefault("wz_id", "직접 입력")

    pending = st.session_state.pop("wz_pending_preset", None)
    if pending is not None:
        for spec in UI_FIELDS:
            if spec.key in pending:
                data[spec.key] = pending[spec.key]
        st.session_state["wz_id"] = str(pending.get("student_id", "직접 입력"))
        # 위젯 사본을 버려서 아래 동기화가 저장소 값으로 다시 채우게 한다.
        for spec in UI_FIELDS:
            st.session_state.pop(key_of(spec), None)

    for spec in UI_FIELDS:
        key = key_of(spec)
        if key in st.session_state:
            data[spec.key] = st.session_state[key]
        else:
            st.session_state[key] = data[spec.key]


def request_preset(values: dict[str, Any]) -> None:
    """예시 채우기 '요청'. 실제 반영은 다음 실행의 `init_state()` 가 한다."""
    st.session_state["wz_pending_preset"] = values


def current_student() -> StudentInput:
    """지금까지 입력된 값으로 학생을 조립한다.

    아직 안 지나온 단계의 값도 기본값으로 채워져 있으므로 **언제든 조립된다** —
    덕분에 단계 중간에도 파생변수를 계산해서 "알아낸 것"을 보여줄 수 있다.
    """
    data = st.session_state[DATA_KEY]
    values = {spec.key: data[spec.key] for spec in UI_FIELDS}
    return StudentInput(student_id=st.session_state.get("wz_id", "직접 입력"), **values)


def goto(step: int) -> None:
    st.session_state[STEP_KEY] = max(0, min(step, LAST))
    st.rerun()


# ---------------------------------------------------------------------------
# 조각
# ---------------------------------------------------------------------------

def render_rail(step: int) -> None:
    labels = [title for title, _, _ in STEPS] + ["결과"]
    nodes = []
    for index, label in enumerate(labels):
        state = "done" if index < step else ("now" if index == step else "")
        mark = "✓" if index < step else ("★" if index == len(labels) - 1 else str(index + 1))
        nodes.append(
            f'<div class="wz-node {state}"><div class="dot">{mark}</div>'
            f'<div class="t">{label}</div></div>'
        )
    st.markdown(f'<div class="wz-rail">{"".join(nodes)}</div>', unsafe_allow_html=True)


def render_field(spec: FieldSpec) -> None:
    """필드 하나. 값은 위젯 key 로만 오가고, 저장소와의 동기화는 `init_state()` 가 한다."""
    key = key_of(spec)

    if spec.kind == "text_select":
        choices = list(spec.choices or ())
        if st.session_state.get(key) not in choices:
            st.session_state[key] = spec.default
        labels = spec.labels or {}
        st.selectbox(spec.label, options=choices, key=key,
                     format_func=lambda v: labels.get(v, v), help=spec.help or None)
        return

    if spec.kind == "select":
        options = list(spec.options or {})
        if st.session_state.get(key) not in options:
            st.session_state[key] = spec.default
        st.selectbox(spec.label, options=options, key=key,
                     format_func=lambda c: (spec.options or {}).get(c, str(c)),
                     help=spec.help or None)
        return

    cast = type(spec.default)
    if spec.kind == "slider":
        st.session_state[key] = cast(
            min(max(st.session_state.get(key, spec.default), spec.minimum), spec.maximum)
        )
        st.slider(spec.label, min_value=cast(spec.minimum), max_value=cast(spec.maximum),
                  step=cast(spec.step or 1), key=key,
                  format="%.1f" if cast is float else None, help=spec.help or None)
        return

    st.session_state[key] = int(
        min(max(st.session_state.get(key, spec.default), spec.minimum), spec.maximum)
    )
    st.number_input(spec.label, min_value=int(spec.minimum), max_value=int(spec.maximum),
                    step=int(spec.step or 1), key=key, help=spec.help or None)


def findings(student: StudentInput, upto: int) -> list[tuple[str, str, str]]:
    """지나온 단계에서 **실제로 계산된** 사실만 (라벨, 값, 색).

    지어내지 않는다. 각 항목은 팀 파생변수나 원본 값 그대로이고,
    위험 쪽이면 색이 붙는다 — 그래서 배지가 쌓일수록 결과가 예고된다.
    """
    out: list[tuple[str, str, str]] = []
    ok, warn, bad = RISK_COLORS["LOW"], RISK_COLORS["MEDIUM"], RISK_COLORS["HIGH"]

    if upto >= 1:
        out.append(("전공", student.major_field, COLORS["primary"]))
        out.append(("수업", "주간" if student.attendance == 1 else "야간",
                    ok if student.attendance == 1 else warn))
        if student.age_at_enrollment > 22:
            out.append(("입학 나이", f"{student.age_at_enrollment}세", warn))
    if upto >= 2:
        rate = student.sem2_approval_rate
        out.append(("2학기 이수율", f"{rate:.0%}",
                    bad if rate < 0.5 else warn if rate < 0.75 else ok))
        out.append(("평균 성적", f"{student.average_grade:.1f}/20",
                    bad if student.average_grade < 11 else ok))
        if student.grade_change <= -2.0:
            out.append(("성적 변화", f"{student.grade_change:+.1f}점", bad))
    if upto >= 3:
        score = student.financial_risk_score
        out.append(("재정위험", f"{score}/3", bad if score >= 2 else warn if score else ok))
        if student.tuition_fees_up_to_date == 0:
            out.append(("등록금", "미납", bad))
    if upto >= 4:
        out.append(("지망", f"{student.application_order + 1}지망",
                    warn if student.application_order >= 3 else ok))
        out.append(("전형", student.admission_pathway, COLORS["primary"]))
    return out


def render_findings(student: StudentInput, upto: int) -> None:
    items = findings(student, upto)
    if not items:
        st.markdown('<div class="wz-empty">아직 알아낸 것이 없습니다.</div>',
                    unsafe_allow_html=True)
        return
    chips = "".join(
        f'<span class="wz-chip" style="--c:{color}"><span class="m">✓</span>'
        f'<span class="k">{label}</span>{value}</span>'
        for label, value, color in items
    )
    st.markdown(f'<div class="wz-found">{chips}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

inject_css()
init_state()
service = get_service()
step = int(st.session_state[STEP_KEY])
student = current_student()

st.markdown(
    '<div class="page-head"><div class="titles">'
    "<h1>학생 위험도 확인</h1>"
    "<p>네 단계로 물어보고 마지막에 전부 보여드립니다. 언제든 뒤로 갈 수 있습니다.</p>"
    "</div>"
    '<div class="meta"><div class="ds-eyebrow">Layout B</div>'
    '<div class="ds-sub" style="margin-top:4px">단계형</div></div></div>',
    unsafe_allow_html=True,
)
ab_notice("B")
ui.prototype_banner(service)
ui.spacer(10)
render_rail(step)
ui.spacer(14)

# ── 입력 단계 ──────────────────────────────────────────────────────────────
if step < LAST:
    title, desc, groups = STEPS[step]

    left, right = st.columns([1.55, 1], gap="large")

    with left, st.container(border=True):
        st.markdown(
            f'<div class="wz-step">Step {step + 1} / {LAST}</div>'
            f'<div class="wz-title">{title}</div>'
            f'<div class="wz-desc">{desc}</div>',
            unsafe_allow_html=True,
        )
        st.divider()
        specs = [s for s in UI_FIELDS if s.group in groups]
        columns = st.columns(2, gap="large")
        per = -(-len(specs) // 2)
        for index, spec in enumerate(specs):
            with columns[min(index // per, 1)]:
                render_field(spec)

    with right, st.container(border=True):
        st.markdown(
            '<div class="card-title">지금까지 알아낸 것</div>'
            '<div class="card-sub">입력한 값에서 바로 계산된 사실입니다. '
            "단계를 지날수록 쌓입니다.</div>",
            unsafe_allow_html=True,
        )
        ui.spacer(10)
        render_findings(student, step + 1)

        if step == 0:
            ui.spacer(16)
            st.markdown('<div class="ds-caption">발표용 예시로 한 번에 채우기</div>',
                        unsafe_allow_html=True)
            if st.button("HIGH · 복합 위험 예시", width="stretch", key="wz_preset"):
                request_preset(PRESET_HIGH)
                st.rerun()

    ui.spacer(12)
    back, forward = st.columns([1, 2], gap="small")
    with back:
        if st.button("← 이전", width="stretch", disabled=step == 0, key=f"wz_back_{step}"):
            goto(step - 1)
    with forward:
        label = "위험도 분석하기 →" if step == LAST - 1 else "다음 →"
        if st.button(label, width="stretch", type="primary", key=f"wz_next_{step}"):
            goto(step + 1)

    for problem in student.validate():
        st.warning(problem)

# ── 결과 단계 ──────────────────────────────────────────────────────────────
else:
    result = service.predict(student)
    recommendation = rules.evaluate(student, result)

    st.markdown(
        '<div class="wz-step">Result</div>'
        f'<div class="wz-title">{student.student_id} · 확인이 끝났습니다</div>'
        '<div class="wz-desc">입력한 값으로 계산한 위험도와, 그에 대응하는 교내 지원입니다.</div>',
        unsafe_allow_html=True,
    )
    ui.spacer(14)

    with st.container(border=True):
        st.markdown(
            '<div class="card-title">이 판단에 쓰인 사실</div>'
            '<div class="card-sub">네 단계에서 모은 것 전부입니다.</div>',
            unsafe_allow_html=True,
        )
        ui.spacer(10)
        render_findings(student, LAST)

    ui.spacer(16)
    ui.result_panel(student, result, recommendation, show_summary=True)

    ui.spacer(12)
    ui.case_downloads(student, result, recommendation, key="wizard")

    ui.spacer(14)
    again, back = st.columns(2, gap="small")
    with again:
        if st.button("↺ 처음부터 다시", width="stretch", key="wz_restart"):
            goto(0)
    with back:
        if st.button("← 입력 고치기", width="stretch", key="wz_edit"):
            goto(LAST - 1)

_KEEP = CATEGORY_COLORS  # 카테고리 색을 이 모듈 경유로도 얻을 수 있게 남긴다.
