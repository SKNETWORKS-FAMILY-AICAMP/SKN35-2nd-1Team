"""
화면 테스트 — 실제 Streamlit 스크립트를 실행해 4개 화면이 뜨는지 확인한다.

실행:  cd app && python -m unittest discover -s tests -t .

`streamlit.testing.v1.AppTest` 는 브라우저 없이 앱을 돌린다. 여기서 잡으려는 것은
"예외 없이 렌더되는가" 와 "값이 화면 사이를 제대로 건너가는가" 두 가지다.
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

#: 명단 80명 예측 + 차트가 있어 기본 3초로는 모자랄 때가 있다.
TIMEOUT = 60


def run_page(page: str | None = None) -> AppTest:
    app = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
    if page:
        app.switch_page(page)
    return app.run()


def assert_clean(case: unittest.TestCase, app: AppTest) -> None:
    case.assertEqual(list(app.exception), [], f"화면에서 예외가 발생했습니다: {list(app.exception)}")


class TestHome(unittest.TestCase):
    def test_renders(self):
        app = run_page()
        assert_clean(self, app)

    def test_shows_data_source_and_portability(self):
        body = " ".join(element.value for element in run_page().markdown)
        self.assertIn("포르투갈", body)
        self.assertIn("4,424", body)
        self.assertIn("다른 나라", body)

    def test_prototype_banner_is_visible(self):
        body = " ".join(element.value for element in run_page().markdown)
        self.assertIn("프로토타입 모드", body)


class TestDashboard(unittest.TestCase):
    def test_renders(self):
        app = run_page(PAGE_DASHBOARD)
        assert_clean(self, app)

    def test_has_kpi_and_table(self):
        app = run_page(PAGE_DASHBOARD)
        body = " ".join(element.value for element in app.markdown)
        self.assertIn("전체 학생 수", body)
        self.assertGreaterEqual(len(app.dataframe), 1)


class TestPrediction(unittest.TestCase):
    def test_renders_without_result_first(self):
        app = run_page(PAGE_PREDICTION)
        assert_clean(self, app)
        self.assertTrue(app.info)

    def test_analyse_produces_result(self):
        app = run_page(PAGE_PREDICTION)
        app.button[len(app.button) - 1].click().run()  # 마지막 버튼 = 분석하기
        assert_clean(self, app)
        body = " ".join(element.value for element in app.markdown)
        self.assertIn("중도탈락 위험도", body)

    def test_high_risk_preset_gives_high_probability(self):
        app = run_page(PAGE_PREDICTION)
        self._click_named(app, "복합 위험 사례")
        app.button[len(app.button) - 1].click().run()
        assert_clean(self, app)
        body = " ".join(element.value for element in app.markdown)
        self.assertIn("HIGH", body)

    def test_safe_preset_gives_low_probability(self):
        app = run_page(PAGE_PREDICTION)
        self._click_named(app, "안정 사례")
        app.button[len(app.button) - 1].click().run()
        assert_clean(self, app)
        body = " ".join(element.value for element in app.markdown)
        self.assertIn("LOW", body)

    def test_contradictory_input_warns_but_does_not_crash(self):
        app = run_page(PAGE_PREDICTION)
        app.number_input(key="in_sem1_enrolled").set_value(3).run()
        app.number_input(key="in_sem1_approved").set_value(9).run()
        app.button[len(app.button) - 1].click().run()
        assert_clean(self, app)
        self.assertTrue(app.warning)

    @staticmethod
    def _click_named(app: AppTest, label: str) -> None:
        for button in app.button:
            if button.label == label:
                button.click().run()
                return
        raise AssertionError(f"'{label}' 버튼을 찾지 못했습니다.")


class TestStudents(unittest.TestCase):
    def test_renders(self):
        app = run_page(PAGE_STUDENTS)
        assert_clean(self, app)

    def test_table_is_present(self):
        app = run_page(PAGE_STUDENTS)
        self.assertGreaterEqual(len(app.dataframe), 1)

    def test_filters_exist(self):
        app = run_page(PAGE_STUDENTS)
        self.assertGreaterEqual(len(app.multiselect), 2)
        self.assertGreaterEqual(len(app.checkbox), 1)

    def test_empty_filter_shows_info_not_error(self):
        app = run_page(PAGE_STUDENTS)
        app.multiselect[0].set_value([]).run()
        assert_clean(self, app)
        self.assertTrue(app.info)

    def test_keyword_filter_narrows_result(self):
        app = run_page(PAGE_STUDENTS)
        app.text_input[0].set_value("S001").run()
        assert_clean(self, app)


if __name__ == "__main__":
    unittest.main()
