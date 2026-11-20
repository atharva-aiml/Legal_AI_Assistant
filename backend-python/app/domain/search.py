from dataclasses import dataclass
from datetime import date, datetime

from app.domain.matter import MatterStatus


class InvalidSearchError(ValueError):
    pass


@dataclass(frozen=True)
class SearchQuery:
    """REQ-011: "Lawyer can search/filter Clients and Matters by name, status,
    and date." A search always runs within the caller's Firm (BR-008, enforced
    by the application layer) and never excludes Closed Matters (BR-007) —
    this only validates *what* was asked for."""

    q: str | None
    status: MatterStatus | None
    from_date: date | None
    to_date: date | None

    @staticmethod
    def parse(raw_q: str | None, raw_status: str | None, from_date: date | None, to_date: date | None) -> "SearchQuery":
        """At least one real criterion is required — an entirely empty search
        isn't a meaningful request, it's a missing one."""
        q = raw_q.strip() if raw_q is not None else None
        if q is not None and not q:
            q = None

        status = None
        if raw_status is not None and raw_status.strip():
            try:
                status = MatterStatus(raw_status.strip())
            except ValueError:
                raise InvalidSearchError(f"Unknown status: '{raw_status}' — expected 'open' or 'closed'.") from None

        if q is None and status is None and from_date is None and to_date is None:
            raise InvalidSearchError("A search needs at least a query, a status, or a date range (REQ-011).")

        if from_date is not None and to_date is not None and from_date > to_date:
            raise InvalidSearchError("The date range's start can't be after its end.")

        return SearchQuery(q, status, from_date, to_date)


@dataclass(frozen=True)
class RecentSearch:
    """I-48: "this Lawyer ran this query at this time", upserted one row per
    (lawyer_id, query). One real invariant: a blank query isn't worth remembering."""

    lawyer_id: str
    query: str
    searched_at: datetime

    @staticmethod
    def validate_query(query: str | None) -> str:
        trimmed = (query or "").strip()
        if not trimmed:
            raise InvalidSearchError("A recent search needs a non-empty query.")
        return trimmed
