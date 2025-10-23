from __future__ import annotations

import sqlite3
from typing import List, Dict, Any, Optional, Tuple

from .settings import DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _has_fts(conn: sqlite3.Connection) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='report_search'"
    )
    return cur.fetchone() is not None


def _apply_filters(where: List[str], params: List[Any], filters: Optional[Dict[str, Any]]) -> None:
    if not filters:
        return
    if (city := filters.get("ciudad")):
        where.append("r.ciudad = ?")
        params.append(city)
    if (cat := filters.get("categoria_problema")):
        where.append("r.categoria_problema = ?")
        params.append(cat)
    if (urg := filters.get("urgente")) is not None:
        where.append("r.urgente = ?")
        params.append(int(urg))
    if (dfrom := filters.get("fecha_desde")):
        where.append("r.fecha_reporte >= ?")
        params.append(dfrom)
    if (dto := filters.get("fecha_hasta")):
        where.append("r.fecha_reporte <= ?")
        params.append(dto)


def search_reports(query: str, k: int = 8, filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], bool]:
    """Return top-k contexts for query; bool indicates whether FTS was used."""
    conn = _connect()
    try:
        used_fts = _has_fts(conn)
        params: List[Any] = []
        where: List[str] = []
        _apply_filters(where, params, filters)
        where_clause = (" AND ".join(where)) if where else "1=1"

        if used_fts:
            sql = (
                "SELECT r.id, r.comentario, r.ciudad, r.categoria_problema, r.fecha_reporte, r.urgente "
                "FROM report_search s JOIN reports r ON r.id = s.rowid "
                "WHERE (s MATCH ?) AND (" + where_clause + ") "
                "ORDER BY bm25(s) LIMIT ?"
            )
            params = [query] + params + [k]
        else:
            # Fallback LIKE across important text columns
            like = f"%{query}%"
            sql = (
                "SELECT r.id, r.comentario, r.ciudad, r.categoria_problema, r.fecha_reporte, r.urgente "
                "FROM reports r WHERE (r.comentario LIKE ? OR r.ciudad LIKE ? OR r.categoria_problema LIKE ?) "
                "AND (" + where_clause + ") ORDER BY r.fecha_reporte DESC LIMIT ?"
            )
            params = [like, like, like] + params + [k]

        rows = conn.execute(sql, params).fetchall()
        contexts = [dict(row) for row in rows]
        return contexts, used_fts
    finally:
        conn.close()
