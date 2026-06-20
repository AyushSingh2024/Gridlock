from __future__ import annotations

import json

import folium
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score

from src.config import FIGURES_DIR, PROCESSED_DIR, ensure_dirs
from src.utils import write_json


def detect_hotspots(eps_km: float = 0.12, min_samples: int = 3) -> dict:
    ensure_dirs()
    features = pd.read_parquet(PROCESSED_DIR / "location_features.parquet")
    coords_rad = np.radians(features[["latitude", "longitude"]].to_numpy())
    kms_per_radian = 6371.0088

    clusterer_name = "DBSCAN_haversine_grid_fallback"
    try:
        import hdbscan  # type: ignore

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=max(min_samples, 5),
            min_samples=min_samples,
            metric="haversine",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(coords_rad)
        clusterer_name = "HDBSCAN_haversine"
    except Exception:
        clusterer = DBSCAN(
            eps=eps_km / kms_per_radian,
            min_samples=min_samples,
            metric="haversine",
            algorithm="ball_tree",
        )
        labels = clusterer.fit_predict(coords_rad)

    features = features.copy()
    features["cluster_id"] = labels
    clustered = features[features["cluster_id"] >= 0].copy()

    if clustered.empty:
        raise RuntimeError("No hotspot clusters found. Lower min_samples or increase eps_km.")

    hotspots = (
        clustered.groupby("cluster_id")
        .agg(
            centroid_lat=("latitude", "mean"),
            centroid_lon=("longitude", "mean"),
            point_count=("violation_count", "sum"),
            grid_cell_count=("cluster_id", "size"),
            unique_records=("unique_records", "sum"),
            distinct_days=("distinct_days", "max"),
            unique_vehicles=("unique_vehicles", "sum"),
            daytime_count=("daytime_count", "sum"),
            overnight_count=("overnight_count", "sum"),
            evening_count=("evening_count", "sum"),
            no_junction_share=("no_junction_share", "mean"),
            min_lat=("latitude", "min"),
            max_lat=("latitude", "max"),
            min_lon=("longitude", "min"),
            max_lon=("longitude", "max"),
        )
        .reset_index()
    )
    hotspots["spatial_extent_km"] = (
        ((hotspots["max_lat"] - hotspots["min_lat"]) * 111) ** 2
        + ((hotspots["max_lon"] - hotspots["min_lon"]) * 102) ** 2
    ) ** 0.5
    hotspots = hotspots.sort_values("point_count", ascending=False)
    hotspots.to_parquet(PROCESSED_DIR / "hotspots.parquet", index=False)
    features.to_parquet(PROCESSED_DIR / "location_features_clustered.parquet", index=False)

    labels_for_score = features["cluster_id"].to_numpy()
    non_noise = labels_for_score >= 0
    silhouette = None
    if non_noise.sum() > 10 and len(set(labels_for_score[non_noise])) > 1:
        sample = features.loc[non_noise, ["latitude", "longitude"]].to_numpy()
        if len(sample) > 5000:
            rng = np.random.default_rng(42)
            idx = rng.choice(len(sample), 5000, replace=False)
            sample_labels = labels_for_score[non_noise][idx]
            sample = sample[idx]
        else:
            sample_labels = labels_for_score[non_noise]
        silhouette = float(silhouette_score(sample, sample_labels))

    center = [float(hotspots["centroid_lat"].mean()), float(hotspots["centroid_lon"].mean())]
    fmap = folium.Map(location=center, zoom_start=11, tiles="cartodbpositron")
    for _, row in hotspots.head(200).iterrows():
        radius = max(4, min(22, np.sqrt(row["point_count"]) / 4))
        folium.CircleMarker(
            location=[row["centroid_lat"], row["centroid_lon"]],
            radius=radius,
            color="#d73027",
            fill=True,
            fill_opacity=0.65,
            popup=f"Cluster {int(row['cluster_id'])}: {int(row['point_count'])} events",
        ).add_to(fmap)
    fmap.save(FIGURES_DIR / "hotspots_static_map.html")

    stats = {
        "clusterer": clusterer_name,
        "eps_km": eps_km,
        "min_samples": min_samples,
        "input_grid_cells": int(len(features)),
        "clustered_grid_cells": int(non_noise.sum()),
        "noise_grid_cells": int((labels_for_score < 0).sum()),
        "hotspot_count": int(len(hotspots)),
        "silhouette_sample": silhouette,
    }
    write_json(PROCESSED_DIR / "clustering_stats.json", stats)
    return stats


def main() -> None:
    print(json.dumps(detect_hotspots(), indent=2))


if __name__ == "__main__":
    main()
