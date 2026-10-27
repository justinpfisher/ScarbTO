# Selected calls UI integration

The reviewed on-demand client now lives at `docs/selected-calls.mjs` and is used by the explicit “Selected police calls” view. Its tests remain here as the research-contract suite and import the deployed module directly.

The view requests only grouped totals for TPS divisions D41, D42, and D43. It makes no request until selected, keeps counts in memory only, aborts and clears them when hidden or left, and shows no current counts when the upstream result is stale or fails.

The counts represent selected calls published for these divisions, not all crime, police activity, or officer presence. The UI links to the official TPS map and displays Open Government Licence – Ontario attribution. Browser tests intercept the service with synthetic responses; they do not make live TPS requests.
