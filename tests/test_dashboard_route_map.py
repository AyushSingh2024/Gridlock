from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dashboard.app import make_route_map


def route_frames(route_count: int = 3, stops_per_route: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    points = []
    segments = []
    for route_id in range(1, route_count + 1):
        start_lat = 12.9716
        start_lon = 77.5946
        points.append(
            {
                "route_id": route_id,
                "stop_order": 0,
                "cluster_id": -1,
                "centroid_lat": start_lat,
                "centroid_lon": start_lon,
                "nc_cis": 0.0,
            }
        )
        prev_cluster = -1
        prev_lat = start_lat
        prev_lon = start_lon
        for stop_order in range(1, stops_per_route + 1):
            cluster_id = route_id * 100 + stop_order
            lat = 12.90 + route_id * 0.01 + stop_order * 0.001
            lon = 77.50 + route_id * 0.01 + stop_order * 0.001
            points.append(
                {
                    "route_id": route_id,
                    "stop_order": stop_order,
                    "cluster_id": cluster_id,
                    "centroid_lat": lat,
                    "centroid_lon": lon,
                    "nc_cis": float(route_id) + stop_order / 10,
                }
            )
            segments.append(
                {
                    "route_id": route_id,
                    "segment_order": stop_order,
                    "from_cluster_id": prev_cluster,
                    "to_cluster_id": cluster_id,
                    "from_lat": prev_lat,
                    "from_lon": prev_lon,
                    "to_lat": lat,
                    "to_lon": lon,
                    "distance_km": float(stop_order),
                }
            )
            prev_cluster = cluster_id
            prev_lat = lat
            prev_lon = lon
    return pd.DataFrame(points), pd.DataFrame(segments)


def empty_route_points() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "route_id",
            "stop_order",
            "cluster_id",
            "centroid_lat",
            "centroid_lon",
            "nc_cis",
        ]
    )


def empty_route_segments() -> pd.DataFrame:
    return pd.DataFrame(
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
        ]
    )


@given(route_count=st.integers(min_value=1, max_value=3))
@settings(max_examples=100, deadline=None)
def test_polyline_count_matches_route_count(route_count: int) -> None:
    # Feature: patrol-route-visualization, Property 7: Route map polyline count matches route count
    points, segments = route_frames(route_count=route_count)
    html = make_route_map(points, segments, selected_vehicle="All")

    assert html.count("L.polyline(") == route_count


@given(route_count=st.integers(min_value=2, max_value=3))
@settings(max_examples=100, deadline=None)
def test_vehicle_filter_isolates_single_route(route_count: int) -> None:
    # Feature: patrol-route-visualization, Property 8: Vehicle filter isolates single route
    points, segments = route_frames(route_count=route_count)

    for selected_vehicle in range(1, route_count + 1):
        html = make_route_map(points, segments, selected_vehicle=selected_vehicle)
        assert html.count("L.polyline(") == 1
        assert f"Patrol Vehicle {selected_vehicle}" in html
        for other_vehicle in set(range(1, route_count + 1)) - {selected_vehicle}:
            assert f"Patrol Vehicle {other_vehicle}" not in html


@given(route_count=st.integers(min_value=1, max_value=3), stops_per_route=st.integers(min_value=1, max_value=4))
@settings(max_examples=100, deadline=None)
def test_marker_count_matches_non_start_stops(route_count: int, stops_per_route: int) -> None:
    # Feature: patrol-route-visualization, Property 9: Marker count matches non-start stops
    points, segments = route_frames(route_count=route_count, stops_per_route=stops_per_route)
    html = make_route_map(points, segments, selected_vehicle="All")

    assert html.count("L.marker(") == route_count * stops_per_route


@given(route_count=st.integers(min_value=1, max_value=3), stops_per_route=st.integers(min_value=1, max_value=3))
@settings(max_examples=100, deadline=None)
def test_marker_popups_contain_required_fields(route_count: int, stops_per_route: int) -> None:
    # Feature: patrol-route-visualization, Property 10: Marker popup fields
    points, segments = route_frames(route_count=route_count, stops_per_route=stops_per_route)
    html = make_route_map(points, segments, selected_vehicle="All")

    for _, row in points.loc[points["stop_order"] > 0].iterrows():
        assert f"route_id: {int(row['route_id'])}" in html
        assert f"stop_order: {int(row['stop_order'])}" in html
        assert f"cluster_id: {int(row['cluster_id'])}" in html
        assert f"nc_cis: {float(row['nc_cis'])}" in html


def test_route_map_returns_html_string() -> None:
    points, segments = route_frames(route_count=1, stops_per_route=1)
    html = make_route_map(points, segments, selected_vehicle="All")

    assert isinstance(html, str)
    assert "<html" in html


def test_route_map_uses_route_opacity_values() -> None:
    points, segments = route_frames(route_count=3, stops_per_route=1)
    html = make_route_map(points, segments, selected_vehicle="All")

    assert "0.9" in html
    assert "0.75" in html
    assert "0.6" in html


def test_route_map_empty_points_uses_bengaluru_fallback() -> None:
    with pytest.warns(UserWarning):
        html = make_route_map(
            empty_route_points(),
            empty_route_segments(),
            selected_vehicle="All",
        )

    assert "12.9716" in html


def test_route_map_empty_segments_skips_polylines() -> None:
    points, _ = route_frames(route_count=1, stops_per_route=1)

    with pytest.warns(UserWarning):
        html = make_route_map(points, empty_route_segments(), selected_vehicle="All")

    assert "<html" in html
    assert "L.polyline(" not in html
