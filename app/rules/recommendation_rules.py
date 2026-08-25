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

DISCLAIMER = (
    "이 추천은 모델이 탐지한 위험요인에 대응하는 교내 지원 프로그램을 연결한 것입니다. "
    "예측 결과는 학생의 중도탈락을 단정하지 않으며, 지원 프로그램 참여가 중도탈락을 "
    "방지한다는 인과관계를 의미하지도 않습니다. 최종 판단은 담당자가 합니다."
)


# ---------------------------------------------------------------------------
# 지원 프로그램 / 규칙 자료구조
# ---------------------------------------------------------------------------

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

    @property
    def category_label(self) -> str:
        return RISK_CATEGORIES.get(self.category, self.category)


@dataclass(frozen=True)
class MatchedRule:
    """실제로 발동한 규칙 + 그 학생에게 맞춰 채운 사유 문구."""

    rule: Rule
    reason: str

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

LOW_APPROVAL = 0.50          # 이수율이 이 아래면 "낮다"고 본다
LOW_GRADE = 11.0             # 원본 0~20 기준
APPROVAL_DROP = 0.15         # 1→2학기 이수율 하락 폭
GRADE_DROP = 2.0             # 학기 평점 하락 폭 (grade_change 기준)
HIGH_FINANCIAL_RISK = 2      # 재정위험점수 0~3 중 이 값 이상이면 복합 재정위험
LATE_CHOICE_ORDER = 3        # 지망 순위 4지망 이상

RULES: tuple[Rule, ...] = (
    # ---------------- 학업 위험 ----------------------------------------
    Rule(
        id="A1",
        category="academic",
        title="2학기 이수율 저조",
        reason_template="2학기 이수율이 {sem2_rate:.0%} 로 기준({threshold:.0%}) 아래입니다.",
        condition=lambda s, r: s.sem2_enrolled > 0 and s.sem2_approval_rate < LOW_APPROVAL,
        feature="sem2_approval_rate",
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
        programs=(
            SupportProgram("학습 저해요인 진단", "교수학습개발센터",
                           "성적이 떨어진 학기의 수강 구성과 생활 여건을 함께 점검한다."),
        ),
        priority=2,
    ),
    # ---------------- 경제 위험 ----------------------------------------
    Rule(
        id="F1",
        category="financial",
        title="등록금 납부 미완료",
        reason_template="등록금 납부 상태가 '미납'으로 기록되어 있습니다.",
        condition=lambda s, r: s.tuition_fees_up_to_date == 0,
        feature="Tuition fees up to date",
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


def _fill_reason(rule: Rule, student: StudentInput, result: PredictionResult) -> str:
    """규칙의 사유 문구에 이 학생의 실제 값을 채운다."""
    if "{avg_grade" in rule.reason_template:
        threshold: float = LOW_GRADE
    elif "{grade_change" in rule.reason_template:
        threshold = GRADE_DROP
    else:
        threshold = LOW_APPROVAL

    values = {
        "sem1_rate": student.sem1_approval_rate,
        "sem2_rate": student.sem2_approval_rate,
        "avg_grade": student.average_grade,
        "grade_change": student.grade_change,
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


def evaluate(student: StudentInput, result: PredictionResult) -> RecommendationSet:
    """학생 + 예측결과 → 추천 묶음.

    규칙은 위험등급과 무관하게 조건만 보고 발동한다. 다만 '집중관리 우선 대상'
    판정에는 위험등급을 함께 본다.
    """
    matched: list[MatchedRule] = []
    for rule in RULES:
        try:
            fired = bool(rule.condition(student, result))
        except Exception:  # 규칙 하나가 잘못돼도 나머지는 평가되어야 한다.
            fired = False
        if fired:
            matched.append(MatchedRule(rule=rule, reason=_fill_reason(rule, student, result)))

    matched.sort(key=lambda m: (m.rule.priority, m.rule.id))

    recommendation = RecommendationSet(matched=matched)

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
