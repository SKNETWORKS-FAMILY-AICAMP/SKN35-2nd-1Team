# 최종 모델 선정 결과 보고서

- 작성자: 조현주 (PM)
- 관련 파일: `reports/3) model_results.csv`, `models/best_model.joblib`, `reports/4) lightgbm_report.md`

---

## 1. 배경 및 목적

각 팀원이 개별적으로 모델링(LightGBM, MLP, Logistic Regression, Random Forest, XGBoost)을
진행하면서 recall을 높이기 위해 각자 다른 threshold를 적용했다.

| model | team_member | threshold | recall | f1 |
|---|---|---|---|---|
| LightGBM | 조현주 | 0.50 | 0.8596 | 0.8046 |
| MLP | 조현주 | 0.40 | 0.8421 | 0.8040 |
| Logistic Regression | 고은하 | 0.40 | 0.8134 | 0.8091 |
| Random Forest | 고은하 | 0.55 | 0.8099 | 0.8273 |
| XGBoost | 정은미 | 0.59 | 0.8000 | 0.8000 |

threshold를 낮출수록 recall은 오르고(또는 유지), 올릴수록 recall은 내려가는(또는 유지) 단조적 특성이
있으므로, 위 표만으로는 **"모델 자체의 성능 차이"인지 "threshold 설정의 차이"인지 구분할 수 없었다.**
이에 따라 최종 모델 선정 전, **공통 threshold(0.5) 기준으로 재검증**을 실시했다.

---

## 2. 공통 threshold(0.5) 기준 재검증

| model | 원래 threshold | **recall@0.5** | **f1@0.5** |
|---|---|---|---|
| **LightGBM** | 0.50 (원래도 0.5) | **0.8596** | 0.8046 |
| Random Forest | 0.55 | 0.8386 | **0.8115** |

공통 기준에서도 LightGBM의 recall이 가장 높음을 확인.

---

## 3. 선정 기준 및 최종 결론

팀 원칙: **recall을 F1보다 우선하는 지표로 채택** — 실제 자퇴 위험 학생을 놓치는 오류(False Negative)가
오탐지보다 운영상 비용이 훨씬 크다고 판단했기 때문.

### ✅ 최종 채택 모델: **LightGBM (threshold=0.5)**

- **Val** Recall: 0.8596 / F1: 0.8046
- 담당: 조현주

**채택 사유:** 모든 모델을 공통 threshold(0.5) 기준으로 재비교했을 때도 recall이 가장 높았으며,
팀이 사전에 합의한 "recall 우선" 원칙에 부합함.

**최종 채택 하이퍼파라미터** (n_iter=80, scoring="recall" 탐색 결과):
```python
{'n_estimators': 300, 'num_leaves': 15, 'learning_rate': 0.01,
 'subsample': 0.8, 'colsample_bytree': 0.8, 'max_depth': -1,
 'min_child_samples': 20, 'class_weight': 'balanced', 'random_state': 42}
```

---

## 4. Test 성능 확인

| 구분 | Recall | F1 |
|---|---|---|
| Val | 0.8596 | 0.8046 |
| **Test (최종 확정)** | **0.8380** | **0.8165** |

```
              precision    recall  f1-score   support
           0       0.92      0.90      0.91       601
           1       0.80      0.84      0.82       284

    accuracy                           0.88       885
   macro avg       0.86      0.87      0.86       885
weighted avg       0.88      0.88      0.88       885
```

- 자퇴(class 1) Precision이 val(0.76)보다 test(0.80)에서 더 높게 나와, 위험군 예측의
  신뢰도가 test에서도 안정적으로 유지됨을 확인

> 상세 classification report 및 검증 이력은 `reports/4) lightgbm_report.md` 참고

---

## 5. Feature Importance 최종 확인

상세 top10 표와 해석은 `reports/4) lightgbm_report.mdd` 4절 참고.
