"""
예측 계층의 계약(contract).

    UI → PredictionService → Predictor 구현체
                              ├─ DummyPredictor      (지금: 학습된 모델 없음)
                              └─ RealModelPredictor  (팀 최종 모델이 오면)

화면 코드는 이 파일의 `PredictionResult` 만 알면 된다. 구현체가 바뀌어도
화면은 바뀌지 않는다 — 그것이 이 계층을 만든 유일한 이유다.

Target 은 팀 전처리 기준 **이진**이다 (1=Dropout, 0=Non-Dropout).
확률은 `dropout_probability` 하나만 저장하고 반대쪽은 계산해서 쓴다 —
두 값을 따로 들고 있으면 언젠가 합이 1이 아니게 된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol, runtime_checkable

from utils.feature_mapping import TARGET_CLASSES, StudentInput

# ---------------------------------------------------------------------------
# 위험도 등급
# ---------------------------------------------------------------------------

#: 중도탈락 확률 → 위험등급 경계. 등급 기준을 바꿀 곳은 여기 한 군데다.
RISK_THRESHOLDS: dict[str, float] = {"HIGH": 0.60, "MEDIUM": 0.30}

RISK_LEVELS: tuple[str, ...] = ("HIGH", "MEDIUM", "LOW")

RISK_LABELS_KO: dict[str, str] = {"HIGH": "높음", "MEDIUM": "중간", "LOW": "낮음"}

#: 이진 분류의 판정 임계값. 위험등급 경계와는 별개다
#  (등급은 3단계, 예측 클래스는 2단계라 기준이 다르다).
DECISION_THRESHOLD = 0.50


def risk_level_of(dropout_probability: float) -> str:
    """확률 → HIGH / MEDIUM / LOW. 모든 구현체가 이 함수를 쓴다."""
    if dropout_probability >= RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    if dropout_probability >= RISK_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def class_of(dropout_probability: float) -> str:
    return "Dropout" if dropout_probability >= DECISION_THRESHOLD else "Non-Dropout"


# ---------------------------------------------------------------------------
# 위험요인 (설명 계층)
# ---------------------------------------------------------------------------

#: 위험요인 카테고리. 규칙엔진의 분류 체계와 같은 값을 쓴다.
RISK_CATEGORIES: dict[str, str] = {
    "academic": "학업",
    "financial": "경제",
    "adaptation": "진로·적응",
}


@dataclass(frozen=True)
class RiskFactor:
    """위험요인 1개.

    지금은 DummyPredictor 가 자기 가중치를 그대로 풀어서 만든다.
    실제 모델이 붙으면 SHAP value 를 `contribution` 에 넣어 그대로 대체할 수 있다.
    """

    key: str            # 내부 식별자. 규칙엔진이 이 key 로 조건을 매칭한다.
    label: str          # 화면 표시용 한글 설명
    category: str       # RISK_CATEGORIES 의 키
    contribution: float # 0~1. 이 요인이 위험 판단에서 차지한 비중(상대값)
    detail: str = ""    # 근거가 된 실제 값 ("2학기 이수율 33% (2/6)")

    @property
    def category_label(self) -> str:
        return RISK_CATEGORIES.get(self.category, self.category)


# ---------------------------------------------------------------------------
# 예측 결과
# ---------------------------------------------------------------------------

#: 설명(top_factors)의 출처. 화면은 이 값으로 "프로토타입" 배지를 띄운다.
EXPLANATION_DUMMY = "dummy-heuristic"
EXPLANATION_SHAP = "shap"
EXPLANATION_FEATURE_IMPORTANCE = "feature-importance"


@dataclass(frozen=True)
class PredictionResult:
    """학생 1명에 대한 예측 결과 (이진)."""

    dropout_probability: float               # 0~1. P(Dropout)
    risk_level: str                          # "HIGH" | "MEDIUM" | "LOW"
    top_factors: list[RiskFactor] = field(default_factory=list)

    # -- 출처 표기 (화면에 그대로 노출된다) --------------------------------
    model_name: str = "unknown"
    model_version: str = "0"
    explanation_source: str = EXPLANATION_DUMMY
    is_dummy: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.dropout_probability <= 1.0:
            raise ValueError(f"확률 범위를 벗어났습니다: {self.dropout_probability}")
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"알 수 없는 위험등급: {self.risk_level}")

    @property
    def non_dropout_probability(self) -> float:
        return round(1.0 - self.dropout_probability, 6)

    @property
    def predicted_class(self) -> str:
        """"Dropout" | "Non-Dropout" — 임계값 0.5 기준."""
        return class_of(self.dropout_probability)

    @property
    def class_probabilities(self) -> dict[str, float]:
        """화면 막대용. 합은 항상 정확히 1이다 (한쪽을 계산해서 만들기 때문)."""
        return {
            "Dropout": self.dropout_probability,
            "Non-Dropout": self.non_dropout_probability,
        }

    @property
    def dropout_percent(self) -> float:
        return round(self.dropout_probability * 100, 1)

    def factors_by_category(self, category: str) -> list[RiskFactor]:
        return [f for f in self.top_factors if f.category == category]

    @property
    def factor_keys(self) -> set[str]:
        return {f.key for f in self.top_factors}


def make_result(dropout_probability: float, **kwargs) -> PredictionResult:
    """확률에서 등급을 자동으로 채워 결과를 만든다. 구현체가 등급 계산을 잊지 않게 한다."""
    probability = float(min(max(dropout_probability, 0.0), 1.0))
    return PredictionResult(
        dropout_probability=probability,
        risk_level=risk_level_of(probability),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 예측기 인터페이스
# ---------------------------------------------------------------------------

@runtime_checkable
class Predictor(Protocol):
    """예측기가 지켜야 할 최소 계약.

    새 구현체는 이 5개만 맞추면 화면 수정 없이 교체된다.
    """

    name: str
    version: str
    is_dummy: bool

    def predict(self, student: StudentInput) -> PredictionResult:
        ...

    def predict_many(self, students: Iterable[StudentInput]) -> list[PredictionResult]:
        ...


_KEEP = TARGET_CLASSES  # 화면이 클래스 순서를 이 모듈 경유로도 얻을 수 있게 남긴다.
