"""
더미 학생 명단 생성 / 로딩.

⚠️ 여기서 만든 데이터는 UCI 원본 데이터가 아니다.
    팀 전처리(Model B)의 **컬럼 구조와 값 분포만** 따르는 합성 데이터이며,
    화면과 필터를 검증하기 위한 것이다. 통계 분석이나 모델 학습에 쓰지 않는다.
    실제 분석은 팀의 데이터 담당자가 원본 4,424건으로 수행한다.

범주 비율은 reports/preprocessing_report.md 의 인원 표를 그대로 가중치로 썼다.
그래야 대시보드의 전공계열·전형 분포가 실제 데이터와 비슷한 모양으로 보인다.

시드를 고정한 이유
    발표 중 새로고침할 때마다 명단과 KPI 가 달라지면 설명을 할 수 없다.
    같은 시드 → 항상 같은 80명. CSV 를 지워도 똑같이 재생성된다.
"""

from __future__ import annotations

import csv
from dataclasses import fields
from pathlib import Path

import numpy as np

from utils.feature_mapping import (
    ADMISSION_PATHWAYS,
    MAJOR_FIELDS,
    OCCUPATION_GROUPS,
    PARENT_EDUCATION_LEVELS,
    PREVIOUS_EDUCATION_LEVELS,
    StudentInput,
    student_from_mapping,
)

#: 고정 시드 — 바꾸면 명단 전체가 바뀐다.
SEED = 20260831
DEFAULT_STUDENT_COUNT = 80

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CSV_PATH = DATA_DIR / "dummy_students.csv"

CSV_COLUMNS = [f.name for f in fields(StudentInput)]

# ---------------------------------------------------------------------------
# 범주 가중치 — preprocessing_report.md 의 인원 수를 그대로 옮긴 것
# ---------------------------------------------------------------------------

MAJOR_FIELD_WEIGHTS = (1189, 916, 570, 441, 351, 331, 252, 192, 170, 12)
ADMISSION_PATHWAY_WEIGHTS = (2704, 785, 449, 248, 139, 54, 30, 15)
PREVIOUS_EDUCATION_WEIGHTS = (3717, 255, 232, 189, 16, 15)
MOTHER_EDUCATION_WEIGHTS = (2590, 1069, 14, 534, 81, 136)
FATHER_EDUCATION_WEIGHTS = (2949, 906, 28, 357, 62, 122)
MOTHER_OCCUPATION_WEIGHTS = (1933, 1371, 793, 231, 96)
FATHER_OCCUPATION_WEIGHTS = (2034, 920, 1004, 212, 254)

#: Marital status 원본 코드 1~6. 미혼이 압도적으로 많다.
MARITAL_STATUS_WEIGHTS = (3919, 379, 4, 91, 25, 6)


def _weighted(rng: np.random.Generator, choices, weights) -> str:
    probabilities = np.asarray(weights, dtype=float)
    probabilities = probabilities / probabilities.sum()
    return str(rng.choice(list(choices), p=probabilities))


