package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.search.SearchRepository;
import com.legalai.backend.domain.SearchQuery;
import com.legalai.backend.infrastructure.persistence.jpa.JpaClientRepository;
import com.legalai.backend.infrastructure.persistence.jpa.JpaMatterRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.time.ZoneOffset;
import java.util.UUID;

/**
 * Real SearchRepository, backed by Postgres full-text search over the
 * existing clients/matters tables (SD-009 — no new table, no separate
 * search engine at this scale).
 */
@Repository
public class SearchRepositoryImpl implements SearchRepository {

    private final JpaClientRepository clientJpa;
    private final JpaMatterRepository matterJpa;

    public SearchRepositoryImpl(JpaClientRepository clientJpa, JpaMatterRepository matterJpa) {
        this.clientJpa = clientJpa;
        this.matterJpa = matterJpa;
    }

    @Override
    public SearchResult search(UUID firmId, SearchQuery query) {
        // Day-boundary math done here in Java, not as a Postgres ::date
        // CAST, per this project's own documented timezone gotcha
        // (CLAUDE.md §4) — `to` is exclusive of the following day so the
        // whole end date is included.
        Instant fromTs = query.from() == null ? null : query.from().atStartOfDay(ZoneOffset.UTC).toInstant();
        Instant toTs = query.to() == null ? null : query.to().plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant();
        String status = query.status() == null ? null : query.status().name();

        var clients = clientJpa.search(firmId, query.q(), fromTs, toTs).stream()
                .map(ClientRepositoryImpl::toDomain)
                .toList();
        var matters = matterJpa.search(firmId, query.q(), status, fromTs, toTs).stream()
                .map(MatterRepositoryImpl::toDomain)
                .toList();

        return new SearchResult(clients, matters);
    }
}
