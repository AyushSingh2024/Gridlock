from __future__ import annotations

import json

import pandas as pd
import plotly.express as px

from src.config import DEFAULT_TOP_K, FIGURES_DIR, PROCESSED_DIR, ensure_dirs
from src.utils import haversine_km, route_distance_km, write_json


def greedy_route(points: pd.DataFrame, start: tuple[float, float]) -> list[int]:
    remaining = set(points.index.tolist())
    route: list[int] = []
    current = start
    while remaining:
        best = min(
            remaining,
            key=lambda idx: haversine_km(
                current[0],
                current[1],
                float(points.loc[idx, "centroid_lat"]),
                float(points.loc[idx, "centroid_lon"]),
            )
            / max(float(points.loc[idx, "nc_cis"]), 0.001),
        )
        route.append(best)
        current = (
            float(points.loc[best, "centroid_lat"]),
            float(points.loc[best, "centroid_lon"]),
        )
        remaining.remove(best)
    return route


def optimize_patrol_routes(top_k: int = DEFAULT_TOP_K, units: int = 3) -> dict:
    if units < 1:
        raise ValueError("units must be at least 1")

    ensure_dirs()
    all_hotspots = pd.read_parquet(PROCESSED_DIR / "ranked_hotspots.parquet")
    hotspots = all_hotspots.head(top_k).copy()
    city_center = (
        float(all_hotspots["centroid_lat"].mean()),
        float(all_hotspots["centroid_lon"].mean()),
    )

    assignments = [[] for _ in range(units)]
    for i, idx in enumerate(hotspots.index.tolist()):
        assignments[i % units].append(idx)

    rows = []
    route_points = []
    segments = []
    for unit_id, assigned in enumerate(assignments, start=1):
        assigned_df = hotspots.loc[assigned]
        ordered_idx = greedy_route(assigned_df, city_center)
        ordered = hotspots.loc[ordered_idx]
        all_stops = [
            {
                "cluster_id": -1,
                "centroid_lat": city_center[0],
                "centroid_lon": city_center[1],
            }
        ] + [
            {
                "cluster_id": int(row["cluster_id"]),
                "centroid_lat": float(row["centroid_lat"]),
                "centroid_lon": float(row["centroid_lon"]),
            }
            for _, row in ordered.iterrows()
        ]
        points = [
            (float(stop["centroid_lat"]), float(stop["centroid_lon"]))
            for stop in all_stops
        ]
        coverage = float(ordered["nc_cis"].sum())
        distance = route_distance_km(points)
        rows.append(
            {
                "route_id": unit_id,
                "hotspot_count": int(len(ordered)),
                "coverage_score": coverage,
                "distance_km": distance,
                "shift_recommendation": "09:00-18:00 added daytime patrol",
                "hotspot_sequence": " -> ".join(ordered["cluster_id"].astype(str).tolist()),
            }
        )
        route_points.append(
            {
                "route_id": unit_id,
                "stop_order": 0,
                "cluster_id": -1,
                "centroid_lat": city_center[0],
                "centroid_lon": city_center[1],
                "nc_cis": 0.0,
            }
        )
        for stop_order, (_, row) in enumerate(ordered.iterrows(), start=1):
            route_points.append(
                {
                    "route_id": unit_id,
                    "stop_order": stop_order,
                    "cluster_id": int(row["cluster_id"]),
                    "centroid_lat": float(row["centroid_lat"]),
                    "centroid_lon": float(row["centroid_lon"]),
                    "nc_cis": float(row["nc_cis"]),
                }
            )
        try:
            for segment_order, (start_stop, end_stop) in enumerate(
                zip(all_stops[:-1], all_stops[1:]), start=1
            ):
                coords = [
                    start_stop["centroid_lat"],
                    start_stop["centroid_lon"],
                    end_stop["centroid_lat"],
                    end_stop["centroid_lon"],
                ]
                if any(pd.isna(coord) for coord in coords):
                    raise ValueError("segment coordinate contains NaN")
                segments.append(
                    {
                        "route_id": unit_id,
                        "segment_order": segment_order,
                        "from_cluster_id": int(start_stop["cluster_id"]),
                        "to_cluster_id": int(end_stop["cluster_id"]),
                        "from_lat": float(start_stop["centroid_lat"]),
                        "from_lon": float(start_stop["centroid_lon"]),
                        "to_lat": float(end_stop["centroid_lat"]),
                        "to_lon": float(end_stop["centroid_lon"]),
                        "distance_km": haversine_km(
                            start_stop["centroid_lat"],
                            start_stop["centroid_lon"],
                            end_stop["centroid_lat"],
                            end_stop["centroid_lon"],
                        ),
                    }
                )
        except Exception as exc:
            raise RuntimeError(f"Segment computation failed for route_id={unit_id}: {exc}") from exc

    routes = pd.DataFrame(rows)
    route_points_df = pd.DataFrame(route_points)
    segments_df = pd.DataFrame(
        segments,
        columns=[
            "route_id",
            "segment_order",
            "from_cluster_id",
            "to_cluster_id",
            "from_lat",
            "from_lon",
            "to_lat",
            "to_lon",
            "distance_km",
        ],
    )

    naive = all_hotspots.sort_values("point_count", ascending=False).head(top_k)
    optimized_coverage = float(routes["coverage_score"].sum())
    naive_coverage = float(naive["nc_cis"].sum())
    improvement_pct = (
        ((optimized_coverage - naive_coverage) / naive_coverage) * 100 if naive_coverage else 0.0
    )

    routes.to_parquet(PROCESSED_DIR / "patrol_routes.parquet", index=False)
    route_points_df.to_parquet(PROCESSED_DIR / "patrol_route_points.parquet", index=False)
    segments_df.to_parquet(PROCESSED_DIR / "patrol_route_segments.parquet", index=False)

    fig = px.scatter_map(
        route_points_df,
        lat="centroid_lat",
        lon="centroid_lon",
        color="route_id",
        size="nc_cis",
        hover_data=["cluster_id", "stop_order", "nc_cis"],
        zoom=10,
        height=720,
        title="NC-CIS optimized patrol route stops",
    )
    fig.write_html(FIGURES_DIR / "patrol_routes.html")

    stats = {
        "top_k": top_k,
        "units": units,
        "optimized_coverage_score": optimized_coverage,
        "naive_top_density_coverage_score": naive_coverage,
        "simulated_coverage_improvement_pct": improvement_pct,
        "daytime_reallocation": (
            "Recommend moving added coverage into 09:00-18:00 at the top NC-CIS hotspots; "
            "this is based on the observed daytime enforcement blind spot."
        ),
    }
    write_json(PROCESSED_DIR / "optimization_stats.json", stats)
    return stats


def main() -> None:
    print(json.dumps(optimize_patrol_routes(), indent=2))


if __name__ == "__main__":
    main()
