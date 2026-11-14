"""Ideas de contenido y calendario (reglas, sin IA de pago).

Convierte cada keyword en una pieza concreta: plataforma, formato, gancho,
guion en 3 partes, llamada a la acción y hashtags.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta

import pandas as pd

HOOKS = {
    "Pregunta": [
        "¿{K}? Te lo explico en 30 segundos.",
        "Casi nadie responde bien esto: ¿{k}?",
        "Si te preguntan «¿{k}?», contesta esto.",
    ],
    "Tutorial": [
        "{K}: el paso a paso que yo uso con clientes.",
        "Así se hace, sin rodeos: {k}.",
        "3 pasos para {k_sin_como} (el 2 es el que todos se saltan).",
    ],
    "Formación": [
        "Antes de pagar un {k}, mira esto.",
        "Probé las opciones para aprender esto. Te cuento cuál vale la pena: {k}.",
        "{K}: qué debería enseñarte en 2026 (y qué no).",
    ],
    "Comparativa": [
        "{K}: la comparación honesta.",
        "Lo gratis sale caro si no sabes esto: {k}.",
        "¿Vale la pena? {K}, con números.",
    ],
    "Herramienta": [
        "Guarda esto: {k} listos para copiar.",
        "Lo que hago con {k} en 10 minutos al día.",
        "5 usos de {k} que te ahorran horas.",
    ],
    "Concepto": [
        "{K}, explicado con un caso real.",
        "Lo que aprendí sobre {k} trabajando con Visa y Mastercard.",
        "El error más común con {k} (y cómo evitarlo).",
    ],
}
GUION = {
    "Pregunta":    ["Gancho con la pregunta en pantalla", "Respuesta en 3 ideas con texto grande", "Ejemplo real de 1 frase + CTA"],
    "Tutorial":    ["Muestra el resultado final primero", "Paso a paso en pantalla (graba la pantalla)", "Error común + CTA al curso"],
    "Formación":   ["Qué buscar en un curso (3 criterios)", "Opciones gratis vs. pagadas, con sus límites", "Dónde encaja tu curso y para quién no es"],
    "Comparativa": ["Tabla con 3–4 opciones", "Precio, tiempo y resultado de cada una", "Veredicto claro según el perfil"],
    "Herramienta": ["Slide 1: promesa concreta", "Slides 2–6: un uso o prompt por slide", "Slide 7: guarda y comparte + link en bio"],
    "Concepto":    ["Definición en 1 frase", "Caso real tuyo con antes/después", "Lección práctica + pregunta para comentar"],
}
CTA = {
    "TikTok + Reels": "Sígueme para la parte 2 y comenta «QUIERO» para recibir la guía.",
    "YouTube + Blog": "Link al curso en la descripción; suscríbete para el siguiente tutorial.",
    "Google (blog) + YouTube": "Cierra con un botón al curso y un lead magnet gratis.",
    "Blog + Carrusel IG": "Guarda la comparación y escribe tu caso en comentarios.",
    "Carrusel IG + TikTok": "Guarda este post y compártelo con alguien que lo necesite.",
    "LinkedIn + Carrusel IG": "Pregunta abierta al final para generar conversación.",
}


def _pick(options: list[str], key: str) -> str:
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return options[h % len(options)]


PROPER = {"seo": "SEO", "sem": "SEM", "ia": "IA", "cv": "CV", "cx": "CX", "ats": "ATS", "chatgpt": "ChatGPT",
          "tiktok": "TikTok", "instagram": "Instagram", "google": "Google", "linkedin": "LinkedIn", "shopify": "Shopify",
          "gemini": "Gemini", "claude": "Claude", "copilot": "Copilot", "microsoft": "Microsoft", "excel": "Excel",
          "ads": "Ads", "maps": "Maps", "scrum": "Scrum", "lean": "Lean", "six": "Six", "sigma": "Sigma"}


def natural(kw: str) -> str:
    """Pasa una keyword tal como se busca a una frase legible: 'scrum qué es' -> 'qué es Scrum'."""
    k = kw.strip()
    for q in ("qué es", "qué hace", "cómo usar"):
        if k.endswith(" " + q):
            subj = k[: -len(q) - 1]
            k = f"{q} {'un ' if q == 'qué hace' else ''}{subj}"
    k = re.sub(r"\bmeta ads\b", "Meta Ads", k)
    return " ".join(PROPER.get(w, w) for w in k.split())


def _fill(tpl: str, kw: str) -> str:
    k = natural(kw)
    k_sin = k
    for p in ("cómo ", "como "):
        if k_sin.startswith(p):
            k_sin = k_sin[len(p):]
    return tpl.format(k=k, K=k[:1].upper() + k[1:], k_sin_como=k_sin)


def hashtags_for(cluster: str, social: dict, n: int = 4) -> list[str]:
    pool = social["hashtags"].get(cluster, []) + social["hashtags"]["General educación"]
    # 1 amplio + 2 medios/nicho + 1 general: mezcla de alcance y precisión
    amplio = [h["tag"] for h in pool if h["tamaño"] == "amplio"]
    nicho = [h["tag"] for h in pool if h["tamaño"] != "amplio"]
    out = amplio[:1] + nicho[:2] + amplio[1:2]
    return list(dict.fromkeys(out))[:n]


def idea(row: pd.Series, social: dict) -> dict:
    it = row["intencion"] if row["intencion"] in HOOKS else "Concepto"
    kw = row["keyword"]
    return {
        "keyword": kw,
        "titulo": _fill(_pick(HOOKS[it], kw), kw),
        "plataforma": row["plataforma"],
        "formato": row["formato"],
        "guion": GUION[it],
        "cta": CTA.get(row["plataforma"], "Invita a comentar y guardar."),
        "hashtags": hashtags_for(row["cluster"], social),
        "curso": row.get("curso_nombre", "") or "",
        "oportunidad": int(row["oportunidad"]),
        "intencion": it,
        "cluster": row["cluster"],
    }


SLOTS = [
    ("TikTok / Reel", {"Pregunta", "Herramienta"}),
    ("Carrusel Instagram", {"Herramienta", "Concepto", "Comparativa"}),
    ("YouTube / Blog", {"Tutorial", "Formación", "Comparativa"}),
    ("LinkedIn", {"Concepto", "Pregunta", "Tutorial"}),
]
DAY_OF = {"LinkedIn": 0, "TikTok / Reel": 1, "Carrusel Instagram": 2, "YouTube / Blog": 3}
SLOT_FORMAT = {"TikTok / Reel": "Video vertical de 30–60 s con texto en pantalla",
               "Carrusel Instagram": "Carrusel de 7–10 slides para guardar",
               "YouTube / Blog": "Video de 6–10 min + artículo con la misma keyword",
               "LinkedIn": "Post de texto con un caso real y pregunta final"}
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fecha_es(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"


def calendar(kw: pd.DataFrame, courses: dict, social: dict) -> pd.DataFrame:
    start = date.fromisoformat(courses["inicio_publicacion"])
    pool = kw[kw["oportunidad"] > 0].copy()
    used: set[str] = set()
    rows = []
    for c in sorted(courses["cursos"], key=lambda x: x["semana"]):
        week_start = start + timedelta(weeks=c["semana"] - 1)
        mine = pool[pool["curso"] == c["id"]]
        broad = pool[pool["curso"] == ""]
        for slot, intents in SLOTS:
            cand = mine[mine["intencion"].isin(intents) & ~mine["keyword"].isin(used)]
            if cand.empty:
                cand = mine[~mine["keyword"].isin(used)]
            if cand.empty:
                cand = broad[broad["intencion"].isin(intents) & ~broad["keyword"].isin(used)]
            if cand.empty:
                continue
            r = cand.iloc[0]
            used.add(r["keyword"])
            i = idea(r, social)
            rows.append({
                "Semana": c["semana"],
                "Fecha": fecha_es(week_start + timedelta(days=DAY_OF[slot])),
                "Curso de la semana": c["nombre"] + (" (gratis)" if c.get("gratis") else ""),
                "Pieza": slot,
                "Keyword": r["keyword"],
                "Título / gancho": i["titulo"],
                "Formato": SLOT_FORMAT[slot],
                "Hashtags": " ".join(i["hashtags"]) if slot != "YouTube / Blog" else "",
                "Oportunidad": int(r["oportunidad"]),
            })
    out = pd.DataFrame(rows)
    order = {k: n for n, k in enumerate(DAY_OF)}
    return out.sort_values(["Semana", "Pieza"], key=lambda c: c.map(order) if c.name == "Pieza" else c).reset_index(drop=True)


def content_brief(row: pd.Series, related: list[str]) -> dict:
    """Brief SEO rápido para blog o YouTube."""
    kw = natural(row["keyword"])
    K = kw[:1].upper() + kw[1:]
    title = f"{K}: guía práctica 2026 | Marketnus"
    if len(title) > 60:
        title = f"{K} | Marketnus"[:60]
    meta = (f"Aprende {kw} con ejemplos reales y pasos claros. Guía en español para LATAM, "
            f"con plantillas y un curso de €9,99 para ir más lejos.")[:158]
    h2 = [f"Qué es y por qué importa en 2026", f"Paso a paso: {kw}", "Errores comunes (y cómo evitarlos)",
          "Herramientas gratis para empezar", "Siguiente paso: practica con un caso real"]
    faqs = [q for q in related if q.lower() != kw.lower()][:5]
    return {"title": title, "meta": meta, "h2": h2, "faqs": faqs}
