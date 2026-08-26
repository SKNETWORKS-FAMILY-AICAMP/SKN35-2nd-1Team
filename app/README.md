# app/ — Streamlit 서비스

팀 저장소의 **서비스 구현 담당분**입니다. 전처리·모델링 산출물(`data/`, `models/`, `notebooks/`)을
그대로 받아 쓰고, 이 폴더는 **화면과 예측 계층만** 소유합니다.

```bash
pip install -r requirements.txt      # 저장소 루트의 것
streamlit run app/app.py             # 반드시 저장소 루트에서 실행
```

기본 주소는 http://localhost:8501 입니다.

---

## 1. 화면은 파일 하나씩 나뉘어 있습니다

```
app/
├─ app.py                  # 진입점 — 전역 설정 + st.navigation 라우팅만
├─ views/
│  ├─ 0_home.py            # 시작화면 — 서비스 소개 · 데이터 출처(지구본) · 확장 가능성
│  ├─ 1_dashboard.py       # 전체 현황 — KPI 6종 · 분포 4종 · 우선 확인 명단
│  ├─ 2_prediction.py      # 학생 1명 예측 — 입력 32개 → 위험도 · 위험요인 · 지원 추천
│  └─ 3_students.py        # 학생 목록 — 필터 4종 · 행 선택 시 상세
├─ components/             # 화면 공통 (테마 · UI 조각 · 지구본 · 캐시)
├─ services/               # 예측 계층 (더미 ↔ 실제 모델 교체 지점)
├─ rules/                  # 규칙 기반 지원 추천 엔진
├─ utils/                  # 팀 전처리 스키마 매핑 · 더미 데이터
├─ data/dummy_students.csv # 합성 더미 80명 (원본 데이터 아님)
└─ tests/                  # unittest 66개
```

화면을 하나 고치려면 `views/` 의 파일 **하나만** 열면 됩니다. 서로를 import 하지 않으므로
여러 사람이 동시에 다른 화면을 작업해도 충돌하지 않습니다.

> `st.navigation` 을 쓰는 이유: Streamlit 은 `views/` 폴더를 자동 멀티페이지로 인식해
> 라우팅을 가져가 버립니다. `st.navigation` 으로 라우팅을 직접 잡으면 사이드바 구성과
> 화면 간 값 전달을 통제하면서도 화면별 파일 분리를 그대로 얻습니다.

---

## 2. 현재 상태 — 학습된 모델이 아직 없습니다

`models/` 에는 `preprocessor.joblib` 만 있고 학습된 모델은 없습니다.
지금 화면의 확률·위험요인은 전부 `services/dummy_predictor.py` 의 **규칙 기반 DummyPredictor**
값이며, 모든 화면 상단에 그 사실을 배너로 띄웁니다.

이 프로토타입이 **하지 않는 것**: 모델 학습 · 성능 수치 주장 · 실제 SHAP 분석 표시.

---

## 3. 팀 전처리(Model B)와 맞춰 둔 것

| 항목 | 반영 내용 |
|---|---|
| Target | **이진** (1=Dropout, 0=Non-Dropout) — `feature_schema.json` 정의 그대로 |
| 범주 | `Major_field`(10) · `Admission_pathway`(8) · `Previous_education_level`(6) · 부모 학력(6)/직업군(5) |
| 제거된 컬럼 | `Course` · `Application mode` 등 원본 코드는 **화면에서도 쓰지 않음** |
| 파생변수 5종 | 화면 입력에서 **자동 계산** (아래) |
| 입력 컬럼 순서 | `data/processed/feature_schema.json` 을 **런타임에 읽어** 조립 (하드코딩 없음) |

파생변수는 `utils/feature_mapping.py` 의 `StudentInput` 안에서만 정의합니다.

| 파생변수 | 계산 |
|---|---|
| `sem1/2_approval_rate` | 이수 ÷ 수강 (수강 0이면 0 — 분모 0 방어) |
| `grade_change` | 2학기 평점 − 1학기 평점 |
| `zero_enrolled_1st_sem` | 1학기 수강 과목 0 여부 |
| `financial_risk_score` | 등록금 미납 + 채무 + 장학금 미수혜 (0~3) |

> ⚠️ **범주 라벨 문자열은 `notebooks/preprocess.ipynb` 의 매핑 딕셔너리와 글자 단위로 같아야 합니다.**
> `OneHotEncoder(handle_unknown='ignore')` 라서 한 글자만 달라도 **에러 없이 전부 0** 이 됩니다.
> 전처리 매핑을 바꾸면 `utils/feature_mapping.py` 의 상수를 함께 고치고 테스트를 돌려주세요.

---

