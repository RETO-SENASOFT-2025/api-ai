from __future__ import annotations

from typing import Optional, Dict, Any, List

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from .settings import LLM_URL, N_PREDICT, TEMPERATURE, TOP_K, TOP_P, MAX_CTX_DOCS
from .retrieval import search_reports
from .prompts import build_prompt

app = FastAPI(title="RAG API - Mistral + SQLite FTS5")


class AskRequest(BaseModel):
    texto: str


class AskResponse(BaseModel):
    answer: str
    contexts: List[Dict[str, Any]]
    used_fts: bool


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    contexts, used_fts = search_reports(req.texto, k=MAX_CTX_DOCS, filters=None)
    prompt = build_prompt(contexts, req.texto)

    payload = {
        "prompt": prompt,
        "n_predict": N_PREDICT,
        "temperature": TEMPERATURE,
        "top_k": TOP_K,
        "top_p": TOP_P,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        r = await client.post(f"{LLM_URL}/completion", json=payload)
        r.raise_for_status()
        data = r.json()
        # Try multiple possible keys depending on server version
        text = data.get("content") or data.get("result") or data.get("text") or ""

    return AskResponse(answer=text, contexts=contexts, used_fts=used_fts)


@app.get("/status")
async def status() -> Dict[str, str]:
    return {"status": "ok"}
