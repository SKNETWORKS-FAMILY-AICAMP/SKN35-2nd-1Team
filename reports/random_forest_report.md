# Random Forest 모델링 결과 리포트

- 작성일: 2026-08-28
- 노트북: `notebooks/modeling_random_forest.ipynb`
- 모델: `models/random_forest.joblib`
- 결과: `reports/model_results.csv`

---

## 1. 모델 개요

대학생 중도이탈(Dropout) 여부를 예측하기 위해 Random Forest를 적용하였다.

Target은 다음과 같이 이진 분류로 구성하였다.

- `1`: Dropout
- `0`: Non-Dropout (Graduate + Enrolled)

Random Forest는 여러 개의 Decision Tree를 결합하여 예측하는 앙상블 모델이다.
단일 Decision Tree보다 과적합을 줄이면서 변수 간 비선형적인 관계도 학습할 수 있다는
장점이 있다.

본 프로젝트에서는 단순 Accuracy뿐만 아니라 Precision, Recall,
F1-score, ROC-AUC를 함께 평가하였다.

특히 실제 중도이탈 학생을 놓치지 않는 것이 중요하기 때문에
Recall과 F1-score를 주요 지표로 고려하였다.

---

## 2. Baseline Random Forest

먼저 기본 Random Forest 모델을 학습하였다.

Validation 결과는 다음과 같다.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Baseline Random Forest | 0.8814 | 0.8462 | 0.7719 | 0.8073 | 0.9266 |

Accuracy와 Precision은 높은 수준이었지만 Recall은 0.7719로 나타났다.

즉, 전체적인 분류 성능은 안정적이었으나 실제 중도이탈 학생 중
일부를 놓칠 가능성이 있었다.

따라서 중도이탈 학생 탐지 성능을 개선하기 위해
하이퍼파라미터 튜닝을 진행하였다.

---

## 3. 하이퍼파라미터 튜닝

RandomizedSearchCV를 이용하여 Random Forest의 주요
하이퍼파라미터를 탐색하였다.

Cross Validation의 평가 기준은 F1-score를 사용하여
Precision과 Recall의 균형을 고려하였다.

최적 하이퍼파라미터는 다음과 같다.

- `n_estimators = 500`
- `max_depth = 20`
- `min_samples_split = 5`
- `min_samples_leaf = 2`
- `max_features = "sqrt"`
- `class_weight = "balanced"`

Best Cross Validation F1-score는 **0.7837**이었다.

튜닝 후 Validation 결과는 다음과 같다.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Baseline | 0.8814 | 0.8462 | 0.7719 | 0.8073 | 0.9266 |
| Tuned Random Forest | 0.8746 | 0.7862 | **0.8386** | **0.8115** | **0.9289** |

튜닝 후 Accuracy와 Precision은 일부 감소했지만,
Recall은

**0.7719 → 0.8386**

으로 개선되었다.

이는 실제 중도이탈 학생을 탐지하는 능력이 향상되었다는 의미이다.

---

## 4. Threshold 조정

튜닝된 Random Forest의 예측 확률을 이용하여
Threshold를 0.40~0.60 범위에서 비교하였다.

기본 Threshold=0.50에서는 Recall이 높았지만,
Precision과 Recall의 균형을 추가로 개선하기 위해
Threshold를 조정하였다.

Threshold=0.55에서:

- Precision: **0.8112**
- Recall: **0.8140**
- F1-score: **0.8126**

으로 Precision과 Recall이 약 0.81 수준에서 균형을 이루었다.

따라서 최종 Threshold를 **0.55**로 선정하였다.

---

## 5. 최종 Test 평가

최종 Tuned Random Forest와 Threshold=0.55를
Test 데이터에 적용하였다.

| Metric | Test Result |
|---|---:|
| Accuracy | **0.8915** |
| Precision | **0.8456** |
| Recall | **0.8099** |
| F1-score | **0.8273** |
| ROC-AUC | **0.9349** |
| Threshold | **0.55** |

