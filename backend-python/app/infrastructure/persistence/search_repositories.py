from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import text

from app.application.crud_ports import SearchResult
from app.domain.search import RecentSearch, SearchQuery
from app.infrastructure.persistence.connection import connection
from app.infrastructure.persistence.mappers import to_client, to_matter, utc


def _start_of_day_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


class SqlSearchRepository:
    """Postgres full-text search over the existing clients/matters tables
    (SD-009 — no new table, no separate search engine at this scale).
    plainto_tsquery's AND-semantics are deliberate here (name search), unlike
    AI Chat's keyword retrieval (CLAUDE.md §4)."""

    def search(self, firm_id: str, query: SearchQuery) -> SearchResult:
        # Day boundaries computed here in UTC, not as a Postgres ::date CAST;
        # `to` is exclusive of the following day so the whole end date is included.
        params = {
            "firm_id": firm_id,
            "q": query.q,
            "status": query.status.value if query.status else None,
            "from_ts": _start_of_day_utc(query.from_date) if query.from_date else None,
            "to_ts": _start_of_day_utc(query.to_date + timedelta(days=1)) if query.to_date else None,
        }
        date_filter = (
            "AND (CAST(:from_ts AS timestamptz) IS NULL OR {t}.created_at >= CAST(:from_ts AS timestamptz)) "
            "AND (CAST(:to_ts AS timestamptz) IS NULL OR {t}.created_at < CAST(:to_ts AS timestamptz))"
        )
        with connection() as conn:
            clients = conn.execute(
                text(
                    "SELECT * FROM clients c WHERE c.firm_id = :firm_id "
                    "AND (CAST(:q AS text) IS NULL OR to_tsvector('english', c.name) @@ plainto_tsquery('english', CAST(:q AS text))) "
                    + date_filter.format(t="c")
                ),
                params,
            ).mappings().all()
            matters = conn.execute(
                text(
                    "SELECT * FROM matters m WHERE m.firm_id = :firm_id "
                    "AND (CAST(:q AS text) IS NULL OR to_tsvector('english', m.title) @@ plainto_tsquery('english', CAST(:q AS text))) "
                    "AND (CAST(:status AS text) IS NULL OR m.status::text = CAST(:status AS text)) "
                    + date_filter.format(t="m")
                ),
                params,
            ).mappings().all()
        return SearchResult([to_client(r) for r in clients], [to_matter(r) for r in matters])


class SqlRecentSearchRepository:
    def record(self, lawyer_id: str, query: str) -> None:
        """One row per (lawyer_id, query) — I-48's unique index makes this an atomic upsert."""
        with connection() as conn:
            conn.execute(
                text(
                    "INSERT INTO recent_searches (lawyer_id, query, searched_at) VALUES (:lawyer_id, :query, now()) "
                    "ON CONFLICT (lawyer_id, query) DO UPDATE SET searched_at = now()"
                ),
                {"lawyer_id": lawyer_id, "query": query},
            )

    def list_recent(self, lawyer_id: str, limit: int) -> list[RecentSearch]:
        with connection() as conn:
            rows = conn.execute(
                text("SELECT lawyer_id, query, searched_at FROM recent_searches WHERE lawyer_id = :lawyer_id ORDER BY searched_at DESC LIMIT :limit"),
                {"lawyer_id": lawyer_id, "limit": limit},
            ).mappings().all()
        return [RecentSearch(str(r["lawyer_id"]), r["query"], utc(r["searched_at"])) for r in rows]
