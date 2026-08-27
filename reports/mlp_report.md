# MLP(딥러닝) 모델링 결과 리포트

- 작성자: 조현주
- 작성일: 2026-08-28
- 노트북: `notebooks/modeling_mlp.ipynb`
- 관련 파일: `models/mlp.keras`, `models/mlp_threshold.json`, `reports/3) model_results.csv`

---

## 1. 모델 학습 및 튜닝 과정

기본 구조 설계 → EarlyStopping 기준 문제 발견 및 수정 → threshold 조정까지
4단계에 걸쳐 성능을 비교했다.

| 단계 | 설정 | Recall | F1 |
|---|---|---|---|
| 1-1. 1차 시도 (수정 전) | Dense(128-64-32-1), BatchNorm+Dropout, `class_weight="balanced"`, EarlyStopping(`monitor="val_recall"`) | 0.8737 | 0.7557 |
| 1-2. monitor 수정 후, threshold=0.50 (기본값) | 동일 구조, EarlyStopping(`monitor="val_f1_metric"`, 커스텀 지표) | 0.8351 | **0.8151** |
| 1-3. threshold=0.35 | 1-2 모델에 임계값만 조정 | 0.8456 | 0.7902 |
| **1-4. threshold=0.40 ← 최종 채택** | 1-2 모델에 임계값만 조정 | **0.8421** | 0.8040 |

### 1-1. 모델 구조

```python
model = keras.Sequential([
    layers.Input(shape=(X_train.shape[1],)),

    layers.Dense(128, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.3),

    layers.Dense(64, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.3),

    layers.Dense(32, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.2),

    layers.Dense(1, activation="sigmoid")
])
```

- 총 파라미터: 21,761개 (Trainable 21,313 / Non-trainable 448)
- 클래스 불균형(32:68) 보정을 위해 `class_weight="balanced"` 적용
- 입력 shape: (81,)

### 1-2. EarlyStopping 기준 문제 발견 및 수정

**1차 시도 (monitor="val_recall")**: `patience=15`로 설정했으나 16 epoch만에 학습이 종료됨.
`restore_best_weights=True`였기 때문에 실제로는 **1번째 epoch 가중치가 최종 모델로 복원**된 것으로 확인됨.

- 원인: 학습 초반 `class_weight="balanced"`의 영향으로, 모델이 패턴을 제대로 배우기 전부터
  "양성(자퇴)으로 많이 예측"하는 경향을 보여 recall이 우연히 높게 나타남
- `val_recall`만 단독으로 모니터링할 경우, 이런 얕은 상태를 "최고 성능"으로 오판할 위험이 있음을 확인

**수정**: Precision과 Recall을 함께 반영하는 커스텀 F1 지표를 정의하여 EarlyStopping 기준으로 교체

```python
def f1_metric(y_true, y_pred):
    y_true = K.cast(y_true, "float32")
    y_pred = K.cast(K.round(y_pred), "float32")

    tp = K.sum(y_true * y_pred)
    fp = K.sum((1 - y_true) * y_pred)
    fn = K.sum(y_true * (1 - y_pred))

    precision = tp / (tp + fp + K.epsilon())
    recall = tp / (tp + fn + K.epsilon())
    return 2 * precision * recall / (precision + recall + K.epsilon())

early_stop = keras.callbacks.EarlyStopping(
    monitor="val_f1_metric",
    mode="max",
    patience=15,
    restore_best_weights=True
)
```

수정 후에는 **7번째 epoch**(val_f1_metric 0.8045)가 최고 기록으로 확인되었고, 이후 15 epoch 동안
개선이 없어 22 epoch에서 학습 종료 및 해당 가중치로 복원됨. train/val 지표 추이를 보면
21~22 epoch 구간에서 train f1(0.88)과 val f1(0.78)의 격차가 벌어지는 **과적합 패턴**이 뚜렷했으며,
이는 EarlyStopping이 정상적으로 이를 감지하고 이전 시점(7 epoch)으로 되돌렸음을 보여준다.

### 1-3. Threshold(임계값) 조정

`predict()`의 기본 판정 기준(0.5)을 조정하며 Recall/Precision 트레이드오프를 탐색.

