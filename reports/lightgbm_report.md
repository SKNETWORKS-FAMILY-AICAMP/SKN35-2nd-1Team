  # LightGBM 모델링 결과 리포트

- 작성자: 조현주
- 작성일: 2026-08-28
- 노트북: `notebooks/modeling_lightgbm.ipynb`, `notebooks/best_modeling_lightgbm.ipynb` (test 평가 전용)
- 관련 파일: `models/lightgbm.joblib`, `models/best_model.joblib`, `reports/lightgbm_importance.csv`, `reports/3) model_results.csv`

---

## 1. 모델 학습 및 튜닝 과정

기본 모델에서 출발해 하이퍼파라미터 튜닝, 임계값(threshold) 조정, 탐색 기준 지표 변경까지
5단계에 걸쳐 성능을 비교했다.

| 단계 | 설정 | Recall | F1 | F2 |
|---|---|---|---|---|
| 2-1. Baseline | 기본 파라미터, `class_weight="balanced"`, threshold=0.5 | 0.8456 | 0.8033 | - |
| 2-2. 튜닝 (n_iter=30) | RandomizedSearchCV, scoring="recall" | 0.8491 | 0.7987 | - |
| **2-3. 튜닝 (n_iter=80) ← 최종 채택** | RandomizedSearchCV, scoring="recall" | **0.8596** | **0.8046** | - |
| 2-4. 튜닝(n_iter=80) + threshold=0.35 | 2-3 모델에 임계값만 조정 | 0.9018 | 0.7581 | - |
| 2-5. F2 Score 기준 재탐색 + threshold=0.35 | scoring을 F2(beta=2)로 변경 | 0.9018 | 0.7581 | 0.8382 |

### 1-1. Baseline (2-1)
```python
model = lgb.LGBMClassifier(
    objective="binary",
    class_weight="balanced",
    random_state=42
)
```
클래스 불균형(32:68) 보정을 위해 `class_weight="balanced"` 적용. Early stopping(50 rounds)을 걸었으나
정체 없이 66번째 라운드에서 최적점 도달 (`Did not meet early stopping`).

### 1-2. 하이퍼파라미터 튜닝 (2-2 → 2-3)
`RandomizedSearchCV`로 `num_leaves`, `max_depth`, `learning_rate`, `n_estimators`, `min_child_samples`,
`subsample`, `colsample_bytree` 7개 파라미터를 탐색.

- n_iter=30에서는 Recall만 미세하게 개선(F1은 오히려 소폭 하락) → 우연적 변동 수준으로 판단
- **n_iter=80으로 탐색 횟수를 늘리자 Recall·F1 모두 baseline 대비 개선** → 이 결과를 최종 모델로 채택

최적 하이퍼파라미터:
```python
{'subsample': 0.8, 'num_leaves': 15, 'n_estimators': 300,
 'min_child_samples': 20, 'max_depth': -1, 'learning_rate': 0.01,
 'colsample_bytree': 0.8}
```
학습률(learning_rate)을 0.01로 낮추고 트리 개수(n_estimators)를 300으로 늘려 천천히, 많이 학습하는 방향으로 조정되었고, num_leaves를 15로 제한해 개별 트리의 복잡도는 낮춘 조합.

### 1-3. Threshold(임계값) 조정 (2-4)
`predict()`의 기본 판정 기준(0.5)을 낮춰 Recall을 추가로 끌어올리는 실험.

| threshold | Recall | F1 |
|---|---|---|
| 0.30 | 0.9123 | 0.7525 |
| 0.35 | 0.8912 | 0.7616 |
| 0.40 | 0.8807 | 0.7795 |
| 0.45 | 0.8667 | 0.7917 |
| 0.50 (기본) | 0.8596 | 0.8046 |

threshold를 낮출수록 Recall은 상승하지만 Precision·F1이 함께 하락하는 트레이드오프 확인.
0.35 적용 시 Recall 0.9018까지 상승하나, Precision은 0.65 수준으로 하락(오탐 35%).

### 1-4. F2 Score 기준 재탐색 (2-5)
Recall에 2배 가중치를 준 F2(beta=2) 스코어로 다시 탐색했으나, 동일한 파라미터 조합·동일한 결과로 수렴.
→ 현재 탐색 범위(`param_dist`) 내에서는 Recall 기준과 F2 기준의 최적점이 사실상 일치하며,
   추가 탐색 대비 효과가 크지 않은 것으로 판단.

## 2. 최종 평가 결과 (채택 모델 기준: 2-3, threshold=0.5)

### Val 성능
```
Recall: 0.8596, F1: 0.8046

              precision    recall  f1-score   support
           0       0.93      0.87      0.90       600
           1       0.76      0.86      0.80       285

    accuracy                           0.87       885
   macro avg       0.84      0.86      0.85       885
weighted avg       0.87      0.87      0.87       885
```

- 자퇴(class 1) Recall 0.86 → 실제 자퇴생 285명 중 약 245명을 정확히 탐지
- 자퇴(class 1) Precision 0.76 → 위험군으로 예측한 학생 중 76%가 실제 자퇴

### Test 성능
```
Recall: 0.8345, F1: 0.8215

              precision    recall  f1-score   support
           0       0.92      0.91      0.91       601
           1       0.81      0.83      0.82       284

    accuracy                           0.88       885
   macro avg       0.86      0.87      0.87       885
weighted avg       0.88      0.88      0.88       885
```

