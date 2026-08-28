# Dropout Insight: 대학생 중도 자퇴 예측 및 맞춤 대응 전략

## 목차
- [1. 프로젝트 개요](#1-프로젝트-개요)
- [2. 팀 소개](#2-팀-소개)
- [3. 프로젝트 구조](#3-프로젝트-구조)
- [4. 개발 환경](#4-개발-환경)
- [5. 설치 및 실행 방법](#5-설치-및-실행-방법)
- [6. 데이터 구성](#6-데이터-구성)
- [7. 데이터 전처리](#7-데이터-전처리)
- [8. 평가 지표](#8-평가-지표)
- [9. 결과](#9-결과)
- [10. Git 협업 규칙](#10-git-협업-규칙)
- [11. 모델 및 데이터 파일 규칙](#11-모델-및-데이터-파일-규칙)
- [12. Streamlit 실행](#12-streamlit-실행)

---

## 1. 프로젝트 개요

**프로젝트 명**: 대학생 중도 자퇴 예측 및 맞춤 대응 전략

**프로젝트 소개**

UCI "Predict Students' Dropout and Academic Success" 데이터셋(4,424명 규모)을 기반으로, 학생의 인구통계·사회경제적 배경·1·2학기 학업 성과 데이터를 분석하여 중도 자퇴(Dropout) 여부를 예측하는 프로젝트입니다.

- EDA를 통해 자퇴에 실질적으로 영향을 주는 변수(학기별 성적·이수과목 수, 등록금 완납 여부, 나이 등)와 상대적으로 영향이 적은 변수(국적, 특수교육 대상 여부 등)를 구분합니다.
- 데이터 전처리(결측치 확인, 파생변수 생성, 범주형 그룹화·인코딩, 스케일링)를 거쳐 여러 머신러닝/딥러닝 모델(Logistic Regression, Random Forest, XGBoost, LightGBM, MLP)의 성능을 비교합니다.
- 최종적으로 성능이 가장 우수한 모델을 선정하고, Streamlit으로 배포하여 신규 학생 데이터 입력 시 자퇴 위험도를 예측할 수 있도록 합니다.

**프로젝트 목표**

- 데이터 정제 및 분석
  - 결측치·중복행 확인(원본 데이터 자체는 결측치 0건), 컬럼명 정리, 파생변수 생성(1학기 0과목 등록 플래그, 학기별 이수율, 성적 변화량, 재정 위험도 점수 등)
  - EDA를 통한 변수별 Dropout 영향력 분석 (범주형 교차분석, 수치형 상관관계 분석)
  - 고카디널리티 범주형 변수(전공, 지원 전형, 부모 학력/직업)의 그룹화 및 한글 라벨링
- 머신러닝·딥러닝 모델 비교
  - Logistic Regression, Random Forest, XGBoost, LightGBM(머신러닝) + MLP(PyTorch, 딥러닝) 다중 모델 비교
  - 클래스 불균형(Dropout 32.12% : Non-Dropout 67.88%)을 고려한 평가 지표 설정
- 결과 확인 및 분석
  - 모델별 성능 비교 (F1-score, Recall, Precision 등)
  - 자퇴에 영향을 미치는 핵심 요인 도출 및 맞춤 대응 전략(재정지원 그룹 vs 학습지원 그룹 세그먼트 등) 제안

---

## 2. 팀 소개


👥 **팀원**

| 역할 | 담당 | 주요 업무 |
| --- | --- | --- |
| **1. 팀장/PM·서비스 통합** | 조현주 | 기획 총괄, Streamlit 앱 구조 설계·통합, 전체 산출물 취합, README/PPT 총괄 |
| **2. 데이터 전처리·EDA** | 박수휘 | 품질점검, EDA, 결측/이상치 처리, Target 정의 근거 마련, 전처리 결과서 |
| **3. 모델링 A (ML 계열 1)** | 고은하 | Logistic Regression + Random Forest 학습·튜닝, 변수중요도 분석 |
| **4. 모델링 B (ML 계열 2 + DL)** | 정은미, 조현주 | XGBoost/LightGBM + MLP(딥러닝) 학습·튜닝, 임계값 최적화 |
| **5. 세그먼트 분석·해석** | 전체 | K-Means 군집분석, SHAP/Permutation Importance로 "맞춤 대응 전략" 설계, 학습 결과서 취합 |
| **6. Streamlit** | 이세희 | Streamlit UI 설계 및 구현 |

---

## 3. 프로젝트 구조

```
SKN35-2nd-1Team
├── app/                                   # Streamlit 서비스 (예정)
│
├── data/
│   ├── raw/
│   │   └── data.csv                       # 원본 데이터 (UCI CSV, 용량 커서 커밋 X)
│   └── processed/                         # 전처리 완료 데이터 (Git 추적 대상)
│
├── notebooks/                             # 팀원별 EDA·실험 노트북 (.ipynb)
│   ├── 01_eda.ipynb                       # 탐색적 데이터 분석 노트북
│   ├── preprocess.ipynb                   # 전처리 파이프라인 노트북
│
├─ src                                     # 공용 전처리/모델링 함수 (.py)
│
├── models/                                # 학습 완료된 모델 파일 (.pkl 등)
│   ├── preprocessor.joblib                # 학습된 전처리 파이프라인 (ColumnTransformer)
│   ├── logistic_regression.joblib
│   ├── random_forest.joblib 
│   ├── xgboost.joblib 
│   ├── lightgbm.joblib
│   └── mlp.joblib
│
├── reports/                               # 전처리 결과서, 학습 결과서 (.md)
│   ├── eda_report.md                      # EDA 결과 리포트
│   └── figures/
│       ├── target_distribution.png
│       ├── correlation_heatmap.png
│       ├── categorical_dropout_rate.png
│       ├── derived_features.png
│       └── numeric_boxplots.png
│
├─ venv                                    # 가상환경 (커밋 X)
├─ .gitignore                              # Git 추적 제외 목록
├─ .gitattributes                          # 줄바꿈(LF) 통일 설정
├─ README.md                               # 프로젝트 소개 및 환경설정 안내
└─ requirements.txt                        # 파이썬 라이브러리 목록
```

---

## 4. 개발 환경

| 구분 | 기술 |
| ------------ | ------------|
| **언어** | ![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white) |
| **데이터 분석** | ![Pandas](https://img.shields.io/badge/Pandas-2.2.3-150458?logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-2.1.0-013243?logo=numpy&logoColor=white) |
| **머신러닝** | ![Scikit--learn](https://img.shields.io/badge/Scikit--learn-1.9.0-F7931E?logo=scikit-learn&logoColor=white) ![LogisticRegression](https://img.shields.io/badge/LogisticRegression-0.0.0-2C3E50?logo=LogisticRegression&logoColor=white)![RandomForest](https://img.shields.io/badge/RandomForest-0.0.0-2C3E50?logo=RandomForest&logoColor=white) ![LightGBM](https://img.shields.io/badge/LightGBM-4.5.0-2C3E50?logo=LightGBM&logoColor=white) ![XGBoost](https://img.shields.io/badge/XGBoost-0.0.0-189FDD?logo=xgboost&logoColor=white)|
| **딥러닝** | ![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?logo=pytorch&logoColor=white) ![MLP](https://img.shields.io/badge/MLP-0.0.0-189FDD?logo=MLP&logoColor=white) |
| **웹 애플리케이션** | ![Streamlit](https://img.shields.io/badge/Streamlit-1.49-FF4B4B?logo=streamlit&logoColor=white) |
| **협업** | ![Git](https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white) ![GitHub](https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white) |

세부 버전은 `requirements.txt`를 따르며, `scikit-learn`은 **1.9.0으로 고정**되어 있습니다. (전처리 파이프라인이 pickle(`preprocessor.joblib`)로 팀 전체에 공유되기 때문에, 버전 불일치 시 로드 오류/결과 불일치가 발생할 수 있어 정확히 고정했습니다.)

| 항목 | 내용 |
|---|---|
| Python | 3.12 |
| 패키지 매니저 | uv |
| 개발 도구 | VS Code + Jupyter Notebook |
| OS | macOS(Apple Silicon) / Windows 혼용 — 팀원별 환경 상이 |

---

## 5. 설치 및 실행 방법

프로젝트 루트에서 아래 명령으로 가상환경을 만들고 의존성을 설치합니다.

```bash
uv venv
source .venv/bin/activate      # Windows는 .venv\Scripts\activate
uv pip install -r requirements.txt
```

설치 후 버전이 정확히 맞는지 확인합니다.

```bash
python3 -c "import sklearn; print(sklearn.__version__)"   # 1.9.0 확인
```

---

## 6. 데이터 구성

원본 데이터는 [UCI Machine Learning Repository - Predict Students' Dropout and Academic Success](https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success)에서 다운로드한 뒤, 아래 경로에 저장합니다.

| 데이터 | 저장 경로 |
|---|---|
| 원본 데이터 | `data/raw/data.csv` |
| 전처리 완료 데이터(train/val/test) | `data/processed/*.csv` |

원본 CSV는 구분자가 세미콜론(`;`)이며 BOM 포함 UTF-8로 인코딩되어 있어, 로드 시 `sep=';', encoding='utf-8-sig'` 지정이 필요합니다.

---

## 7. 데이터 전처리

원본 데이터(4,424행 × 37열, 결측치 0건, 중복행 0건)를 대상으로 전처리를 진행한 뒤, Train/Validation/Test 세 파일로 분리하여 저장합니다.

```
원본 데이터 로드 (data/raw/data.csv)
    → 컬럼명 정리 (탭 문자 제거)
    → 이진 타겟 생성 (Dropout=1 / Graduate·Enrolled=0)
    → 파생변수 생성 (행 단위 계산, split 전 처리 가능)
    → Train(60%) / Val(20%) / Test(20%) 계층 분할 (stratify=y)
    → ColumnTransformer 기반 전처리 (fit은 Train에만)
    → train.csv / val.csv / test.csv 저장
    → preprocessor.joblib 저장
```

| 단계 | 적용 내용 |
|---|---|
| 파생변수 | `zero_enrolled_1st_sem`(1학기 0과목 등록 플래그), `sem1_approval_rate`/`sem2_approval_rate`(학기별 이수율), `grade_change`(성적 변화량), `financial_risk_score`(재정 위험도 점수) |
| 범주형 그룹화 | `Application mode` → `Admission_pathway`(전형 유형 8종, 한글 라벨), `Course` → `Major_field`(전공 계열 10종), `Previous qualification` → `Previous_education_level`, 부모 학력/직업 코드 → `Mother/Father_education_level`, `Mother/Father_occupation_group` |
| 인코딩 | 저카디널리티 범주형(`Marital status`, 그룹화된 범주형)은 `OneHotEncoder` |
| 스케일링 | 연속형 변수(성적, 나이, 실업률 등 19개)는 `StandardScaler` |
| 이진 플래그 | `Displaced`, `Debtor`, `Tuition fees up to date` 등은 원본 값 그대로 통과(passthrough) |
| 데이터 분할 | `random_state=42`, Dropout 비율(32.12%)을 유지하는 계층 추출로 Train 60% / Val 20% / Test 20% 분리 |

데이터 누수(leakage) 방지를 위해, 여러 행의 통계가 필요한 변환(`StandardScaler`, `OneHotEncoder`)은 Train 데이터에만 `fit`한 뒤 Val/Test에는 `transform`만 적용했습니다.

### 전처리 결과

| 파일 | 구성 | 크기 |
|---|---|---|
| `data/processed/train.csv` | 입력 특성 81개 + 타깃(target) | 2,654행 × 82열 |
| `data/processed/val.csv` | 동일 | 885행 × 82열 |
| `data/processed/test.csv` | 동일 | 885행 × 82열 |

EDA 분석 근거는 `reports/eda_report.md`에서 확인할 수 있습니다.

---

## 8. 평가 지표

클래스 비율이 완전한 균형이 아니므로(Dropout 32.12% : Non-Dropout 67.88%), Accuracy 단독으로는 판단하지 않고 아래 지표를 함께 확인합니다.

- **F1-score**: 전체 모델 비교의 기준 지표
- **Recall(재현율)**: 실제 자퇴 위험군을 놓치지 않는지 확인 (맞춤 대응 전략 설계상 False Negative가 가장 치명적)
- **Precision**: 재정·학습 지원 리소스가 한정적이므로 오탐 비율도 함께 고려

```python
from sklearn.metrics import classification_report
print(classification_report(y_test, pred))
```

---

## 9. 결과


| 모델 | F1-score | Recall | Precision |
|---|---|---|---|
| Logistic Regression | | | |
| Random Forest | | | |
| XGBoost | | | |
| LightGBM | | | |
| MLP (PyTorch) | | | |

최종 채택 모델: 

핵심 인사이트: 

---

## 11. Git 협업 규칙

- 팀원별 개인 브랜치에서 작업 후 `main`으로 병합합니다.
- 파일 단위가 아닌 **의미 단위**로 커밋을 분리합니다. (예: EDA 노트북 / EDA 리포트+그림 / 전처리 노트북 / 전처리 산출물을 각각 별도 커밋)
- 여러 명이 동시에 다루는 바이너리 산출물(`preprocessor.joblib` 등)은 임의로 덮어쓰지 않고, 변경 시 팀에 공지합니다.

---

## 12. 모델 및 데이터 파일 규칙

- `data/raw/`의 원본 데이터는 절대 직접 수정하지 않습니다.
- `models/preprocessor.joblib`은 Streamlit 등 후속 단계에서 동일한 변환을 재현하기 위한 목적으로 Git에 커밋합니다.
- `scikit-learn`은 **1.9.0으로 고정**합니다 (`requirements.txt` 참고). 버전이 다르면 `preprocessor.joblib` 로드 시 호환성 경고/오류가 발생하거나, 동일 코드라도 결과가 미묘하게 달라질 수 있습니다.
- 전처리 파이프라인이나 데이터 분할 방식이 변경되면 `train.csv` / `val.csv` / `test.csv` / `preprocessor.joblib`을 함께 재생성하여 팀 전체에 공지합니다.
  
## 환경 설정 (공식)
이 프로젝트는 `venv` + `requirements.txt`를 표준으로 사용합니다.

python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt

⚠️ pyproject.toml / uv.lock 은 실험적으로 추가된 파일로, 현재 사용하지 않습니다.

---

## 13. Streamlit 실행

```bash
streamlit run app/main.py
```
