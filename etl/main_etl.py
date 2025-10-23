from __future__ import annotations

import os
from typing import Tuple

import pandas as pd

from etl.extract.dataset import read_dataset
from etl.transform.clean_dataset import transform_dataset
from etl.load.store_sqlite import build_sqlite_db


# CSV export deshabilitado: ETL ahora solo construye la base SQLite


def run_etl(input_path: str | None = None) -> str:
    """Run ETL on the dataset and build SQLite DB only.

    Returns sqlite_abs_path
    """
    # Extract
    src_df = read_dataset(input_path)
    src_count = len(src_df)

    # Transform
    clean_df = transform_dataset(src_df)
    clean_count = len(clean_df)

    # Build SQLite DB only
    sqlite_path = build_sqlite_db(clean_df)

    print(
        f"ETL completed. Rows: source={src_count}, cleaned={clean_count}.\n"
        f"SQLite: {sqlite_path}"
    )

    return sqlite_path


if __name__ == "__main__":
    run_etl()
