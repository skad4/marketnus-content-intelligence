"""Hashtags populares de TikTok Creative Center (mejor esfuerzo).

TikTok no tiene una API pública gratuita de tendencias. Creative Center sí muestra
los hashtags populares por país, pero su endpoint interno a veces pide cabeceras
firmadas. Si responde, guardamos los hashtags; si no, la app usa la lista semilla
de config/social.json y lo dice en pantalla.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

URL = "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
    "Referer": "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/es",
    "Accept": "application/json",
}
COUNTRIES = ["MX", "CO", "ES", "AR", "PE"]
EDU_WORDS = ["aprend", "curso", "educ", "marketing", "emprend", "negocio", "ia", "ai", "chatgpt", "tips",
             "dinero", "trabajo", "empleo", "estudi", "seo", "ventas", "linkedin", "productiv", "tecnolog"]


def collect() -> dict | None:
    items = []
    for cc in COUNTRIES:
        try:
            r = requests.get(URL, headers=HEADERS, timeout=20, params={
                "page": 1, "limit": 50, "period": 7, "country_code": cc, "sort_by": "popular"})
            data = r.json()
            rows = (data.get("data") or {}).get("list") or []
        except Exception as e:  # noqa: BLE001
            print(f"[tiktok] {cc}: {e}")
            rows = []
        for row in rows:
            name = str(row.get("hashtag_name", "")).strip()
            if not name:
                continue
            items.append({
                "country": cc,
                "tag": f"#{name}",
                "rank": row.get("rank"),
                "posts": row.get("publish_cnt"),
                "views": row.get("video_views"),
                "edu": any(w in name.lower() for w in EDU_WORDS),
            })
        time.sleep(1.5)
    if not items:
        print("[tiktok] Creative Center no respondió; la app usará la lista semilla")
        return None
    return {
        "source": "TikTok Creative Center",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "items": items,
    }
