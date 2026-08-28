# XGBoost 모델링 결과 리포트

* 작성자: [정은미]
* 작성일: 2026-08-28
* 노트북: `notebooks/xgboost_report.ipynb`
* 관련 파일: `models/xgboost.joblib`, `reports/xgboost_importance.csv`, `reports/model_results.csv`

---

## 1. 모델 학습 및 튜닝 과정

중도탈락(Dropout) 가능성이 있는 학생을 사전에 탐지하는 것을 목적으로 XGBoost 모델을 구축했다.

기본 XGBoost 모델을 기준으로 하여 **하이퍼파라미터 탐색 횟수(n_iter)**와 **분류 임계값(Threshold)**을 반복적으로 테스트했다.

본 프로젝트에서는 실제 Dropout 학생을 놓치지 않는 것이 중요하기 때문에 **Recall을 주요 평가 지표**로 설정했다.

다만 Recall만 최대화할 경우 Threshold가 지나치게 낮아지면서 많은 학생을 Dropout 위험군으로 잘못 분류할 수 있고, Precision과 F1-score가 크게 하락할 수 있다.

따라서 최종적으로는 다음과 같은 기준을 적용했다.

> **F1-score가 0.8 이상인 후보만 남긴 뒤, 그중 Dropout Recall이 가장 높은 모델을 최종 모델로 선정**

### 모델 비교 및 튜닝 기준

| 단계           | 설정                                     | 주요 기준            |
| ------------ | -------------------------------------- | ---------------- |
| Baseline     | 기본 XGBoost, threshold=0.5              | 기본 성능 확인         |
| 튜닝           | RandomizedSearchCV, `scoring="recall"` | CV Recall 최대화    |
| Threshold 탐색 | 0.30 ~ 0.80, 0.01 간격                   | Validation 성능 비교 |
| **최종 선택**    | F1 >= 0.8 후보만 유지                       | **Recall 최대화**   |

---

## 1-1. Baseline XGBoost

Baseline 모델은 별도의 하이퍼파라미터를 지정하지 않고 XGBoost 기본 설정에서 출발했다.

클래스 불균형 문제를 보완하기 위해 `scale_pos_weight`를 적용했다.

```python
baseline_model = XGBClassifier(
    scale_pos_weight=weight,
    random_state=42
)
```

`scale_pos_weight`는 다음과 같이 계산했다.

```python
weight = 
    len(y_train[y_train == 0]) /
    len(y_train[y_train == 1])
```

본 프로젝트에서는

* `0` = Non-Dropout
* `1` = Dropout

이므로, 상대적으로 적은 Dropout 클래스가 학습 과정에서 충분히 고려되도록 가중치를 적용했다.

Baseline의 최종 Test 성능은 다음과 같다.

| 지표                 |      Baseline |
| ------------------ | ------------: |
| Accuracy           |     [0.8768] |
| Precision          |     [0.8159] |
| **Dropout Recall** | **[0.7958]** |
| F1-score           |     [0.8057] |
| ROC-AUC            |     [0.9149] |

---

## 1-2. 하이퍼파라미터 튜닝

`RandomizedSearchCV`를 사용하여 XGBoost의 주요 하이퍼파라미터를 탐색했다.

탐색 대상은 다음과 같다.

```python
param_dist = {
    'n_estimators': [100, 200, 300],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.01, 0.05, 0.1],
    'subsample': [0.8, 0.9, 1.0]
}
```

총 하이퍼파라미터 조합은 **81개**이며, `n_iter`를 변경하면서 탐색 범위를 단계적으로 비교했다.

```python
n_iter_list = [10, 20, 30, 40, 50, 60, 70, 81]
```

5-Fold Stratified Cross Validation을 적용했으며, 하이퍼파라미터 탐색 단계에서는 **Recall을 scoring 기준으로 사용**했다.

```python
RandomizedSearchCV(
    estimator=xgb_model,
    param_distributions=param_dist,
    n_iter=n_iter,
    scoring='recall',
    cv=skf,
    random_state=42,
    n_jobs=-1
)
```

### 최종 선택 기준

단순히 Recall이 가장 높은 모델을 선택하지 않았다.

Recall만 기준으로 선택할 경우 Threshold가 낮아지면서 실제 Dropout 학생을 많이 찾아낼 수 있지만, Non-Dropout 학생까지 Dropout 위험군으로 분류하는 경우가 증가하여 F1-score가 크게 낮아지는 문제가 확인됐다.

