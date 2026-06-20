from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

import pandas as pd

from src.config import (
    BENGALURU_BOUNDS,
    EXPECTED_COLUMNS,
    PARKING_VIOLATIONS,
    PROCESSED_DIR,
    REPORTS_DIR,
    ensure_dirs,
    find_raw_csv,
)
from src.utils import write_json


def parse_violation_list(value) -> list[str]:
    if pd.isna(value):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value]
    text = str(value).strip()
    if not text:
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed]
        except Exception:
            continue
    return [text]


def validate_schema(df: pd.DataFrame) -> dict:
    observed = list(df.columns)
    return {
        "row_count": int(len(df)),
        "expected_column_count": len(EXPECTED_COLUMNS),
        "observed_column_count": len(observed),
        "columns_match_expected": observed == EXPECTED_COLUMNS,
        "missing_columns": [col for col in EXPECTED_COLUMNS if col not in observed],
        "extra_columns": [col for col in observed if col not in EXPECTED_COLUMNS],
        "latitude_null_pct": float(df["latitude"].isna().mean() * 100),
        "longitude_null_pct": float(df["longitude"].isna().mean() * 100),
    }


def compute_reactivity_stats(raw: pd.DataFrame, cleaned: pd.DataFrame) -> dict:
    created = pd.to_datetime(raw["created_datetime"], errors="coerce", utc=True)
    validation = pd.to_datetime(raw["validation_timestamp"], errors="coerce", utc=True)
    lag_hours = (validation - created).dt.total_seconds() / 3600
    lag_hours = lag_hours[lag_hours.notna()]

    cleaned_created = pd.to_datetime(cleaned["created_datetime"], errors="coerce", utc=True)
    date_min = cleaned_created.min()
    date_max = cleaned_created.max()

    return {
        "raw_records": int(len(raw)),
        "parking_violation_events": int(len(cleaned)),
        "parking_unique_records": int(cleaned["id"].nunique()),
        "unique_locations_rounded_6dp": int(
            cleaned[["latitude", "longitude"]].round(6).drop_duplicates().shape[0]
        ),
        "start_datetime": str(date_min) if pd.notna(date_min) else None,
        "end_datetime": str(date_max) if pd.notna(date_max) else None,
        "closed_datetime_non_null_pct": float(raw["closed_datetime"].notna().mean() * 100),
        "action_taken_timestamp_non_null_pct": float(
            raw["action_taken_timestamp"].notna().mean() * 100
        ),
        "validation_timestamp_non_null_pct": float(
            raw["validation_timestamp"].notna().mean() * 100
        ),
        "validation_lag_median_hours": float(lag_hours.median())
        if not lag_hours.empty
        else None,
        "validation_lag_mean_hours": float(lag_hours.mean()) if not lag_hours.empty else None,
        "no_junction_pct": float((raw["junction_name"].fillna("") == "No Junction").mean() * 100),
    }


def clean(raw_csv: Path | None = None) -> dict:
    ensure_dirs()
    raw_csv = raw_csv or find_raw_csv()
    raw = pd.read_csv(raw_csv, low_memory=False)

    schema_stats = validate_schema(raw)

    df = raw.copy()
    df["created_datetime"] = pd.to_datetime(df["created_datetime"], errors="coerce", utc=True)
    df["validation_timestamp"] = pd.to_datetime(
        df["validation_timestamp"], errors="coerce", utc=True
    )
    df["violation"] = df["violation_type"].apply(parse_violation_list)
    df = df.explode("violation")
    df["violation"] = df["violation"].astype("string").str.strip()
    df = df[df["violation"].isin(PARKING_VIOLATIONS)].copy()

    bounds = BENGALURU_BOUNDS
    in_bounds = (
        df["latitude"].between(bounds["min_lat"], bounds["max_lat"])
        & df["longitude"].between(bounds["min_lon"], bounds["max_lon"])
    )
    outlier_events = int((~in_bounds).sum())
    df = df[in_bounds].copy()
    df = df.drop_duplicates(subset=["id", "violation"]).reset_index(drop=True)

    stats = compute_reactivity_stats(raw, df)
    stats.update(schema_stats)
    stats["parking_violation_types_kept"] = sorted(PARKING_VIOLATIONS)
    stats["outlier_events_dropped"] = outlier_events
    stats["source_csv"] = str(raw_csv)

    output = PROCESSED_DIR / "parking_violations_clean.parquet"
    df.to_parquet(output, index=False)
    write_json(PROCESSED_DIR / "pipeline_stats.json", stats)

    note = REPORTS_DIR / "reactivity_stats.md"
    note.write_text(
        "\n".join(
            [
                "# Reactivity and Cleaning Stats",
                "",
                f"- Source CSV: `{raw_csv.name}`",
                f"- Raw records: {stats['raw_records']:,}",
                f"- Parking-only violation events after exploding labels: {stats['parking_violation_events']:,}",
                f"- Unique source records containing parking violations: {stats['parking_unique_records']:,}",
                f"- Unique lat/lon points rounded to 6 decimals: {stats['unique_locations_rounded_6dp']:,}",
                f"- Date range: {stats['start_datetime']} to {stats['end_datetime']}",
                f"- `closed_datetime` non-null rate: {stats['closed_datetime_non_null_pct']:.2f}%",
                f"- `action_taken_timestamp` non-null rate: {stats['action_taken_timestamp_non_null_pct']:.2f}%",
                f"- `validation_timestamp` non-null rate: {stats['validation_timestamp_non_null_pct']:.2f}%",
                f"- Median validation lag: {stats['validation_lag_median_hours']:.2f} hours",
                f"- Mean validation lag: {stats['validation_lag_mean_hours']:.2f} hours",
                f"- `No Junction` share in raw data: {stats['no_junction_pct']:.2f}%",
                f"- Out-of-bounds parking events dropped: {stats['outlier_events_dropped']:,}",
                "",
                "Pitch sentence: "
                f"We have {stats['parking_violation_events']:,} parking violation events "
                f"across {stats['unique_locations_rounded_6dp']:,} unique GPS points, "
                f"spanning {stats['start_datetime']} to {stats['end_datetime']}, "
                f"with a current formal closure/action-tracking rate of "
                f"{max(stats['closed_datetime_non_null_pct'], stats['action_taken_timestamp_non_null_pct']):.2f}%.",
            ]
        ),
        encoding="utf-8",
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=None)
    args = parser.parse_args()
    stats = clean(args.csv)
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
