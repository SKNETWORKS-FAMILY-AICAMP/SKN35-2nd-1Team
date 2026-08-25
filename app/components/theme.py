"""
디자인 토큰과 공통 스타일.

색·간격·차트 레이아웃을 여기 한 곳에서만 정의한다. 화면 파일에 색상 코드를
직접 적지 않는다 — 발표 직전에 톤을 바꿀 때 한 파일만 고치면 되도록.

방침
    · Streamlit 기본 컴포넌트를 먼저 쓰고, CSS 는 기본 컴포넌트로 표현되지 않는
      카드·배지·요인 막대에만 얇게 얹는다.
    · 애니메이션 없음. 발표 화면에서 시선을 뺏는 요소를 만들지 않는다.
    · 라이트 테마 고정 (.streamlit/config.toml). 발표 PC 설정에 따라 색이
      달라지면 안 되기 때문이다.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# 색 토큰
# ---------------------------------------------------------------------------

COLORS = {
    "ink": "#0F172A",         # 본문 텍스트
    "ink_soft": "#475569",    # 보조 텍스트
    "muted": "#7C8AA0",       # 캡션
    "line": "#E4E9F0",        # 경계선
    "surface": "#FFFFFF",     # 카드 배경
    "canvas": "#F5F7FA",      # 페이지 배경
    "primary": "#1E4B8F",     # 강조 (대학 행정 톤의 진한 블루)
    "primary_soft": "#E9F0F9",
    "deep": "#0B2545",        # 시작화면 히어로 배경
}

#: 위험등급 색 — 화면 전체(배지·표·차트)에서 같은 값을 쓴다.
RISK_COLORS = {"HIGH": "#C2453D", "MEDIUM": "#B77606", "LOW": "#1F7A5C"}
RISK_SOFT = {"HIGH": "#FBEDEB", "MEDIUM": "#FCF3E2", "LOW": "#E9F5EF"}

#: 위험요인 카테고리 색 (services.predictor.RISK_CATEGORIES 의 키와 같다)
CATEGORY_COLORS = {
    "academic": "#1E4B8F",
    "financial": "#B77606",
    "adaptation": "#5B6B8C",
}

#: 이진 Target 색 (팀 전처리 기준 1=Dropout / 0=Non-Dropout)
CLASS_COLORS = {
    "Dropout": "#C2453D",
    "Non-Dropout": "#1F7A5C",
}

#: 시작화면 지구본 색. 히어로와 같은 딥네이비 계열로 잡아 페이지의 시선 축을 하나로 만든다.
#  옅은 색으로 그리면 배경에 묻혀 "무언가 덜 그려진 화면"처럼 보인다 — 대비를 세게 준다.
PORTUGAL = {
    "ocean": "#12335C",
    "land": "#2C5E96",
    "border": "rgba(255,255,255,.28)",
    "graticule": "rgba(255,255,255,.16)",
    "highlight": "#FF6B5B",
    "halo": "rgba(255,107,91,.30)",
}

FONT_STACK = (
    "'Pretendard', 'Pretendard Variable', -apple-system, BlinkMacSystemFont, "
    "'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif"
)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _css() -> str:
    c = COLORS
    return f"""