따라서 다음의 조건을 적용했다.

```text
① Validation F1 >= 0.8
② 위 조건을 만족하는 후보 중 Recall 최대
③ Recall 동률 → F1 높은 모델
④ F1 동률 → ROC-AUC 높은 모델
```

---

## 1-3. Threshold(임계값) 탐색

XGBoost가 출력하는 Dropout 확률에 대해 기본값인 0.5뿐만 아니라 여러 Threshold를 적용하여 성능을 비교했다.

탐색 범위는 다음과 같다.

```python
threshold_list = np.arange(0.30, 0.81, 0.01)
```

즉, 0.30부터 0.80까지 0.01 단위로 모든 Threshold를 테스트했다.

Threshold를 낮추면 Dropout으로 판정되는 학생이 증가하기 때문에 일반적으로 Recall은 높아지는 반면 Precision과 F1-score는 낮아질 수 있다.

이번 프로젝트에서도 이러한 **Recall과 F1-score 사이의 Trade-off**를 확인했다.

따라서 단순히 Recall이 가장 높은 Threshold가 아니라,

> **F1 >= 0.8을 만족하면서 Recall이 가장 높은 Threshold**

를 선택하도록 설정했다.

---

## 1-4. 최종 Tuned XGBoost

탐색 결과, 최종 모델은 다음 조합으로 선정되었다.

| 항목                            |       최종 값 |
| ----------------------------- | ---------: |
| n_iter                        |     **10** |
| Threshold                     |   **0.59** |
| Validation Accuracy           | **0.8712** |
| Validation Precision          | **0.8000** |
| **Validation Dropout Recall** | **0.8000** |
| **Validation F1-score**       | **0.8000** |
| Validation ROC-AUC            | **0.9153** |

최종 모델의 하이퍼파라미터는 탐색 결과에 따라 결정되었으며, 실제 최적 파라미터는 코드 실행 결과의 `best_result['Best_Params']`를 기준으로 기록한다.

---

## 2. 최종 Validation 평가 결과

최종 선정된 XGBoost 모델에 `Threshold=0.59`를 적용한 Validation 결과는 다음과 같다.

```text
n_iter         : 10
Threshold      : 0.59
Accuracy       : 0.8712
Precision      : 0.8000
Dropout Recall : 0.8000
F1-score       : 0.8000
ROC-AUC        : 0.9153
```

Classification Report:

```text
              precision    recall  f1-score   support

 Non-Dropout       0.91      0.91      0.91       600
     Dropout       0.80      0.80      0.80       285

    accuracy                           0.87       885
   macro avg       0.85      0.85      0.85       885
weighted avg       0.87      0.87      0.87       885
```

### Confusion Matrix

```text
[[543  57]
 [ 57 228]]
```

|                | 예측 Non-Dropout | 예측 Dropout |
| -------------- | -------------: | ---------: |
| 실제 Non-Dropout |       TN = 543 |    FP = 57 |
| 실제 Dropout     |        FN = 57 |   TP = 228 |

따라서 Validation 데이터의 실제 Dropout 학생 285명 중 **228명을 Dropout으로 정확하게 탐지**했다.

즉,

> **Dropout Recall = 228 / 285 = 0.80**

으로, 실제 중도탈락 학생의 약 **80%를 사전에 위험군으로 탐지**할 수 있었다.

---

## 3. 최종 모델 선정 이유

이번 프로젝트의 목적은 단순히 전체 예측 정확도를 높이는 것이 아니라,

> **중도탈락 가능성이 있는 학생을 최대한 놓치지 않고 사전에 찾아내어 관리하는 것**

이다.

따라서 Dropout Recall을 중요하게 평가했다.

그러나 Recall만을 무조건 최대화할 경우 Threshold가 지나치게 낮아지고, 실제로 중도탈락하지 않는 학생까지 위험군으로 많이 분류하게 된다.

실제로 Recall만을 기준으로 탐색했을 때 Threshold가 **0.30**까지 낮아졌으며, Validation Recall은 약 **0.94**까지 증가했지만 F1-score는 약 **0.67** 수준으로 크게 하락했다.

따라서 다음과 같이 기준을 변경했다.

```text
Recall 최대화
        ↓
F1 >= 0.8인 후보만 유지
        ↓
그중 Recall 최대인 모델 선택
```

