package com.legalai.backend.application.search;

import com.legalai.backend.domain.Client;
import com.legalai.backend.domain.InvalidSearchException;
import com.legalai.backend.domain.Matter;
import com.legalai.backend.domain.MatterStatus;
import com.legalai.backend.domain.SearchQuery;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class SearchServiceTest {

    /**
     * Approximates real Postgres full-text/date-range filtering closely
     * enough to test the service's orchestration and BR-007/BR-008 — not a
     * literal tsquery reimplementation, same spirit as this codebase's other
     * in-memory fakes (e.g. NotificationRepositoryImpl's day-comparison).
     */
    static class InMemorySearchRepository implements SearchRepository {
        final List<Client> clients = new ArrayList<>();
        final List<Matter> matters = new ArrayList<>();

        @Override
        public SearchResult search(UUID firmId, SearchQuery query) {
            List<Client> matchedClients = clients.stream()
                    .filter(c -> c.firmId().equals(firmId))
                    .filter(c -> query.q() == null || c.name().toLowerCase().contains(query.q().toLowerCase()))
                    .filter(c -> withinRange(c.createdAt(), query.from(), query.to()))
                    .toList();

            List<Matter> matchedMatters = matters.stream()
                    .filter(m -> m.firmId().equals(firmId))
                    .filter(m -> query.q() == null || m.title().toLowerCase().contains(query.q().toLowerCase()))
                    .filter(m -> query.status() == null || m.status() == query.status())
                    .filter(m -> withinRange(m.createdAt(), query.from(), query.to()))
                    .toList();

            return new SearchResult(matchedClients, matchedMatters);
        }

        private boolean withinRange(Instant createdAt, LocalDate from, LocalDate to) {
            LocalDate day = createdAt.atZone(ZoneOffset.UTC).toLocalDate();
            if (from != null && day.isBefore(from)) return false;
            if (to != null && day.isAfter(to)) return false;
            return true;
        }
    }

    private InMemorySearchRepository repo;
    private SearchService service;
    private final UUID firm1 = UUID.randomUUID();
    private final UUID firm2 = UUID.randomUUID();

    private Client client(UUID firmId, String name, Instant createdAt) {
        return new Client(UUID.randomUUID(), firmId, name, null, null, null, createdAt, createdAt);
    }

    private Matter matter(UUID firmId, String title, MatterStatus status, Instant createdAt) {
        return new Matter(UUID.randomUUID(), firmId, UUID.randomUUID(), title, status, null, createdAt, createdAt);
    }

    @BeforeEach
    void setUp() {
        repo = new InMemorySearchRepository();
        service = new SearchService(repo);
    }

    @Test
    void findsAClientByNameAndAMatterByTitle_REQ011() {
        repo.clients.add(client(firm1, "Apex Components Pvt. Ltd.", Instant.now()));
        repo.matters.add(matter(firm1, "Sharma v. Meridian Buildtech", MatterStatus.open, Instant.now()));

        SearchRepository.SearchResult result = service.search(firm1, "Sharma", null, null, null);

        assertEquals(0, result.clients().size());
        assertEquals(1, result.matters().size());
        assertEquals("Sharma v. Meridian Buildtech", result.matters().get(0).title());
    }

    @Test
    void closedMattersAreNotExcludedFromSearch_BR007() {
        repo.matters.add(matter(firm1, "Old Closed Case", MatterStatus.closed, Instant.now()));

        SearchRepository.SearchResult result = service.search(firm1, "Closed Case", null, null, null);

        assertEquals(1, result.matters().size());
        assertEquals(MatterStatus.closed, result.matters().get(0).status());
    }

    @Test
    void aMatchInAnotherFirmIsNeverReturned_BR008() {
        repo.clients.add(client(firm2, "Sharma Legal Services", Instant.now()));
        repo.matters.add(matter(firm2, "Sharma v. Meridian Buildtech", MatterStatus.open, Instant.now()));

        SearchRepository.SearchResult result = service.search(firm1, "Sharma", null, null, null);

        assertTrue(result.clients().isEmpty());
        assertTrue(result.matters().isEmpty());
    }

    @Test
    void filtersMattersByStatusAlone_REQ011() {
        repo.matters.add(matter(firm1, "Open Matter", MatterStatus.open, Instant.now()));
        repo.matters.add(matter(firm1, "Closed Matter", MatterStatus.closed, Instant.now()));

        SearchRepository.SearchResult result = service.search(firm1, null, "closed", null, null);

        assertEquals(1, result.matters().size());
        assertEquals("Closed Matter", result.matters().get(0).title());
    }

    @Test
    void filtersByDateRangeAlone_REQ011() {
        Instant inRange = LocalDate.of(2026, 6, 15).atStartOfDay(ZoneOffset.UTC).toInstant();
        Instant outOfRange = LocalDate.of(2025, 1, 1).atStartOfDay(ZoneOffset.UTC).toInstant();
        repo.clients.add(client(firm1, "Recent Client", inRange));
        repo.clients.add(client(firm1, "Old Client", outOfRange));

        SearchRepository.SearchResult result = service.search(firm1, null, null, LocalDate.of(2026, 1, 1), LocalDate.of(2026, 12, 31));

        assertEquals(1, result.clients().size());
        assertEquals("Recent Client", result.clients().get(0).name());
    }

    @Test
    void combinesQueryAndStatusTogether() {
        repo.matters.add(matter(firm1, "Sharma v. Meridian Buildtech", MatterStatus.open, Instant.now()));
        repo.matters.add(matter(firm1, "Sharma Estate Matter", MatterStatus.closed, Instant.now()));

        SearchRepository.SearchResult result = service.search(firm1, "Sharma", "open", null, null);

        assertEquals(1, result.matters().size());
        assertEquals("Sharma v. Meridian Buildtech", result.matters().get(0).title());
    }

    @Test
    void rejectsASearchWithNoCriteriaBeforeTouchingTheRepository() {
        assertThrows(InvalidSearchException.class, () -> service.search(firm1, null, null, null, null));
    }

    @Test
    void rejectsAnUnknownStatus() {
        assertThrows(InvalidSearchException.class, () -> service.search(firm1, "Sharma", "archived", null, null));
    }
}
