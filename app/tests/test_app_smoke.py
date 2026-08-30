"""
화면 테스트 — 브라우저 없이 앱을 실제로 돌린다.

    cd app && python -m unittest discover -s tests -t .

`streamlit.testing.v1.AppTest` 는 스크립트를 그대로 실행하므로 여기서 잡으려는 것은
**렌더 중 죽는가**와 **말하지 말아야 할 것을 말하는가** 둘이다. 픽셀은 브라우저에서 본다.

화면은 다섯이다 — 메인 · 대시보드 · 학생 목록 · 집중관리 대상 · 예비학생 예측.
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
PAGE_MANUAL = "views/4_manual.py"

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


#: 예시 버튼(PRESETS)은 2026-08-28 회의 결정으로 화면에서 빠졌다. 규칙이 실제로
#  발동하는 학생이 있어야 근거 화면을 검사할 수 있으므로, 버튼 대신 폼 위젯의
#  session_state 를 직접 심는다 (예전 "HIGH · 복합 위험" 예시와 같은 값).
HIGH_RISK_INPUT: dict[str, object] = {
    "age_at_enrollment": 30, "gender": 1, "major_field": "사회",
    "attendance": 0, "displaced": 1, "admission_pathway": "성인학습자 전형",
    "application_order": 3, "admission_grade": 118.0,
    "tuition_fees_up_to_date": 0, "scholarship_holder": 0, "debtor": 1,
    "sem1_enrolled": 6, "sem1_approved": 3, "sem1_grade": 10.8,
    "sem1_without_evaluations": 1,
    "sem2_enrolled": 6, "sem2_approved": 1, "sem2_grade": 7.9,
    "sem2_without_evaluations": 2,
}


def analysed_manual(app: AppTest | None = None) -> AppTest:
    """예비학생 예측 화면에 고위험 값을 넣고 '위험도 분석' 까지 누른 상태."""
    app = app or run_page(PAGE_MANUAL)
    for key, value in HIGH_RISK_INPUT.items():
        app.session_state[f"in_{key}"] = value
    click(app, "위험도 분석")
    return app


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
    PAGES = (None, PAGE_DASHBOARD, PAGE_STUDENTS, PAGE_RISK, PAGE_MANUAL)

    def test_all_pages_render(self):
        for page in self.PAGES:
            with self.subTest(page=page or "home"):
                assert_clean(self, run_page(page))

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
        """표지 구성 — 브랜드·표제·규모 칩 셋·버튼 셋."""
        app = run_page()
        body = text_of(app)
        self.assertIn("대학생 학업 지속 지원 시스템", body)
        self.assertIn("전체 재학생", body)
        self.assertIn("고위험 HIGH", body)

        # 히어로 안의 행동 버튼 셋 — 대시보드 · 학생 목록 · 고위험군(집중관리).
        # 고위험군 버튼은 인원수를 라벨에 달고 나오므로 부분 일치로 본다.
        labels = " | ".join(b.label for b in app.button)
        for wanted in ("대시보드 바로가기", "학생 분석 시작", "집중관리 대상 확인"):
            with self.subTest(button=wanted):
                self.assertIn(wanted, labels)

    def test_cover_shows_the_roster_scale(self):
        """표지의 숫자는 명단에서 직접 센 값이다 — 지어낸 수치가 아니다."""
        import sys

        sys.path.insert(0, str(APP_ROOT))
        from components.state import cached_roster

        frame = cached_roster().frame
        body = text_of(run_page())
        self.assertIn(f"{len(frame):,}", body)
        self.assertIn(f"{int((frame['위험등급'] == 'HIGH').sum()):,}", body)


# ---------------------------------------------------------------------------
# 대시보드
# ---------------------------------------------------------------------------

class TestDashboard(unittest.TestCase):
    def test_kpi_and_shortcut(self):
        app = run_page(PAGE_DASHBOARD)
        body = text_of(app)
        for wanted in ("전체 재학생", "HIGH 위험", "MEDIUM 위험", "예측 Dropout 비율"):
            with self.subTest(kpi=wanted):
                self.assertIn(wanted, body)
        self.assertIn("즉시 개입 필요 학생", body)     # 경고 띠
        self.assertIn("위험학생목록 보기", [b.label for b in app.button])

    def test_four_charts_are_present(self):
        body = text_of(run_page(PAGE_DASHBOARD))
        for title in ("Feature Importance", "위험요인 카테고리",
                      "전공계열별 Dropout 분포", "재정 · 학업 이슈 비중"):
            with self.subTest(chart=title):
                self.assertIn(title, body)

    def test_chart_types_match_the_values(self):
        """값의 성격에 맞는 그래프인지 — 도넛(비중) · 세로막대 · 가로막대가 모두 있어야 한다.

        도넛은 Plotly 가 아니라 인라인 SVG 다(조각이 차오르는 등장 때문). 마크업에
        남는 클래스가 그 증거다.
        """
        body = text_of(run_page(PAGE_DASHBOARD))
        for marker, what in (("dn-seg", "도넛 조각"), ("dn-legend", "도넛 범례"),
                             ('class="cols"', "세로 막대"), ('class="bars"', "가로 막대")):
            with self.subTest(chart=what):
                self.assertIn(marker, body)

    def test_charts_animate(self):
        """막대와 도넛은 0에서 값까지 차오른다 — 애니메이션 훅이 마크업에 남아 있는지."""
        body = text_of(run_page(PAGE_DASHBOARD))
        self.assertIn("--len:", body)     # 도넛 조각의 목표 길이
        self.assertIn("--fill:", body)    # 세로 막대의 목표 높이

    def test_feature_importance_declares_where_it_came_from(self):
        """🔴 1번 카드는 **어느 쪽 값인지 반드시 밝힌다.**

        학습 결과서가 없으면 거기 서는 것은 모델의 중요도가 아니라, 지금 화면의
        확률을 만든 규칙식이 이 명단에서 실제로 쓴 비중이다. 둘을 같은 얼굴로
        내보내면 없는 모델 해석을 주장하는 셈이라 발표에서 가장 큰 사고가 된다.
        """
        from services import model_metrics

        body = text_of(run_page(PAGE_DASHBOARD))
        self.assertIn("Feature Importance", body)
        if model_metrics.available():
            self.assertIn("학습 결과서의 모델 중요도", body)
        else:
            self.assertIn("현재 예측기(규칙 기반)", body)
            self.assertIn("학습된 모델의 중요도가 아니며", body)

    def test_contribution_profile_is_measured_not_typed(self):
        """규칙 예측기의 기여도는 명단에서 **실측**한 값이다 — 손으로 적은 표가 아니다.

        같은 명단이면 항상 같고, 합이 1 이고, 학생을 빼면 값이 달라져야 한다.
        """
        import sys

        sys.path.insert(0, str(APP_ROOT))
        from components.state import cached_roster
        from services.prediction_service import get_service

        service = get_service()
        if not service.is_dummy:
            self.skipTest("실제 모델이 붙어 있습니다.")
        students = [row.student for row in cached_roster().rows]
        full = service.contribution_profile(students)
        self.assertTrue(full)
        self.assertAlmostEqual(sum(share for _, share in full), 1.0, places=6)
        self.assertEqual(full, service.contribution_profile(students))
        self.assertEqual(full, sorted(full, key=lambda pair: pair[1], reverse=True))
        self.assertNotEqual(full, service.contribution_profile(students[:20]))

    def test_no_placeholder_card_without_the_report(self):
        """결과서가 없으면 그 카드는 **그리지 않는다** — 빈 자리는 미완성으로 읽힌다."""
        from services import model_metrics

        if model_metrics.available():
            self.skipTest("학습 결과서가 이미 들어와 있습니다.")
        body = text_of(run_page(PAGE_DASHBOARD))
        self.assertNotIn("학습 결과서가 아직 없습니다", body)
        self.assertNotIn("모델이 크게 본 변수", body)


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

    def test_toolbar_filters(self):
        """툴바는 셋뿐이다 — 학번 검색 · 전공 계열 · 위험도 버튼(HIGH/MEDIUM/LOW)."""
        app = run_page(PAGE_STUDENTS)
        assert_clean(self, app)
        self.assertIn("HIGH", text_of(app))
        self.assertTrue(app.text_input)
        self.assertEqual(len(app.multiselect), 1)      # 전공 계열
        pills = app.get("button_group")
        self.assertTrue(pills)
        self.assertEqual(len(pills[0].options), 3)     # HIGH · MEDIUM · LOW

    # 원본에 없는 값(이름·학년)을 만든 값이라고 밝히던 캡션은 2026-08-28 회의
    # 결정으로 화면에서 빠졌다. 고지 문구를 검사하던 테스트도 함께 내린다.
    # 이름·학년이 화면 예시용이라는 사실 자체는 여전히 참이다.

    def test_made_up_columns_are_stable(self):
        """새로고침마다 이름이 바뀌면 아무도 그 화면을 믿지 않는다."""
        import sys

        sys.path.insert(0, str(APP_ROOT))
        from utils.display_id import display_name, display_year

        self.assertEqual(display_name("S0042"), display_name("S0042"))
        self.assertEqual(display_year("S0042"), display_year("S0042"))
        self.assertNotEqual(display_name("S0042"), display_name("S0043"))

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
        self.assertIn(sid, body)                   # 팝업 머리의 학번
        self.assertNotIn("학생을 선택하지 않았습니다", body)
        self.assertIn("맞춤 조치 제안", body)      # 조치 탭의 조치 패널

    def test_detail_offers_downloads(self):
        app, _ = self._with_student()
        labels = [b.label for b in app.download_button]
        self.assertTrue(any("상담 카드" in label for label in labels), labels)
        self.assertTrue(any("명단 요약" in label for label in labels), labels)

    def test_manual_input_left_this_screen(self):
        """직접 입력은 여기서 뺐다 — 명단은 **있는 학생을 찾는 곳**이다.

        접힌 폼이 명단 아래 남아 있으면 화면이 길어지기만 한다. 없는 학생을
        넣어 보는 일은 `예비학생 예측` 화면이 가져갔다.
        """
        app = run_page(PAGE_STUDENTS)
        self.assertNotIn("실제 학생 기록이 아닙니다", text_of(app))
        self.assertNotIn("HIGH · 복합 위험", [b.label for b in app.button])


# ---------------------------------------------------------------------------
# 예비학생 예측 — 명단에 없는 학생을 손으로 넣는 화면
# ---------------------------------------------------------------------------

class TestManual(unittest.TestCase):
    def test_form_is_here(self):
        app = run_page(PAGE_MANUAL)
        assert_clean(self, app)
        self.assertIn("위험도 분석", [b.label for b in app.button])

    def test_manual_input_produces_a_result(self):
        app = analysed_manual()
        assert_clean(self, app)
        body = text_of(app)
        self.assertIn("분석 결과", body)
        self.assertIn("무엇을 할 것인가", body)


# ---------------------------------------------------------------------------
# 추천 근거 — 이 제품이 하는 말의 핵심이라 화면에서 사라지면 안 된다
# ---------------------------------------------------------------------------

class TestRecommendationEvidence(unittest.TestCase):
    def _analysed(self) -> AppTest:
        return analysed_manual()

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
        # 범위는 분절 토글(HIGH + MEDIUM / HIGH 만), 나머지 둘은 다중 선택
        self.assertTrue(app.get("button_group"))
        self.assertEqual(len(app.multiselect), 2)     # 위험 영역 · 상담 상태

    def test_scope_widens_the_list(self):
        app = run_page(PAGE_RISK)
        app.get("button_group")[0].set_value("HIGH + MEDIUM").run()
        assert_clean(self, app)
        self.assertIn("HIGH + MEDIUM", text_of(app))

    def test_cards_carry_what_the_team_asked_for(self):
        """표가 아니라 카드다 — 확률 링 · 등급 · 핵심 요인 · 상담 상태가 한 줄에 있다."""
        body = text_of(run_page(PAGE_RISK))
        for marker in ("rl-ring", "rl-tags", "rl-status", "미착수"):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)

    def test_list_is_sorted_by_probability(self):
        """카드에 찍힌 확률이 내림차순인지 — 마크업에서 링의 값을 읽어 확인한다."""
        import re

        body = text_of(run_page(PAGE_RISK))
        values = [int(v) for v in re.findall(r"--p:(\d+);", body)]
        self.assertTrue(values, "확률 링을 찾지 못했습니다")
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
