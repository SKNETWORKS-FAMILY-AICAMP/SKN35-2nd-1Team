"""
디자인 시스템 — 색·타이포·간격·모서리·그림자·상태를 **여기 한 곳에서만** 정의한다.

화면 파일에 색상 코드나 px 값을 직접 적지 않는다. 발표 직전에 톤을 바꿀 때
한 파일만 고치면 되도록, 그리고 화면 4개가 같은 언어를 쓰도록.

방침
    · **다크 고정.** 시작화면의 캠퍼스 사진과 톤을 잇는다. 대신 어두운 배경에서
      회색으로 뜨는 것을 막으려고 **본문 글자를 밝게(#C2CEDE 이상) 잡고**
      캡션까지 명암비를 실측했다. `.streamlit/config.toml` 에서도 고정한다.
      빔프로젝터가 밝기를 못 내는 방이면 이 파일의 색 표만 되돌리면 된다.
    · **색은 장식이 아니라 신호다.** 위험 3단계와 카테고리 3종에만 색을 쓰고
      나머지는 잉크·중성 그레이로 간다. 색이 많아지면 위험 신호가 묻힌다.
    · **상태를 색으로만 구분하지 않는다.** HIGH/MEDIUM/LOW 는 항상 글자를 함께 쓴다.
    · **그림자는 계층에만.** 모든 카드에 그림자를 넣으면 아무것도 강조되지 않는다.
    · Streamlit 기본 인상은 지우되 **`data-testid` 처럼 비교적 안정된 선택자만** 쓴다.
      DOM 을 깊게 찔러 버전마다 깨지는 CSS 는 만들지 않는다.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# 1. 색 — 잉크 / 중성 / 강조 / 상태
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    # 잉크 (텍스트) — 어두운 면 위에서의 명암비를 카드 배경(#131F33) 기준으로 실측했다.
    "ink": "#EEF3FA",          # 제목·수치      15.6:1
    "ink_soft": "#C2CEDE",     # 본문           10.4:1
    "muted": "#95A4BA",        # 보조·캡션       6.2:1
    "faint": "#7F8DA5",        # 비활성·단위     4.6:1
    # 표면 — 바닥에서 카드로 올라올수록 밝아진다
    "canvas": "#0B1524",       # 페이지 바닥
    "surface": "#131F33",      # 카드
    "raised": "#18243B",       # 카드 안 한 단계 들어간 면
    "line": "#26344B",         # 경계선
    "line_soft": "#1D2A40",    # 옅은 구분선
    # 강조 — 어두운 면 위에서 읽히도록 밝은 블루로 올렸다
    "primary": "#5B9BE8",      # 글자·아이콘용   6.4:1
    "primary_hover": "#7CB2F0",
    "primary_soft": "#16283F", # 옅은 배경(칩·배너)
    "primary_line": "#2C4A73",
    # 버튼처럼 **면을 채우는** 파랑은 흰 글자가 얹히므로 한 단계 어둡게 쓴다
    "primary_fill": "#2B5FA8",
    "primary_fill_hover": "#356FBF",
    # 강조 보조 — 파랑만으로는 화면이 단조롭다. 청록 하나만 더 쓴다.
    # (색을 늘릴수록 위험 신호가 묻히므로 여기서 멈춘다.)
    "accent": "#2CB6BD",
    "accent_soft": "#0E2A31",
    "accent_line": "#1E4B54",
    # 히어로
    "deep": "#0A1E3C",
    "deep_mid": "#143462",
}

#: 위험등급 — 화면 전체(배지·표·차트)에서 같은 값을 쓴다.
#  명암비(카드 #131F33 기준): HIGH 6.4:1 · MEDIUM 8.6:1 · LOW 8.9:1
RISK_COLORS: dict[str, str] = {"HIGH": "#FF7A6B", "MEDIUM": "#E8AC3E", "LOW": "#3FCB96"}
#: 같은 색의 **어두운 면** 버전 — 배지·경보 카드의 바탕이다.
RISK_SOFT: dict[str, str] = {"HIGH": "#2C1A1A", "MEDIUM": "#2B2415", "LOW": "#12291F"}
RISK_LINE: dict[str, str] = {"HIGH": "#5B322C", "MEDIUM": "#5A4620", "LOW": "#1F4C3A"}

#: 위험요인 카테고리 (services.predictor.RISK_CATEGORIES 의 키와 같다)
CATEGORY_COLORS: dict[str, str] = {
    "academic": "#5B9BE8",
    "financial": "#E8AC3E",
    "adaptation": "#2CB6BD",
}

#: 이진 Target (팀 전처리 기준 1=Dropout / 0=Non-Dropout)
CLASS_COLORS: dict[str, str] = {"Dropout": "#FF7A6B", "Non-Dropout": "#3FCB96"}

#: 시작화면 지구본
#  히어로(진한 남색) 위에 올라가므로 배경보다 **어두운 바다 + 밝은 육지**로 잡는다.
#  배경과 톤이 겹치면 구가 아니라 얼룩으로 보인다.
PORTUGAL: dict[str, str] = {
    "ocean": "rgba(10,34,66,.34)",
    "land": "rgba(120,178,240,.34)",
    "border": "rgba(255,255,255,.30)",
    "graticule": "rgba(255,255,255,.18)",
    "highlight": "#FF7A6B",
    "halo": "rgba(255,122,107,.26)",
}

# ---------------------------------------------------------------------------
# 2. 타이포 — 한글·영문이 같이 안정적으로 나오는 시스템 스택만 쓴다
# ---------------------------------------------------------------------------

#: 외부 폰트 CDN 을 쓰지 않는다. 발표장 네트워크가 막히면 폰트가 통째로 바뀐다.
FONT_STACK = (
    "'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, "
    "'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', 'Segoe UI', sans-serif"
)
MONO_STACK = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

#: 타입 스케일 (rem). 단계 사이를 충분히 벌려 계층이 눈에 보이게 한다.
TYPE: dict[str, str] = {
    "display": "2.45rem",
    "h1": "1.72rem",
    "h2": "1.16rem",
    "h3": "0.98rem",
    "body": "0.92rem",
    "secondary": "0.86rem",
    "caption": "0.78rem",
    "label": "0.72rem",
    "kpi": "2.35rem",
    "kpi_sm": "1.62rem",
}

# ---------------------------------------------------------------------------
# 3. 간격 · 모서리 · 선 · 그림자
# ---------------------------------------------------------------------------

SPACE: dict[str, str] = {
    "1": "4px", "2": "8px", "3": "12px", "4": "16px", "5": "20px",
    "6": "24px", "8": "32px", "12": "48px", "16": "64px",
}

RADIUS: dict[str, str] = {"sm": "6px", "md": "10px", "lg": "14px", "pill": "999px"}

SHADOW: dict[str, str] = {
    # 두 단계뿐이다. 어두운 면에서는 그림자보다 **테두리 빛**이 계층을 만든다.
    "raise": "0 1px 2px rgba(0,0,0,.32), 0 4px 14px rgba(0,0,0,.28)",
    "float": "0 4px 12px rgba(0,0,0,.38), 0 18px 40px rgba(0,0,0,.42)",
}


# ---------------------------------------------------------------------------
# 4. CSS
# ---------------------------------------------------------------------------

def _css() -> str:
    c, t, s, r = COLORS, TYPE, SPACE, RADIUS
    return f"""
