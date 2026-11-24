"""P1: resolve only documented aliases and official area names."""

OFFICIAL_AREAS = ("West Rouge", "Highland Creek", "Agincourt North")

def canonical_area(value: str | None) -> str | None:
    """Return official area for exact matches or West Rouge alias; None otherwise."""
    # Deliberately incomplete: do not commit this implementation as correct.
    return value
