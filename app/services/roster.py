"""
명단(roster) 조립 — 더미 학생 + 예측 결과 + 규칙 판정을 한 표로 합친다.

대시보드와 학생 목록 화면이 같은 숫자를 보게 하려고 계산을 여기 한 곳에 모았다.
예측기를 실제 모델로 바꿔도 이 파일은 그대로다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from rules import recommendation_rules as rules
from services.predictor import RISK_CATEGORIES, RISK_LABELS_KO, PredictionResult
from services.prediction_service import PredictionService
from utils.dummy_data import load_students
from utils.feature_mapping import TARGET_LABELS_KO, StudentInput
from utils.real_data import load_real_students


@dataclass(frozen=True)
class RosterRow:
    """명단 한 줄. 상세 화면으로 넘어갈 때 원본 객체를 그대로 들고 간다."""

    student: StudentInput
    result: PredictionResult
    recommendation: rules.RecommendationSet

    @property
    def primary_category(self) -> str:
        if self.recommendation.matched:
            return self.recommendation.matched[0].category
        if self.result.top_factors:
            return self.result.top_factors[0].category
        return ""


@dataclass(frozen=True)
class Roster:
    rows: list[RosterRow]
    frame: pd.DataFrame
    source: str          # 화면에 그대로 밝힌다 ("실제 전처리 데이터" / "합성 더미")
    is_real: bool

    def by_id(self, student_id: str) -> RosterRow | None:
        for row in self.rows:
            if row.student.student_id == student_id:
                return row
        return None


def load_roster_students() -> tuple[list[StudentInput], str, bool]:
    """명단으로 쓸 학생 목록을 고른다.

    팀이 올린 전처리 CSV 가 있으면 **그걸 원래 값으로 되돌려** 쓴다. 없으면 합성 더미로
    물러난다. 어느 쪽인지는 반환값으로 알려주고 화면이 그대로 표시한다 —
    무엇을 보고 있는지 모르는 채로 발표하면 안 된다.
    """
    real = load_real_students()
    if real is not None:
        return (
            real.students,
            f"팀 전처리 실데이터 {len(real.students)}명 (data/processed/{real.source})",
            True,
        )
    students = load_students()
    return students, f"합성 더미 {len(students)}명 (원본 데이터 아님)", False


def build_roster(service: PredictionService) -> Roster:
    """명단 전체를 예측하고 규칙까지 평가한다."""
    students, source, is_real = load_roster_students()
    results = service.predict_many(students)

    rows: list[RosterRow] = []
    records: list[dict] = []
    for student, result in zip(students, results):
        recommendation = rules.evaluate(student, result)
        row = RosterRow(student=student, result=result, recommendation=recommendation)
        rows.append(row)

        category = row.primary_category
        records.append(
            {
                "학생 ID": student.student_id,
                "전공 계열": student.major_field,
                "예측": TARGET_LABELS_KO.get(result.predicted_class, result.predicted_class),
                "예측(원본)": result.predicted_class,
                # 0~1 원본값은 정렬·필터용, (%)는 표 표시용으로 둘 다 둔다.
                "중도탈락 확률": result.dropout_probability,
                "중도탈락 확률(%)": result.dropout_percent,
                "위험등급": result.risk_level,
                "위험등급(한글)": RISK_LABELS_KO.get(result.risk_level, result.risk_level),
                "주요 위험": RISK_CATEGORIES.get(category, "-") if category else "-",
                "집중관리": "●" if recommendation.is_priority_case else "",
                "2학기 이수율": round(student.sem2_approval_rate * 100),  # 표 표시용 백분율
                "평균 성적": round(student.average_grade, 1),
                "재정위험점수": student.financial_risk_score,
                "등록금 미납": "미납" if student.tuition_fees_up_to_date == 0 else "",
                "장학금": "수혜" if student.scholarship_holder == 1 else "",
            }
        )

    frame = pd.DataFrame.from_records(records)
    return Roster(rows=rows, frame=frame, source=source, is_real=is_real)
