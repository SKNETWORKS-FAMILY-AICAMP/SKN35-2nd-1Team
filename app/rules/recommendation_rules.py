"""
규칙 기반 맞춤지원 추천 엔진.

설계 원칙
    1. **LLM 을 쓰지 않는다.** 상담 문구를 모델이 생성하면 담당자가 근거를 설명할 수 없다.
       모든 추천은 아래 RULES 목록에 명시된 조건에서만 나온다.
    2. **조건은 팀 전처리가 실제로 쓰는 변수로만 판단한다.** 데이터에 없는 사정
       (가정환경·심리상태 등)을 추측하지 않는다. 조건식에 쓰는 이름은
       `sem2_approval_rate` · `financial_risk_score` 처럼 팀 파생변수와 같은 이름이라,
       "왜 이 추천이 나왔나"를 모델 피처로 바로 되짚을 수 있다.
    3. **인과를 주장하지 않는다.** 이 엔진의 출력은
       "모델이 탐지한 위험요인에 대응하는 교내 지원 프로그램 연결"이지
       "이 지원을 하면 중도탈락을 막는다"가 아니다. DISCLAIMER 를 화면에 함께 띄운다.

규칙 추가하는 법
    RULES 리스트에 Rule 을 하나 더 넣으면 끝이다. 화면 코드는 고치지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from services.predictor import RISK_CATEGORIES, PredictionResult
from utils.feature_mapping import StudentInput

#: 화면에 붙는 한 줄. 길게 쓰면 아무도 안 읽고 화면만 무거워진다 —
#: 파일에 적히는 정식 문구는 `services/case_sheet.py` 가 따로 갖는다.
DISCLAIMER = (
    "지원 프로그램 참여가 중도탈락을 막는다는 인과관계를 뜻하지 않습니다."
)


# ---------------------------------------------------------------------------
# 지원 프로그램 / 규칙 자료구조
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Evidence:
    """규칙이 발동한 **수치 근거** 1개.

    사유 문구(`reason_template`)는 사람이 읽는 문장이고, 이쪽은 화면이 그리는 값이다.
    같은 임계값을 문자열에 한 번, 여기에 한 번 적지 않도록 **둘 다 모듈 상수를 참조**한다.
    담당자가 알아야 하는 것은 "기준을 넘었다"가 아니라 **"얼마나 넘었는가"** 이므로
    값·기준선·눈금 범위를 함께 들고 다닌다.
    """

    label: str                  # "2학기 이수율"
    value: float                # 이 학생의 값
    threshold: float            # 규칙 기준선
    unit: str = ""              # "%" | "점" | "/3"
    worse: str = "below"        # "below" | "above" — 기준선의 어느 쪽이 위험한가
    #: 기준선 **자기 값**이 발동에 포함되는가. 조건이 `<=` · `>=` 면 True, `<` · `>` 면 False.
    #  화면 문구가 여기서 갈린다 — 미만/이하, 초과/이상. 조건과 다르게 적으면
    #  경계에 딱 걸린 학생에게 "발동했는데 기준 미만은 아니다" 라는 화면이 나온다.
    inclusive: bool = False
    minimum: float = 0.0        # 눈금 범위 (막대를 그리려면 필요하다)
    maximum: float = 100.0

    @property
    def value_text(self) -> str:
        return f"{self.value:g}{self.unit}"

    @property
    def threshold_text(self) -> str:
        return f"{self.threshold:g}{self.unit}"

    def ratio(self, value: float) -> float:
        """눈금 범위 안에서의 위치(0~1). 화면이 막대 폭으로 쓴다."""
        span = self.maximum - self.minimum
        if span <= 0:
            return 0.0
        return min(max((value - self.minimum) / span, 0.0), 1.0)


@dataclass(frozen=True)
class SupportProgram:
    """연결할 교내 지원 프로그램 1개."""

    name: str
    owner: str      # 담당 부서 (예시 값이다 — 실제 운영 시 학교 조직에 맞게 교체)
    action: str     # 담당자가 실제로 할 일


@dataclass(frozen=True)
class Rule:
    """조건 1개 → 지원 프로그램 묶음 1개."""

    id: str
    category: str                                           # RISK_CATEGORIES 의 키
    title: str
    reason_template: str
    condition: Callable[[StudentInput, PredictionResult], bool]
    programs: tuple[SupportProgram, ...]
    feature: str = ""                                       # 근거가 되는 팀 피처 이름
    priority: int = 3                                       # 1이 가장 급함

    #: 수치 근거를 만드는 함수. 값 비교가 없는 boolean 규칙(F1·F2·P3·P4)은 None 이다.
    evidence: Callable[[StudentInput], Evidence] | None = None

    #: 이 규칙이 대응하는 **모델 위험요인**의 key. `services/dummy_predictor.py` 의
    #  `_Term.key` 와 같은 값을 쓴다 — 화면이 "왜 위험한가"와 "무엇을 할 것인가"를
    #  같은 이름으로 이을 수 있어야 한다.
    factor_keys: tuple[str, ...] = ()

    @property
    def category_label(self) -> str:
        return RISK_CATEGORIES.get(self.category, self.category)


@dataclass(frozen=True)
class MatchedRule:
    """실제로 발동한 규칙 + 그 학생에게 맞춰 채운 사유 문구."""

    rule: Rule
    reason: str
    evidence: Evidence | None = None     # 규칙에 evidence 가 없으면 None 이다

    @property
    def factor_keys(self) -> tuple[str, ...]:
        return self.rule.factor_keys

    @property
    def category(self) -> str:
        return self.rule.category

    @property
    def category_label(self) -> str:
        return self.rule.category_label


@dataclass
class RecommendationSet:
    """학생 1명에 대한 추천 결과 묶음."""

    matched: list[MatchedRule] = field(default_factory=list)
    #: 발동하지 **않은** 규칙. "왜 이 추천은 안 나왔나" 에 답하려면 이것도 있어야 한다.
    unmatched: list[Rule] = field(default_factory=list)
    is_priority_case: bool = False          # 복합 위험 → 집중관리 우선 대상
    priority_reason: str = ""
    disclaimer: str = DISCLAIMER

    @property
    def categories(self) -> list[str]:
        seen: list[str] = []
        for m in self.matched:
            if m.category not in seen:
                seen.append(m.category)
        return seen

    @property
    def category_labels(self) -> list[str]:
        return [RISK_CATEGORIES.get(c, c) for c in self.categories]

    @property
    def programs(self) -> list[SupportProgram]:
        """중복을 제거한 프로그램 목록 (같은 프로그램이 여러 규칙에서 나올 수 있다)."""
        out: list[SupportProgram] = []
        names: set[str] = set()
        for m in self.matched:
            for p in m.rule.programs:
                if p.name not in names:
                    names.add(p.name)
                    out.append(p)
        return out

    def __bool__(self) -> bool:
        return bool(self.matched)


# ---------------------------------------------------------------------------
# 규칙 정의
# ---------------------------------------------------------------------------

# 검증된 운영 기준
# - LOW_APPROVAL:
#   원본 데이터의 기존 Train/Validation 분할(random_state=42, stratify)을 재현한 뒤
#   50% / 55% / 60% 후보를 비교했다.
#   Train과 Validation 모두 60% 기준에서 세 후보 중 F1이 가장 높았고,
#   Validation Recall도 77.2%로 가장 높아 최종 지원 기준을 60% 미만으로 설정했다.
LOW_APPROVAL = 0.60
LOW_GRADE = 11.0             # 원본 0~20 기준

# - LOW_ADMISSION_GRADE:
#   Train 데이터에서 Admission grade 하나만 사용한 깊이 1 Decision Tree가
#   첫 분기점 111.85를 선택했다.
#   운영 편의성을 위해 112점 이하를 기준으로 사용하고,
#   Validation에서도 112점 이하 그룹의 실제 중도탈락률이 48.7%,
#   112점 초과 그룹은 29.7%로 차이가 확인되었다.
#   단, 단독 Recall은 낮으므로 '즉시 개입'이 아니라 초기 모니터링/기초학습 지원용으로 사용한다.
LOW_ADMISSION_GRADE: float = 112.0
APPROVAL_DROP = 0.15         # 1→2학기 이수율 하락 폭
GRADE_DROP = 2.0             # 학기 평점 하락 폭 (grade_change 기준)
HIGH_FINANCIAL_RISK = 2      # 재정위험점수 0~3 중 이 값 이상이면 복합 재정위험
LATE_CHOICE_ORDER = 3        # 지망 순위 4지망 이상


def _admission_grade(student: StudentInput) -> float | None:
    """StudentInput에서 입학 성적을 안전하게 읽는다.

    팀 feature_mapping.py에서 일반적으로 admission_grade로 매핑하는 것을 가정한다.
    실제 필드명이 다르면 아래 후보에 그 이름을 추가하면 된다.
    """
    for name in ("admission_grade", "Admission grade"):
        value = getattr(student, name, None)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _low_admission_grade(student: StudentInput) -> bool:
    """검증된 기준값이 설정된 경우에만 '낮은 입학 성적' 규칙을 발동한다."""
    value = _admission_grade(student)
    return (
        LOW_ADMISSION_GRADE is not None
        and value is not None
        and value <= LOW_ADMISSION_GRADE
    )


def _admission_grade_evidence(student: StudentInput) -> Evidence:
    value = _admission_grade(student)
    if value is None or LOW_ADMISSION_GRADE is None:
        raise ValueError("입학 성적 또는 검증된 기준값이 없습니다.")
    return Evidence(
        "입학 성적", round(value, 1), LOW_ADMISSION_GRADE,
        unit="점", worse="below", inclusive=True, minimum=0.0, maximum=200.0,
    )


RULES: tuple[Rule, ...] = (
    # ---------------- 학업 위험 ----------------------------------------
    Rule(
        id="A1",
        category="academic",
        title="2학기 이수율 저조",
        reason_template="2학기 이수율이 {sem2_rate:.0%} 로 기준({threshold:.0%}) 아래입니다.",
        condition=lambda s, r: s.sem2_enrolled > 0 and s.sem2_approval_rate < LOW_APPROVAL,
        feature="sem2_approval_rate",
        evidence=lambda s: Evidence(
            "2학기 이수율", round(s.sem2_approval_rate * 100, 1), LOW_APPROVAL * 100,
            unit="%", worse="below",
        ),
        factor_keys=("sem2_approval",),
        programs=(
            SupportProgram("학습지원센터 1:1 상담", "교수학습개발센터",
                           "수강 과목별 학습 장애 요인 진단 상담을 예약한다."),
            SupportProgram("동료 튜터링 프로그램", "교수학습개발센터",
                           "미이수 과목 중심으로 튜터를 매칭한다."),
        ),
        priority=1,
    ),
    Rule(
        id="A2",
        category="academic",
        title="평균 성적 저조",
        reason_template="두 학기 평균 성적이 {avg_grade:.1f}/20 으로 기준({threshold:.1f}) 아래입니다.",
        condition=lambda s, r: (s.sem1_enrolled + s.sem2_enrolled) > 0 and s.average_grade < LOW_GRADE,
        feature="Curricular units 1st/2nd sem (grade)",
        evidence=lambda s: Evidence(
            "두 학기 평균 성적", round(s.average_grade, 1), LOW_GRADE,
            unit="/20", worse="below", maximum=20.0,
        ),
        factor_keys=("sem2_grade", "sem1_grade"),
        programs=(
            SupportProgram("학습계획 수립 상담", "교수학습개발센터",
                           "다음 학기 수강 설계와 학습 시간표를 함께 작성한다."),
            SupportProgram("지도교수 정기 면담", "학과 사무실",
                           "학기 중 2회 이상 정기 면담 일정을 배정한다."),
        ),
        priority=2,
    ),
    Rule(
        id="A3",
        category="academic",
        title="1학기 대비 2학기 이수율 하락",
        reason_template="이수율이 1학기 {sem1_rate:.0%} → 2학기 {sem2_rate:.0%} 로 하락했습니다.",
        condition=lambda s, r: (
            s.sem1_enrolled > 0 and s.sem2_enrolled > 0
            and (s.sem1_approval_rate - s.sem2_approval_rate) >= APPROVAL_DROP
        ),
        feature="sem1_approval_rate → sem2_approval_rate",
        evidence=lambda s: Evidence(
            "이수율 하락폭",
            round((s.sem1_approval_rate - s.sem2_approval_rate) * 100, 1),
            APPROVAL_DROP * 100, unit="%p", worse="above", inclusive=True,
        ),
        factor_keys=("sem2_approval", "sem1_approval"),
        programs=(
            SupportProgram("조기 학업점검 면담", "학생지원팀",
                           "이수율이 떨어진 시점의 사유를 확인하는 면담을 진행한다."),
        ),
        priority=2,
    ),
    Rule(
        id="A4",
        category="academic",
        title="수강 신청 과목이 없음",
        reason_template="2학기 수강 과목이 0과목으로 기록되어 있습니다. 학적 상태 확인이 필요합니다.",
        condition=lambda s, r: s.sem2_enrolled == 0 or s.zero_enrolled_1st_sem == 1,
        feature="zero_enrolled_1st_sem",
        evidence=lambda s: Evidence(
            "2학기 수강 과목", s.sem2_enrolled, 1,
            unit="과목", worse="below", maximum=12.0,
        ),
        factor_keys=("sem2_approval", "sem1_approval"),
        programs=(
            SupportProgram("학적 상태 확인", "학사관리팀",
                           "휴학·미등록 여부를 학사 시스템에서 대조한다."),
        ),
        priority=1,
    ),
    Rule(
        id="A5",
        category="academic",
        title="학기 간 성적 급락",
        reason_template="학기 평점이 {grade_change:+.1f}점 변동했습니다 (하락 기준 {threshold:.1f}점).",
        condition=lambda s, r: (
            s.sem1_enrolled > 0 and s.sem2_enrolled > 0 and s.grade_change <= -GRADE_DROP
        ),
        feature="grade_change",
        evidence=lambda s: Evidence(
            "학기 평점 변화", round(s.grade_change, 1), -GRADE_DROP,
            unit="점", worse="below", inclusive=True, minimum=-10.0, maximum=10.0,
        ),
        factor_keys=("grade_change",),
        programs=(
            SupportProgram("학습 저해요인 진단", "교수학습개발센터",
                           "성적이 떨어진 학기의 수강 구성과 생활 여건을 함께 점검한다."),
        ),
        priority=2,
    ),
    Rule(
        id="A6",
        category="academic",
        title="입학 초기 학업지원 필요",
        reason_template="입학 성적이 {admission_grade:.1f}점으로 기준({threshold:.1f}점) 이하입니다.",
        condition=lambda s, r: _low_admission_grade(s),
        feature="Admission grade",
        evidence=_admission_grade_evidence,
        factor_keys=("admission_grade",),
        programs=(
            SupportProgram("입학 초기 기초학습 진단", "교수학습개발센터",
                           "기초학업 역량을 진단하고 보완이 필요한 영역을 확인한다."),
            SupportProgram("신입생 튜터링 프로그램", "교수학습개발센터",
                           "기초과목 중심으로 튜터를 매칭하고 1학기 학업 적응을 지원한다."),
        ),
        priority=3,
    ),
    # ---------------- 경제 위험 ----------------------------------------
    Rule(
        id="F1",
        category="financial",
        title="등록금 납부 미완료",
        reason_template="등록금 납부 상태가 '미납'으로 기록되어 있습니다.",
        condition=lambda s, r: s.tuition_fees_up_to_date == 0,
        feature="Tuition fees up to date",
        factor_keys=("tuition_unpaid",),
        programs=(
            SupportProgram("등록금 분할납부 안내", "학생지원팀",
                           "분할납부·납부기한 연장 제도를 안내한다."),
            SupportProgram("학자금 지원 상담", "장학복지팀",
                           "국가장학금·학자금대출 신청 가능 여부를 확인한다."),
        ),
        priority=1,
    ),
    Rule(
        id="F2",
        category="financial",
        title="채무 보유",
        reason_template="채무 보유(Debtor) 상태로 기록되어 있습니다.",
        condition=lambda s, r: s.debtor == 1,
        feature="Debtor",
        factor_keys=("debtor",),
        programs=(
            SupportProgram("학자금 대출 상담", "장학복지팀",
                           "상환 유예·전환 대출 가능 여부를 상담한다."),
            SupportProgram("학생복지 지원제도 안내", "학생지원팀",
                           "긴급 생활지원·교내 근로장학 정보를 제공한다."),
        ),
        priority=2,
    ),
    Rule(
        id="F3",
        category="financial",
        title="재정 위험요인 복합",
        reason_template="재정위험점수가 {financial_risk}/3 입니다 "
                        "(등록금 미납 · 채무 · 장학금 미수혜 중 {financial_risk}개 해당).",
        condition=lambda s, r: s.financial_risk_score >= HIGH_FINANCIAL_RISK,
        feature="financial_risk_score",
        evidence=lambda s: Evidence(
            "재정위험점수", s.financial_risk_score, HIGH_FINANCIAL_RISK,
            unit="/3", worse="above", inclusive=True, maximum=3.0,
        ),
        factor_keys=("financial_risk", "scholarship"),
        programs=(
            SupportProgram("교내 장학제도 안내", "장학복지팀",
                           "성적·소득 연계 교내 장학 신청 자격을 검토한다."),
        ),
        priority=1,
    ),
    # ---------------- 진로·적응 위험 ------------------------------------
    Rule(
        id="P1",
        category="adaptation",
        title="낮은 지망 순위로 입학",
        reason_template="{choice}지망으로 입학한 기록이 있습니다(원본 Application order 기준).",
        condition=lambda s, r: s.application_order >= LATE_CHOICE_ORDER,
        feature="Application order",
        evidence=lambda s: Evidence(
            "지망 순위", s.application_order + 1, LATE_CHOICE_ORDER + 1,
            unit="지망", worse="above", inclusive=True, minimum=1.0, maximum=10.0,
        ),
        factor_keys=("application_order",),
        programs=(
            SupportProgram("전공 적합도 상담", "학과 사무실",
                           "전공 만족도와 전과·복수전공 선택지를 함께 검토한다."),
            SupportProgram("진로상담센터 연계", "진로취업지원팀",
                           "진로검사 후 상담사를 배정한다."),
        ),
        priority=3,
    ),
    Rule(
        id="P2",
        category="adaptation",
        title="야간 과정 재학 + 학업 부진",
        reason_template="야간 과정 재학 중이며 2학기 이수율이 {sem2_rate:.0%} 입니다.",
        condition=lambda s, r: s.attendance == 0 and s.sem2_approval_rate < LOW_APPROVAL,
        feature="Daytime/evening attendance",
        evidence=lambda s: Evidence(
            "2학기 이수율", round(s.sem2_approval_rate * 100, 1), LOW_APPROVAL * 100,
            unit="%", worse="below",
        ),
        factor_keys=("evening", "sem2_approval"),
        programs=(
            SupportProgram("학사 유연화 상담", "학사관리팀",
                           "수강 부담 조정(감축 수강·계절학기)을 안내한다."),
        ),
        priority=3,
    ),
    Rule(
        id="P3",
        category="adaptation",
        title="타지 거주 + 고위험",
        reason_template="타지 거주(Displaced) 상태이며 위험등급이 {risk_level} 입니다.",
        condition=lambda s, r: s.displaced == 1 and r.risk_level == "HIGH",
        feature="Displaced",
        factor_keys=("displaced",),
        programs=(
            SupportProgram("생활·주거 지원 안내", "학생지원팀",
                           "기숙사 우선배정·생활지원 정보를 안내한다."),
        ),
        priority=3,
    ),
    Rule(
        id="P4",
        category="adaptation",
        title="교육적 특별지원 대상",
        reason_template="교육적 특별지원(Educational special needs) 대상으로 기록되어 있습니다.",
        condition=lambda s, r: s.special_needs == 1,
        feature="Educational special needs",
        factor_keys=(),  # 데이터에 없는 사정이라 모델 요인과 잇지 않는다
        programs=(
            SupportProgram("장애학생지원센터 연계", "학생지원팀",
                           "학습 편의 지원(보조기기·대체자료·시험 조정)을 안내한다."),
        ),
        priority=2,
    ),
)


# ---------------------------------------------------------------------------
# 평가
# ---------------------------------------------------------------------------

#: 복합 위험(집중관리 우선 대상) 판정 기준
PRIORITY_MIN_CATEGORIES = 2

#: `Rule.priority` 를 담당자가 읽는 말로. 화면과 내려받는 파일이 **같은 말**을 써야
#  하므로 규칙 모듈이 소유한다 (예전에는 ui.py 안에만 있었다).
PRIORITY_LABELS: dict[int, str] = {1: "즉시", 2: "이번 학기", 3: "모니터링"}


def _fill_reason(rule: Rule, student: StudentInput, result: PredictionResult) -> str:
    """규칙의 사유 문구에 이 학생의 실제 값을 채운다."""
    if "{avg_grade" in rule.reason_template:
        threshold: float | None = LOW_GRADE
    elif "{grade_change" in rule.reason_template:
        threshold = GRADE_DROP
    elif "{admission_grade" in rule.reason_template:
        threshold = LOW_ADMISSION_GRADE
    else:
        threshold = LOW_APPROVAL

    values = {
        "sem1_rate": student.sem1_approval_rate,
        "sem2_rate": student.sem2_approval_rate,
        "avg_grade": student.average_grade,
        "grade_change": student.grade_change,
        "admission_grade": _admission_grade(student),
        "financial_risk": student.financial_risk_score,
        "threshold": threshold,
        "choice": student.application_order + 1,
        "risk_level": result.risk_level,
    }
    try:
        return rule.reason_template.format(**values)
    except (KeyError, IndexError, ValueError):
        # 문구 서식이 잘못돼도 화면이 죽으면 안 된다.
        return rule.title


def evidence_of(rule: Rule, student: StudentInput) -> Evidence | None:
    """규칙의 수치 근거. 근거가 없거나 계산이 실패하면 None 이다.

    **발동한 규칙과 발동하지 않은 규칙이 같은 함수를 쓴다** — 판정 트레이스에서
    "이 학생 값은 얼마였고 기준은 얼마였나" 를 미발동 규칙에도 똑같이 보여줘야 하기 때문이다.
    """
    if rule.evidence is None:
        return None
    try:
        return rule.evidence(student)
    except Exception:  # 근거 하나가 깨져도 추천 자체는 나와야 한다.
        return None


def evaluate(student: StudentInput, result: PredictionResult) -> RecommendationSet:
    """학생 + 예측결과 → 추천 묶음.

    규칙은 위험등급과 무관하게 조건만 보고 발동한다. 다만 '집중관리 우선 대상'
    판정에는 위험등급을 함께 본다.
    """
    matched: list[MatchedRule] = []
    unmatched: list[Rule] = []
    for rule in RULES:
        try:
            fired = bool(rule.condition(student, result))
        except Exception:  # 규칙 하나가 잘못돼도 나머지는 평가되어야 한다.
            fired = False
        if fired:
            matched.append(
                MatchedRule(
                    rule=rule,
                    reason=_fill_reason(rule, student, result),
                    evidence=evidence_of(rule, student),
                )
            )
        else:
            unmatched.append(rule)

    matched.sort(key=lambda m: (m.rule.priority, m.rule.id))

    recommendation = RecommendationSet(matched=matched, unmatched=unmatched)

    distinct = len(recommendation.categories)
    if distinct >= PRIORITY_MIN_CATEGORIES and result.risk_level in ("HIGH", "MEDIUM"):
        labels = " · ".join(recommendation.category_labels)
        recommendation.is_priority_case = True
        recommendation.priority_reason = (
            f"{labels} 영역의 위험요인이 동시에 확인되었고 위험등급이 "
            f"{result.risk_level} 입니다. 단일 부서 대응보다 통합 관리가 필요합니다."
        )

    return recommendation


def primary_category(student: StudentInput, result: PredictionResult) -> str:
    """학생 목록 테이블의 '주요 위험' 열에 쓸 대표 카테고리 1개.

    가장 우선순위가 높은(숫자가 작은) 규칙의 카테고리를 쓰고, 발동 규칙이 없으면
    예측기가 준 최상위 위험요인의 카테고리를 쓴다. 둘 다 없으면 빈 문자열.
    """
    recommendation = evaluate(student, result)
    if recommendation.matched:
        return recommendation.matched[0].category
    if result.top_factors:
        return result.top_factors[0].category
    return ""
