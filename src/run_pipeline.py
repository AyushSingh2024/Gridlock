from __future__ import annotations

import json

from src.clustering.detect_hotspots import detect_hotspots
from src.features.build_features import build_features
from src.ingestion.clean_data import clean
from src.optimization.patrol_optimizer import optimize_patrol_routes
from src.scoring.nc_cis import score_hotspots


def main() -> None:
    results = {
        "clean": clean(),
        "features": build_features(),
        "clustering": detect_hotspots(),
        "scoring": score_hotspots(),
        "optimization": optimize_patrol_routes(),
    }
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
