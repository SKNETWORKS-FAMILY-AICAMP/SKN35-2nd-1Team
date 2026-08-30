"""
DummyPredictor — 학습된 모델이 없는 동안 화면을 완성하기 위한 대체 구현.

⚠️ 이것은 머신러닝 모델이 아니다.
    학습도, 검증도, 성능 측정도 하지 않았다. 아래 가중치는 UI 프로토타입이
    "그럴듯하게 움직이도록" 사람이 손으로 정한 값이며 어떤 성능 수치도 주장하지 않는다.
    실제 예측력은 팀의 최종 모델(RealModelPredictor)이 붙은 뒤에만 이야기할 수 있다.

왜 규칙식으로 만들었나
    난수로 확률을 뽑으면 같은 학생이 새로고침마다 다른 등급이 되어 발표 중에 무너진다.
    입력이 같으면 결과가 항상 같아야 하고(결정론), 성적이 나쁜 학생이 더 높은 위험으로
    나와야 화면 검증이 가능하다. 그래서 투명한 가중합 → 시그모이드(이진) 구조를 썼다.
    팀 전처리가 Target 을 이진으로 확정했으므로 출력 형태도 거기에 맞춘다.

설명(top_factors) 생성 방식
    각 항이 위험을 얼마나 밀어올렸는지를 그대로 노출한다. 실제 모델이 붙으면
    이 자리에 SHAP value 를 넣기만 하면 화면은 그대로 동작한다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from services.predictor import (
    RISK_THRESHOLDS,
    EXPLANATION_DUMMY,
    PredictionResult,
    RiskFactor,
    make_result,
)
from utils.feature_mapping import StudentInput

# ---------------------------------------------------------------------------
# 가중치 — 전부 이 자리에 모아 둔다 (숨은 상수를 만들지 않는다)
# ---------------------------------------------------------------------------

#: 시그모이드 로짓의 절편. 더미 명단 80명의 Dropout 비율이 원본 데이터의 32.1% 근처
#  (실측 30.0%)에 오도록 손으로 맞춘 값이며, 학습된 계수가 아니다.
INTERCEPT = -1.30

#: 위험 가중합을 그대로 쓰면 위험요인이 몇 개만 겹쳐도 99% 가 나온다.
#  학습된 모델이 아닌 이상 그런 확신을 화면에 띄우면 안 되므로 눌러서 쓴다.
RISK_SCALE = 0.72

#: 각 항의 기준점과 가중치. 값이 기준보다 나쁠수록 항의 값이 커진다.
WEIGHTS = {
    "sem2_approval": 3.00,      # 2학기 이수율 (팀 EDA 에서도 상관 -0.659 로 가장 강한 신호)
    "sem1_approval": 1.90,
    "sem2_grade": 1.90,
    "sem1_grade": 1.30,
    "admission_grade": 0.80,
    "financial_risk": 1.05,     # 팀 파생변수 financial_risk_score(0~3) 1점당
    "tuition_unpaid": 1.30,     # 등록금 미납 (financial_risk 와 별도로 더 본다)
    "debtor": 0.90,
    "scholarship_bonus": -0.85, # 장학금 수혜 (위험을 낮추는 항)
    "grade_change": 1.10,       # 성적 하락 폭 (팀 파생변수 grade_change)
    "age": 0.045,               # 입학 시 나이 (기준 22세 초과분에 비례)
    "evening": 0.35,            # 야간 과정
    "application_order": 0.10,  # 지망 순위 (0=1지망)
    "displaced": 0.15,          # 타지 거주
    "no_evaluation": 0.22,      # 평가 미응시 과목 1개당
}

APPROVAL_BASELINE = 0.60        # 이수율 기준선
GRADE_BASELINE = 11.0           # 평균 성적 기준선 (원본 0~20)
ADMISSION_BASELINE = 125.0      # 입학 성적 기준선 (원본 0~200)
AGE_BASELINE = 22
AGE_TERM_CAP = 0.90

#: 위험요인으로 화면에 띄울 최소 기여도와 최대 개수
FACTOR_MIN_TERM = 0.06
FACTOR_MAX_COUNT = 5


@dataclass(frozen=True)
class _Term:
    """가중합의 항 1개."""

    key: str
    value: float          # 위험 방향(+)으로의 기여. 음수면 위험을 낮춘 항이다.
    label: str
    category: str
    detail: str


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(logit: float) -> float:
    # math.exp 는 큰 음수에서 overflow 하지 않지만, 큰 양수 로짓에서 안전하게 나누기 위해 분기한다.
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    exp = math.exp(logit)
    return exp / (1.0 + exp)


#: 손으로 정한 가중치가 낼 수 있는 확신의 한계. 규칙식은 "99.6% 확실히 탈락" 같은
#  말을 할 자격이 없다 — 발표 화면에 그런 숫자가 뜨면 없는 성능을 주장하는 셈이다.
CONFIDENCE_CAP = 0.94
CONFIDENCE_FLOOR = 0.02


def _temper(probability: float) -> float:
    """확률의 양 끝만 눌러 과장된 확신을 없앤다.

    **등급 경계(0.30 / 0.60)는 건드리지 않는다.** 경계 밖 구간만 선형으로 다시 매핑하므로
    순서도, HIGH/MEDIUM/LOW 판정도 그대로다. 바뀌는 것은 "얼마나 극단적으로 보이는가" 뿐이다.
    """
    high = RISK_THRESHOLDS["HIGH"]
    medium = RISK_THRESHOLDS["MEDIUM"]
    if probability > high:
        return high + (probability - high) * (CONFIDENCE_CAP - high) / (1.0 - high)
    if probability < medium:
        return CONFIDENCE_FLOOR + probability * (medium - CONFIDENCE_FLOOR) / medium
    return probability


def _build_terms(student: StudentInput) -> list[_Term]:
    """학생 1명 → 가중합의 항 목록. 예측과 설명이 같은 계산을 쓰게 하는 지점."""
    r1 = student.sem1_approval_rate
    r2 = student.sem2_approval_rate
    no_eval = student.sem1_without_evaluations + student.sem2_without_evaluations
    return [
        _Term(
            "sem2_approval",
            WEIGHTS["sem2_approval"] * (APPROVAL_BASELINE - r2),
            "2학기 이수율 저조",
            "academic",
            f"2학기 이수율 {r2:.0%} ({student.sem2_approved}/{student.sem2_enrolled}과목)",
        ),
        _Term(
            "sem1_approval",
            WEIGHTS["sem1_approval"] * (APPROVAL_BASELINE - r1),
            "1학기 이수율 저조",
            "academic",
            f"1학기 이수율 {r1:.0%} ({student.sem1_approved}/{student.sem1_enrolled}과목)",
        ),
        _Term(
            "sem2_grade",
            WEIGHTS["sem2_grade"] * (GRADE_BASELINE - student.sem2_grade) / GRADE_BASELINE,
            "2학기 학업성취 저조",
            "academic",
            f"2학기 평균 성적 {student.sem2_grade:.1f} / 20",
        ),
        _Term(
            "sem1_grade",
            WEIGHTS["sem1_grade"] * (GRADE_BASELINE - student.sem1_grade) / GRADE_BASELINE,
            "1학기 학업성취 저조",
            "academic",
            f"1학기 평균 성적 {student.sem1_grade:.1f} / 20",
        ),
        _Term(
            "grade_change",
            _clamp(WEIGHTS["grade_change"] * (-student.grade_change) / GRADE_BASELINE, 0.0, 1.2),
            "직전 학기 대비 성적 하락",
            "academic",
            f"성적 변화 {student.grade_change:+.1f}점 (1학기 → 2학기)",
        ),
        _Term(
            "no_evaluation",
            WEIGHTS["no_evaluation"] * no_eval,
            "평가 미응시 과목 존재",
            "academic",
            f"두 학기 합계 미응시 {no_eval}과목",
        ),
        _Term(
            "admission_grade",
            WEIGHTS["admission_grade"]
            * (ADMISSION_BASELINE - student.admission_grade) / ADMISSION_BASELINE,
            "입학 성적이 기준선 아래",
            "academic",
            f"입학 성적 {student.admission_grade:.1f} / 200",
        ),
        _Term(
            "financial_risk",
            WEIGHTS["financial_risk"] * student.financial_risk_score,
            "재정 위험 누적",
            "financial",
            f"재정위험점수 {student.financial_risk_score} / 3 "
            "(등록금 미납 + 채무 + 장학금 미수혜)",
        ),
        _Term(
            "tuition_unpaid",
            WEIGHTS["tuition_unpaid"] if student.tuition_fees_up_to_date == 0 else -0.30,
            "등록금 납부 미완료",
            "financial",
            "등록금 미납 상태" if student.tuition_fees_up_to_date == 0 else "등록금 정상 납부",
        ),
        _Term(
            "debtor",
            WEIGHTS["debtor"] if student.debtor == 1 else -0.12,
            "채무 보유",
            "financial",
            "채무 있음" if student.debtor == 1 else "채무 없음",
        ),
        _Term(
            "scholarship",
            WEIGHTS["scholarship_bonus"] if student.scholarship_holder == 1 else 0.0,
            "장학금 미수혜",
            "financial",
            "장학금 수혜 중" if student.scholarship_holder == 1 else "장학금 미수혜",
        ),
        _Term(
            "age",
            _clamp(WEIGHTS["age"] * (student.age_at_enrollment - AGE_BASELINE), 0.0, AGE_TERM_CAP),
            "표준 학령보다 늦은 입학",
            "adaptation",
            f"입학 시 나이 {student.age_at_enrollment}세",
        ),
        _Term(
            "evening",
            WEIGHTS["evening"] if student.attendance == 0 else 0.0,
            "야간 과정 재학",
            "adaptation",
            "야간 과정",
        ),
        _Term(
            "application_order",
            WEIGHTS["application_order"] * student.application_order,
            "낮은 지망 순위로 입학",
            "adaptation",
            f"지망 순위 {student.application_order + 1}지망",
        ),
        _Term(
            "displaced",
            WEIGHTS["displaced"] if student.displaced == 1 else 0.0,
            "타지 거주(이주) 상태",
            "adaptation",
            "타지 거주",
        ),
    ]


#: 기여도 화면에 세울 짧은 이름. `_Term.label` 은 "2학기 이수율 저조" 처럼 문장이라
#  축 라벨로는 길다. 여기 없는 키는 라벨을 그대로 쓴다.
CONTRIBUTION_LABELS = {
    "sem2_approval": "2학기 이수율",
    "sem1_approval": "1학기 이수율",
    "sem2_grade": "2학기 성적",
    "sem1_grade": "1학기 성적",
    "grade_change": "성적 하락 폭",
    "no_evaluation": "평가 미응시 과목",
    "admission_grade": "입학 성적",
    "financial_risk": "재정위험점수",
    "tuition_unpaid": "등록금 납부 여부",
    "debtor": "채무 보유",
    "scholarship": "장학금 수혜",
    "age": "입학 시 나이",
    "evening": "야간 과정",
    "application_order": "지망 순위",
    "displaced": "타지 거주",
}


def contribution_profile(students: Iterable[StudentInput]) -> list[tuple[str, float]]:
    """명단 전체에서 각 항이 **실제로 움직인 크기**의 비중. 큰 것부터.

    ⚠️ 학습된 모델의 feature importance 가 아니다. 이건 지금 화면의 확률을 만들고
    있는 **규칙식이 이 명단에서 얼마나 썼는가**를 그대로 집계한 값이다. 가중치를
    베껴 쓰는 게 아니라 학생 885명에 대해 항의 절댓값을 평균 낸 것이라, 명단이
    바뀌면 이 그림도 바뀐다. 화면은 이 값을 **모델 중요도라고 말하지 않는다.**

    학습 결과서(`reports/model_metrics.json`)가 들어오면 화면은 그쪽을 쓰고 이
    함수는 더 이상 불리지 않는다.
    """
    totals: dict[str, float] = {}
    labels: dict[str, str] = {}
    count = 0
    for student in students:
        count += 1
        for term in _build_terms(student):
            totals[term.key] = totals.get(term.key, 0.0) + abs(term.value)
            labels.setdefault(term.key, term.label)
    if not count:
        return []

    grand = sum(totals.values())
    if grand <= 0:
        return []
    ranked = sorted(totals.items(), key=lambda pair: pair[1], reverse=True)
    return [
        (CONTRIBUTION_LABELS.get(key, labels.get(key, key)), value / grand)
        for key, value in ranked
    ]


def _top_factors(terms: list[_Term]) -> list[RiskFactor]:
    """위험을 올린 항만 골라 상대 기여도로 정규화한다."""
    positive = [t for t in terms if t.value > FACTOR_MIN_TERM]
    if not positive:
        return []
    positive.sort(key=lambda t: t.value, reverse=True)
    selected = positive[:FACTOR_MAX_COUNT]
    total = sum(t.value for t in selected)
    return [
        RiskFactor(
            key=t.key,
            label=t.label,
            category=t.category,
            contribution=round(t.value / total, 4) if total else 0.0,
            detail=t.detail,
        )
        for t in selected
    ]


class DummyPredictor:
    """`Predictor` 프로토콜의 더미 구현. 실제 모델이 오면 통째로 교체된다."""

    name = "DummyPredictor (규칙 기반 · 학습되지 않음)"
    version = "0.2.0-modelB"
    is_dummy = True

    def contribution_profile(self, students: Iterable[StudentInput]) -> list[tuple[str, float]]:
        """이 명단에서 각 항을 실제로 얼마나 반영했는지 — 모듈 함수를 그대로 쓴다."""
        return contribution_profile(students)

    def predict(self, student: StudentInput) -> PredictionResult:
        terms = _build_terms(student)
        risk_score = sum(t.value for t in terms)
        probability = _temper(_sigmoid(INTERCEPT + RISK_SCALE * risk_score))

        return make_result(
            probability,
            top_factors=_top_factors(terms),
            model_name=self.name,
            model_version=self.version,
            explanation_source=EXPLANATION_DUMMY,
            is_dummy=True,
        )

    def predict_many(self, students: Iterable[StudentInput]) -> list[PredictionResult]:
        return [self.predict(s) for s in students]
