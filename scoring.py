"""Métricas de keywords (estilo SEMrush, pero con fuentes gratis).

Cada keyword recibe:
- demanda      0-100  Google Trends reescalado con la keyword ancla (o estimación inicial)
- momentum     %      últimas 12 semanas contra las 12 anteriores
- competencia  0-100  estimación según lo genérica que es la keyword y si la competencia la cubre
- encaje       0-100  qué tan directo lleva a un curso de Marketnus
- oportunidad  0-100  combinación de las anteriores: dónde conviene publicar primero
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config"

W_DEMANDA, W_MOMENTUM, W_ENCAJE, W_COMPETENCIA = 0.40, 0.20, 0.25, 0.15
BRAND_CLUSTER = "Marcas competidoras"
BROAD_CLUSTERS = {"Marketing digital", "Carrera y empleabilidad", "Emprendimiento"}


def load_json(name: str) -> dict:
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def load_keywords() -> pd.DataFrame:
    df = pd.read_csv(CONFIG / "keywords.csv")
    df["curso"] = df["curso"].fillna("").astype(str)
    return df


def intent(kw: str) -> str:
    k = f" {kw.lower()} "
    if re.search(r"\b(platzi|coursera|udemy|marketnus)\b", k):
        return "Marca"
    if re.search(r" (mejor|mejores|vs|precio|cuánto cuesta|gratis|comparativa) ", k):
        return "Comparativa"
    if re.search(r" (curso|cursos|certificado|bootcamp|aprender) ", k):
        return "Formación"
    if re.search(r" (cómo|como) (hacer|crear|usar|vender|crecer|pasar|mejorar|ganar|emprender) ", k):
        return "Tutorial"
    if re.search(r" (qué es|que es|qué hace|para qué|significa) ", k):
        return "Pregunta"
    if re.search(r" (herramientas|prompts|chatgpt|gemini|copilot|claude|shopify|excel) ", k):
        return "Herramienta"
    return "Concepto"


FORMATO = {
    "Pregunta":    ("TikTok + Reels", "Video corto de 30–45 s: la respuesta en 3 pasos"),
    "Tutorial":    ("YouTube + Blog", "Tutorial paso a paso de 6–10 min con pantalla"),
    "Formación":   ("Google (blog) + YouTube", "Guía larga que compara opciones y cierra con tu curso"),
    "Comparativa": ("Blog + Carrusel IG", "Comparativa honesta con tabla y veredicto"),
    "Herramienta": ("Carrusel IG + TikTok", "Carrusel de 7 slides con prompts o pasos listos para copiar"),
    "Concepto":    ("LinkedIn + Carrusel IG", "Explicación con un caso real tuyo (Blackhawk, CX, Lean)"),
    "Marca":       ("—", "Keyword de marca: úsala para medir a la competencia"),
}


def _series_stats(values: list[float]) -> tuple[float, float]:
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return 0.0, 0.0
    mean = float(v.mean())
    last, prev = v[-12:].mean(), v[-24:-12].mean() if v.size >= 24 else v[:-12].mean() if v.size > 12 else 0
    if prev <= 0.5:
        mom = 0.0 if last <= 0.5 else 100.0
    else:
        mom = (last - prev) / prev * 100
    return mean, float(np.clip(mom, -100, 300))


def build_keywords(latest: dict | None) -> pd.DataFrame:
    df = load_keywords()
    courses = {c["id"]: c["nombre"] for c in load_json("courses.json")["cursos"]}
    latest = latest or {}
    trends = (latest.get("trends") or {})
    series = trends.get("series", {})
    ac = (latest.get("autocomplete") or {})
    breadth = ac.get("breadth", {})
    brand_text = " ".join(" ".join(v) for v in (ac.get("brands") or {}).values()).lower()

    means, moms, src, spark = [], [], [], []
    for kw in df["keyword"]:
        s = series.get(kw)
        if s and s.get("values"):
            m, mo = _series_stats(s["values"])
            means.append(m)
            moms.append(mo)
            src.append("Google Trends")
            spark.append([round(x, 1) for x in s["values"]])
        else:
            means.append(np.nan)
            moms.append(np.nan)
            src.append("Estimado")
            spark.append(None)
    df["_mean"] = means
    df["momentum"] = moms
    df["fuente"] = src
    df["serie"] = spark

    real = df["_mean"].dropna()
    if len(real):
        top = max(real.max(), 1e-6)
        df["demanda"] = np.where(df["_mean"].notna(), np.round(100 * np.sqrt(df["_mean"].clip(lower=0) / top)),
                                 df["est_demanda"])
    else:
        df["demanda"] = df["est_demanda"]
    df["demanda"] = df["demanda"].astype(float)

    def comp(row):
        c = float(row["est_competencia"])
        core = [w for w in re.findall(r"[a-záéíóúñ]{4,}", row["keyword"].lower())
                if w not in {"curso", "cursos", "gratis", "cómo", "como", "para", "hacer", "qué"}]
        if core and any(w in brand_text for w in core):
            c += 10
        return float(min(c, 100))

    df["competencia"] = df.apply(comp, axis=1)

    def encaje(row):
        if row["cluster"] == BRAND_CLUSTER:
            return 0.0
        if row["curso"]:
            return 100.0
        return 60.0 if row["cluster"] in BROAD_CLUSTERS else 35.0

    df["encaje"] = df.apply(encaje, axis=1)
    mom_norm = (50 + df["momentum"].fillna(0) / 2).clip(0, 100)
    df["oportunidad"] = np.round(W_DEMANDA * df["demanda"] + W_MOMENTUM * mom_norm + W_ENCAJE * df["encaje"]
                                 + W_COMPETENCIA * (100 - df["competencia"]))
    df.loc[df["cluster"] == BRAND_CLUSTER, "oportunidad"] = 0
    df["intencion"] = df["keyword"].map(intent)
    df["plataforma"] = df["intencion"].map(lambda i: FORMATO[i][0])
    df["formato"] = df["intencion"].map(lambda i: FORMATO[i][1])
    df["curso_nombre"] = df["curso"].map(lambda c: courses.get(c, ""))
    df["sug_google"] = df["keyword"].map(lambda k: breadth.get(k, {}).get("google"))
    df["sug_youtube"] = df["keyword"].map(lambda k: breadth.get(k, {}).get("youtube"))
    df["kd_label"] = pd.cut(df["competencia"], [-1, 30, 50, 70, 85, 101],
                            labels=["Muy fácil", "Fácil", "Posible", "Difícil", "Muy difícil"]).astype(str)
    return df.drop(columns=["_mean"]).sort_values("oportunidad", ascending=False).reset_index(drop=True)


def brand_share(latest: dict | None) -> pd.DataFrame | None:
    """Share of search de marcas educativas (Google Trends)."""
    series = ((latest or {}).get("trends") or {}).get("series", {})
    brands = [b for b in ["coursera", "udemy", "platzi", "marketnus"] if b in series]
    if len(brands) < 2:
        return None
    frames = []
    for b in brands:
        s = series[b]
        frames.append(pd.DataFrame({"fecha": pd.to_datetime(s["dates"]), "marca": b.capitalize(), "interes": s["values"]}))
    return pd.concat(frames)
