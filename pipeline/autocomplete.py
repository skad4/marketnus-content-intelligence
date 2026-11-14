"""Sugerencias de búsqueda de Google y YouTube (gratis, sin clave).

Lo que la gente empieza a escribir en el buscador es la mejor pista de qué preguntas
tiene. Usamos el mismo servicio que alimenta el autocompletado del navegador:
  - Google:  suggestqueries.google.com ... client=firefox
  - YouTube: lo mismo con ds=yt (sirve también como pista de búsquedas en video,
             porque TikTok e Instagram no publican sus búsquedas)
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

URL = "https://suggestqueries.google.com/complete/search"
HEADERS = {"User-Agent": "Mozilla/5.0 (marketnus-content-intelligence; investigación semanal)"}
MARKETS = {"MX": "México", "CO": "Colombia", "ES": "España", "AR": "Argentina", "PE": "Perú"}

QUESTION_SEEDS = [
    "curso de", "cómo aprender", "cómo usar", "qué es", "cómo hacer", "mejor curso de",
    "cursos gratis de", "cómo ganar dinero con", "para qué sirve", "herramientas de",
]
TOPIC_SEEDS = [
    "inteligencia artificial", "chatgpt", "agentes de ia", "marketing digital", "seo", "google ads",
    "meta ads", "instagram", "tiktok", "email marketing", "copywriting", "ecommerce",
    "tienda online", "transformación digital", "community manager", "marca personal", "cv",
]
BRANDS = ["platzi", "coursera", "udemy"]


def suggest(q: str, gl: str = "MX", ds: str | None = None) -> list[str]:
    params = {"client": "firefox", "hl": "es", "gl": gl.lower(), "q": q}
    if ds:
        params["ds"] = ds
    try:
        r = requests.get(URL, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        return [s for s in data[1] if isinstance(s, str)]
    except Exception as e:  # noqa: BLE001
        print(f"[autocomplete] {q!r} ({gl}, {ds or 'web'}): {e}")
        return []


def collect(keywords: list[str]) -> dict | None:
    google: dict[str, list[str]] = {}
    youtube: dict[str, list[str]] = {}
    breadth: dict[str, dict] = {}
    by_market: dict[str, dict[str, list[str]]] = {}
    brands: dict[str, list[str]] = {}
    calls = 0

    # 1) Preguntas por tema (Google + YouTube, México como mercado base)
    for topic in TOPIC_SEEDS:
        for seed in QUESTION_SEEDS[:6]:
            q = f"{seed} {topic}"
            google[q] = suggest(q)
            youtube[q] = suggest(q, ds="yt")
            calls += 2
            time.sleep(0.4)

    # 2) Amplitud de cada keyword: cuántas variantes sugiere el buscador
    for kw in keywords:
        g = suggest(kw)
        y = suggest(kw, ds="yt")
        breadth[kw] = {"google": len(g), "youtube": len(y), "google_top": g[:5], "youtube_top": y[:5]}
        calls += 2
        time.sleep(0.4)

    # 3) Diferencias por país en los temas principales
    for gl in MARKETS:
        by_market[gl] = {}
        for topic in ["curso de", "cómo ganar dinero", "inteligencia artificial para", "marketing digital"]:
            by_market[gl][topic] = suggest(topic, gl=gl)
            calls += 1
            time.sleep(0.4)

    # 4) Qué buscan de la competencia (marca + curso)
    for b in BRANDS:
        out: list[str] = []
        for q in [f"{b} curso de", f"{b} cursos", f"curso de {b}", f"{b} gratis", f"{b} vs"]:
            out += suggest(q)
            calls += 1
            time.sleep(0.4)
        brands[b] = list(dict.fromkeys(out))

    total = sum(len(v) for v in google.values()) + sum(len(v) for v in youtube.values())
    if total == 0:
        return None
    return {
        "source": "Google y YouTube autocompletado",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "calls": calls,
        "google": google,
        "youtube": youtube,
        "breadth": breadth,
        "by_market": by_market,
        "brands": brands,
    }