이를 통해 **중도탈락 학생을 놓치지 않는 것(Recall)**과 **위험군 예측의 균형(F1)**을 동시에 고려했다.

최종 모델은 Validation 기준으로 Recall 0.80, F1 0.80을 달성했다.

---

## 4. Feature Importance

최종 Tuned XGBoost 모델의 `feature_importances_`를 이용하여 각 변수가 중도탈락 예측에 얼마나 활용되었는지 확인했다.

상위 Feature는 `reports/xgboost_importance.csv`에 저장한다.

| 순위 | Feature                                   | Importance |
| -- | ------------------------------------------ | ---------: |
| 1  | [num__sem2_approval_rate]                  |   [0.340802] |
| 2  | [num__sem1_approval_rate]                  |   [0.084654] |
| 3  | [remainder__financial_risk_score]          |   [0.063248] |
| 4  | [remainder__Tuition fees up to date]       |   [0.056756] |
| 5  | [num__Curricular units 1st sem (enrolled)] |   [0.049108] |
| 6  | [num__Age at enrollment]                   |   [0.046765] |
| 7  | [cat__Major_field_예술·디자인]               |   [0.035199] |
| 8  | [num__Curricular units 2nd sem (grade)]    |   [0.028440] |
| 9  | [remainder__Gender]                        |   [0.026863] |
| 10 | [cat__Mother_education_level_미상·기타]      |   [0.026785] |

Feature Importance는 **예측에 많이 활용된 변수**를 보여주는 지표이며, 해당 변수가 중도탈락의 직접적인 원인이라는 의미로 해석하지 않는다.

---

## 5. 프로젝트 관점에서의 활용

최종 모델의 목적은 단순히 학생을 `Dropout / Non-Dropout`으로 분류하는 것이 아니다.

모델이 산출한 Dropout 확률을 이용하여 중도탈락 위험이 높은 학생을 선별하고, 학교 측에서 사전에 상담이나 학업·재정 지원 등의 관리 활동을 수행할 수 있도록 하는 것이 목적이다.

예를 들어 다음과 같이 활용할 수 있다.

```text
학생 데이터
    ↓
XGBoost
    ↓
Dropout 확률 산출
    ↓
Threshold = 0.59
    ↓
위험군 / 일반군 분류
    ↓
위험군 학생 사전 관리
```

따라서 본 모델에서는 Accuracy보다 **Dropout Recall과 F1-score의 균형**을 중요하게 고려했다.

---

## 6. 저장 산출물

| 파일                               | 내용                                     |
| -------------------------------- | -------------------------------------- |
| `models/xgboost.joblib`          | 최종 Tuned XGBoost 모델                    |
| `reports/xgboost_importance.csv` | 최종 모델 Feature Importance               |
| `reports/model_results.csv`      | Baseline과 Tuned XGBoost의 최종 Test 성능 비교 |

### 최종 모델 설정

```text
Model       : Tuned XGBoost
n_iter      : 10
Threshold   : 0.59
CV scoring  : Recall
F1 조건     : Validation F1 >= 0.8
최종 선택   : F1 >= 0.8 후보 중 Recall 최대
```

---

## 8. 최종 요약

이번 모델링에서는 XGBoost를 활용하여 중도탈락 가능성이 있는 학생을 사전에 탐지하는 모델을 구축했다.

하이퍼파라미터 탐색에서는 **Recall을 scoring 기준으로 설정**하여 실제 Dropout 학생을 놓치지 않는 방향으로 모델을 탐색했다.

이후 Threshold를 0.30~0.80 범위에서 반복적으로 테스트했으며, Recall만을 최대화할 경우 F1-score가 지나치게 낮아지는 문제가 확인되었다.

따라서 **Validation F1 >= 0.8이라는 최소 기준을 설정하고, 해당 조건을 만족하는 모델 중 Recall이 가장 높은 조합을 최종 모델로 선정**했다.

최종 Validation 결과는 다음과 같다.

> **Accuracy 0.8712 / Precision 0.8000 / Dropout Recall 0.8000 / F1-score 0.8000 / ROC-AUC 0.9153**

이를 통해 단순히 높은 정확도를 얻는 것보다, **실제 중도탈락 학생을 놓치지 않으면서도 불필요한 위험군 분류를 과도하게 늘리지 않는 방향**으로 모델을 선정했다.
