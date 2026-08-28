"""
model_metrics.json 조립 스크립트
====================================

목적
    각 모델러가 만든 `reports/*_importance.csv`와 `reports/3) model_results.csv`를 읽어,
    Streamlit 앱(`app/`)이 기대하는 형식의 `reports/model_metrics.json`을 만든다.

    Streamlit 쪽 README에 명시된 스키마를 그대로 따른다:
        {
          "generated_at": "...",
          "dataset": {"train": N, "valid": N, "test": N},
          "threshold": 0.5,
          "selected": "LightGBM",
          "models": [ {...}, ... ],
          "feature_importance": [ {"feature": "...", "importance": 0.xx}, ... ]
        }

누가 어떻게 쓰나
    누가 최종 모델로 선정되든(LightGBM/XGBoost/RandomForest/...) 이 스크립트 하나로 바로
    JSON을 만들 수 있다. 아래처럼 부르면 된다:

        from src.build_model_metrics import build_model_metrics
        build_model_metrics(
            selected_model="LightGBM",
            importance_csv="reports/lightgbm_importance.csv",
        )

    노트북에서건 터미널에서건, **어디서 실행하든 항상 저장소 루트 기준 경로를 사용**하므로
    `../` 상대경로를 따로 신경 쓸 필요가 없다. (이 파일이 `src/`에 있다는 것만 전제한다.)
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 저장소 루트 자동 탐지 — 이 파일이 <repo_root>/src/build_model_metrics.py 라는
# 전제 하나만으로, 실행 위치(노트북/터미널/CI)에 관계없이 항상 같은 경로를 가리킨다.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_RESULTS_CSV = REPO_ROOT / "reports" / "3) model_results.csv"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "reports" / "model_metrics.json"

# team_results.csv 의 model 이름 표기와, 화면에 보여줄 type(ML/DL) 매핑.
# 새 모델이 추가되면 이 딕셔너리에 한 줄만 추가하면 된다.
MODEL_TYPE_MAP: dict[str, str] = {
    "LightGBM": "ML",
    "XGBoost": "ML",
    "RandomForest": "ML",
    "Random Forest": "ML",
    "LogisticRegression": "ML",
    "Logistic Regression": "ML",
    "MLP": "DL",
}


def normalize_importance(csv_path: str | Path, top_n: int = 10) -> list[dict]:
    """어느 모델의 importance.csv든 상위 N개를 0~1 비율로 정규화해서 반환.

    LightGBM(split count, 정수) / RandomForest(gini, 0~1) / XGBoost(gain 등) /
    LogisticRegression(abs_coefficient) 처럼 모델마다 스케일이 전혀 다르므로,
    화면에 표시하기 전 반드시 합이 1이 되도록 정규화한다.

    컬럼명이 `importance` 든 `abs_coefficient` 든 자동으로 인식한다.
    """
    csv_path = Path(csv_path)
    if not csv_path.is_absolute():
        csv_path = REPO_ROOT / csv_path

    df = pd.read_csv(csv_path)

    # 값 컬럼 자동 탐지: importance 또는 abs_coefficient
    value_col = None
    for candidate in ("importance", "abs_coefficient"):
        if candidate in df.columns:
            value_col = candidate
            break
    if value_col is None:
        raise ValueError(
            f"{csv_path.name} 에서 'importance' 또는 'abs_coefficient' 컬럼을 찾지 못함. "
            f"실제 컬럼: {list(df.columns)}"
        )

    # 전처리 접두사(num__, cat__, remainder__) 제거 — 화면 표시용 이름 정리
    df = df.copy()
    df["feature"] = df["feature"].str.replace(r"^(num__|cat__|remainder__)", "", regex=True)

    top = df.sort_values(value_col, ascending=False).head(top_n).copy()
    total = top[value_col].sum()
    if total <= 0:
        raise ValueError(f"{csv_path.name} 의 {value_col} 합이 0 이하라 정규화할 수 없음")

    top["importance"] = (top[value_col] / total).round(4)

    return top[["feature", "importance"]].to_dict(orient="records")


def _row_to_model_entry(row: pd.Series) -> dict:
    """model_results.csv 한 행 → model_metrics.json 의 models[] 항목 하나."""
    model_name = row["model"]

    confusion_matrix = None
    if {"tn", "fp", "fn", "tp"}.issubset(row.index):
        tn, fp, fn, tp = row.get("tn"), row.get("fp"), row.get("fn"), row.get("tp")
        if pd.notna(tn) and pd.notna(fp) and pd.notna(fn) and pd.notna(tp):
            confusion_matrix = [[int(tn), int(fp)], [int(fn), int(tp)]]

    def _get(col: str):
        val = row.get(col)
        return None if pd.isna(val) else float(val)

    return {
        "name": model_name,
        "type": MODEL_TYPE_MAP.get(model_name, "ML"),
        "accuracy": _get("accuracy"),
        "precision": _get("precision"),
        "recall": _get("recall"),
        "f1": _get("f1"),
        "roc_auc": _get("roc_auc"),
        "confusion_matrix": confusion_matrix,
        "notes": row.get("notes", "") if pd.notna(row.get("notes", "")) else "",
    }


def build_model_metrics(
    selected_model: str,
    importance_csv: str | Path,
    results_csv: str | Path = DEFAULT_RESULTS_CSV,
    output_json: str | Path = DEFAULT_OUTPUT_JSON,
    dataset_sizes: dict | None = None,
    threshold: float = 0.5,
    top_n_importance: int = 10,
) -> dict:
    """`reports/model_metrics.json` 을 조립해서 파일로 저장하고, 내용을 반환한다.

    Parameters
    ----------
    selected_model : 팀이 최종 채택한 모델 이름. `model_results.csv` 의 `model` 컬럼 값과
        정확히 같은 문자열이어야 한다 (예: "LightGBM").
    importance_csv : 채택된 모델의 importance/coefficient csv 경로.
        저장소 루트 기준 상대경로("reports/lightgbm_importance.csv") 또는 절대경로 모두 가능.
    results_csv, output_json : 기본값을 그대로 쓰면 된다. 테스트용으로만 바꾸면 됨.
    dataset_sizes : {"train": N, "valid": N, "test": N}. 생략하면 팀 확정 분할 크기 사용.
    threshold : 팀이 최종 채택한 공통 threshold. 기본 0.5.
    """
    results_csv = Path(results_csv)
    output_json = Path(output_json)
    if dataset_sizes is None:
        dataset_sizes = {"train": 2654, "valid": 885, "test": 885}

    if not results_csv.is_absolute():
        results_csv = REPO_ROOT / results_csv
    if not output_json.is_absolute():
        output_json = REPO_ROOT / output_json

    results_df = pd.read_csv(results_csv)

    if selected_model not in results_df["model"].values:
        raise ValueError(
            f"'{selected_model}' 이 {results_csv.name} 의 model 컬럼에 없음. "
            f"존재하는 값: {results_df['model'].tolist()}"
        )

    models = [_row_to_model_entry(row) for _, row in results_df.iterrows()]

    metrics = {
        "generated_at": str(date.today()),
        "dataset": dataset_sizes,
        "threshold": threshold,
        "selected": selected_model,
        "models": models,
        "feature_importance": normalize_importance(importance_csv, top_n=top_n_importance),
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {output_json.relative_to(REPO_ROOT)}")
    return metrics


if __name__ == "__main__":
    # 터미널에서 직접 실행할 때 기본값: 팀 최종 채택 모델(LightGBM) 기준으로 조립.
    # 다른 모델이 선정되면 아래 두 줄만 바꿔서 다시 실행하면 된다.
    build_model_metrics(
        selected_model="LightGBM",
        importance_csv="reports/lightgbm_importance.csv",
    )