package com.legalai.backend.application.recentsearch;

import com.legalai.backend.domain.InvalidSearchException;
import com.legalai.backend.domain.RecentSearch;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class RecentSearchServiceTest {

    /** In-memory fake — real upsert semantics: one row per (lawyerId, query), re-searched rows just get a new timestamp. */
    static class InMemoryRecentSearchRepository implements RecentSearchRepository {
        final List<RecentSearch> searches = new ArrayList<>();
        private Instant clock = Instant.now();

        @Override
        public void record(UUID lawyerId, String query) {
            clock = clock.plusSeconds(1); // deterministic, strictly increasing "now" for ordering assertions
            searches.removeIf(s -> s.lawyerId().equals(lawyerId) && s.query().equals(query));
            searches.add(new RecentSearch(lawyerId, query, clock));
        }

        @Override
        public List<RecentSearch> listRecent(UUID lawyerId, int limit) {
            return searches.stream()
                    .filter(s -> s.lawyerId().equals(lawyerId))
                    .sorted(Comparator.comparing(RecentSearch::searchedAt).reversed())
                    .limit(limit)
                    .toList();
        }
    }

    private InMemoryRecentSearchRepository repo;
    private RecentSearchService service;
    private final UUID lawyer1 = UUID.randomUUID();
    private final UUID lawyer2 = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryRecentSearchRepository();
        service = new RecentSearchService(repo);
    }

    @Test
    void aFreshlyRunSearchIsTheMostRecent() {
        service.record(lawyer1, "Acme Corp");
        List<RecentSearch> recent = service.listRecent(lawyer1);
        assertEquals(1, recent.size());
        assertEquals("Acme Corp", recent.get(0).query());
    }

    @Test
    void aSecondSearchPushesTheFirstDownButDoesNotRemoveIt() {
        service.record(lawyer1, "Acme Corp");
        service.record(lawyer1, "Meridian Buildtech");

        List<RecentSearch> recent = service.listRecent(lawyer1);
        assertEquals(2, recent.size());
        assertEquals("Meridian Buildtech", recent.get(0).query());
        assertEquals("Acme Corp", recent.get(1).query());
    }

    @Test
    void reRunningTheSameQueryMovesItBackToTheTopWithoutDuplicatingIt() {
        service.record(lawyer1, "Acme Corp");
        service.record(lawyer1, "Meridian Buildtech");
        service.record(lawyer1, "Acme Corp"); // re-search

        List<RecentSearch> recent = service.listRecent(lawyer1);
        assertEquals(2, recent.size(), "'Acme Corp' must appear once, not twice");
        assertEquals("Acme Corp", recent.get(0).query());
        assertEquals("Meridian Buildtech", recent.get(1).query());
    }

    @Test
    void listIsCappedAtTheRecentLimit() {
        for (int i = 0; i < 8; i++) {
            service.record(lawyer1, "query-" + i);
        }
        assertEquals(5, service.listRecent(lawyer1).size());
    }

    @Test
    void oneLawyersRecentSearchesNeverLeakIntoAnothersList() {
        service.record(lawyer1, "Acme Corp");
        service.record(lawyer2, "Meridian Buildtech");

        List<RecentSearch> lawyer1Recent = service.listRecent(lawyer1);
        assertEquals(1, lawyer1Recent.size());
        assertEquals("Acme Corp", lawyer1Recent.get(0).query());
    }

    @Test
    void rejectsABlankQueryBeforeEverTouchingTheRepository() {
        assertThrows(InvalidSearchException.class, () -> service.record(lawyer1, "   "));
        assertTrue(repo.searches.isEmpty());
    }
}
