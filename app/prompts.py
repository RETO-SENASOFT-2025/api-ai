from __future__ import annotations

from typing import List, Dict, Optional

SYSTEM = (
    "Eres un analista cívico. Responde EXCLUSIVAMENTE en español (español neutro) y "
    "EXCLUSIVAMENTE con base en el Contexto de reportes ciudadanos proveniente de la base SQLite indicada cuando exista. "
    "No inventes datos ni cifras; evita usar conocimientos externos. "
    "Cita IDs relevantes solo si hay contexto. Si el Contexto está vacío, ofrece una respuesta breve y general sin datos concretos. "
    "Si hay Estadísticas agregadas, utilízalas para sustentar números y proporciones. "
    "Si la pregunta viene en otro idioma, tradúcela y responde en español. No incluyas texto en inglés."
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


def build_prompt(contexts: List[Dict], question: str, stats_lines: Optional[List[str]] = None) -> str:
    ctx = render_contexts(contexts)
    stats = "\n".join(stats_lines) if stats_lines else ""
    instructions = (
        "Responde ÚNICAMENTE en español y limita tus afirmaciones al Contexto anterior cuando esté disponible. "
        "Usa también las Estadísticas agregadas si están presentes para respaldar números. "
        "Devuelve hallazgos y conclusiones basadas en ese Contexto y cita IDs solo si aplica. "
        "No repitas los encabezados 'Contexto:' ni 'Pregunta:' ni el contenido del prompt; "
        "entrega la respuesta directamente en un párrafo o lista concisa."
    )
    stats_block = f"\n\nEstadísticas agregadas:\n{stats}" if stats else ""
    return f"{SYSTEM}\n\nContexto:\n{ctx}{stats_block}\n\nPregunta:\n{question}\n\n{instructions}\n"