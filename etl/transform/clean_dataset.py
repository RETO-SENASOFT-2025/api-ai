from __future__ import annotations

import re
from typing import List

import pandas as pd

# Column mapping from source (Spanish) to normalized snake_case
COLUMN_RENAME_MAP = {
    "ID": "id",
    "Nombre": "nombre",
    "Edad": "edad",
    "Género": "genero",
    "Ciudad": "ciudad",
    "Comentario": "comentario",
    "Categoría del problema": "categoria_problema",
    "Nivel de urgencia": "nivel_urgencia",
    "Fecha del reporte": "fecha_reporte",
    "Acceso a internet": "acceso_internet",
    "Atención previa del gobierno": "atencion_previa_gobierno",
    "Zona rural": "zona_rural",
}

# Required fields that must not be null
REQUIRED_FIELDS = [
    "nombre",
    "edad",
    "genero",
    "ciudad",
    "comentario",
    "categoria_problema",
    "nivel_urgencia",
    "fecha_reporte",
    "acceso_internet",
    "atencion_previa_gobierno",
    "zona_rural",
]

# Map urgency text to boolean/int for indexing (1=Urgente, 0=No urgente)
URGENCIA_MAP = {
    "Urgente": 1,
    "No urgente": 0,
}

# Normalize genero values
GENERO_MAP = {
    "M": "M",
    "F": "F",
    "Otro": "Otro",
    "O": "Otro",
}


def _trim_strings(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].astype("string").str.strip()
    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=COLUMN_RENAME_MAP)


def _normalize_fecha(df: pd.DataFrame) -> pd.DataFrame:
    # Parse to datetime and normalize to ISO date string YYYY-MM-DD
    df["fecha_reporte"] = pd.to_datetime(
        df["fecha_reporte"],
        errors="coerce",
        dayfirst=False,
    ).dt.date
    # Convert to string for consistent CSV/SQLite storage
    df["fecha_reporte"] = df["fecha_reporte"].astype("string")
    return df


def _normalize_edad(df: pd.DataFrame) -> pd.DataFrame:
    # Ages may come as floats like 23.0; coerce to Int64 and validate range
    df["edad"] = pd.to_numeric(df["edad"], errors="coerce")
    df["edad"] = df["edad"].round().astype("Int64")
    # Filter unrealistic ages
    df = df[(df["edad"].notna()) & (df["edad"] >= 0) & (df["edad"] <= 120)]
    return df


def _normalize_genero(df: pd.DataFrame) -> pd.DataFrame:
    df["genero"] = df["genero"].map(lambda x: GENERO_MAP.get(str(x), None))
    return df


def _normalize_booleans(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["acceso_internet", "atencion_previa_gobierno", "zona_rural"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        df[col] = df[col].where(df[col].isin([0, 1]))  # keep only 0/1
    return df


def _normalize_urgencia(df: pd.DataFrame) -> pd.DataFrame:
    def map_urg(v: object) -> int | None:
        s = str(v).strip().lower()
        if s in ("urgente", "alta", "alta urgencia"):
            return 1
        if s in ("no urgente", "baja", "baja urgencia"):
            return 0
        return None
    df["urgente"] = df["nivel_urgencia"].map(map_urg)
    return df


def _clean_nan_comentario(df: pd.DataFrame) -> pd.DataFrame:
    if "comentario" in df.columns:
        df["comentario"] = df["comentario"].replace(
            to_replace=[r"^\s*$", r"(?i)^nan$", r"(?i)^none$", r"(?i)^null$"],
            value=pd.NA,
            regex=True,
        )
    return df


def transform_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize the dataset according to requirements.

    Steps:
    - Rename columns to snake_case
    - Trim strings
    - Normalize date (fecha_reporte) to YYYY-MM-DD
    - Normalize edad to Int64 and validate range
    - Map genero to known values (M/F/Otro)
    - Ensure booleans (0 carencia, 1 dispone) for acceso_internet, atencion_previa_gobierno, zona_rural
    - Map nivel_urgencia to 'urgente' flag (1/0)
    - Drop rows with nulls in required fields
    - Drop duplicates by id
    """
    # Rename columns
    df = _normalize_columns(df)

    # Basic trims
    df = _trim_strings(df)
    df = _clean_nan_comentario(df)

    # Normalize types and values
    df = _normalize_fecha(df)
    df = _normalize_edad(df)
    df = _normalize_genero(df)
    df = _normalize_booleans(df)
    df = _normalize_urgencia(df)

    # Drop rows with any required field null, and ensure 'urgente' is valid
    df = df.dropna(subset=REQUIRED_FIELDS + ["urgente"]) 

    # Deduplicate on id, keeping first occurrence
    if "id" in df.columns:
        df = df.drop_duplicates(subset=["id"], keep="first")

    # Final type coercions (ensure plain Python ints for SQLite)
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df.dropna(subset=["id"])  # ensure id present
    df["id"] = df["id"].astype(int)

    df["edad"] = df["edad"].astype(int)
    df["acceso_internet"] = df["acceso_internet"].astype(int)
    df["atencion_previa_gobierno"] = df["atencion_previa_gobierno"].astype(int)
    df["zona_rural"] = df["zona_rural"].astype(int)
    df["urgente"] = pd.to_numeric(df["urgente"], errors="coerce").astype(int)

    # Reorder columns for consistency
    ordered_cols: List[str] = [
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
    ]
    df = df[[c for c in ordered_cols if c in df.columns]]
    return df

