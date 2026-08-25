"""
시작화면의 지구본 — 이 서비스가 **포르투갈 데이터**로 만들어졌음을 한눈에 보여준다.

두 가지 구현을 둔다.

    1. Plotly 정사영(orthographic) 지구본 — 마우스로 돌릴 수 있다.
    2. 인라인 SVG 지구본 — 외부 통신이 0이다.

왜 둘인가
    Plotly 의 지도(geo) 계열 그래프는 국가 경계 데이터(topojson)를 실행 시점에
    CDN 에서 받아온다. 발표장 네트워크가 막혀 있으면 **빈 원**이 뜬다.
    발표에서 그 사고가 나면 되돌릴 방법이 없으므로, 좌표 계산까지 파이썬에서 끝내는
    SVG 판을 함께 두고 상수 하나로 갈아 끼울 수 있게 했다.

    `USE_PLOTLY_GLOBE = False` 로 바꾸면 화면 코드는 그대로 두고 SVG 로 바뀐다.
"""

from __future__ import annotations

import base64
import math
from html import escape

import plotly.graph_objects as go

from components.theme import COLORS, FONT_STACK, PORTUGAL

#: True = Plotly 지구본(돌릴 수 있음), False = SVG 지구본(외부 통신 없음)
USE_PLOTLY_GLOBE = True

#: 포르투갈 본토의 대략적인 중심 (리스본 북쪽)
PORTUGAL_LON, PORTUGAL_LAT = -8.2, 39.6

#: 지구본을 바라보는 시점. 포르투갈이 정면에 오되 유럽·아프리카가 함께 보이도록 살짝 틀었다.
VIEW_LON, VIEW_LAT = -12.0, 32.0

#: 포르투갈 본토 외곽선(단순화). 위경도 (lon, lat) 를 시계 방향으로 돈다.
#  국경을 정밀하게 그리려는 것이 아니라 "이 나라"를 알아보게 하는 용도다.
PORTUGAL_OUTLINE: tuple[tuple[float, float], ...] = (
    (-8.87, 41.88), (-8.22, 42.13), (-7.42, 41.87), (-6.55, 41.94), (-6.19, 41.57),
    (-6.85, 41.02), (-6.94, 40.35), (-7.02, 39.67), (-7.54, 39.66), (-7.15, 39.10),
    (-7.34, 38.46), (-7.10, 38.18), (-7.27, 37.44), (-7.42, 37.18), (-7.86, 36.99),
    (-8.60, 37.10), (-8.99, 37.03), (-8.82, 37.44), (-8.79, 38.07), (-9.00, 38.41),
    (-9.48, 38.71), (-9.35, 39.35), (-8.87, 39.83), (-8.78, 40.60), (-8.73, 41.15),
)


# ---------------------------------------------------------------------------
# 1. Plotly 지구본
# ---------------------------------------------------------------------------

