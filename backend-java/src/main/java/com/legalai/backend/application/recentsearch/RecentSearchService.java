package com.legalai.backend.application.recentsearch;

import com.legalai.backend.domain.RecentSearch;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

@Service
public class RecentSearchService {

    /** I-48: a short, dropdown-suggestion-sized list, not a full search history. */
    private static final int RECENT_LIMIT = 5;

    private final RecentSearchRepository repository;

    public RecentSearchService(RecentSearchRepository repository) {
        this.repository = repository;
    }

    public void record(UUID lawyerId, String query) {
        String validated = RecentSearch.validateQuery(query);
        repository.record(lawyerId, validated);
    }

    public List<RecentSearch> listRecent(UUID lawyerId) {
        return repository.listRecent(lawyerId, RECENT_LIMIT);
    }
}
