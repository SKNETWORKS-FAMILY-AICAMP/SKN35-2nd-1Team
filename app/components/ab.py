"""
A/B 비교 안내 — 예측 화면 두 안을 팀원이 견줘 보게 하는 임시 장치.

**정하고 나면 이 파일과 진 쪽 화면을 함께 지운다.** 남겨 두면 안내 문구가 발표장에서
그대로 노출되고, 화면 수도 하나 더 많은 채로 굳는다.
"""

from __future__ import annotations

import streamlit as st

from components import ui
from components.theme import COLORS

#: 두 안의 이름과 한 줄 설명. 사이드바 라벨과 글자를 맞춘다.
LAYOUTS: dict[str, tuple[str, str]] = {
    "A": ("한 화면", "32개 입력을 네 탭에 담아 한 번에 보고 바로 분석한다."),
    "B": ("단계형", "네 단계로 나눠 묻고, 단계마다 알아낸 것을 쌓아 마지막에 전부 보여준다."),
}


def ab_notice(current: str) -> None:
    """지금 보는 안이 무엇이고 다른 안은 무엇인지 한 줄로 밝힌다."""
    other = "B" if current == "A" else "A"
    now_name, now_desc = LAYOUTS[current]
    other_name, _ = LAYOUTS[other]

    ui.banner(
        f"안 {current}",
        f"<b>{now_name}</b> — {now_desc} "
        f"사이드바의 <b>학생 위험 예측 ({other} · {other_name})</b> 과 견줘 보고 "
        "어느 쪽이 나은지 의견 주세요. <b>정해지면 한쪽은 지웁니다.</b>",
        foreground=COLORS["ink_soft"],
        background=COLORS["raised"],
        border=COLORS["line"],
    )
    st.caption(
        "두 화면은 같은 예측기·같은 규칙 엔진을 씁니다. 다른 것은 **입력을 받는 방식**뿐이라 "
        "결과 화면의 내용은 같습니다."
    )
