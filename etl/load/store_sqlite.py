from __future__ import annotations

import os
import sqlite3
from typing import Iterable

import pandas as pd

DB_OUTPUT_PATH = os.path.join("data", "db", "reports.sqlite")


SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = -20000; -- 20MB page cache

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    edad INTEGER NOT NULL,
    genero TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    comentario TEXT NOT NULL,
    categoria_problema TEXT NOT NULL,
    nivel_urgencia TEXT NOT NULL,
    urgente INTEGER NOT NULL, -- 1 urgente, 0 no urgente
    fecha_reporte TEXT NOT NULL, -- ISO YYYY-MM-DD
    acceso_internet INTEGER NOT NULL, -- 0 carencia, 1 dispone
    atencion_previa_gobierno INTEGER NOT NULL,
    zona_rural INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_fecha ON reports (fecha_reporte);
CREATE INDEX IF NOT EXISTS idx_reports_ciudad ON reports (ciudad);
CREATE INDEX IF NOT EXISTS idx_reports_categoria ON reports (categoria_problema);
CREATE INDEX IF NOT EXISTS idx_reports_urgente ON reports (urgente);
"""


def _ensure_dirs(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _remove_db_files(path: str) -> None:
    # Remove main DB and any WAL/SHM sidecar files to avoid corruption
    for p in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def _insert_reports(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    # Use executemany inside a single transaction for speed
    rows = df[[
        "id",
        "nombre",
        "edad",
        "genero",
        "ciudad",
        "comentario",
        "categoria_problema",
        "nivel_urgencia",
        "urgente",
        "fecha_reporte",
        "acceso_internet",
        "atencion_previa_gobierno",
        "zona_rural",
    ]].itertuples(index=False, name=None)

    conn.executemany(
        """
        INSERT OR REPLACE INTO reports (
            id, nombre, edad, genero, ciudad, comentario,
            categoria_problema, nivel_urgencia, urgente, fecha_reporte,
            acceso_internet, atencion_previa_gobierno, zona_rural
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        list(rows),
    )


def _setup_fts(conn: sqlite3.Connection) -> None:
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS report_search USING fts5(
                comentario, ciudad, categoria_problema, content='reports'
            );
            """
        )
    except sqlite3.DatabaseError as e:
        # FTS5 puede no estar disponible o hay corrupción de DB: continuar sin FTS
        print(f"No se pudo crear FTS5 (soporte inexistente o DB corrupta). Motivo: {e}")


def _populate_fts(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("DELETE FROM report_search")
        conn.execute(
            """
            INSERT INTO report_search(rowid, comentario, ciudad, categoria_problema)
            SELECT id, comentario, ciudad, categoria_problema FROM reports
            """
        )
    except sqlite3.DatabaseError as e:
        # FTS5 puede no estar disponible o hay corrupción de DB: continuar sin FTS
        print(f"No se pudo poblar FTS5 (soporte inexistente o DB corrupta). Motivo: {e}")


def build_sqlite_db(df: pd.DataFrame, output_path: str = DB_OUTPUT_PATH) -> str:
    """Create SQLite DB optimized for querying by the model or APIs.

    Returns the absolute path to the generated database file.
    """
    _ensure_dirs(output_path)
    # Rebuild DB from scratch and clear any WAL/SHM sidecars
    _remove_db_files(output_path)

    conn = sqlite3.connect(output_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.execute("BEGIN")
        _insert_reports(conn, df)
        conn.commit()

        # Try to enable FTS5 and populate
        _setup_fts(conn)
        _populate_fts(conn)
        conn.commit()
    finally:
        conn.close()

    return os.path.abspath(output_path)