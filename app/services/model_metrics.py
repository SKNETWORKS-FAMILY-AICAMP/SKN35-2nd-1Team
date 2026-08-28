"""
팀 학습 결과서(`reports/model_metrics.json`) 읽기.

전처리 산출물과 같은 원칙이다 — **팀이 파일을 제 위치에 두면 화면이 알아서 바뀐다.**
파일이 없으면 조용히 없는 상태로 물러나고 앱은 그대로 뜬다.

이 파일은 `reports/` 를 **읽기만 한다.** 거기는 모델링 담당자의 영역이고, 서비스
구현이 남의 산출물을 덮어쓰면 안 된다. 형식이 맞지 않으면 고쳐 쓰지 않고 사유를 낸다.

기대하는 형식은 `SCHEMA_HINT` 에 그대로 적어 두었고, 화면이 파일 없을 때 그걸 띄운다.
팀원이 화면만 보고도 무엇을 만들어 오면 되는지 알 수 있어야 하기 때문이다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

#: app/ 기준 두 단계 위가 저장소 루트다.
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
METRICS_PATH = REPORTS_DIR / "model_metrics.json"

SCHEMA_HINT = """{
  "generated_at": "2026-08-29",
  "dataset": { "train": 3096, "valid": 443, "test": 885 },
  "threshold": 0.5,
  "selected": "XGBoost",
  "models": [
    {
      "name": "LogisticRegression", "type": "ML",
      "accuracy": 0.87, "precision": 0.81, "recall": 0.75, "f1": 0.78, "roc_auc": 0.91,
      "confusion_matrix": [[TN, FP], [FN, TP]],
      "notes": "baseline"
    }
  ],
  "feature_importance": [ { "feature": "sem2_approval_rate", "importance": 0.21 } ]
}"""

#: 모델 하나에 최소한 있어야 하는 것. 나머지는 있으면 쓰고 없으면 비운다.
REQUIRED_MODEL_KEYS = ("name",)

SCORE_KEYS = ("accuracy", "precision", "recall", "f1", "roc_auc")


@dataclass(frozen=True)
class ModelScore:
    name: str
    kind: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    confusion_matrix: list[list[int]] | None = None
    notes: str = ""

    def value(self, key: str) -> float | None:
        value = self.scores.get(key)
        return float(value) if isinstance(value, (int, float)) else None


@dataclass(frozen=True)
class MetricsReport:
    models: list[ModelScore]
    selected: str = ""
    threshold: float | None = None
    dataset: dict[str, int] = field(default_factory=dict)
    generated_at: str = ""
    feature_importance: list[tuple[str, float]] = field(default_factory=list)
    source: str = ""

    @property
    def best(self) -> ModelScore | None:
        """팀이 고른 모델. 지정이 없으면 ROC-AUC 가 가장 높은 것."""
        for model in self.models:
            if model.name == self.selected:
                return model
        ranked = [m for m in self.models if m.value("roc_auc") is not None]
        return max(ranked, key=lambda m: m.value("roc_auc")) if ranked else None


def available() -> bool:
    return METRICS_PATH.exists()


def load() -> MetricsReport | None:
    """학습 결과서를 읽는다. 없거나 형식이 깨졌으면 None.

    **예외를 밖으로 내보내지 않는다.** 발표 직전에 팀원이 넣은 JSON 에 쉼표 하나가
    빠졌다고 앱 전체가 죽으면 안 된다. 화면은 "아직 없음" 으로 물러난다.
    """
    if not METRICS_PATH.exists():
        return None
    try:
        raw = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None

    models: list[ModelScore] = []
    for entry in raw.get("models", []):
        if not isinstance(entry, dict) or not all(k in entry for k in REQUIRED_MODEL_KEYS):
            continue
        matrix = entry.get("confusion_matrix")
        models.append(
            ModelScore(
                name=str(entry["name"]),
                kind=str(entry.get("type", "")),
                scores={k: entry[k] for k in SCORE_KEYS if isinstance(entry.get(k), (int, float))},
                confusion_matrix=matrix if isinstance(matrix, list) else None,
                notes=str(entry.get("notes", "")),
            )
        )
    if not models:
        return None

    importance = [
        (str(item.get("feature", "")), float(item.get("importance", 0.0)))
        for item in raw.get("feature_importance", [])
        if isinstance(item, dict) and isinstance(item.get("importance"), (int, float))
    ]
    dataset = {
        str(k): int(v)
        for k, v in (raw.get("dataset") or {}).items()
        if isinstance(v, (int, float))
    }
    threshold = raw.get("threshold")

    return MetricsReport(
        models=models,
        selected=str(raw.get("selected", "")),
        threshold=float(threshold) if isinstance(threshold, (int, float)) else None,
        dataset=dataset,
        generated_at=str(raw.get("generated_at", "")),
        feature_importance=sorted(importance, key=lambda pair: pair[1], reverse=True),
        source=str(METRICS_PATH.relative_to(REPORTS_DIR.parent)).replace("\\", "/"),
    )
