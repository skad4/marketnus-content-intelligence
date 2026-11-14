"""Google Trends (gratis, vía pytrends).

Google Trends compara como máximo 5 términos por consulta y cada consulta usa su
propia escala 0-100. Para poner todas las keywords en una misma escala se mete una
keyword ancla en cada lote (como hicimos en el estudio editorial) y se reescala
cada lote según cuánto vale el ancla en él.

Si Google bloquea la consulta (error 429), el lote se salta y la app sigue usando
los datos de la semana anterior para esas keywords.
"""
from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone

import pandas as pd

ANCHOR = "marketing digital"
TIMEFRAME = "today 12-m"
GEO = os.getenv("TRENDS_GEO", "MX")   # series y búsquedas en ascenso: México, el mayor mercado hispano
REGION_GEO = ""                        # el mapa por país sí se pide a nivel mundial
COUNTRIES = {"Mexico": "MX", "Colombia": "CO", "Spain": "ES", "Argentina": "AR", "Peru": "PE",
             "Chile": "CL", "Ecuador": "EC", "Guatemala": "GT", "El Salvador": "SV",
             "Dominican Republic": "DO", "Venezuela": "VE", "Bolivia": "BO", "Costa Rica": "CR",
             "Honduras": "HN", "Panama": "PA", "Paraguay": "PY", "Uruguay": "UY", "United States": "US"}
ES_NAMES = {"MX": "méxico", "CO": "colombia", "ES": "españa", "AR": "argentina", "PE": "perú", "CL": "chile",
            "EC": "ecuador", "GT": "guatemala", "SV": "el salvador", "DO": "república dominicana", "VE": "venezuela",
            "BO": "bolivia", "CR": "costa rica", "HN": "honduras", "PA": "panamá", "PY": "paraguay", "UY": "uruguay",
            "US": "estados unidos"}
NAME_TO_CODE = {**{k.lower(): v for k, v in COUNTRIES.items()}, **{v: k for k, v in ES_NAMES.items()}}
RELEVANT = {"curso", "cursos", "ia", "inteligencia", "artificial", "marketing", "chatgpt", "gemini", "claude", "agente",
            "agentes", "prompts", "seo", "ads", "tiktok", "instagram", "negocio", "dinero", "certificado", "gratis",
            "aprender", "ventas", "emprender", "digital", "online", "trabajo", "excel", "copilot"}
RISING_SEEDS = ["curso de", "inteligencia artificial", "marketing digital", "cómo ganar dinero", "cursos gratis"]


def _client():
    from pytrends.request import TrendReq  # import tardío: la app no lo necesita
    # retries=0: pytrends usa un parámetro de urllib3 que ya no existe; reintentamos nosotros
    return TrendReq(hl="es-419", tz=360, timeout=(10, 30))


def _call(fn, label: str, tries: int = 3):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            wait = 30 * (i + 1) + random.uniform(0, 10)
            print(f"[trends] {label}: {type(e).__name__} {e} -> reintento en {wait:.0f}s")
            time.sleep(wait)
    print(f"[trends] {label}: sin datos tras {tries} intentos")
    return None


def collect(keywords: list[str], max_batches: int | None = None) -> dict | None:
    kws = [k for k in dict.fromkeys(keywords) if k and k != ANCHOR]
    batches = [kws[i:i + 4] for i in range(0, len(kws), 4)]
    if max_batches:
        batches = batches[:max_batches]
    try:
        py = _client()
        py_reg = _client()  # cliente aparte: pytrends conserva el geo anterior si se pasa ''
    except Exception as e:  # noqa: BLE001
        print(f"[trends] pytrends no disponible: {e}")
        return None

    series: dict[str, dict] = {}
    regions: dict[str, dict] = {}
    anchor_ref = None
    ok = 0
    for n, batch in enumerate(batches, 1):
        terms = batch + [ANCHOR]
        label = f"lote {n}/{len(batches)}"
        df = _call(lambda: (py.build_payload(terms, timeframe=TIMEFRAME, geo=GEO), py.interest_over_time())[1], label)
        if df is None or df.empty or ANCHOR not in df.columns:
            continue
        df = df.drop(columns=[c for c in ["isPartial"] if c in df.columns])
        a_mean = float(df[ANCHOR].mean()) or 1.0
        if anchor_ref is None:
            anchor_ref = a_mean
        factor = anchor_ref / a_mean
        for kw in batch + ([ANCHOR] if ANCHOR not in series else []):
            if kw in df.columns:
                series[kw] = {
                    "dates": [d.strftime("%Y-%m-%d") for d in df.index],
                    "values": [round(float(v) * factor, 2) for v in df[kw].tolist()],
                }
        reg = _call(lambda: (py_reg.build_payload(batch, timeframe=TIMEFRAME, geo=REGION_GEO),
                             py_reg.interest_by_region(resolution="COUNTRY", inc_low_vol=True, inc_geo_code=True))[1],
                    label, tries=2)
        if n <= 2:
            print(f"[trends] regiones lote {n}: {None if reg is None else (reg.shape, list(reg.columns)[:6], list(reg.index)[:3])}")
        if reg is not None and not reg.empty:
            if "geoCode" in reg.columns and reg["geoCode"].isin(COUNTRIES.values()).any():
                reg = reg[reg["geoCode"].isin(COUNTRIES.values())].set_index("geoCode")
            else:  # sin código ISO: mapear por nombre (inglés o español)
                codes = reg.index.to_series().map(lambda n: NAME_TO_CODE.get(str(n).strip().lower()))
                reg = reg[codes.notna().values].set_axis(codes.dropna().values, axis=0)
                reg = reg.drop(columns=[c for c in ["geoCode"] if c in reg.columns])
            for kw in [c for c in reg.columns if c in batch]:
                vals = {cc: int(v) for cc, v in reg[kw].items() if v > 0}
                if vals:
                    regions[kw] = vals
        ok += 1
        time.sleep(random.uniform(4, 8))

    rising = []
    for seed in RISING_SEEDS:
        rq = _call(lambda: (py.build_payload([seed], timeframe="today 3-m", geo=GEO), py.related_queries())[1],
                   f"rising {seed}", tries=2)
        if not rq or seed not in rq or rq[seed].get("rising") is None:
            continue
        for _, r in rq[seed]["rising"].head(25).iterrows():
            q = str(r["query"]).lower()
            # descarta ruido sin relación con el tema (pasa con términos amplios)
            if not (set(q.split()) & (set(seed.split()) | RELEVANT)):
                continue
            rising.append({"seed": seed, "query": str(r["query"]), "value": str(r["value"])})
        time.sleep(random.uniform(4, 8))

    if ok == 0:
        return None
    return {
        "source": "Google Trends (pytrends)",
        "geo": GEO or "mundial",
        "anchor": ANCHOR,
        "timeframe": TIMEFRAME,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "batches_ok": ok,
        "batches_total": len(batches),
        "series": series,
        "regions": regions,
        "rising": rising,
    }


if __name__ == "__main__":
    kw = pd.read_csv("config/keywords.csv")["keyword"].tolist()
    out = collect(kw, max_batches=1)
    print(out and {k: v for k, v in out.items() if k not in ("series", "regions")})
