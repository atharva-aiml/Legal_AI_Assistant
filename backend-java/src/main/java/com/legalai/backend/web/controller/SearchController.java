package com.legalai.backend.web.controller;

import com.legalai.backend.application.recentsearch.RecentSearchService;
import com.legalai.backend.application.search.SearchRepository;
import com.legalai.backend.application.search.SearchService;
import com.legalai.backend.domain.InvalidSearchException;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.domain.RecentSearch;
import com.legalai.backend.web.ApiError;
import com.legalai.backend.web.CurrentLawyerResolver;
import com.legalai.backend.web.dto.ClientDtos.ClientResponse;
import com.legalai.backend.web.dto.MatterDtos.MatterResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
public class SearchController {

    private final SearchService searchService;
    private final RecentSearchService recentSearchService;
    private final CurrentLawyerResolver currentLawyerResolver;

    public SearchController(SearchService searchService, RecentSearchService recentSearchService,
                             CurrentLawyerResolver currentLawyerResolver) {
        this.searchService = searchService;
        this.recentSearchService = recentSearchService;
        this.currentLawyerResolver = currentLawyerResolver;
    }

    /** SD-009 / REQ-011: search/filter Clients and Matters by name, status, and date, scoped to the caller's Firm (BR-008). */
    @GetMapping("/api/search")
    public ResponseEntity<?> search(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        try {
            SearchRepository.SearchResult result = searchService.search(lawyer.get().firmId(), q, status, from, to);
            return ResponseEntity.ok(Map.of(
                    "clients", result.clients().stream().map(ClientResponse::from).toList(),
                    "matters", result.matters().stream().map(MatterResponse::from).toList()));
        } catch (InvalidSearchException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    /** I-48: record a real search so it can be offered back as a one-click suggestion next time. */
    @PostMapping("/api/search/recent")
    public ResponseEntity<?> recordRecentSearch(@RequestBody RecentSearchRequest body, HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        try {
            recentSearchService.record(lawyer.get().id(), body.query());
            return ResponseEntity.ok(Map.of());
        } catch (InvalidSearchException e) {
            return ResponseEntity.badRequest().body(ApiError.of("VALIDATION", e.getMessage()));
        }
    }

    @GetMapping("/api/search/recent")
    public ResponseEntity<?> recentSearches(HttpServletRequest request) {
        Optional<Lawyer> lawyer = currentLawyerResolver.resolve(request);
        if (lawyer.isEmpty()) return unauthenticated();

        List<String> queries = recentSearchService.listRecent(lawyer.get().id()).stream().map(RecentSearch::query).toList();
        return ResponseEntity.ok(Map.of("queries", queries));
    }

    private ResponseEntity<?> unauthenticated() {
        return ResponseEntity.status(org.springframework.http.HttpStatus.UNAUTHORIZED).body(ApiError.unauthenticated());
    }

    private record RecentSearchRequest(String query) {}
}
