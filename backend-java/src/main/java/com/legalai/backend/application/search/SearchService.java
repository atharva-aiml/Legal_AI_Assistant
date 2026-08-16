package com.legalai.backend.application.search;

import com.legalai.backend.domain.SearchQuery;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.UUID;

@Service
public class SearchService {

    private final SearchRepository repository;

    public SearchService(SearchRepository repository) {
        this.repository = repository;
    }

    /** Validated by the domain layer (REQ-011) before the repository is ever touched. */
    public SearchRepository.SearchResult search(UUID firmId, String q, String status, LocalDate from, LocalDate to) {
        SearchQuery query = SearchQuery.parse(q, status, from, to);
        return repository.search(firmId, query);
    }
}
