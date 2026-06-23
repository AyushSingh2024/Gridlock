from __future__ import annotations

import json
import warnings
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
ROUTE_COLOR = "#006DFF"
ROUTE_WEIGHT = 5
OPACITY = {1: 0.9, 2: 0.75, 3: 0.6}


def make_route_map(
    route_points: pd.DataFrame,
    route_segments: pd.DataFrame,
    *,
    selected_vehicle,
) -> str:
    stop_points = route_points.loc[route_points["stop_order"] > 0].dropna(
        subset=["centroid_lat", "centroid_lon"]
    )
    if stop_points.empty:
        center = [12.9716, 77.5946]
    else:
        center = [
            float(stop_points["centroid_lat"].mean()),
            float(stop_points["centroid_lon"].mean()),
        ]

    m = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")

    filtered_points = route_points.copy()
    filtered_segments = route_segments.copy()
    if selected_vehicle != "All":
        filtered_points = filtered_points.loc[filtered_points["route_id"] == selected_vehicle]
        filtered_segments = filtered_segments.loc[
            filtered_segments["route_id"] == selected_vehicle
        ]

    if filtered_segments.empty:
        warnings.warn("route_segments is empty - polylines skipped", stacklevel=2)
    else:
        for route_id in sorted(filtered_segments["route_id"].dropna().unique()):
            route_segment_rows = filtered_segments.loc[
                filtered_segments["route_id"] == route_id
            ].sort_values("segment_order")
            first = route_segment_rows.iloc[0]
            coords = [(float(first["from_lat"]), float(first["from_lon"]))]
            coords.extend(
                (float(row["to_lat"]), float(row["to_lon"]))
                for _, row in route_segment_rows.iterrows()
            )
            folium.PolyLine(
                locations=coords,
                color=ROUTE_COLOR,
                weight=ROUTE_WEIGHT,
                opacity=OPACITY.get(int(route_id), 0.6),
            ).add_to(m)

    marker_rows = filtered_points.loc[filtered_points["stop_order"] > 0].dropna(
        subset=["centroid_lat", "centroid_lon"]
    )
    for _, row in marker_rows.iterrows():
        route_id = int(row["route_id"])
        stop_order = int(row["stop_order"])
        cluster_id = int(row["cluster_id"])
        nc_cis = float(row["nc_cis"])
        popup_html = (
            f"route_id: {route_id}<br>"
            f"stop_order: {stop_order}<br>"
            f"cluster_id: {cluster_id}<br>"
            f"nc_cis: {nc_cis}"
        )
        folium.Marker(
            location=[float(row["centroid_lat"]), float(row["centroid_lon"])],
            tooltip=f"Patrol Vehicle {route_id}, Stop {stop_order}",
            popup=folium.Popup(popup_html, max_width=260),
            icon=folium.DivIcon(
                html=(
                    '<div style="background:#006DFF;color:white;border:2px solid white;'
                    'border-radius:50%;width:28px;height:28px;line-height:24px;'
                    'text-align:center;font-weight:700;box-shadow:0 1px 4px #555;">'
                    f"{stop_order}</div>"
                )
            ),
        ).add_to(m)

    return m.get_root().render()


@st.cache_data
def load_outputs():
    ranked = pd.read_parquet(PROCESSED / "ranked_hotspots.parquet")
    routes = pd.read_parquet(PROCESSED / "patrol_routes.parquet")
    route_points = pd.read_parquet(PROCESSED / "patrol_route_points.parquet")
    route_segments = pd.read_parquet(PROCESSED / "patrol_route_segments.parquet")
    offenders = pd.read_parquet(PROCESSED / "repeat_offenders.parquet")
    hour_counts = pd.read_csv(PROCESSED / "hour_of_day_counts.csv")
    with open(PROCESSED / "pipeline_stats.json", encoding="utf-8") as handle:
        pipeline_stats = json.load(handle)
    with open(PROCESSED / "feature_stats.json", encoding="utf-8") as handle:
        feature_stats = json.load(handle)
    with open(PROCESSED / "optimization_stats.json", encoding="utf-8") as handle:
        optimization_stats = json.load(handle)
    return (
        ranked,
        routes,
        route_points,
        route_segments,
        offenders,
        hour_counts,
        pipeline_stats,
        feature_stats,
        optimization_stats,
    )


def main() -> None:
    st.set_page_config(page_title="Gridlock Parking Intelligence", layout="wide")
    st.title("Parking Congestion Intelligence")
    st.caption("NC-CIS ranks illegal-parking hotspots by density, recurrence, capacity-loss proxy, and network centrality.")

    (
        ranked,
        routes,
        route_points,
        route_segments,
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
            ]
            .head(30),
            use_container_width=True,
            hide_index=True,
        )

    with tab_routes:
        cols = st.columns(3)
        cols[0].metric("Patrol units", optimization_stats["units"])
        cols[1].metric("Top hotspots routed", optimization_stats["top_k"])
        cols[2].metric("Simulated gain vs density baseline", f"{optimization_stats['simulated_coverage_improvement_pct']:.1f}%")
        vehicle_options = ["All"] + [
            f"Vehicle {int(route_id)}" for route_id in sorted(route_points["route_id"].dropna().unique())
        ]
        vehicle_choice = st.selectbox("Select patrol vehicle", vehicle_options, index=0)
        selected_vehicle = "All" if vehicle_choice == "All" else int(vehicle_choice.split()[-1])
        components.html(
            make_route_map(
                route_points,
                route_segments,
                selected_vehicle=selected_vehicle,
            ),
            height=560,
        )
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


if __name__ == "__main__":
    main()
