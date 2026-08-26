"""
팀 전처리 산출물(`data/processed/*.csv`)을 **원래 값으로 되돌려** 화면에 쓴다.

왜 되돌리는가
    팀이 올린 CSV 는 이미 표준화·원-핫 인코딩된 상태다 (81 피처).
    `-0.55` 같은 z-score 를 담당자에게 보여줄 수는 없다. 학습된 전처리기
    (`models/preprocessor.joblib`)가 스케일러의 평균·표준편차와 인코더의 범주를
    모두 들고 있으므로, **그 역함수로 원래 단위를 정확히 복원**할 수 있다.

    복원된 값은 지어낸 수치가 아니라 **UCI 원본 데이터 그대로**다.

왜 폴백이 필요한가
    `data/processed/*.csv` 는 팀 `.gitignore` 대상이라 브랜치에 따라 없을 수 있다.
    파일이 없으면 합성 더미 명단으로 조용히 물러나고, **어느 쪽을 쓰고 있는지
    화면에 표시한다.** 팀원이 최종 데이터를 그 경로에 넣기만 하면 자동으로 바뀐다.

정답 라벨(`target`)에 대하여
    CSV 에는 실제 결과가 들어 있다. 하지만 지금 예측기는 학습된 모델이 아니라
    DummyPredictor 다. **정답과 나란히 놓으면 정확도처럼 읽히므로 화면에 쓰지 않는다.**
    실제 모델이 연결된 뒤 평가 화면을 만들 때 쓰라고 `RealRoster.labels` 로만 남겨 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from utils.feature_mapping import StudentInput
from utils.schema import PREPROCESSOR_PATH

DATA_DIR = PREPROCESSOR_PATH.parent.parent / "data" / "processed"

#: 화면 명단으로 쓸 파일. test 는 학습에 쓰이지 않은 홀드아웃이라 데모에 가장 적절하다.
CANDIDATE_FILES: tuple[str, ...] = ("test.csv", "val.csv", "train.csv")

#: 전처리기 컬럼명 → StudentInput 속성명
_COLUMN_TO_KEY: dict[str, str] = {
    "Age at enrollment": "age_at_enrollment",
    "Gender": "gender",
    "Marital status": "marital_status",
    "Major_field": "major_field",
    "Daytime/evening attendance": "attendance",
    "Displaced": "displaced",
    "International": "international",
    "Educational special needs": "special_needs",
    "Admission_pathway": "admission_pathway",
    "Application order": "application_order",
    "Admission grade": "admission_grade",
    "Previous_education_level": "previous_education_level",
    "Previous qualification (grade)": "previous_qualification_grade",
    "Tuition fees up to date": "tuition_fees_up_to_date",
    "Scholarship holder": "scholarship_holder",
    "Debtor": "debtor",
    "Curricular units 1st sem (enrolled)": "sem1_enrolled",
    "Curricular units 1st sem (approved)": "sem1_approved",
    "Curricular units 1st sem (grade)": "sem1_grade",
    "Curricular units 1st sem (evaluations)": "sem1_evaluations",
    "Curricular units 1st sem (without evaluations)": "sem1_without_evaluations",
    "Curricular units 1st sem (credited)": "sem1_credited",
    "Curricular units 2nd sem (enrolled)": "sem2_enrolled",
    "Curricular units 2nd sem (approved)": "sem2_approved",
    "Curricular units 2nd sem (grade)": "sem2_grade",
    "Curricular units 2nd sem (evaluations)": "sem2_evaluations",
    "Curricular units 2nd sem (without evaluations)": "sem2_without_evaluations",
    "Curricular units 2nd sem (credited)": "sem2_credited",
    "Mother_education_level": "mother_education_level",
    "Father_education_level": "father_education_level",
    "Mother_occupation_group": "mother_occupation_group",
    "Father_occupation_group": "father_occupation_group",
}

#: 정수로 되돌려야 하는 속성 (스케일러 역변환은 실수를 준다)
_INT_KEYS = frozenset(
    {
        "age_at_enrollment", "gender", "marital_status", "attendance", "displaced",
        "international", "special_needs", "application_order",
        "tuition_fees_up_to_date", "scholarship_holder", "debtor",
        "sem1_enrolled", "sem1_approved", "sem1_evaluations",
        "sem1_without_evaluations", "sem1_credited",
        "sem2_enrolled", "sem2_approved", "sem2_evaluations",
        "sem2_without_evaluations", "sem2_credited",
    }
)


@dataclass(frozen=True)
class RealRoster:
    """복원된 실제 학생 명단."""

    students: list[StudentInput]
    labels: list[int]        # 1=Dropout, 0=Non-Dropout. **화면에 쓰지 않는다** (모듈 설명 참조)
    source: str              # 어느 파일에서 왔는지 (화면에 밝힌다)

    @property
    def dropout_rate(self) -> float:
        return sum(self.labels) / len(self.labels) if self.labels else 0.0


def available_file() -> Path | None:
    """쓸 수 있는 전처리 CSV 를 찾는다. 없으면 None."""
    for name in CANDIDATE_FILES:
        path = DATA_DIR / name
        if path.exists():
            return path
    return None


def load_real_students(limit: int | None = None) -> RealRoster | None:
    """전처리 CSV → 원래 값의 StudentInput 목록.

    파일이 없거나 되돌리다 실패하면 **None** 을 돌려준다. 호출부가 더미로 물러난다.
    """
    path = available_file()
    if path is None:
        return None

    try:
        import joblib
        import numpy as np
        import pandas as pd
    except ImportError:
        return None

    try:
        preprocessor = joblib.load(PREPROCESSOR_PATH)
        frame = pd.read_csv(path)
    except (OSError, ValueError):
        return None

    if "target" not in frame.columns:
        return None

    labels = [int(v) for v in frame["target"].tolist()]
    matrix = frame.drop(columns=["target"])

    try:
        num_cols = list(preprocessor.transformers_[0][2])
        cat_cols = list(preprocessor.transformers_[1][2])
        rem_cols = list(preprocessor.transformers_[2][2])
        encoder = preprocessor.named_transformers_["cat"]
        scaler = preprocessor.named_transformers_["num"]

        n_num = len(num_cols)
        n_cat = sum(len(c) for c in encoder.categories_)

        numeric = scaler.inverse_transform(matrix.iloc[:, :n_num].to_numpy(dtype=float))
        categorical = encoder.inverse_transform(
            matrix.iloc[:, n_num : n_num + n_cat].to_numpy(dtype=float)
        )
        remainder = matrix.iloc[:, n_num + n_cat :].to_numpy()
    except (AttributeError, IndexError, ValueError, KeyError):
        return None

    rows = numeric.shape[0]
    if limit is not None:
        rows = min(rows, limit)

    students: list[StudentInput] = []
    for i in range(rows):
        values: dict[str, object] = {}
        for block, columns in (
            (numeric[i], num_cols),
            (categorical[i], cat_cols),
            (remainder[i], rem_cols),
        ):
            for value, column in zip(block, columns):
                key = _COLUMN_TO_KEY.get(column)
                if key is None:
                    continue                       # 파생변수는 StudentInput 이 직접 계산한다
                values[key] = _coerce(key, value)

        values["student_id"] = f"S{i + 1:04d}"
        try:
            students.append(StudentInput(**values))  # type: ignore[arg-type]
        except TypeError:
            return None                              # 스키마가 어긋났다 — 더미로 물러난다

    if not students:
        return None
    return RealRoster(students=students, labels=labels[:rows], source=path.name)


def _coerce(key: str, value: object) -> object:
    """역변환 결과를 StudentInput 이 기대하는 자료형으로 맞춘다.

    스케일러를 되돌리면 정수여야 할 값도 `5.999999` 같은 실수로 나온다.
    반올림하지 않으면 '수강 6과목'이 '5과목'이 된다.
    """
    if key in _INT_KEYS:
        return int(round(float(value)))
    if key in ("major_field", "admission_pathway", "previous_education_level",
               "mother_education_level", "father_education_level",
               "mother_occupation_group", "father_occupation_group"):
        return str(value)
    return round(float(value), 2)
