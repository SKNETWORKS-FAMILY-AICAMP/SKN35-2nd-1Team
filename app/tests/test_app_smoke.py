"""
화면 테스트 — 브라우저 없이 앱을 실제로 돌린다.

    cd app && python -m unittest discover -s tests -t .

`streamlit.testing.v1.AppTest` 는 스크립트를 그대로 실행하므로 여기서 잡으려는 것은
**렌더 중 죽는가**와 **말하지 말아야 할 것을 말하는가** 둘이다. 픽셀은 브라우저에서 본다.

화면은 넷이다 (팀 초안 기준) — 메인 · 대시보드 · 학생 목록 · 집중관리 대상.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from rules import recommendation_rules as rules

APP_ROOT = Path(__file__).resolve().parent.parent
ENTRYPOINT = str(APP_ROOT / "app.py")

PAGE_DASHBOARD = "views/1_dashboard.py"
PAGE_STUDENTS = "views/2_students.py"
PAGE_RISK = "views/3_risk_list.py"

#: 명단 예측 + 차트가 있어 기본 3초로는 모자란다.
TIMEOUT = 180


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
    PAGES = (None, PAGE_DASHBOARD, PAGE_STUDENTS, PAGE_RISK)

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

        banned = ("Accuracy", "F1 score", "F1-score", "AUC", "Recall", "Precision")
        for page in self.PAGES:
            raw = text_of(run_page(page))
            visible = re.sub(r"<[^>]+>", " ", raw)
            visible = re.sub(r"#[0-9A-Fa-f]{3,8}", " ", visible)
            for word in banned:
                with self.subTest(page=page or "home", word=word):
                    self.assertNotIn(word, visible)

    def test_html_blocks_have_no_blank_line(self):
        """HTML 문자열 안에 빈 줄이 있으면 마크다운이 블록을 끊어 태그가 글자로 샌다."""
        for page in self.PAGES:
            for element in run_page(page).markdown:
                value = str(element.value)
                if "<div" not in value:
                    continue
                with self.subTest(page=page or "home"):
                    self.assertNotIn("\n\n", value.strip())


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

class TestHome(unittest.TestCase):
    def test_core_numbers_and_shortcuts(self):
        """팀 초안의 [메인] 구성 — 타이틀·설명·전체 학생 수·F1·버튼 셋."""
        app = run_page()
        body = text_of(app)
        self.assertIn("Student Dropout", body)
        self.assertIn("전체 학생", body)
        self.assertIn("모델 정확도", body)

        labels = [b.label for b in app.button]
        for wanted in ("대시보드", "학생 목록", "집중관리 대상"):
            with self.subTest(button=wanted):
                self.assertIn(wanted, labels)

    def test_f1_waits_for_the_model(self):
        """🔴 학습 모델이 없는 동안 첫 화면에 성능 숫자를 만들어 내지 않는다."""
        from services import model_metrics

        if model_metrics.available():
            self.skipTest("학습 결과서가 이미 들어와 있습니다.")
        self.assertIn("연결 대기", text_of(run_page()))

    def test_dataset_facts_remain(self):
        body = text_of(run_page())
        self.assertIn("4,424", body)
        self.assertIn("UCI", body)


# ---------------------------------------------------------------------------
# 대시보드
# ---------------------------------------------------------------------------

class TestDashboard(unittest.TestCase):
    def test_kpi_and_shortcut(self):
        app = run_page(PAGE_DASHBOARD)
        body = text_of(app)
        for wanted in ("즉시 개입 필요", "전체 학생", "MEDIUM", "예측 Dropout 비율"):
            with self.subTest(kpi=wanted):
                self.assertIn(wanted, body)
        self.assertIn("위험학생 목록 열기 →", [b.label for b in app.button])

    def test_four_charts_are_present(self):
        body = text_of(run_page(PAGE_DASHBOARD))
        for title in ("위험등급 구성", "위험요인 카테고리",
                      "전공계열별 Dropout 분포", "재정 · 학업 이슈 비중",
                      "Feature Importance"):
            with self.subTest(chart=title):
                self.assertIn(title, body)

    def test_proportions_are_donuts(self):
        """비율 차트는 도넛이다 — 직접 그린 범례가 그 증거다."""
        app = run_page(PAGE_DASHBOARD)
        self.assertIn("dn-legend", text_of(app))
        self.assertGreaterEqual(len(app.get("plotly_chart")), 4)

    def test_feature_importance_waits_for_the_report(self):
        from services import model_metrics

        if model_metrics.available():
            self.skipTest("학습 결과서가 이미 들어와 있습니다.")
        self.assertIn("학습 결과서가 아직 없습니다", text_of(run_page(PAGE_DASHBOARD)))


# ---------------------------------------------------------------------------
# 학생 목록
# ---------------------------------------------------------------------------

class TestStudents(unittest.TestCase):
    def _with_student(self) -> tuple[AppTest, str]:
        """`?student=` 로 상세를 연 화면과 그 학생 ID."""
        import sys

        sys.path.insert(0, str(APP_ROOT))
        from components.state import cached_roster

        sid = cached_roster().rows[0].student.student_id
        app = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
        app.query_params["student"] = sid
        app.switch_page(PAGE_STUDENTS)
        app.run()
        return app, sid

    def test_toolbar_and_counts(self):
        app = run_page(PAGE_STUDENTS)
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("전체 학생", body)
        self.assertIn("HIGH", body)
        # 학번 검색 · 전공 계열 · 위험도 · 집중관리만
        self.assertTrue(app.text_input)
        self.assertEqual(len(app.multiselect), 2)
        self.assertTrue(app.checkbox)

    def test_name_search_is_explained_not_faked(self):
        """🔴 데이터에 없는 것을 있는 척하지 않는다. 이름은 원본에 존재하지 않는다."""
        self.assertIn("학생 이름이 존재하지 않습니다", text_of(run_page(PAGE_STUDENTS)))

    def test_no_match_shows_empty_state_not_error(self):
        app = run_page(PAGE_STUDENTS)
        app.text_input[0].set_value("없는학생ID").run()
        assert_clean(self, app)
        self.assertIn("조건에 맞는 학생이 없습니다", text_of(app))

    def test_major_filter_narrows_the_roster(self):
        app = run_page(PAGE_STUDENTS)
        before = text_of(app)
        app.multiselect[0].set_value(["경영"]).run()
        assert_clean(self, app)
        self.assertNotEqual(text_of(app), before)

    def test_deeplink_opens_detail(self):
        app, sid = self._with_student()
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn(f"{sid} 위험 예측 분석", body)
        self.assertNotIn("학생을 선택하지 않았습니다", body)
        self.assertIn("지금 할 일", body)          # 조치 탭의 상담 카드

    def test_detail_offers_downloads(self):
        app, _ = self._with_student()
        labels = [b.label for b in app.download_button]
        self.assertTrue(any("상담 카드" in label for label in labels), labels)
        self.assertTrue(any("명단 요약" in label for label in labels), labels)

    def test_manual_input_is_absorbed_here(self):
        """예측 화면을 흡수했다 — 명단에 없는 학생도 이 화면에서 넣는다."""
        app = run_page(PAGE_STUDENTS)
        self.assertIn("실제 학생 기록이 아닙니다", text_of(app))
        self.assertIn("HIGH · 복합 위험", [b.label for b in app.button])

    def test_manual_input_produces_a_result(self):
        app = run_page(PAGE_STUDENTS)
        click(app, "HIGH · 복합 위험")
        click(app, "위험도 분석")
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("분석 결과", body)
        self.assertIn("무엇을 할 것인가", body)


# ---------------------------------------------------------------------------
# 추천 근거 — 이 제품이 하는 말의 핵심이라 화면에서 사라지면 안 된다
# ---------------------------------------------------------------------------

class TestRecommendationEvidence(unittest.TestCase):
    def _analysed(self) -> AppTest:
        app = run_page(PAGE_STUDENTS)
        click(app, "HIGH · 복합 위험")
        click(app, "위험도 분석")
        return app

    def test_evidence_meter_is_drawn_for_numeric_rules(self):
        body = text_of(self._analysed())
        self.assertIn("ev-track", body)
        self.assertIn("ev-danger", body)

    def test_rule_trace_covers_every_rule(self):
        app = self._analysed()
        labels = [e.label for e in app.expander]
        trace = next((label for label in labels if "규칙 판정 전체 보기" in label), "")
        self.assertTrue(trace, f"판정 트레이스 expander 가 없습니다: {labels}")
        fired = int(trace.split("발동 ")[1].split("건")[0])
        quiet = int(trace.split("미발동 ")[1].split("건")[0])
        self.assertEqual(fired + quiet, len(rules.RULES))

    def test_factors_link_back_to_rules(self):
        body = text_of(self._analysed())
        self.assertIn("→ RULE", body)
        self.assertIn("모델 요인", body)


# ---------------------------------------------------------------------------
# 집중관리 대상
# ---------------------------------------------------------------------------

class TestRiskList(unittest.TestCase):
    def setUp(self):
        """상담 상태 파일을 임시 경로로 돌린다 — 테스트가 실제 기록을 덮으면 안 된다."""
        import sys
        import tempfile

        sys.path.insert(0, str(APP_ROOT))
        from services import followup

        self._tmp = tempfile.TemporaryDirectory()
        self._saved = (followup.STATE_DIR, followup.STATE_FILE)
        followup.STATE_DIR = Path(self._tmp.name)
        followup.STATE_FILE = Path(self._tmp.name) / "followup.json"

    def tearDown(self):
        from services import followup

        followup.STATE_DIR, followup.STATE_FILE = self._saved
        self._tmp.cleanup()

    def test_renders_with_scope_and_status_filters(self):
        app = run_page(PAGE_RISK)
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("대상 학생", body)
        self.assertIn("미착수", body)
        self.assertTrue(app.radio)                    # 범위 (HIGH 만 / HIGH + MEDIUM)
        self.assertEqual(len(app.multiselect), 2)     # 위험 영역 · 상담 상태

    def test_scope_widens_the_list(self):
        app = run_page(PAGE_RISK)
        app.radio[0].set_value("HIGH + MEDIUM").run()
        assert_clean(self, app)
        self.assertIn("HIGH + MEDIUM", text_of(app))

    def test_columns_the_team_asked_for(self):
        """확률 / 핵심 요인 / 권장 조치 / 상담 진행 상태."""
        frame = run_page(PAGE_RISK).get("dataframe")[0].value
        for column in ("중도탈락 확률(%)", "핵심 요인", "권장 조치", "상담 상태"):
            with self.subTest(column=column):
                self.assertIn(column, list(frame.columns))

    def test_list_is_sorted_by_probability(self):
        frame = run_page(PAGE_RISK).get("dataframe")[0].value
        values = list(frame["중도탈락 확률(%)"])
        self.assertEqual(values, sorted(values, reverse=True))

    def test_status_is_stored_and_read_back(self):
        """상담 상태는 앱이 유일하게 **쓰는** 데이터다. 저장과 복구를 함께 본다."""
        from services import followup

        table = followup.set_status({}, "S0001", "연락함")
        self.assertEqual(table["S0001"], "연락함")
        self.assertEqual(followup.load(), {"S0001": "연락함"})

        # 기본값으로 되돌리면 파일에서 빠진다 — 885명이 통째로 쌓이지 않게.
        table = followup.set_status(table, "S0001", "미착수")
        self.assertEqual(followup.load(), {})

    def test_unknown_status_is_ignored_on_load(self):
        """손으로 고친 파일이 화면을 깨뜨리지 않아야 한다."""
        from services import followup

        followup.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        followup.STATE_FILE.write_text('{"S0002": "이상한값"}', encoding="utf-8")
        self.assertEqual(followup.load(), {})

    def test_broken_file_does_not_raise(self):
        from services import followup

        followup.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        followup.STATE_FILE.write_text("{망가진 json", encoding="utf-8")
        self.assertEqual(followup.load(), {})


if __name__ == "__main__":
    unittest.main()
