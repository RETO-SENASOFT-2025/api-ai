from __future__ import annotations

import os
from typing import Tuple

import pandas as pd

from etl.extract.dataset import read_dataset
from etl.transform.clean_dataset import transform_dataset
from etl.load.store_sqlite import build_sqlite_db


PROCESSED_CSV_PATH = os.path.join("data", "processed", "dataset_clean.csv")

def _ensure_dirs(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _verify_file_written(path: str) -> None:
    abs_path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise RuntimeError(f"No se generó el CSV en: {abs_path}")


def run_etl(input_path: str | None = None) -> Tuple[str, str]:
    """Run ETL on the dataset and export CSV and SQLite DB.

    Returns (processed_csv_abs_path, sqlite_abs_path)
    """
    # Extract
    src_df = read_dataset(input_path)
    src_count = len(src_df)

    # Transform
    clean_df = transform_dataset(src_df)
    clean_count = len(clean_df)

    # Export CSV
    _ensure_dirs(PROCESSED_CSV_PATH)
    clean_df.to_csv(PROCESSED_CSV_PATH, index=False, encoding="utf-8")
    _verify_file_written(PROCESSED_CSV_PATH)

    # Build SQLite DB
    sqlite_path = build_sqlite_db(clean_df)

    print(
        f"ETL completed. Rows: source={src_count}, cleaned={clean_count}.\n"
        f"CSV: {os.path.abspath(PROCESSED_CSV_PATH)}\n"
        f"SQLite: {sqlite_path}"
    )

    return os.path.abspath(PROCESSED_CSV_PATH), sqlite_path


if __name__ == "__main__":
    run_etl()
