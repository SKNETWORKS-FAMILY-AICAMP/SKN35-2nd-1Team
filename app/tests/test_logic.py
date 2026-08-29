"""
로직 테스트 — 화면을 띄우지 않고 계약·계산·규칙을 검증한다.

실행:  cd app && python -m unittest discover -s tests -t .

가장 중요한 것은 `TestPreprocessorContract` 다. 학습된 모델이 없는 지금도
**팀 전처리기가 우리 입력을 그대로 받아들이는지**는 실제로 확인할 수 있다.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from rules import recommendation_rules as rules
from services import case_sheet, model_metrics
from services.dummy_predictor import DummyPredictor, _build_terms
from services.predictor import (
    DECISION_THRESHOLD,
    RISK_THRESHOLDS,
    make_result,
    risk_level_of,
)
from utils.dummy_data import generate_students, load_students
from utils.feature_mapping import (
    ADMISSION_PATHWAYS,
    MAJOR_FIELDS,
    TARGET_CLASSES,
    UI_FIELDS,
    StudentInput,
    missing_model_columns,
    student_from_mapping,
)
from utils.schema import model_input_columns, schema_available

PREDICTOR = DummyPredictor()


def student(**overrides) -> StudentInput:
    return StudentInput(**overrides)


# ---------------------------------------------------------------------------
# 1. 팀 전처리 스키마와의 계약
# ---------------------------------------------------------------------------

class TestSchemaContract(unittest.TestCase):
    def test_schema_file_is_readable(self):
        self.assertTrue(schema_available(), "data/processed/feature_schema.json 을 읽지 못했습니다.")

    def test_input_order_has_37_columns(self):
        self.assertEqual(len(model_input_columns()), 37)

    def test_no_column_is_left_unfilled(self):
        """전처리기가 요구하는 컬럼을 화면 입력 + 파생변수가 모두 덮는가."""
        self.assertEqual(missing_model_columns(), ())

    def test_model_row_matches_schema_order(self):
        ordered = student().to_model_ordered()
        self.assertEqual([name for name, _ in ordered], list(model_input_columns()))

    def test_ui_fields_map_to_distinct_columns(self):
        columns = [spec.column for spec in UI_FIELDS]
        self.assertEqual(len(columns), len(set(columns)))

    def test_ui_field_columns_all_exist_in_schema(self):
        known = set(model_input_columns())
        for spec in UI_FIELDS:
            with self.subTest(field=spec.key):
                self.assertIn(spec.column, known)


# ---------------------------------------------------------------------------
# 2. 파생변수 계산
# ---------------------------------------------------------------------------

class TestDerivedFeatures(unittest.TestCase):
    def test_approval_rate(self):
        s = student(sem1_enrolled=6, sem1_approved=3, sem2_enrolled=8, sem2_approved=2)
        self.assertAlmostEqual(s.sem1_approval_rate, 0.5)
        self.assertAlmostEqual(s.sem2_approval_rate, 0.25)

    def test_approval_rate_guards_zero_denominator(self):
        s = student(sem1_enrolled=0, sem1_approved=0, sem2_enrolled=0, sem2_approved=0)
        self.assertEqual(s.sem1_approval_rate, 0.0)
        self.assertEqual(s.sem2_approval_rate, 0.0)

    def test_approval_rate_is_capped_at_one(self):
        """이수가 수강보다 많은 모순 입력에서도 1을 넘지 않는다."""
        s = student(sem1_enrolled=3, sem1_approved=9)
        self.assertEqual(s.sem1_approval_rate, 1.0)

    def test_grade_change(self):
        s = student(sem1_grade=14.0, sem2_grade=10.5)
        self.assertAlmostEqual(s.grade_change, -3.5)

    def test_zero_enrolled_flag(self):
        self.assertEqual(student(sem1_enrolled=0).zero_enrolled_1st_sem, 1)
        self.assertEqual(student(sem1_enrolled=6).zero_enrolled_1st_sem, 0)

    def test_financial_risk_score_range_and_composition(self):
        worst = student(tuition_fees_up_to_date=0, debtor=1, scholarship_holder=0)
        best = student(tuition_fees_up_to_date=1, debtor=0, scholarship_holder=1)
        self.assertEqual(worst.financial_risk_score, 3)
        self.assertEqual(best.financial_risk_score, 0)
        self.assertEqual(student(debtor=1, scholarship_holder=1).financial_risk_score, 1)

    def test_average_grade_ignores_semester_without_enrollment(self):
        s = student(sem1_enrolled=6, sem1_grade=12.0, sem2_enrolled=0, sem2_grade=0.0)
        self.assertAlmostEqual(s.average_grade, 12.0)


# ---------------------------------------------------------------------------
# 3. 예측 결과 계약 (이진)
# ---------------------------------------------------------------------------

class TestPredictionResult(unittest.TestCase):
    def test_target_is_binary(self):
        self.assertEqual(TARGET_CLASSES, ("Dropout", "Non-Dropout"))

    def test_probabilities_sum_to_one(self):
        for probability in (0.0, 0.137, 0.5, 0.9999, 1.0):
            with self.subTest(p=probability):
                result = make_result(probability)
                self.assertAlmostEqual(sum(result.class_probabilities.values()), 1.0, places=6)

    def test_predicted_class_follows_threshold(self):
        self.assertEqual(make_result(DECISION_THRESHOLD).predicted_class, "Dropout")
        self.assertEqual(make_result(DECISION_THRESHOLD - 0.001).predicted_class, "Non-Dropout")

    def test_risk_level_boundaries(self):
        self.assertEqual(risk_level_of(RISK_THRESHOLDS["HIGH"]), "HIGH")
        self.assertEqual(risk_level_of(RISK_THRESHOLDS["HIGH"] - 0.001), "MEDIUM")
        self.assertEqual(risk_level_of(RISK_THRESHOLDS["MEDIUM"]), "MEDIUM")
        self.assertEqual(risk_level_of(RISK_THRESHOLDS["MEDIUM"] - 0.001), "LOW")

    def test_out_of_range_probability_is_rejected(self):
        from services.predictor import PredictionResult

        with self.assertRaises(ValueError):
            PredictionResult(dropout_probability=1.4, risk_level="HIGH")


# ---------------------------------------------------------------------------
# 4. DummyPredictor
# ---------------------------------------------------------------------------

class TestDummyPredictor(unittest.TestCase):
    def test_is_deterministic(self):
        """같은 입력이면 항상 같은 결과. 발표 중 새로고침으로 등급이 바뀌면 안 된다."""
        s = student(sem1_approved=2, sem2_approved=1, sem1_grade=9.0, sem2_grade=8.0)
        first = PREDICTOR.predict(s)
        second = PREDICTOR.predict(s)
        self.assertEqual(first.dropout_probability, second.dropout_probability)
        self.assertEqual(first.risk_level, second.risk_level)

    def test_worse_academics_raise_risk(self):
        good = student(sem1_approved=6, sem2_approved=6, sem1_grade=17.0, sem2_grade=17.0)
        bad = student(sem1_approved=1, sem2_approved=0, sem1_grade=6.0, sem2_grade=5.0)
        self.assertLess(
            PREDICTOR.predict(good).dropout_probability,
            PREDICTOR.predict(bad).dropout_probability,
        )

    def test_financial_risk_raises_risk(self):
        safe = student(tuition_fees_up_to_date=1, debtor=0, scholarship_holder=1)
        risky = student(tuition_fees_up_to_date=0, debtor=1, scholarship_holder=0)
        self.assertLess(
            PREDICTOR.predict(safe).dropout_probability,
            PREDICTOR.predict(risky).dropout_probability,
        )

    def test_probability_stays_in_range_for_extreme_inputs(self):
        extremes = [
            student(sem1_enrolled=0, sem1_approved=0, sem2_enrolled=0, sem2_approved=0,
                    sem1_grade=0.0, sem2_grade=0.0, admission_grade=0.0,
                    tuition_fees_up_to_date=0, debtor=1, scholarship_holder=0,
                    age_at_enrollment=70, application_order=9, attendance=0, displaced=1),
            student(sem1_enrolled=26, sem1_approved=26, sem2_enrolled=26, sem2_approved=26,
                    sem1_grade=20.0, sem2_grade=20.0, admission_grade=200.0,
                    scholarship_holder=1),
            student(sem1_approved=99, sem2_approved=99),  # 모순 입력
        ]
        for index, s in enumerate(extremes):
            with self.subTest(case=index):
                result = PREDICTOR.predict(s)
                self.assertGreaterEqual(result.dropout_probability, 0.0)
                self.assertLessEqual(result.dropout_probability, 1.0)

    def test_factor_contributions_are_normalised(self):
        result = PREDICTOR.predict(
            student(sem1_approved=1, sem2_approved=0, sem1_grade=7.0, sem2_grade=6.0,
                    tuition_fees_up_to_date=0, debtor=1)
        )
        self.assertTrue(result.top_factors)
        self.assertLessEqual(len(result.top_factors), 5)
        self.assertAlmostEqual(sum(f.contribution for f in result.top_factors), 1.0, places=3)

    def test_safe_student_has_no_or_few_factors(self):
        result = PREDICTOR.predict(
            student(sem1_approved=6, sem2_approved=6, sem1_grade=18.0, sem2_grade=18.5,
                    admission_grade=170.0, scholarship_holder=1)
        )
        self.assertEqual(result.risk_level, "LOW")


# ---------------------------------------------------------------------------
# 5. 규칙 엔진
# ---------------------------------------------------------------------------

class TestRules(unittest.TestCase):
    def fire(self, s: StudentInput) -> set[str]:
        return {m.rule.id for m in rules.evaluate(s, PREDICTOR.predict(s)).matched}

    def test_low_approval_fires_a1(self):
        self.assertIn("A1", self.fire(student(sem2_enrolled=6, sem2_approved=1)))

    def test_approval_drop_fires_a3(self):
        fired = self.fire(student(sem1_enrolled=6, sem1_approved=6, sem2_enrolled=6, sem2_approved=2))
        self.assertIn("A3", fired)

    def test_zero_enrolled_fires_a4(self):
        self.assertIn("A4", self.fire(student(sem2_enrolled=0, sem2_approved=0)))
        self.assertIn("A4", self.fire(student(sem1_enrolled=0, sem1_approved=0)))

    def test_grade_drop_fires_a5(self):
        self.assertIn("A5", self.fire(student(sem1_grade=15.0, sem2_grade=11.0)))
        self.assertNotIn("A5", self.fire(student(sem1_grade=15.0, sem2_grade=14.5)))

    def test_low_admission_grade_fires_a6(self):
    self.assertIn("A6", self.fire(student(admission_grade=100.0)))
    self.assertNotIn("A6", self.fire(student(admission_grade=150.0)))

    def test_unpaid_tuition_fires_f1(self):
        self.assertIn("F1", self.fire(student(tuition_fees_up_to_date=0)))

    def test_financial_risk_score_fires_f3(self):
        self.assertIn("F3", self.fire(student(tuition_fees_up_to_date=0, scholarship_holder=0)))
        self.assertNotIn("F3", self.fire(student(tuition_fees_up_to_date=1, debtor=0,
                                                 scholarship_holder=1)))

    def test_special_needs_fires_p4(self):
        self.assertIn("P4", self.fire(student(special_needs=1)))

    def test_healthy_student_fires_nothing_or_little(self):
        fired = self.fire(
            student(sem1_approved=6, sem2_approved=6, sem1_grade=17.0, sem2_grade=17.2,
                    scholarship_holder=1, tuition_fees_up_to_date=1, debtor=0)
        )
        self.assertEqual(fired, set())

    def test_priority_case_needs_two_categories_and_risk(self):
        s = student(sem1_enrolled=6, sem1_approved=1, sem2_enrolled=6, sem2_approved=0,
                    sem1_grade=8.0, sem2_grade=7.0, tuition_fees_up_to_date=0, debtor=1)
        recommendation = rules.evaluate(s, PREDICTOR.predict(s))
        self.assertTrue(recommendation.is_priority_case)
        self.assertGreaterEqual(len(recommendation.categories), 2)

    def test_every_rule_has_programs_and_feature(self):
        for rule in rules.RULES:
            with self.subTest(rule=rule.id):
                self.assertTrue(rule.programs)
                self.assertTrue(rule.feature)

    def test_reason_text_is_filled_without_placeholders(self):
        s = student(sem1_enrolled=6, sem1_approved=1, sem2_enrolled=6, sem2_approved=0,
                    tuition_fees_up_to_date=0, debtor=1, application_order=5, special_needs=1)
        for matched in rules.evaluate(s, PREDICTOR.predict(s)).matched:
            with self.subTest(rule=matched.rule.id):
                self.assertNotIn("{", matched.reason)


# ---------------------------------------------------------------------------
# 5.6 상담 카드 — 화면 밖으로 나가는 파일
# ---------------------------------------------------------------------------

class TestCaseSheet(unittest.TestCase):
    """내려받은 파일만 봐도 근거와 출처를 알 수 있는가."""

    def setUp(self):
        self.student = student(
            student_id="T-001", sem2_approved=1, sem2_grade=7.9,
            tuition_fees_up_to_date=0, debtor=1, scholarship_holder=0,
        )
        self.result = PREDICTOR.predict(self.student)
        self.recommendation = rules.evaluate(self.student, self.result)

    def _text(self):
        return case_sheet.build_text(self.student, self.result, self.recommendation)

    def test_card_carries_notice_and_source(self):
        """화면 배너는 파일을 따라가지 않는다. 파일이 스스로 밝혀야 한다."""
        text = self._text()
        self.assertIn(case_sheet.FILE_NOTICE, text)
        self.assertIn(self.result.model_name, text)

    def test_card_lists_every_fired_rule(self):
        text = self._text()
        for m in self.recommendation.matched:
            with self.subTest(rule=m.rule.id):
                self.assertIn(f"[{m.rule.id}]", text)

    def test_card_also_lists_rules_that_did_not_fire(self):
        """'확인했으나 해당 없음' 이 빠지면 카드가 근거의 절반만 담는다."""
        text = self._text()
        for rule in self.recommendation.unmatched:
            with self.subTest(rule=rule.id):
                self.assertIn(f"[{rule.id}]", text)

    def test_action_rows_cover_every_program(self):
        rows = case_sheet.action_rows(self.student, self.result, self.recommendation)
        expected = sum(len(m.rule.programs) for m in self.recommendation.matched)
        self.assertEqual(len(rows), expected)
        self.assertTrue(all(r["담당 부서"] for r in rows))

    def test_csv_is_excel_safe(self):
        """BOM 이 없으면 엑셀에서 한글이 깨진다. 실제로 담당자가 여는 것은 엑셀이다."""
        rows = case_sheet.action_rows(self.student, self.result, self.recommendation)
        blob = case_sheet.to_csv(rows, case_sheet.ACTION_FIELDS)
        self.assertTrue(blob.startswith(b"\xef\xbb\xbf"))
        decoded = blob.decode("utf-8-sig")
        self.assertIn("담당 부서", decoded.splitlines()[0])
        self.assertIn(case_sheet.FILE_NOTICE, decoded)

    def test_summary_row_matches_declared_fields(self):
        row = case_sheet.summary_row(self.student, self.result, self.recommendation)
        self.assertEqual(set(row), set(case_sheet.SUMMARY_FIELDS))

    def test_filename_is_ascii(self):
        """발표 PC 브라우저의 한글 파일명 처리에 데모를 걸지 않는다."""
        name = case_sheet.filename("case_sheet", self.student.student_id)
        name.encode("ascii")   # 실패하면 예외로 떨어진다


# ---------------------------------------------------------------------------
# 6. 더미 데이터
# ---------------------------------------------------------------------------
# 5.5 규칙의 수치 근거 · 판정 트레이스
# ---------------------------------------------------------------------------

class TestRuleEvidence(unittest.TestCase):
    """추천의 근거를 화면이 그릴 수 있는 형태로 들고 있는가."""

    def _evaluate(self, **overrides):
        s = student(**overrides)
        return s, rules.evaluate(s, PREDICTOR.predict(s))

    def test_every_rule_is_accounted_for(self):
        """발동 + 미발동 = 규칙 전체. 판정에서 빠지는 규칙이 있으면 트레이스가 거짓말을 한다."""
        for overrides in ({}, {"sem2_approved": 1, "tuition_fees_up_to_date": 0},
                          {"sem2_enrolled": 0}, {"scholarship_holder": 1}):
            with self.subTest(overrides=overrides):
                _, rec = self._evaluate(**overrides)
                self.assertEqual(len(rec.matched) + len(rec.unmatched), len(rules.RULES))

    def test_matched_and_unmatched_do_not_overlap(self):
        _, rec = self._evaluate(sem2_approved=1, debtor=1)
        fired = {m.rule.id for m in rec.matched}
        quiet = {r.id for r in rec.unmatched}
        self.assertEqual(fired & quiet, set())

    def test_fired_rule_evidence_is_on_the_dangerous_side(self):
        """발동한 규칙의 근거값은 반드시 기준선의 위험한 쪽에 있어야 한다.

        조건식과 근거가 따로 놀면 화면이 '기준 안인데 발동했다'를 그리게 된다.
        규칙을 추가할 때 가장 하기 쉬운 실수라 여러 학생으로 훑는다.
        """
        cases = (
            {},
            {"sem2_approved": 1, "sem2_grade": 7.9, "sem1_grade": 10.8},
            {"tuition_fees_up_to_date": 0, "debtor": 1, "scholarship_holder": 0},
            {"application_order": 5, "attendance": 0},
            {"sem1_approved": 6, "sem2_approved": 2},
        )
        for overrides in cases:
            s, rec = self._evaluate(**overrides)
            for m in rec.matched:
                if m.evidence is None:
                    continue
                with self.subTest(rule=m.rule.id, overrides=overrides):
                    e = m.evidence
                    if e.worse == "below":
                        self.assertLess(e.value, e.threshold)
                    else:
                        self.assertGreaterEqual(e.value, e.threshold)

    def test_evidence_value_stays_inside_its_own_scale(self):
        """눈금 범위를 벗어난 값은 막대 밖에 표식을 그린다. ratio 가 잘라 주는지 본다."""
        s, rec = self._evaluate(sem2_approved=1)
        for m in rec.matched:
            if m.evidence is None:
                continue
            with self.subTest(rule=m.rule.id):
                self.assertGreaterEqual(m.evidence.ratio(m.evidence.value), 0.0)
                self.assertLessEqual(m.evidence.ratio(m.evidence.value), 1.0)

    def test_factor_keys_exist_in_the_predictor(self):
        """`Rule.factor_keys` 오타를 잡는다.

        오타가 나도 예외가 나지 않고 **연결선만 조용히 사라진다** — 화면에서
        알아채기 어려운 종류의 사고라 테스트로 막는다.
        """
        known = {term.key for term in _build_terms(student())}
        for rule in rules.RULES:
            for key in rule.factor_keys:
                with self.subTest(rule=rule.id, key=key):
                    self.assertIn(key, known)

    def test_evidence_of_never_raises(self):
        """근거 하나가 깨져도 추천 자체는 나와야 한다."""
        s = student(sem1_enrolled=0, sem2_enrolled=0)
        for rule in rules.RULES:
            with self.subTest(rule=rule.id):
                rules.evidence_of(rule, s)   # 예외가 나면 실패다


# ---------------------------------------------------------------------------
# 5.7 What-if — 시뮬레이션이 예측과 같은 방향을 보는가
# ---------------------------------------------------------------------------

class TestWhatIf(unittest.TestCase):
    """슬라이더를 좋은 쪽으로 밀었는데 위험이 올라가면 발표가 그 자리에서 무너진다."""

    BASE = dict(sem2_enrolled=6, sem2_approved=1, sem2_grade=7.9,
                tuition_fees_up_to_date=0, scholarship_holder=0, debtor=1)

    def test_controls_are_real_student_fields(self):
        """조작 대상 이름이 틀리면 replace() 가 TypeError 로 터진다."""
        from components import whatif

        base = student()
        for name in whatif.CONTROLS:
            with self.subTest(field=name):
                self.assertTrue(hasattr(base, name))

    def test_raising_approval_never_raises_risk(self):
        previous = None
        for approved in range(0, 7):
            s = student(**{**self.BASE, "sem2_approved": approved})
            probability = PREDICTOR.predict(s).dropout_probability
            if previous is not None:
                with self.subTest(approved=approved):
                    self.assertLessEqual(probability, previous + 1e-9)
            previous = probability

    def test_raising_grade_never_raises_risk(self):
        previous = None
        for grade in (0.0, 5.0, 10.0, 15.0, 20.0):
            s = student(**{**self.BASE, "sem2_grade": grade})
            probability = PREDICTOR.predict(s).dropout_probability
            if previous is not None:
                with self.subTest(grade=grade):
                    self.assertLessEqual(probability, previous + 1e-9)
            previous = probability

    def test_improving_every_control_only_removes_rules(self):
        """개선 방향으로 다 밀었을 때 새로 발동하는 규칙이 있으면 규칙 조건이 뒤집힌 것이다."""
        base = student(**self.BASE)
        better = replace(base, sem2_approved=6, sem2_grade=16.0,
                         tuition_fees_up_to_date=1, scholarship_holder=1)

        before = rules.evaluate(base, PREDICTOR.predict(base))
        after = rules.evaluate(better, PREDICTOR.predict(better))

        fired_before = {m.rule.id for m in before.matched}
        fired_after = {m.rule.id for m in after.matched}
        self.assertEqual(fired_after - fired_before, set())
        self.assertLess(len(fired_after), len(fired_before))

    def test_simulation_uses_the_same_predictor_as_the_screen(self):
        """시뮬레이션이 별도 계산을 쓰면 What-if 는 아무것도 증명하지 못한다."""
        s = student(**self.BASE)
        self.assertEqual(
            PREDICTOR.predict(s).dropout_probability,
            PREDICTOR.predict(replace(s)).dropout_probability,
        )


class TestMetricsReport(unittest.TestCase):
    """팀 결과서가 없거나 깨져 있어도 앱이 죽으면 안 된다."""

    def test_missing_file_is_not_an_error(self):
        if not model_metrics.available():
            self.assertIsNone(model_metrics.load())

    def test_schema_hint_is_valid_shape(self):
        """팀에 보여주는 예시가 실제로 우리가 읽는 형식이어야 한다."""
        self.assertIn('"models"', model_metrics.SCHEMA_HINT)
        for key in model_metrics.SCORE_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, model_metrics.SCHEMA_HINT)


class TestRosterLabels(unittest.TestCase):
    def test_labels_line_up_with_rows_or_are_absent(self):
        """라벨이 한 칸이라도 밀리면 성능이 조용히 거짓이 된다."""
        from components.state import cached_roster

        roster = cached_roster()
        if roster.labels:
            self.assertEqual(len(roster.labels), len(roster.rows))
            self.assertTrue(roster.has_labels)
            self.assertTrue(set(roster.labels) <= {0, 1})

    def test_labels_never_reach_the_roster_table(self):
        """정답을 명단 표에 실으면 예측 옆에서 정확도처럼 읽힌다."""
        from components.state import cached_roster

        columns = set(cached_roster().frame.columns)
        for banned in ("target", "정답", "라벨", "label"):
            with self.subTest(column=banned):
                self.assertNotIn(banned, columns)


# ---------------------------------------------------------------------------

class TestDummyData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.students = generate_students()

    def test_count_and_ids(self):
        self.assertEqual(len(self.students), 80)
        self.assertEqual(len({s.student_id for s in self.students}), 80)

    def test_seed_is_fixed(self):
        self.assertEqual(
            [s.student_id for s in generate_students()],
            [s.student_id for s in self.students],
        )
        self.assertEqual(generate_students()[7], self.students[7])

    def test_categories_are_valid(self):
        for s in self.students:
            with self.subTest(student=s.student_id):
                self.assertIn(s.major_field, MAJOR_FIELDS)
                self.assertIn(s.admission_pathway, ADMISSION_PATHWAYS)
                self.assertIn(s.marital_status, range(1, 7))

    def test_value_ranges(self):
        for s in self.students:
            with self.subTest(student=s.student_id):
                self.assertGreaterEqual(s.sem1_approved, 0)
                self.assertLessEqual(s.sem1_approved, s.sem1_enrolled)
                self.assertLessEqual(s.sem2_approved, s.sem2_enrolled)
                self.assertTrue(0 <= s.sem1_grade <= 20)
                self.assertTrue(0 <= s.sem2_grade <= 20)
                self.assertTrue(0 <= s.admission_grade <= 200)

    def test_csv_round_trip_preserves_values(self):
        loaded = load_students()
        self.assertEqual(len(loaded), 80)
        self.assertEqual(loaded[0], self.students[0])

    def test_student_from_mapping_ignores_unknown_keys(self):
        row = dict(self.students[0].to_ui_dict())
        row["삭제된_컬럼"] = "무시되어야 함"
        self.assertEqual(student_from_mapping(row), self.students[0])


# ---------------------------------------------------------------------------
# 7. 전처리기 실물 계약 — 모델이 없어도 지금 검증할 수 있는 가장 중요한 항목
# ---------------------------------------------------------------------------

class TestPreprocessorContract(unittest.TestCase):
    """`models/preprocessor.joblib` 이 우리 입력을 그대로 받아들이는지 실제로 통과시켜 본다."""

    @classmethod
    def setUpClass(cls):
        try:
            import joblib  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:  # pragma: no cover - 실행 환경에 따라 다름
            raise unittest.SkipTest("joblib / pandas 가 없어 전처리기 검증을 건너뜁니다.")

        from utils.schema import PREPROCESSOR_PATH

        if not PREPROCESSOR_PATH.exists():
            raise unittest.SkipTest(f"{PREPROCESSOR_PATH} 가 없습니다.")

        import joblib as jl

        cls.preprocessor = jl.load(PREPROCESSOR_PATH)
        cls.students = generate_students()

    def _frame(self):
        import pandas as pd

        records = [s.to_model_row() for s in self.students]
        return pd.DataFrame(records)[list(model_input_columns())]

    def test_column_names_match_preprocessor(self):
        expected = list(getattr(self.preprocessor, "feature_names_in_", []))
        self.assertEqual(list(self._frame().columns), expected)

    def test_no_unknown_categories(self):
        """OneHotEncoder 는 handle_unknown='ignore' 라 조용히 0으로 만든다.

        조용한 실패가 가장 위험하므로 라벨 문자열을 직접 대조한다.
        """
        frame = self._frame()
        categorical = self.preprocessor.transformers_[1][2]
        known = dict(zip(categorical, self.preprocessor.named_transformers_["cat"].categories_))
        for column in categorical:
            with self.subTest(column=column):
                unknown = set(frame[column].unique()) - set(known[column])
                self.assertEqual(unknown, set(), f"{column} 에 미지 범주가 있습니다: {unknown}")

    def test_transform_produces_expected_feature_count(self):
        from utils.schema import final_feature_count

        matrix = self.preprocessor.transform(self._frame())
        self.assertEqual(matrix.shape[0], len(self.students))
        self.assertEqual(matrix.shape[1], final_feature_count())

    def test_transform_emits_no_warning(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self.preprocessor.transform(self._frame())


# ---------------------------------------------------------------------------
# 8. 시작화면 지구본 — 발표장에서 네트워크가 막혔을 때 쓸 폴백
# ---------------------------------------------------------------------------

class TestGlobeFallback(unittest.TestCase):
    """`USE_PLOTLY_GLOBE = False` 로 바꿨을 때 쓸 SVG 가 실제로 그려지는지."""

    @classmethod
    def setUpClass(cls):
        from components.globe import svg_globe

        cls.svg = svg_globe(340)

    def test_is_a_complete_svg(self):
        self.assertIn("<svg", self.svg)
        self.assertTrue(self.svg.strip().endswith("</svg>"))

    def test_has_no_external_reference(self):
        """폴백의 존재 이유가 '외부 통신 0' 이므로 http 참조가 하나라도 있으면 실패다."""
        for token in ("http://", "https://"):
            with self.subTest(token=token):
                # xmlns 선언만 예외다 (네트워크 요청을 만들지 않는다).
                stripped = self.svg.replace('xmlns="http://www.w3.org/2000/svg"', "")
                self.assertNotIn(token, stripped)

    def test_draws_graticule_and_portugal(self):
        self.assertGreater(self.svg.count("<polyline"), 10)   # 경위선
        self.assertIn("<polygon", self.svg)                   # 포르투갈 외곽선
        self.assertIn("PORTUGAL", self.svg)

    def test_autorotate_script_clears_previous_timer(self):
        """리런마다 스크립트가 다시 실행되므로 이전 타이머를 끄지 않으면 회전이 누적돼 빨라진다."""
        from components.globe import _autorotate_script

        script = _autorotate_script()
        self.assertIn("clearInterval", script)
        self.assertIn("__globeSpinTimer", script)
        self.assertIn("setInterval", script)

    def test_autorotate_step_matches_period(self):
        """한 바퀴 도는 시간이 설정값과 맞는지 (문구와 실제가 어긋나지 않게)."""
        import re

        from components.globe import (
            ROTATION_INTERVAL_MS,
            ROTATION_PERIOD,
            _autorotate_script,
        )

        step = float(re.search(r"var STEP = ([\d.]+);", _autorotate_script()).group(1))
        seconds_per_turn = 360.0 / (step * 1000.0 / ROTATION_INTERVAL_MS)
        self.assertAlmostEqual(seconds_per_turn, ROTATION_PERIOD, delta=0.5)

    def test_geometry_stays_inside_canvas(self):
        """인셋이 캔버스 밖으로 나가면 발표 화면에서 잘린다."""
        import re

        from components.globe import PORTUGAL_OUTLINE, svg_globe  # noqa: F401

        width = 340 * 1.45
        polygon = re.search(r'<polygon points="([^"]+)"', self.svg).group(1)
        for pair in polygon.split():
            x, y = (float(v) for v in pair.split(","))
            self.assertTrue(0 <= x <= width, f"x={x} 가 캔버스를 벗어났습니다.")
            self.assertTrue(0 <= y <= 340, f"y={y} 가 캔버스를 벗어났습니다.")


if __name__ == "__main__":
    unittest.main()
