"""
디자인 시스템 — 색·타이포·간격·모서리·그림자·상태를 **여기 한 곳에서만** 정의한다.

화면 파일에 색상 코드나 px 값을 직접 적지 않는다. 발표 직전에 톤을 바꿀 때
한 파일만 고치면 되도록, 그리고 화면 4개가 같은 언어를 쓰도록.

방침
    · **라이트 고정.** 발표는 빔프로젝터다. 어두운 배경은 명암비가 무너지고
      회의실 조명에서 회색으로 뜬다. `.streamlit/config.toml` 에서도 고정한다.
    · **색은 장식이 아니라 신호다.** 위험 3단계와 카테고리 3종에만 색을 쓰고
      나머지는 잉크·중성 그레이로 간다. 색이 많아지면 위험 신호가 묻힌다.
    · **상태를 색으로만 구분하지 않는다.** HIGH/MEDIUM/LOW 는 항상 글자를 함께 쓴다.
    · **그림자는 계층에만.** 모든 카드에 그림자를 넣으면 아무것도 강조되지 않는다.
    · Streamlit 기본 인상은 지우되 **`data-testid` 처럼 비교적 안정된 선택자만** 쓴다.
      DOM 을 깊게 찔러 버전마다 깨지는 CSS 는 만들지 않는다.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# 1. 색 — 잉크 / 중성 / 강조 / 상태
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    # 잉크 (텍스트)
    "ink": "#0B1524",          # 제목·수치
    "ink_soft": "#3D4C61",     # 본문
    "muted": "#6B7A90",        # 보조·캡션
    "faint": "#95A2B5",        # 비활성·단위
    # 표면
    "canvas": "#F4F6F9",       # 페이지 바닥
    "surface": "#FFFFFF",      # 카드
    "raised": "#FAFBFD",       # 카드 안 한 단계 들어간 면
    "line": "#E2E8F0",         # 경계선
    "line_soft": "#EDF1F6",    # 옅은 구분선
    # 강조 — 대학 행정 톤의 차분한 블루
    "primary": "#1B4F91",
    "primary_hover": "#173F75",
    "primary_soft": "#EAF1FA",
    "primary_line": "#C7DAF0",
    # 히어로
    "deep": "#0A1E3C",
    "deep_2": "#153A६E".replace("६", "6"),  # #153A6E
}

#: 위험등급 — 화면 전체(배지·표·차트)에서 같은 값을 쓴다.
RISK_COLORS: dict[str, str] = {"HIGH": "#B3382F", "MEDIUM": "#A66A05", "LOW": "#1B6E54"}
RISK_SOFT: dict[str, str] = {"HIGH": "#FCEEEC", "MEDIUM": "#FCF4E4", "LOW": "#E9F4EF"}
RISK_LINE: dict[str, str] = {"HIGH": "#F0CBC6", "MEDIUM": "#EFDDB4", "LOW": "#C5E3D7"}

#: 위험요인 카테고리 (services.predictor.RISK_CATEGORIES 의 키와 같다)
CATEGORY_COLORS: dict[str, str] = {
    "academic": "#1B4F91",
    "financial": "#A66A05",
    "adaptation": "#5B6B8C",
}

#: 이진 Target (팀 전처리 기준 1=Dropout / 0=Non-Dropout)
CLASS_COLORS: dict[str, str] = {"Dropout": "#B3382F", "Non-Dropout": "#1B6E54"}

#: 시작화면 지구본
PORTUGAL: dict[str, str] = {
    "ocean": "#12335C",
    "land": "#2C5E96",
    "border": "rgba(255,255,255,.28)",
    "graticule": "rgba(255,255,255,.16)",
    "highlight": "#FF6B5B",
    "halo": "rgba(255,107,91,.30)",
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
    "1": "4px", "2": "8px", "3": "12px", "4": "16px",
    "6": "24px", "8": "32px", "12": "48px", "16": "64px",
}

RADIUS: dict[str, str] = {"sm": "6px", "md": "10px", "lg": "14px", "pill": "999px"}

SHADOW: dict[str, str] = {
    # 두 단계뿐이다. 카드가 떠 있을 이유가 없으면 선으로 끝낸다.
    "raise": "0 1px 2px rgba(11,21,36,.04), 0 4px 12px rgba(11,21,36,.05)",
    "float": "0 2px 6px rgba(11,21,36,.06), 0 12px 28px rgba(11,21,36,.09)",
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
    --high:{RISK_COLORS['HIGH']}; --medium:{RISK_COLORS['MEDIUM']}; --low:{RISK_COLORS['LOW']};
    --radius-sm:{r['sm']}; --radius-md:{r['md']}; --radius-lg:{r['lg']};
    --shadow-raise:{SHADOW['raise']}; --shadow-float:{SHADOW['float']};
  }}

  /* ── 기본 ──────────────────────────────────────────────────────────── */
  html, body, .stApp, [class*="st-"] {{ font-family: {FONT_STACK}; }}
  /* 아이콘 폰트까지 덮으면 아이콘이 글자로 깨진다 — 되돌린다 */
  [data-testid="stIconMaterial"],
  span.material-symbols-rounded, span.material-symbols-outlined, .material-icons
    {{ font-family: "Material Symbols Rounded" !important; }}

  .stApp {{ background: var(--canvas); color: var(--ink-soft); }}
  .block-container {{
    padding-top: {s['6']}; padding-bottom: {s['16']};
    max-width: 1380px;
  }}

  /* Streamlit 기본 상단 장식·헤더를 걷어낸다 (발표 화면에 불필요) */
  [data-testid="stDecoration"] {{ display: none; }}
  [data-testid="stHeader"] {{ background: transparent; height: 0; }}
  /* Deploy 버튼·햄버거는 발표 화면에서 "이거 Streamlit 이네" 를 즉시 드러낸다.
     캐시를 비울 일이 있으면 앱을 재시작한다. */
  [data-testid="stToolbar"] {{ display: none; }}
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
  }}
  .sec-rule {{ flex: 1; height: 1px; background: var(--line); }}
  .sec-desc {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['1']}; }}

  /* ── 카드 ──────────────────────────────────────────────────────────── */
  .card {{
    background: var(--surface); border: 1px solid var(--line);
    border-radius: var(--radius-md); padding: {s['4']} {s['6']};
  }}
  .card-lg {{ padding: {s['6']}; }}
  .card-title {{ font-size: {t['h3']}; font-weight: 700; color: var(--ink); }}
  .card-sub {{ font-size: {t['caption']}; color: var(--muted); margin-top: {s['1']}; }}

  /* ── KPI — 계층이 있다. hero 하나, 보조 여럿 ───────────────────────── */
  .kpi-row {{ display: grid; gap: {s['3']}; }}
  .kpi {{
    background: var(--surface); border: 1px solid var(--line);
    border-radius: var(--radius-md); padding: {s['4']} {s['4']} {s['4']} {s['4']};
    position: relative; overflow: hidden;
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

  /* hero KPI — 화면에서 가장 먼저 읽혀야 하는 하나 */
  .kpi-hero {{
    background: var(--surface); border: 1px solid var(--line);
    border-left: 3px solid var(--accent, var(--primary));
    box-shadow: var(--shadow-raise);
    border-radius: var(--radius-md); padding: {s['6']};
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
    margin-top: auto; padding-top: {s['2']}; border-top: 1px dashed var(--line);
    font-family: {MONO_STACK}; font-size: {t['label']}; color: var(--faint);
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
    display: flex; align-items: center; gap: {s['2']}; min-width: 132px;
  }}
  .riskbar .track {{ flex: 1; height: 5px; border-radius: 3px; background: var(--line-soft); }}
  .riskbar .fill {{ height: 100%; border-radius: 3px; }}
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
  .hero {{
    position: relative; overflow: hidden;
    background:
      radial-gradient(1100px 420px at 88% -20%, rgba(78,140,214,.30), transparent 62%),
      linear-gradient(135deg, {c['deep']} 0%, #143462 58%, #17406F 100%);
    border-radius: var(--radius-lg); padding: {s['12']} {s['12']} {s['8']} {s['12']};
    color: #FFFFFF;
  }}
  .hero::after {{
    content: ""; position: absolute; inset: 0; pointer-events: none;
    background-image: linear-gradient(rgba(255,255,255,.045) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px);
    background-size: 44px 44px; mask-image: linear-gradient(105deg, transparent 38%, #000 100%);
  }}
  .hero > * {{ position: relative; z-index: 1; }}
  .hero .eyebrow {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .16em;
    text-transform: uppercase; color: #8FB4E4;
  }}
  .hero h1 {{
    font-size: {t['display']}; font-weight: 700; color: #FFFFFF;
    letter-spacing: -.035em; line-height: 1.14; margin: {s['3']} 0 0 0;
  }}
  .hero .kr {{
    font-size: {t['h2']}; font-weight: 600; color: #C9DBF2;
    margin-top: {s['2']}; letter-spacing: -.01em;
  }}
  .hero p {{
    font-size: {t['body']}; line-height: 1.72; color: #B9CDE8;
    margin: {s['4']} 0 0 0; max-width: 62ch;
  }}
  .hero-meta {{
    display: flex; flex-wrap: wrap; gap: {s['8']};
    margin-top: {s['8']}; padding-top: {s['6']};
    border-top: 1px solid rgba(255,255,255,.16);
  }}
  .hero-meta .item .k {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .11em;
    text-transform: uppercase; color: #7FA5D6;
  }}
  .hero-meta .item .v {{
    font-size: {t['h2']}; font-weight: 700; color: #FFFFFF;
    margin-top: {s['1']}; font-variant-numeric: tabular-nums; letter-spacing: -.01em;
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
    background: var(--primary); border-color: var(--primary); color: #FFFFFF;
    box-shadow: var(--shadow-raise);
  }}
  .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
    background: {c['primary_hover']}; border-color: {c['primary_hover']}; color: #FFFFFF;
  }}

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
  .sb-block {{ margin-top: {s['4']}; }}
  .sb-block .k {{
    font-size: {t['label']}; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    color: var(--faint);
  }}
  .sb-block .v {{ font-size: {t['caption']}; color: var(--ink-soft); margin-top: {s['1']}; line-height: 1.55; }}
  .sb-block .v code {{ font-family: {MONO_STACK}; font-size: .95em; color: var(--muted); }}
  .sb-foot {{
    margin-top: {s['6']}; padding-top: {s['3']}; border-top: 1px solid var(--line);
    font-size: {t['label']}; color: var(--faint); line-height: 1.55;
  }}

  /* 스크롤바 — 기본 굵은 회색 막대가 발표 화면에서 눈에 띈다 */
  ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
  ::-webkit-scrollbar-thumb {{ background: #D3DBE6; border-radius: 6px; border: 2px solid var(--canvas); }}
  ::-webkit-scrollbar-thumb:hover {{ background: #BCC7D6; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}

  /* 좁은 화면에서 파이프라인/그리드가 찌그러지지 않게 */
  @media (max-width: 1180px) {{
    .flow {{ grid-template-columns: repeat(2, 1fr); }}
    .flow .step {{ border-right: 1px solid var(--line); border-radius: var(--radius-md); }}
    .hero {{ padding: {s['8']}; }}
    .hero h1 {{ font-size: 1.95rem; }}
  }}
</style>
"""


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