- Val 대비 Recall은 소폭 하락(-0.025), F1은 오히려 소폭 상승(+0.017) — 두 지표가 서로 다른
  방향으로 미세하게 움직인 것으로, 과적합 신호라기보다 정상적인 표본 변동 범위로 판단
- 자퇴(class 1) Precision이 val(0.76)보다 test(0.81)에서 더 높게 나와, 위험군 예측의 신뢰도가
  test에서도 안정적으로 유지됨을 확인

## 3. 최종 모델 선정 이유

| 후보 | Recall | F1 | 채택 여부 |
|---|---|---|---|
| **튜닝(n_iter=80), threshold=0.5** | 0.8596 | **0.8046** | ✅ 메인 채택 |
| 튜닝(n_iter=80), threshold=0.35 | 0.9018 | 0.7581 | 참고용 보조 옵션 |

- threshold=0.35 옵션은 Recall은 가장 높지만 Precision 손실(0.65)이 커서 메인으로 채택하지 않음
- 팀 전체 5개 모델(LightGBM/MLP/LR/RF/XGBoost)을 공통 threshold=0.5 기준으로 재비교한 결과,
  LightGBM이 recall 기준 1위를 유지 → **8/28 팀 회의에서 최종 모델로 확정**
  (자세한 비교 과정은 `reports/4) final_model_selection_report.md` 참고)

## 4. 어떤 요인이 자퇴에 가장 큰 영향을 미쳤는가 (Feature Importance)

`reports/lightgbm_importance.csv`를 기준으로, 최종 채택 모델이 분기(split)에 가장 많이 사용한
상위 10개 피처는 다음과 같다. (컬럼명의 `num__`, `cat__`, `remainder__`는 전처리 단계
ColumnTransformer가 붙인 접두사이며, 아래 표에서는 가독성을 위해 제거했다.)

| 순위 | 피처 | Importance | 해석 |
|---|---|---|---|
| 1 | Age at enrollment (입학 시 나이) | 180 | 압도적 1위. 늦은 나이에 입학한 학생일수록 자퇴 경향과 연관 |
| 2 | Admission grade (입학 성적) | 176 | 입학 당시 학업 역량이 자퇴 여부와 밀접하게 연관됨 |
| 3 | sem2_approval_rate (2학기 이수율) | 142 | 2학기 학점 이수율이 낮을수록 자퇴 위험 신호 |
| 4 | Previous qualification (grade) | 136 | 이전 학력 성적 |
| 5 | sem1_approval_rate (1학기 이수율) | 134 | 1학기부터 학업 부진 신호가 나타남 |
| 6 | 2nd sem 성적(grade) | 130 | 2학기 학업 성취도 |
| 7 | Tuition fees up to date (등록금 납부 여부) | 108 | 등록금 연체 여부 — top10 중 유일한 재정 관련 변수 |
| 8 | grade_change (성적 변화량, 파생변수) | 102 | 1학기→2학기 성적 하락 폭이 클수록 위험 신호 |
| 9 | 2nd sem 평가 응시 횟수(evaluations) | 101 | 2학기 시험/평가 참여 빈도 |
| 10 | 1st sem 평가 응시 횟수(evaluations) | 74 | 1학기 시험/평가 참여 빈도 |

**핵심 요약 — 3가지 축으로 정리 (정정됨):**

1. **학업 이수 관련 (2~6, 8~10위 — 8개)** — 상위 10개 중 압도적으로 가장 많은 비중을 차지.
   입학 성적·이전 학력 성적 같은 "입학 시점 학업 역량"과, 학기 이수율·성적 변화·평가 응시
   횟수 같은 "재학 중 학업 궤적"이 모두 강한 신호로 작동함
2. **재정 관련 (7위, 단 1개)** — 등록금 납부 여부만 top10에 포함됨. **`financial_risk_score`는
   더 이상 top10에 들지 않음** — 최초 작성 시 재정 요인의 비중을 과대평가했던 부분을 정정함
3. **인구통계/배경 (1위)** — 입학 나이가 전체 1위로, 개별 요인 중 가장 강력한 신호. 다만 이 요인은
   대학이 직접 개입할 수 없는(non-actionable) 변수이므로, STEP 8 대응 규칙 설계 시 "원인 설명"에는
   활용하되 "개입 방안"으로는 연결하지 않음

**STEP 8 관련 참고사항**: 재정 관련 요인의 비중이 예상보다 낮게 나왔으므로, 세희님의 기존 규칙 중
재정 카테고리(F1~F3)의 상대적 우선순위를 발표 자료에서 과장하지 않도록 유의할 것. 반면 "입학 성적/이전
학력 성적이 낮은 학생"에 대한 신규 규칙(A6 제안, 지난 논의 참고)의 근거는 이번 정정으로 오히려
강화됨(Admission grade가 2위로 상승).

![상위 10개 피처 중요도](lightgbm_importance_top10.png)


## 5. 저장 산출물

| 파일 | 내용 |
|---|---|
| `models/lightgbm.joblib` | 최종 채택 모델 (n_iter=80 튜닝 결과) |
| `models/best_model.joblib` | 팀 최종 선정 모델 (Streamlit 앱 연동용, lightgbm.joblib과 동일) |
| `reports/lightgbm_importance.csv` | Feature Importance (원인 분석용) |
| `reports/lightgbm_importance_top10.png` | 상위 10개 피처 중요도 시각화 (본 리포트에 삽입) |
| `reports/3) model_results.csv` | 팀 전체 모델 비교표 (val/test recall·f1 포함) |