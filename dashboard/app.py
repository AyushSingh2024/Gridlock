from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


@st.cache_data
def load_outputs():
    ranked = pd.read_parquet(PROCESSED / "ranked_hotspots.parquet")
    routes = pd.read_parquet(PROCESSED / "patrol_routes.parquet")
    route_points = pd.read_parquet(PROCESSED / "patrol_route_points.parquet")
    offenders = pd.read_parquet(PROCESSED / "repeat_offenders.parquet")
    hour_counts = pd.read_csv(PROCESSED / "hour_of_day_counts.csv")
    with open(PROCESSED / "pipeline_stats.json", encoding="utf-8") as handle:
        pipeline_stats = json.load(handle)
    with open(PROCESSED / "feature_stats.json", encoding="utf-8") as handle:
        feature_stats = json.load(handle)
    with open(PROCESSED / "optimization_stats.json", encoding="utf-8") as handle:
        optimization_stats = json.load(handle)
    return ranked, routes, route_points, offenders, hour_counts, pipeline_stats, feature_stats, optimization_stats


st.set_page_config(page_title="Gridlock Parking Intelligence", layout="wide")
st.title("Parking Congestion Intelligence")
st.caption("NC-CIS ranks illegal-parking hotspots by density, recurrence, capacity-loss proxy, and network centrality.")

(
    ranked,
    routes,
    route_points,
    offenders,
    hour_counts,
    pipeline_stats,
    feature_stats,
    optimization_stats,
) = load_outputs()

metric_cols = st.columns(4)
metric_cols[0].metric("Parking events", f"{pipeline_stats['parking_violation_events']:,}")
metric_cols[1].metric("Closure/action rate", f"{max(pipeline_stats['closed_datetime_non_null_pct'], pipeline_stats['action_taken_timestamp_non_null_pct']):.2f}%")
metric_cols[2].metric("Median validation lag", f"{pipeline_stats['validation_lag_median_hours']:.1f}h")
metric_cols[3].metric("Chronic vehicles", f"{feature_stats['chronic_offenders_5_plus']:,}")

tab_map, tab_routes, tab_temporal, tab_offenders = st.tabs(
    ["NC-CIS Map", "Patrol Routes", "Temporal Blind Spot", "Repeat Offenders"]
)

with tab_map:
    selected = st.selectbox(
        "What-if: remove hotspot from enforcement burden",
        ["None"] + ranked["cluster_id"].astype(str).head(50).tolist(),
    )
    view = ranked.copy()
    if selected != "None":
        removed = view["cluster_id"].astype(str) == selected
        removed_score = float(view.loc[removed, "nc_cis"].sum())
        view = view.loc[~removed].copy()
        st.info(f"Simulated removal of hotspot {selected}: {removed_score:.3f} NC-CIS burden removed from the ranked list.")

    fig = px.scatter_map(
        view.head(250),
        lat="centroid_lat",
        lon="centroid_lon",
        size="point_count",
        color="nc_cis",
        hover_data=["rank", "cluster_id", "point_count", "distinct_days", "betweenness_centrality"],
        zoom=10,
        height=620,
        color_continuous_scale="Turbo",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        view[
            [
                "rank",
                "cluster_id",
                "nc_cis",
                "point_count",
                "betweenness_centrality",
                "capacity_loss_proxy",
                "distinct_days",
                "no_junction_share",
            ]
        ].head(30),
        use_container_width=True,
        hide_index=True,
    )

with tab_routes:
    cols = st.columns(3)
    cols[0].metric("Patrol units", optimization_stats["units"])
    cols[1].metric("Top hotspots routed", optimization_stats["top_k"])
    cols[2].metric("Simulated gain vs density baseline", f"{optimization_stats['simulated_coverage_improvement_pct']:.1f}%")
    route_fig = px.scatter_map(
        route_points,
        lat="centroid_lat",
        lon="centroid_lon",
        color="route_id",
        size="nc_cis",
        hover_data=["stop_order", "cluster_id", "nc_cis"],
        zoom=10,
        height=560,
    )
    st.plotly_chart(route_fig, use_container_width=True)
    st.dataframe(routes, use_container_width=True, hide_index=True)

with tab_temporal:
    temporal_fig = px.bar(
        hour_counts,
        x="hour",
        y="violation_events",
        title="Observed enforcement timestamps by hour",
    )
    st.plotly_chart(temporal_fig, use_container_width=True)
    cols = st.columns(3)
    cols[0].metric("Daytime 09-17 share", f"{feature_stats['daytime_9_18_share_pct']:.2f}%")
    cols[1].metric("Overnight 00-07 share", f"{feature_stats['overnight_0_7_share_pct']:.2f}%")
    cols[2].metric("Evening 19-23 share", f"{feature_stats['evening_19_23_share_pct']:.2f}%")
    st.warning("Treat low daytime volume as an enforcement visibility gap, not as evidence that daytime illegal parking does not exist.")

with tab_offenders:
    st.dataframe(
        offenders.head(100),
        use_container_width=True,
        hide_index=True,
    )