최종 Test에서 F1-score 0.8273, ROC-AUC 0.9349를 기록하였다.

Precision 0.8456과 Recall 0.8099가 모두 0.80 이상으로 나타나
중도이탈 학생 탐지와 오탐 방지 사이에서 안정적인 균형을 보였다.

---

## 6. Feature Importance 분석

Random Forest의 `feature_importances_`를 이용하여
모델이 중도이탈 여부를 판단할 때 어떤 변수를 중요하게 활용했는지 분석하였다.

Feature Importance 값이 클수록 해당 변수가 Random Forest의
의사결정 과정에서 상대적으로 많이 활용되었다는 의미이다.

단, Feature Importance는 해당 변수가 중도이탈을 증가시키는지
감소시키는지에 대한 방향성을 나타내지는 않는다.

또한 Feature Importance가 높다고 해서 해당 변수가
중도이탈의 직접적인 원인이라는 의미는 아니다.

---

## 7. Feature Importance Top 10

| 순위 | Feature | Importance |
|---:|---|---:|
| 1 | sem2_approval_rate | **0.131186** |
| 2 | Curricular units 2nd sem (approved) | **0.108240** |
| 3 | sem1_approval_rate | **0.098014** |
| 4 | Curricular units 2nd sem (grade) | **0.080297** |
| 5 | Curricular units 1st sem (approved) | **0.059122** |
| 6 | Curricular units 1st sem (grade) | **0.047980** |
| 7 | financial_risk_score | **0.042798** |
| 8 | Tuition fees up to date | **0.038413** |
| 9 | grade_change | **0.036352** |
| 10 | Age at enrollment | **0.031950** |

---

## 8. 주요 Feature 해석

### 8-1. 2학기 이수율 (sem2_approval_rate)

가장 높은 Feature Importance를 보인 변수는
`sem2_approval_rate`로 Importance는 **0.131186**이었다.

이는 Random Forest가 학생의 중도이탈 여부를 판단할 때
2학기 이수율을 가장 중요한 변수로 활용했다는 의미이다.

특히 단순한 학생 배경 정보보다 실제 대학 생활 이후 나타나는
학업 수행 정보가 높은 중요도를 보였다는 점이 특징적이다.

---

### 8-2. 2학기 이수 과목 수

`Curricular units 2nd sem (approved)`는
Importance **0.108240**으로 전체 2위를 기록하였다.

1위인 2학기 이수율과 함께 2학기 학업 진행 상황을 나타내는 변수가
상위권을 차지하였다.

따라서 Random Forest는 학생의 중도이탈 위험을 구분할 때
최근 학업 수행 상태를 중요한 예측 신호로 활용하고 있음을 확인할 수 있다.

---

### 8-3. 1학기 이수율

`sem1_approval_rate`는 Importance **0.098014**로
전체 3위를 기록하였다.

1학기와 2학기 이수율이 모두 Top 3에 포함되면서,
학생의 실제 학업 이수 상태가 중도이탈 예측에 중요한 정보로
활용되고 있음을 확인할 수 있다.

---

### 8-4. 학기별 성적 및 이수 과목

Top 10에는 다음 학업 관련 Feature도 포함되었다.

- 2학기 평균 성적
- 1학기 이수 과목 수
- 1학기 평균 성적
- 성적 변화량(grade_change)

즉, 단순히 한 시점의 성적만 보는 것이 아니라
학생의 학업 이수 정도와 성적 변화가 함께
중도이탈 예측에 활용되고 있음을 확인하였다.

---

### 8-5. 재정 관련 Feature

`financial_risk_score`는 Importance **0.042798**로 7위,
`Tuition fees up to date`는 **0.038413**으로 8위를 기록하였다.

따라서 학업 관련 변수뿐만 아니라 학생의 재정 상태 역시
Random Forest의 중도이탈 예측에 활용되는 중요한 신호로 나타났다.

