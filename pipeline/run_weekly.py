"""Corre cada lunes desde GitHub Actions (o a mano: python -m pipeline.run_weekly).

1. Lee las keywords de config/keywords.csv
2. Junta Google Trends, autocompletado de Google/YouTube y TikTok Creative Center
3. Si una fuente falla, conserva lo de la semana anterior para esa fuente
4. Guarda data/latest.json y una foto de las métricas en data/history/AAAA-MM-DD.csv
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import autocomplete, google_trends, tiktok  # noqa: E402

DATA = ROOT / "data"
LATEST = DATA / "latest.json"
HISTORY = DATA / "history"


def main() -> None:
    kw = pd.read_csv(ROOT / "config" / "keywords.csv")["keyword"].dropna().tolist()
    prev = json.loads(LATEST.read_text(encoding="utf-8")) if LATEST.exists() else {}
    status = {}

    quick = os.getenv("QUICK_RUN") == "1"   # para pruebas: solo 2 lotes de Trends
    trends = google_trends.collect(kw, max_batches=2 if quick else None)
    status["trends"] = "ok" if trends else "falló (se mantiene la semana anterior)"
    if trends and prev.get("trends") and trends["batches_ok"] < trends["batches_total"]:
        # completar keywords que no entraron esta semana con lo anterior
        for k, v in prev["trends"].get("series", {}).items():
            trends["series"].setdefault(k, v)
        for k, v in prev["trends"].get("regions", {}).items():
            trends["regions"].setdefault(k, v)

    ac = autocomplete.collect(kw)
    status["autocomplete"] = "ok" if ac else "falló (se mantiene la semana anterior)"

    tt = tiktok.collect()
    status["tiktok"] = "ok" if tt else "sin respuesta (se usa la lista semilla)"

    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "trends": trends or prev.get("trends"),
        "autocomplete": ac or prev.get("autocomplete"),
        "tiktok": tt or prev.get("tiktok"),
    }
    DATA.mkdir(exist_ok=True)
    LATEST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # foto semanal de métricas para comparar semana contra semana
    sys.path.insert(0, str(ROOT))
    from scoring import build_keywords  # noqa: E402
    HISTORY.mkdir(exist_ok=True)
    df = build_keywords(out)
    df[["keyword", "demanda", "momentum", "oportunidad"]].to_csv(HISTORY / f"{date.today():%Y-%m-%d}.csv", index=False)
    print(json.dumps(status, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
