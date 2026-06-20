from __future__ import annotations

import json

import pandas as pd
import plotly.express as px

from src.config import FIGURES_DIR, GRID_SIZE_DEGREES, PROCESSED_DIR, REPORTS_DIR, ensure_dirs
from src.utils import write_json


def add_time_fields(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    created = pd.to_datetime(df["created_datetime"], errors="coerce", utc=True)
    df["date"] = created.dt.date
    df["hour"] = created.dt.hour
    df["day_of_week"] = created.dt.day_name()
    df["is_daytime_9_18"] = df["hour"].between(9, 17)
    df["is_overnight_0_7"] = df["hour"].between(0, 7)
    df["is_evening_19_23"] = df["hour"].between(19, 23)
    return df


def build_features() -> dict:
    ensure_dirs()
    source = PROCESSED_DIR / "parking_violations_clean.parquet"
    df = pd.read_parquet(source)
    df = add_time_fields(df)

    df["grid_lat"] = (df["latitude"] / GRID_SIZE_DEGREES).round() * GRID_SIZE_DEGREES
    df["grid_lon"] = (df["longitude"] / GRID_SIZE_DEGREES).round() * GRID_SIZE_DEGREES

    grouped = df.groupby(["grid_lat", "grid_lon"], dropna=False)
    location_features = grouped.agg(
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean"),
        violation_count=("violation", "size"),
        unique_records=("id", "nunique"),
        distinct_days=("date", "nunique"),
        unique_vehicles=("vehicle_number", "nunique"),
        police_station_count=("police_station", "nunique"),
        no_junction_share=("junction_name", lambda s: float((s.fillna("") == "No Junction").mean())),
        daytime_count=("is_daytime_9_18", "sum"),
        overnight_count=("is_overnight_0_7", "sum"),
        evening_count=("is_evening_19_23", "sum"),
    ).reset_index()

    dominant_violation = (
        df.groupby(["grid_lat", "grid_lon", "violation"]).size().rename("count").reset_index()
        .sort_values(["grid_lat", "grid_lon", "count"], ascending=[True, True, False])
        .drop_duplicates(["grid_lat", "grid_lon"])
        [["grid_lat", "grid_lon", "violation"]]
        .rename(columns={"violation": "dominant_violation"})
    )
    peak_hour = (
        df.groupby(["grid_lat", "grid_lon", "hour"]).size().rename("count").reset_index()
        .sort_values(["grid_lat", "grid_lon", "count"], ascending=[True, True, False])
        .drop_duplicates(["grid_lat", "grid_lon"])
        [["grid_lat", "grid_lon", "hour"]]
        .rename(columns={"hour": "peak_hour"})
    )
    location_features = location_features.merge(
        dominant_violation, on=["grid_lat", "grid_lon"], how="left"
    ).merge(peak_hour, on=["grid_lat", "grid_lon"], how="left")

    vehicles = (
        df.drop_duplicates(["vehicle_number", "id"])
        .dropna(subset=["vehicle_number"])
        .groupby("vehicle_number")
        .agg(
            violation_records=("id", "nunique"),
            first_seen=("created_datetime", "min"),
            last_seen=("created_datetime", "max"),
            vehicle_types=("vehicle_type", lambda s: ", ".join(sorted(set(map(str, s.dropna())))[:3])),
        )
        .reset_index()
        .sort_values("violation_records", ascending=False)
    )
    vehicles["is_chronic_5_plus"] = vehicles["violation_records"] >= 5

    hour_counts = df.groupby("hour").size().rename("violation_events").reset_index()
    dow_counts = df.groupby("day_of_week").size().rename("violation_events").reset_index()

    location_features.to_parquet(PROCESSED_DIR / "location_features.parquet", index=False)
    vehicles.to_parquet(PROCESSED_DIR / "repeat_offenders.parquet", index=False)
    hour_counts.to_csv(PROCESSED_DIR / "hour_of_day_counts.csv", index=False)
    dow_counts.to_csv(PROCESSED_DIR / "day_of_week_counts.csv", index=False)

    fig = px.bar(
        hour_counts,
        x="hour",
        y="violation_events",
        title="Parking violation enforcement is concentrated outside commercial daytime hours",
    )
    fig.write_html(FIGURES_DIR / "hour_of_day_blind_spot.html")

    stats = {
        "location_feature_rows": int(len(location_features)),
        "repeat_offender_rows": int(len(vehicles)),
        "chronic_offenders_5_plus": int(vehicles["is_chronic_5_plus"].sum()),
        "max_vehicle_records": int(vehicles["violation_records"].max()),
        "daytime_9_18_share_pct": float(df["is_daytime_9_18"].mean() * 100),
        "overnight_0_7_share_pct": float(df["is_overnight_0_7"].mean() * 100),
        "evening_19_23_share_pct": float(df["is_evening_19_23"].mean() * 100),
    }
    write_json(PROCESSED_DIR / "feature_stats.json", stats)
    (REPORTS_DIR / "feature_findings.md").write_text(
        "\n".join(
            [
                "# Feature Findings",
                "",
                f"- Location grid cells: {stats['location_feature_rows']:,}",
                f"- Vehicles with 5+ recorded parking violations: {stats['chronic_offenders_5_plus']:,}",
                f"- Highest repeat-offender record count: {stats['max_vehicle_records']:,}",
                f"- Daytime (09:00-17:59) enforcement share: {stats['daytime_9_18_share_pct']:.2f}%",
                f"- Overnight (00:00-07:59) enforcement share: {stats['overnight_0_7_share_pct']:.2f}%",
                f"- Evening (19:00-23:59) enforcement share: {stats['evening_19_23_share_pct']:.2f}%",
                "",
                "Interpretation: the timestamp distribution is an enforcement-visibility blind spot, "
                "not proof that daytime illegal parking is absent.",
            ]
        ),
        encoding="utf-8",
    )
    return stats


def main() -> None:
    print(json.dumps(build_features(), indent=2))


if __name__ == "__main__":
    main()