def plotly_globe(height: int = 380) -> go.Figure:
    """포르투갈을 강조한 정사영 지구본."""
    fig = go.Figure(
        go.Choropleth(
            locations=["PRT"],
            locationmode="ISO-3",
            z=[1],
            colorscale=[[0, PORTUGAL["highlight"]], [1, PORTUGAL["highlight"]]],
            showscale=False,
            marker_line_color="#FFFFFF",
            marker_line_width=0.8,
            hovertemplate="포르투갈<br>UCI 원본 데이터의 수집 국가<extra></extra>",
        )
    )
    # 포르투갈은 지구본 크기에서 점만 해진다. 뒤에 옅은 광륜을 깔아 눈에 먼저 걸리게 한다.
    fig.add_trace(
        go.Scattergeo(
            lon=[PORTUGAL_LON],
            lat=[PORTUGAL_LAT],
            mode="markers",
            marker=dict(size=34, color=PORTUGAL["halo"], line=dict(width=0)),
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lon=[PORTUGAL_LON],
            lat=[PORTUGAL_LAT],
            mode="markers+text",
            marker=dict(size=10, color=PORTUGAL["highlight"],
                        line=dict(color="#FFFFFF", width=1.6)),
            text=["  PORTUGAL"],
            textposition="middle right",
            textfont=dict(family=FONT_STACK, size=13, color="#FFFFFF"),
            hovertemplate="포르투갈<br>UCI 원본 데이터의 수집 국가<extra></extra>",
        )
    )
    fig.update_geos(
        projection_type="orthographic",
        projection_rotation=dict(lon=VIEW_LON, lat=VIEW_LAT),
        projection_scale=1.06,
        showland=True,
        landcolor=PORTUGAL["land"],
        showocean=True,
        oceancolor=PORTUGAL["ocean"],
        showlakes=False,
        showcountries=True,
        countrycolor=PORTUGAL["border"],
        countrywidth=0.5,
        showcoastlines=True,
        coastlinecolor="rgba(255,255,255,.45)",
        coastlinewidth=0.7,
        showframe=True,
        framecolor="rgba(255,255,255,.35)",
        framewidth=1,
        bgcolor="rgba(0,0,0,0)",
        lataxis_showgrid=True,
        lonaxis_showgrid=True,
        lataxis_gridcolor=PORTUGAL["graticule"],
        lonaxis_gridcolor=PORTUGAL["graticule"],
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        dragmode="orbit",
        # 마커 trace 를 두 개 겹쳐 광륜을 만들었기 때문에 범례를 켜 두면
        # "trace 1 / trace 2" 가 그대로 노출된다.
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# 2. SVG 지구본 (외부 통신 없음)
# ---------------------------------------------------------------------------

def _project(lon: float, lat: float, lon0: float, lat0: float) -> tuple[float, float, bool]:
    """정사영(orthographic) 투영. 반환값은 (x, y, 앞면인가)."""
    rad = math.radians
    dlon = rad(lon - lon0)
    lat_r, lat0_r = rad(lat), rad(lat0)
    cos_c = math.sin(lat0_r) * math.sin(lat_r) + math.cos(lat0_r) * math.cos(lat_r) * math.cos(dlon)
    x = math.cos(lat_r) * math.sin(dlon)
    y = math.cos(lat0_r) * math.sin(lat_r) - math.sin(lat0_r) * math.cos(lat_r) * math.cos(dlon)
    return x, y, cos_c >= 0


def _polyline(points: list[tuple[float, float]], radius: float, cx: float, cy: float) -> str:
    """투영 좌표(-1~1) → SVG points 문자열. y 축은 화면 좌표라 뒤집는다."""
    return " ".join(f"{cx + x * radius:.2f},{cy - y * radius:.2f}" for x, y in points)


def _graticule(radius: float, cx: float, cy: float) -> str:
    """경위선 격자. 앞면에 보이는 구간만 잇는다."""
    parts: list[str] = []
    style = 'fill="none" stroke="rgba(255,255,255,.28)" stroke-width="1"'

    for lat in range(-60, 61, 30):                      # 위선
        run: list[tuple[float, float]] = []
        for step in range(0, 361, 3):
            x, y, front = _project(step - 180, lat, VIEW_LON, VIEW_LAT)
            if front:
                run.append((x, y))
            elif run:
                parts.append(f'<polyline points="{_polyline(run, radius, cx, cy)}" {style}/>')
                run = []
        if run:
            parts.append(f'<polyline points="{_polyline(run, radius, cx, cy)}" {style}/>')

    for lon in range(-180, 180, 30):                    # 경선
        run = []
        for step in range(-90, 91, 3):
            x, y, front = _project(lon, step, VIEW_LON, VIEW_LAT)
            if front:
                run.append((x, y))
            elif run:
                parts.append(f'<polyline points="{_polyline(run, radius, cx, cy)}" {style}/>')
                run = []
        if run:
            parts.append(f'<polyline points="{_polyline(run, radius, cx, cy)}" {style}/>')

    return "".join(parts)


def svg_globe(size: int = 340) -> str:
    """포르투갈을 표시한 SVG 지구본. 외부 리소스를 전혀 쓰지 않는다.

    캔버스는 정사각형이 아니라 가로로 길다 — 왼쪽에 지구본, 오른쪽에 포르투갈 외곽선
    인셋을 두어 둘이 겹치지 않게 한다.
    """
    width = size * 1.45
    cx, cy = size * 0.46, size / 2
    radius = size * 0.42

    px, py, _ = _project(PORTUGAL_LON, PORTUGAL_LAT, VIEW_LON, VIEW_LAT)
    mark_x, mark_y = cx + px * radius, cy - py * radius

    # 포르투갈을 실제 크기로 지구본에 얹으면 점만 해진다.
    # 위치는 마커로 찍고, 나라 모양은 오른쪽 인셋에 크게 그린다.
    lons = [p[0] for p in PORTUGAL_OUTLINE]
    lats = [p[1] for p in PORTUGAL_OUTLINE]
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    inset_h = size * 0.46
    inset_w = inset_h * (lon_max - lon_min) / (lat_max - lat_min)
    inset_x = width - inset_w - size * 0.10
    inset_y = cy - inset_h / 2
    outline = " ".join(
        f"{inset_x + (lon - lon_min) / (lon_max - lon_min) * inset_w:.2f},"
        f"{inset_y + (lat_max - lat) / (lat_max - lat_min) * inset_h:.2f}"
        for lon, lat in PORTUGAL_OUTLINE
    )

    return f"""
<svg viewBox="0 0 {width:.0f} {size}" width="{width:.0f}" height="{size}"
     role="img" aria-label="포르투갈을 표시한 지구본"
     xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="globe-sphere" cx="34%" cy="28%" r="78%">
      <stop offset="0%" stop-color="#3B79B8"/>
      <stop offset="45%" stop-color="{PORTUGAL['ocean']}"/>
      <stop offset="100%" stop-color="#08203C"/>
    </radialGradient>
  </defs>

  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius + 7:.1f}"
          fill="{COLORS['primary']}" opacity=".10"/>
  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="url(#globe-sphere)"/>
  {_graticule(radius, cx, cy)}
  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="none"
          stroke="#FFFFFF" stroke-opacity=".35" stroke-width="1.2"/>

  <line x1="{mark_x:.2f}" y1="{mark_y:.2f}" x2="{inset_x - 14:.2f}" y2="{cy:.1f}"
        stroke="{PORTUGAL['highlight']}" stroke-width="1.1" stroke-dasharray="3 3" opacity=".55"/>
  <circle cx="{mark_x:.2f}" cy="{mark_y:.2f}" r="12" fill="{PORTUGAL['highlight']}" opacity=".22"/>
  <circle cx="{mark_x:.2f}" cy="{mark_y:.2f}" r="6" fill="{PORTUGAL['highlight']}"
          stroke="#FFFFFF" stroke-width="2"/>

  <polygon points="{outline}" fill="{PORTUGAL['highlight']}" fill-opacity=".18"
           stroke="{PORTUGAL['highlight']}" stroke-width="1.8" stroke-linejoin="round"/>
  <text x="{inset_x:.2f}" y="{inset_y - 12:.2f}" font-family="{FONT_STACK}"
        font-size="14" font-weight="700" fill="{COLORS['ink']}">PORTUGAL</text>
  <text x="{inset_x:.2f}" y="{inset_y + inset_h + 20:.2f}" font-family="{FONT_STACK}"
        font-size="11" fill="{COLORS['muted']}">UCI 데이터 수집 국가</text>
</svg>
"""


# ---------------------------------------------------------------------------
# 화면이 부르는 단일 진입점
# ---------------------------------------------------------------------------

def render(height: int = 340) -> None:
    """시작화면에 지구본을 그린다. 어떤 구현을 쓸지는 이 함수만 안다."""
    import streamlit as st

    if USE_PLOTLY_GLOBE:
        from components.theme import PLOTLY_CONFIG

        st.plotly_chart(
            plotly_globe(height),
            width="stretch",
            config={**PLOTLY_CONFIG, "scrollZoom": False},
            key="home_globe",
        )
        st.caption("드래그하면 지구본이 회전합니다. 붉게 표시된 곳이 포르투갈입니다.")
    else:
        # Streamlit 의 HTML 살균기는 <svg> 를 통째로 걸러낸다 (st.markdown 도 st.html 도 마찬가지).
        # <img> 는 통과하므로 SVG 를 data URI 로 감싸서 넣는다. 여전히 외부 통신은 0이다.
        encoded = base64.b64encode(svg_globe(height).strip().encode("utf-8")).decode("ascii")
        st.markdown(
            f'<img src="data:image/svg+xml;base64,{encoded}" '
            'alt="포르투갈을 표시한 지구본" '
            'style="width:100%;height:auto;display:block;margin:0 auto"/>',
            unsafe_allow_html=True,
        )
        st.caption("붉게 표시된 곳이 포르투갈입니다.")


_KEEP = escape  # 향후 라벨을 동적으로 넣을 때 쓴다.
