from __future__ import annotations

import os
import json
import sqlite3
import argparse
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Renderiza sin necesidad de UI/display
import matplotlib.pyplot as plt
import seaborn as sns

DEFAULT_DB_PATH = os.getenv("DB_PATH", os.path.join("data", "db", "reports.sqlite"))
OUTPUT_DIR = os.path.join("data", "analysis")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_reports(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * FROM reports", conn)
    finally:
        conn.close()

    # Normaliza tipos útiles para gráficas
    if "fecha_reporte" in df.columns:
        df["fecha_reporte"] = pd.to_datetime(df["fecha_reporte"], errors="coerce")
    return df


def assess_db(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Verifica tablas e índices básicos
        tbls = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {t[0] for t in tbls}
        has_reports = "reports" in names
        has_fts = "report_search" in names
        row_count = conn.execute("SELECT COUNT(1) FROM reports").fetchone()[0] if has_reports else 0
        idxs = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        idx_names = [i[0] for i in idxs]
        return {
            "db_path": os.path.abspath(db_path),
            "has_reports": has_reports,
            "has_fts": has_fts,
            "row_count": row_count,
            "indexes": idx_names,
        }
    finally:
        conn.close()


def plot_heatmap_correlations(df: pd.DataFrame, out_dir: str) -> str:
    num_cols = [c for c in [
        "edad", "acceso_internet", "atencion_previa_gobierno", "zona_rural", "urgente"
    ] if c in df.columns]
    corr = df[num_cols].corr(numeric_only=True)
    plt.figure(figsize=(6, 4))
    sns.heatmap(corr, annot=True, cmap="Reds", fmt=".2f")
    plt.title("Correlaciones (numéricas)")
    out_path = os.path.join(out_dir, "heatmap_correlaciones.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def plot_heatmap_ciudad_categoria(df: pd.DataFrame, out_dir: str, top_cities: int = 12, top_cats: int = 12) -> str:
    if "ciudad" not in df.columns or "categoria_problema" not in df.columns:
        return ""
    top_ciudades = df["ciudad"].value_counts().nlargest(top_cities).index
    top_categorias = df["categoria_problema"].value_counts().nlargest(top_cats).index
    sub = df[df["ciudad"].isin(top_ciudades) & df["categoria_problema"].isin(top_categorias)]
    pivot = sub.pivot_table(index="ciudad", columns="categoria_problema", values="id", aggfunc="count", fill_value=0)
    plt.figure(figsize=(10, 6))
    sns.heatmap(pivot, cmap="Blues")
    plt.title("Mapa de calor: Ciudad vs Categoría (Top)")
    out_path = os.path.join(out_dir, "heatmap_ciudad_categoria.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def plot_bar_categorias(df: pd.DataFrame, out_dir: str, top: int = 15) -> str:
    if "categoria_problema" not in df.columns:
        return ""
    counts = df["categoria_problema"].value_counts().nlargest(top)
    plt.figure(figsize=(10, 5))
    sns.barplot(x=counts.index, y=counts.values, color="tab:blue")
    plt.xticks(rotation=45, ha="right")
    plt.title("Distribución de categorías (Top)")
    plt.ylabel("# reportes")
    out_path = os.path.join(out_dir, "bar_categorias.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def plot_bar_urgente(df: pd.DataFrame, out_dir: str) -> str:
    if "urgente" not in df.columns:
        return ""
    counts = df["urgente"].value_counts().sort_index()
    labels = ["No urgente (0)", "Urgente (1)"] if set(counts.index) == {0, 1} else counts.index
    plt.figure(figsize=(5, 4))
    sns.barplot(x=labels, y=counts.values, palette=["tab:gray", "tab:red"])
    plt.title("Urgencia")
    plt.ylabel("# reportes")
    out_path = os.path.join(out_dir, "bar_urgente.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def plot_bar_ciudades(df: pd.DataFrame, out_dir: str, top: int = 15) -> str:
    if "ciudad" not in df.columns:
        return ""
    counts = df["ciudad"].value_counts().nlargest(top)
    plt.figure(figsize=(10, 5))
    sns.barplot(x=counts.index, y=counts.values, color="tab:green")
    plt.xticks(rotation=45, ha="right")
    plt.title("Top ciudades por # de reportes")
    plt.ylabel("# reportes")
    out_path = os.path.join(out_dir, "bar_ciudades.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def plot_linea_tiempo(df: pd.DataFrame, out_dir: str) -> str:
    if "fecha_reporte" not in df.columns:
        return ""
    ts = df.dropna(subset=["fecha_reporte"]).copy()
    ts["fecha"] = ts["fecha_reporte"].dt.to_period("D").dt.to_timestamp()
    daily = ts.groupby("fecha").size().sort_index()
    plt.figure(figsize=(10, 4))
    plt.plot(daily.index, daily.values, color="tab:blue")
    plt.title("Reportes por día")
    plt.ylabel("# reportes")
    plt.xlabel("Fecha")
    out_path = os.path.join(out_dir, "line_diario.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def plot_linea_mensual(df: pd.DataFrame, out_dir: str) -> str:
    if "fecha_reporte" not in df.columns:
        return ""
    ts = df.dropna(subset=["fecha_reporte"]).copy()
    ts["mes"] = ts["fecha_reporte"].dt.to_period("M").dt.to_timestamp()
    monthly = ts.groupby("mes").size().sort_index()
    plt.figure(figsize=(10, 4))
    plt.plot(monthly.index, monthly.values, color="tab:orange")
    plt.title("Reportes por mes")
    plt.ylabel("# reportes")
    plt.xlabel("Mes")
    out_path = os.path.join(out_dir, "line_mensual.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def generate_all(db_path: str, out_dir: str = OUTPUT_DIR) -> dict:
    _ensure_dir(out_dir)
    df = load_reports(db_path)
    summary = assess_db(db_path)

    outputs = {
        "heatmap_correlaciones": plot_heatmap_correlations(df, out_dir),
        "heatmap_ciudad_categoria": plot_heatmap_ciudad_categoria(df, out_dir),
        "bar_categorias": plot_bar_categorias(df, out_dir),
        "bar_ciudades": plot_bar_ciudades(df, out_dir),
        "bar_urgente": plot_bar_urgente(df, out_dir),
        "line_diario": plot_linea_tiempo(df, out_dir),
        "line_mensual": plot_linea_mensual(df, out_dir),
    }

    # Guarda resumen de integración de DB + rutas de salida
    summary_out = {
        "db": summary,
        "charts": {k: os.path.abspath(v) if v else "" for k, v in outputs.items()},
        "rows": len(df),
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary_out, f, ensure_ascii=False, indent=2)

    # Mensaje final
    print("Análisis completado. Salidas:")
    for k, v in summary_out["charts"].items():
        print(f"- {k}: {v}")
    print(f"Resumen DB: {json.dumps(summary_out['db'], ensure_ascii=False)}")
    return summary_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera gráficas (heatmap, barras, líneas) desde SQLite")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Ruta de la base SQLite (por defecto data/db/reports.sqlite)")
    parser.add_argument("--out-dir", default=OUTPUT_DIR, help="Carpeta de salida para las gráficas")
    args = parser.parse_args()
    generate_all(args.db_path, args.out_dir)


if __name__ == "__main__":
    main()
