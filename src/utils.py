from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def normalize(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    min_value = float(values.min())
    max_value = float(values.max())
    if np.isclose(max_value, min_value):
        return pd.Series(np.zeros(len(values)), index=values.index)
    return (values - min_value) / (max_value - min_value)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    radius = 6371.0
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(
        np.radians, [lat1, lon1, lat2, lon2]
    )
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    return float(2 * radius * np.arcsin(np.sqrt(a)))


def route_distance_km(points: Iterable[tuple[float, float]]) -> float:
    points = list(points)
    if len(points) < 2:
        return 0.0
    return sum(
        haversine_km(a[0], a[1], b[0], b[1])
        for a, b in zip(points[:-1], points[1:])
    )
