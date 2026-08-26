# 데이터 전처리 결과서 — Model B (범주 일반화)

- **원본 데이터**: `data/raw/data.csv` (UCI Predict Students' Dropout and Academic Success, 4,424행 × 37열)
- **전처리 코드**: [`notebooks/preprocess.ipynb`](../notebooks/preprocess.ipynb)
- **기준 문서**: `model_b_preprocessing_guide.html` (팀 공유 가이드)
- **관련 분석**: [`reports/eda_report.md`](eda_report.md)

> Model A(원본 구조 최대한 유지) 대비, 포르투갈 제도에 종속된 세부 범주와 지나치게 세분화된 값을 보편적으로 이해 가능한 상위 개념으로 일반화한 버전. 한국형으로 바꾸는 것이 아니라 **분석·해석을 쉽게 하기 위한 재분류**임.

---

## 1. Target 정의

| 값 | 의미 | 원본 매핑 |
|---|---|---|
| 1 | Dropout | `Target == 'Dropout'` |
| 0 | Non-Dropout | `Target == 'Graduate'` 또는 `'Enrolled'` |

전체 데이터 기준 클래스 비율 **Non-Dropout 67.9% : Dropout 32.1%**.

## 2. 범주 일반화 매핑

### 2-1. Application mode → Admission_pathway (입학전형 유형)

18종 → 8개 그룹. 매핑 후 NaN 0건(누락 코드 없음) 확인.

| 그룹 | 원본 코드 | 인원 |
|---|---|---|
| 일반전형 | 1, 17, 18 | 2,704 |
| 성인학습자 전형 | 39 | 785 |
| 편입·전과 | 42, 43, 51, 57 | 449 |
| 직업·기술교육 연계전형 | 44, 53 | 248 |
| 고등교육 이수자 전형 | 7 | 139 |
| 특별전형(지역/도서) | 5, 16 | 54 |
| 외국인·국제학생 전형 | 15 | 30 |
| 기타·특수전형 | 2, 10, 26, 27 | 15 |

### 2-2. Course → Major_field (전공계열)

17개 개별 학과 → 10개 전공계열. 매핑 후 NaN 0건 확인.

| 전공계열 | 인원 |
|---|---|
| 보건 | 1,189 |
| 경영 | 916 |
| 사회 | 570 |
| 예술·디자인 | 441 |
| 자연·농생명 | 351 |
| 인문·사회 | 331 |
| 경영·서비스 | 252 |
| 교육 | 192 |
| 공학·IT | 170 |
| 공학·자연 | 12 |

> ⚠️ 한국 대학 공식 학과분류가 아니라 분석용 재분류임을 발표 시 명시할 것.

### 2-3. Previous qualification → Previous_education_level (이전 학력 수준)

17종 → 6단계. 매핑 후 NaN 0건 확인.

| 수준 | 인원 |
|---|---|
| Secondary | 3,717 |
| Vocational | 255 |
| Below secondary | 232 |
| Bachelor | 189 |
| Higher education experience | 16 |
| Graduate | 15 |

### 2-4. 부모 학력 → Mother/Father_education_level (교육 수준)

"중등교육 이하 → 고등학교 → 전문·직업교육 → 대학 → 대학원 → 미상·기타" 6단계로 통합. 매핑 후 NaN 0건 확인 (모/부 각각).

| 수준 | 모(어머니) | 부(아버지) |
|---|---|---|
| 중등교육 이하 | 2,590 | 2,949 |
| 고등학교 | 1,069 | 906 |
| 대학 | 534 | 357 |
| 미상·기타 | 136 | 122 |
| 대학원 | 81 | 62 |
| 전문·직업교육 | 14 | 28 |

### 2-5. 부모 직업 → Mother/Father_occupation_group (직업군)

가이드 권고대로 원본 코드별 빈도를 먼저 확인한 뒤 5개 직업군으로 통합. 매핑 후 NaN 0건 확인 (모/부 각각).

| 직업군 | 모(어머니) | 부(아버지) |
|---|---|---|
| 기술·생산 | 1,933 | 2,034 |
| 사무·서비스 | 1,371 | 920 |
| 전문·관리직 | 793 | 1,004 |
| 무직·기타 | 231 | 212 |
| 농림 | 96 | 254 |

## 3. Nacionality → 제거 (International과 중복)

**검증 결과**: `Nacionality != 1(Portuguese)`이면서 `International == 0`인 경우 **0건** — 두 변수가 사실상 동일한 정보(국제학생 여부)를 담고 있음을 확인. 국적 전체의 97.5%가 포르투갈로 극단적으로 편중되어 있어 원-핫 인코딩 시 정보 가치도 낮음. → **Nacionality 제거, International만 유지.**

## 4. 거시경제 변수 3개 제거

`Unemployment rate`, `Inflation rate`, `GDP`는 학생 개인 특성이 아니라 특정 시점의 포르투갈 경제상황을 나타내는 변수로, **국가·시점 의존성이 높은 변수이므로 일반화 전처리 모델에서는 제외**하였다. (EDA에서도 세 변수 모두 Target과의 상관계수 0.05 미만으로 확인됨)

## 5. 파생변수 (Model A와 동일하게 유지, 5개)

범주 일반화와 무관하게 EDA에서 검증된 예측력이 높은 파생변수는 그대로 유지.

| 변수명 | 계산 방법 | Target과의 상관계수(Model A 기준) |
|---|---|---|
| `sem1_approval_rate` | 1학기 (합격과목 / 등록과목) | -0.591 |
| `sem2_approval_rate` | 2학기 (합격과목 / 등록과목) | -0.659 |
| `financial_risk_score` | (등록금미납+채무자+무장학금) 합산, 0~3점 | +0.435 |
| `grade_change` | 2학기 평점 − 1학기 평점 | -0.225 |
| `zero_enrolled_1st_sem` | 1학기 등록과목 수 0 여부 | +0.047 |

## 6. 전처리 전후 검증

| 항목 | 전 | 후 |
|---|---|---|
| 행(row) 수 | 4,424 | 4,424 (동일 — 원칙 준수) |
| 결측치 | 0 | 0 |
| 원본 컬럼(Target 포함) | 37 | — |
| 일반화·파생 반영 후 컬럼 | — | 38 |

## 7. 컬럼 분류 및 처리 방법

Model B는 모든 범주형 컬럼이 이미 저카디널리티(5~10종)로 일반화되어 있어, **Model A에서 필요했던 "희소 카테고리 그룹화" 단계가 불필요**함 — 일반화 자체가 그 역할을 겸함.

| 분류 | 개수 | 컬럼 | 처리 방법 |
|---|---|---|---|
| 이진(0/1) | 8 | Displaced, Educational special needs, Debtor, Tuition fees up to date, Gender, Scholarship holder, International, Daytime/evening attendance | 그대로 통과 |
| 파생 플래그 | 2 | zero_enrolled_1st_sem, financial_risk_score | 그대로 통과 |
| 저카디널리티 범주형 | 8 | Marital status, Admission_pathway, Major_field, Previous_education_level, Mother/Father_education_level, Mother/Father_occupation_group | 원-핫 인코딩 |
| 연속형 | 9 | Previous qualification (grade), Admission grade, Age at enrollment, 1·2학기 평점, **Application order**, sem1/2_approval_rate, grade_change | 표준화 |
| 카운트형 | 10 | 1·2학기 credited/enrolled/evaluations/approved/without evaluations | 표준화 |

> Model A에서 분류 누락됐던 `Application order`(지원 순위, 0~9)도 이번에 연속형으로 정식 편입.

**인코딩 전 37개 피처 → 인코딩 후 81개 피처**로 확장 (Model A의 132개 대비 **약 39% 감소**, 목표했던 "단순화" 효과 확인).

## 8. Train/Val/Test 분할

60:20:20, 층화추출, `random_state=42`

| 데이터셋 | 행 수 | 열 수 (81 피처 + target) | Dropout 비율 |
|---|---|---|---|
| train | 2,654 | 82 | 32.1% |
| val | 885 | 82 | 32.2% |
| test | 885 | 82 | 32.1% |

## 9. 데이터 누수 방지 조치

1. Train/Val/Test 분할을 인코딩·스케일링 이전에 수행
2. StandardScaler/OneHotEncoder를 Train에만 `fit`, Val/Test는 `transform`만 적용
3. 범주 일반화 매핑(Application mode→Admission_pathway 등)은 값 자체의 고정된 정의(도메인 지식)에 기반한 것이라 Train/Test 분할과 무관하게 전체에 동일 적용 — 데이터 통계에 의존하지 않으므로 누수 위험 없음

## 10. 최종 산출물

| 파일 | 설명 |
|---|---|
| `data/processed/train.csv` | 학습용 데이터 (2,654행 × 82열) |
| `data/processed/val.csv` | 검증용 데이터 (885행 × 82열) |
| `data/processed/test.csv` | 평가용 데이터 (885행 × 82열) |
| `models/preprocessor.joblib` | 학습된 전처리 파이프라인 |
| `data/processed/feature_schema.json` | 컬럼 분류·제거 목록 메타데이터 |

### `preprocessor.joblib` 재사용 방법
```python
import joblib
preprocessor = joblib.load('models/preprocessor.joblib')
X_new_processed = preprocessor.transform(X_new)  # fit_transform 아님, transform만
```
단, 새 데이터에도 `Admission_pathway`, `Major_field` 등 일반화 컬럼을 **동일한 매핑 딕셔너리로 먼저 생성**해야 함 (전처리기 자체는 일반화 매핑을 포함하지 않음, `preprocess.ipynb`의 매핑 딕셔너리 참고).

## 11. 모델링 팀 참고사항

1. **클래스 불균형(32:68)**: `class_weight='balanced'` 또는 threshold 튜닝 권장.
(2. **Model A와의 성능 비교 권장**: 동일 데이터를 두 가지 방식(원본 구조 유지 vs 범주 일반화)으로 전처리했으므로, 두 버전으로 각각 모델을 학습해 성능·해석력을 비교하는 실험 설계?)
3. **핵심 피처**: `sem2_approval_rate`, `financial_risk_score` 계열은 Model B에서도 동일하게 가장 강력한 신호.
4. **Major_field '공학·자연'**: 표본이 12건뿐으로 매우 적음 — 학습/평가 시 이 카테고리의 예측 안정성에 유의.
