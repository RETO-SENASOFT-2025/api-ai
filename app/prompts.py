from __future__ import annotations

from typing import List, Dict

SYSTEM = (
    "Eres un analista cívico. Responde EXCLUSIVAMENTE con base en el Contexto "
    "de reportes ciudadanos proveniente de la base SQLite indicada. No inventes datos, "
    "no uses conocimientos externos ni información fuera del Contexto. Si el Contexto no "
    "es suficiente, indica explícitamente la falta de evidencia y sugiere cómo consultar "
    "la misma base para obtener más información. Cita IDs relevantes siempre que sea posible."
)


def render_contexts(contexts: List[Dict]) -> str:
    lines = []
    for c in contexts:
        line = (
            f"- id={c['id']} fecha={c['fecha_reporte']} ciudad={c['ciudad']} "
            f"categoria={c['categoria_problema']} urgente={c['urgente']}: {c['comentario']}"
        )
        lines.append(line)
    return "\n".join(lines)


def build_prompt(contexts: List[Dict], question: str) -> str:
    ctx = render_contexts(contexts)
    instructions = (
        "Responde en español y limita tus afirmaciones ÚNICAMENTE al Contexto anterior. "
        "Devuelve hallazgos y conclusiones basadas en ese Contexto y cita IDs. "
        "Si la pregunta excede el Contexto o falta información, explica qué falta y "
        "no agregues información externa ni especulaciones."
    )
    return f"{SYSTEM}\n\nContexto:\n{ctx}\n\nPregunta:\n{question}\n\n{instructions}\n"