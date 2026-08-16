package com.legalai.backend.application.search;

import com.legalai.backend.domain.Client;
import com.legalai.backend.domain.Matter;
import com.legalai.backend.domain.SearchQuery;

import java.util.List;
import java.util.UUID;

/**
 * SD-009: cross-entity search over Client/Matter, scoped to the caller's
 * Firm (BR-008). No new table — this reads the existing Client/Matter
 * storage, so there's no create/update here, only the query.
 */
public interface SearchRepository {

    /** BR-007: never filters out Closed Matters — a status filter, if given, narrows results, it doesn't exclude Closed by default. */
    SearchResult search(UUID firmId, SearchQuery query);

    record SearchResult(List<Client> clients, List<Matter> matters) {
    }
}
