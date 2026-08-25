"""
로직 테스트 — 화면을 띄우지 않고 계약·계산·규칙을 검증한다.

실행:  cd app && python -m unittest discover -s tests -t .

가장 중요한 것은 `TestPreprocessorContract` 다. 학습된 모델이 없는 지금도
**팀 전처리기가 우리 입력을 그대로 받아들이는지**는 실제로 확인할 수 있다.
"""

from __future__ import annotations

import unittest

from rules import recommendation_rules as rules
from services.dummy_predictor import DummyPredictor
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
# 6. 더미 데이터
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
