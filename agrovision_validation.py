"""Independent validation utilities for comparing AGROVISION with station observations.

Metrics follow standard paired-observation definitions. Positive bias means
NASA POWER/model values are higher than the station observations.
"""
import numpy as np
import pandas as pd


def paired_validation_metrics(model: pd.Series, observed: pd.Series) -> dict:
    """Align two dated series and calculate validation statistics.

    Inputs must already represent the same physical quantity, unit and
    temporal aggregation. Missing pairs are excluded, never imputed.
    """
    pair = pd.concat(
        [pd.to_numeric(model, errors="coerce").rename("model"),
         pd.to_numeric(observed, errors="coerce").rename("observed")],
        axis=1,
    ).replace([np.inf, -np.inf], np.nan).dropna()
    if len(pair) < 3:
        raise ValueError("At least three paired, valid observations are required.")
    error = pair["model"] - pair["observed"]
    bias = float(error.mean())
    mae = float(error.abs().mean())
    rmse = float(np.sqrt((error ** 2).mean()))
    denominator = float(((pair["observed"] - pair["observed"].mean()) ** 2).sum())
    r_squared = None if denominator == 0 else float(
        1 - (error ** 2).sum() / denominator
    )
    return {
        "n": int(len(pair)),
        "bias": bias,
        "mae": mae,
        "rmse": rmse,
        "r_squared": r_squared,
        "paired": pair,
    }
