# Selected police calls client prototype

This module is an on-demand, in-memory client for the Toronto Police Service
`C4S_Public_NoGO` aggregate. It requests only grouped counts for divisions
D41, D42, and D43. It never requests event identifiers, locations, or
incident-level rows.

The client is deliberately separate from the historical quarterly CSI
prototype. The counts describe selected calls published for these divisions;
they are not a complete measure of crime, police activity, or officer presence.
The source is queried only while the caller is visible and explicitly requests
the selected-calls view. Nothing is archived or polled in the background.

The conservative application policy is a 30-minute maximum upstream edit age,
a 10-minute in-memory result lifetime, and a 5-minute minimum interval between
attempts (including failures). These are application safeguards, not a TPS
service-level agreement. A stale or failed response returns an unavailable
state with no counts.

Tests use synthetic ArcGIS responses only. They do not query the live service or
publish current counts. Before UI integration, the host page should disclose
that opening this mode makes an on-demand request to TPS/Esri, and show the
source attribution and official map link.

Source: <https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0>
Official map: <https://experience.arcgis.com/experience/a22f5295933e48a5b0a4c90cd3c4cae1>
Attribution: Contains information licensed under the Open Government Licence - Toronto.

