from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from src.optimization import patrol_optimizer
from src.utils import haversine_km


@given(units=st.integers(min_value=1, max_value=5), top_k=st.integers(min_value=1, max_value=30))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_start_point_row_invariant(temp_processed_dir, units: int, top_k: int) -> None:
    # Feature: patrol-route-visualization, Property 1: Start-point row invariant
    assume(top_k >= units)

    patrol_optimizer.optimize_patrol_routes(top_k=top_k, units=units)
    route_points = pd.read_parquet(temp_processed_dir / "patrol_route_points.parquet")
    start_rows = route_points.loc[route_points["stop_order"] == 0]

    assert len(start_rows) == units
    assert start_rows["route_id"].nunique() == units
    assert (start_rows["cluster_id"] == -1).all()
    assert (start_rows["nc_cis"] == 0.0).all()
    assert len(route_points) == top_k + units


@given(units=st.integers(min_value=1, max_value=5), top_k=st.integers(min_value=1, max_value=30))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_segment_ordering_and_sentinel(temp_processed_dir, units: int, top_k: int) -> None:
    # Feature: patrol-route-visualization, Property 2: Segment ordering and sentinel
    assume(top_k >= units)

    patrol_optimizer.optimize_patrol_routes(top_k=top_k, units=units)
    segments = pd.read_parquet(temp_processed_dir / "patrol_route_segments.parquet")

    for _, group in segments.groupby("route_id"):
        orders = group.sort_values("segment_order")["segment_order"].tolist()
        assert orders == list(range(1, len(group) + 1))
        first = group.loc[group["segment_order"] == 1].iloc[0]
        assert first["from_cluster_id"] == -1


@given(units=st.integers(min_value=1, max_value=5), top_k=st.integers(min_value=1, max_value=30))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_segment_distance_correctness(temp_processed_dir, units: int, top_k: int) -> None:
    # Feature: patrol-route-visualization, Property 3: Segment distance correctness
    assume(top_k >= units)

    patrol_optimizer.optimize_patrol_routes(top_k=top_k, units=units)
    segments = pd.read_parquet(temp_processed_dir / "patrol_route_segments.parquet")

    for _, row in segments.iterrows():
        expected = haversine_km(row["from_lat"], row["from_lon"], row["to_lat"], row["to_lon"])
        assert row["distance_km"] == pytest.approx(expected, abs=1e-9)


@given(units=st.integers(min_value=1, max_value=5), top_k=st.integers(min_value=1, max_value=30))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_segment_count_equals_top_k(temp_processed_dir, units: int, top_k: int) -> None:
    # Feature: patrol-route-visualization, Property 4: Segment count equals top_k
    assume(top_k >= units)

    patrol_optimizer.optimize_patrol_routes(top_k=top_k, units=units)
    segments = pd.read_parquet(temp_processed_dir / "patrol_route_segments.parquet")

    assert len(segments) == top_k


@given(units=st.integers(min_value=1, max_value=5), top_k=st.integers(min_value=1, max_value=30))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_segment_output_is_idempotent(temp_processed_dir, units: int, top_k: int) -> None:
    # Feature: patrol-route-visualization, Property 5: Idempotent output (overwrite)
    assume(top_k >= units)

    patrol_optimizer.optimize_patrol_routes(top_k=top_k, units=units)
    first = pd.read_parquet(temp_processed_dir / "patrol_route_segments.parquet")
    patrol_optimizer.optimize_patrol_routes(top_k=top_k, units=units)
    second = pd.read_parquet(temp_processed_dir / "patrol_route_segments.parquet")

    pd.testing.assert_frame_equal(first, second)


@given(units=st.integers(min_value=1, max_value=8), top_k=st.integers(min_value=1, max_value=30))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_round_robin_balance(temp_processed_dir, units: int, top_k: int) -> None:
    # Feature: patrol-route-visualization, Property 6: Round-robin balance
    patrol_optimizer.optimize_patrol_routes(top_k=top_k, units=units)
    routes = pd.read_parquet(temp_processed_dir / "patrol_routes.parquet")
    expected_counts = {top_k // units, top_k // units + 1}

    assert set(routes["hotspot_count"].tolist()).issubset(expected_counts)


def test_descriptive_exception_identifies_failing_route(temp_processed_dir, ranked_hotspots) -> None:
    # Feature: patrol-route-visualization, Property 11: Descriptive exception identifies failing route
    broken = ranked_hotspots.copy()
    broken.loc[1, "centroid_lat"] = float("nan")
    broken.to_parquet(temp_processed_dir / "ranked_hotspots.parquet", index=False)

    with pytest.raises(RuntimeError, match="route_id=2"):
        patrol_optimizer.optimize_patrol_routes(top_k=6, units=3)


def test_existing_output_schema_is_preserved(temp_processed_dir) -> None:
    patrol_optimizer.optimize_patrol_routes(top_k=6, units=2)

    routes = pd.read_parquet(temp_processed_dir / "patrol_routes.parquet")
    route_points = pd.read_parquet(temp_processed_dir / "patrol_route_points.parquet")

    assert {
        "route_id",
        "hotspot_count",
        "coverage_score",
        "distance_km",
        "hotspot_sequence",
    }.issubset(routes.columns)
    assert {
        "route_id",
        "stop_order",
        "cluster_id",
        "centroid_lat",
        "centroid_lon",
        "nc_cis",
    }.issubset(route_points.columns)


def test_segments_column_schema(temp_processed_dir) -> None:
    patrol_optimizer.optimize_patrol_routes(top_k=6, units=2)
    segments = pd.read_parquet(temp_processed_dir / "patrol_route_segments.parquet")

    assert {
        "route_id",
        "segment_order",
        "from_cluster_id",
        "to_cluster_id",
        "from_lat",
        "from_lon",
        "to_lat",
        "to_lon",
        "distance_km",
    }.issubset(segments.columns)


def test_pipeline_outputs_are_written(temp_processed_dir) -> None:
    patrol_optimizer.optimize_patrol_routes(top_k=6, units=2)

    route_points_path = temp_processed_dir / "patrol_route_points.parquet"
    segments_path = temp_processed_dir / "patrol_route_segments.parquet"
    routes_path = temp_processed_dir / "patrol_routes.parquet"

    assert route_points_path.exists()
    assert segments_path.exists()
    assert routes_path.exists()

    route_points = pd.read_parquet(route_points_path)
    segments = pd.read_parquet(segments_path)
    routes = pd.read_parquet(routes_path)

    assert route_points.loc[route_points["stop_order"] == 0, "route_id"].nunique() == 2
    assert len(segments) == 6
    assert {
        "route_id",
        "segment_order",
        "from_cluster_id",
        "to_cluster_id",
        "from_lat",
        "from_lon",
        "to_lat",
        "to_lon",
        "distance_km",
    }.issubset(segments.columns)
    assert {
        "route_id",
        "hotspot_count",
        "coverage_score",
        "distance_km",
        "hotspot_sequence",
    }.issubset(routes.columns)
