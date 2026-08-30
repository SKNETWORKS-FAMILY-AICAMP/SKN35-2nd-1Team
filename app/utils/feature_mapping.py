"""
팀 전처리(Model B) ↔ 화면 입력 필드의 대응관계를 소유하는 모듈.

기준 문서
    reports/preprocessing_report.md   — 범주 일반화 정의
    notebooks/preprocess.ipynb        — 매핑 딕셔너리 원본
    data/processed/feature_schema.json— 컬럼 분류·순서 (utils/schema.py 가 읽는다)

이 파일의 규칙
    1. **범주 라벨 문자열은 노트북과 글자 단위로 같아야 한다.** 한 글자라도 다르면
       `preprocessor.joblib` 의 OneHotEncoder 가 미지 범주로 처리해 전부 0으로 만든다.
       아래 상수는 preprocess.ipynb 의 매핑 딕셔너리에서 그대로 가져온 값이다.
    2. **원본 코드(Course·Application mode 등)는 화면에 노출하지 않는다.** 팀 전처리가
       이미 제거한 컬럼이다. 화면은 일반화된 상위 개념만 받는다.
    3. **파생변수는 입력이 아니라 계산 결과다.** 담당자가 이수율을 직접 입력하지 않는다.
       계산 정의는 `StudentInput` 안에 한 번만 둔다 — 예측기·규칙엔진·모델이 같은 값을 쓴다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Literal

from utils.schema import model_input_columns

# ---------------------------------------------------------------------------
# 1. Target — 팀 전처리에서 이진으로 확정됐다
# ---------------------------------------------------------------------------

#: 1=Dropout, 0=Non-Dropout(Graduate + Enrolled). data/processed/feature_schema.json 기준.
TARGET_CLASSES: tuple[str, ...] = ("Dropout", "Non-Dropout")

TARGET_LABELS_KO: dict[str, str] = {
    "Dropout": "중도탈락",
    "Non-Dropout": "재학·졸업",
}

# ---------------------------------------------------------------------------
# 2. 일반화 범주 — preprocess.ipynb 의 매핑 딕셔너리와 문자열이 동일해야 한다
# ---------------------------------------------------------------------------

#: Application mode(18종) → Admission_pathway(8전형)
ADMISSION_PATHWAYS: tuple[str, ...] = (
    "일반전형",
    "성인학습자 전형",
    "편입·전과",
    "직업·기술교육 연계전형",
    "고등교육 이수자 전형",
    "특별전형",
    "외국인·국제학생 전형",
    "기타·특수전형",
)

#: Course(17개 학과) → Major_field(10계열)
MAJOR_FIELDS: tuple[str, ...] = (
    "보건",
    "경영",
    "사회",
    "예술·디자인",
    "자연·농생명",
    "인문·사회",
    "경영·서비스",
    "교육",
    "공학·IT",
    "공학·자연",
)

#: Previous qualification(17종) → Previous_education_level(6단계). 원본이 영문이라 라벨만 한글로 보여준다.
PREVIOUS_EDUCATION_LEVELS: tuple[str, ...] = (
    "Secondary",
    "Vocational",
    "Below secondary",
    "Bachelor",
    "Higher education experience",
    "Graduate",
)

PREVIOUS_EDUCATION_LABELS_KO: dict[str, str] = {
    "Secondary": "중등교육 이수 (Secondary)",
    "Vocational": "직업교육 (Vocational)",
    "Below secondary": "중등교육 미만 (Below secondary)",
    "Bachelor": "학사 (Bachelor)",
    "Higher education experience": "고등교육 경험 (Higher education experience)",
    "Graduate": "대학원 (Graduate)",
}

#: 부모 학력 → Mother/Father_education_level(6단계)
PARENT_EDUCATION_LEVELS: tuple[str, ...] = (
    "중등교육 이하",
    "고등학교",
    "전문·직업교육",
    "대학",
    "대학원",
    "미상·기타",
)

#: 부모 직업 → Mother/Father_occupation_group(5직업군)
OCCUPATION_GROUPS: tuple[str, ...] = (
    "기술·생산",
    "사무·서비스",
    "전문·관리직",
    "무직·기타",
    "농림",
)

#: Marital status — 원본 코드를 그대로 유지한 컬럼(일반화 대상이 아니었다).
#  전처리기는 이 값을 그대로 원-핫 인코딩하므로 **정수 1~6 을 넘겨야 한다.**
MARITAL_STATUS_CODES: dict[int, str] = {
    1: "미혼",
    2: "기혼",
    3: "사별",
    4: "이혼",
    5: "사실혼",
    6: "법적 별거",
}

#: Gender — 원본: 1 male / 0 female
GENDER_CODES: dict[int, str] = {1: "남성", 0: "여성"}

#: Daytime/evening attendance — 원본: 1 daytime / 0 evening
ATTENDANCE_CODES: dict[int, str] = {1: "주간", 0: "야간"}

#: 1/0 이진 Feature 공통 라벨
YES_NO_CODES: dict[int, str] = {1: "예", 0: "아니오"}

# ---------------------------------------------------------------------------
# 3. 화면 입력 필드 스펙 — UI 위젯과 전처리기 입력 컬럼을 잇는 단일 정의
# ---------------------------------------------------------------------------

FieldKind = Literal["number", "slider", "select", "text_select"]


@dataclass(frozen=True)
class FieldSpec:
    """화면 입력 필드 1개 = 전처리기 입력 컬럼 1개."""

    key: str                        # StudentInput 의 속성명
    label: str                      # 화면 라벨
    column: str                     # 전처리기가 기대하는 컬럼명
    group: str                      # 입력 폼 섹션
    kind: FieldKind
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    options: dict[int, str] | None = None       # kind == "select"
    choices: tuple[str, ...] | None = None      # kind == "text_select"
    labels: dict[str, str] | None = None        # text_select 의 표시용 라벨
    help: str = ""


#: 입력 폼 섹션. 마지막 '가정 배경'은 접어 둔다 — 담당자가 매번 만질 값이 아니다.
FIELD_GROUPS: tuple[str, ...] = (
    "기본 정보",
    "입학 정보",
    "경제 정보",
    "1학기 학업",
    "2학기 학업",
    "가정 배경",
)

COLLAPSED_GROUPS: frozenset[str] = frozenset({"가정 배경"})

UI_FIELDS: tuple[FieldSpec, ...] = (
    # ---- 기본 정보 -------------------------------------------------------
    FieldSpec("age_at_enrollment", "입학 시 나이", "Age at enrollment", "기본 정보",
              "number", 20, 17, 70, 1),
    FieldSpec("gender", "성별", "Gender", "기본 정보",
              "select", 0, options=GENDER_CODES, help="원본 코드: 1=남성, 0=여성"),
    FieldSpec("marital_status", "혼인 상태", "Marital status", "기본 정보",
              "select", 1, options=MARITAL_STATUS_CODES,
              help="원본 코드 1~6 을 그대로 씁니다 (일반화 대상이 아니었던 컬럼)"),
    FieldSpec("major_field", "전공 계열", "Major_field", "기본 정보",
              "text_select", "경영", choices=MAJOR_FIELDS,
              help="원본 학과 17종을 팀 전처리가 10개 계열로 일반화한 값"),
    FieldSpec("attendance", "수업 시간대", "Daytime/evening attendance", "기본 정보",
              "select", 1, options=ATTENDANCE_CODES, help="원본 코드: 1=주간, 0=야간"),
    FieldSpec("displaced", "타지 거주(이주) 여부", "Displaced", "기본 정보",
              "select", 0, options=YES_NO_CODES),
    FieldSpec("international", "국제학생 여부", "International", "기본 정보",
              "select", 0, options=YES_NO_CODES,
              help="Nacionality 는 이 컬럼과 중복이라 팀 전처리에서 제거됐습니다"),
    FieldSpec("special_needs", "교육적 특별지원 대상", "Educational special needs", "기본 정보",
              "select", 0, options=YES_NO_CODES),
    # ---- 입학 정보 -------------------------------------------------------
    FieldSpec("admission_pathway", "입학 전형", "Admission_pathway", "입학 정보",
              "text_select", "일반전형", choices=ADMISSION_PATHWAYS,
              help="원본 전형 18종을 팀 전처리가 8개 유형으로 일반화한 값"),
    FieldSpec("application_order", "지망 순위", "Application order", "입학 정보",
              "slider", 0, 0, 9, 1, help="원본: 0=1지망 … 9=마지막 지망"),
    FieldSpec("admission_grade", "입학 성적", "Admission grade", "입학 정보",
              "slider", 125.0, 0.0, 200.0, 0.5, help="원본 범위 0~200"),
    FieldSpec("previous_education_level", "이전 학력 수준", "Previous_education_level", "입학 정보",
              "text_select", "Secondary", choices=PREVIOUS_EDUCATION_LEVELS,
              labels=PREVIOUS_EDUCATION_LABELS_KO,
              help="원본 학력 17종을 팀 전처리가 6단계로 일반화한 값"),
    FieldSpec("previous_qualification_grade", "이전 학력 성적", "Previous qualification (grade)", "입학 정보",
              "slider", 132.0, 0.0, 200.0, 0.5, help="원본 범위 0~200"),
    # ---- 경제 정보 -------------------------------------------------------
    FieldSpec("tuition_fees_up_to_date", "등록금 납부 정상 여부", "Tuition fees up to date", "경제 정보",
              "select", 1, options=YES_NO_CODES, help="원본 코드: 1=정상 납부, 0=미납"),
    FieldSpec("scholarship_holder", "장학금 수혜 여부", "Scholarship holder", "경제 정보",
              "select", 0, options=YES_NO_CODES),
    FieldSpec("debtor", "채무 보유 여부", "Debtor", "경제 정보",
              "select", 0, options=YES_NO_CODES),
    # ---- 1학기 학업 ------------------------------------------------------
    FieldSpec("sem1_enrolled", "1학기 수강 과목 수", "Curricular units 1st sem (enrolled)", "1학기 학업",
              "number", 6, 0, 26, 1),
    FieldSpec("sem1_approved", "1학기 이수(통과) 과목 수", "Curricular units 1st sem (approved)", "1학기 학업",
              "number", 5, 0, 26, 1),
    FieldSpec("sem1_grade", "1학기 평균 성적", "Curricular units 1st sem (grade)", "1학기 학업",
              "slider", 12.0, 0.0, 20.0, 0.1, help="원본 범위 0~20"),
    FieldSpec("sem1_evaluations", "1학기 평가 응시 횟수", "Curricular units 1st sem (evaluations)", "1학기 학업",
              "number", 8, 0, 45, 1),
    FieldSpec("sem1_without_evaluations", "1학기 미응시 과목 수", "Curricular units 1st sem (without evaluations)",
              "1학기 학업", "number", 0, 0, 26, 1),
    FieldSpec("sem1_credited", "1학기 인정(학점인정) 과목 수", "Curricular units 1st sem (credited)", "1학기 학업",
              "number", 0, 0, 26, 1),
    # ---- 2학기 학업 ------------------------------------------------------
    FieldSpec("sem2_enrolled", "2학기 수강 과목 수", "Curricular units 2nd sem (enrolled)", "2학기 학업",
              "number", 6, 0, 26, 1),
    FieldSpec("sem2_approved", "2학기 이수(통과) 과목 수", "Curricular units 2nd sem (approved)", "2학기 학업",
              "number", 5, 0, 26, 1),
    FieldSpec("sem2_grade", "2학기 평균 성적", "Curricular units 2nd sem (grade)", "2학기 학업",
              "slider", 12.0, 0.0, 20.0, 0.1, help="원본 범위 0~20"),
    FieldSpec("sem2_evaluations", "2학기 평가 응시 횟수", "Curricular units 2nd sem (evaluations)", "2학기 학업",
              "number", 8, 0, 45, 1),
    FieldSpec("sem2_without_evaluations", "2학기 미응시 과목 수", "Curricular units 2nd sem (without evaluations)",
              "2학기 학업", "number", 0, 0, 26, 1),
    FieldSpec("sem2_credited", "2학기 인정(학점인정) 과목 수", "Curricular units 2nd sem (credited)", "2학기 학업",
              "number", 0, 0, 26, 1),
    # ---- 가정 배경 -------------------------------------------------------
    FieldSpec("mother_education_level", "어머니 교육 수준", "Mother_education_level", "가정 배경",
              "text_select", "중등교육 이하", choices=PARENT_EDUCATION_LEVELS),
    FieldSpec("father_education_level", "아버지 교육 수준", "Father_education_level", "가정 배경",
              "text_select", "중등교육 이하", choices=PARENT_EDUCATION_LEVELS),
    FieldSpec("mother_occupation_group", "어머니 직업군", "Mother_occupation_group", "가정 배경",
              "text_select", "기술·생산", choices=OCCUPATION_GROUPS),
    FieldSpec("father_occupation_group", "아버지 직업군", "Father_occupation_group", "가정 배경",
              "text_select", "기술·생산", choices=OCCUPATION_GROUPS),
)

FIELDS_BY_KEY: dict[str, FieldSpec] = {f.key: f for f in UI_FIELDS}

#: 화면이 입력받는 컬럼명 집합 (파생변수는 여기 없다)
INPUT_COLUMNS: frozenset[str] = frozenset(f.column for f in UI_FIELDS)

#: 화면이 받지 않고 계산으로 채우는 파생 컬럼 5종
DERIVED_COLUMNS: tuple[str, ...] = (
    "sem1_approval_rate",
    "sem2_approval_rate",
    "grade_change",
    "zero_enrolled_1st_sem",
    "financial_risk_score",
)


def missing_model_columns() -> tuple[str, ...]:
    """전처리기가 요구하는데 화면도 파생도 채우지 못하는 컬럼.

    비어 있어야 정상이다. 팀이 전처리를 바꾸면 이 함수가 즉시 알려준다 —
    실제 모델을 붙이기 전에 반드시 확인하는 지점이다.
    """
    required = set(model_input_columns())
    if not required:
        return ()
    covered = INPUT_COLUMNS | set(DERIVED_COLUMNS)
    return tuple(sorted(required - covered))


# ---------------------------------------------------------------------------
# 4. StudentInput — UI ↔ 예측기 사이의 유일한 데이터 계약
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StudentInput:
    """화면에서 받은 학생 1명의 입력값.

    예측기(Predictor)는 이 객체만 받는다. Streamlit 위젯 값이나 DataFrame 행을
    예측기에 직접 넘기지 않는다 — UI 와 전처리를 섞지 않기 위한 경계다.
    """

    student_id: str = "S000"
    name: str = ""

    # 기본 정보
    age_at_enrollment: int = 20
    gender: int = 0
    marital_status: int = 1
    major_field: str = "경영"
    attendance: int = 1
    displaced: int = 0
    international: int = 0
    special_needs: int = 0
    # 입학 정보
    admission_pathway: str = "일반전형"
    application_order: int = 0
    admission_grade: float = 125.0
    previous_education_level: str = "Secondary"
    previous_qualification_grade: float = 132.0
    # 경제 정보
    tuition_fees_up_to_date: int = 1
    scholarship_holder: int = 0
    debtor: int = 0
    # 1학기
    sem1_enrolled: int = 6
    sem1_approved: int = 5
    sem1_grade: float = 12.0
    sem1_evaluations: int = 8
    sem1_without_evaluations: int = 0
    sem1_credited: int = 0
    # 2학기
    sem2_enrolled: int = 6
    sem2_approved: int = 5
    sem2_grade: float = 12.0
    sem2_evaluations: int = 8
    sem2_without_evaluations: int = 0
    sem2_credited: int = 0
    # 가정 배경
    mother_education_level: str = "중등교육 이하"
    father_education_level: str = "중등교육 이하"
    mother_occupation_group: str = "기술·생산"
    father_occupation_group: str = "기술·생산"

    # -- 파생변수 5종 ------------------------------------------------------
    #    팀 전처리(preprocess.ipynb)와 같은 정의를 쓴다. 정의를 바꾸려면 여기 한 곳만 바꾼다.

    @property
    def sem1_approval_rate(self) -> float:
        """1학기 이수율 = 이수 / 수강. 수강 0과목이면 0.0 (분모 0 방어)."""
        if self.sem1_enrolled <= 0:
            return 0.0
        return min(self.sem1_approved / self.sem1_enrolled, 1.0)

    @property
    def sem2_approval_rate(self) -> float:
        if self.sem2_enrolled <= 0:
            return 0.0
        return min(self.sem2_approved / self.sem2_enrolled, 1.0)

    @property
    def grade_change(self) -> float:
        """2학기 평점 − 1학기 평점."""
        return round(self.sem2_grade - self.sem1_grade, 4)

    @property
    def zero_enrolled_1st_sem(self) -> int:
        return int(self.sem1_enrolled == 0)

    @property
    def financial_risk_score(self) -> int:
        """등록금 미납 + 채무 보유 + 장학금 미수혜 (0~3점)."""
        return (
            int(self.tuition_fees_up_to_date == 0)
            + int(self.debtor == 1)
            + int(self.scholarship_holder == 0)
        )

    # -- 화면 표시용 보조값 -------------------------------------------------

    @property
    def overall_approval_rate(self) -> float:
        total = self.sem1_enrolled + self.sem2_enrolled
        if total <= 0:
            return 0.0
        return min((self.sem1_approved + self.sem2_approved) / total, 1.0)

    @property
    def average_grade(self) -> float:
        """두 학기 평균 성적(0~20). 수강 이력이 없는 학기는 평균에서 뺀다."""
        grades = []
        if self.sem1_enrolled > 0:
            grades.append(self.sem1_grade)
        if self.sem2_enrolled > 0:
            grades.append(self.sem2_grade)
        if not grades:
            return 0.0
        return sum(grades) / len(grades)

    @property
    def marital_status_label(self) -> str:
        return MARITAL_STATUS_CODES.get(self.marital_status, f"코드 {self.marital_status}")

    @property
    def display_name(self) -> str:
        return self.name or self.student_id

    # -- 검증 / 변환 -------------------------------------------------------

    def validate(self) -> list[str]:
        """치명적이지 않은 논리 오류를 문자열 목록으로 돌려준다 (예외를 던지지 않는다).

        UI 는 이 목록을 경고로 표시하고 예측은 그대로 진행한다 — 담당자가 입력 도중
        잠깐 모순된 값을 넣었다고 앱이 죽으면 안 되기 때문이다.
        """
        problems: list[str] = []
        if self.sem1_approved > self.sem1_enrolled:
            problems.append("1학기 이수 과목 수가 수강 과목 수보다 많습니다.")
        if self.sem2_approved > self.sem2_enrolled:
            problems.append("2학기 이수 과목 수가 수강 과목 수보다 많습니다.")
        if self.sem1_without_evaluations > self.sem1_enrolled:
            problems.append("1학기 미응시 과목 수가 수강 과목 수보다 많습니다.")
        if self.sem2_without_evaluations > self.sem2_enrolled:
            problems.append("2학기 미응시 과목 수가 수강 과목 수보다 많습니다.")
        if not (0 <= self.sem1_grade <= 20) or not (0 <= self.sem2_grade <= 20):
            problems.append("학기 평균 성적은 원본 데이터 기준 0~20 범위입니다.")
        if not (0 <= self.admission_grade <= 200):
            problems.append("입학 성적은 원본 데이터 기준 0~200 범위입니다.")
        if self.age_at_enrollment < 15:
            problems.append("입학 시 나이 값이 비정상적입니다.")
        return problems

    def to_ui_dict(self) -> dict[str, Any]:
        """화면/CSV 저장용 평면 딕셔너리 (UI 필드명 그대로)."""
        return asdict(self)

    def to_model_row(self) -> dict[str, Any]:
        """전처리기 입력 1행. **컬럼명은 팀 전처리 기준, 파생변수까지 채운다.**

        ▶ 실제 모델 연결 지점: RealModelPredictor 가 이 딕셔너리를 DataFrame 으로 만들어
          `preprocessor.transform()` 에 넣는다.
        """
        row: dict[str, Any] = {spec.column: getattr(self, spec.key) for spec in UI_FIELDS}
        row["sem1_approval_rate"] = self.sem1_approval_rate
        row["sem2_approval_rate"] = self.sem2_approval_rate
        row["grade_change"] = self.grade_change
        row["zero_enrolled_1st_sem"] = self.zero_enrolled_1st_sem
        row["financial_risk_score"] = self.financial_risk_score
        return row

    def to_model_ordered(self) -> list[tuple[str, Any]]:
        """전처리기가 기대하는 **순서대로** (컬럼명, 값) 목록.

        스키마를 못 읽으면 빈 목록을 돌려준다 — 임의 순서로 넘기지 않는다.
        """
        order = model_input_columns()
        if not order:
            return []
        row = self.to_model_row()
        return [(col, row[col]) for col in order if col in row]


def student_from_mapping(row: dict[str, Any]) -> StudentInput:
    """CSV 한 행(dict)을 StudentInput 으로 되돌린다. 알 수 없는 키는 무시한다."""
    typed: dict[str, Any] = {}
    for spec in fields(StudentInput):
        if spec.name not in row:
            continue
        value = row[spec.name]
        if spec.type is int or spec.type == "int":
            typed[spec.name] = int(float(value))
        elif spec.type is float or spec.type == "float":
            typed[spec.name] = float(value)
        else:
            typed[spec.name] = str(value)
    return StudentInput(**typed)
