from __future__ import annotations

from typing import Optional, Dict, Any, List

import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .settings import LLM_URL, N_PREDICT, TEMPERATURE, TOP_K, TOP_P, MAX_CTX_DOCS, LLM_TIMEOUT_SECONDS
from .retrieval import search_reports, count_reports, count_reports_by_city, count_reports_by_category, count_urgent_reports, count_urgent_by_city, count_urgent_by_category, monthly_counts
from .prompts import build_prompt
import unicodedata
import re

app = FastAPI(title="RAG API - Mistral + SQLite FTS5")

_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "*")
_origins = ["*"] if _origins_env.strip() == "*" else [o.strip() for o in _origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    texto: str


class AskSimpleResponse(BaseModel):
    answer: str


# Detector simple de intenciones de cálculo para respuestas determinísticas
def _try_calc_intent(question: str) -> Optional[str]:
    q = question.strip().lower()
    # Conteo total / urgentes
    if (("cuant" in q or "cantidad" in q) and any(w in q for w in ["registro", "registros", "reporte", "reportes"])):
        urgent = ("urgente" in q or "urgentes" in q)
        total = count_urgent_reports(None) if urgent else count_reports(None)
        return (
            f"Hay {total} reportes urgentes en total." if urgent else f"Hay {total} registros en total."
        )
    # Ciudad con más reportes
    if ("ciudad" in q and ("más" in q or "mas" in q) and any(w in q for w in ["reporte", "reportes", "registro", "registros"])):
        by_city = count_reports_by_city(None)
        if by_city:
            top = by_city[0]
            return f"La ciudad con más reportes es {top['ciudad']} con {top['count']} registros."
    # Categoría con más reportes
    if ("categor" in q and ("más" in q or "mas" in q)):
        by_cat = count_reports_by_category(None)
        if by_cat:
            top = by_cat[0]
            return f"La categoría con más reportes es {top['categoria']} con {top['count']} registros."
    # Mes con más reportes
    if ("mes" in q and ("más" in q or "mas" in q)):
        monthly = monthly_counts(None)
        if monthly:
            top = max(monthly, key=lambda x: x["count"])
            return f"El mes con más reportes es {top['mes']} con {top['count']} registros."
    return None


# Utilidad para normalizar y comparar nombres con y sin acentos
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

# Extrae filtros de fecha (YYYY o YYYY-MM) desde la pregunta
def _extract_date_filters(question: str) -> Dict[str, Any]:
    q = question.lower()
    filters: Dict[str, Any] = {}
    # YYYY-MM
    mm = re.search(r"\b((?:19|20)\d{2})-(\d{1,2})\b", q)
    if mm:
        year = mm.group(1)
        month = int(mm.group(2))
        filters["fecha_desde"] = f"{year}-{month:02d}-01"
        filters["fecha_hasta"] = f"{year}-{month:02d}-31"
        return filters
    # Mes en español + año
    MONTHS_ES = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "setiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }
    ys = re.findall(r"\b((?:19|20)\d{2})\b", q)
    for mname, mnum in MONTHS_ES.items():
        if mname in q and ys:
            year = ys[0]
            filters["fecha_desde"] = f"{year}-{mnum}-01"
            filters["fecha_hasta"] = f"{year}-{mnum}-31"
            return filters
    # Rango de años (uno o dos)
    if ys:
        y1 = ys[0]
        y2 = ys[-1]
        filters["fecha_desde"] = f"{y1}-01-01"
        filters["fecha_hasta"] = f"{y2}-12-31"
        return filters
    return filters

# Construye líneas de estadísticas agregadas basadas en la intención de la pregunta
def _build_stats_context(question: str) -> List[str]:
    q = question.strip().lower()
    norm_q = _strip_accents(q)
    date_filters = _extract_date_filters(q)
    lines: List[str] = []

    # Totales (y urgentes si se pide)
    if (("cuant" in q or "cantidad" in q) and any(w in q for w in ["registro", "registros", "reporte", "reportes"])):
        if ("urgente" in q or "urgentes" in q):
            total_urg = count_urgent_reports(date_filters or None)
            lines.append(f"Total urgentes: {total_urg}")
        total = count_reports(date_filters or None)
        lines.append(f"Total registros: {total}")

    # Por ciudad, si se mencionan ciudades
    by_city_all = count_reports_by_city(None)  # solo para descubrir nombres existentes
    for c in by_city_all:
        name = c["ciudad"]
        if not name:
            continue
        name_norm = _strip_accents(name.lower())
        if name_norm and name_norm in norm_q:
            base_filters = dict(date_filters) if date_filters else {}
            base_filters["ciudad"] = name
            cnt = int(count_reports(base_filters))
            line = f"Ciudad: {name}; registros: {cnt}"
            if ("urgente" in q or "urgentes" in q):
                u = int(count_urgent_reports(base_filters))
                line += f"; urgentes: {u}"
            lines.append(line)

    # Por categoría, si se mencionan
    by_cat_all = count_reports_by_category(None)  # para descubrir nombres de categorías
    for cat in by_cat_all:
        cname = cat["categoria"]
        if not cname:
            continue
        cname_norm = _strip_accents(cname.lower())
        if cname_norm in norm_q:
            base_filters = dict(date_filters) if date_filters else {}
            base_filters["categoria_problema"] = cname
            cnt = int(count_reports(base_filters))
            line = f"Categoría: {cname}; registros: {cnt}"
            if ("urgente" in q or "urgentes" in q):
                u = int(count_urgent_reports(base_filters))
                line += f"; urgentes: {u}"
            lines.append(line)

    # Top ciudad / categoría si se pide "más" (aplica filtros de fecha)
    if (("más" in q or "mas" in q) and "ciudad" in q and not any(l.startswith("Ciudad:") for l in lines)):
        by_city_filtered = count_reports_by_city(date_filters or None)
        if by_city_filtered:
            top = by_city_filtered[0]
            lines.append(f"Top ciudad por registros: {top['ciudad']} ({int(top['count'])})")
    if (("más" in q or "mas" in q) and "categor" in q and not any(l.startswith("Categoría:") for l in lines)):
        by_cat_filtered = count_reports_by_category(date_filters or None)
        if by_cat_filtered:
            topc = by_cat_filtered[0]
            lines.append(f"Top categoría por registros: {topc['categoria']} ({int(topc['count'])})")

    # Pico mensual si se menciona "mes" (aplica filtros de fecha)
    if ("mes" in q):
        monthly = monthly_counts(date_filters or None)
        if monthly:
            peak = max(monthly, key=lambda x: x["count"])
            lines.append(f"Mes pico de registros: {peak['mes']} ({int(peak['count'])})")

    return lines


@app.post("/ask", response_model=AskSimpleResponse)
async def ask(req: AskRequest) -> AskSimpleResponse:
    # Construir estadísticas para que el MODELO las use en la respuesta
    stats_lines = _build_stats_context(req.texto)

    contexts, used_fts = search_reports(req.texto, k=MAX_CTX_DOCS, filters=None)

    # Siempre invocar al LLM, incluyendo estadísticas agregadas en el Contexto
    prompt = build_prompt(contexts, req.texto, stats_lines=stats_lines if stats_lines else None)

    payload = {
        "prompt": prompt,
        "n_predict": N_PREDICT,
        "temperature": TEMPERATURE,
        "top_k": TOP_K,
        "top_p": TOP_P,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(LLM_TIMEOUT_SECONDS)) as client:
        try:
            r = await client.post(f"{LLM_URL}/completion", json=payload)
            r.raise_for_status()
            data = r.json()
            # Try multiple possible keys depending on server version
            text = data.get("content") or data.get("result") or data.get("text") or ""
        except httpx.TimeoutException:
            text = (
                "El modelo tardó demasiado en responder; se agotó el tiempo de espera. "
                "Prueba una consulta más breve o vuelve a intentarlo más tarde."
            )
        except httpx.HTTPError as e:
            text = f"No se pudo contactar el modelo: {str(e)}"

    return AskSimpleResponse(answer=text)





@app.get("/status")
async def status() -> Dict[str, str]:
    return {"status": "ok"}