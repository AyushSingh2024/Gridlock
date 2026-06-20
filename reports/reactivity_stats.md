# Reactivity and Cleaning Stats

- Source CSV: `jan to may police violation_anonymized791b166.csv`
- Raw records: 298,450
- Parking-only violation events after exploding labels: 338,907
- Unique source records containing parking violations: 298,282
- Unique lat/lon points rounded to 6 decimals: 208,311
- Date range: 2023-11-09 19:11:46+00:00 to 2024-04-08 17:30:46+00:00
- `closed_datetime` non-null rate: 0.00%
- `action_taken_timestamp` non-null rate: 0.00%
- `validation_timestamp` non-null rate: 58.03%
- Median validation lag: 31.04 hours
- Mean validation lag: 96.78 hours
- `No Junction` share in raw data: 49.55%
- Out-of-bounds parking events dropped: 200

Pitch sentence: We have 338,907 parking violation events across 208,311 unique GPS points, spanning 2023-11-09 19:11:46+00:00 to 2024-04-08 17:30:46+00:00, with a current formal closure/action-tracking rate of 0.00%.