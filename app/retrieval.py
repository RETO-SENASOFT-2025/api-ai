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
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='report_search'"
    )
    row = cur.fetchone()
    return bool(row and row["sql"] and "using fts5" in row["sql"].lower())


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
        filters_params: List[Any] = []
        where: List[str] = []
        _apply_filters(where, filters_params, filters)
        where_clause = (" AND ".join(where)) if where else "1=1"

        if used_fts:
            sql_fts = (
                "SELECT r.id, r.comentario, r.ciudad, r.categoria_problema, r.fecha_reporte, r.urgente "
                "FROM report_search JOIN reports r ON r.id = report_search.rowid "
                "WHERE (report_search MATCH ?) AND (" + where_clause + ") "
                "ORDER BY bm25(report_search) LIMIT ?"
            )
            params_fts = [query] + filters_params + [k]
            try:
                rows = conn.execute(sql_fts, params_fts).fetchall()
            except sqlite3.OperationalError:
                # Fallback gracefully if FTS is misconfigured or unavailable
                used_fts = False
                like = f"%{query}%"
                sql_like = (
                    "SELECT r.id, r.comentario, r.ciudad, r.categoria_problema, r.fecha_reporte, r.urgente "
                    "FROM reports r WHERE (r.comentario LIKE ? OR r.ciudad LIKE ? OR r.categoria_problema LIKE ?) "
                    "AND (" + where_clause + ") ORDER BY r.fecha_reporte DESC LIMIT ?"
                )
                params_like = [like, like, like] + filters_params + [k]
                rows = conn.execute(sql_like, params_like).fetchall()
        else:
            # Fallback LIKE across important text columns
            like = f"%{query}%"
            sql_like = (
                "SELECT r.id, r.comentario, r.ciudad, r.categoria_problema, r.fecha_reporte, r.urgente "
                "FROM reports r WHERE (r.comentario LIKE ? OR r.ciudad LIKE ? OR r.categoria_problema LIKE ?) "
                "AND (" + where_clause + ") ORDER BY r.fecha_reporte DESC LIMIT ?"
            )
            params_like = [like, like, like] + filters_params + [k]
            rows = conn.execute(sql_like, params_like).fetchall()

        contexts = [dict(row) for row in rows]
        return contexts, used_fts
    finally:
        conn.close()