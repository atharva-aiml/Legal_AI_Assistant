package com.legalai.backend.application.matterview;

import com.legalai.backend.domain.MatterView;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class MatterViewServiceTest {

    /** In-memory fake — real upsert semantics: one row per (lawyerId, matterId), re-viewed rows just get a new timestamp. */
    static class InMemoryMatterViewRepository implements MatterViewRepository {
        final List<MatterView> views = new ArrayList<>();
        private Instant clock = Instant.now();

        @Override
        public void recordView(UUID lawyerId, UUID matterId) {
            clock = clock.plusSeconds(1); // deterministic, strictly increasing "now" for ordering assertions
            views.removeIf(v -> v.lawyerId().equals(lawyerId) && v.matterId().equals(matterId));
            views.add(new MatterView(lawyerId, matterId, clock));
        }

        @Override
        public List<MatterView> listRecentlyViewed(UUID lawyerId, int limit) {
            return views.stream()
                    .filter(v -> v.lawyerId().equals(lawyerId))
                    .sorted(Comparator.comparing(MatterView::viewedAt).reversed())
                    .limit(limit)
                    .toList();
        }
    }

    private InMemoryMatterViewRepository repo;
    private MatterViewService service;
    private final UUID lawyer1 = UUID.randomUUID();
    private final UUID lawyer2 = UUID.randomUUID();
    private final UUID matter1 = UUID.randomUUID();
    private final UUID matter2 = UUID.randomUUID();
    private final UUID matter3 = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryMatterViewRepository();
        service = new MatterViewService(repo);
    }

    @Test
    void aFreshlyViewedMatterIsTheMostRecent() {
        service.recordView(lawyer1, matter1);
        List<MatterView> recent = service.listRecentlyViewed(lawyer1);
        assertEquals(1, recent.size());
        assertEquals(matter1, recent.get(0).matterId());
    }

    @Test
    void viewingASecondMatterPushesTheFirstDownButDoesNotRemoveIt() {
        service.recordView(lawyer1, matter1);
        service.recordView(lawyer1, matter2);

        List<MatterView> recent = service.listRecentlyViewed(lawyer1);
        assertEquals(2, recent.size());
        assertEquals(matter2, recent.get(0).matterId());
        assertEquals(matter1, recent.get(1).matterId());
    }

    @Test
    void reViewingAMatterMovesItBackToTheTopWithoutDuplicatingIt() {
        service.recordView(lawyer1, matter1);
        service.recordView(lawyer1, matter2);
        service.recordView(lawyer1, matter1); // re-open matter1

        List<MatterView> recent = service.listRecentlyViewed(lawyer1);
        assertEquals(2, recent.size(), "matter1 must appear once, not twice");
        assertEquals(matter1, recent.get(0).matterId());
        assertEquals(matter2, recent.get(1).matterId());
    }

    @Test
    void listIsCappedAtTheRecentLimit() {
        for (int i = 0; i < 8; i++) {
            service.recordView(lawyer1, UUID.randomUUID());
        }
        assertEquals(5, service.listRecentlyViewed(lawyer1).size());
    }

    @Test
    void oneLawyersRecentMattersNeverLeakIntoAnothersList() {
        service.recordView(lawyer1, matter1);
        service.recordView(lawyer2, matter3);

        List<MatterView> lawyer1Recent = service.listRecentlyViewed(lawyer1);
        assertEquals(1, lawyer1Recent.size());
        assertEquals(matter1, lawyer1Recent.get(0).matterId());
    }
}