| threshold | Recall | Precision | F1 |
|---|---|---|---|
| 0.10 | 0.9298 | 0.5354 | 0.6795 |
| 0.20 | 0.8982 | 0.6432 | 0.7496 |
| 0.30 | 0.8596 | 0.7164 | 0.7815 |
| 0.35 | 0.8456 | 0.7415 | 0.7902 |
| **0.40** | **0.8421** | **0.7692** | **0.8040** |
| 0.45 | 0.8386 | 0.7810 | 0.8088 |
| 0.50 (기본) | 0.8351 | 0.7960 | 0.8151 |
| 0.60 | 0.7860 | 0.8266 | 0.8058 |

threshold를 낮출수록 Recall은 상승하지만 Precision·F1이 함께 하락하는 트레이드오프를 확인.
0.35 적용 시 LightGBM 채택 모델(threshold=0.50)과 Recall이 거의 동일한 수준(0.8456)까지 근접하나,
F1 손실(0.7902)이 상대적으로 큰 편이었다.

## 2. 최종 평가 결과 (채택 모델 기준: threshold=0.40)

```
최종 채택 threshold: 0.40
Recall: 0.8421
Precision: 0.7692
F1: 0.8040

              precision    recall  f1-score   support

           0       0.92      0.88      0.90       600
           1       0.77      0.84      0.80       285

    accuracy                           0.87       885
   macro avg       0.85      0.86      0.85       885
weighted avg       0.87      0.87      0.87       885
```

- 자퇴(class 1) Recall 0.84 → 실제 자퇴생 285명 중 약 240명을 정확히 탐지
- 자퇴(class 1) Precision 0.77 → 위험군으로 예측한 학생 중 77%가 실제 자퇴

## 3. 최종 모델 선정 이유

| 후보 | Recall | F1 | 채택 여부 |
|---|---|---|---|
| threshold=0.50 (기본값) | 0.8351 | **0.8151** | F1은 최고지만 Recall이 LightGBM 대비 낮음 |
| **threshold=0.40 ← 메인 채택** | **0.8421** | 0.8040 | ✅ Recall·F1 균형 + LightGBM과 비교 가능한 수준 |
| threshold=0.35 | 0.8456 | 0.7902 | Recall은 LightGBM과 거의 동일하나 F1 손실이 더 큼 |

- 팀 평가 기준(Recall 우선, 자퇴생을 놓치는 False Negative가 가장 costly)에 따라
  기본값(threshold=0.50)보다 Recall을 끌어올릴 필요가 있다고 판단
- threshold=0.35는 Recall을 LightGBM과 완전히 맞출 수 있으나, F1 손실(0.7902)이 상대적으로 커서
  "Recall만 맞추고 전체 균형은 포기한 모델"이 될 위험이 있음
- **threshold=0.40이 Recall(0.8421)을 LightGBM(0.8596)에 근접시키면서도 F1(0.8040)의 손실을
  최소화하는 절충점**으로 판단하여 최종 채택
- LightGBM(Recall 0.8596, F1 0.8046, threshold=0.50)과 비교 시, F1은 거의 동률이나
  Recall은 LightGBM이 근소 우위 → **정형 데이터에서는 트리 기반 모델이 신경망보다
  안정적으로 소수 클래스를 탐지**한다는 것을 보여주는 비교 포인트로 활용 가능

## 4. 원인 설명(Feature Importance)에 대한 한계

MLP는 LightGBM과 같은 트리 기반 모델과 달리 **분기(split) 기준의 feature importance를
직접 제공하지 않는다**. 가중치 자체는 여러 뉴런에 걸쳐 얽혀 있어 "어떤 변수가 중요했는가"를
바로 해석하기 어렵기 때문에, 별도의 설명 기법(SHAP, Permutation Importance 등)이 필요하다.

- 본 프로젝트에서는 시간 제약 상 MLP에 대한 별도 SHAP 분석은 진행하지 않았음.
- MLP는 "동일 데이터에서 트리 모델과 비교했을 때 성능이 어느 정도 나오는가"를 보여주는
  **비교 실험(ML vs DL) 목적**으로 자리매김

## 5. 저장 산출물

| 파일 | 내용 |
|---|---|
| `models/mlp.keras` | 최종 채택 모델 (Dense 128-64-32-1, threshold=0.40 기준) |
| `models/mlp_threshold.json` | 최종 채택 threshold(0.40) 기록 — Streamlit 앱에서 동일하게 재사용 |
| `reports/3) model_results.csv` | 팀 전체 모델 비교표에 기록 (model, threshold, recall, precision, f1) |