<style>
  /* 본문 폰트. 아이콘 폰트(Material Symbols)까지 덮으면 아이콘이 글자로 깨지므로
     상속되는 최상위에만 걸고, 아이콘 요소는 아래에서 원래 폰트로 되돌린다. */
  html, body, .stApp {{ font-family: {FONT_STACK}; }}
  [data-testid="stIconMaterial"],
  span.material-symbols-rounded,
  span.material-symbols-outlined,
  .material-icons {{ font-family: "Material Symbols Rounded" !important; }}
  .stApp {{ background: {c['canvas']}; }}
  .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1320px; }}

  /* ---- 페이지 헤더 ---------------------------------------------------- */
  .page-head {{ margin-bottom: 1.4rem; }}
  .page-head h1 {{
    font-size: 1.65rem; font-weight: 700; color: {c['ink']};
    margin: 0 0 .35rem 0; letter-spacing: -.02em;
  }}
  .page-head p {{ color: {c['ink_soft']}; font-size: .93rem; margin: 0; line-height: 1.6; }}

  /* ---- 섹션 제목 ------------------------------------------------------ */
  .section-title {{
    font-size: 1.02rem; font-weight: 700; color: {c['ink']};
    margin: 1.9rem 0 .2rem 0; padding-left: .55rem;
    border-left: 3px solid {c['primary']};
  }}
  .section-desc {{ color: {c['muted']}; font-size: .84rem; margin: 0 0 .8rem .6rem; }}

  /* ---- KPI 카드 -------------------------------------------------------- */
  .kpi-grid {{ display: grid; gap: .7rem; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }}
  .kpi-card {{
    background: {c['surface']}; border: 1px solid {c['line']}; border-radius: 12px;
    padding: 1rem 1.05rem; border-top: 3px solid var(--accent, {c['primary']});
  }}
  .kpi-label {{ font-size: .8rem; color: {c['muted']}; font-weight: 600; letter-spacing: -.01em; }}
  .kpi-value {{
    font-size: 1.95rem; font-weight: 700; color: var(--accent, {c['ink']});
    line-height: 1.25; margin-top: .25rem; font-variant-numeric: tabular-nums;
  }}
  .kpi-caption {{ font-size: .78rem; color: {c['muted']}; margin-top: .1rem; }}

  /* ---- 위험등급 배지 ---------------------------------------------------- */
  .risk-badge {{
    display: inline-block; padding: .28rem .8rem; border-radius: 999px;
    font-weight: 700; font-size: .85rem; letter-spacing: .01em;
  }}
  .risk-badge.lg {{ font-size: 1.05rem; padding: .42rem 1.15rem; }}

  /* ---- 일반 카드 ------------------------------------------------------- */
  .card {{
    background: {c['surface']}; border: 1px solid {c['line']};
    border-radius: 12px; padding: 1.15rem 1.25rem;
  }}
  .card + .card {{ margin-top: .6rem; }}
  .card-title {{ font-weight: 700; color: {c['ink']}; font-size: .95rem; margin-bottom: .15rem; }}
  .card-sub {{ color: {c['muted']}; font-size: .82rem; }}

  /* ---- 확률 막대 ------------------------------------------------------- */
  .prob-row {{ display: flex; align-items: center; gap: .7rem; margin-bottom: .5rem; }}
  .prob-name {{ width: 92px; font-size: .87rem; color: {c['ink_soft']}; font-weight: 600; }}
  .prob-track {{ flex: 1; height: 9px; background: #EDF1F6; border-radius: 999px; overflow: hidden; }}
  .prob-fill {{ height: 100%; border-radius: 999px; }}
  .prob-value {{
    width: 54px; text-align: right; font-size: .87rem; font-weight: 700;
    color: {c['ink']}; font-variant-numeric: tabular-nums;
  }}

  /* ---- 위험요인 목록 ---------------------------------------------------- */
  .factor {{ padding: .62rem 0; border-bottom: 1px dashed {c['line']}; }}
  .factor:last-child {{ border-bottom: none; }}
  .factor-head {{ display: flex; align-items: baseline; gap: .5rem; }}
  .factor-rank {{
    font-size: .75rem; font-weight: 700; color: {c['muted']};
    min-width: 18px; font-variant-numeric: tabular-nums;
  }}
  .factor-label {{ font-weight: 600; color: {c['ink']}; font-size: .92rem; }}
  .factor-chip {{
    font-size: .7rem; font-weight: 700; padding: .1rem .45rem;
    border-radius: 5px; background: {c['primary_soft']}; color: {c['primary']};
  }}
  .factor-detail {{ font-size: .8rem; color: {c['muted']}; margin: .15rem 0 .3rem 26px; }}
  .factor-track {{ height: 6px; background: #EDF1F6; border-radius: 999px; margin-left: 26px; }}
  .factor-fill {{ height: 100%; border-radius: 999px; }}

  /* ---- 추천 카드 ------------------------------------------------------- */
  .rule-card {{
    background: {c['surface']}; border: 1px solid {c['line']};
    border-left: 3px solid var(--accent, {c['primary']});
    border-radius: 10px; padding: .85rem 1rem; margin-bottom: .55rem;
  }}
  .rule-head {{ display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }}
  .rule-title {{ font-weight: 700; color: {c['ink']}; font-size: .93rem; }}
  .rule-id {{ font-size: .72rem; color: {c['muted']}; font-family: ui-monospace, monospace; }}
  .rule-reason {{ font-size: .84rem; color: {c['ink_soft']}; margin: .3rem 0 .55rem 0; }}
  .program {{ font-size: .85rem; color: {c['ink']}; padding: .2rem 0; }}
  .program .owner {{ color: {c['muted']}; font-size: .78rem; margin-left: .3rem; }}
  .program .action {{ display: block; color: {c['ink_soft']}; font-size: .8rem; margin-left: 1.1rem; }}

  /* ---- 배너 ------------------------------------------------------------ */
  .banner {{
    border-radius: 10px; padding: .75rem 1rem; font-size: .86rem;
    border: 1px solid var(--accent, {c['line']}); background: var(--bg, {c['primary_soft']});
    color: {c['ink']}; line-height: 1.55;
  }}
  .banner b {{ color: var(--accent, {c['primary']}); }}

  .disclaimer {{
    font-size: .78rem; color: {c['muted']}; line-height: 1.6;
    border-top: 1px solid {c['line']}; padding-top: .7rem; margin-top: .9rem;
  }}

  /* ---- 시작화면 히어로 --------------------------------------------------- */
  .hero {{
    background: linear-gradient(135deg, {c['deep']} 0%, {c['primary']} 100%);
    border-radius: 16px; padding: 2.1rem 2.2rem; color: #FFFFFF;
  }}
  .hero .eyebrow {{
    font-size: .78rem; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: #9DBBE4;
  }}
  .hero h1 {{
    font-size: 2.05rem; font-weight: 700; margin: .5rem 0 .6rem 0;
    letter-spacing: -.03em; line-height: 1.25; color: #FFFFFF;
  }}
  .hero p {{ font-size: .95rem; line-height: 1.7; color: #D6E2F2; margin: 0; }}
  .hero .flow {{
    margin-top: 1.3rem; display: flex; flex-wrap: wrap; gap: .45rem; align-items: center;
  }}
  .hero .step {{
    background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22);
    border-radius: 999px; padding: .32rem .85rem; font-size: .83rem; font-weight: 600;
  }}
  .hero .arrow {{ color: #7EA3D6; font-size: .9rem; }}

  /* ---- 이식성(다른 나라 적용) 카드 --------------------------------------- */
  .port-card {{
    background: {c['surface']}; border: 1px solid {c['line']}; border-radius: 12px;
    padding: 1.1rem 1.2rem; height: 100%;
  }}
  .port-card h4 {{
    font-size: .92rem; font-weight: 700; color: {c['ink']}; margin: 0 0 .4rem 0;
  }}
  .port-card p {{ font-size: .84rem; color: {c['ink_soft']}; line-height: 1.65; margin: 0; }}
  .port-card .tag {{
    display: inline-block; font-size: .7rem; font-weight: 700; padding: .12rem .5rem;
    border-radius: 5px; background: {c['primary_soft']}; color: {c['primary']};
    margin-bottom: .5rem;
  }}

  /* ---- Streamlit 기본 컴포넌트 미세 조정 --------------------------------- */
  div[data-testid="stMetricValue"] {{ font-size: 1.6rem; }}
  section[data-testid="stSidebar"] {{ background: {c['surface']}; border-right: 1px solid {c['line']}; }}
  section[data-testid="stSidebar"] .block-container {{ padding-top: 1.6rem; }}
  div[data-testid="stDataFrame"] {{ border: 1px solid {c['line']}; border-radius: 10px; }}
</style>
"""


def inject_css() -> None:
    """페이지마다 1회 호출한다.

    멀티페이지에서는 페이지를 옮길 때마다 스크립트가 새로 실행되므로,
    진입점에서 한 번만 넣으면 스타일이 유실될 수 있다. 각 페이지가 직접 부른다.
    """
    st.markdown(_css(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 차트 공통
# ---------------------------------------------------------------------------

#: plotly 툴바를 숨긴다 (발표 화면에서 불필요한 UI).
PLOTLY_CONFIG = {"displayModeBar": False, "staticPlot": False}


def style_figure(fig, height: int = 260, show_legend: bool = False):
    """모든 차트에 같은 여백·폰트·배경을 입힌다."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, size=13, color=COLORS["ink_soft"]),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, x=0),
        hoverlabel=dict(font_family=FONT_STACK, font_size=12),
        separators=".,",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=COLORS["line"])
    fig.update_yaxes(
        showgrid=True, gridcolor=COLORS["line"], zeroline=False, linecolor="rgba(0,0,0,0)"
    )
    return fig
