"""P5: combine verified components to make source-traceable synthetic cards."""

from .areas import canonical_area
from .dates import inspection_date_label
from .outcomes import outcome_label
from .changes import unique_events

def summary_cards(records: list[dict]) -> list[dict]:
    """One unique card per known area/source; preserve source ID, date and outcome."""
    raise NotImplementedError("P5 must wait for verified P1-P4")
