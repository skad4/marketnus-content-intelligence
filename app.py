"""Marketnus Content Intelligence
Qué contenido publicar para Marketnus: keywords de Google y YouTube, tendencias,
competencia (Coursera, Udemy, Platzi), hashtags y calendario.

Ejecutar:  streamlit run app.py
Datos:     pipeline semanal (GitHub Actions) -> data/latest.json
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import copylab
import ideas as ideas_mod
import ui
from scoring import BRAND_CLUSTER, brand_share, build_keywords, intent, load_json

ROOT = Path(__file__).parent
LATEST = ROOT / "data" / "latest.json"
HISTORY = ROOT / "data" / "history"

st.set_page_config(page_title="Marketnus · Content Intelligence", page_icon="📈", layout="wide",
                   initial_sidebar_state="collapsed")
ui.inject_css()


# --------------------------------------------------------------------------- datos
@st.cache_data(ttl=600)
def load_latest() -> dict:
    if LATEST.exists():
        return json.loads(LATEST.read_text(encoding="utf-8"))
    return {}


@st.cache_data(ttl=600)
def load_history() -> pd.DataFrame | None:
    files = sorted(HISTORY.glob("*.csv")) if HISTORY.exists() else []
    if len(files) < 2:
        return None
    prev = pd.read_csv(files[-2]).set_index("keyword")
    return prev


def parse_trends_csv(raw: bytes) -> dict:
    """Lee un multiTimeline.csv exportado de Google Trends."""
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.lower().startswith(("week", "semana", "month", "mes", "day", "día")))
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])))
    df.columns = [c.split(":")[0].strip() for c in df.columns]
    date_col = df.columns[0]
    out = {}
    for c in df.columns[1:]:
        vals = pd.to_numeric(df[c].astype(str).str.replace("<1", "0.5"), errors="coerce").fillna(0).tolist()
        out[c.lower()] = {"dates": pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d").tolist(), "values": vals}
    return out


latest = load_latest()
if st.session_state.get("uploaded_series"):
    latest = json.loads(json.dumps(latest)) if latest else {}
    tr = latest.setdefault("trends", {"source": "CSV subido", "series": {}, "regions": {}, "rising": []})
    tr.setdefault("series", {}).update(st.session_state["uploaded_series"])

courses = load_json("courses.json")
competitors = load_json("competitors.json")
social = load_json("social.json")
instagram = load_json("instagram.json")


def fmt_n(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".replace(".", ",").replace(",0", "") + " M"
    if n >= 1_000:
        return f"{n / 1_000:.0f} K"
    return f"{n:,.0f}".replace(",", ".")


def ig_section(data: dict) -> None:
    """Comparativa de Instagram: Marketnus (@marketnuss) contra Coursera, Udemy y Platzi."""
    df = pd.DataFrame(data["cuentas"])
    df["tasa"] = df["eng_medio"] / df["seguidores"] * 100
    df["com_rate"] = df["comentarios_medio"] / df["seguidores"] * 100
    mk = df[df["marca"] == "Marketnus"].iloc[0]
    rivals = df[df["marca"] != "Marketnus"]
    ui.head("Instagram", "Marketnus vs competencia en Instagram",
            f"Perfiles públicos leídos el {data['capturado']}. Engagement = me gusta + comentarios por publicación, "
            "promedio de las publicaciones recientes con contador visible. Tasa = engagement medio ÷ seguidores.")

    best_rival = rivals.sort_values("tasa", ascending=False).iloc[0]
    c = st.columns(4)
    c[0].markdown(ui.stat("Seguidores @marketnuss", fmt_n(mk["seguidores"]),
                          f"Platzi tiene {rivals.loc[rivals.marca == 'Platzi', 'seguidores'].iloc[0] / mk['seguidores']:,.0f}× más".replace(",", "."),
                          accent=True), unsafe_allow_html=True)
    c[1].markdown(ui.stat("Tasa de engagement", f"{mk['tasa']:.1f}".replace(".", ","), 
                          f"{best_rival['marca']}: {best_rival['tasa']:.2f}%".replace(".", ","), unit="%"), unsafe_allow_html=True)
    c[2].markdown(ui.stat("Interacciones por post", f"{mk['eng_medio']:.0f}",
                          f"Platzi {rivals.loc[rivals.marca == 'Platzi', 'eng_medio'].iloc[0]:.0f} · Udemy {rivals.loc[rivals.marca == 'Udemy', 'eng_medio'].iloc[0]:.0f}"),
                  unsafe_allow_html=True)
    c[3].markdown(ui.stat("Ritmo de publicación", f"{mk['por_semana']:.1f}".replace(".", ","),
                          f"último post {mk['ultima']} · Coursera 2,8/sem · Udemy 8,8/sem", unit="/sem"), unsafe_allow_html=True)
    st.write("")

    order = ["Marketnus", "Platzi", "Coursera", "Udemy"]
    view = st.segmented_control("Métrica", ["Seguidores", "Tasa de engagement", "Interacciones por post", "Comentarios por post"],
                                default="Tasa de engagement", key="ig_metric")
    col = {"Seguidores": "seguidores", "Tasa de engagement": "tasa", "Interacciones por post": "eng_medio",
           "Comentarios por post": "comentarios_medio"}[view or "Tasa de engagement"]
    d = df.set_index("marca").loc[order].reset_index()
    labels = [fmt_n(v) if col == "seguidores" else (f"{v:.2f}%".replace(".", ",") if col == "tasa" else f"{v:.0f}") for v in d[col]]
    fig = go.Figure(go.Bar(x=d["marca"], y=d[col], text=labels, textposition="outside",
                           marker_color=[ui.BRAND_COLORS[m] for m in d["marca"]],
                           hovertemplate="%{x}: %{text}<extra></extra>"))
    if col in ("seguidores", "tasa"):
        fig.update_yaxes(type="log", showticklabels=False)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    a, b = st.columns([1.15, 1])
    with a:
        st.plotly_chart(ui.fig_style(fig, 320, legend=False), width="stretch", config=ui.CHART_CFG)
        if col in ("seguidores", "tasa"):
            st.markdown('<div class="small">Escala logarítmica: las diferencias son de varios órdenes de magnitud.</div>',
                        unsafe_allow_html=True)
    with b:
        t = d.assign(
            Cuenta=lambda x: "@" + x["handle"],
            Seguidores=lambda x: x["seguidores"].map(fmt_n),
            Publicaciones=lambda x: x["publicaciones"].map(lambda v: f"{v:,}".replace(",", ".")),
            Tasa=lambda x: x["tasa"].map(lambda v: f"{v:.2f}%".replace(".", ",")),
            Interacciones=lambda x: x["eng_medio"].round(0).astype(int),
            Comentarios=lambda x: x["comentarios_medio"].round(0).astype(int),
            Ritmo=lambda x: [r.get("frecuencia_texto") or (f"{r['por_semana']:.1f}/sem".replace(".", ",")) for _, r in x.iterrows()],
            Muestra=lambda x: x["muestra"].astype(str) + " posts",
        )[["marca", "Cuenta", "Seguidores", "Publicaciones", "Tasa", "Interacciones", "Comentarios", "Ritmo", "Muestra"]]
        st.dataframe(t.rename(columns={"marca": "Marca"}), hide_index=True, width="stretch")

    ui.head("Qué les funciona", "Engagement por tipo de contenido",
            "Promedio de interacciones por publicación según el tema del post (clasificado por palabras clave del texto).")
    rows = [{"marca": a["marca"], "pilar": p, "posts": a["mix"][p], "eng": a["mix_eng"][p]}
            for a in data["cuentas"] for p in a["mix"]]
    pdf = pd.DataFrame(rows)
    fig2 = px.bar(pdf, x="eng", y="pilar", color="marca", orientation="h", barmode="group",
                  color_discrete_map=ui.BRAND_COLORS, custom_data=["posts"],
                  category_orders={"marca": order})
    fig2.update_traces(hovertemplate="%{y}: %{x:.0f} interacciones · %{customdata[0]} posts<extra></extra>")
    fig2.update_xaxes(title="Interacciones por post", type="log")
    fig2.update_yaxes(title=None)
    st.plotly_chart(ui.fig_style(fig2, 330), width="stretch", config=ui.CHART_CFG)

    p_ia = data["cuentas"][[x["marca"] for x in data["cuentas"]].index("Platzi")]["mix_eng"]
    ratio = p_ia["IA y herramientas"] / p_ia["Promoción y precios"]
    ui.insight(f"{mk['tasa']:.1f}%".replace(".", ","),
               f"<b>Tu comunidad es la más activa en proporción</b> ({mk['tasa']:.1f}% vs {best_rival['tasa']:.2f}% de {best_rival['marca']}), "
               f"pero el alcance es mínimo: {mk['seguidores']:.0f} seguidores y {mk['por_semana']:.1f} posts por semana. "
               "La tasa alta es normal en cuentas pequeñas; el cuello de botella es el volumen y la constancia.")
    ui.insight(f"{ratio:.0f}×",
               f"En Platzi, los posts de <b>IA y herramientas</b> logran {ratio:.0f} veces más interacción que los de promoción "
               f"({p_ia['IA y herramientas']:,.0f} vs {p_ia['Promoción y precios']:,.0f}). 3 de tus 5 posts recientes son promocionales: "
               "cambia la mezcla hacia tips de IA aplicada y deja la promo para 1 de cada 4 publicaciones.")
    ui.insight("3/sem",
               "Meta mínima para salir de la invisibilidad: <b>3 publicaciones por semana</b> (Coursera publica ~2,8 con 2 M de seguidores). "
               "Los Reels de la pestaña Calendario ya están listos para cubrir ese ritmo.")
    ui.note("Muestra pequeña: algunas cuentas ocultan los me gusta (Udemy en 7 de 12 posts), así que el promedio usa solo los visibles. "
            "Para actualizar, corre <code>tools/ig_scan.js</code> en Chrome con sesión iniciada y pega el resultado en "
            "<code>config/instagram.json</code>.")
kw = build_keywords(latest)
prev_hist = load_history()
has_trends = (kw["fuente"] == "Google Trends").any()
ac = latest.get("autocomplete") or {}
tt = latest.get("tiktok") or {}

# semana actual del plan de publicación
start = date.fromisoformat(courses["inicio_publicacion"])
today = date.today()
course_list = sorted(courses["cursos"], key=lambda c: c["semana"])
if today < start:
    current = course_list[0]
    week_label = f"Arranca el {start:%d %b}"
else:
    wk = (today - start).days // 7 + 1
    current = next((c for c in course_list if c["semana"] == wk), course_list[-1])
    week_label = f"Semana {wk}"

upd = latest.get("updated_at")
upd_txt = datetime.fromisoformat(upd).strftime("%d %b %Y") if upd else "sin datos en vivo todavía"
src_txt = "Google Trends + autocompletado" if has_trends else ("Autocompletado + estimación inicial" if ac else "Estimación inicial")

st.markdown(
    f'<div class="mast"><div class="mast-row"><div><div class="brand">Marketnus <span>Content Intelligence</span></div>'
    f'<div class="sub">Qué publicar · Google · YouTube · TikTok · Instagram · Competencia</div></div>'
    f'<div class="meta">Datos: <b>{ui.esc(src_txt)}</b><br>Actualizado: <b>{ui.esc(upd_txt)}</b><br>Developer: <b>Ed Trigueros</b></div>'
    f'</div><div class="rule"></div></div>', unsafe_allow_html=True)

if not has_trends:
    ui.note("Las métricas de demanda son una <b>estimación inicial</b> hasta que corra el pipeline semanal "
            "(GitHub Actions, cada lunes). Cuando llegue Google Trends, la columna «Fuente» cambia sola.")

T = st.tabs(["Esta semana", "Keywords", "Tendencias", "Competencia", "Redes", "Calendario", "Copy Lab", "Datos y fuentes"])
work = kw[kw["cluster"] != BRAND_CLUSTER]

# =========================================================================== 1. ESTA SEMANA
with T[0]:
    rising = work[work["momentum"] > 15] if has_trends else work.iloc[0:0]
    top = work.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(ui.stat("Keywords monitoreadas", len(work), f"{work['cluster'].nunique()} temas · {len(kw) - len(work)} de marcas"), unsafe_allow_html=True)
    c2.markdown(ui.stat("En alza", len(rising) if has_trends else "—",
                        "suben más de 15% en 12 semanas" if has_trends else "llega con Google Trends"), unsafe_allow_html=True)
    c3.markdown(ui.stat("Mejor oportunidad", int(top["oportunidad"]), ui.esc(top["keyword"]), unit="/100"), unsafe_allow_html=True)
    c4.markdown(ui.stat("Curso de la semana", current["nombre"], week_label, accent=True), unsafe_allow_html=True)
    st.write("")

    mine = work[work["curso"] == current["id"]]
    best_mine = mine.iloc[0] if len(mine) else top
    ui.insight(f"{int(best_mine['oportunidad'])}",
               f"Para empujar <b>{ui.esc(current['nombre'])}</b>, la keyword con más oportunidad es "
               f"<b>«{ui.esc(best_mine['keyword'])}»</b> ({ui.esc(best_mine['intencion'].lower())}, competencia "
               f"{ui.esc(best_mine['kd_label'].lower())}). Formato sugerido: {ui.esc(best_mine['formato'])}.")

    ui.head("Publica esto", "6 piezas para esta semana",
            "Mezcla keywords del curso de la semana con las de mayor oportunidad general, sin repetir formato.")
    picks, seen_fmt = [], set()
    for _, r in pd.concat([mine, work]).drop_duplicates("keyword").iterrows():
        if r["plataforma"] in seen_fmt and len(seen_fmt) < 5:
            continue
        picks.append(ideas_mod.idea(r, social))
        seen_fmt.add(r["plataforma"])
        if len(picks) == 6:
            break
    colors = [ui.CYAN, ui.GOLD, ui.BLUE, ui.NAVY, ui.CYAN, ui.GOLD]
    for row in range(2):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            k = row * 3 + j
            if k < len(picks):
                col.markdown(ui.idea_card(picks[k], colors[k]), unsafe_allow_html=True)
        st.write("")

    a, b = st.columns(2)
    with a:
        ui.head("Movimiento", "Suben y bajan")
        if has_trends:
            mv = work.dropna(subset=["momentum"]).sort_values("momentum", ascending=False)
            html_rows = ""
            for _, r in pd.concat([mv.head(5), mv.tail(3)]).iterrows():
                cls = "up" if r["momentum"] >= 0 else "down"
                html_rows += (f'<div class="row-item"><div><div class="a">{ui.esc(r["keyword"])}</div>'
                              f'<div class="b">{ui.esc(r["cluster"])}</div></div>'
                              f'<span class="pill {cls}">{r["momentum"]:+.0f}%</span></div>')
            st.markdown(html_rows, unsafe_allow_html=True)
        else:
            st.markdown('<div class="small">Aparece cuando llegue la primera serie de Google Trends.</div>', unsafe_allow_html=True)
    with b:
        ui.head("Lo que pregunta la gente", "Preguntas reales del buscador")
        qs = []
        for q, sugg in (ac.get("google") or {}).items():
            if any(w in q for w in ["qué es", "cómo usar", "cómo hacer"]):
                qs += sugg[:2]
        if qs:
            st.markdown(ui.chips(list(dict.fromkeys(qs))[:18]), unsafe_allow_html=True)
        else:
            st.markdown('<div class="small">Se llena con el autocompletado de Google y YouTube en la próxima actualización.</div>',
                        unsafe_allow_html=True)

# =========================================================================== 2. KEYWORDS
with T[1]:
    ui.head("Keyword Magic", "Todas las keywords, con su oportunidad",
            "Demanda y momentum vienen de Google Trends; competencia y encaje son estimaciones explicadas en «Datos y fuentes». "
            "Ordena por cualquier columna.")
    f1, f2, f3, f4 = st.columns([2, 1.4, 1.4, 1.2])
    clusters = f1.multiselect("Tema", sorted(kw["cluster"].unique()), placeholder="Todos (sin marcas)")
    clusters = clusters or [c for c in kw["cluster"].unique() if c != BRAND_CLUSTER]
    intents = f2.multiselect("Intención", sorted(kw["intencion"].unique()), placeholder="Todas")
    curso_opts = ["Todos"] + [c["nombre"] for c in course_list] + ["Sin curso"]
    curso_sel = f3.selectbox("Curso", curso_opts)
    min_d = f4.slider("Demanda mínima", 0, 100, 0, 5)
    qtext = st.text_input("Buscar", placeholder="ej. chatgpt, tienda, seo")

    v = kw[kw["cluster"].isin(clusters) & (kw["demanda"] >= min_d)]
    if intents:
        v = v[v["intencion"].isin(intents)]
    if curso_sel == "Sin curso":
        v = v[v["curso"] == ""]
    elif curso_sel != "Todos":
        v = v[v["curso_nombre"] == curso_sel]
    if qtext:
        v = v[v["keyword"].str.contains(qtext.lower(), regex=False)]

    cols_show = ["keyword", "cluster", "demanda", "serie", "momentum", "competencia", "kd_label", "encaje", "oportunidad",
                 "intencion", "plataforma", "curso_nombre", "fuente"]
    if not has_trends:
        cols_show = [c for c in cols_show if c not in ("serie", "momentum")]
    show = v[cols_show].copy()
    st.dataframe(
        show, hide_index=True, width="stretch", height=430,
        column_config={
            "keyword": st.column_config.TextColumn("Keyword", width="medium"),
            "cluster": "Tema",
            "demanda": st.column_config.ProgressColumn("Demanda", min_value=0, max_value=100, format="%d"),
            "serie": st.column_config.LineChartColumn("12 meses", width="small"),
            "momentum": st.column_config.NumberColumn("Momentum", format="%+.0f%%"),
            "competencia": st.column_config.NumberColumn("KD", format="%d", help="Dificultad estimada 0–100"),
            "kd_label": "Dificultad",
            "encaje": st.column_config.NumberColumn("Encaje", format="%d"),
            "oportunidad": st.column_config.ProgressColumn("Oportunidad", min_value=0, max_value=100, format="%d"),
            "intencion": "Intención", "plataforma": "Dónde publicar", "curso_nombre": "Curso", "fuente": "Fuente",
        })
    st.download_button("Descargar CSV", v.drop(columns=["serie"]).to_csv(index=False).encode("utf-8"),
                       "keywords_marketnus.csv", "text/csv")

    st.write("")
    m1, m2 = st.columns([1.3, 1])
    with m1:
        ui.head("Matriz", "Demanda contra dificultad", "Arriba a la izquierda: mucha demanda y poca competencia. Ahí se gana rápido.")
        mv = v[v["cluster"] != BRAND_CLUSTER]
        fig = px.scatter(mv, x="competencia", y="demanda", size="oportunidad", color="cluster", hover_name="keyword",
                         color_discrete_sequence=ui.SEQ, size_max=26)
        fig.add_vline(x=50, line_dash="dot", line_color=ui.LINE)
        fig.add_hline(y=50, line_dash="dot", line_color=ui.LINE)
        fig.add_annotation(x=8, y=98, text="Ganar rápido", showarrow=False, font=dict(color=ui.GREEN, size=12), xanchor="left")
        fig.add_annotation(x=98, y=98, text="Pelea de gigantes", showarrow=False, font=dict(color=ui.RED, size=12), xanchor="right")
        fig.update_xaxes(title="Dificultad (KD)", range=[0, 102])
        fig.update_yaxes(title="Demanda", range=[0, 104])
        st.plotly_chart(ui.fig_style(fig, 420), width="stretch", config=ui.CHART_CFG)
    with m2:
        ui.head("Por tema", "Oportunidad media por tema")
        g = (v[v["cluster"] != BRAND_CLUSTER].groupby("cluster", as_index=False)
             .agg(oportunidad=("oportunidad", "mean"), n=("keyword", "count")).sort_values("oportunidad"))
        fig = px.bar(g, x="oportunidad", y="cluster", orientation="h", text=g["oportunidad"].round(0),
                     color_discrete_sequence=[ui.NAVY])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_xaxes(title=None, range=[0, 100])
        fig.update_yaxes(title=None)
        st.plotly_chart(ui.fig_style(fig, 420, legend=False), width="stretch", config=ui.CHART_CFG)

    st.divider()
    ui.head("Detalle", "Análisis de una keyword")
    sel = st.selectbox("Keyword", v["keyword"].tolist() or kw["keyword"].tolist(), label_visibility="collapsed")
    r = kw[kw["keyword"] == sel].iloc[0]
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.markdown(ui.stat("Demanda", int(r["demanda"]), r["fuente"]), unsafe_allow_html=True)
    mom = "—" if pd.isna(r["momentum"]) else f"{r['momentum']:+.0f}%"
    d2.markdown(ui.stat("Momentum", mom, "12 sem. vs 12 anteriores"), unsafe_allow_html=True)
    d3.markdown(ui.stat("Dificultad", int(r["competencia"]), r["kd_label"]), unsafe_allow_html=True)
    d4.markdown(ui.stat("Encaje", int(r["encaje"]), r["curso_nombre"] or "sin curso directo"), unsafe_allow_html=True)
    d5.markdown(ui.stat("Oportunidad", int(r["oportunidad"]), r["intencion"], accent=True), unsafe_allow_html=True)
    st.write("")
    e1, e2 = st.columns([1.4, 1])
    series = ((latest.get("trends") or {}).get("series") or {}).get(sel)
    regions = ((latest.get("trends") or {}).get("regions") or {}).get(sel)
    with e1:
        if series:
            s = pd.DataFrame({"fecha": pd.to_datetime(series["dates"]), "interés": series["values"]})
            fig = px.area(s, x="fecha", y="interés", color_discrete_sequence=[ui.BLUE])
            fig.update_traces(line_width=2, fillcolor="rgba(21,101,192,.12)")
            fig.update_xaxes(title=None)
            fig.update_yaxes(title="Interés (escala común)")
            st.plotly_chart(ui.fig_style(fig, 260, legend=False), width="stretch", config=ui.CHART_CFG)
        else:
            st.markdown('<div class="small">Sin serie de Google Trends todavía para esta keyword.</div>', unsafe_allow_html=True)
        if regions:
            rg = pd.DataFrame({"país": list(regions), "interés": list(regions.values())}).sort_values("interés").tail(10)
            fig = px.bar(rg, x="interés", y="país", orientation="h", color_discrete_sequence=[ui.CYAN])
            fig.update_xaxes(title="Interés por país (0–100)")
            fig.update_yaxes(title=None)
            st.plotly_chart(ui.fig_style(fig, 240, legend=False), width="stretch", config=ui.CHART_CFG)
    with e2:
        b = (ac.get("breadth") or {}).get(sel, {})
        related = list(dict.fromkeys((b.get("google_top") or []) + (b.get("youtube_top") or [])))
        brief = ideas_mod.content_brief(r, related)
        st.markdown(f'<div class="comp"><div class="k">Título SEO</div><div class="v"><b>{ui.esc(brief["title"])}</b> '
                    f'<span class="small">({len(brief["title"])} car.)</span></div>'
                    f'<div class="k">Meta description</div><div class="v">{ui.esc(brief["meta"])} '
                    f'<span class="small">({len(brief["meta"])} car.)</span></div>'
                    f'<div class="k">Estructura H2</div><ul>{"".join(f"<li>{ui.esc(h)}</li>" for h in brief["h2"])}</ul>'
                    + (f'<div class="k">Preguntas para FAQ (buscador)</div><ul>{"".join(f"<li>{ui.esc(q)}</li>" for q in brief["faqs"])}</ul>' if brief["faqs"] else "")
                    + '</div>', unsafe_allow_html=True)
    st.write("")
    st.markdown(ui.idea_card(ideas_mod.idea(r, social), ui.GOLD), unsafe_allow_html=True)

# =========================================================================== 3. TENDENCIAS
with T[2]:
    trends = latest.get("trends") or {}
    if not has_trends:
        ui.head("Tendencias", "Demanda estimada por tema",
                "Esta pestaña muestra series semanales, estacionalidad y mapa por país cuando corre el pipeline de Google Trends. "
                "Mientras tanto, este es el punto de partida estimado.")
        g = work.groupby("cluster", as_index=False)["demanda"].mean().sort_values("demanda")
        fig = px.bar(g, x="demanda", y="cluster", orientation="h", color_discrete_sequence=[ui.BLUE],
                     text=g["demanda"].round(0))
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_xaxes(title="Demanda media estimada", range=[0, 100])
        fig.update_yaxes(title=None)
        st.plotly_chart(ui.fig_style(fig, 380, legend=False), width="stretch", config=ui.CHART_CFG)
    else:
        rows = []
        for _, r in work[work["fuente"] == "Google Trends"].iterrows():
            s = trends["series"][r["keyword"]]
            rows += [{"fecha": d, "cluster": r["cluster"], "keyword": r["keyword"], "v": x} for d, x in zip(s["dates"], s["values"])]
        long = pd.DataFrame(rows)
        long["fecha"] = pd.to_datetime(long["fecha"])
        ui.head("Tendencias", "Interés semanal por tema", "Suma del interés de las keywords de cada tema en Google Trends "
                + ("México" if trends.get("geo", "MX") == "MX" else ui.esc(trends.get("geo", ""))) + ", en escala común (keyword ancla: «"
                + ui.esc(trends.get("anchor", "")) + "»).")
        by_c = long.groupby(["fecha", "cluster"], as_index=False)["v"].sum()
        pick = st.multiselect("Temas", sorted(by_c["cluster"].unique()), default=sorted(by_c["cluster"].unique())[:5],
                              placeholder="Elige temas")
        fig = px.line(by_c[by_c["cluster"].isin(pick)], x="fecha", y="v", color="cluster", color_discrete_sequence=ui.SEQ)
        fig.update_xaxes(title=None)
        fig.update_yaxes(title="Interés")
        st.plotly_chart(ui.fig_style(fig, 340), width="stretch", config=ui.CHART_CFG)

        a, b = st.columns(2)
        with a:
            ui.head("Estacionalidad", "En qué meses sube cada tema", "100 = el mejor mes del tema. Útil para planear lanzamientos.")
            long["mes"] = long["fecha"].dt.month
            sz = long.groupby(["cluster", "mes"])["v"].mean().unstack().fillna(0)
            sz = sz.div(sz.max(axis=1).replace(0, 1), axis=0) * 100
            meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
            fig = go.Figure(go.Heatmap(z=sz.values, x=[meses[m - 1] for m in sz.columns], y=sz.index,
                                       colorscale=[[0, "#F3F4F9"], [.5, ui.CYAN], [1, ui.NAVY]], showscale=False,
                                       hovertemplate="%{y} · %{x}: %{z:.0f}<extra></extra>"))
            st.plotly_chart(ui.fig_style(fig, 330, legend=False), width="stretch", config=ui.CHART_CFG)
        with b:
            ui.head("Mapa", "Dónde está el interés", "Promedio del interés por país en todas las keywords con datos.")
            regs = trends.get("regions") or {}
            if regs:
                import pycountry
                agg: dict[str, list[int]] = {}
                for vals in regs.values():
                    for cc, val in vals.items():
                        agg.setdefault(cc, []).append(val)
                mp = pd.DataFrame([{"iso2": k, "interés": sum(v) / len(v)} for k, v in agg.items()])
                mp["iso3"] = mp["iso2"].map(lambda c: pycountry.countries.get(alpha_2=c).alpha_3)
                fig = px.choropleth(mp, locations="iso3", color="interés", hover_name="iso2",
                                    color_continuous_scale=[[0, "#E3F7FA"], [1, ui.NAVY]])
                fig.update_geos(scope="world", showframe=False, showcoastlines=False, projection_type="natural earth",
                                lataxis_range=[-58, 50], lonaxis_range=[-120, 10])
                fig.update_layout(coloraxis_showscale=False)
                st.plotly_chart(ui.fig_style(fig, 330, legend=False), width="stretch", config=ui.CHART_CFG)
            else:
                st.markdown('<div class="small">Sin datos por país esta semana.</div>', unsafe_allow_html=True)

        ui.head("Búsquedas en ascenso", "Lo que más está creciendo en Google",
                "«Breakout» significa que la búsqueda creció más de 5.000% en los últimos 3 meses.")
        rq = pd.DataFrame(trends.get("rising") or [])
        if len(rq):
            rq = rq.rename(columns={"seed": "Tema base", "query": "Búsqueda", "value": "Crecimiento"})
            rq["Crecimiento"] = rq["Crecimiento"].map(lambda x: "Breakout" if str(x) in ("Breakout", "5000") or str(x).isdigit() and int(x) >= 5000 else f"+{x}%")
            st.dataframe(rq, hide_index=True, width="stretch", height=320)
        else:
            st.markdown('<div class="small">Google no devolvió búsquedas en ascenso esta semana.</div>', unsafe_allow_html=True)

# =========================================================================== 4. COMPETENCIA
with T[3]:
    ui.head("Competencia", "Coursera, Udemy y Platzi",
            f"Datos públicos revisados el {competitors['actualizado']}. Coursera y Udemy son una sola empresa desde mayo de 2026, "
            "pero siguen operando como plataformas separadas.")
    cols = st.columns(4)
    for col, c in zip(cols, competitors["competidores"]):
        trend_li = "".join(f"<li>{ui.esc(t)}</li>" for t in c["tendencias"])
        col.markdown(
            f'<div class="comp" style="border-top:4px solid {c["color"]}"><div class="nm" style="color:{c["color"]}">{ui.esc(c["nombre"])}</div>'
            f'<div class="k">Modelo</div><div class="v">{ui.esc(c["modelo"])}</div>'
            f'<div class="k">Precio</div><div class="v">{ui.esc(c["precio"])} <a href="{c["precio_fuente"]}" target="_blank">fuente</a></div>'
            f'<div class="k">Escala</div><div class="v">{ui.esc(c["escala"])} <a href="{c["escala_fuente"]}" target="_blank">fuente</a></div>'
            f'<div class="k">Redes</div><div class="v">{ui.esc(c["redes"]["instagram"])} <a href="{c["redes"]["fuente"]}" target="_blank">fuente</a></div>'
            f'<div class="k">Qué están empujando</div><ul>{trend_li}</ul><a href="{c["tendencias_fuente"]}" target="_blank">fuente</a>'
            f'<div class="k">Dónde son débiles</div><ul>{"".join(f"<li>{ui.esc(x)}</li>" for x in c["debilidades"])}</ul></div>',
            unsafe_allow_html=True)
    pos = "".join(f"<li>{ui.esc(x)}</li>" for x in competitors["posicionamiento_marketnus"])
    cols[3].markdown(f'<div class="comp dark" style="border-top:4px solid {ui.GOLD}; background:{ui.NAVY}">'
                     f'<div class="nm" style="color:{ui.GOLD}">Marketnus</div>'
                     f'<div class="k" style="color:rgba(255,255,255,.6)">Precio</div><div class="v" style="color:#fff">€{str(courses["precio_curso_eur"]).replace(".", ",")} por curso, sin suscripción</div>'
                     f'<div class="k" style="color:rgba(255,255,255,.6)">Cómo ganarles</div><ul style="color:#fff">{pos}</ul></div>',
                     unsafe_allow_html=True)

    st.write("")
    a, b = st.columns([1.2, 1])
    with a:
        ui.head("Share of search", "Quién se busca más en Google", "Interés de búsqueda de cada marca en la misma escala.")
        bs = brand_share(latest)
        if bs is not None:
            fig = px.line(bs, x="fecha", y="interes", color="marca", color_discrete_map=ui.BRAND_COLORS)
            fig.update_xaxes(title=None)
            fig.update_yaxes(title="Interés")
            st.plotly_chart(ui.fig_style(fig, 320), width="stretch", config=ui.CHART_CFG)
            last = bs[bs["fecha"] >= bs["fecha"].max() - pd.Timedelta(weeks=12)].groupby("marca")["interes"].mean()
            share = (last / last.sum() * 100).round(1).sort_values(ascending=False)
            st.markdown(ui.chips([f"{m}: {v}%" for m, v in share.items()]), unsafe_allow_html=True)
        else:
            est = kw[kw["keyword"].isin(["coursera", "udemy", "platzi", "marketnus"])][["keyword", "demanda"]]
            fig = px.bar(est, x="keyword", y="demanda", color="keyword",
                         color_discrete_map={k.lower(): v for k, v in ui.BRAND_COLORS.items()})
            fig.update_xaxes(title=None)
            fig.update_yaxes(title="Demanda estimada")
            st.plotly_chart(ui.fig_style(fig, 300, legend=False), width="stretch", config=ui.CHART_CFG)
            st.markdown('<div class="small">Estimación inicial. La serie real llega con Google Trends.</div>', unsafe_allow_html=True)
    with b:
        ui.head("Lo que buscan de ellos", "Marca + tema en el buscador",
                "Qué escribe la gente junto al nombre de cada competidor: te dice qué cursos les compran.")
        brands = ac.get("brands") or {}
        if brands:
            for bname, lst in brands.items():
                st.markdown(f'<div class="k" style="font-weight:800;font-size:.75rem;color:{ui.GRAY};margin-top:6px">'
                            f'{ui.esc(bname.upper())}</div>' + ui.chips(lst[:10]), unsafe_allow_html=True)
        else:
            st.markdown('<div class="small">Se llena con el autocompletado en la próxima actualización.</div>', unsafe_allow_html=True)

    st.write("")
    ig_section(instagram)

    st.write("")
    ui.head("Cobertura", "Quién enseña qué", "Evaluación cualitativa de los catálogos públicos. Los huecos marcados son temas donde Marketnus es fuerte y la competencia no.")
    topics = competitors["cobertura_temas"]
    lv = {"Fuerte": 3, "Media": 2, "Débil": 1}
    names = {"coursera": "Coursera", "udemy": "Udemy", "platzi": "Platzi", "marketnus": "Marketnus"}
    z = [[lv[x] for x in competitors["cobertura"][k]] for k in names]
    fig = go.Figure(go.Heatmap(z=z, x=topics, y=list(names.values()), text=[competitors["cobertura"][k] for k in names],
                               texttemplate="%{text}", colorscale=[[0, "#F3F4F9"], [.5, "#9EDCE6"], [1, ui.NAVY]],
                               showscale=False, hovertemplate="%{y} · %{x}: %{text}<extra></extra>", xgap=3, ygap=3))
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(ui.fig_style(fig, 330, legend=False), width="stretch", config=ui.CHART_CFG)
    gaps = [t for i, t in enumerate(topics) if competitors["cobertura"]["marketnus"][i] == "Fuerte"
            and sum(competitors["cobertura"][k][i] != "Fuerte" for k in ["coursera", "udemy", "platzi"]) >= 2]
    ui.insight(str(len(gaps)), "Temas donde Marketnus puede liderar: <b>" + ", ".join(ui.esc(g) for g in gaps) + "</b>. "
               "Prioriza contenido de estos temas: compites contra menos.")

# =========================================================================== 5. REDES
with T[4]:
    ui.head("Redes", "TikTok, Instagram, YouTube y LinkedIn",
            "TikTok e Instagram no publican sus búsquedas. Para video usamos el autocompletado de YouTube como señal, "
            "más los hashtags de TikTok Creative Center cuando responde.")
    net = st.segmented_control("Red", ["TikTok", "Instagram", "YouTube", "LinkedIn"], default="TikTok", label_visibility="collapsed")
    a, b = st.columns([1, 1.2])
    with a:
        topic = st.selectbox("Tema", [c for c in social["hashtags"] if c != "General educación"])
        rec = ideas_mod.hashtags_for(topic, social, n=5 if net == "TikTok" else 4)
        if net in ("TikTok", "Instagram"):
            ui.head("Set recomendado", f"{len(rec)} hashtags para {net}",
                    "1 amplio para alcance, 2 de nicho para que el algoritmo entienda el tema y 1 de educación.")
            st.code(" ".join(rec), language=None)
            lst = social["hashtags"][topic]
            st.markdown("".join(f'<div class="row-item"><div class="a">{ui.esc(h["tag"])}</div>'
                                f'<span class="pill">{ui.esc(h["tamaño"])}</span></div>' for h in lst), unsafe_allow_html=True)
        else:
            st.markdown('<div class="small">En YouTube y LinkedIn los hashtags pesan poco: lo que manda es el título y las primeras líneas.</div>',
                        unsafe_allow_html=True)
        st.write("")
        ui.head("Cuándo publicar", f"Horarios sugeridos en {net}")
        st.markdown(ui.chips(social["horarios"].get(net, [])), unsafe_allow_html=True)
        st.markdown(f'<div class="small">{ui.esc(social["horarios"]["_nota"])}</div>', unsafe_allow_html=True)
    with b:
        if net == "TikTok":
            ui.head("TikTok Creative Center", "Hashtags populares esta semana")
            items = pd.DataFrame(tt.get("items") or [])
            if len(items):
                only_edu = st.toggle("Solo temas de educación y negocio", value=True)
                if only_edu:
                    items = items[items["edu"]]
                st.dataframe(items[["country", "tag", "rank", "posts", "views"]].rename(columns={
                    "country": "País", "tag": "Hashtag", "rank": "Puesto", "posts": "Publicaciones", "views": "Vistas"}),
                    hide_index=True, width="stretch", height=300)
            else:
                ui.note("Creative Center no respondió en la última corrida. Revisa a mano en "
                        "<a href='https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/es' target='_blank'>TikTok Creative Center</a> "
                        "(filtra por México y categoría Educación).")
            st.markdown(f'<div class="small">{ui.esc(social["reglas"]["tiktok_engagement_latam"])} · '
                        f'<a href="{social["reglas"]["tiktok_engagement_fuente"]}" target="_blank">fuente</a></div>', unsafe_allow_html=True)
        ui.head("Búsquedas en video", "Lo que la gente busca en YouTube",
                "Si aparece en YouTube, también se busca en TikTok. Usa estas frases tal cual en el primer texto en pantalla.")
        yt = ac.get("youtube") or {}
        topic_words = topic.lower().split()[0][:5]
        hits = []
        for q, sugg in yt.items():
            if any(w in q for w in [topic_words, "curso", "cómo"]):
                hits += sugg[:3]
        if hits:
            st.markdown(ui.chips(list(dict.fromkeys(hits))[:24]), unsafe_allow_html=True)
        else:
            st.markdown('<div class="small">Se llena con el autocompletado de YouTube en la próxima actualización.</div>', unsafe_allow_html=True)
        st.write("")
        ui.head("Formato", "Qué funciona en esta red")
        guide = {
            "TikTok": ["Gancho en el primer segundo con texto en pantalla", "La keyword dicha en voz y escrita en el caption: TikTok funciona como buscador",
                       "Videos de 1–3 min rinden bien en LATAM para temas educativos", "3–5 hashtags, no más"],
            "Instagram": ["Carruseles de 7–10 slides para guardar (tutoriales, prompts, checklists)", "Reels de 30–60 s con subtítulos",
                          "Máximo 5 hashtags por publicación", "Keyword en la primera línea del caption"],
            "YouTube": ["Keyword al inicio del título (40–70 caracteres)", "Capítulos en la descripción", "Miniatura con 3–4 palabras",
                        "Shorts para captar, videos largos para vender el curso"],
            "LinkedIn": ["Casos reales con números (Blackhawk, Visa, Mastercard)", "Texto con espacios y una idea por línea",
                         "Carrusel PDF para frameworks", "Pregunta al final para conversación"],
        }[net]
        st.markdown("".join(f'<div class="row-item"><div class="a" style="font-weight:600">{ui.esc(g)}</div></div>' for g in guide),
                    unsafe_allow_html=True)

# =========================================================================== 6. CALENDARIO
with T[5]:
    cal = ideas_mod.calendar(kw, courses, social)
    ui.head("Calendario", f"Plan de {cal['Semana'].nunique()} semanas alineado con la migración de cursos",
            f"Un curso nuevo por semana desde el {start:%d %b %Y}. Cada semana: un video corto, un carrusel, una pieza larga "
            "(YouTube o blog) y un post de LinkedIn, usando las keywords con más oportunidad de ese curso.")
    piezas = st.multiselect("Piezas", cal["Pieza"].unique().tolist(), placeholder="Todas las piezas")
    piezas = piezas or cal["Pieza"].unique().tolist()
    cv = cal[cal["Pieza"].isin(piezas)]
    st.dataframe(cv, hide_index=True, width="stretch", height=460,
                 column_config={"Oportunidad": st.column_config.ProgressColumn("Oportunidad", min_value=0, max_value=100, format="%d")})
    st.download_button("Descargar calendario (CSV)", cv.to_csv(index=False).encode("utf-8"), "calendario_marketnus.csv", "text/csv")
    pending = len(course_list) < 13
    if pending:
        ui.note(f"Hay {len(course_list)} cursos cargados de 13. Agrega los que faltan en <code>config/courses.json</code> "
                "y el calendario se extiende solo.")

# =========================================================================== 7. COPY LAB
with T[6]:
    ui.head("Copy Lab", "Revisa tu texto antes de publicar",
            "Reglas de 2026: keyword en la primera línea (TikTok e Instagram la usan para búsqueda), gancho corto, CTA y máximo 5 hashtags en Instagram.")
    a, b = st.columns([1.2, 1])
    with a:
        fmt = st.selectbox("Formato", list(copylab.FORMATS))
        k = st.text_input("Keyword objetivo", value=str(work.iloc[0]["keyword"]))
        txt = st.text_area("Texto", height=200, placeholder="Pega aquí tu caption o título…")
        meta = st.text_area("Meta description", height=80) if fmt == "Título + meta de blog" else ""
    with b:
        if txt.strip():
            sc, checks = copylab.score(txt, fmt, k, meta)
            color = ui.GREEN if sc >= 75 else ui.GOLD if sc >= 50 else ui.RED
            fig = go.Figure(go.Indicator(mode="gauge+number", value=sc, number={"suffix": "/100", "font": {"color": ui.NAVY}},
                                         gauge={"axis": {"range": [0, 100], "visible": False}, "bar": {"color": color},
                                                "bgcolor": "#F3F4F9", "borderwidth": 0}))
            st.plotly_chart(ui.fig_style(fig, 200, legend=False), width="stretch", config=ui.CHART_CFG)
            st.markdown("".join(f'<div class="row-item"><div class="a" style="font-weight:600">{"✅" if ok else "⚠️"} {ui.esc(m)}</div></div>'
                                for ok, m in checks), unsafe_allow_html=True)
        else:
            st.markdown('<div class="small">Escribe un texto para ver la puntuación.</div>', unsafe_allow_html=True)
    st.write("")
    ui.head("Ideas de gancho", f"Tres arranques para «{k}»")
    row = kw[kw["keyword"] == k]
    it = row.iloc[0]["intencion"] if len(row) else intent(k)
    it = it if it in ideas_mod.HOOKS else "Concepto"
    hooks = [ideas_mod._fill(h, k) for h in ideas_mod.HOOKS.get(it, ideas_mod.HOOKS["Concepto"])]
    st.markdown("".join(f'<div class="row-item"><div class="a">{ui.esc(h)}</div></div>' for h in hooks), unsafe_allow_html=True)

# =========================================================================== 8. DATOS
with T[7]:
    ui.head("Datos y fuentes", "De dónde sale cada número")
    stt = latest.get("status") or {}
    srcs = [
        ("Google Trends", (latest.get("trends") or {}).get("fetched_at"), stt.get("trends"),
         "Interés de búsqueda semanal, por país y búsquedas en ascenso. Escala común con keyword ancla."),
        ("Autocompletado Google / YouTube", ac.get("fetched_at"), stt.get("autocomplete"),
         "Preguntas reales que la gente escribe; amplitud de cada keyword; búsquedas de marca de la competencia."),
        ("TikTok Creative Center", tt.get("fetched_at"), stt.get("tiktok"), "Hashtags populares por país (cuando el servicio responde)."),
        ("Competencia", competitors["actualizado"], "manual", "Precios, escala, redes y tendencias con enlace a cada fuente."),
        ("Instagram (perfiles públicos)", instagram["capturado"], "manual",
         "Seguidores, interacciones por post, ritmo y temas de @marketnuss, @platzi, @coursera y @udemy (tools/ig_scan.js)."),
    ]
    st.dataframe(pd.DataFrame(srcs, columns=["Fuente", "Última lectura", "Estado", "Qué aporta"]).fillna("—"),
                 hide_index=True, width="stretch")

    ui.head("Cómo se calcula", "Métricas")
    st.markdown(
        "- **Demanda (0–100):** promedio de 12 meses en Google Trends México (el mayor mercado hispano; el mapa por país sí es mundial), llevado a escala común con la keyword ancla «marketing digital» "
        "y comprimido con raíz cuadrada. Si Trends redondea a 0 una keyword que el buscador sí sugiere, recibe un piso de 4–20 según cuántas variantes sugiere (fuente: «Autocompletado (volumen bajo)»).\n"
        "- **Momentum:** interés de las últimas 12 semanas contra las 12 anteriores.\n"
        "- **Dificultad (KD):** estimación según lo genérica que es la keyword (cuanto más corta y amplia, más difícil) "
        "y si aparece en las búsquedas de marca de Coursera, Udemy o Platzi (+10).\n"
        "- **Encaje:** 100 si lleva a un curso de Marketnus, 60 si es un tema amplio que conecta con varios, 35 si no.\n"
        "- **Oportunidad:** 40% demanda + 20% momentum + 25% encaje + 15% facilidad (100 − KD).\n"
        "- **Intención y formato:** reglas por palabras («qué es» → pregunta → video corto; «cómo hacer» → tutorial → YouTube/blog).")
    st.write("")
    ui.head("Subir datos", "Agregar un CSV de Google Trends",
            "Exporta un gráfico de Google Trends («Interés a lo largo del tiempo» → descargar CSV) y súbelo aquí para verlo en la app durante esta sesión. "
            "Para dejarlo fijo, agrega las keywords a <code>config/keywords.csv</code> en GitHub.")
    up = st.file_uploader("multiTimeline.csv", type=["csv"])
    if up is not None:
        try:
            parsed = parse_trends_csv(up.getvalue())
            st.session_state["uploaded_series"] = parsed
            st.success(f"Cargadas {len(parsed)} series: {', '.join(parsed)}. Recarga la pestaña Keywords.")
        except Exception as e:  # noqa: BLE001
            st.error(f"No pude leer el archivo: {e}")
    st.download_button("Descargar todas las métricas (CSV)", kw.drop(columns=["serie"]).to_csv(index=False).encode("utf-8"),
                       "metricas_marketnus.csv", "text/csv")

st.markdown('<div class="foot"><b>Marketnus</b> Content Intelligence · datos públicos y gratuitos · '
            'se actualiza cada lunes · Developer: <b>Ed Trigueros</b></div>', unsafe_allow_html=True)