---

### 8-6. 입학 당시 나이

`Age at enrollment`는 Importance **0.031950**으로
Top 10에 포함되었다.

이는 학생의 학업·재정 정보뿐만 아니라 입학 당시의 개인적 배경 정보도
모델의 예측 과정에서 일정 부분 활용되었음을 의미한다.

다만 나이가 중도이탈의 직접적인 원인이라는 의미는 아니므로
해석에 주의할 필요가 있다.

---

## 9. Feature Importance 종합

Random Forest의 Top 10 Feature를 성격별로 분류하면 다음과 같다.

### 학업 관련

- sem2_approval_rate
- Curricular units 2nd sem (approved)
- sem1_approval_rate
- Curricular units 2nd sem (grade)
- Curricular units 1st sem (approved)
- Curricular units 1st sem (grade)
- grade_change

### 재정 관련

- financial_risk_score
- Tuition fees up to date

### 학생 배경

- Age at enrollment

Top 10 중 **7개가 학업 관련 Feature**로 나타났다.

따라서 Random Forest는 학생의 중도이탈 위험을 판단할 때
입학 당시의 정적인 정보보다 대학 입학 이후 실제로 나타나는
**학업 수행 및 변화 정보를 특히 중요하게 활용한 것**으로 해석할 수 있다.

---

## 10. 최종 모델 선정 이유

Baseline Random Forest는 높은 Accuracy와 Precision을 보였지만
Recall이 상대적으로 낮았다.

하이퍼파라미터 튜닝 및 클래스 불균형 보정 후 Recall이
0.7719에서 0.8386으로 개선되었다.

이후 Threshold를 0.55로 조정하여 Precision과 Recall의 균형을 맞추었다.

최종 Test 결과는 다음과 같다.

- Accuracy: **0.8915**
- Precision: **0.8456**
- Recall: **0.8099**
- F1-score: **0.8273**
- ROC-AUC: **0.9349**

따라서 중도이탈 학생 탐지 능력과 전체적인 분류 성능의 균형을 고려하여
**Tuned Random Forest + Threshold 0.55**를 최종 모델로 선정하였다.

---

## 11. 모델 활용 방향

Feature Importance 분석에서 가장 눈에 띄는 결과는
**학업 관련 Feature가 Top 10의 대부분을 차지했다는 점**이다.

특히 1·2학기 이수율, 이수 과목 수, 평균 성적 및 성적 변화와 같은
학생의 실제 학업 진행 상황이 높은 중요도를 보였다.

이를 실제 대학의 학생 지원 시스템과 연결한다면,
학기별 학업 데이터를 지속적으로 확인하여 학업 수행 수준이 변화하는
학생을 조기에 파악하는 방식으로 활용할 수 있다.

또한 재정 위험도와 등록금 납부 상태 역시 Top 10에 포함되었으므로
학업 문제와 재정 문제를 함께 고려한 지원 체계가 필요할 수 있다.

예를 들어 위험 학생에게 단순히 '중도이탈 위험'이라는 결과만 제공하기보다

- 학업 위험 → 학습 상담 및 튜터링
- 재정 위험 → 장학금·재정지원 안내
- 복합 위험 → 학생 상담 및 맞춤형 지원

등으로 연결할 수 있다.

단, Feature Importance는 예측 모델에서의 중요도를 나타내는 것이며
각 변수가 실제 중도이탈의 직접적인 원인임을 증명하는 것은 아니다.

---

## 12. 저장 산출물

| 파일 | 내용 |
|---|---|
| `models/random_forest.joblib` | 최종 Random Forest 모델 |
| `reports/random_forest_importance.csv` | Feature Importance Top 10 |
| `reports/random_forest_importance_top10.png` | Feature Importance 시각화 |
| `reports/model_results.csv` | 모델 성능 비교 결과 |