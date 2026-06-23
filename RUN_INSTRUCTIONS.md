# Run Instructions

This project is a Streamlit dashboard and data pipeline for Gridlock Parking Congestion Intelligence.

## 1. Clone The Repository

```powershell
git clone https://github.com/AyushSingh2024/Gridlock.git
cd Gridlock
```

## 2. Create And Activate A Python Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Optional heavier dependencies for HDBSCAN, OSMnx, and YOLO support:

```powershell
python -m pip install -r requirements-optional.txt
```

## 4. Add The Raw Dataset

Place the organizer CSV in the project root with this filename:

```text
jan to may police violation_anonymized791b166.csv
```

The raw CSV is intentionally not committed to GitHub because it is large. The repository already includes processed demo outputs, so the dashboard can run without recomputing the full pipeline.

## 5. Run The Full Pipeline

Run this only when the raw CSV is present:

```powershell
python -m src.run_pipeline
```

This regenerates cleaned data, features, hotspots, NC-CIS scores, patrol route outputs, and report figures under `data/processed/` and `reports/`.

## 6. Start The Dashboard

```powershell
python -m streamlit run dashboard/app.py
```

Open the local URL printed by Streamlit, usually:

```text
http://localhost:8501
```

## 7. Run Tests

```powershell
python -m pytest tests -v --tb=short
```

The tests cover the patrol route optimizer, segment output schema, dashboard route map rendering, and route visualization invariants.

## 8. Useful Commands

Run only the optimizer after `ranked_hotspots.parquet` exists:

```powershell
python -m src.optimization.patrol_optimizer
```

Run the dashboard on a different port:

```powershell
python -m streamlit run dashboard/app.py --server.port 8502
```

## Expected Main Outputs

- `data/processed/ranked_hotspots.parquet`
- `data/processed/patrol_routes.parquet`
- `data/processed/patrol_route_points.parquet`
- `data/processed/patrol_route_segments.parquet`
- `reports/figures/patrol_routes.html`

