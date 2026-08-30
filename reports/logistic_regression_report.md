# Logistic Regression 모델링 결과 리포트

- 작성자: 고은하
- 작성일: 2026-08-28
- 노트북: `notebooks/modeling_logistic_regression.ipynb`
- 모델: `models/logistic_regression.joblib`
- 결과: `reports/model_results.csv`

---

## 1. 모델 개요

대학생 중도이탈(Dropout) 여부를 예측하기 위해 Logistic Regression을 적용하였다.

Target은 다음과 같이 이진 분류로 구성하였다.

- `1`: Dropout
- `0`: Non-Dropout (Graduate + Enrolled)

학습 데이터는 2,654명이며 총 81개의 Feature를 사용하였다.

Target 분포는 다음과 같다.

- Non-Dropout(0): 1,802명 (67.9%)
- Dropout(1): 852명 (32.1%)

따라서 클래스 간 불균형이 존재하며, 단순 Accuracy뿐만 아니라
Precision, Recall, F1-score, ROC-AUC를 함께 평가하였다.

특히 본 프로젝트는 중도이탈 위험 학생을 조기에 발견하는 것이 목적이므로,
실제 중도이탈 학생을 얼마나 잘 탐지하는지를 나타내는 Recall을 중요하게 고려하였다.

---

## 2. 모델 학습 및 성능 개선

### 2-1. Baseline Logistic Regression

먼저 기본 Logistic Regression 모델을 학습하였다.

Validation 결과는 다음과 같다.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Baseline | 0.8859 | 0.8651 | 0.7649 | 0.8119 | 0.9243 |

Accuracy와 Precision은 높은 수준이었으나 Recall은 0.7649로 나타났다.

즉, 전체적인 예측 정확도는 높지만 실제 중도이탈 학생 중 일부를
놓칠 가능성이 존재하였다.

---

### 2-2. Class Weight 조정

데이터에서 Non-Dropout 학생이 Dropout 학생보다 많기 때문에
`class_weight="balanced"`를 적용하여 클래스 불균형을 보정하였다.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Baseline | 0.8859 | 0.8651 | 0.7649 | 0.8119 | 0.9243 |
| Balanced | 0.8576 | 0.7477 | 0.8421 | 0.7921 | 0.9237 |

Balanced 모델에서는 Recall이

`0.7649 → 0.8421`

로 크게 상승하였다.

이는 실제 중도이탈 학생을 더 많이 찾아낼 수 있다는 의미이다.

반면 Precision이 0.8651 → 0.7477로 감소하여,
중도이탈하지 않을 학생을 위험군으로 판단하는 경우가 증가하였다.

따라서 Recall만 높이는 것보다 Precision과 Recall의 균형을
맞추기 위한 추가적인 Threshold 조정을 진행하였다.

---

## 3. Threshold 조정

Logistic Regression의 기본 분류 기준은 0.50이다.

본 프로젝트에서는 중도이탈 학생을 조금 더 적극적으로 탐지하기 위해
Threshold를 낮추면서 성능 변화를 비교하였다.

| Threshold | Accuracy | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|
| 0.50 | 0.8859 | 0.8651 | 0.7649 | 0.8119 |
| 0.45 | 0.8814 | 0.8383 | 0.7825 | 0.8094 |
| 0.40 | 0.8791 | 0.8134 | 0.8134 | 0.8134 |

Threshold를 낮추면서 Precision은 일부 감소했지만,
Recall은 상승하는 경향을 보였다.

Threshold=0.40에서는 Precision과 Recall이 약 0.81 수준으로
균형을 이루었다.

따라서 중도이탈 학생 탐지와 오탐 사이의 균형을 고려하여
최종 Threshold를 **0.40**으로 선정하였다.

---

## 4. 최종 Test 평가

Validation 데이터에서 결정한 Threshold=0.40을
최종 Test 데이터에 적용하였다.

| Metric | Test Result |
|---|---:|
| Accuracy | **0.8768** |
| Precision | **0.8049** |
| Recall | **0.8134** |
| F1-score | **0.8091** |
| ROC-AUC | **0.9333** |
| Threshold | **0.40** |

최종 Test 데이터에서도 ROC-AUC 0.9333을 기록하여
Dropout과 Non-Dropout 학생을 구분하는 능력이 안정적으로 유지되었다.

Recall은 0.8134로, 실제 중도이탈 학생을 약 81% 수준으로
탐지하였다.

Precision 역시 0.8049로 나타나 중도이탈 탐지 능력을 높이면서도
과도한 오탐을 어느 정도 억제하였다.

---

## 5. Feature Importance 분석

Logistic Regression은 Random Forest나 LightGBM과 달리
`feature_importances_`를 직접 제공하지 않는다.

따라서 각 Feature의 **Coefficient(회귀계수)**를 이용하여
변수의 영향력을 분석하였다.

쉽게 설명하면:

- Coefficient가 `+` → Dropout 방향으로 작용
- Coefficient가 `-` → Non-Dropout 방향으로 작용
- Coefficient의 절댓값이 클수록 → 모델의 판단에 더 크게 작용

Feature Importance 순위는 Coefficient의 절댓값을 기준으로 산출하였다.

> 주의: Feature Importance는 모델의 예측에 얼마나 크게 활용되었는지를
> 나타내며, 해당 변수가 실제 중도이탈의 직접적인 원인이라는 의미는 아니다.

---

## 6. Feature Importance Top 10

