# 최종 모델 선정 결과 보고서

- 작성자: 조현주 (PM)
- 작성일: 2026-08-28 (2026-08-29 갱신: test 성능 반영)
- 관련 파일: `reports/3) model_results.csv`, `models/best_model.joblib`, `reports/model_metrics.json`(예정)
- 결정 방식: 8/28 전체 팀 회의 (STEP 7)

---

## 1. 배경 및 목적

각 팀원이 개별적으로 모델링(LightGBM, MLP, Logistic Regression, Random Forest, XGBoost)을
진행하면서 recall을 높이기 위해 각자 다른 threshold를 적용했다. 그 결과 `model_results.csv`에
기록된 1차 비교표는 **모델 간 threshold가 서로 달라 공정한 비교가 아니었다.**

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
| XGBoost | 0.59 | 0.8000 | 0.8000 |

공통 기준에서도 LightGBM의 recall이 가장 높음을 확인. Random Forest는 F1 기준으로는 가장 높으나
recall은 LightGBM보다 낮음.

---

## 3. 선정 기준 및 최종 결론

팀 원칙: **recall을 F1보다 우선하는 지표로 채택** — 실제 자퇴 위험 학생을 놓치는 오류(False Negative)가
오탐지보다 운영상 비용이 훨씬 크다고 판단했기 때문.

### ✅ 최종 채택 모델: **LightGBM (threshold=0.5)**

- **Val** Recall: 0.8596 / F1: 0.8046
- 담당: 조현주

**채택 사유:** 모든 모델을 공통 threshold(0.5) 기준으로 재비교했을 때도 recall이 가장 높았으며,
팀이 사전에 합의한 "recall 우선" 원칙에 부합함.

---

## 4. Test 성능 확인 (2026-08-29, 최초이자 유일 평가)

팀 규칙에 따라 test set은 8/28 최종 모델 확정 이후 **딱 한 번만** 사용했다.

| 구분 | Recall | F1 |
|---|---|---|
| Val | 0.8596 | 0.8046 |
| **Test** | **0.8345** | **0.8215** |

- Val 대비 Recall은 소폭 하락(-0.025), F1은 오히려 소폭 상승(+0.017)
- 두 지표가 반대 방향으로 미세하게 움직인 정도로, **과적합 신호로 보기 어려우며 정상적인
  표본 변동 범위**로 판단
- 자퇴(class 1) Precision이 val(0.76)보다 test(0.81)에서 더 높게 나와, 위험군 예측의
  신뢰도가 test에서도 안정적으로 유지됨을 확인

> 상세 classification report는 `reports/lightgbm_report.md` 2절 참고

---

## 5. 참고 — 채택하지 않은 옵션들

| 후보 | 특이사항 | 미채택 사유 |
|---|---|---|
| LightGBM, threshold=0.35 | Recall 0.9018까지 상승 가능 | Precision 0.65로 하락(오탐 35%) — 보조 참고용으로만 발표에 활용 |
| Random Forest | F1 0.8115로 val 기준 최고 | recall이 LightGBM보다 낮아 팀 원칙상 후순위 |
| XGBoost | 공통 기준에서도 recall/f1 모두 최저 | 성능상 채택 어려움 |
| MLP | Recall 0.8421 (threshold=0.40) | LightGBM 대비 recall 낮음 |
| Logistic Regression | 해석력(계수 방향)은 우수 | 예측 성능 자체는 상대적으로 낮음. 단, 원인 설명(cause) 문구 작성 시 방향성 근거로 활용 예정 |
