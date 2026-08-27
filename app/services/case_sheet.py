"""
상담 카드 — 화면에서 본 것을 담당자 손에 남기는 계층.

**예측만 하고 끝나지 않는다**는 이 제품의 주장은 화면 밖으로 나가는 파일이 있어야
증명된다. 규칙 엔진이 담당 부서(`SupportProgram.owner`)와 할 일(`action`)을 이미 들고
있으므로 여기서는 **조립만 한다** — 새 판단을 만들지 않는다.

설계에서 지킨 것
    1. **면책 문구를 파일 안에 넣는다.** 화면 배너는 파일을 따라가지 않는다.
       출처(더미인지 실제 모델인지)도 카드 안에 그대로 적는다.
    2. **엑셀 한글이 깨지지 않게 UTF-8 BOM 으로 낸다.** 담당자가 여는 것은 대개 엑셀이다.
    3. 화면 코드에 문자열을 만들지 않는다. 예측 화면과 목록 화면이 같은 함수를 부른다.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from rules.recommendation_rules import (
    PRIORITY_LABELS,
    RecommendationSet,
    evidence_of,
)
from services.predictor import PredictionResult
from utils.feature_mapping import StudentInput

PRODUCT = "Student Dropout Intelligence · SKN35 2nd Team"

#: 파일에도 남기는 면책. 화면의 DISCLAIMER 와 같은 말이지만 **더 짧고 단정적**으로 쓴다 —
#  파일은 맥락 없이 전달되므로 한 문단 안에서 스스로 설명해야 한다.
FILE_NOTICE = (
    "이 카드는 예측 모델이 탐지한 위험요인에 대응하는 교내 지원 프로그램을 연결한 것입니다. "
    "학생의 중도탈락을 단정하지 않으며, 지원 참여가 중도탈락을 방지한다는 인과관계를 "
    "의미하지도 않습니다. 최종 판단과 학생 접촉은 담당자가 합니다. "
    "학생 개인정보가 포함되므로 취급에 주의하십시오."
)


def _source_line(result: PredictionResult) -> str:
    kind = "프로토타입(학습되지 않은 규칙 기반)" if result.is_dummy else "학습된 모델"
    return f"{result.model_name} v{result.model_version} · {kind} · 설명 출처 {result.explanation_source}"


# ---------------------------------------------------------------------------
# 1. 상담 카드 (텍스트 한 장)
# ---------------------------------------------------------------------------

def build_text(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
    *,
    now: datetime | None = None,
) -> str:
    """학생 1명의 상담 카드. 화면의 읽는 순서를 그대로 옮긴다.

        얼마나 위험한가 → 왜 위험한가 → 무엇을 할 것인가 → 무엇은 해당 없었나
    """
    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
    out: list[str] = []
    add = out.append

    add("=" * 68)
    add(f"학생 상담 카드 · {student.student_id}")
    add("=" * 68)
    add("")
    add(f"중도탈락 확률   {result.dropout_percent:.1f}%   (위험등급 {result.risk_level})")
    add(f"전공 계열       {student.major_field}")
    add(f"입학 전형       {student.admission_pathway} · {student.application_order + 1}지망")
    add(f"수업 시간대     {'주간' if student.attendance == 1 else '야간'}")
    add(f"2학기 이수율    {student.sem2_approval_rate:.0%} "
        f"({student.sem2_approved}/{student.sem2_enrolled}과목)")
    add(f"평균 성적       {student.average_grade:.1f} / 20")
    add(f"재정위험점수    {student.financial_risk_score} / 3")
    if recommendation.is_priority_case:
        add("")
        add(f"[집중관리 우선 대상] {recommendation.priority_reason}")

    add("")
    add("-" * 68)
    add("모델이 본 위험요인")
    add("-" * 68)
    if result.top_factors:
        for index, factor in enumerate(result.top_factors, start=1):
            add(f"{index}. {factor.label}  ({factor.contribution:.0%} · {factor.category_label})")
            add(f"   {factor.detail}")
    else:
        add("기준선을 넘는 위험요인이 확인되지 않았습니다.")

    add("")
    add("-" * 68)
    add(f"발동한 지원 규칙 {len(recommendation.matched)}건 — 무엇을 할 것인가")
    add("-" * 68)
    if not recommendation.matched:
        add("조건을 넘는 규칙이 없습니다. 정기 모니터링 대상으로만 유지합니다.")
    for m in recommendation.matched:
        timing = PRIORITY_LABELS.get(m.rule.priority, "검토")
        add(f"[{m.rule.id}] {m.rule.title}   ({timing} · {m.category_label})")
        add(f"   사유  {m.reason}")
        if m.evidence is not None:
            side = "미만" if m.evidence.worse == "below" else "이상"
            add(f"   수치  {m.evidence.label} {m.evidence.value_text} "
                f"(기준 {m.evidence.threshold_text} {side}이면 발동)")
        for program in m.rule.programs:
            add(f"   → {program.name}  [{program.owner}]")
            add(f"      {program.action}")
        add("")

    add("-" * 68)
    add(f"발동하지 않은 규칙 {len(recommendation.unmatched)}건 — 확인했으나 해당 없음")
    add("-" * 68)
    for rule in recommendation.unmatched:
        evidence = evidence_of(rule, student)
        detail = (
            f"{evidence.label} {evidence.value_text} (기준 {evidence.threshold_text})"
            if evidence is not None else "해당 없음"
        )
        add(f"[{rule.id}] {rule.title} — {detail}")

    add("")
    add("=" * 68)
    add(f"예측 출처  {_source_line(result)}")
    add(f"생성       {stamp} · {PRODUCT}")
    add("")
    add(FILE_NOTICE)
    add("=" * 68)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 2. 표 (CSV)
# ---------------------------------------------------------------------------

SUMMARY_FIELDS = (
    "학생 ID", "전공 계열", "중도탈락 확률(%)", "위험등급", "집중관리",
    "발동 규칙 수", "발동 규칙", "대응 영역", "담당 부서", "2학기 이수율(%)",
    "평균 성적", "재정위험점수", "예측 출처",
)

ACTION_FIELDS = (
    "학생 ID", "중도탈락 확률(%)", "위험등급", "우선순위", "담당 부서",
    "지원 프로그램", "조치 내용", "규칙", "발동 사유", "수치 근거",
)


def summary_row(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
) -> dict[str, object]:
    """학생 1명 = 한 행. 명단 전체를 표로 넘길 때 쓴다."""
    return {
        "학생 ID": student.student_id,
        "전공 계열": student.major_field,
        "중도탈락 확률(%)": round(result.dropout_percent, 1),
        "위험등급": result.risk_level,
        "집중관리": "Y" if recommendation.is_priority_case else "",
        "발동 규칙 수": len(recommendation.matched),
        "발동 규칙": " ".join(m.rule.id for m in recommendation.matched),
        "대응 영역": " · ".join(recommendation.category_labels),
        # 부서로 필터해서 나눠 갖는 것이 이 표의 주 용도다.
        "담당 부서": " · ".join(dict.fromkeys(p.owner for p in recommendation.programs)),
        "2학기 이수율(%)": round(student.sem2_approval_rate * 100),
        "평균 성적": round(student.average_grade, 1),
        "재정위험점수": student.financial_risk_score,
        "예측 출처": _source_line(result),
    }


def action_rows(
    student: StudentInput,
    result: PredictionResult,
    recommendation: RecommendationSet,
) -> list[dict[str, object]]:
    """학생 × 지원 프로그램 = 한 행.

    부서별로 정렬·필터하면 그대로 **업무 배분표**가 된다. 요약 표와 달리 한 학생이
    여러 줄을 차지하므로, 두 형식 중 무엇이 필요한지는 쓰는 사람이 고르게 둔다.
    """
    rows: list[dict[str, object]] = []
    for m in recommendation.matched:
        if m.evidence is not None:
            side = "미만" if m.evidence.worse == "below" else "이상"
            evidence_text = (
                f"{m.evidence.label} {m.evidence.value_text} "
                f"(기준 {m.evidence.threshold_text} {side})"
            )
        else:
            evidence_text = "해당·미해당 판정"
        for program in m.rule.programs:
            rows.append({
                "학생 ID": student.student_id,
                "중도탈락 확률(%)": round(result.dropout_percent, 1),
                "위험등급": result.risk_level,
                "우선순위": PRIORITY_LABELS.get(m.rule.priority, "검토"),
                "담당 부서": program.owner,
                "지원 프로그램": program.name,
                "조치 내용": program.action,
                "규칙": f"{m.rule.id} {m.rule.title}",
                "발동 사유": m.reason,
                "수치 근거": evidence_text,
            })
    return rows


def to_csv(rows: list[dict[str, object]], fields: tuple[str, ...]) -> bytes:
    """CSV 바이트. **UTF-8 BOM** 을 붙인다 — 없으면 엑셀에서 한글이 깨진다.

    마지막 줄에 면책 문구를 한 칸으로 남긴다. 표만 떼어 전달돼도 근거를 잃지 않게.
    """
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(fields), extrasaction="ignore",
                            lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    writer.writerow({fields[0]: f"※ {FILE_NOTICE}"})
    return buffer.getvalue().encode("utf-8-sig")


def filename(prefix: str, student_id: str = "", *, extension: str = "csv",
             now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d")
    middle = f"_{student_id}" if student_id else ""
    return f"{prefix}{middle}_{stamp}.{extension}"
