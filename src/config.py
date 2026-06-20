from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

RAW_CSV_GLOB = "*police*violation*anonymized*.csv"

EXPECTED_COLUMNS = [
    "id",
    "latitude",
    "longitude",
    "location",
    "vehicle_number",
    "vehicle_type",
    "description",
    "violation_type",
    "offence_code",
    "created_datetime",
    "closed_datetime",
    "modified_datetime",
    "device_id",
    "created_by_id",
    "center_code",
    "police_station",
    "data_sent_to_scita",
    "junction_name",
    "action_taken_timestamp",
    "data_sent_to_scita_timestamp",
    "updated_vehicle_number",
    "updated_vehicle_type",
    "validation_status",
    "validation_timestamp",
]

PARKING_VIOLATIONS = {
    "WRONG PARKING",
    "NO PARKING",
    "PARKING IN A MAIN ROAD",
    "PARKING ON FOOTPATH",
    "DOUBLE PARKING",
    "PARKING NEAR ROAD CROSSING",
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC",
    "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS",
    "PARKING OPPOSITE TO ANOTHER PARKED VEHICLE",
    "PARKING OTHER THAN BUS STOP",
}

BENGALURU_BOUNDS = {
    "min_lat": 12.7,
    "max_lat": 13.2,
    "min_lon": 77.3,
    "max_lon": 77.8,
}

GRID_SIZE_DEGREES = 0.0015
DEFAULT_TOP_K = 30


def ensure_dirs() -> None:
    for path in [DATA_DIR, RAW_DIR, PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def find_raw_csv() -> Path:
    candidates = sorted(ROOT.glob(RAW_CSV_GLOB)) + sorted(RAW_DIR.glob(RAW_CSV_GLOB))
    if not candidates:
        raise FileNotFoundError(
            f"Could not find dataset matching {RAW_CSV_GLOB!r} in {ROOT} or {RAW_DIR}."
        )
    return candidates[0]
