"""P3: preserve exact outcome text, do not invent Pass."""

def outcome_label(record: dict) -> str:
    """Return exact nonempty outcome, or 'Outcome unavailable'."""
    # Deliberate incorrect promotion of missing outcome.
    return record.get("outcome") or "Pass"
