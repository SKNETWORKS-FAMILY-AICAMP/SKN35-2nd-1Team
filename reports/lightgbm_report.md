  # LightGBM 모델링 결과 리포트

- 작성자: 조현주
- 작성일: 2026-08-28
- 노트북: `notebooks/modeling_lightgbm.ipynb`
- 관련 파일: `models/lightgbm.joblib`, `reports/lightgbm_importance.csv`, `reports/3) model_results.csv`

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
{'subsample': 0.7, 'num_leaves': 50, 'n_estimators': 100,
 'min_child_samples': 20, 'max_depth': 5, 'learning_rate': 0.05,
 'colsample_bytree': 1.0}
```
기본값 대비 트리 깊이(`max_depth`)를 얕게 제한하고, 학습률을 낮추고(0.1→0.05),
데이터 샘플링 비율(`subsample`)을 줄여 과적합을 억제하는 방향으로 조정됨.

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

## 3. 최종 모델 선정 이유

| 후보 | Recall | F1 | 채택 여부 |
|---|---|---|---|
| **튜닝(n_iter=80), threshold=0.5** | 0.8596 | **0.8046** | ✅ 메인 채택 |
| 튜닝(n_iter=80), threshold=0.35 | 0.9018 | 0.7581 | 참고용 보조 옵션 |

- threshold=0.35 옵션은 Recall은 가장 높지만 Precision 손실(0.65)이 커서 메인으로 채택하지 않음
- MLP 모델(Recall 0.8421, F1 0.8040, threshold=0.40)과 비교했을 때도 F1은 거의 동률이나
  Recall은 LightGBM이 근소 우위 → **공정 비교를 위해 threshold=0.5(기본값) 기준으로 최종 채택**
- threshold 조정으로 Recall을 0.90까지 높일 수 있다는 점은 발표 시 보조 설명(트레이드오프 분석)으로 활용 예정

## 4. 어떤 요인이 자퇴에 가장 큰 영향을 미쳤는가 (Feature Importance)

`reports/lightgbm_importance.csv`를 기준으로, 최종 채택 모델이 분기(split)에 가장 많이 사용한
상위 15개 피처는 다음과 같다. (컬럼명의 `num__`, `cat__`, `remainder__`는 전처리 단계
ColumnTransformer가 붙인 접두사이며, 아래 표에서는 가독성을 위해 제거했다.)

| 순위 | 피처 | Importance | 해석 |
|---|---|---|---|
| 1 | sem2_approval_rate (2학기 이수율) | 449 | 압도적 1위. 2학기 학점 이수율이 낮을수록 자퇴 위험 신호 |
| 2 | Age at enrollment (입학 시 나이) | 330 | 늦은 나이에 입학한 학생일수록 자퇴 경향과 연관 |
| 3 | Tuition fees up to date (등록금 납부 여부) | 280 | 등록금 연체 여부 — 재정 상태가 핵심 변수 중 하나 |
| 4 | sem1_approval_rate (1학기 이수율) | 248 | 1학기부터 학업 부진 신호가 나타남 |
| 5 | financial_risk_score (재정 위험 점수, 파생변수) | 241 | 팀이 만든 파생 변수가 실제로 중요하게 작동함 |
| 6 | 2nd sem 성적(grade) | 230 | 2학기 학업 성취도 |
| 7 | Admission grade (입학 성적) | 189 | 입학 당시 학업 역량 |
| 8 | Previous qualification (grade) | 182 | 이전 학력 성적 |
| 9 | 2nd sem 이수 과목 수(approved) | 152 | 2학기에 실제로 통과한 과목 수 |
| 10 | grade_change (성적 변화량, 파생변수) | 139 | 1학기→2학기 성적 하락 폭이 클수록 위험 신호 |
| 11 | 1st sem 수강신청 과목 수(enrolled) | 127 | 1학기 수강 규모 |
| 12 | 아버지 학력 (중등교육 이하) | 125 | 가정 배경 요인 |
| 13 | 2nd sem 평가 응시 횟수(evaluations) | 118 | 2학기 시험/평가 참여도 |
| 14 | 1st sem 성적(grade) | 112 | 1학기 학업 성취도 |
| 15 | Gender (성별) | 100 | 성별에 따른 차이 존재 |

**핵심 요약 — 3가지 축으로 정리 가능:**

1. **학업 이수 관련 (1, 4, 6, 8, 9, 10, 11, 13, 14위)** — 압도적으로 가장 많은 비중을 차지.
   특히 **학기 이수율(approval_rate)**과 **성적 변화량(grade_change)** 같은 팀이 직접 설계한
   파생 변수가 상위권에 포진해, 전처리 단계의 파생변수 설계가 실제로 예측력에 기여했음을 확인
2. **재정 관련 (3, 5위)** — 등록금 납부 여부, 재정 위험 점수 모두 상위 5위 안에 위치.
   학업 문제 다음으로 중요한 자퇴 원인 축
3. **인구통계/배경 (2, 7, 12, 15위)** — 입학 나이, 입학 성적, 부모 학력, 성별 등
   개인 배경 요인도 일정 부분 영향

이 결과는 STEP 8(대응 추천 로직 설계)에서 "학업 이수율 저하 → 학습 상담", "재정 위험 점수 높음 →
장학금/재정 지원 상담" 같은 규칙 기반 추천의 근거로 바로 활용할 수 있다.

![상위 15개 피처 중요도](lightgbm_importance_top15.png)

## 5. 저장 산출물

| 파일 | 내용 |
|---|---|
| `models/lightgbm.joblib` | 최종 채택 모델 (n_iter=80 튜닝 결과) |
| `reports/lightgbm_importance.csv` | Feature Importance (원인 분석용) |
| `reports/lightgbm_importance_top15.png` | 상위 15개 피처 중요도 시각화 (본 리포트에 삽입) |
| `reports/3) model_results.csv` | 팀 전체 모델 비교표에 기록 (model, team_member, threshold, recall, f1) |