from __future__ import annotations

import os
from typing import Optional

import pandas as pd

# Paths are relative to repo root
DEFAULT_INPUT_PATHS = [
    os.path.join("data", "dataset", "dataset.csv"),
]


def _resolve_path(csv_path: Optional[str]) -> str:
    if csv_path:
        return csv_path
    env_path = os.getenv("DATASET_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    for p in DEFAULT_INPUT_PATHS:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(
        "Dataset not found. Checked DATASET_PATH and default paths: "
        + ", ".join(DEFAULT_INPUT_PATHS)
    )


def read_dataset(csv_path: Optional[str] = None) -> pd.DataFrame:
    """Read the source dataset CSV into a DataFrame.

    - Accepts optional custom path; checks env DATASET_PATH; falls back to common locations
    - Treat common empty markers as NaN
    - Keeps original column names; transformation module will normalize
    """
    path = _resolve_path(csv_path)

    df = pd.read_csv(
        path,
        encoding="utf-8",
        na_values=["", "NA", "NaN", "null", "None"],
        keep_default_na=True,
    )
    return df
