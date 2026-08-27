"""
평가 계산 — 정답 라벨과 예측 확률만으로 성능 지표를 만든다.

왜 sklearn 을 부르지 않는가
    `requirements.txt` 는 팀 공용이다. 화면 한 장 때문에 무거운 의존을 새로 얹지 않는다.
    여기서 필요한 계산(혼동행렬 · ROC-AUC · PR 곡선)은 정렬과 누적합이면 끝난다.

왜 이 계층이 따로 있는가
    화면에서 numpy 를 직접 만지면 임계값 정의가 화면마다 갈라진다. **"임계값 t 이상이면
    Dropout"** 이라는 정의를 이 파일 하나만 알게 한다.

🔴 이 모듈은 확률이 어디서 왔는지 모른다.
    더미 예측기의 확률을 넣어도 숫자는 나온다. **학습되지 않은 값으로 성능을 계산해
    화면에 띄우면 없는 성능을 주장하는 것**이므로, 호출하는 쪽(views/4_model.py)이
    실제 모델인지 먼저 확인한다. 그 판단을 이 파일에서 하지 않는 이유는, 테스트가
    더미 확률로도 계산 자체를 검증할 수 있어야 하기 때문이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Confusion:
    """이진 혼동행렬. 팀 정의대로 1=Dropout 을 양성으로 본다."""

    threshold: float
    tn: int
    fp: int
    fn: int
    tp: int

    @property
    def total(self) -> int:
        return self.tn + self.fp + self.fn + self.tp

    @property
    def flagged(self) -> int:
        """모델이 위험하다고 표시한 인원 = 상담 대상 규모."""
        return self.tp + self.fp

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total else 0.0

    @property
    def precision(self) -> float:
        denominator = self.tp + self.fp
        return self.tp / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        """놓치지 않은 비율. 이 제품의 운영 지표는 정확도가 아니라 이쪽이다."""
        denominator = self.tp + self.fn
        return self.tp / denominator if denominator else 0.0

    @property
    def specificity(self) -> float:
        denominator = self.tn + self.fp
        return self.tn / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _validate(labels: Sequence[int], probabilities: Sequence[float]) -> None:
    if len(labels) != len(probabilities):
        raise ValueError(
            f"라벨 {len(labels)}개와 확률 {len(probabilities)}개의 수가 다릅니다. "
            "명단과 정답이 어긋난 상태로 계산하면 성능이 조용히 거짓이 됩니다."
        )
    if not labels:
        raise ValueError("평가할 데이터가 없습니다.")


def confusion_at(
    labels: Sequence[int], probabilities: Sequence[float], threshold: float
) -> Confusion:
    """확률 ≥ threshold 이면 Dropout 으로 판정했을 때의 혼동행렬."""
    _validate(labels, probabilities)
    tn = fp = fn = tp = 0
    for label, probability in zip(labels, probabilities):
        predicted = probability >= threshold
        if label == 1:
            if predicted:
                tp += 1
            else:
                fn += 1
        else:
            if predicted:
                fp += 1
            else:
                tn += 1
    return Confusion(threshold=float(threshold), tn=tn, fp=fp, fn=fn, tp=tp)


def roc_auc(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """순위 기반 AUC (Mann-Whitney U).

    동점 확률은 **평균 순위**로 처리한다. 더미 예측기처럼 같은 값이 여럿 나오는
    상황에서 동점을 무시하면 AUC 가 실제보다 좋게 나온다.
    """
    _validate(labels, probabilities)
    positives = sum(1 for label in labels if label == 1)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return 0.5

    order = sorted(range(len(probabilities)), key=lambda i: probabilities[i])
    ranks = [0.0] * len(order)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and probabilities[order[end + 1]] == probabilities[order[index]]:
            end += 1
        average = (index + end) / 2 + 1          # 순위는 1부터
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1

    rank_sum = sum(rank for rank, label in zip(ranks, labels) if label == 1)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def sweep(
    labels: Sequence[int], probabilities: Sequence[float], *, steps: int = 101
) -> list[Confusion]:
    """임계값을 0~1 로 훑은 혼동행렬 목록. 곡선과 트레이드오프 표가 이걸 쓴다."""
    _validate(labels, probabilities)
    return [confusion_at(labels, probabilities, index / (steps - 1)) for index in range(steps)]


def pr_points(matrices: Sequence[Confusion]) -> list[tuple[float, float]]:
    """(재현율, 정밀도) 점 목록. 재현율 오름차순으로 정리해 곡선으로 그린다."""
    points = [(m.recall, m.precision) for m in matrices if m.flagged > 0]
    return sorted(points)


def average_precision(matrices: Sequence[Confusion]) -> float:
    """PR 곡선 아래 면적 근사. 재현율 증가분 × 그 지점의 정밀도."""
    points = pr_points(matrices)
    if not points:
        return 0.0
    area = 0.0
    previous_recall = 0.0
    for recall, precision in points:
        area += (recall - previous_recall) * precision
        previous_recall = recall
    return max(min(area, 1.0), 0.0)


def best_threshold(matrices: Sequence[Confusion], *, minimum_recall: float) -> Confusion | None:
    """재현율 하한을 만족하는 것 중 **상담 대상이 가장 적은** 임계값.

    "재현율 우선" 을 말로만 하지 않고 하나의 운영값으로 내놓는 자리다. 놓친 학생의
    비용이 헛걸음한 상담보다 크다는 전제를, 하한을 정하는 방식으로 드러낸다.
    """
    candidates = [m for m in matrices if m.recall >= minimum_recall]
    if not candidates:
        return None
    return min(candidates, key=lambda m: (m.flagged, -m.threshold))
