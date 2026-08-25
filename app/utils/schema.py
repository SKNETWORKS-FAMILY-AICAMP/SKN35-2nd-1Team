"""
팀 전처리 스키마를 **런타임에 읽는** 모듈.

왜 하드코딩하지 않는가
    컬럼 목록·순서를 앱에 베껴 두면, 팀이 전처리를 고칠 때마다 앱이 조용히
    틀린 값을 만든다. 정답은 언제나 저장소의 산출물이다:

        data/processed/feature_schema.json   ← 컬럼 분류 (이 파일이 읽는 것)
        models/preprocessor.joblib           ← 학습된 전처리 파이프라인

    전처리기가 기대하는 입력 컬럼 순서는
    `binary → low_card_categorical → continuous → count → flag` 이고,
    이는 `preprocessor.feature_names_in_` 과 일치한다(37개).
    joblib 을 읽지 않고도 순서를 알 수 있게 여기서 같은 규칙으로 조립한다.

스키마 파일이 없을 때
    앱은 죽지 않는다. 더미 모드에서는 이 순서가 쓰이지 않기 때문이다.
    대신 `SCHEMA_AVAILABLE` 이 False 가 되고, 실제 모델 연결 시점에 명시적으로 실패한다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

#: 저장소 루트 = app/ 의 부모
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SCHEMA_PATH = REPO_ROOT / "data" / "processed" / "feature_schema.json"
PREPROCESSOR_PATH = REPO_ROOT / "models" / "preprocessor.joblib"

#: feature_schema.json 의 키를 전처리기 입력 순서대로 나열한 것.
#  ColumnTransformer 가 num → cat → remainder 순으로 열을 요구하지만,
#  입력 프레임 자체는 아래 순서(= feature_names_in_)로 만들어야 경고 없이 통과한다.
_ORDERED_GROUPS: tuple[str, ...] = (
    "binary_cols",
    "low_card_categorical",
    "continuous_cols",
    "count_cols",
    "flag_cols",
)


@lru_cache(maxsize=1)
def load_schema() -> dict:
    """feature_schema.json 을 읽는다. 없으면 빈 dict."""
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def schema_available() -> bool:
    return bool(load_schema())


@lru_cache(maxsize=1)
def model_input_columns() -> tuple[str, ...]:
    """전처리기가 기대하는 입력 컬럼 37개를 순서대로 돌려준다.

    스키마 파일이 없으면 빈 튜플. 이 값이 비어 있는 채로 실제 모델을 부르면
    `real_predictor` 가 명시적으로 실패한다 — 조용히 틀린 순서로 넣지 않는다.
    """
    schema = load_schema()
    if not schema:
        return ()
    columns: list[str] = []
    for group in _ORDERED_GROUPS:
        columns.extend(schema.get(group, []))
    return tuple(columns)


def target_definition() -> str:
    return load_schema().get("target_definition", "1=Dropout, 0=Non-Dropout")


def dropped_columns() -> tuple[str, ...]:
    """전처리에서 제거된 원본 컬럼. 시작화면의 '이식성' 설명이 이 목록을 근거로 쓴다."""
    return tuple(load_schema().get("dropped_columns", []))


def final_feature_count() -> int:
    """원-핫 인코딩 후 최종 피처 수 (스키마 기준)."""
    return int(load_schema().get("final_feature_count", 0))