## 4. 모델이 나오면 — 할 일은 두 가지뿐입니다

1. 학습된 모델을 `models/best_model.joblib` 로 저장합니다.
   (`.pkl` · `model.joblib` 도 인식합니다 — `services/real_predictor.py` 의 `MODEL_CANDIDATES`)
2. `services/prediction_service.py` 의 `USE_REAL_MODEL = False` → `True`

**화면 코드(`views/`, `components/`)는 한 줄도 고치지 않습니다.**
전처리는 `real_predictor.py` 안에서 `preprocessor.joblib` 으로 끝냅니다 (`transform` 만, `fit` 금지).

모델 담당자에게 확인해 주세요.

- `predict_proba` 를 제공하는지 (sklearn 계열이면 있습니다). keras 라면 분기 하나를 더 채웁니다.
- 클래스 순서 — 팀 정의가 `1=Dropout` 이므로 `predict_proba(...)[:, 1]` 을 씁니다.
  모델에 `classes_` 가 있으면 그 값으로 한 번 더 확인합니다.
- SHAP explainer 는 **선택**입니다. 없으면 확률만 실제 모델 값을 쓰고 위험요인 설명은
  프로토타입 설명을 유지하며, 그 사실이 화면에 그대로 표시됩니다.

---

## 5. 검증

```bash
cd app
python -m unittest discover -s tests -t .
```

**66개 통과** (로직 51 + 화면 15). 가장 중요한 것은 `TestPreprocessorContract` 입니다 —
학습된 모델이 없는 지금도 **팀 전처리기가 우리 입력을 그대로 받는지**는 실제로 확인할 수 있습니다.

- 더미 80명 → `to_model_row()` → `preprocessor.transform()` 이 **경고 없이 (80, 81)** 을 반환
- 범주형 8개 컬럼에 **미지 범주 0건** (라벨 문자열 대조)
- 입력 컬럼명·순서가 `preprocessor.feature_names_in_` 과 일치

브라우저(Chrome 1440×900)에서도 4개 화면 렌더링을 직접 확인했습니다.

---

## 6. 규칙 엔진

`rules/recommendation_rules.py` 하나가 소유하며 **LLM을 쓰지 않습니다** —
상담 문구를 모델이 생성하면 담당자가 근거를 설명할 수 없기 때문입니다.

| 카테고리 | 규칙 | 근거 피처 |
|---|---|---|
| 학업 | A1 이수율 저조 · A2 성적 저조 · A3 이수율 하락 · A4 미등록 · A5 성적 급락 | `sem2_approval_rate` · `grade_change` · `zero_enrolled_1st_sem` |
| 경제 | F1 등록금 미납 · F2 채무 · F3 재정위험 복합 | `financial_risk_score` |
| 진로·적응 | P1 낮은 지망 · P2 야간+부진 · P3 타지+고위험 · P4 특별지원 대상 | `Application order` · `Displaced` 등 |

서로 다른 카테고리 2개 이상 + 위험등급 HIGH/MEDIUM 이면 **집중관리 우선 대상**으로 표시합니다.
규칙을 추가하려면 `RULES` 리스트에 `Rule` 하나를 넣습니다. 화면 코드는 건드리지 않습니다.

지원 프로그램의 부서명은 **예시값**이므로 실제 운영 시 학교 조직에 맞게 바꿔야 합니다.

---

## 7. 발표 관련 메모

- `.streamlit/config.toml` 에서 **라이트 테마를 고정**했습니다. 발표 PC 설정에 따라 색이 뒤집히지 않습니다.
- DummyPredictor 는 난수를 쓰지 않습니다. **입력이 같으면 결과가 항상 같습니다** —
  새로고침마다 등급이 바뀌면 발표 중 설명이 무너지기 때문입니다.
- 더미 명단 80명은 시드 고정(`SEED = 20260831`)이라 CSV 를 지워도 같은 명단이 재생성됩니다.
- 시작화면 지구본은 **저절로 회전합니다** (한 바퀴 42초). 드래그하면 직접 돌릴 수 있고,
  손을 뗀 뒤 4초가 지나면 자동 회전이 다시 시작됩니다. 속도는 `components/globe.py` 의
  `ROTATION_PERIOD`, 끄려면 `AUTOROTATE = False`.
- 지구본은 Plotly 지도라 국가 경계 데이터를 실행 시점에 받아옵니다.
  **발표장 네트워크가 막혀 있으면** `components/globe.py` 의 `USE_PLOTLY_GLOBE = False` 로 바꾸세요.
  외부 통신이 전혀 없는 SVG 지구본으로 즉시 교체됩니다 (화면 코드는 그대로 · 단 회전은 없습니다).
