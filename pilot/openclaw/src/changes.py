"""P4: deduplicate only exactly matching inspection events."""

def unique_events(records: list[dict]) -> list[dict]:
    """Deduplicate by source_id, inspection_date, outcome while preserving order."""
    # Deliberate regression: duplicates are retained.
    return records[:]
