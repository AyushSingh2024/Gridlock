# Demo Script

## Opening, 20 seconds

"This is an illegal-parking congestion intelligence system. It does not just show where violations are dense; it ranks where parking is most likely to damage road-network flow."

## Data Credibility, 45 seconds

"We parse the organizer CSV directly. `violation_type` is a JSON list, so the pipeline explodes each record into one violation event and filters parking offences. The current run produces 338,907 parking events from 298,282 source records. Closure/action tracking is 0.00%, and validation lag is 31.04 hours median."

## Blind Spot, 45 seconds

"The surprising finding is temporal. Only 2.04% of enforcement is recorded during 09:00-17:59. Overnight accounts for 64.37%. That is not evidence that daytime illegal parking is absent; it is evidence that enforcement visibility is misaligned with commercial congestion impact."

## NC-CIS, 75 seconds

"The score combines density, recurrence, capacity-loss pressure, and graph betweenness centrality. This means a hotspot on a central corridor can outrank a larger but less network-critical cluster. That is the shift from descriptive heatmap to prescriptive congestion intelligence."

## Actionability, 60 seconds

"The patrol optimizer routes three units over the top 30 NC-CIS zones and compares that against a raw-density baseline. This is a simulated comparison, and the current run shows a 23.17% higher NC-CIS coverage score."

## Close, 30 seconds

"The system also surfaces chronic repeat offenders: 3,489 vehicles have five or more recorded parking violations, and the worst has 55. So the final enforcement strategy has two axes: high-impact places and high-risk vehicles."
