from __future__ import annotations

from typing import List, Dict

SYSTEM = (
    "Eres un analista cívico. Responde con base en el contexto "
    "de reportes ciudadanos. Resume de forma clara, cita IDs relevantes "
    "y señala incertidumbres si faltan datos."
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
        "Responde en español. Si corresponde, devuelve una lista de hallazgos y "
        "conclusiones. Si la pregunta excede el contexto, explica qué falta y sugiere "
        "cómo consultarlo."
    )
    return f"{SYSTEM}\n\nContexto:\n{ctx}\n\nPregunta:\n{question}\n\n{instructions}\n"