<style>
  :root {{
    --ink:{c['ink']}; --ink-soft:{c['ink_soft']}; --muted:{c['muted']}; --faint:{c['faint']};
    --canvas:{c['canvas']}; --surface:{c['surface']}; --raised:{c['raised']};
    --line:{c['line']}; --line-soft:{c['line_soft']};
    --primary:{c['primary']}; --primary-soft:{c['primary_soft']}; --primary-line:{c['primary_line']};
    --accent:{c['accent']}; --accent-soft:{c['accent_soft']}; --accent-line:{c['accent_line']};
    --high:{RISK_COLORS['HIGH']}; --medium:{RISK_COLORS['MEDIUM']}; --low:{RISK_COLORS['LOW']};
    --radius-sm:{r['sm']}; --radius-md:{r['md']}; --radius-lg:{r['lg']};
    --shadow-raise:{SHADOW['raise']}; --shadow-float:{SHADOW['float']};
  }}

  /* ── 기본 ──────────────────────────────────────────────────────────── */
  html, body, .stApp, [class*="st-"] {{ font-family: {FONT_STACK}; }}
  html {{ font-size: 20px; }}
  /* 아이콘 폰트까지 덮으면 아이콘이 글자로 깨진다 — 되돌린다 */
  [data-testid="stIconMaterial"],
  span.material-symbols-rounded, span.material-symbols-outlined, .material-icons
    {{ font-family: "Material Symbols Rounded" !important; }}

  /* 평평한 회색 한 장보다, 거의 안 보이는 그라디언트가 화면을 덜 답답하게 만든다 */
  .stApp {{
    color: var(--ink-soft);
    background:
      radial-gradient(900px 420px at 12% -6%, {c['primary_soft']}, transparent 62%),
      radial-gradient(760px 380px at 92% 4%, {c['accent_soft']}, transparent 58%),
      var(--canvas);
    background-attachment: fixed;
  }}
  /* 폭을 가두지 않는다. 발표 화면이 넓을수록 표와 차트가 넓어지는 편이 낫고,
     읽는 폭이 중요한 문장(히어로 설명·페이지 부제)은 각자 max-width 를 갖고 있다. */
  .block-container {{
    padding: {s['6']} {s['8']} {s['16']} {s['8']};
    max-width: 100%;
  }}
  /* 사이드바가 없는 표지에서는 좌우 여백을 조금 더 준다 — 사진이 끝까지 붙으면 답답하다 */
  [data-testid="stAppViewContainer"]:not(:has([data-testid="stSidebar"])) .block-container {{
    padding-left: {s['12']}; padding-right: {s['12']};
  }}

  /* 표지(시작화면)에는 사이드바가 없다. 다른 화면에서 돌아오면 내용 없는 껍데기가
     남으므로, 히어로가 화면에 있을 때만 통째로 감춘다. */
  [data-testid="stAppViewContainer"]:has(.st-key-hero) [data-testid="stSidebar"],
  [data-testid="stAppViewContainer"]:has(.st-key-hero) [data-testid="stExpandSidebarButton"] {{
    display: none !important;
  }}

  /* Streamlit 기본 상단 장식·헤더를 걷어낸다 (발표 화면에 불필요) */
  [data-testid="stDecoration"] {{ display: none; }}
  [data-testid="stHeader"] {{ background: transparent; height: 0; }}
  /* Deploy 버튼·햄버거는 발표 화면에서 "이거 Streamlit 이네" 를 즉시 드러낸다.
     다만 **툴바를 통째로 숨기면 안 된다** — 접힌 사이드바를 다시 여는 버튼이
     그 안에 살아서, 한 번 접으면 영영 못 여는 화면이 된다. 셋만 골라 숨긴다. */
  [data-testid="stToolbarActions"],
  [data-testid="stAppDeployButton"],
  [data-testid="stMainMenu"] {{ display: none !important; }}
  footer, #MainMenu {{ visibility: hidden; }}

  /* st.container(border=True) 를 카드로 — 위젯을 감싸야 할 때 쓰는 유일한 방법이다
     (여는/닫는 태그를 st.markdown 으로 따로 내보내면 감싸지지 않는다) */
  [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
    background: var(--surface);
  }}
  div[data-testid="stVerticalBlockBorderWrapper"][style*="border"] {{
    border-radius: var(--radius-md);
  }}
  [data-testid="stExpanderDetails"] {{ padding-top: {s['2']}; }}

  /* 위젯 사이 기본 간격이 들쭉날쭉해 리듬이 깨진다 */
  [data-testid="stVerticalBlock"] {{ gap: {s['3']}; }}
  [data-testid="stHorizontalBlock"] {{ gap: {s['4']}; }}

  /* ── 타이포 ────────────────────────────────────────────────────────── */
  .ds-eyebrow {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .13em;
    text-transform: uppercase; color: var(--muted);
  }}
  .ds-h1 {{
    font-size: {t['h1']}; font-weight: 700; color: var(--ink);
    letter-spacing: -.022em; line-height: 1.28; margin: 0;
  }}
  .ds-h2 {{
    font-size: {t['h2']}; font-weight: 700; color: var(--ink);
    letter-spacing: -.012em; margin: 0;
  }}
  .ds-h3 {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink); margin: 0; }}
  .ds-body {{ font-size: {t['body']}; color: var(--ink-soft); line-height: 1.68; }}
  .ds-sub {{ font-size: {t['secondary']}; color: var(--muted); line-height: 1.6; }}
  .ds-caption {{ font-size: {t['caption']}; color: var(--muted); line-height: 1.55; }}
  .ds-num {{ font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }}
  .ds-mono {{ font-family: {MONO_STACK}; font-size: {t['caption']}; color: var(--muted); }}

  /* ── 페이지 헤더 ───────────────────────────────────────────────────── */
  .page-head {{
    display: flex; align-items: flex-end; justify-content: space-between;
    gap: {s['6']}; padding-bottom: {s['4']}; margin-bottom: {s['6']};
    border-bottom: 1px solid var(--line);
  }}
  .page-head .titles {{ min-width: 0; }}
  .page-head h1 {{
    font-size: {t['h1']}; font-weight: 700; color: var(--ink);
    letter-spacing: -.022em; margin: {s['1']} 0 0 0; line-height: 1.25;
  }}
  .page-head p {{
    font-size: {t['secondary']}; color: var(--muted);
    margin: {s['2']} 0 0 0; line-height: 1.6; max-width: 74ch;
  }}
  .page-head .meta {{ flex-shrink: 0; text-align: right; }}

  /* ── 섹션 ──────────────────────────────────────────────────────────── */
  .sec {{ margin: {s['8']} 0 {s['4']} 0; }}
  .sec:first-of-type {{ margin-top: {s['4']}; }}
  .sec-row {{ display: flex; align-items: baseline; gap: {s['3']}; }}
  .sec-title {{
    font-size: {t['h2']}; font-weight: 700; color: var(--ink); letter-spacing: -.012em;
    display: inline-flex; align-items: center; gap: {s['3']};
  }}
  /* 제목 앞 작은 색 표식 — 화면마다 같은 자리에서 리듬을 만든다 */
  .sec-title::before {{
    content: ""; width: 4px; height: 15px; border-radius: 2px; flex: none;
    background: linear-gradient(180deg, var(--primary), var(--accent));
  }}
  .sec-rule {{ flex: 1; height: 1px; background: var(--line); }}
  .sec-desc {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['1']}; }}

  /* ── 카드 ──────────────────────────────────────────────────────────── */
  .card {{
    background: var(--surface); border: 1px solid var(--line);
    border-radius: var(--radius-lg); padding: {s['4']} {s['6']};
  }}
  .card-lg {{ padding: {s['6']}; }}
  .card-title {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink); }}
  .card-sub {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['1']}; }}

  /* ── KPI — 계층이 있다. hero 하나, 보조 여럿 ───────────────────────── */
  .kpi-row {{ display: grid; gap: {s['3']}; }}
  .kpi {{
    background: var(--surface); border: 1px solid var(--line);
    border-radius: var(--radius-lg); padding: {s['5']} {s['4']} {s['4']};
    position: relative; overflow: hidden;
  }}
  /* 카드 위 3px 색 띠 — 무엇에 대한 숫자인지 색으로 먼저 읽힌다 */
  .kpi::before {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: var(--accent, var(--primary)); opacity: .92;
  }}
  .kpi .lab {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: var(--muted);
  }}
  .kpi .val {{
    font-size: {t['kpi_sm']}; font-weight: 700; color: var(--ink);
    line-height: 1.15; margin-top: {s['2']};
    font-variant-numeric: tabular-nums; letter-spacing: -.02em;
  }}
  .kpi .val .unit {{ font-size: .58em; font-weight: 600; color: var(--faint); margin-left: 2px; }}
  .kpi .cap {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['1']}; }}

  /* 아이콘이 붙은 KPI — 숫자가 넷 늘어설 때 무엇에 대한 값인지 먼저 읽힌다 */
  .kpi.has-icon {{ display: flex; align-items: center; gap: {s['4']}; }}
  .kpi.has-icon .ico {{
    width: 44px; height: 44px; border-radius: var(--radius-md); flex: none;
    display: flex; align-items: center; justify-content: center; font-size: 23px;
    color: var(--accent); background: color-mix(in srgb, var(--accent) 16%, {c['surface']});
    border: 1px solid color-mix(in srgb, var(--accent) 34%, {c['surface']});
  }}
  .kpi.has-icon .kpi-body {{ min-width: 0; }}
  .kpi.has-icon .val {{ margin-top: 0; }}

  /* 경보 줄 — 지금 움직여야 하는 이유 하나 */
  .alert-bar {{
    display: flex; align-items: center; gap: {s['4']};
    background: var(--s); border: 1px solid var(--l); border-left: 3px solid var(--c);
    border-radius: var(--radius-lg); padding: {s['4']} {s['5']};
  }}
  .alert-bar .ico {{
    width: 42px; height: 42px; border-radius: var(--radius-md); flex: none;
    display: flex; align-items: center; justify-content: center; font-size: 22px;
    color: {c['canvas']}; background: var(--c);
  }}
  .alert-bar .t {{ display: flex; flex-direction: column; }}
  .alert-bar .n {{ font-size: {t['h3']}; font-weight: 700; color: var(--c); }}
  .alert-bar .d {{ font-size: {t['secondary']}; color: var(--ink-soft); margin-top: 2px; }}
  /* 버튼은 줄을 나눠 옆에 세우지 않고 **줄 안쪽 오른쪽**에 앉힌다. 칸을 나누면
     경보 줄이 그만큼 짧아져서 "화면을 가로지르는 한 줄"이 아니게 된다. Streamlit
     위젯은 HTML 안에 못 넣으므로 컨테이너째 겹쳐 놓고, 줄은 그만큼 오른쪽을
     비워 글이 버튼 밑으로 들어가지 않게 한다. */
  .st-key-dash_alert {{ position: relative; }}
  /* Streamlit 의 마크다운 컨테이너는 margin-bottom: -16px 를 달고 나온다. 그래서 줄을
     감싼 상자가 줄보다 16px 짧아지고, 그 절반(8px)만큼 top:50% 가운데가 위로 빗나간다.
     이 줄에서만 그 음수 여백을 지운다 — 상자와 줄의 높이가 같아야 가운데가 맞는다. */
  .st-key-dash_alert [data-testid="stMarkdownContainer"] {{ margin-bottom: 0; }}
  /* 높이는 **패딩으로** 만든다. min-height 로 늘리면 줄을 감싼 컨테이너는 그대로라
     줄이 아래로 흘러넘치고, 그 어긋난 만큼 가운데 정렬(top:50%)도 빗나간다. */
  .st-key-dash_alert .alert-bar {{ padding: {s['6']} 252px {s['6']} {s['5']}; }}
  .st-key-dash_alert [data-testid="stElementContainer"]:has(.stButton) {{
    position: absolute; right: {s['5']}; top: 50%; transform: translateY(-50%);
    width: auto; margin: 0;
  }}
  /* 버튼 색은 줄의 색을 따른다 — 경보와 다른 색이면 둘이 남남으로 읽힌다 */
  /* 아래쪽 전역 규칙(.stButton > button[kind="primary"])과 특이도가 같으면 나중에
     오는 그쪽이 이긴다 — 여기서도 [kind] 를 붙여 한 단계 위로 올린다. */
  .st-key-dash_alert .stButton > button[kind="primary"] {{
    padding: 12px {s['5']}; font-weight: 700; white-space: nowrap;
    background: var(--high); border: 1px solid var(--high); color: {c['canvas']};
  }}
  .st-key-dash_alert .stButton > button[kind="primary"]:hover {{
    background: color-mix(in srgb, var(--high) 82%, #fff);
    border-color: color-mix(in srgb, var(--high) 82%, #fff); color: {c['canvas']};
  }}
  .st-key-dash_alert .stButton > button[kind="primary"] p {{ color: {c['canvas']}; }}
  .st-key-dash_alert .stButton > button[kind="primary"]:focus-visible {{
    outline: 2px solid var(--ink); outline-offset: 2px;
  }}
  /* 폭이 좁으면 겹칠 수밖에 없다 — 그때만 줄 아래로 내려 앉힌다 */
  @media (max-width: 1000px) {{
    .st-key-dash_alert .alert-bar {{ padding-right: {s['5']}; }}
    .st-key-dash_alert [data-testid="stElementContainer"]:has(.stButton) {{
      position: static; transform: none; width: 100%; margin-top: {s['3']};
    }}
  }}

  /* 차트 카드 넷은 좌우 높이를 맞추고, 바닥을 한 겹 밝게 띄운다 — 그래프 영역이
     아니라 **카드(큰 네모) 전체**다. 배경은 카드 자신에게 준다: 이 버전의 Streamlit 은
     테두리를 이 요소에 직접 그리고 BorderWrapper 를 더 이상 두지 않는다. */
  [class*="st-key-dash_c"] {{
    min-height: 470px;
    background: rgba(255,255,255,.1);
  }}

  /* ── 명단 표 (직접 그린다) ─────────────────────────────────────────── */
  /* `st.dataframe` 은 행 선택을 켜면 체크박스 열이 따라붙는다. 담당자가 하는 일은
     고르는 게 아니라 **여는 것**이라 그 한 칸이 군더더기다. 직접 그리고 덮는다. */
  .rt-head, .rt-row {{
    display: grid; grid-template-columns: 1.1fr 1.1fr 1.6fr .8fr .9fr;
    align-items: center; gap: {s['3']}; padding: {s['3']} {s['4']};
  }}
  .rt-head {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: var(--faint);
    border-bottom: 1px solid var(--line);
  }}
  .rt-row {{
    font-size: {t['secondary']}; color: var(--ink-soft);
    border-bottom: 1px solid var(--line-soft);
    transition: background .14s ease;
  }}
  [class*="st-key-rt_row_"] {{ position: relative; }}
  [class*="st-key-rt_row_"]:hover .rt-row {{ background: var(--raised); }}
  .rt-row .nm {{ color: var(--ink); font-weight: 600; }}
  .rt-row .g {{ text-align: right; }}
  .rt-head .g {{ text-align: right; }}
  .rt-row .lv {{
    display: inline-block; font-size: {t['label']}; font-weight: 800; letter-spacing: .05em;
    color: var(--c); background: color-mix(in srgb, var(--c) 16%, {c['surface']});
    border: 1px solid color-mix(in srgb, var(--c) 38%, {c['surface']});
    border-radius: {r['pill']}; padding: 2px {s['2']};
  }}
  /* 줄 전체가 버튼이다 (집중관리 카드와 같은 방식) */
  [class*="st-key-rt_row_"] [data-testid="stElementContainer"]:has(.stButton) {{
    position: absolute !important; inset: 0 !important; height: auto !important;
    margin: 0 !important; z-index: 2;
  }}
  [class*="st-key-rt_row_"] .stButton {{
    position: static !important; width: 100%; height: 100%; margin: 0;
  }}
  [class*="st-key-rt_row_"] .stButton > button {{
    width: 100%; height: 100%; opacity: 0; padding: 0; border: none;
    background: transparent; cursor: pointer;
  }}
  [class*="st-key-rt_row_"] .stButton > button:focus-visible {{
    opacity: 1; background: rgba(91,155,232,.12); border: 2px solid var(--primary);
    color: var(--ink);
  }}

  /* hero KPI — 화면에서 가장 먼저 읽혀야 하는 하나 */
  .kpi-hero {{
    background: linear-gradient(180deg, var(--surface), var(--raised));
    border: 1px solid var(--line);
    border-left: 3px solid var(--accent, var(--primary));
    box-shadow: var(--shadow-raise);
    border-radius: var(--radius-lg); padding: {s['6']};
    /* 옆 열이 두 줄이면 빈 공간이 생긴다 — 높이를 채워 카드가 떠 보이지 않게 한다 */
    height: 100%; display: flex; flex-direction: column; justify-content: center;
  }}
  .kpi-hero .lab {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: var(--accent, var(--primary));
  }}
  .kpi-hero .val {{
    font-size: {t['kpi']}; font-weight: 700; color: var(--ink);
    line-height: 1.05; margin-top: {s['2']};
    font-variant-numeric: tabular-nums; letter-spacing: -.03em;
  }}
  .kpi-hero .val .unit {{ font-size: .42em; font-weight: 600; color: var(--faint); margin-left: 3px; }}
  .kpi-hero .cap {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['2']}; }}

  /* 지표 옆 미니 막대 — 비율을 숫자와 함께 보여준다 */
  .kpi-bar {{ height: 3px; border-radius: 2px; background: var(--line-soft); margin-top: {s['3']}; }}
  .kpi-bar > span {{ display: block; height: 100%; border-radius: 2px; background: var(--accent, var(--primary)); }}

  /* ── 상태 배지 — 색 + 글자. 색만으로 구분하지 않는다 ───────────────── */
  .pill {{
    display: inline-flex; align-items: center; gap: {s['1']};
    padding: 2px {s['2']}; border-radius: var(--radius-sm);
    font-size: {t['label']}; font-weight: 700; letter-spacing: .04em;
    border: 1px solid transparent; white-space: nowrap;
  }}
  .pill.lg {{ font-size: {t['caption']}; padding: {s['1']} {s['3']}; }}
  .pill .dot {{ width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }}
  .pill-HIGH   {{ color: var(--high);   background: {RISK_SOFT['HIGH']};   border-color: {RISK_LINE['HIGH']}; }}
  .pill-MEDIUM {{ color: var(--medium); background: {RISK_SOFT['MEDIUM']}; border-color: {RISK_LINE['MEDIUM']}; }}
  .pill-LOW    {{ color: var(--low);    background: {RISK_SOFT['LOW']};    border-color: {RISK_LINE['LOW']}; }}
  .pill-neutral{{ color: var(--muted);  background: var(--raised);         border-color: var(--line); }}
  .pill-focus  {{ color: var(--high);   background: {RISK_SOFT['HIGH']};   border-color: {RISK_LINE['HIGH']}; }}

  /* ── 배너 ──────────────────────────────────────────────────────────── */
  .banner {{
    display: flex; gap: {s['3']}; align-items: flex-start;
    border: 1px solid var(--bd, var(--primary-line)); background: var(--bg, var(--primary-soft));
    border-radius: var(--radius-md); padding: {s['3']} {s['4']};
    font-size: {t['secondary']}; color: var(--ink-soft); line-height: 1.6;
  }}
  .banner .mark {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    color: var(--fg, var(--primary)); border: 1px solid var(--bd, var(--primary-line));
    border-radius: var(--radius-sm); padding: 2px {s['2']}; background: var(--surface);
    white-space: nowrap; flex: none; margin-top: 1px;
  }}
  .banner b {{ color: var(--fg, var(--primary)); }}

  /* ── 도넛 (인라인 SVG) ─────────────────────────────────────────────── */
  /* 조각이 시계방향으로 차오른다. dasharray 를 0 → 목표 길이로 애니메이션하는 것이
     전부라 라이브러리가 필요 없다. */
  .dn {{
    position: relative; width: var(--size, 250px); max-width: 100%;
    aspect-ratio: 1; margin: {s['2']} auto {s['4']};
  }}
  .dn svg {{ width: 100%; height: 100%; display: block; overflow: visible; }}
  .dn .dn-seg {{
    stroke-linecap: butt;
    animation: dn-grow .85s cubic-bezier(.2,.75,.3,1) both var(--d, 0s);
  }}
  .dn .dn-seg:hover {{ filter: brightness(1.06); }}
  .dn-center {{
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; pointer-events: none;
  }}
  .dn-center b {{
    font-size: 1.72rem; font-weight: 800; color: var(--ink); letter-spacing: -.03em;
    font-variant-numeric: tabular-nums; line-height: 1.1;
    animation: ds-rise .4s ease-out both .25s;
  }}
  .dn-center span {{ font-size: {t['caption']}; color: var(--muted); margin-top: 2px; }}

  /* ── 세로 막대 ─────────────────────────────────────────────────────── */
  /* 항목이 적고 라벨이 짧을 때. 막대는 바닥에서 위로 자란다. */
  .cols {{
    display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
    align-items: end; gap: {s['3']}; padding: {s['4']} 0 0;
  }}
  .cols .col {{ display: flex; flex-direction: column; align-items: center; gap: {s['2']}; }}
  .cols .v {{
    font-size: {t['caption']}; font-weight: 700; color: var(--ink-soft);
    font-variant-numeric: tabular-nums; white-space: nowrap;
    animation: ds-rise .4s ease-out both var(--d, 0s);
  }}
  .cols .track {{
    display: flex; align-items: flex-end; justify-content: center;
    width: 100%; max-width: 76px; height: var(--h, 176px);
    background: var(--line-soft); border-radius: var(--radius-sm);
    overflow: hidden;
  }}
  .cols .bar {{
    display: block; width: 100%; height: var(--fill, 0%);
    background: var(--c, var(--primary));
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    animation: dn-raise .7s cubic-bezier(.2,.75,.3,1) both var(--d, 0s);
  }}
  .cols .lab {{
    font-size: {t['caption']}; color: var(--muted); font-weight: 600;
    text-align: center; line-height: 1.35;
  }}
  .cols .col:hover .lab {{ color: var(--ink); }}

  /* ── 도넛 범례 ─────────────────────────────────────────────────────── */
  /* Plotly 범례는 이 높이에서 눌려 잘린다. 직접 그리면 값·비율을 같이 적을 수 있다. */
  .dn-legend {{ margin-top: -{s['2']}; }}
  .dn-item {{
    display: flex; align-items: center; gap: {s['2']};
    padding: {s['1']} 0; font-size: {t['secondary']};
    border-bottom: 1px solid var(--line-soft);
  }}
  .dn-item:last-child {{ border-bottom: none; }}
  .dn-item .sw {{ width: 10px; height: 10px; border-radius: 3px; flex: none; }}
  .dn-item .lb {{ color: var(--ink); font-weight: 600; }}
  .dn-item .vl {{ margin-left: auto; color: var(--ink-soft); }}
  .dn-item .pc {{
    width: 40px; text-align: right; color: var(--muted); font-weight: 700;
  }}

  /* ── 집중관리 명단 카드 ────────────────────────────────────────────── */
  /* 표 대신 카드다. 한 줄에서 알아야 하는 넷 — 확률 · 등급 · 무엇이 위험한가 ·
     지금 어디까지 갔는가 — 을 격자 없이 읽히게 놓는다. */
  [class*="st-key-rl_row_"] {{ position: relative; margin-bottom: {s['2']}; }}
  .rl-card {{
    display: grid; grid-template-columns: 78px minmax(190px, 1fr) 3fr auto;
    align-items: center; gap: {s['4']};
    background: var(--surface); border: 1px solid var(--line);
    border-radius: var(--radius-lg); padding: {s['4']} {s['5']};
    transition: border-color .15s ease, background .15s ease, transform .15s ease;
  }}
  [class*="st-key-rl_row_"]:hover .rl-card {{
    border-color: var(--primary-line); background: var(--raised);
  }}
  /* 확률 링 — conic-gradient 로 그린다 (SVG 는 Streamlit 이 걸러낸다) */
  .rl-ring {{
    position: relative; width: 60px; height: 60px; border-radius: 50%;
    background: conic-gradient(var(--c) calc(var(--p) * 1%), var(--line-soft) 0);
    display: flex; align-items: center; justify-content: center;
  }}
  .rl-ring::after {{
    content: ""; position: absolute; inset: 7px; border-radius: 50%; background: var(--surface);
  }}
  [class*="st-key-rl_row_"]:hover .rl-ring::after {{ background: var(--raised); }}
  .rl-ring span {{
    position: relative; z-index: 1; font-size: {t['caption']}; font-weight: 800;
    color: var(--ink); font-variant-numeric: tabular-nums;
  }}
  .rl-who .n {{
    display: flex; align-items: center; gap: {s['2']};
    font-size: {t['h3']}; font-weight: 700; color: var(--ink);
  }}
  .rl-who .lv {{
    font-size: {t['label']}; font-weight: 800; letter-spacing: .06em;
    color: var(--c); background: color-mix(in srgb, var(--c) 18%, {c['surface']});
    border: 1px solid color-mix(in srgb, var(--c) 40%, {c['surface']});
    border-radius: {r['pill']}; padding: 2px {s['2']};
  }}
  .rl-who .d {{ font-size: {t['caption']}; color: var(--muted); margin-top: 3px; }}
  .rl-tags .k {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: var(--faint);
  }}
  .rl-tags .t {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }}
  .rl-tags .tag {{
    font-size: {t['caption']}; font-weight: 600; padding: 3px {s['2']};
    border-radius: var(--radius-sm); white-space: nowrap;
  }}
  /* 위험요인은 경고색, 권장 조치는 중립색 — 문제와 처방을 색으로 가른다 */
  .rl-tags .tag.f {{
    color: {RISK_COLORS['MEDIUM']}; background: {RISK_SOFT['MEDIUM']};
    border: 1px solid {RISK_LINE['MEDIUM']};
  }}
  /* 조치는 처방이다 — 문제(경고색)와 다른 색으로 둔다 */
  .rl-tags .tag.a {{
    color: {c['accent']}; background: {c['accent_soft']}; border: 1px solid {c['accent_line']};
  }}
  .rl-status {{ justify-self: end; }}

  /* 카드 전체가 버튼이다 — 투명하게 덮어 어디를 눌러도 팝업이 열린다.
     Streamlit 이 위젯마다 씌우는 stElementContainer 가 position:relative 라,
     그 안에서 inset:0 을 잡으면 **버튼 한 줄 높이**밖에 못 덮는다. 컨테이너째 덮는다. */
  [class*="st-key-rl_row_"] [data-testid="stElementContainer"]:has(.stButton) {{
    position: absolute !important; inset: 0 !important; height: auto !important;
    margin: 0 !important; z-index: 2;
  }}
  [class*="st-key-rl_row_"] .stButton {{
    position: static !important; width: 100%; height: 100%; margin: 0;
  }}
  [class*="st-key-rl_row_"] .stButton > button {{
    width: 100%; height: 100%; opacity: 0; padding: 0; border: none;
    background: transparent; cursor: pointer;
  }}
  /* 키보드로 왔을 때는 보이게 — 안 보이는 버튼에 초점이 가면 길을 잃는다 */
  [class*="st-key-rl_row_"] .stButton > button:focus-visible {{
    opacity: 1; background: rgba(91,155,232,.12); border: 2px solid var(--primary);
    border-radius: var(--radius-lg); color: var(--ink);
  }}

  .rl-page {{
    font-size: {t['secondary']}; font-weight: 700; color: var(--ink-soft);
    padding: 8px {s['3']}; font-variant-numeric: tabular-nums;
  }}

  /* 팝업 안 상담 상태 */
  .dlg-status {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: var(--faint); margin-top: {s['4']};
  }}

  /* ── 위험 미터 — 속도계 대신 구간이 보이는 가로 미터 ───────────────── */
  .meter-val {{ display: flex; align-items: baseline; gap: {s['3']}; }}
  .meter-val .n {{
    font-size: 3.1rem; font-weight: 700; line-height: 1; letter-spacing: -.04em;
    font-variant-numeric: tabular-nums; color: var(--accent, var(--ink));
  }}
  .meter-val .n .p {{ font-size: .42em; font-weight: 600; margin-left: 2px; }}
  .meter-cap {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['2']}; }}
  .meter {{ margin-top: {s['4']}; }}
  .meter .track {{
    position: relative; height: 10px; border-radius: 5px; overflow: hidden;
    display: flex; background: var(--line-soft);
  }}
  .meter .zone {{ height: 100%; opacity: .55; }}
  .meter .mark {{
    position: absolute; top: -5px; width: 3px; height: 20px; border-radius: 2px;
    background: var(--ink); box-shadow: 0 0 0 2px var(--surface);
  }}
  .meter .ticks {{
    display: flex; justify-content: space-between; margin-top: {s['2']};
    font-size: {t['label']}; color: var(--faint); font-variant-numeric: tabular-nums;
  }}
  .meter .zones {{
    display: flex; justify-content: space-between; margin-top: {s['1']};
    font-size: {t['label']}; font-weight: 700; letter-spacing: .06em;
  }}

  /* ── 위험요인 막대 ─────────────────────────────────────────────────── */
  .factor {{ padding: {s['3']} 0; border-bottom: 1px solid var(--line-soft); }}
  .factor:last-child {{ border-bottom: none; }}
  .factor-top {{ display: flex; align-items: baseline; gap: {s['2']}; }}
  .factor-name {{ font-size: {t['body']}; font-weight: 600; color: var(--ink); }}
  .factor-pct {{
    margin-left: auto; font-size: {t['secondary']}; font-weight: 700; color: var(--ink-soft);
    font-variant-numeric: tabular-nums;
  }}
  .factor-detail {{ font-size: {t['caption']}; color: var(--muted); margin-top: 2px; }}
  .factor-track {{ height: 6px; border-radius: 3px; background: var(--line-soft); margin-top: {s['2']}; }}
  .factor-fill {{ height: 100%; border-radius: 3px; }}

  /* ── 지원 액션 카드 ────────────────────────────────────────────────── */
  .act {{
    background: var(--surface); border: 1px solid var(--line);
    border-radius: var(--radius-md); padding: {s['4']}; height: 100%;
    display: flex; flex-direction: column; gap: {s['2']};
    transition: border-color .15s ease, box-shadow .15s ease;
  }}
  .act:hover {{ border-color: var(--primary-line); box-shadow: var(--shadow-raise); }}
  .act-head {{ display: flex; align-items: center; gap: {s['2']}; flex-wrap: wrap; }}
  .act-title {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink); }}
  .act-reason {{
    font-size: {t['caption']}; color: var(--ink-soft); line-height: 1.6;
    background: var(--raised); border-left: 2px solid var(--accent, var(--primary));
    padding: {s['2']} {s['3']}; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  }}
  .act-prog {{ font-size: {t['secondary']}; color: var(--ink); padding: {s['1']} 0; }}
  .act-prog .owner {{ font-size: {t['caption']}; color: var(--muted); margin-left: {s['1']}; }}
  .act-prog .todo {{ display: block; font-size: {t['caption']}; color: var(--ink-soft); margin-top: 1px; }}
  .act-feat {{
    padding-top: {s['2']}; margin-top: {s['2']}; border-top: 1px dashed var(--line);
    font-family: {MONO_STACK}; font-size: {t['label']}; color: var(--faint);
  }}
  /* 카테고리 카드 안에서 규칙 여러 개를 세로로 쌓는다 */
  .act-item + .act-item {{
    margin-top: {s['3']}; padding-top: {s['3']}; border-top: 1px solid var(--line-soft);
  }}
  .act-item .act-title {{ font-size: {t['secondary']}; }}

  /* ── 상담 카드 ────────────────────────────────────────────────── */
  /* 담당자가 **그대로 캡처해서 쓸 수 있는 한 장**이 목표다. 그래서 본문보다
     강한 위계를 주고(띄 + 큰 숫자), 카드 밖으로 나가도 뜻이 통하도록
     출처와 면책을 카드 안에 넣는다. */
  .rc {{
    /* 폭을 묶어야 '카드' 로 읽힌다 — 화면 폭을 다 쓰면 그냥 한 구획이 된다.
       캡처해서 메신저에 붙이는 용도라 세로로 긴 비율이 맞다. */
    max-width: 660px;
    border: 1px solid var(--line); border-radius: var(--radius-lg);
    background: var(--surface); overflow: hidden; box-shadow: var(--shadow-raise);
  }}
  .rc-band {{
    display: flex; align-items: center; gap: {s['2']}; flex-wrap: wrap;
    padding: {s['3']} {s['4']}; background: var(--accent-soft, var(--raised));
    border-bottom: 1px solid var(--accent-line, var(--line));
  }}
  .rc-band .who {{
    margin-left: auto; font-size: {t['caption']}; color: var(--muted);
  }}
  .rc-body {{ padding: {s['4']} {s['4']} {s['3']}; }}
  .rc-id {{
    font-size: 1.5rem; font-weight: 800; letter-spacing: -.01em; color: var(--ink);
    font-variant-numeric: tabular-nums;
  }}
  .rc-sub {{ font-size: {t['caption']}; color: var(--muted); margin-top: 2px; }}
  .rc-prob {{ display: flex; align-items: baseline; gap: {s['3']}; margin-top: {s['4']}; }}
  .rc-prob .n {{
    font-size: 2.8rem; font-weight: 800; line-height: 1; color: var(--accent);
    font-variant-numeric: tabular-nums;
  }}
  .rc-prob .n .p {{ font-size: .38em; font-weight: 700; margin-left: 2px; }}
  .rc-prob .l {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: var(--muted);
  }}
  .rc-bar {{
    height: 6px; border-radius: 3px; background: var(--line-soft); margin-top: {s['3']};
  }}
  .rc-bar > span {{ display: block; height: 100%; border-radius: 3px; background: var(--accent); }}
  .rc-stats {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: {s['3']};
    margin-top: {s['4']}; padding-top: {s['4']}; border-top: 1px solid var(--line-soft);
  }}
  .rc-stats .k {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: var(--muted);
  }}
  .rc-stats .v {{
    font-size: 1.05rem; font-weight: 700; color: var(--ink); margin-top: 3px;
    font-variant-numeric: tabular-nums;
  }}
  .rc-todo {{ margin-top: {s['4']}; padding-top: {s['4']}; border-top: 1px solid var(--line-soft); }}
  .rc-todo .k {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: var(--accent);
  }}
  .rc-step {{ display: flex; gap: {s['3']}; margin-top: {s['3']}; align-items: baseline; }}
  .rc-step .i {{
    flex: none; width: 20px; height: 20px; border-radius: 50%;
    background: var(--accent-soft, var(--raised)); color: var(--accent);
    font-size: {t['label']}; font-weight: 800; text-align: center; line-height: 20px;
  }}
  .rc-step .t {{ font-size: {t['secondary']}; font-weight: 600; color: var(--ink); }}
  .rc-step .o {{ font-size: {t['caption']}; color: var(--muted); margin-left: {s['1']}; }}
  .rc-step .d {{ display: block; font-size: {t['caption']}; color: var(--ink-soft); margin-top: 1px; }}
  .rc-more {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['3']}; }}
  .rc-foot {{
    padding: {s['3']} {s['4']}; background: var(--raised); border-top: 1px solid var(--line-soft);
    font-size: {t['label']}; color: var(--faint); line-height: 1.6;
  }}

  /* ── 근거 미터 ─────────────────────────────────────────────────────── */
  /* 규칙이 "기준을 넘었다"가 아니라 **얼마나 넘었는가**를 보여준다.
     위험 구간을 띠로 칠하고 기준선과 학생 값을 각각 표시한다 —
     학생 표식이 띠 안에 들어가 있는 그림이 곧 발동 근거다. */
  .ev {{ margin-top: {s['2']}; margin-bottom: {s['3']}; }}
  .ev-top {{
    display: flex; align-items: baseline; gap: {s['2']};
    font-size: {t['label']}; line-height: 1.4;
  }}
  .ev-lab {{
    font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--muted);
  }}
  .ev-val {{
    margin-left: auto; font-weight: 700; font-variant-numeric: tabular-nums;
    color: var(--accent, var(--primary));
  }}
  .ev-thr {{ color: var(--faint); font-variant-numeric: tabular-nums; }}
  .ev-track {{
    position: relative; height: 8px; border-radius: 4px;
    background: var(--line-soft); margin-top: 7px;
  }}
  .ev-danger {{
    position: absolute; top: 0; bottom: 0; border-radius: 4px;
    background: var(--accent, var(--primary)); opacity: .20;
  }}
  .ev-thrmark {{
    position: absolute; top: -3px; bottom: -3px; width: 2px;
    background: var(--ink-soft); border-radius: 1px;
  }}
  .ev-mark {{
    position: absolute; top: -4px; width: 3px; height: 16px; border-radius: 2px;
    background: var(--accent, var(--primary)); box-shadow: 0 0 0 2px var(--surface);
  }}
  .ev-foot {{
    display: flex; justify-content: space-between;
    font-size: {t['label']}; color: var(--faint); margin-top: 6px;
    font-variant-numeric: tabular-nums;
  }}
  .ev-none {{
    margin-top: {s['2']}; font-size: {t['label']}; color: var(--faint);
  }}

  /* ── What-if 비교 ──────────────────────────────────────────────────── */
  .wi {{ background: var(--surface); border: 1px solid var(--line);
        border-radius: var(--radius-md); padding: {s['4']}; }}
  .wi-row {{ display: flex; align-items: stretch; gap: {s['4']}; flex-wrap: wrap; }}
  .wi-side {{ flex: 1 1 180px; min-width: 0; }}
  .wi-side .k {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: var(--muted);
  }}
  .wi-side .v {{
    font-size: 2.1rem; font-weight: 800; line-height: 1.05; color: var(--ink);
    margin-top: {s['2']};
  }}
  .wi-side .v .p {{ font-size: .44em; font-weight: 600; margin-left: 2px; }}
  .wi-side .d {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['2']}; }}
  .wi-side.after .v {{ color: var(--accent, var(--primary)); }}
  .wi-arrow {{
    display: flex; align-items: center; color: var(--faint); font-size: 1.5rem;
    padding: 0 {s['2']};
  }}
  .wi-delta {{
    flex: 0 0 auto; align-self: center; text-align: right;
    font-size: {t['h2']}; font-weight: 800; font-variant-numeric: tabular-nums;
    color: var(--accent, var(--primary));
  }}
  .wi-delta .c {{
    display: block; font-size: {t['label']}; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: var(--muted); margin-top: 4px;
  }}
  .wi-rules {{
    margin-top: {s['4']}; padding-top: {s['4']}; border-top: 1px solid var(--line-soft);
    font-size: {t['caption']}; color: var(--ink-soft); line-height: 1.75;
  }}
  .wi-rules .tag {{
    font-family: {MONO_STACK}; font-weight: 700; color: var(--ink-soft);
  }}

  /* ── 규칙 판정 트레이스 ────────────────────────────────────────────── */
  .dt .fired {{ font-weight: 700; }}
  .dt .quiet td {{ color: var(--faint); }}
  .dt .quiet .rid {{ color: var(--faint); }}
  .dt .rid {{
    font-family: {MONO_STACK}; font-size: {t['label']}; font-weight: 700; color: var(--ink-soft);
  }}
  /* 위험요인 ↔ 규칙 연결 표시 */
  .factor-rule {{
    font-family: {MONO_STACK}; font-size: {t['label']}; color: var(--faint);
    margin-left: {s['2']};
  }}

  /* ── 데이터 테이블 (직접 그리는 우선순위 표) ───────────────────────── */
  .dt {{ width: 100%; border-collapse: separate; border-spacing: 0; }}
  .dt th {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    color: var(--muted); text-align: left; padding: 0 {s['3']} {s['2']} {s['3']};
    border-bottom: 1px solid var(--line); white-space: nowrap;
  }}
  .dt td {{
    padding: {s['3']}; border-bottom: 1px solid var(--line-soft);
    font-size: {t['secondary']}; color: var(--ink-soft); vertical-align: middle;
  }}
  .dt tbody tr:hover td {{ background: var(--raised); }}
  .dt tbody tr:last-child td {{ border-bottom: none; }}
  .dt .rank {{
    font-family: {MONO_STACK}; font-size: {t['caption']}; color: var(--faint);
    font-variant-numeric: tabular-nums; width: 34px;
  }}
  .dt .sid {{ font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; }}
  .dt .num {{ font-variant-numeric: tabular-nums; }}
  .riskbar {{
    display: flex; align-items: center; gap: {s['2']}; min-width: 148px;
  }}
  /* span 은 인라인이라 width/height 가 먹지 않는다 — 반드시 블록으로 만든다
     (막대 차트에서 똑같이 겪은 문제다) */
  .riskbar .track {{
    display: block; flex: 1; height: 7px; border-radius: 4px; background: var(--line-soft);
  }}
  .riskbar .fill {{
    display: block; height: 100%; border-radius: 4px; transform-origin: left center;
    animation: ds-grow .55s cubic-bezier(.2,.75,.3,1) both;
  }}

  /* ── 우선 명단 — 가리키거나 클릭한 줄만 또렷하게 ───────────────────── */
  /* tabindex 를 주면 클릭이 곧 focus 라서 **JS 없이** "눌러서 고정" 이 된다.
     덤으로 키보드(Tab)로도 줄을 옮겨 다닐 수 있다. */
  .dt tbody tr {{
    position: relative;                 /* 줄 전체를 덮는 링크의 기준점 */
    transition: opacity .18s ease, filter .18s ease, background .18s ease;
    outline: none;
  }}
  /* 줄 전체가 링크다. <tr> 를 <a> 로 감쌀 수 없으므로 링크의 가상요소를 줄 전체로 늘린다.
     진짜 <a> 라서 키보드로도 열리고, 새 탭으로 열기 같은 브라우저 기능도 그대로 쓴다. */
  .dt a.rowlink {{ color: inherit; text-decoration: none; }}
  .dt a.rowlink::after {{ content: ""; position: absolute; inset: 0; z-index: 1; }}
  .dt tbody tr:has(a.rowlink) {{ cursor: pointer; }}
  .dt tbody tr:has(a.rowlink):hover td {{ background: var(--primary-soft); }}

  .dt tbody:has(a.rowlink):hover tr,
  .dt tbody:has(a.rowlink:focus-visible) tr {{ opacity: .34; filter: saturate(.55); }}
  /* `:has()` 는 인자만큼 특이도를 올린다. 그래서 되살리는 쪽도 같은 형태로 써야
     흐리게 하는 규칙을 이긴다 — 안 그러면 가리킨 줄까지 같이 흐려진다 (두 번 겪었다:
     흐리기를 `tbody:has(a.rowlink):hover` 로 좁혔을 때 여기를 같이 안 올려서 재발했다). */
  .dt tbody:has(a.rowlink):hover tr:hover,
  .dt tbody:has(a.rowlink:focus-visible) tr:has(a.rowlink:focus-visible)
    {{ opacity: 1; filter: none; }}
  .dt tbody tr:has(a.rowlink:focus-visible) td {{
    background: var(--primary-soft);
    box-shadow: inset 0 0 0 1px var(--primary-line);
  }}
  .dt .go {{
    font-size: {t['label']}; font-weight: 700; color: var(--primary);
    opacity: 0; transition: opacity .18s ease; white-space: nowrap;
  }}
  .dt tbody tr:hover .go, .dt tbody tr:has(a.rowlink:focus-visible) .go {{ opacity: 1; }}
  .riskbar .pct {{
    font-size: {t['secondary']}; font-weight: 700; font-variant-numeric: tabular-nums;
    width: 46px; text-align: right;
  }}

  /* ── 빈 상태 ───────────────────────────────────────────────────────── */
  .empty {{
    border: 1px dashed var(--line); border-radius: var(--radius-md);
    background: var(--raised); padding: {s['12']} {s['6']}; text-align: center;
  }}
  .empty .t {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink-soft); }}
  .empty .d {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['2']}; }}

  /* ── 히어로 (시작화면) ─────────────────────────────────────────────── */
  /* 캠퍼스 사진 위에 어두운 스크림을 깔고 그 위에 문장·버튼·유리 카드를 얹는다.
     사진은 `--hero-photo` 로 따로 주입한다(theme.inject_hero_photo). 파일이 없으면
     변수가 정의되지 않아 아래 그라디언트만 남는다 — 발표 PC 에서 이미지가 빠져도
     화면이 깨지지 않는다.
     `st.container(key="hero")` 가 붙여 주는 `.st-key-hero` 는 문서화된 훅이라
     DOM 을 깊게 찌르지 않아도 된다. */
  .st-key-hero {{
    position: relative; overflow: hidden;
    background-image:
      linear-gradient(180deg, rgba(6,15,30,.86) 0%, rgba(6,15,30,.44) 40%, rgba(6,15,30,.90) 100%),
      var(--hero-photo, linear-gradient(rgba(0,0,0,0), rgba(0,0,0,0))),
      radial-gradient(1100px 420px at 88% -20%, rgba(78,140,214,.30), transparent 62%),
      linear-gradient(135deg, {c["deep"]} 0%, {c["deep_mid"]} 58%, #17406F 100%);
    background-size: auto, cover, auto, auto;
    background-position: center, center 56%, center, center;
    background-repeat: no-repeat;
    border-radius: var(--radius-lg);
    padding: {s['16']} {s['12']} {s['12']} {s['12']};
    color: #FFFFFF;
    /* 창 높이에 맞춘다. 표지 아래에 빈 바닥이 남으면 잘린 페이지처럼 보인다 */
    min-height: calc(100vh - 92px);
    /* 내용은 세로 가운데로 — 위아래 여백이 화면 비율에 따라 알아서 나뉜다 */
    display: flex; flex-direction: column; justify-content: center;
  }}
  .st-key-hero::after {{
    content: ""; position: absolute; inset: 0; pointer-events: none; z-index: 0;
    background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
    background-size: 44px 44px; mask-image: linear-gradient(105deg, transparent 46%, #000 100%);
  }}
  .st-key-hero > div {{ position: relative; z-index: 1; }}
  /* 어두운 히어로 위에서는 캡션도 밝아야 읽힌다 */
  .st-key-hero [data-testid="stCaptionContainer"],
  .st-key-hero [data-testid="stCaptionContainer"] p {{ color: #9DBBE4 !important; }}

  /* 보이지 않는 도우미 iframe(지구본 자동회전 · 번역 차단)이 1px 흰 조각으로 남는다.
     이 앱은 st.iframe 을 눈에 보이는 용도로 쓰지 않으므로 컨테이너째 숨긴다.
     나중에 iframe 으로 무언가를 보여줄 일이 생기면 이 규칙을 좁혀야 한다. */
  [data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]) {{ display: none; }}

  .hero {{ color: #FFFFFF; position: relative; }}

  /* 상단 바 — 브랜드와 이동 링크 */
  .hero-brand {{ display: flex; align-items: center; gap: {s['3']}; }}
  .hero-brand .mark {{
    width: 38px; height: 38px; border-radius: var(--radius-md); flex: none;
    display: flex; align-items: center; justify-content: center; font-size: 21px;
    background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.24);
    color: #FFFFFF; backdrop-filter: blur(8px);
  }}
  .hero-brand .t {{ display: flex; flex-direction: column; line-height: 1.25; }}
  .hero-brand .n {{ font-size: {t['h3']}; font-weight: 700; color: #FFFFFF; letter-spacing: -.01em; }}
  .hero-brand .s {{ font-size: {t['label']}; color: #A9C0DE; }}

  /* 이동 링크 — 사이드바가 없는 화면이라 여기가 유일한 메뉴다 */
  .st-key-hero_nav a {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 14px; border-radius: {r['pill']};
    background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.16);
    color: #E4ECF8 !important; font-size: {t['caption']}; font-weight: 600;
    backdrop-filter: blur(8px); white-space: nowrap;
  }}
  .st-key-hero_nav a:hover {{
    background: rgba(255,255,255,.18); border-color: rgba(255,255,255,.32);
    color: #FFFFFF !important;
  }}
  .st-key-hero_nav a p {{ font-size: {t['caption']} !important; font-weight: 600 !important; }}
  .st-key-hero_nav [data-testid="stElementContainer"] {{ width: auto; }}
  /* 지구본은 사진 위에 떠 있어야 한다 — 배경도 테두리도 주지 않는다 */
  .st-key-hero [data-testid="stPlotlyChart"] {{ background: transparent; }}

  .st-key-hero .brand {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .18em;
    text-transform: uppercase; color: #9FBFE8;
  }}
  /* 상태 알약 — 지금 어떤 명단을 물고 있는지 첫 줄에서 밝힌다 */
  .st-key-hero .hero-pills {{ display: flex; flex-wrap: wrap; gap: {s['2']}; margin-top: {s['4']}; }}
  .st-key-hero .hero-pill {{
    display: inline-flex; align-items: center; gap: {s['2']}; padding: 7px 14px; border-radius: {r['pill']};
    background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.24);
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    font-size: {t['caption']}; font-weight: 600; color: #EAF1FB;
  }}
  .st-key-hero .hero-pill .i {{ font-size: 15px; color: #7FE3C4; }}
  .st-key-hero .hero-pill .dot {{
    width: 7px; height: 7px; border-radius: 50%; background: #5FD3A6;
    box-shadow: 0 0 0 3px rgba(95,211,166,.22);
  }}
  .st-key-hero h1 {{
    font-size: 3.05rem; font-weight: 800; color: #FFFFFF;
    letter-spacing: -.045em; line-height: 1.16; margin: {s['4']} 0 0 0;
    max-width: 22ch; text-shadow: 0 2px 20px rgba(3,9,20,.42);
    /* 한글은 어절 안에서 줄이 끊기면 읽기 나쁘다 ("맞춤 지원 / 을 제안합니다") */
    word-break: keep-all;
  }}
  /* 한 구절만 색을 준다 — 문장에서 무엇이 이 제품의 약속인지 눈이 먼저 잡는다 */
  .st-key-hero h1 .hl {{ color: {c['accent']}; }}
  .st-key-hero .kr {{
    font-size: {t['h2']}; font-weight: 600; color: #C9DBF2;
    margin-top: {s['2']}; letter-spacing: -.01em;
  }}
  .st-key-hero .hero-lead {{
    font-size: 1rem; line-height: 1.78; color: #CBDAEE;
    margin: {s['4']} 0 0 0; max-width: 62ch; word-break: keep-all;
  }}
  .st-key-hero .hero-lead b {{ color: #EAF2FC; }}
  /* 히어로 버튼 — 배경이 사진이라 유리처럼 띄운다 */
  .st-key-hero_cta {{ margin-top: {s['6']}; }}
  .st-key-hero_cta .stButton > button {{
    padding: 12px 24px; border-radius: var(--radius-md);
    font-size: {t['body']}; font-weight: 700;
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  }}
  .st-key-hero_cta .stButton > button[kind="primary"] {{
    background: rgba(20,40,72,.90); border: 1px solid rgba(255,255,255,.22);
    color: #FFFFFF; box-shadow: 0 12px 28px rgba(3,9,20,.38);
  }}
  .st-key-hero_cta .stButton > button[kind="primary"]:hover {{
    background: rgba(28,56,98,.95); border-color: rgba(255,255,255,.34); color: #FFFFFF;
  }}
  /* 두 번째 버튼은 위험으로 가는 길이다 — 색으로도 그렇게 말한다 */
  .st-key-hero_cta .stButton > button[kind="secondary"] {{
    background: {RISK_COLORS['HIGH']}; border: 1px solid {RISK_COLORS['HIGH']};
    color: #23100D; font-weight: 700; box-shadow: 0 12px 28px rgba(3,9,20,.28);
  }}
  .st-key-hero_cta .stButton > button[kind="secondary"]:hover {{
    background: #FF9083; border-color: #FF9083; color: #23100D;
  }}
  /* 숫자 칩 — 표지에서 규모를 한 줄로 말한다 */
  .hero-chips {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: {s['3']}; }}
  .hero-chips .chip {{
    display: flex; align-items: center; gap: {s['3']};
    padding: {s['4']} {s['5']}; border-radius: var(--radius-lg);
    background: rgba(13,24,42,.58); border: 1px solid rgba(255,255,255,.14);
    backdrop-filter: blur(14px);
  }}
  .hero-chips .chip .i {{
    width: 38px; height: 38px; border-radius: var(--radius-md); flex: none;
    display: flex; align-items: center; justify-content: center; font-size: 20px;
    background: rgba(255,255,255,.10); color: {c['accent']};
  }}
  .hero-chips .chip .t {{ display: flex; flex-direction: column; }}
  .hero-chips .chip .v {{
    font-size: {t['h2']}; font-weight: 800; color: #FFFFFF; letter-spacing: -.02em;
    font-variant-numeric: tabular-nums; line-height: 1.2;
  }}
  .hero-chips .chip .k {{ font-size: {t['caption']}; color: #A9C0DE; margin-top: 1px; }}

  /* 위험 구성 띠 — 칩이 "얼마나"라면 이 띠는 "어떻게 나뉘는가"다 */
  .hero-split {{
    padding: {s['4']} {s['5']}; border-radius: var(--radius-lg);
    background: rgba(13,24,42,.58); border: 1px solid rgba(255,255,255,.14);
    backdrop-filter: blur(14px);
  }}
  .hero-split .hs-head {{
    display: flex; align-items: baseline; gap: {s['3']};
    font-size: {t['caption']}; font-weight: 700; color: #E4ECF8;
    letter-spacing: .04em;
  }}
  .hero-split .hs-head .n {{ font-size: {t['label']}; font-weight: 600; color: #93A9C6; }}
  .hero-split .hs-bar {{
    display: flex; height: 12px; margin-top: {s['3']};
    border-radius: 6px; overflow: hidden; background: rgba(255,255,255,.08);
  }}
  .hero-split .hs-bar > span {{
    display: block; height: 100%; transform-origin: left center;
    animation: ds-grow .7s cubic-bezier(.2,.75,.3,1) both;
  }}
  .hero-split .hs-bar > span:nth-child(2) {{ animation-delay: .08s; }}
  .hero-split .hs-bar > span:nth-child(3) {{ animation-delay: .16s; }}
  .hero-split .hs-legend {{
    display: flex; flex-wrap: wrap; gap: {s['5']}; margin-top: {s['3']};
    font-size: {t['caption']}; color: #A9C0DE;
  }}
  .hero-split .hs-legend .l {{ display: inline-flex; align-items: center; gap: 6px; }}
  .hero-split .hs-legend i {{ width: 9px; height: 9px; border-radius: 3px; }}
  .hero-split .hs-legend b {{ color: #FFFFFF; font-weight: 700; }}
  .hero-split .hs-legend em {{ font-style: normal; color: #7F93AE; }}

  /* 아래 카드 — 이 제품이 답하는 것 */
  .st-key-hero_card {{
    padding: {s['5']} {s['6']}; border-radius: var(--radius-lg);
    background: rgba(13,24,42,.58); border: 1px solid rgba(255,255,255,.14);
    backdrop-filter: blur(14px);
  }}
  .st-key-hero_card .hc-title {{
    font-size: {t['h2']}; font-weight: 700; color: #FFFFFF; letter-spacing: -.015em;
    word-break: keep-all;
  }}
  .st-key-hero_card .hc-title b {{ color: {c['accent']}; }}
  .st-key-hero_card .hc-desc {{
    font-size: {t['secondary']}; color: #B9CBE2; line-height: 1.7; margin-top: {s['2']};
  }}
  .st-key-hero_card .stButton > button {{
    background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.28);
    color: #FFFFFF; font-weight: 700; padding: 11px 18px; border-radius: var(--radius-md);
  }}
  .st-key-hero_card .stButton > button:hover {{
    background: rgba(255,255,255,.20); border-color: rgba(255,255,255,.42); color: #FFFFFF;
  }}

  /* 지구본 — 콘텐츠가 아니라 배경이다. 오른쪽에 얹고 클릭은 통과시킨다. */
  /* Streamlit 이 컨테이너를 래퍼로 한 겹 더 감싸므로 자식 선택자(>)로는 못 잡는다 */
  /* 포르투갈 표시의 맥박 — 지구본 위에 얹은 점 하나가 파문처럼 퍼진다.
     Plotly 가 그린 마커에 직접 걸지 않는 이유는 globe.py 주석에 적어 뒀다. */
  #sdi-geo-ping {{
    position: absolute; width: 10px; height: 10px; margin: -5px 0 0 -5px;
    border-radius: 50%; background: {RISK_COLORS['HIGH']}; pointer-events: none;
    box-shadow: 0 0 10px 2px {RISK_COLORS['HIGH']}80;
  }}
  #sdi-geo-ping::before, #sdi-geo-ping::after {{
    content: ""; position: absolute; inset: -3px; border-radius: 50%;
    border: 2px solid {RISK_COLORS['HIGH']};
    animation: geo-ping 2.4s cubic-bezier(.15,.6,.3,1) infinite;
  }}
  #sdi-geo-ping::after {{ animation-delay: 1.2s; }}
  @keyframes geo-ping {{
    0%   {{ opacity: .75; transform: scale(.6); }}
    70%  {{ opacity: 0;   transform: scale(4.2); }}
    100% {{ opacity: 0;   transform: scale(4.2); }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    #sdi-geo-ping::before, #sdi-geo-ping::after {{ animation: none; opacity: .35; }}
  }}

  /* 지구본 자리 — 오른쪽에 크게 앉히고 **화면 밖으로 흘려보낸다.**
     구를 액자에 맞춰 줄이면 지구본이 아니라 아이콘처럼 보인다. 잘리는 편이 낫다.
     글자·카드는 모두 이 위(z-index 1)에 얹히므로 읽는 데는 영향이 없다. */
  .st-key-hero > div:has(> .st-key-hero_globe) {{
    position: absolute; top: 50%; right: -14%; transform: translateY(-50%);
    z-index: 0; width: clamp(560px, 74%, 1240px); pointer-events: none;
    transform-origin: 80% 50%;
  }}
  @media (max-height: 900px) {{
    .st-key-hero > div:has(> .st-key-hero_globe) {{ transform: translateY(-50%) scale(.9); }}
  }}
  @media (max-height: 800px) {{
    .st-key-hero > div:has(> .st-key-hero_globe) {{ transform: translateY(-50%) scale(.78); }}
  }}
  .st-key-hero .st-key-hero_globe {{ position: static; width: 100%; opacity: .96; }}
  /* 구 뒤에 옅은 빛을 깔면 평면 그림이 아니라 떠 있는 물체로 읽힌다.
     3D 오브젝트를 하나 더 얹는 것보다 이 편이 조용하고, 발표 화면에서 덜 시끄럽다. */
  .st-key-hero .st-key-hero_globe::before {{
    content: ""; position: absolute; inset: 8% 6%; border-radius: 50%;
    background: radial-gradient(circle at 42% 38%,
      rgba(120,190,255,.20), rgba(44,182,189,.12) 46%, transparent 68%);
    filter: blur(18px); z-index: -1;
  }}
  /* 화면이 좁으면 글자와 겹친다 — 그때는 지구본을 내린다 */
  @media (max-width: 1180px) {{
    .st-key-hero .st-key-hero_globe {{ display: none; }}
  }}

  /* 유리 카드 — 사진 위에 얹는 밝은 면. 숫자는 어두운 잉크로 읽는다 */
  /* 두 장의 아래 선이 맞아야 한다. Streamlit 열 안쪽에는 래퍼가 두 겹 더 있어서
     height:100% 로는 안 늘어난다 — 래퍼까지 flex 로 이어 붙여 카드가 열 높이를 채우게 한다. */
  .st-key-hero [data-testid="stHorizontalBlock"] {{ align-items: stretch; }}
  .st-key-hero [data-testid="stColumn"] {{ display: flex; }}
  .st-key-hero [data-testid="stColumn"] > div,
  .st-key-hero [data-testid="stColumn"] > div > [data-testid="stVerticalBlock"],
  .st-key-hero [data-testid="stColumn"] [data-testid="stLayoutWrapper"] {{
    display: flex; flex-direction: column; flex: 1 1 auto; width: 100%;
  }}
  .st-key-hero .glass,
  .st-key-hero .st-key-hero_stat,
  .st-key-hero .st-key-hero_alert {{
    height: 100%;
    background: rgba(13,24,42,.62); border: 1px solid rgba(255,255,255,.16);
    border-radius: var(--radius-lg); padding: {s['6']};
    box-shadow: 0 20px 44px rgba(0,0,0,.42);
    backdrop-filter: blur(16px) saturate(1.1); -webkit-backdrop-filter: blur(16px) saturate(1.1);
    display: flex; flex-direction: column; justify-content: center;
    /* 열(column) stretch 는 Streamlit 안쪽 래퍼에서 끊긴다 —
       두 장이 나란히 서는 화면이라 최소 높이로 직접 맞춘다. */
    min-height: 268px;
  }}
  .st-key-hero .g-lab {{
    font-size: {t['caption']}; font-weight: 700; color: {c['muted']};
  }}
  .st-key-hero .g-val {{
    font-size: 2.4rem; font-weight: 800; color: {c['ink']}; letter-spacing: -.035em;
    margin-top: {s['2']}; font-variant-numeric: tabular-nums; line-height: 1.05;
  }}
  .st-key-hero .g-val .u {{
    font-size: .38em; font-weight: 700; color: {c['faint']}; margin-left: 4px;
  }}
  .st-key-hero .g-cap {{
    font-size: {t['caption']}; color: {c['muted']}; margin-top: {s['2']};
  }}
  .st-key-hero .g-split {{
    display: flex; gap: {s['6']}; margin-top: {s['4']}; padding-top: {s['4']};
    border-top: 1px solid {c['line_soft']};
  }}
  .st-key-hero .g-split .k {{ font-size: {t['caption']}; color: {c['muted']}; }}
  .st-key-hero .g-split .v {{
    font-size: {t['h3']}; font-weight: 700; color: {c['ink_soft']}; margin-top: 2px;
  }}
  /* 경보 카드 — 버튼이 카드 안에 들어가야 해서 컨테이너 자체를 유리로 만든다 */
  .st-key-hero_alert .g-head {{ display: flex; align-items: center; gap: {s['3']}; }}
  .st-key-hero_alert .g-ico {{
    width: 40px; height: 40px; border-radius: var(--radius-md); flex: 0 0 40px;
    background: {RISK_SOFT['HIGH']}; border: 1px solid {RISK_LINE['HIGH']}; color: {RISK_COLORS['HIGH']};
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; font-weight: 700;
  }}
  .st-key-hero_alert .g-title {{ font-size: {t['h2']}; font-weight: 700; color: {c['ink']}; }}
  .st-key-hero_alert .g-body {{
    font-size: {t['secondary']}; color: {c['ink_soft']}; line-height: 1.7; margin-top: {s['3']};
  }}
  /* 왼쪽 카드 버튼 — 유리 위의 얇은 버튼. 카드 전체가 이동 수단임을 알린다 */
  .st-key-hero_stat .stButton > button {{
    margin-top: {s['4']}; padding: 10px 18px; border-radius: var(--radius-md);
    background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.24);
    color: #FFFFFF; font-size: {t['secondary']}; font-weight: 700;
  }}
  .st-key-hero_stat .stButton > button:hover {{
    background: rgba(255,255,255,.18); border-color: rgba(255,255,255,.38); color: #FFFFFF;
  }}
  .st-key-hero_alert .stButton > button {{
    margin-top: {s['2']}; padding: 11px 22px; border-radius: var(--radius-md);
    background: {RISK_SOFT['HIGH']}; border: 1px solid {RISK_LINE['HIGH']}; color: {RISK_COLORS['HIGH']};
    font-size: {t['secondary']}; font-weight: 700;
  }}
  .st-key-hero_alert .stButton > button:hover {{
    background: #F8DCD7; border-color: {RISK_COLORS['HIGH']}; color: {RISK_COLORS['HIGH']};
  }}

  /* ── 파이프라인 (DATA → MODEL → RISK → ACTION) ─────────────────────── */
  .flow {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; }}
  .flow .step {{
    position: relative; background: var(--surface); border: 1px solid var(--line);
    border-right: none; padding: {s['6']};
  }}
  .flow .step:first-child {{ border-radius: var(--radius-md) 0 0 var(--radius-md); }}
  .flow .step:last-child {{ border-right: 1px solid var(--line); border-radius: 0 var(--radius-md) var(--radius-md) 0; }}
  .flow .step::before {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: var(--accent, var(--primary)); opacity: .85;
  }}
  .flow .step .n {{
    font-family: {MONO_STACK}; font-size: {t['label']}; color: var(--faint);
    letter-spacing: .1em;
  }}
  .flow .step .k {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .13em; text-transform: uppercase;
    color: var(--accent, var(--primary)); margin-top: {s['2']};
  }}
  .flow .step .t {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink); margin-top: {s['2']}; }}
  .flow .step .d {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['2']}; line-height: 1.6; }}

  /* ── 로컬라이제이션 사슬 ───────────────────────────────────────────── */
  .chain {{ display: flex; flex-direction: column; gap: {s['2']}; }}
  .chain .node {{
    display: flex; align-items: center; gap: {s['3']};
    border: 1px solid var(--line); border-radius: var(--radius-sm);
    background: var(--surface); padding: {s['3']} {s['4']};
  }}
  .chain .node .i {{
    font-family: {MONO_STACK}; font-size: {t['label']}; color: var(--faint); width: 18px;
  }}
  .chain .node .t {{ font-size: {t['secondary']}; font-weight: 600; color: var(--ink); }}
  .chain .node .d {{ font-size: {t['caption']}; color: var(--muted); margin-left: auto; text-align: right; }}
  .chain .arrow {{ text-align: center; color: var(--faint); font-size: {t['caption']}; line-height: 1; }}

  /* ── Streamlit 위젯 손보기 ─────────────────────────────────────────── */
  /* 버튼 */
  .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
    border-radius: var(--radius-sm); border: 1px solid var(--line);
    font-size: {t['secondary']}; font-weight: 600; color: var(--ink-soft);
    background: var(--surface); transition: all .14s ease; box-shadow: none;
    padding: {s['2']} {s['4']};
  }}
  .stButton > button:hover, .stFormSubmitButton > button:hover {{
    border-color: var(--primary-line); color: var(--primary); background: var(--primary-soft);
  }}
  .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {c['primary_fill']} 0%, #3E7FCB 100%);
    border-color: {c['primary_fill']}; color: #FFFFFF; box-shadow: var(--shadow-raise);
  }}
  .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
    background: {c['primary_fill_hover']}; border-color: {c['primary_fill_hover']}; color: #FFFFFF;
  }}

  /* 위험도 버튼(학생 목록) — 켜진 등급이 **그 등급의 색**으로 채워진다.
     순서가 HIGH·MEDIUM·LOW 로 고정이라 nth-child 로 색을 건다. */
  .st-key-roster_filter [data-testid="stButtonGroup"] {{
    display: flex; flex-wrap: wrap; gap: {s['2']};
  }}
  .st-key-roster_filter [data-testid="stButtonGroup"] button {{
    border-radius: {r['pill']} !important; padding: 8px 16px !important;
    font-size: {t['caption']} !important; font-weight: 700 !important;
    background: var(--raised) !important; border: 1px solid var(--line) !important;
    color: var(--muted) !important;
  }}
  .st-key-roster_filter [data-testid="stButtonGroup"] button:hover {{ color: var(--ink) !important; }}
  .st-key-roster_filter [data-testid="stButtonGroup"] button:nth-child(1)[aria-pressed="true"],
  .st-key-roster_filter [data-testid="stButtonGroup"] button:nth-child(1)[data-selected] {{
    background: {RISK_SOFT['HIGH']} !important; border-color: {RISK_COLORS['HIGH']} !important;
    color: {RISK_COLORS['HIGH']} !important;
  }}
  .st-key-roster_filter [data-testid="stButtonGroup"] button:nth-child(2)[aria-pressed="true"],
  .st-key-roster_filter [data-testid="stButtonGroup"] button:nth-child(2)[data-selected] {{
    background: {RISK_SOFT['MEDIUM']} !important; border-color: {RISK_COLORS['MEDIUM']} !important;
    color: {RISK_COLORS['MEDIUM']} !important;
  }}
  .st-key-roster_filter [data-testid="stButtonGroup"] button:nth-child(3)[aria-pressed="true"],
  .st-key-roster_filter [data-testid="stButtonGroup"] button:nth-child(3)[data-selected] {{
    background: {RISK_SOFT['LOW']} !important; border-color: {RISK_COLORS['LOW']} !important;
    color: {RISK_COLORS['LOW']} !important;
  }}
  /* 필터 줄의 위젯 높이를 아래로 맞춘다 */
  .st-key-roster_filter [data-testid="stColumn"] {{ display: flex; align-items: center; }}
  .st-key-roster_filter [data-testid="stColumn"] > div {{ width: 100%; }}

  /* 분절 토글(집중관리 대상의 범위 필터) — 눌린 쪽이 채워진 알약으로 보인다 */
  .st-key-risk_filter [data-testid="stButtonGroup"] {{
    display: inline-flex; gap: 2px; padding: 4px;
    background: var(--raised); border: 1px solid var(--line); border-radius: {r['pill']};
  }}
  .st-key-risk_filter [data-testid="stButtonGroup"] button {{
    border: none !important; background: transparent !important;
    border-radius: {r['pill']} !important; padding: 8px 20px !important;
    font-size: {t['secondary']} !important; font-weight: 700 !important;
    color: var(--muted) !important; box-shadow: none !important;
  }}
  .st-key-risk_filter [data-testid="stButtonGroup"] button:hover {{ color: var(--ink) !important; }}
  .st-key-risk_filter [data-testid="stButtonGroup"] button[aria-checked="true"],
  .st-key-risk_filter [data-testid="stButtonGroup"] button[kind$="Active"] {{
    background: {c['primary_fill']} !important; color: #FFFFFF !important;
    box-shadow: var(--shadow-raise) !important;
  }}
  /* 필터 줄은 위젯 높이가 서로 달라 아래로 맞춘다 */
  .st-key-risk_filter [data-testid="stColumn"] {{ display: flex; align-items: flex-end; }}
  .st-key-risk_filter [data-testid="stColumn"] > div {{ width: 100%; }}

  /* 다크에서 Streamlit 기본 흰 면이 남는 자리들 */
  [data-testid="stDialog"] [role="dialog"],
  [data-baseweb="popover"] > div, [data-baseweb="menu"], [role="listbox"] {{
    background: var(--surface) !important; color: var(--ink-soft) !important;
  }}
  [data-testid="stDataFrame"] {{ background: var(--surface); }}

  /* 입력 위젯 */
  [data-baseweb="select"] > div, .stTextInput input, .stNumberInput input {{
    border-radius: var(--radius-sm) !important; border-color: var(--line) !important;
    font-size: {t['secondary']} !important; background: var(--surface) !important;
  }}
  .stTextInput label, .stNumberInput label, .stSelectbox label,
  .stSlider label, .stMultiSelect label, .stCheckbox label {{
    font-size: {t['caption']} !important; font-weight: 600 !important; color: var(--ink-soft) !important;
  }}
  /* 폼 안 위젯 간격이 넓어 32개 입력이 실제보다 길어 보인다 */
  [data-testid="stForm"] {{
    border: 1px solid var(--line); border-radius: var(--radius-md);
    background: var(--surface); padding: {s['6']};
  }}
  [data-testid="stForm"] [data-testid="stVerticalBlock"] {{ gap: {s['2']}; }}

  /* 익스팬더 */
  [data-testid="stExpander"] {{
    border: 1px solid var(--line) !important; border-radius: var(--radius-md) !important;
    background: var(--surface); box-shadow: none !important;
  }}
  [data-testid="stExpander"] summary {{ font-size: {t['secondary']}; font-weight: 600; color: var(--ink-soft); }}

  /* 탭 */
  [data-baseweb="tab-list"] {{ gap: {s['1']}; border-bottom: 1px solid var(--line); }}
  [data-baseweb="tab"] {{
    font-size: {t['secondary']}; font-weight: 600; color: var(--muted);
    padding: {s['2']} {s['4']}; border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  }}
  [aria-selected="true"][data-baseweb="tab"] {{ color: var(--primary); }}

  /* 데이터프레임 */
  [data-testid="stDataFrame"] {{
    border: 1px solid var(--line); border-radius: var(--radius-md); overflow: hidden;
  }}
  [data-testid="stDataFrame"] [data-testid="stTable"] {{ font-size: {t['secondary']}; }}

  /* 사이드바 */
  [data-testid="stSidebar"] {{
    background: var(--surface); border-right: 1px solid var(--line);
  }}
  [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding-top: {s['4']}; }}
  [data-testid="stSidebarNav"] {{ padding-top: {s['2']}; }}
  [data-testid="stSidebarNav"] a {{ border-radius: var(--radius-sm); }}
  [data-testid="stSidebarNav"] span {{ font-size: {t['secondary']}; font-weight: 600; }}
  .sb-brand {{
    padding: 0 0 {s['4']} 0; margin-bottom: {s['2']}; border-bottom: 1px solid var(--line);
  }}
  .sb-brand .n {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink); letter-spacing: -.01em; }}
  .sb-brand .s {{ font-size: {t['label']}; color: var(--muted); margin-top: 2px; letter-spacing: .04em; }}
  .sb-foot {{
    margin-top: {s['8']}; padding: {s['4']};
    border: 1px solid var(--line); border-radius: var(--radius-lg);
    background: linear-gradient(160deg, {c['primary_soft']}, {c['accent_soft']});
  }}
  .sb-foot .k {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .11em; text-transform: uppercase;
    color: var(--primary);
  }}
  .sb-foot .v {{
    font-size: {t['h2']}; font-weight: 800; color: var(--ink); margin-top: {s['1']};
    letter-spacing: -.02em; font-variant-numeric: tabular-nums;
  }}
  .sb-foot .d {{ font-size: {t['caption']}; color: var(--muted); margin-top: 2px; }}

  /* ── 맞춤 조치 제안 ────────────────────────────────────────────────── */
  /* 상담 카드가 "누구를 · 얼마나 위험하게" 라면 이 패널은 "그래서 무엇부터" 다.
     레퍼런스는 밝은 크림색이었는데, 우리 화면은 다크라 같은 구조를 어두운 면 위에
     올리고 강조만 카테고리 색으로 가져왔다. */
  .plan {{
    background: linear-gradient(180deg, {c['raised']}, {c['surface']});
    border: 1px solid var(--line); border-radius: var(--radius-lg);
    padding: {s['5']};
  }}
  .plan-head {{ display: flex; align-items: center; gap: {s['3']}; }}
  .plan-head .ico {{
    width: 40px; height: 40px; border-radius: var(--radius-md); flex: none;
    display: flex; align-items: center; justify-content: center; font-size: 21px;
    color: {c['accent']}; background: {c['accent_soft']};
    border: 1px solid {c['accent_line']};
  }}
  .plan-head .t {{ display: flex; flex-direction: column; min-width: 0; }}
  .plan-head .n {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink); }}
  .plan-head .s {{ font-size: {t['caption']}; color: var(--muted); margin-top: 2px; }}
  .plan-head .cats {{ margin-left: auto; display: flex; gap: 6px; flex-wrap: wrap; }}
  .plan-head .cat {{
    display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;
    font-size: {t['label']}; font-weight: 700; color: var(--c);
    background: color-mix(in srgb, var(--c) 16%, {c['surface']});
    border: 1px solid color-mix(in srgb, var(--c) 38%, {c['surface']});
    border-radius: {r['pill']}; padding: 3px {s['2']};
  }}
  .plan-head .cat .material-symbols-rounded {{ font-size: 13px; }}

  .plan-item {{
    display: flex; align-items: flex-start; gap: {s['3']};
    margin-top: {s['3']}; padding: {s['3']} {s['4']};
    background: var(--surface); border: 1px solid var(--line);
    border-left: 3px solid var(--c, var(--primary)); border-radius: var(--radius-md);
  }}
  .plan-item .n {{
    width: 24px; height: 24px; border-radius: 50%; flex: none; margin-top: 1px;
    display: flex; align-items: center; justify-content: center;
    font-size: {t['label']}; font-weight: 800; color: #0B1524;
    background: var(--c, var(--primary));
  }}
  .plan-item .t {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink); }}
  .plan-item .m {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }}
  .plan-item .chip {{
    display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;
    font-size: {t['label']}; font-weight: 600; padding: 3px {s['2']};
    border-radius: var(--radius-sm); border: 1px solid var(--line);
    background: var(--raised); color: var(--muted);
  }}
  .plan-item .chip .material-symbols-rounded {{ font-size: 13px; }}
  /* 언제까지 · 최우선 두 개만 색을 준다 — 나머지는 사실 표기다 */
  .plan-item .chip.when {{
    color: {c['accent']}; background: {c['accent_soft']}; border-color: {c['accent_line']};
  }}
  .plan-item .chip.star {{
    color: {RISK_COLORS['MEDIUM']}; background: {RISK_SOFT['MEDIUM']};
    border-color: {RISK_LINE['MEDIUM']};
  }}
  .plan-more {{ font-size: {t['caption']}; color: var(--faint); margin-top: {s['3']}; }}

  /* ── 팝업 (학생 상세) ──────────────────────────────────────────────── */
  /* 기본 폭은 이 내용(조치 3장 + 근거 + What-if)에 좁다. 넓히고 스크롤은 안쪽에 준다. */
  /* 패널은 <section role="dialog"> 다 — div 로 지정하면 걸리지 않는다.
     폭은 CSS 로 늘리지 않는다: Streamlit 은 안쪽 열 너비를 **자기가 아는 폭**으로
     계산하기 때문에, CSS 로만 넓히면 오른쪽에 빈 띠가 남는다.
     넓게 쓰려면 `st.dialog(width=...)` 로 알려 줘야 한다. */
  [data-testid="stDialog"] [role="dialog"] {{
    border-radius: {r['lg']}; box-shadow: 0 30px 80px rgba(0,0,0,.55);
    /* 높이를 제한했으면 **넘치는 내용은 스크롤**로 보내야 한다.
       overflow 를 안 주면 아래쪽 What-if 가 통째로 잘려 나간다. */
    max-height: 90vh; overflow-y: auto; overscroll-behavior: contain;
  }}
  .dlg-head {{
    display: flex; align-items: center; justify-content: space-between; gap: {s['4']};
    padding-bottom: {s['4']}; margin-bottom: {s['2']}; border-bottom: 1px solid var(--line);
  }}
  .dlg-head .who {{ display: flex; align-items: center; gap: {s['3']}; }}
  .dlg-head .avatar {{
    width: 44px; height: 44px; border-radius: 50%; flex: none;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: {t['secondary']}; color: var(--c, var(--primary));
    background: color-mix(in srgb, var(--c, var(--primary)) 22%, {c['surface']});
    border: 1px solid color-mix(in srgb, var(--c, var(--primary)) 46%, {c['surface']});
  }}
  .st-key-dlg_head_bar {{ align-items: center; }}
  .st-key-dlg_head_bar [data-testid="stButtonGroup"] button {{
    padding: 6px 12px !important; font-size: {t['caption']} !important;
  }}
  .dlg-head .nm {{ font-size: {t['h2']}; font-weight: 800; color: var(--ink); letter-spacing: -.02em; }}
  .dlg-head .sub {{ font-size: {t['caption']}; color: var(--muted); margin-top: 2px; }}
  /* 등급 배지는 이제 머리 오른쪽 바 안에 있다 — 두 자리 모두에서 같게 보이게 한다 */
  .dlg-head .lv, .st-key-dlg_head_bar .lv {{
    font-size: {t['caption']}; font-weight: 700; color: var(--c, var(--primary));
    padding: 6px {s['3']}; border-radius: {r['pill']}; white-space: nowrap;
    background: color-mix(in srgb, var(--c, var(--primary)) 20%, {c['surface']});
    border: 1px solid color-mix(in srgb, var(--c, var(--primary)) 44%, {c['surface']});
  }}

  /* 스크롤바 — 기본 굵은 회색 막대가 발표 화면에서 눈에 띈다 */
  ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
  ::-webkit-scrollbar-thumb {{ background: #2C3B54; border-radius: 6px; border: 2px solid var(--canvas); }}
  ::-webkit-scrollbar-thumb:hover {{ background: #3B4D6B; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}

  /* ── 막대 차트 (직접 그린다) ───────────────────────────────────────── */
  /* Plotly 막대로는 "가리킨 막대만 또렷하게" 를 JS 없이 못 한다. 직접 그리면
     포커스 처리가 CSS 몇 줄이고 테마도 완전히 맞는다. 산점도처럼 좌표가 필요한
     그래프만 Plotly 에 남긴다. */
  .bars {{ display: flex; flex-direction: column; gap: 2px; }}
  .bars .row {{
    display: grid; grid-template-columns: var(--labelw, 118px) 1fr auto;
    align-items: center; gap: {s['3']};
    padding: {s['2']} {s['2']}; border-radius: var(--radius-sm);
    transition: opacity .18s ease, background .18s ease, filter .18s ease;
  }}
  /* 하나를 가리키면 나머지는 물러난다 — 흐리게 하는 대신 **옅게** 한다.
     작은 한글 라벨에 blur 를 걸면 뭉개져서 오히려 읽기 나빠진다. */
  .bars:hover .row {{ opacity: .34; filter: saturate(.55); }}
  .bars .row:hover {{ opacity: 1; filter: none; background: var(--raised); }}
  .bars .lab {{
    font-size: {t['secondary']}; color: var(--ink-soft); font-weight: 600;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .bars .row:hover .lab {{ color: var(--ink); }}
  /* span 은 인라인이라 width/height 가 먹지 않는다 — 반드시 블록으로 만든다 */
  .bars .track {{
    display: block; height: 10px; border-radius: 5px; background: var(--line-soft);
  }}
  .bars .fill {{
    display: block; height: 100%; border-radius: 5px; transform-origin: left center;
    animation: ds-grow .55s cubic-bezier(.2,.75,.3,1) both;
  }}
  .bars .val {{
    font-size: {t['caption']}; font-weight: 700; color: var(--ink-soft);
    font-variant-numeric: tabular-nums; white-space: nowrap; min-width: 74px;
    text-align: right;
  }}
  .bars .row:hover .val {{ color: var(--ink); }}
  .bars-hint {{ font-size: {t['label']}; color: var(--faint); margin-top: {s['2']}; }}

  /* ── 모션 — 값이 "찼다"는 것만 보여주고 끝낸다 ─────────────────────── */
  /* 기관용 분석 제품이라 절제한다. 등장 애니메이션은 **막대와 마커에만** 쓰고
     화면 전체를 움직이지 않는다. 접근성 설정을 켠 사용자에겐 전부 끈다. */
  @keyframes ds-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
  @keyframes ds-rise {{ from {{ opacity: 0; transform: translateY(6px); }}
                        to   {{ opacity: 1; transform: translateY(0); }} }}
  @keyframes ds-mark {{ from {{ opacity: 0; transform: translateX(-10px); }}
                        to   {{ opacity: 1; transform: translateX(0); }} }}
  /* 도넛 조각이 그려지는 애니메이션 — 길이(dasharray)를 0에서 목표까지 민다 */
  @keyframes dn-grow {{ from {{ stroke-dasharray: 0 var(--c); }}
                        to   {{ stroke-dasharray: var(--len) var(--c); }} }}
  @keyframes dn-raise {{ from {{ height: 0; }} to {{ height: var(--fill); }} }}

  .factor-fill, .kpi-bar > span, .riskbar .fill {{
    transform-origin: left center;
    animation: ds-grow .5s cubic-bezier(.2,.75,.3,1) both;
  }}
  /* 위험요인은 위에서부터 차례로 — 기여도 순서가 눈에 남는다 */
  .factor:nth-child(2) .factor-fill {{ animation-delay: .05s; }}
  .factor:nth-child(3) .factor-fill {{ animation-delay: .10s; }}
  .factor:nth-child(4) .factor-fill {{ animation-delay: .15s; }}
  .factor:nth-child(5) .factor-fill {{ animation-delay: .20s; }}

  /* 가로 막대도 위에서부터 차례로 — 순위가 눈에 남는다 */
  .bars .row:nth-child(2) .fill {{ animation-delay: .06s; }}
  .bars .row:nth-child(3) .fill {{ animation-delay: .12s; }}
  .bars .row:nth-child(4) .fill {{ animation-delay: .18s; }}
  .bars .row:nth-child(5) .fill {{ animation-delay: .24s; }}
  .bars .row:nth-child(6) .fill {{ animation-delay: .30s; }}
  .bars .row:nth-child(7) .fill {{ animation-delay: .36s; }}

  .meter .mark {{ animation: ds-mark .45s cubic-bezier(.2,.75,.3,1) both .12s; }}
  .meter-val .n {{ animation: ds-rise .4s ease-out both; }}
  .kpi-hero .val {{ animation: ds-rise .4s ease-out both; }}

  .kpi, .act, .card {{ transition: border-color .15s ease, box-shadow .15s ease; }}
  .kpi:hover {{ border-color: var(--primary-line); }}

  @media (prefers-reduced-motion: reduce) {{
    .factor-fill, .kpi-bar > span, .riskbar .fill, .bars .fill,
    .meter .mark, .meter-val .n, .kpi-hero .val,
    .dn .dn-seg, .dn-center b, .cols .bar, .cols .v {{ animation: none !important; }}
    /* 애니메이션을 끄면 도넛 조각과 막대가 0 인 채로 남는다 — 최종값을 직접 준다 */
    .dn .dn-seg {{ stroke-dasharray: var(--len) var(--c) !important; }}
    .cols .bar {{ height: var(--fill) !important; }}
    * {{ transition-duration: .01ms !important; }}
  }}

  /* 좁은 화면에서 파이프라인/그리드가 찌그러지지 않게 */
  @media (max-width: 1180px) {{
    .flow {{ grid-template-columns: repeat(2, 1fr); }}
    .flow .step {{ border-right: 1px solid var(--line); border-radius: var(--radius-md); }}
    .st-key-hero {{ padding: {s['8']}; }}
    .st-key-hero h1 {{ font-size: 1.95rem; }}
  }}
</style>
"""


#: 히어로 배경 사진. 없으면 그라디언트만 남는다 (파일이 빠져도 화면은 멀쩡하다).
HERO_PHOTO = Path(__file__).resolve().parent.parent / "assets" / "hero_campus.jpg"


@st.cache_data(show_spinner=False)
def _hero_photo_style(path: str, stamp: float) -> str:
    """사진을 data URI 로 CSS 에 심는다.

    Streamlit 의 정적 파일 서빙은 설정(enableStaticServing)에 기대야 하고 발표 PC 에서
    꺼져 있으면 배경이 통째로 빈다. 파일을 CSS 안에 넣어 두면 앱만 뜨면 배경도 뜬다.
    `stamp` 는 파일 수정 시각 — 사진을 바꾸면 캐시가 자동으로 무효화된다.
    """
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"<style>.st-key-hero{{--hero-photo:url('data:image/jpeg;base64,{data}');}}</style>"


def inject_hero_photo() -> None:
    """시작화면에서만 부른다. 다른 화면까지 사진을 실어 보낼 이유가 없다."""
    if not HERO_PHOTO.exists():
        return
    st.markdown(
        _hero_photo_style(str(HERO_PHOTO), HERO_PHOTO.stat().st_mtime),
        unsafe_allow_html=True,
    )


def inject_css() -> None:
    """페이지마다 첫 줄에서 부른다.

    멀티페이지에서는 화면을 옮길 때마다 스크립트가 새로 실행되므로,
    진입점에서 한 번만 넣으면 스타일이 유실될 수 있다.
    """
    st.markdown(_css(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 5. 차트 공통 — Plotly 도 같은 디자인 시스템을 따른다
# ---------------------------------------------------------------------------

#: 발표 화면에 불필요한 툴바를 숨긴다.
PLOTLY_CONFIG = {"displayModeBar": False, "staticPlot": False, "responsive": True}


def style_figure(fig, height: int = 260, show_legend: bool = False, *, grid: str = "y"):
    """모든 차트에 같은 여백·폰트·격자·툴팁을 입힌다.

    `grid` 는 격자를 어느 축에 둘지다 — 막대가 가로면 "x", 세로면 "y".
    양쪽에 다 그으면 표처럼 보여서 읽기 어렵다.
    """
    fig.update_layout(
        height=height,
        margin=dict(l=4, r=4, t=6, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, size=12, color=COLORS["muted"]),
        showlegend=show_legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.26, x=0,
            font=dict(size=11, color=COLORS["ink_soft"]),
        ),
        hoverlabel=dict(
            font_family=FONT_STACK, font_size=12, font_color=COLORS["ink"],
            bgcolor=COLORS["surface"], bordercolor=COLORS["line"],
        ),
        separators=".,",
    )
    axis = dict(
        showline=False, zeroline=False, ticks="",
        tickfont=dict(size=11, color=COLORS["muted"]),
    )
    fig.update_xaxes(**axis, showgrid=(grid == "x"), gridcolor=COLORS["line_soft"])
    fig.update_yaxes(**axis, showgrid=(grid == "y"), gridcolor=COLORS["line_soft"])
    return fig
