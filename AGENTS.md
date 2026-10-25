# Scarb.TO implementation rules

- The agreed product is a Scarborough-first living atlas, not a generic blog or full municipal portal.
- Map dominates the first view, with matching records list, mobile-first usability, recent changes, filters across feed layers, official provenance, a modern credible local identity.
- PoC: a real public map populated by the official Toronto DineSafe CSV, plus machine-readable CSV export. Do not substitute mock records or hardcode fake current inspection status.
- Phase 1B: Toronto Police published historical/updated occurrence data (not live dispatch). Phase 1C: development permits. Beach quality: add when seasonal relevance supports it. Phase 2: election candidate information, linked to authoritative municipal/provincial/federal sources.
- Public sources may be lagged; distinguish occurred/inspected date, source refresh time, and ingestion/detection time; never equate reported incidents with live emergencies.
- Underlying single-file JSON snapshot and normalised export should support future free community-news briefs and paid aggregate reporting; don't build reporting services into the PoC.
- One import process per source. Fail closed on source/schema errors and significant unexpected data loss. Last good public snapshot stays served. Show stale data distinctly and preserve rollback.
- No database, secret, login, paid map key, or large framework for the PoC. Public repository standard GitHub-hosted Actions are permitted for essential daily automation; use GMKtec for normal development. Spend cap C$25/month, target C$0.
- Do not replace the live scarb.to website or modify DNS until a genuine official-data staging build is inspected, validated, and the public cutover can be rolled back.
- Do not turn extra gates, approval ceremonies, new accounts, or paid add-ons into default requirements. Tests, one essential source sanity check, safe release, and live verification suffice.
- User input/corrections, stored preferences beyond browser settings, subscriptions, sponsorship, local discovery, and reports are post-PoC.
- Test, merge, deploy and verify authorised work without another routine permission prompt. Where provider access blocks one item, continue all other work and report only exact owner steps.
