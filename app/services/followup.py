"""
상담 진행 상태 — 이 앱이 직접 들고 있는 유일한 '쓰기' 데이터.

학사 시스템이 없으므로 담당자가 어디까지 접촉했는지는 앱이 기억해야 한다.
예측·규칙과 달리 **사람이 넣는 값**이라, 다른 데이터와 섞이지 않게 여기 한 곳에 둔다.

저장 위치와 원칙
    `app/state/followup.json` 에 `{학생 ID: 상태}` 만 넣는다. 이름·연락처 같은
    개인정보는 애초에 데이터에 없고, 있어도 여기 넣지 않는다.
    이 폴더는 `.gitignore` 로 막았다 — **기기에 남는 운영 기록이지 팀 산출물이 아니다.**

읽기가 실패해도 앱은 그대로 뜬다. 상담 상태 때문에 명단 화면이 죽으면 안 된다.
"""

from __future__ import annotations

import json
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
STATE_FILE = STATE_DIR / "followup.json"

#: 진행 단계. 순서가 곧 진척도라 화면이 이 순서대로 그린다.
STATUSES: tuple[str, ...] = ("미착수", "연락함", "상담완료", "종결")
DEFAULT_STATUS = STATUSES[0]

#: 단계별 표시 기호. 색만으로 구분하지 않는다는 원칙은 여기서도 지킨다.
MARKS: dict[str, str] = {
    "미착수": "○",
    "연락함": "◐",
    "상담완료": "◑",
    "종결": "●",
}


def load() -> dict[str, str]:
    """{학생 ID: 상태}. 파일이 없거나 깨져 있으면 빈 상태로 간다."""
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(k): v for k, v in raw.items()
        if isinstance(v, str) and v in STATUSES
    }


def save(table: dict[str, str]) -> bool:
    """기록을 파일에 남긴다. 실패해도 예외를 내보내지 않는다(화면이 죽으면 안 된다)."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(
            json.dumps(table, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError:
        return False
    return True


def status_of(table: dict[str, str], student_id: str) -> str:
    return table.get(student_id, DEFAULT_STATUS)


def set_status(table: dict[str, str], student_id: str, status: str) -> dict[str, str]:
    """상태를 바꾼 새 표를 돌려주고 파일에도 남긴다.

    기본값(`미착수`)은 **저장하지 않는다.** 손대지 않은 학생까지 파일에 쌓이면
    885명이 통째로 들어가고, 그러면 무엇을 실제로 다뤘는지 알 수 없어진다.
    """
    updated = dict(table)
    if status == DEFAULT_STATUS:
        updated.pop(student_id, None)
    else:
        updated[student_id] = status
    save(updated)
    return updated


def counts(table: dict[str, str], student_ids) -> dict[str, int]:
    """주어진 학생들의 단계별 인원. 화면 상단 집계가 이걸 쓴다."""
    tally = {status: 0 for status in STATUSES}
    for sid in student_ids:
        tally[status_of(table, str(sid))] += 1
    return tally


def touched(table: dict[str, str], student_ids) -> int:
    """한 번이라도 손댄 학생 수 (미착수가 아닌 학생)."""
    return sum(1 for sid in student_ids if status_of(table, str(sid)) != DEFAULT_STATUS)
