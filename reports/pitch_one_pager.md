# One-Page Pitch: Parking Congestion Intelligence

## Problem

Illegal and spillover parking near commercial areas, metro stations, and event zones narrows usable carriageway space and creates downstream congestion. Current enforcement is reactive: in this dataset, formal closure/action timestamps are populated for 0.00% of records, and validation takes a median of 31.04 hours.

## Key Insight

The data shows a visibility blind spot. Only 2.04% of recorded parking enforcement happens during 09:00-17:59, while 64.37% happens overnight. That does not mean daytime illegal parking is absent; it means the system is largely not seeing the period when parking-induced congestion is most operationally expensive.

## Approach

The prototype turns the raw police violation CSV into an enforcement decision system:

1. Parse multi-label `violation_type` JSON and keep parking-related offences.
2. Detect dense, recurring hotspot zones.
3. Score zones using NC-CIS: density, capacity-loss pressure, recurrence, and network centrality.
4. Recommend patrol routes that maximize NC-CIS coverage and shift attention into daytime windows.
5. Surface chronic repeat offenders as a vehicle-level targeting axis.

## Why It Wins

Most solutions stop at a heatmap. This one answers: which parking hotspots actually hurt network flow most, and where should limited patrol capacity go first?

NC-CIS makes the system prescriptive. A small but central chokepoint can outrank a larger low-impact cluster, making enforcement more defensible than raw counts.

## Demo Flow, 3-5 Minutes

1. Show the headline metrics: 338,907 parking events, 0.00% closure/action tracking, 31.04h median validation lag.
2. Show the hour-of-day chart and call out the daytime blind spot.
3. Open the NC-CIS map and ranked table; explain why the top hotspot is top-ranked.
4. Use the what-if selector to remove one hotspot and show the modeled burden reduction.
5. Open patrol routes and show the simulated 23.17% NC-CIS coverage gain over a raw-density baseline.
6. Close with repeat offenders: 3,489 vehicles have 5+ recorded violations, giving enforcement a second targeting axis.

## Fallback

If live app or network rendering fails, use the precomputed HTML artifacts in `reports/figures/` plus the markdown findings in `reports/`.
