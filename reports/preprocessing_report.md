# 데이터 전처리 결과서: 대학생 중도탈락(Dropout) 예측

- **원본 데이터**: `data/raw/data.csv` (UCI Predict Students' Dropout and Academic Success, 4,424행 × 37열)
- **전처리 코드**: [`notebooks/preprocess.ipynb`](../notebooks/preprocess.ipynb)
- **관련 분석**: [`reports/eda_report.md`](eda_report.md) — 파생변수 설계 근거는 이 문서 참고

---

### 1. Target 정의

| 값 | 의미 | 원본 매핑 |
|---|---|---|
| 1 | Dropout | `Target == 'Dropout'` |
| 0 | Non-Dropout | `Target == 'Graduate'` 또는 `'Enrolled'` |

3-class(Dropout/Enrolled/Graduate) 원본을 이진분류로 단순화. 전체 데이터 기준 클래스 비율은 **Non-Dropout 67.9% : Dropout 32.1%**(약 2:1)로, 심각하지 않지만 모델링 시 `class_weight` 또는 threshold 조정 고려 필요.

---

### 2. 파생변수 (5개)

EDA에서 확인된 인사이트를 근거로 생성 (자세한 근거는 `eda_report.md` 참고).

| 변수명 | 계산 방법 | Target과의 상관계수 |
|---|---|---|
| `sem1_approval_rate` | 1학기 (합격과목 / 등록과목), 등록 0인 경우 0 처리 | -0.591 |
| `sem2_approval_rate` | 2학기 (합격과목 / 등록과목), 등록 0인 경우 0 처리 | **-0.659** (전체 변수 중 최강) |
| `financial_risk_score` | (등록금미납 + 채무자 + 무장학금) 합산, 0~3점 | +0.435 |
| `grade_change` | 2학기 평점 − 1학기 평점 | -0.225 |
| `zero_enrolled_1st_sem` | 1학기 등록과목 수가 0이면 1, 아니면 0 | +0.047 (약하지만 실제 이탈률 차이는 11%p로 유지 판단) |

---

### 3. 컬럼 분류 및 처리 방법

인코딩/스케일링 방법이 컬럼 성격마다 다르므로 아래 4종으로 분류 후 처리

| 분류 | 개수 | 컬럼 | 처리 방법 |
|---|---|---|---|
| 이진(0/1) | 8 | Displaced, Educational special needs, Debtor, Tuition fees up to date, Gender, Scholarship holder, International, Daytime/evening attendance | 그대로 통과 (passthrough) |
| 파생 플래그 | 2 | zero_enrolled_1st_sem, financial_risk_score | 그대로 통과 (passthrough) |
| 미분류(누락) | 1 | Application order | 4종 분류에서 누락되어 `remainder`로 자동 통과됨 — 스케일링 안 된 원본 정수(1~9)값 그대로 존재. 의도적 설계는 아니었으나 값 자체는 유효하므로 우선 유지, 필요시 모델링 단계에서 재검토 권장 |
| 저카디널리티 범주형 | 4 | Marital status, Application mode, Course, Previous qualification | 원-핫 인코딩 |
| 고카디널리티 범주형 | 5 | Mother's/Father's qualification, Mother's/Father's occupation, Nacionality | 희소 카테고리 그룹화(&lt;1%→'Other') 후 원-핫 인코딩 |
| 연속형 | 11 | Previous qualification (grade), Admission grade, Age at enrollment, 1·2학기 평점, Unemployment/Inflation rate, GDP, sem1/2_approval_rate, grade_change | 표준화 (StandardScaler) |
| 카운트형 | 10 | 1·2학기 credited/enrolled/evaluations/approved/without evaluations | 표준화 (StandardScaler) |

**원본 40개 컬럼 → 인코딩 후 132개 피처**로 확장됨 (연속형/카운트형 21 + 원-핫 인코딩 100 + 통과 11).

---

### 4. 데이터 누수(Data Leakage) 방지 조치

전처리 전 과정에서 아래 원칙을 지킴:

1. **Train/Val/Test 분할을 인코딩·스케일링 이전에 먼저 수행**
    * 나중 단계에서 계산되는 통계(평균, 카테고리 빈도 등)에 Val/Test 정보가 섞이지 않도록 함
2. **희소 카테고리 그룹화 기준을 X_train만으로 계산**
    * 고카디널리티 컬럼(부모 학력/직업 등)의 "어떤 카테고리가 희소한지" 판단을 Train 데이터만 보고 결정한 뒤, 동일한 규칙을 Val/Test에도 적용
3. **StandardScaler/OneHotEncoder를 Train에만 `fit`**
    * Val/Test는 `transform`만 적용

---

### 5. Train/Val/Test 분할

60:20:20, 층화추출(stratify), `random_state=42`

| 데이터셋 | 행 수 | 열 수 (132 피처 + target) | Dropout 비율 |
|---|---|---|---|
| train | 2,654 | 133 | 32.1% |
| val | 885 | 133 | 32.2% |
| test | 885 | 133 | 32.1% |

원본 전체 비율(32.1%)이 세 데이터셋 모두 거의 동일하게 유지됨 — 층화추출 정상 작동 확인.

---

### 6. 최종 산출물

| 파일 | 설명 |
|---|---|
| `data/processed/train.csv` | 학습용 데이터 (2,654행 × 133열, `target` 컬럼 포함) |
| `data/processed/val.csv` | 검증용 데이터 (885행 × 133열) |
| `data/processed/test.csv` | 평가용 데이터 (885행 × 133열) |
| `models/preprocessor.joblib` | 학습된 전처리 파이프라인 (ColumnTransformer) |


### 컬럼명 규칙 (모델링 시 참고)
전처리된 CSV의 컬럼명에는 `ColumnTransformer`가 자동으로 붙인 접두사가 있음:
- `num__` — 총 21개
    * 표준화된 연속형/카운트형 컬럼 (예: `num__Curricular units 2nd sem (grade)`) 
- `cat__` — 총 100개
    * 원-핫 인코딩된 범주형 컬럼 (예: `cat__Marital status_1`, `cat__Marital status_2`...) 
- `remainder__` — 총 11개
    * 그대로 통과된 이진/플래그/미분류 컬럼 (예: `remainder__Debtor`, `remainder__Application order`)
- `target`
    * 정답 라벨 (1=Dropout, 0=Non-Dropout)

### `preprocessor.joblib` 재사용 방법
새로운 원본 형식 데이터(전처리 전)를 동일하게 변환할 때 사용함.  
**반드시 `transform`만 사용하고 `fit`은 다시 하지 않아야 한다** (Train에서 학습된 규칙을 그대로 적용해야 하기 때문)
```python
import joblib
preprocessor = joblib.load('models/preprocessor.joblib')
X_new_processed = preprocessor.transform(X_new)  # fit_transform 아님, transform만
```

---

### 7. 모델링 팀 참고사항

1. **클래스 불균형(32:68)**
    * `class_weight='balanced'` 옵션 사용 또는 예측 임계값(threshold) 튜닝 권장. 
    * Train 데이터에 SMOTE 등 오버샘플링을 적용하려면 반드시 Train에만 적용하고 Val/Test는 원본 비율 그대로 유지할 것.
2. **`zero_enrolled_1st_sem`**
    * 상관계수는 낮지만(0.047) 실제 이탈률 차이(31.7% vs 42.8%)는 뚜렷함
    * 트리 기반 모델(Random Forest, XGBoost, LightGBM)에서 유의미한 분기 신호가 될 수 있으니 성급하게 제외하지 말 것.
3. **가장 강력한 단일 피처**
    * `sem2_approval_rate`(2학기 승인율), 그다음으로 `financial_risk_score`(재정 위험 점수)
    * 두 계열을 중심으로 모델링 방향을 잡는 것을 추천
