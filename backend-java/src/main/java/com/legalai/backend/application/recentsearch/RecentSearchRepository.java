package com.legalai.backend.application.recentsearch;

import com.legalai.backend.domain.RecentSearch;

import java.util.List;
import java.util.UUID;

public interface RecentSearchRepository {
    /** Upsert semantics: re-running an already-recorded query updates its timestamp, never adds a second row. */
    void record(UUID lawyerId, String query);

    /** Most-recently-searched first, capped at limit. */
    List<RecentSearch> listRecent(UUID lawyerId, int limit);
}