| 순위 | Feature | Coefficient | Importance | 방향 |
|---:|---|---:|---:|---|
| 1 | Tuition fees up to date | -1.4623 | **1.4623** | Dropout ↓ |
| 2 | Curricular units 1st sem (approved) | -1.0764 | **1.0764** | Dropout ↓ |
| 3 | Curricular units 2nd sem (approved) | -1.0267 | **1.0267** | Dropout ↓ |
| 4 | Admission pathway - 외국인·국제학생 전형 | -1.0165 | **1.0165** | Dropout ↓ |
| 5 | Major field - 교육 | +1.0001 | **1.0001** | Dropout ↑ |
| 6 | Major field - 사회 | -0.9203 | **0.9203** | Dropout ↓ |
| 7 | Father occupation group - 농림 | -0.8975 | **0.8975** | Dropout ↓ |
| 8 | financial_risk_score | +0.7663 | **0.7663** | Dropout ↑ |
| 9 | Educational special needs | +0.7582 | **0.7582** | Dropout ↑ |
| 10 | Admission pathway - 직업·기술교육 연계전형 | -0.7170 | **0.7170** | Dropout ↓ |

---

## 7. 주요 Feature 해석

### 7-1. 등록금 납부 여부

가장 높은 Importance를 보인 변수는
`Tuition fees up to date`였다.

- Coefficient: **-1.4623**
- Importance: **1.4623**

계수가 음수이므로 등록금을 정상적으로 납부한 경우
모델은 중도이탈 가능성이 낮아지는 방향으로 판단하였다.

Logistic Regression에서 가장 강하게 작용한 변수라는 점에서
학생의 재정 및 등록 상태가 중도이탈 예측에 중요한 신호로
활용되었음을 확인할 수 있다.

---

### 7-2. 1·2학기 이수 과목 수

다음으로 높은 중요도를 보인 변수는

- `Curricular units 1st sem (approved)`
- `Curricular units 2nd sem (approved)`

였다.

두 변수 모두 Coefficient가 음수로 나타났다.

즉, 이수한 과목 수가 많을수록 모델은 중도이탈 가능성이
낮아지는 방향으로 판단하였다.

이는 학생의 실제 학업 진행 상황과 관련된 변수가
중도이탈 예측에서 중요한 신호로 활용되고 있음을 보여준다.

---

### 7-3. 재정 위험 점수

`financial_risk_score`는 Importance 0.7663으로
전체 Feature 중 8위를 기록하였다.

Coefficient는 **+0.7663**으로 양수였다.

따라서 재정 위험 점수가 증가할수록 모델은 해당 학생을
Dropout 방향으로 판단하는 경향을 보였다.

등록금 납부 여부가 1위 변수로 나타난 결과와 함께 고려하면,
재정 관련 정보가 Logistic Regression의 중도이탈 예측에서
중요하게 활용되고 있음을 확인할 수 있다.

---

### 7-4. 기타 변수

입학전형, 전공 분야, 부모 직업군, 특수교육 필요 여부와 같은
범주형 변수도 Top 10에 포함되었다.

다만 이러한 변수들은 특정 집단의 특성과 중도이탈 사이의
인과관계를 의미하는 것은 아니다.

특히 One-Hot Encoding된 범주형 Feature의 coefficient는
기준 범주 및 다른 변수들과의 관계에 따라 달라질 수 있으므로
해석에 주의할 필요가 있다.

따라서 이러한 변수는 학생 개인을 단정적으로 판단하는 근거가 아니라
추가적인 지원 필요성을 검토하기 위한 보조적인 예측 신호로
활용하는 것이 적절하다.

---

## 8. 최종 모델 선정 이유

기본 Logistic Regression은 Accuracy와 Precision이 높았지만
Recall이 상대적으로 낮아 실제 중도이탈 학생을 놓칠 가능성이 있었다.

Class Weight를 적용한 모델은 Recall을 크게 개선했지만
Precision 감소가 나타났다.

이에 따라 기본 모델의 Threshold를 조정하여 Precision과 Recall의
균형을 비교하였다.

최종적으로 Threshold=0.40에서 Precision과 Recall의 균형이
안정적으로 나타났으며, Test 데이터에서도 다음 성능을 기록하였다.

- Accuracy: **0.8768**
- Precision: **0.8049**
- Recall: **0.8134**
- F1-score: **0.8091**
- ROC-AUC: **0.9333**

따라서 본 프로젝트에서는 중도이탈 위험 학생을 놓치지 않는 것과
과도한 오탐을 줄이는 것 사이의 균형을 고려하여
**Logistic Regression + Threshold 0.40**을 최종 모델로 선정하였다.

---

## 9. 모델 활용 방향

Feature Importance 분석 결과를 종합하면 Logistic Regression은
특히 다음 정보를 중도이탈 예측에 중요하게 활용하였다.

1. 등록금 납부 상태
2. 학기별 이수 과목 수
3. 재정 위험도
4. 입학전형 및 전공 관련 정보
5. 학생의 교육적 지원 필요 정보

특히 등록금 납부 상태와 학업 진행 상황이 높은 중요도를 보였다는 점에서,
실제 대학 시스템에서는 단순히 중도이탈 확률만 제공하기보다
위험 신호의 종류에 따라 학생 지원 방안을 연결하는 방식으로
활용할 수 있다.

예를 들어 학업 진행에 어려움이 있는 학생에게는 학습 상담,
재정 위험이 높은 학생에게는 장학·재정지원 안내 등으로
연계할 수 있다.

단, 본 모델의 결과는 학생의 중도이탈 '원인'을 증명하는 것이 아니라
중도이탈 가능성을 예측하기 위한 통계적 관계를 나타낸다.

---

## 10. 저장 산출물

| 파일 | 내용 |
|---|---|
| `models/logistic_regression.joblib` | 최종 Logistic Regression 모델 |
| `reports/logistic_regression_importance.csv` | Feature Importance Top 10 |
| `reports/logistic_regression_importance_top10.png` | Feature Importance 시각화 |
| `reports/model_results.csv` | 모델 성능 비교 결과 |
