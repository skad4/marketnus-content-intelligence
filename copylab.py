"""Copy Lab: revisa un caption o un título antes de publicarlo.

Reglas simples y transparentes (sin IA de pago). Cada regla suma puntos y
explica qué cambiar.
"""
from __future__ import annotations

import re

CTA_WORDS = ["guarda", "comenta", "comparte", "sígueme", "sigueme", "link en bio", "escribe", "etiqueta",
             "suscríbete", "suscribete", "descarga", "inscríbete", "inscribete", "únete", "unete", "responde"]
FORMATS = {
    "Reel / TikTok": {"max_tags": 5, "min_tags": 3, "hook_max": 90, "len": (80, 600)},
    "Carrusel Instagram": {"max_tags": 5, "min_tags": 3, "hook_max": 110, "len": (120, 1200)},
    "LinkedIn": {"max_tags": 3, "min_tags": 0, "hook_max": 140, "len": (300, 1800)},
    "Título YouTube": {"max_tags": 0, "min_tags": 0, "hook_max": 70, "len": (35, 70)},
    "Título + meta de blog": {"max_tags": 0, "min_tags": 0, "hook_max": 60, "len": (50, 60)},
}


def score(text: str, fmt: str, keyword: str = "", meta: str = "") -> tuple[int, list[tuple[bool, str]]]:
    rules = FORMATS[fmt]
    t = text.strip()
    lines = [l for l in t.splitlines() if l.strip()]
    first = lines[0] if lines else ""
    tags = re.findall(r"#\w+", t, flags=re.UNICODE)
    kw = keyword.strip().lower()
    checks: list[tuple[bool, str, int]] = []

    lo, hi = rules["len"]
    n = len(t)
    checks.append((lo <= n <= hi, f"Largo: {n} caracteres (ideal {lo}–{hi}).", 15))

    if kw:
        checks.append((kw in first.lower(), "La keyword aparece en la primera línea (ayuda a la búsqueda dentro de la app)." if kw in first.lower()
                       else f"Pon «{keyword}» en la primera línea: TikTok, Instagram y YouTube la leen para clasificar el contenido.", 20))
    else:
        checks.append((False, "Escribe la keyword objetivo para revisar si está bien ubicada.", 20))

    hook_ok = 0 < len(first) <= rules["hook_max"]
    checks.append((hook_ok, f"Gancho de {len(first)} caracteres (máximo {rules['hook_max']} para que no se corte).", 15))

    has_num_q = bool(re.search(r"\d|¿|\?", first))
    checks.append((has_num_q, "El gancho tiene un número o una pregunta." if has_num_q
                   else "Agrega un número o una pregunta al gancho: suelen retener más.", 10))

    if fmt in ("Título YouTube", "Título + meta de blog"):
        if fmt == "Título + meta de blog":
            m = meta.strip()
            checks.append((140 <= len(m) <= 160, f"Meta description: {len(m)} caracteres (ideal 140–160).", 20))
            checks.append((bool(kw) and kw in m.lower(), "La keyword aparece en la meta description." if kw and kw in m.lower()
                           else "Incluye la keyword en la meta description.", 20))
        else:
            pos = first.lower().find(kw) if kw else -1
            checks.append((0 <= pos <= 25, "La keyword está al inicio del título." if 0 <= pos <= 25
                           else "Mueve la keyword a las primeras palabras del título.", 20))
            checks.append(("marketnus" not in first.lower()[:20], "La marca no le quita espacio a la keyword.", 20))
    else:
        cta = any(w in t.lower() for w in CTA_WORDS)
        checks.append((cta, "Tiene una llamada a la acción clara." if cta
                       else "Cierra con una acción concreta: «guarda», «comenta QUIERO», «link en bio».", 20))
        mn, mx = rules["min_tags"], rules["max_tags"]
        ok_tags = mn <= len(tags) <= mx
        msg = f"{len(tags)} hashtags (recomendado {mn}–{mx})." if mx else "Sin hashtags."
        if fmt.startswith("Carrusel") or fmt.startswith("Reel"):
            msg += " Instagram ahora permite máximo 5."
        checks.append((ok_tags, msg, 20))

    total = sum(w for _, _, w in checks)
    got = sum(w for ok, _, w in checks if ok)
    return round(100 * got / total), [(ok, m) for ok, m, _ in checks]
