"""화면에 세울 **이름과 학년**.

원본(UCI)은 익명 데이터라 이름도 학년도 없다. 그런데 명단 화면에서 학번만 스무 줄
늘어서면 사람이 아니라 일련번호를 보게 되고, 발표에서 "누구를 돕는 화면인가" 가
전달되지 않는다. 그래서 **화면 예시용 값**을 만든다.

지켜야 하는 두 가지
    1. 학번마다 **항상 같은 값**이 나와야 한다. 새로고침마다 이름이 바뀌면
       그 화면은 아무도 믿지 않는다. 그래서 난수가 아니라 학번의 해시를 쓴다.
    2. **만든 값임을 화면에서 밝힌다.** 명단 화면 캡션 한 줄이 그 역할을 한다
       (`views/2_students.py`). 이 파일을 지우면 그 문구도 같이 지워야 한다.

실제 학사 시스템에 붙일 때는 이 모듈을 걷어내고 학적 테이블의 이름·학년을 그대로 쓴다.
"""

from __future__ import annotations

from hashlib import blake2b

#: 성 · 이름 앞 글자 · 이름 뒤 글자. 곱하면 조합이 충분히 많아 겹침이 눈에 띄지 않는다.
_SURNAMES = ("김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
             "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍")
_FIRST = ("민", "서", "지", "현", "예", "준", "도", "하", "시", "유",
          "은", "채", "성", "동", "재", "수", "가", "주", "태", "다")
_LAST = ("준", "연", "우", "은", "호", "아", "진", "빈", "린", "율",
         "현", "성", "희", "환", "겸", "솔", "람", "찬", "훈", "결")

#: 학년 분포. 1·2학년이 중도탈락 위험이 높다는 실제 경향에 맞춰 앞쪽을 두껍게 둔다.
_YEARS = (1, 1, 1, 2, 2, 2, 3, 3, 4)


def _digest(student_id: str, salt: str) -> int:
    """학번 + 용도로 만드는 고정 해시. 같은 입력이면 언제나 같은 숫자다."""
    return int.from_bytes(
        blake2b(f"{salt}:{student_id}".encode("utf-8"), digest_size=4).digest(), "big"
    )


def display_name(student_id: str) -> str:
    """학번에 대응하는 표시용 이름 (원본에 없는 값이다)."""
    seed = _digest(student_id, "name")
    return (_SURNAMES[seed % len(_SURNAMES)]
            + _FIRST[(seed // len(_SURNAMES)) % len(_FIRST)]
            + _LAST[(seed // (len(_SURNAMES) * len(_FIRST))) % len(_LAST)])


def display_year(student_id: str) -> int:
    """학번에 대응하는 표시용 학년 1~4 (원본에 없는 값이다)."""
    return _YEARS[_digest(student_id, "year") % len(_YEARS)]
