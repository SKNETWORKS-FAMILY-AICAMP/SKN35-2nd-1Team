"""
화면 테스트 — 실제 Streamlit 스크립트를 실행해 4개 화면이 뜨는지 확인한다.

실행:  cd app && python -m unittest discover -s tests -t .

`streamlit.testing.v1.AppTest` 는 브라우저 없이 앱을 돌린다. 여기서 잡으려는 것은
"예외 없이 렌더되는가", "값이 화면 사이를 제대로 건너가는가", 그리고
**"보여주면 안 되는 것을 보여주지 않는가"** 세 가지다.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from rules import recommendation_rules as rules

APP_ROOT = Path(__file__).resolve().parent.parent
ENTRYPOINT = str(APP_ROOT / "app.py")

PAGE_DASHBOARD = "views/1_dashboard.py"
PAGE_PREDICTION = "views/2_prediction.py"
PAGE_STUDENTS = "views/3_students.py"
PAGE_MODEL = "views/4_model.py"
PAGE_STEPS = "views/5_prediction_steps.py"

#: 명단 예측 + 차트가 있어 기본 3초로는 모자란다.
TIMEOUT = 120


def run_page(page: str | None = None) -> AppTest:
    app = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
    if page:
        app.switch_page(page)
    return app.run()


def text_of(app: AppTest) -> str:
    """화면에 나온 마크다운·캡션·경고를 한 덩어리로."""
    parts = [el.value for el in app.markdown]
    parts += [el.value for el in app.caption]
    return " ".join(str(p) for p in parts)


def assert_clean(case: unittest.TestCase, app: AppTest) -> None:
    case.assertEqual(list(app.exception), [], f"화면에서 예외가 발생했습니다: {list(app.exception)}")


def click(app: AppTest, label: str) -> None:
    for button in app.button:
        if button.label == label:
            button.click().run()
            return
    raise AssertionError(f"'{label}' 버튼을 찾지 못했습니다. 있는 것: "
                         f"{[b.label for b in app.button]}")


# ---------------------------------------------------------------------------
# 공통 — 어느 화면에서든 지켜야 하는 것
# ---------------------------------------------------------------------------

class TestEveryPage(unittest.TestCase):
    PAGES = (None, PAGE_DASHBOARD, PAGE_PREDICTION, PAGE_STUDENTS, PAGE_MODEL, PAGE_STEPS)

    def test_all_pages_render(self):
        for page in self.PAGES:
            with self.subTest(page=page or "home"):
                assert_clean(self, run_page(page))

    def test_every_page_declares_prediction_source(self):
        """어느 화면에 있든 지금 보는 숫자가 프로토타입인지 알 수 있어야 한다."""
        for page in self.PAGES:
            with self.subTest(page=page or "home"):
                self.assertIn("Prototype Mode", text_of(run_page(page)))

    def test_no_fabricated_performance_metric(self):
        """디자인 때문에 가짜 성능 수치를 만들지 않았는지.

        태그와 style 속성을 걷어내고 **눈에 보이는 글자만** 본다 —
        안 그러면 색상 hex(`#EDF1F6`)의 `F1` 이 성능지표로 잡힌다.
        """
        import re

        banned = ("정확도", "Accuracy", "F1 score", "F1-score", "AUC", "Recall", "Precision")
        for page in self.PAGES:
            raw = text_of(run_page(page))
            visible = re.sub(r"<[^>]+>", " ", raw)
            visible = re.sub(r"#[0-9A-Fa-f]{3,8}", " ", visible)
            for word in banned:
                with self.subTest(page=page or "home", word=word):
                    self.assertNotIn(word, visible)

    def test_html_blocks_have_no_blank_line(self):
        """HTML 문자열 안에 빈 줄이 있으면 마크다운이 블록을 끊는다.

        그러면 닫는 태그가 화면에 그대로 글자로 나온다 — 실제로 겪은 버그다.
        AppTest 는 렌더 결과가 아니라 **넘긴 원본 문자열**을 돌려주므로,
        결과를 검사하는 대신 **버그를 만드는 조건**을 직접 막는다.
        """
        for page in self.PAGES:
            for index, element in enumerate(run_page(page).markdown):
                value = str(element.value)
                if "<div" not in value and "<table" not in value:
                    continue
                stripped = [line.strip() for line in value.splitlines()]
                with self.subTest(page=page or "home", block=index):
                    self.assertNotIn(
                        "", stripped[1:-1],
                        f"HTML 블록 안에 빈 줄이 있습니다: {value[:120]!r}",
                    )


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

class TestHome(unittest.TestCase):
    def test_hero_and_dataset_facts(self):
        body = text_of(run_page())
        self.assertIn("Student Dropout", body)
        self.assertIn("4,424", body)
        self.assertIn("포르투갈", body)

    def test_pipeline_and_localization_sections(self):
        body = text_of(run_page())
        for token in ("Data", "Risk Signal", "Support Action", "Designed for localization"):
            with self.subTest(token=token):
                self.assertIn(token, body)

    def test_navigation_buttons_exist(self):
        labels = [b.label for b in run_page().button]
        self.assertIn("전체 현황 대시보드", labels)
        self.assertIn("학생 한 명 예측해 보기", labels)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestDashboard(unittest.TestCase):
    def test_hierarchy_and_priority_table(self):
        app = run_page(PAGE_DASHBOARD)
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("즉시 확인 대상", body)     # Level 1
        self.assertIn("위험의 성격", body)        # Level 2
        self.assertIn("먼저 확인할 학생", body)   # Level 3

    def test_charts_are_limited(self):
        """차트를 이유 없이 늘리지 않았는지 — 한 화면에 4개까지."""
        app = run_page(PAGE_DASHBOARD)
        self.assertLessEqual(len(app.get("plotly_chart")), 4)

    def test_counts_are_consistent_with_roster(self):
        """화면 숫자가 명단에서 나온 값인지 (지어낸 값이 아닌지)."""
        import sys

        sys.path.insert(0, str(APP_ROOT))
        from components.state import cached_roster

        frame = cached_roster().frame
        high = int((frame["위험등급"] == "HIGH").sum())
        self.assertIn(f"{high:,}", text_of(run_page(PAGE_DASHBOARD)))


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

class TestPrediction(unittest.TestCase):
    def test_empty_state_before_analysis(self):
        app = run_page(PAGE_PREDICTION)
        assert_clean(self, app)
        self.assertIn("아직 분석하지 않았습니다", text_of(app))

    def test_inputs_are_grouped_into_tabs(self):
        """32개 입력이 한 덩어리로 노출되면 설문지가 된다."""
        app = run_page(PAGE_PREDICTION)
        self.assertGreaterEqual(len(app.tabs), 4)

    def test_analyse_produces_result(self):
        app = run_page(PAGE_PREDICTION)
        click(app, "위험도 분석")
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("분석 결과", body)
        self.assertIn("왜 이 학생이 위험한가", body)

    def test_high_preset_reaches_high_risk(self):
        app = run_page(PAGE_PREDICTION)
        click(app, "HIGH · 복합 위험")
        click(app, "위험도 분석")
        assert_clean(self, app)
        self.assertIn("HIGH", text_of(app))

    def test_low_preset_reaches_low_risk(self):
        app = run_page(PAGE_PREDICTION)
        click(app, "LOW · 안정")
        click(app, "위험도 분석")
        assert_clean(self, app)
        self.assertIn("LOW", text_of(app))

    def test_preset_is_marked_as_example(self):
        """프리셋이 실제 학생 기록처럼 보이면 안 된다."""
        self.assertIn("실제 학생 기록이 아닙니다", text_of(run_page(PAGE_PREDICTION)))

    def test_support_cards_appear_for_risky_student(self):
        app = run_page(PAGE_PREDICTION)
        click(app, "HIGH · 복합 위험")
        click(app, "위험도 분석")
        body = text_of(app)
        self.assertIn("무엇을 할 것인가", body)
        self.assertIn("RULE", body)           # 규칙 카드에 근거 규칙 id 가 붙는다

    def test_contradictory_input_warns_but_does_not_crash(self):
        app = run_page(PAGE_PREDICTION)
        app.number_input(key="in_sem1_enrolled").set_value(3).run()
        app.number_input(key="in_sem1_approved").set_value(9).run()
        click(app, "위험도 분석")
        assert_clean(self, app)
        self.assertTrue(app.warning)

    def test_derived_features_are_shown_not_invented(self):
        app = run_page(PAGE_PREDICTION)
        click(app, "위험도 분석")
        body = text_of(app)
        for name in ("sem1_approval_rate", "financial_risk_score", "grade_change"):
            with self.subTest(name=name):
                self.assertIn(name, body)


# ---------------------------------------------------------------------------
# 추천 근거 — 이 제품이 하는 말의 핵심이라 화면에서 사라지면 안 된다
# ---------------------------------------------------------------------------

class TestRecommendationEvidence(unittest.TestCase):
    def _analysed(self) -> AppTest:
        app = run_page(PAGE_PREDICTION)
        click(app, "HIGH · 복합 위험")
        click(app, "위험도 분석")
        return app

    def test_evidence_meter_is_drawn_for_numeric_rules(self):
        """규칙 카드에 값·기준선 미터가 함께 나오는가."""
        body = text_of(self._analysed())
        self.assertIn("ev-track", body)
        self.assertIn("ev-danger", body)
        self.assertIn("기준", body)

    def test_rule_trace_covers_every_rule(self):
        app = self._analysed()
        labels = [e.label for e in app.expander]
        self.assertTrue(
            any("규칙 판정 전체 보기" in label for label in labels),
            f"판정 트레이스 expander 가 없습니다: {labels}",
        )
        trace = next(label for label in labels if "규칙 판정 전체 보기" in label)
        fired = int(trace.split("발동 ")[1].split("건")[0])
        quiet = int(trace.split("미발동 ")[1].split("건")[0])
        self.assertEqual(fired + quiet, len(rules.RULES))

    def test_factors_link_back_to_rules(self):
        """'왜 위험한가' 와 '무엇을 할 것인가' 가 같은 이름으로 이어지는가."""
        body = text_of(self._analysed())
        self.assertIn("→ RULE", body)
        self.assertIn("모델 요인", body)

    def test_downloads_are_offered(self):
        app = self._analysed()
        labels = [b.label for b in app.download_button]
        self.assertTrue(any("상담 카드" in label for label in labels), labels)
        self.assertTrue(any("조치 목록" in label for label in labels), labels)
        assert_clean(self, app)

    def test_roster_export_is_offered(self):
        app = run_page(PAGE_STUDENTS)
        labels = [b.label for b in app.download_button]
        self.assertTrue(any("명단 요약" in label for label in labels), labels)
        assert_clean(self, app)


# ---------------------------------------------------------------------------
# 모델 성능 — 없는 성능을 주장하지 않는지가 핵심이다
# ---------------------------------------------------------------------------

class TestModelPage(unittest.TestCase):
    def test_page_renders(self):
        assert_clean(self, run_page(PAGE_MODEL))

    def test_dummy_mode_refuses_to_score(self):
        """🔴 회귀 방지 — 학습되지 않은 확률로 혼동행렬을 그리면 없는 성능을 주장하는 것이다."""
        app = run_page(PAGE_MODEL)
        body = text_of(app)
        self.assertIn("학습된 모델이 연결되지 않았습니다", body)
        # 채점 결과에만 나오는 것들이 하나도 없어야 한다.
        for marker in ("놓친 위험학생", "재현율", "정밀도", "상담 대상", "운영 권고"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, body)
        self.assertEqual(list(app.slider), [], "더미 모드에서 임계값 슬라이더가 뜨면 안 됩니다.")

    def test_missing_report_explains_what_to_deliver(self):
        """팀원이 화면만 보고도 무엇을 올리면 되는지 알 수 있어야 한다."""
        import sys

        sys.path.insert(0, str(APP_ROOT))
        from services import model_metrics

        if model_metrics.available():
            self.skipTest("학습 결과서가 이미 들어와 있습니다.")
        app = run_page(PAGE_MODEL)
        self.assertIn("학습 결과서가 아직 없습니다", text_of(app))
        self.assertTrue(
            any("파일 형식" in e.label for e in app.expander),
            [e.label for e in app.expander],
        )


class TestModelPageWithTrainedModel(unittest.TestCase):
    """모델이 붙었을 때만 도는 경로를 **발표 당일에 처음 실행하지 않기 위한** 테스트.

    진짜 모델 파일은 아직 없으므로, 예측은 그대로 두고 `is_dummy` 만 False 인
    대역을 끼워 화면의 채점 경로를 실제로 렌더한다. 여기서 재는 것은 성능이 아니라
    **화면이 죽지 않고 필요한 블록을 그리는가** 다.
    """

    def _reset(self):
        import streamlit as st
        from services.prediction_service import reset_service

        st.cache_resource.clear()
        st.cache_data.clear()
        reset_service(None)

    def test_scoring_path_renders_end_to_end(self):
        import sys

        sys.path.insert(0, str(APP_ROOT))
        import streamlit as st
        from services.dummy_predictor import DummyPredictor
        from services.prediction_service import reset_service

        class StandInTrainedModel(DummyPredictor):
            name = "StandInTrainedModel (테스트 대역)"
            version = "test"
            is_dummy = False

        try:
            st.cache_resource.clear()
            st.cache_data.clear()
            reset_service(StandInTrainedModel())

            app = run_page(PAGE_MODEL)
            assert_clean(self, app)
            body = text_of(app)
            for marker in ("놓친 위험학생", "상담 대상", "이 임계값에서의 판정",
                           "재현율과 정밀도의 교환", "임계값을 어떻게 정하는가"):
                with self.subTest(marker=marker):
                    self.assertIn(marker, body)
            self.assertTrue(app.slider, "임계값 슬라이더가 없습니다.")
        finally:
            self._reset()


# ---------------------------------------------------------------------------
# 예측 화면 A/B — 팀원이 견줘 보는 동안만 둘 다 있다
# ---------------------------------------------------------------------------

class TestPredictionLayouts(unittest.TestCase):
    def test_both_layouts_announce_the_comparison(self):
        """어느 쪽을 보고 있는지, 다른 쪽은 어디 있는지 화면이 말해야 한다."""
        for page, mine, other in ((PAGE_PREDICTION, "한 화면", "B"),
                                  (PAGE_STEPS, "단계형", "A")):
            with self.subTest(page=page):
                body = text_of(run_page(page))
                self.assertIn(mine, body)
                self.assertIn(f"학생 위험 예측 ({other}", body)
                self.assertIn("한쪽은 지웁니다", body)

    def test_steps_layout_starts_at_the_first_step(self):
        app = run_page(PAGE_STEPS)
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("Step 1 / 4", body)
        self.assertIn("학생은 누구인가", body)

    def test_next_advances_and_keeps_earlier_answers(self):
        """🔴 회귀 방지 — 단계형 화면이 밟기 쉬운 가장 큰 함정.

        Streamlit 은 이번 실행에서 그려지지 않은 위젯의 state 를 버린다. 1단계 값을
        위젯 key 에만 두면 2단계로 넘어가는 순간 조용히 기본값으로 돌아간다.
        에러가 나지 않아서 발표 중에는 알아채지 못한다.
        """
        app = run_page(PAGE_STEPS)
        click(app, "HIGH · 복합 위험 예시")
        self.assertEqual(app.session_state["wz_data"]["major_field"], "사회")

        click(app, "다음 →")
        assert_clean(self, app)
        self.assertIn("Step 2 / 4", text_of(app))
        # 1단계에서 넣은 값이 살아 있어야 한다.
        self.assertEqual(app.session_state["wz_data"]["major_field"], "사회")
        self.assertEqual(app.session_state["wz_data"]["attendance"], 0)

    def test_findings_accumulate_as_steps_pass(self):
        """단계를 지날수록 '알아낸 것' 이 늘어야 한다 — 이 흐름의 값어치다."""
        app = run_page(PAGE_STEPS)
        click(app, "HIGH · 복합 위험 예시")
        first = text_of(app)
        self.assertIn("전공", first)
        self.assertNotIn("2학기 이수율", first)   # 아직 학업 단계를 안 지났다

        click(app, "다음 →")
        self.assertIn("2학기 이수율", text_of(app))

    def test_result_step_shows_the_same_output_as_layout_a(self):
        app = run_page(PAGE_STEPS)
        click(app, "HIGH · 복합 위험 예시")
        for _ in range(3):
            click(app, "다음 →")
        click(app, "위험도 분석하기 →")
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("이 판단에 쓰인 사실", body)
        self.assertIn("무엇을 할 것인가", body)
        self.assertIn("지금 할 일", body)          # 상담 카드
        self.assertTrue(
            any("상담 카드" in b.label for b in app.download_button),
            [b.label for b in app.download_button],
        )

    def test_going_back_does_not_lose_answers(self):
        app = run_page(PAGE_STEPS)
        click(app, "HIGH · 복합 위험 예시")
        click(app, "다음 →")
        click(app, "← 이전")
        assert_clean(self, app)
        self.assertIn("Step 1 / 4", text_of(app))
        self.assertEqual(app.session_state["wz_data"]["major_field"], "사회")


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

class TestStudents(unittest.TestCase):
    def test_table_and_toolbar(self):
        app = run_page(PAGE_STUDENTS)
        assert_clean(self, app)
        self.assertGreaterEqual(len(app.dataframe), 1)
        self.assertGreaterEqual(len(app.multiselect), 2)
        self.assertGreaterEqual(len(app.checkbox), 1)

    def test_no_selection_shows_empty_state(self):
        self.assertIn("학생을 선택하지 않았습니다", text_of(run_page(PAGE_STUDENTS)))

    def test_empty_selection_means_all_not_none(self):
        """필터를 비우면 '아무것도 없음' 이 아니라 '전체' 다 (필터 UI 의 일반적 약속)."""
        app = run_page(PAGE_STUDENTS)
        app.multiselect[0].set_value([]).run()
        assert_clean(self, app)
        self.assertNotIn("조건에 맞는 학생이 없습니다", text_of(app))

    def test_no_match_shows_empty_state_not_error(self):
        app = run_page(PAGE_STUDENTS)
        app.text_input[0].set_value("없는학생ID").run()
        assert_clean(self, app)
        self.assertIn("조건에 맞는 학생이 없습니다", text_of(app))

    def test_deeplink_opens_detail_without_table_click(self):
        """대시보드에서 넘어온 ?student=... 는 표를 다시 누르지 않아도 상세가 열려야 한다."""
        import sys

        sys.path.insert(0, str(APP_ROOT))
        from components.state import cached_roster

        sid = cached_roster().rows[0].student.student_id
        app = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
        app.query_params["student"] = sid
        app.switch_page(PAGE_STUDENTS)
        app.run()
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn(f"{sid} 상세 분석", body)
        self.assertNotIn("학생을 선택하지 않았습니다", body)

    def test_whatif_panel_opens_with_the_detail(self):
        """상세를 열면 What-if 가 함께 있어야 한다 — 발표 동선이 여기서 이어진다."""
        import sys

        sys.path.insert(0, str(APP_ROOT))
        from components.state import cached_roster

        sid = cached_roster().rows[0].student.student_id
        app = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
        app.query_params["student"] = sid
        app.switch_page(PAGE_STUDENTS)
        app.run()
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("What-if", body)
        self.assertIn("개입의 효과가 아닙니다", body)   # 인과 오해를 막는 문구
        self.assertIn("아직 바꾼 값이 없습니다", body)  # 조작 전에는 결과를 만들지 않는다

    def test_category_filter_narrows_the_roster(self):
        """부서 단위로 명단을 좁히는 축. 대시보드 차트에서 본 규모를 여기서 연다."""
        app = run_page(PAGE_STUDENTS)
        before = text_of(app)
        # 0=위험등급, 1=예측, 2=주요 위험
        app.multiselect[2].set_value(["경제"]).run()
        assert_clean(self, app)
        self.assertNotEqual(text_of(app), before)

    def test_focus_toggle_is_addressable_from_home(self):
        """시작 화면의 '집중관리 대상부터 보기' 가 켜 두는 상태와 같은 key 인가."""
        app = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
        app.session_state["roster_focus_only"] = True
        app.switch_page(PAGE_STUDENTS)
        app.run()
        assert_clean(self, app)
        self.assertTrue(app.checkbox[0].value)

    def test_keyword_filter_does_not_crash(self):
        app = run_page(PAGE_STUDENTS)
        app.text_input[0].set_value("S0001").run()
        assert_clean(self, app)


if __name__ == "__main__":
    unittest.main()
