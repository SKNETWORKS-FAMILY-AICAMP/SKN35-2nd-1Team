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

APP_ROOT = Path(__file__).resolve().parent.parent
ENTRYPOINT = str(APP_ROOT / "app.py")

PAGE_DASHBOARD = "pages/1_dashboard.py"
PAGE_PREDICTION = "pages/2_prediction.py"
PAGE_STUDENTS = "pages/3_students.py"

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
    PAGES = (None, PAGE_DASHBOARD, PAGE_PREDICTION, PAGE_STUDENTS)

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

    def test_empty_filter_shows_empty_state_not_error(self):
        app = run_page(PAGE_STUDENTS)
        app.multiselect[0].set_value([]).run()
        assert_clean(self, app)
        self.assertIn("조건에 맞는 학생이 없습니다", text_of(app))

    def test_keyword_filter_does_not_crash(self):
        app = run_page(PAGE_STUDENTS)
        app.text_input[0].set_value("S0001").run()
        assert_clean(self, app)


if __name__ == "__main__":
    unittest.main()
