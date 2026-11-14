"""Sistema visual Marketnus.
Paleta del logo: navy #0D0D5C · azul #1565C0 · cian #00BCD4 · dorado de marca #C9A44C
Títulos: Space Grotesk · Texto: Inter
"""
from __future__ import annotations

import html

import streamlit as st

NAVY = "#0D0D5C"
NAVY_2 = "#1A1A6E"
BLUE = "#1565C0"
CYAN = "#00BCD4"
CYAN_SOFT = "#E3F7FA"
GOLD = "#C9A44C"
GOLD_SOFT = "#F7F0DE"
INK = "#14162B"
GRAY = "#6B7085"
LINE = "#E4E6EF"
BG = "#FAFAFD"
GREEN = "#1E8A5A"
RED = "#B3261E"
SEQ = [NAVY, CYAN, GOLD, BLUE, "#7C83A6", "#3FA7B5", "#A88A3E", "#2F3A8F"]
BRAND_COLORS = {"Coursera": "#0056D2", "Udemy": "#A435F0", "Platzi": "#13B866", "Marketnus": GOLD}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], p, li, label, input, textarea, button, select, .stMarkdown {{ font-family: 'Inter', sans-serif !important; color: {INK}; }}
h1, h2, h3, h4, .grot {{ font-family: 'Space Grotesk', sans-serif !important; color: {NAVY}; letter-spacing: -.01em; }}
.stApp {{ background: {BG}; }}
.block-container {{ padding: 0 2.2rem 3rem; max-width: 1320px; }}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {{ display: none !important; }}
header[data-testid="stHeader"] {{ height: 0; background: transparent; }}
[data-testid="stSidebar"] {{ background: #fff; border-right: 1px solid {LINE}; }}

.mast {{ margin: 0 -2.2rem 22px; padding: 22px 2.2rem 0; background: linear-gradient(100deg, {NAVY} 0%, {NAVY_2} 55%, {BLUE} 100%); color: #fff; }}
.mast-row {{ display:flex; justify-content: space-between; align-items: flex-end; gap: 20px; flex-wrap: wrap; }}
.mast .brand {{ font-family: 'Space Grotesk', sans-serif; font-size: 2rem; font-weight: 700; line-height: 1; color: #fff; }}
.mast .brand span {{ color: {CYAN}; }}
.mast .sub {{ font-size: .76rem; letter-spacing: .16em; text-transform: uppercase; color: rgba(255,255,255,.66); margin-top: 8px; }}
.mast .meta {{ text-align: right; font-size: .8rem; color: rgba(255,255,255,.78); line-height: 1.55; }}
.mast .meta b {{ color: #fff; }}
.mast .rule {{ height: 4px; background: linear-gradient(90deg, {CYAN}, {GOLD}); margin: 18px -2.2rem 0; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 0; border-bottom: 1px solid {LINE}; flex-wrap: wrap; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 700; font-size: .9rem; color: {GRAY}; padding: 12px 16px; }}
.stTabs [aria-selected="true"] {{ color: {NAVY} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {CYAN} !important; height: 3px; }}

.eyebrow {{ font-size: .7rem; letter-spacing: .16em; text-transform: uppercase; color: {BLUE}; font-weight: 800; margin-top: 6px; }}
.h {{ font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; color: {NAVY}; font-weight: 700; margin: 2px 0 4px; line-height: 1.15; }}
.lede {{ color: {GRAY}; font-size: .9rem; margin-bottom: 14px; max-width: 80ch; }}

.stat {{ background:#fff; border:1px solid {LINE}; border-radius: 12px; padding: 15px 17px 13px; height: 100%; }}
.stat .l {{ font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:{GRAY}; }}
.stat .v {{ font-family:'Space Grotesk', sans-serif; font-size: 2.1rem; line-height: 1.05; color:{NAVY}; font-weight:700; margin-top: 6px; }}
.stat .v small {{ font-size: .95rem; color: {GRAY}; font-family: 'Inter', sans-serif; font-weight: 600; margin-left: 4px; }}
.stat .s {{ font-size:.8rem; color:{GRAY}; margin-top: 4px; }}
.stat.accent {{ background:{NAVY}; border-color:{NAVY}; }}
.stat.accent .l {{ color: rgba(255,255,255,.65); }}
.stat.accent .v {{ color:#fff; }}
.stat.accent .s {{ color: rgba(255,255,255,.8); }}
.up {{ color: {GREEN}; font-weight: 800; }} .down {{ color: {RED}; font-weight: 800; }}

.insight {{ display:flex; gap: 16px; align-items: center; background: {CYAN_SOFT}; border-radius: 12px; padding: 13px 18px; margin: 6px 0 16px; }}
.insight .n {{ font-family:'Space Grotesk', sans-serif; font-size: 2rem; color: {NAVY}; font-weight:700; line-height: 1; min-width: 70px; }}
.insight .t {{ font-size: .93rem; color: {INK}; }}
.note {{ background: {GOLD_SOFT}; border-left: 3px solid {GOLD}; padding: 10px 14px; font-size: .86rem; border-radius: 0 8px 8px 0; margin: 4px 0 14px; color: {INK}; }}

.card {{ background:#fff; border:1px solid {LINE}; border-radius: 14px; overflow:hidden; height:100%; display:flex; flex-direction:column; }}
.card .band {{ height: 5px; }}
.card .body {{ padding: 13px 15px 15px; display:flex; flex-direction:column; gap: 7px; flex: 1; }}
.card .when {{ font-size:.68rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:{BLUE}; }}
.card .ttl {{ font-family:'Space Grotesk', sans-serif; font-size: 1.12rem; color:{NAVY}; font-weight:700; line-height:1.2; }}
.card .txt {{ font-size:.86rem; color:{INK}; }}
.card .muted {{ font-size:.78rem; color:{GRAY}; }}
.card ol {{ margin: 0 0 0 1.1rem; padding: 0; font-size: .82rem; color: {INK}; }}
.tags {{ display:flex; gap:6px; flex-wrap:wrap; margin-top: auto; }}
.tag {{ font-size:.7rem; font-weight:700; padding: 3px 9px; border-radius: 999px; background:#F3F4F9; color:{NAVY}; border:1px solid {LINE}; }}
.tag.dark {{ background:{NAVY}; color:#fff; border-color:{NAVY}; }}
.tag.cyan {{ background:{CYAN_SOFT}; color:{NAVY}; border-color:{CYAN}; }}
.tag.gold {{ background:{GOLD_SOFT}; color:#6B5420; border-color:{GOLD}; }}

.row-item {{ display:flex; justify-content:space-between; align-items:center; padding: 9px 0; border-bottom:1px solid {LINE}; gap: 10px; }}
.row-item .a {{ font-weight:700; color:{NAVY}; font-size: .9rem; }}
.row-item .b {{ font-size:.76rem; color:{GRAY}; }}
.pill {{ font-size:.74rem; font-weight:800; padding: 3px 9px; border-radius: 8px; background:#F3F4F9; color:{NAVY}; white-space: nowrap; }}
.pill.up {{ background:#E6F4EC; color:{GREEN}; }} .pill.down {{ background:#FBE9E8; color:{RED}; }}
.chip {{ display:inline-block; padding: 5px 11px; margin: 3px 6px 3px 0; border-radius: 999px; font-size: .8rem; font-weight:600; border:1px solid {LINE}; color:{NAVY}; background:#fff; }}

.comp {{ background:#fff; border:1px solid {LINE}; border-radius: 14px; padding: 15px 16px; height: 100%; }}
.comp .nm {{ font-family:'Space Grotesk', sans-serif; font-size:1.3rem; font-weight:700; }}
.comp .k {{ font-size:.68rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:{GRAY}; margin-top:10px; }}
.comp .v {{ font-size:.86rem; color:{INK}; }}
.comp ul {{ margin: 4px 0 0 1rem; padding:0; font-size:.84rem; }}
.comp.dark li, .comp.dark .v {{ color: #fff !important; }}
.comp a {{ font-size:.72rem; color:{BLUE}; }}

.foot {{ text-align:center; font-size:.76rem; color:{GRAY}; margin-top: 40px; padding-top: 14px; border-top:1px solid {LINE}; }}
.foot b {{ color:{NAVY}; }}
.small {{ font-size:.8rem; color:{GRAY}; }}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{ border-radius: 10px; font-weight: 700; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background:{NAVY} !important; border-color:{NAVY} !important; color:#fff !important; }}
.stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] p {{ color:#fff !important; }}
[data-testid="stBaseButton-segmented_controlActive"] {{ background:{NAVY} !important; border-color:{NAVY} !important; }}
[data-testid="stBaseButton-segmented_controlActive"] p {{ color:#fff !important; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def head(eyebrow: str, title: str, lede: str | None = None) -> None:
    st.markdown(f'<div class="eyebrow">{esc(eyebrow)}</div><div class="h">{esc(title)}</div>'
                + (f'<div class="lede">{lede}</div>' if lede else ""), unsafe_allow_html=True)


def stat(label: str, value, sub: str = "", unit: str = "", accent: bool = False) -> str:
    return (f'<div class="stat{" accent" if accent else ""}"><div class="l">{esc(label)}</div>'
            f'<div class="v">{esc(value)}{f"<small>{esc(unit)}</small>" if unit else ""}</div><div class="s">{sub}</div></div>')


def insight(number: str, text: str) -> None:
    st.markdown(f'<div class="insight"><div class="n">{esc(number)}</div><div class="t">{text}</div></div>',
                unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def idea_card(i: dict, color: str = CYAN) -> str:
    steps = "".join(f"<li>{esc(s)}</li>" for s in i["guion"])
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in i["hashtags"])
    curso = f'<span class="tag gold">{esc(i["curso"])}</span>' if i.get("curso") else ""
    return (f'<div class="card"><div class="band" style="background:{color}"></div><div class="body">'
            f'<div class="when">{esc(i["plataforma"])} · oportunidad {i["oportunidad"]}</div>'
            f'<div class="ttl">{esc(i["titulo"])}</div>'
            f'<div class="muted">{esc(i["formato"])}</div><ol>{steps}</ol>'
            f'<div class="txt"><b>CTA:</b> {esc(i["cta"])}</div>'
            f'<div class="tags"><span class="tag dark">{esc(i["keyword"])}</span>{curso}{tags}</div></div></div>')


def chips(items) -> str:
    return "".join(f'<span class="chip">{esc(t)}</span>' for t in items)


def fig_style(fig, height=320, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=0, r=8, t=8, b=0),
        font=dict(family="Inter, sans-serif", color=INK, size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend, legend=dict(orientation="h", y=-0.2, x=0, title=None, font=dict(size=11)),
        hoverlabel=dict(font_family="Inter, sans-serif", bgcolor="#fff"),
        bargap=0.35,
    )
    fig.update_xaxes(gridcolor=LINE, zeroline=False, linecolor=LINE, tickfont=dict(color=GRAY))
    fig.update_yaxes(gridcolor=LINE, zeroline=False, linecolor=LINE, tickfont=dict(color=INK))
    return fig


CHART_CFG = {"displayModeBar": False}
