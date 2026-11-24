"""P2: keep event dates separate from collection and publication."""

def inspection_date_label(record: dict) -> str:
    """Use inspection_date only, or 'Inspection date unavailable'."""
    # Deliberate date-provenance defect for the pilot.
    return str(record.get("collected_at", "Inspection date unavailable"))[:10]
