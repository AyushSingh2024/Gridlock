from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DIR, ensure_dirs


def detection_event(
    latitude: float,
    longitude: float,
    confidence: float,
    source_image: str | None = None,
) -> dict:
    return {
        "id": f"CV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "latitude": latitude,
        "longitude": longitude,
        "location": "cv_live_detection",
        "vehicle_number": None,
        "vehicle_type": "UNKNOWN",
        "description": f"Illegal parking CV detection, confidence={confidence:.2f}",
        "violation_type": '["WRONG PARKING"]',
        "violation": "WRONG PARKING",
        "created_datetime": datetime.now(timezone.utc).isoformat(),
        "validation_status": "cv_unverified",
        "cv_confidence": confidence,
        "cv_source_image": source_image,
    }


def append_detection(event: dict) -> Path:
    ensure_dirs()
    output = PROCESSED_DIR / "cv_detection_events.parquet"
    row = pd.DataFrame([event])
    if output.exists():
        existing = pd.read_parquet(output)
        row = pd.concat([existing, row], ignore_index=True)
    row.to_parquet(output, index=False)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--confidence", type=float, default=0.85)
    parser.add_argument("--source-image", type=str, default=None)
    args = parser.parse_args()
    event = detection_event(args.lat, args.lon, args.confidence, args.source_image)
    output = append_detection(event)
    print(json.dumps({"written": str(output), "event": event}, indent=2))


if __name__ == "__main__":
    main()
