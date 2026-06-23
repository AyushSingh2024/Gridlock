from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def ranked_hotspots() -> pd.DataFrame:
    rows = []
    for i in range(30):
        rows.append(
            {
                "cluster_id": 1000 + i,
                "centroid_lat": 12.90 + (i % 10) * 0.01,
                "centroid_lon": 77.50 + (i // 10) * 0.01 + (i % 3) * 0.002,
                "nc_cis": 1.0 + i / 10,
                "point_count": 100 - i,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def temp_processed_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ranked_hotspots: pd.DataFrame) -> Path:
    from src.optimization import patrol_optimizer

    processed = tmp_path / "processed"
    figures = tmp_path / "figures"
    processed.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    ranked_hotspots.to_parquet(processed / "ranked_hotspots.parquet", index=False)

    class NoopFigure:
        def write_html(self, path: Path) -> None:
            Path(path).write_text("<html></html>", encoding="utf-8")

    def ensure_temp_dirs() -> None:
        processed.mkdir(parents=True, exist_ok=True)
        figures.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(patrol_optimizer, "PROCESSED_DIR", processed)
    monkeypatch.setattr(patrol_optimizer, "FIGURES_DIR", figures)
    monkeypatch.setattr(patrol_optimizer, "ensure_dirs", ensure_temp_dirs)
    monkeypatch.setattr(patrol_optimizer.px, "scatter_map", lambda *args, **kwargs: NoopFigure())
    return processed