def generate_students(count: int = DEFAULT_STUDENT_COUNT, seed: int = SEED) -> list[StudentInput]:
    """합성 학생 명단을 만든다.

    학생마다 잠재 학업역량(latent) 하나를 뽑고, 이수율·성적·경제 상태를 거기에
    느슨하게 연동시킨다. 그래야 화면의 위험등급 분포가 뭉치지 않고 퍼진다.
    """
    rng = np.random.default_rng(seed)
    students: list[StudentInput] = []

    for i in range(count):
        latent = float(np.clip(rng.beta(2.6, 2.0), 0.02, 0.99))  # 0=매우 낮음 … 1=매우 높음

        attendance = int(rng.random() > 0.11)

        # 나이: 대부분 18~23세, 만학도 꼬리
        if rng.random() < 0.78:
            age = int(rng.integers(18, 24))
        else:
            age = int(np.clip(round(rng.normal(33, 8)), 24, 62))

        # 경제 상태: 학업역량이 낮을수록 미납/채무 확률이 조금 더 높게 (상관만 부여)
        tuition_ok = int(rng.random() > (0.05 + 0.22 * (1 - latent)))
        debtor = int(rng.random() < (0.04 + 0.18 * (1 - latent)))
        scholarship = int(rng.random() < (0.08 + 0.34 * latent))

        # 1학기: 수강 과목 수 → 이수 과목 수(latent 기반 이항분포) → 성적
        sem1_enrolled = int(np.clip(round(rng.normal(6.2, 1.1)), 3, 10))
        p1 = float(np.clip(0.18 + 0.80 * latent + rng.normal(0, 0.08), 0.0, 1.0))
        sem1_approved = int(rng.binomial(sem1_enrolled, p1))
        sem1_grade = _grade_from(p1, rng)
        sem1_no_eval = int(rng.binomial(max(sem1_enrolled - sem1_approved, 0), 0.30))
        sem1_evaluations = int(max(sem1_enrolled - sem1_no_eval, 0) + rng.integers(0, 3))
        sem1_credited = int(rng.binomial(2, 0.06))

        # 2학기: 1학기 흐름을 이어가되 소폭 변동. 일부는 아예 수강하지 않는다(미등록).
        if rng.random() < 0.05 and latent < 0.35:
            sem2_enrolled = 0
            sem2_approved = 0
            sem2_grade = 0.0
            sem2_no_eval = 0
            sem2_evaluations = 0
            sem2_credited = 0
        else:
            sem2_enrolled = int(np.clip(sem1_enrolled + rng.integers(-1, 2), 3, 10))
            p2 = float(np.clip(p1 + rng.normal(-0.02, 0.13), 0.0, 1.0))
            sem2_approved = int(rng.binomial(sem2_enrolled, p2))
            sem2_grade = _grade_from(p2, rng)
            sem2_no_eval = int(rng.binomial(max(sem2_enrolled - sem2_approved, 0), 0.30))
            sem2_evaluations = int(max(sem2_enrolled - sem2_no_eval, 0) + rng.integers(0, 3))
            sem2_credited = int(rng.binomial(2, 0.06))

        students.append(
            StudentInput(
                student_id=f"S{i + 1:03d}",
                name="",  # 원본 데이터에 이름이 없으므로 지어내지 않는다.
                age_at_enrollment=age,
                gender=int(rng.integers(0, 2)),
                marital_status=int(
                    _weighted(rng, ("1", "2", "3", "4", "5", "6"), MARITAL_STATUS_WEIGHTS)
                ),
                major_field=_weighted(rng, MAJOR_FIELDS, MAJOR_FIELD_WEIGHTS),
                attendance=attendance,
                displaced=int(rng.random() < 0.48),
                international=int(rng.random() < 0.025),
                special_needs=int(rng.random() < 0.011),
                admission_pathway=_weighted(rng, ADMISSION_PATHWAYS, ADMISSION_PATHWAY_WEIGHTS),
                application_order=int(min(rng.geometric(0.55) - 1, 9)),
                admission_grade=round(float(np.clip(rng.normal(120 + 22 * latent, 11), 95, 190)), 1),
                previous_education_level=_weighted(
                    rng, PREVIOUS_EDUCATION_LEVELS, PREVIOUS_EDUCATION_WEIGHTS
                ),
                previous_qualification_grade=round(
                    float(np.clip(rng.normal(125 + 18 * latent, 13), 95, 190)), 1
                ),
                tuition_fees_up_to_date=tuition_ok,
                scholarship_holder=scholarship,
                debtor=debtor,
                sem1_enrolled=sem1_enrolled,
                sem1_approved=sem1_approved,
                sem1_grade=sem1_grade,
                sem1_evaluations=sem1_evaluations,
                sem1_without_evaluations=sem1_no_eval,
                sem1_credited=sem1_credited,
                sem2_enrolled=sem2_enrolled,
                sem2_approved=sem2_approved,
                sem2_grade=sem2_grade,
                sem2_evaluations=sem2_evaluations,
                sem2_without_evaluations=sem2_no_eval,
                sem2_credited=sem2_credited,
                mother_education_level=_weighted(
                    rng, PARENT_EDUCATION_LEVELS, MOTHER_EDUCATION_WEIGHTS
                ),
                father_education_level=_weighted(
                    rng, PARENT_EDUCATION_LEVELS, FATHER_EDUCATION_WEIGHTS
                ),
                mother_occupation_group=_weighted(
                    rng, OCCUPATION_GROUPS, MOTHER_OCCUPATION_WEIGHTS
                ),
                father_occupation_group=_weighted(
                    rng, OCCUPATION_GROUPS, FATHER_OCCUPATION_WEIGHTS
                ),
            )
        )
    return students


def _grade_from(pass_rate: float, rng: np.random.Generator) -> float:
    """이수율과 느슨하게 연동된 평균 성적(0~20). 이수 실패가 많으면 성적도 낮다."""
    if pass_rate <= 0.01:
        return 0.0
    base = 9.0 + 8.0 * pass_rate
    return round(float(np.clip(rng.normal(base, 1.3), 0.0, 20.0)), 1)


# ---------------------------------------------------------------------------
# CSV 입출력
# ---------------------------------------------------------------------------

def save_students(students: list[StudentInput], path: Path = DEFAULT_CSV_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for student in students:
            writer.writerow({k: v for k, v in student.to_ui_dict().items() if k in CSV_COLUMNS})
    return path


def load_students(
    path: Path = DEFAULT_CSV_PATH, count: int = DEFAULT_STUDENT_COUNT
) -> list[StudentInput]:
    """CSV 를 읽어 온다. 파일이 없거나 깨졌으면 같은 시드로 다시 만든다."""
    if path.exists():
        try:
            with path.open(encoding="utf-8", newline="") as fp:
                rows = list(csv.DictReader(fp))
            if rows:
                return [student_from_mapping(row) for row in rows]
        except (OSError, ValueError, TypeError):
            pass  # 아래에서 재생성한다.
    students = generate_students(count)
    try:
        save_students(students, path)
    except OSError:
        pass  # 읽기 전용 환경이어도 앱은 떠야 한다.
    return students


if __name__ == "__main__":  # python -m utils.dummy_data 로 재생성
    saved = save_students(generate_students())
    print(f"더미 학생 {DEFAULT_STUDENT_COUNT}명을 저장했습니다: {saved}")
