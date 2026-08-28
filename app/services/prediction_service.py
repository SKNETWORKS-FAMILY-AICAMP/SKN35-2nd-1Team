"""
PredictionService — 화면이 예측기를 직접 고르지 않게 만드는 단 하나의 관문.

화면 코드는 항상 이렇게만 쓴다:

    from services.prediction_service import get_service
    result = get_service().predict(student)

예측기를 바꾸는 스위치는 이 파일의 `USE_REAL_MODEL` 하나뿐이다.
"""

from __future__ import annotations

from typing import Iterable

from services.dummy_predictor import DummyPredictor
from services.predictor import PredictionResult, Predictor
from utils.feature_mapping import StudentInput

# ---------------------------------------------------------------------------
# ▶ 실제 모델 연결 스위치
#   models/ 에 학습된 모델을 넣은 뒤 True 로 바꾼다.
#   전처리기(preprocessor.joblib)는 이미 저장소에 있으므로 추가 작업이 없다.
# ---------------------------------------------------------------------------
USE_REAL_MODEL = False


class PredictionService:
    """예측기 선택 + 화면이 쓰기 좋은 형태의 부가 기능을 담는 얇은 계층."""

    def __init__(self, predictor: Predictor | None = None) -> None:
        self._predictor: Predictor = predictor or _build_default_predictor()

    # -- 화면이 쓰는 API ---------------------------------------------------

    def predict(self, student: StudentInput) -> PredictionResult:
        return self._predictor.predict(student)

    def predict_many(self, students: Iterable[StudentInput]) -> list[PredictionResult]:
        return self._predictor.predict_many(students)

    # -- 출처 표기 ---------------------------------------------------------

    @property
    def predictor(self) -> Predictor:
        return self._predictor

    @property
    def is_dummy(self) -> bool:
        return bool(getattr(self._predictor, "is_dummy", True))

    @property
    def model_label(self) -> str:
        return f"{self._predictor.name} · v{self._predictor.version}"


def _build_default_predictor() -> Predictor:
    if USE_REAL_MODEL:
        # 지연 import: 실제 모델 라이브러리(joblib/sklearn)를
        # 프로토타입 모드에서는 설치하지 않아도 앱이 뜨게 한다.
        from services.real_predictor import RealModelPredictor

        return RealModelPredictor()
    return DummyPredictor()


_service: PredictionService | None = None


def get_service() -> PredictionService:
    """프로세스당 1개만 만든다 (실제 모델 로드 비용을 반복하지 않기 위해)."""
    global _service
    if _service is None:
        _service = PredictionService()
    return _service


def reset_service(predictor: Predictor | None = None) -> PredictionService:
    """테스트에서 예측기를 갈아 끼울 때 쓴다."""
    global _service
    _service = PredictionService(predictor)
    return _service
