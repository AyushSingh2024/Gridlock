from __future__ import annotations

import json
import pickle

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.neighbors import NearestNeighbors

from src.config import FIGURES_DIR, PROCESSED_DIR, ensure_dirs
from src.utils import normalize, write_json


def build_hotspot_graph(hotspots: pd.DataFrame, neighbors: int = 4) -> nx.Graph:
    graph = nx.Graph()
    for _, row in hotspots.iterrows():
        node = int(row["cluster_id"])
        graph.add_node(
            node,
            lat=float(row["centroid_lat"]),
            lon=float(row["centroid_lon"]),
            weight=float(row["point_count"]),
        )

    coords = hotspots[["centroid_lat", "centroid_lon"]].to_numpy()
    n_neighbors = min(max(neighbors + 1, 2), len(hotspots))
    nbrs = NearestNeighbors(n_neighbors=n_neighbors, metric="haversine")
    nbrs.fit(np.radians(coords))
    distances, indices = nbrs.kneighbors(np.radians(coords))
    for source_pos, (dist_row, idx_row) in enumerate(zip(distances, indices)):
        source = int(hotspots.iloc[source_pos]["cluster_id"])
        for dist, target_pos in zip(dist_row[1:], idx_row[1:]):
            target = int(hotspots.iloc[target_pos]["cluster_id"])
            graph.add_edge(source, target, distance_km=float(dist * 6371.0088))
    return graph


def score_hotspots() -> dict:
    ensure_dirs()
    hotspots = pd.read_parquet(PROCESSED_DIR / "hotspots.parquet").copy()
    graph = build_hotspot_graph(hotspots)
    node_betweenness = nx.betweenness_centrality(graph, weight="distance_km", normalized=True)
    hotspots["betweenness_centrality"] = hotspots["cluster_id"].map(node_betweenness).fillna(0.0)

    # Simple carriageway loss proxy: more events and mid-block/no-junction share imply more lane friction.
    assumed_vehicle_width_m = 2.0
    assumed_lane_width_m = 3.5
    assumed_lanes = np.where(hotspots["point_count"] >= hotspots["point_count"].median(), 2, 1)
    road_width_m = assumed_lane_width_m * assumed_lanes
    daily_illegal_parking_pressure = hotspots["point_count"] / hotspots["distinct_days"].clip(lower=1)
    hotspots["capacity_loss_proxy"] = (
        assumed_vehicle_width_m * daily_illegal_parking_pressure / road_width_m
    ) * (1 + hotspots["no_junction_share"].fillna(0))

    hotspots["density_norm"] = normalize(hotspots["point_count"])
    hotspots["capacity_loss_norm"] = normalize(hotspots["capacity_loss_proxy"])
    hotspots["centrality_norm"] = normalize(hotspots["betweenness_centrality"])
    hotspots["recurrence_norm"] = normalize(hotspots["distinct_days"])

    weights = {
        "density_norm": 0.25,
        "capacity_loss_norm": 0.20,
        "centrality_norm": 0.35,
        "recurrence_norm": 0.20,
    }
    hotspots["nc_cis"] = sum(hotspots[col] * weight for col, weight in weights.items())
    hotspots["rank"] = hotspots["nc_cis"].rank(ascending=False, method="first").astype(int)
    hotspots = hotspots.sort_values("nc_cis", ascending=False)
    hotspots.to_parquet(PROCESSED_DIR / "ranked_hotspots.parquet", index=False)
    with open(PROCESSED_DIR / "hotspot_graph.gpickle", "wb") as handle:
        pickle.dump(graph, handle, protocol=pickle.HIGHEST_PROTOCOL)

    fig = px.scatter_map(
        hotspots.head(100),
        lat="centroid_lat",
        lon="centroid_lon",
        size="point_count",
        color="nc_cis",
        hover_name="cluster_id",
        hover_data=["rank", "point_count", "betweenness_centrality", "distinct_days"],
        zoom=10,
        height=720,
        title="Top hotspots by Network-Centrality-Weighted Congestion Impact Score",
    )
    fig.write_html(FIGURES_DIR / "nc_cis_hotspots.html")

    stats = {
        "ranked_hotspots": int(len(hotspots)),
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "weights": weights,
        "graph_mode": "offline_hotspot_knn_graph",
        "top_hotspot": hotspots.head(1).to_dict(orient="records")[0],
    }
    write_json(PROCESSED_DIR / "scoring_stats.json", stats)
    return stats


def main() -> None:
    print(json.dumps(score_hotspots(), indent=2, default=str))


if __name__ == "__main__":
    main()
