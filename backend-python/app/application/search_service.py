from datetime import date

from app.application.crud_ports import RecentSearchRepository, SearchRepository, SearchResult
from app.domain.search import RecentSearch, SearchQuery

# I-48: a short, dropdown-suggestion-sized list, not a full search history.
RECENT_LIMIT = 5


class SearchService:
    """SD-009: Client/Matter search, scoped to the caller's Firm (BR-008)."""

    def __init__(self, repository: SearchRepository) -> None:
        self.repository = repository

    def search(self, firm_id: str, q: str | None, status: str | None, from_date: date | None, to_date: date | None) -> SearchResult:
        """Validated by the domain layer (REQ-011) before the repository is ever touched."""
        return self.repository.search(firm_id, SearchQuery.parse(q, status, from_date, to_date))


class RecentSearchService:
    def __init__(self, repository: RecentSearchRepository) -> None:
        self.repository = repository

    def record(self, lawyer_id: str, query: str | None) -> None:
        self.repository.record(lawyer_id, RecentSearch.validate_query(query))

    def list_recent(self, lawyer_id: str) -> list[RecentSearch]:
        return self.repository.list_recent(lawyer_id, RECENT_LIMIT)
