"""
RealModelPredictor — 팀 최종 모델을 붙이는 자리.

전처리기(`models/preprocessor.joblib`)는 **이미 저장소에 있다.** 그래서 전처리 부분은
TODO 가 아니라 실제 코드로 들어가 있고, 남은 것은 **모델 파일 하나**뿐이다.

────────────────────────────────────────────────────────────────────────
연결 절차 — 모델 담당자에게서 파일을 받은 뒤
────────────────────────────────────────────────────────────────────────
1. `models/` 에 학습된 모델을 넣는다. 파일명은 아래 MODEL_CANDIDATES 중 하나면 된다.
       models/best_model.joblib   (권장)
       models/best_model.pkl
       models/model.joblib
2. `services/prediction_service.py` 의 `USE_REAL_MODEL` 을 True 로 바꾼다.
3. 끝이다. **화면 코드(views/·components/)는 한 줄도 고치지 않는다.**

받아야 할 것 / 확인할 것
    · 모델이 `predict_proba` 를 제공하는지 (sklearn 계열이면 있다).
      keras 모델이라면 `_predict_proba()` 의 분기를 하나 더 채운다.
    · 클래스 순서: 팀 전처리 정의가 `1=Dropout` 이므로 `predict_proba(...)[:, 1]` 이
      Dropout 확률이다. 모델이 `classes_` 를 갖고 있으면 그 값으로 한 번 더 확인한다.
    · SHAP explainer 는 선택이다. 없으면 위험요인 목록은 DummyPredictor 의 설명을
      그대로 쓰고(`explanation_source` 로 출처를 밝힘), 확률만 실제 모델 값을 쓴다.
      **확률은 실제 모델, 설명은 프로토타입** 이라는 사실이 화면에 그대로 표시된다.

주의
    · 전처리는 반드시 이 파일 안에서 끝낸다. 화면 코드로 새어 나가면
      예측기를 교체하는 의미가 없어진다.
    · `preprocessor.transform()` 만 쓴다. `fit_transform` 을 쓰면 학습 때의 통계가
      덮어써져 데이터 누수가 된다 (팀 전처리 결과서 9장).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from services.dummy_predictor import _build_terms, _top_factors
from services.predictor import (
    EXPLANATION_DUMMY,
    EXPLANATION_FEATURE_IMPORTANCE,
    PredictionResult,
    make_result,
)
from utils.feature_mapping import StudentInput, missing_model_columns
from utils.schema import PREPROCESSOR_PATH, model_input_columns

MODELS_DIR = PREPROCESSOR_PATH.parent

#: 모델 파일을 찾는 순서. 팀이 어떤 이름으로 주든 하나는 걸리게 둔다.
MODEL_CANDIDATES: tuple[str, ...] = (
    "best_model.joblib",
    "best_model.pkl",
    "model.joblib",
    "model.pkl",
)


def find_model_path() -> Path | None:
    for name in MODEL_CANDIDATES:
        path = MODELS_DIR / name
        if path.exists():
            return path
    return None


def artifacts_available() -> bool:
    """전처리기 + 모델 + 스키마가 모두 준비됐는지."""
    return bool(PREPROCESSOR_PATH.exists() and find_model_path() and model_input_columns())


def artifacts_status() -> dict[str, bool]:
    """무엇이 있고 무엇이 없는지. 화면과 테스트가 이 값을 그대로 보여준다."""
    return {
        "preprocessor": PREPROCESSOR_PATH.exists(),
        "model": find_model_path() is not None,
        "schema": bool(model_input_columns()),
    }


class RealModelPredictor:
    """`Predictor` 프로토콜의 실제 모델 구현.

    DummyPredictor 와 완전히 같은 입출력을 지킨다:
        predict(StudentInput) -> PredictionResult
    """

    name = "RealModelPredictor (팀 Model B)"
    version = "1.0.0"
    is_dummy = False

    def __init__(self) -> None:
        self._model: Any = None
        self._preprocessor: Any = None
        self._loaded = False

    # -- 1. 산출물 로드 ----------------------------------------------------

    def _load_artifacts(self) -> None:
        if self._loaded:
            return

        missing = [k for k, ok in artifacts_status().items() if not ok]
        if missing:
            raise FileNotFoundError(
                f"실제 모델을 쓸 수 없습니다. 없는 것: {', '.join(missing)}. "
                f"모델 파일은 {MODELS_DIR} 에 {MODEL_CANDIDATES[0]} 로 넣어주세요."
            )

        # 화면이 못 채우는 컬럼이 있으면 예측을 시작하지 않는다.
        # 임의값으로 채우는 결정을 이 파일에서 몰래 하지 않는다.
        gaps = missing_model_columns()
        if gaps:
            raise ValueError(
                "전처리기가 요구하는 컬럼을 화면이 채우지 못합니다: "
                f"{', '.join(gaps)}. utils/feature_mapping.py 의 UI_FIELDS 를 먼저 맞춰주세요."
            )

        import joblib  # 지연 import — 더미 모드에서는 sklearn 이 없어도 앱이 뜬다.

        self._preprocessor = joblib.load(PREPROCESSOR_PATH)
        self._model = joblib.load(find_model_path())
        self._loaded = True

    # -- 2. 전처리 ---------------------------------------------------------

    def _to_frame(self, students: list[StudentInput]):
        """StudentInput 목록 → 전처리기가 기대하는 컬럼·순서의 DataFrame."""
        import pandas as pd

        columns = list(model_input_columns())
        records = [s.to_model_row() for s in students]
        return pd.DataFrame(records)[columns]

    # -- 3. 예측 -----------------------------------------------------------

    def _dropout_probabilities(self, students: list[StudentInput]) -> list[float]:
        self._load_artifacts()
        matrix = self._preprocessor.transform(self._to_frame(students))

        if hasattr(self._model, "predict_proba"):
            proba = self._model.predict_proba(matrix)
            index = self._dropout_index()
            return [float(row[index]) for row in proba]

        # keras 계열: 시그모이드 출력 1개를 그대로 Dropout 확률로 본다.
        raw = self._model.predict(matrix, verbose=0)
        return [float(value[0]) if hasattr(value, "__len__") else float(value) for value in raw]

    def _dropout_index(self) -> int:
        """확률 배열에서 Dropout(=1) 이 몇 번째인지.

        팀 정의상 1=Dropout 이라 보통 1번이지만, 모델이 classes_ 를 갖고 있으면
        그 값을 신뢰한다 — 순서를 가정해서 확률을 뒤집는 사고를 막는다.
        """
        classes = getattr(self._model, "classes_", None)
        if classes is None:
            return 1
        for position, value in enumerate(classes):
            if int(value) == 1:
                return position
        return 1

    def predict(self, student: StudentInput) -> PredictionResult:
        return self.predict_many([student])[0]

    def predict_many(self, students: Iterable[StudentInput]) -> list[PredictionResult]:
        batch = list(students)
        if not batch:
            return []
        probabilities = self._dropout_probabilities(batch)

        results: list[PredictionResult] = []
        for student, probability in zip(batch, probabilities):
            # 설명(top_factors): SHAP explainer 가 준비되기 전까지는 규칙 기반 설명을
            # 그대로 쓰되, 출처를 다르게 표기해 화면이 "확률은 실제 모델"임을 밝힌다.
            results.append(
                make_result(
                    probability,
                    top_factors=_top_factors(_build_terms(student)),
                    model_name=self.name,
                    model_version=self.version,
                    explanation_source=EXPLANATION_FEATURE_IMPORTANCE,
                    is_dummy=False,
                )
            )
        return results


_KEEP = EXPLANATION_DUMMY  # 설명 출처 상수를 이 모듈에서도 찾을 수 있게 남긴다.
