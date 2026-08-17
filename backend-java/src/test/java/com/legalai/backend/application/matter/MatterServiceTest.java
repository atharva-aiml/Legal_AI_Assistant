package com.legalai.backend.application.matter;

import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.domain.InvalidMatterException;
import com.legalai.backend.domain.Matter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Direct port of the original TypeScript matter-use-cases.test.ts — same
 * in-memory-fake approach, same cases, now exercising MatterService instead
 * of four separate use-case functions (Java-idiomatic consolidation, see
 * MatterService's class comment).
 */
class MatterServiceTest {

    /** In-memory fake — satisfies the same MatterRepository port the real JPA-backed one does. */
    static class InMemoryMatterRepository implements MatterRepository {
        final List<Matter> matters = new ArrayList<>();

        @Override
        public Matter create(Matter.NewMatter record) {
            Matter matter = new Matter(UUID.randomUUID(), record.firmId(), record.clientId(), record.title(), record.status(), null, Instant.now(), Instant.now());
            matters.add(matter);
            return matter;
        }

        @Override
        public List<Matter> listByFirm(UUID firmId) {
            return matters.stream().filter(m -> m.firmId().equals(firmId)).toList();
        }

        @Override
        public List<Matter> listByClient(UUID firmId, UUID clientId) {
            return matters.stream().filter(m -> m.firmId().equals(firmId) && m.clientId().equals(clientId)).toList();
        }

        @Override
        public Optional<Matter> findById(UUID firmId, UUID id) {
            return matters.stream().filter(m -> m.firmId().equals(firmId) && m.id().equals(id)).findFirst();
        }

        @Override
        public Optional<Matter> updateTitle(UUID firmId, UUID id, String title) {
            for (int i = 0; i < matters.size(); i++) {
                Matter m = matters.get(i);
                if (m.firmId().equals(firmId) && m.id().equals(id)) {
                    Matter renamed = new Matter(m.id(), m.firmId(), m.clientId(), title, m.status(), m.closedAt(), m.createdAt(), Instant.now());
                    matters.set(i, renamed);
                    return Optional.of(renamed);
                }
            }
            return Optional.empty();
        }

        @Override
        public Optional<Matter> close(UUID firmId, UUID id) {
            for (int i = 0; i < matters.size(); i++) {
                Matter m = matters.get(i);
                if (m.firmId().equals(firmId) && m.id().equals(id)) {
                    Matter closed = new Matter(m.id(), m.firmId(), m.clientId(), m.title(), com.legalai.backend.domain.MatterStatus.closed, Instant.now(), m.createdAt(), Instant.now());
                    matters.set(i, closed);
                    return Optional.of(closed);
                }
            }
            return Optional.empty();
        }

        @Override
        public Optional<Matter> reopen(UUID firmId, UUID id) {
            for (int i = 0; i < matters.size(); i++) {
                Matter m = matters.get(i);
                if (m.firmId().equals(firmId) && m.id().equals(id)) {
                    Matter reopened = new Matter(m.id(), m.firmId(), m.clientId(), m.title(), com.legalai.backend.domain.MatterStatus.open, null, m.createdAt(), Instant.now());
                    matters.set(i, reopened);
                    return Optional.of(reopened);
                }
            }
            return Optional.empty();
        }
    }

    /** Minimal fake — MatterService only ever calls listByMatter on this port. */
    static class InMemoryDeadlineRepository implements DeadlineRepository {
        final List<Deadline> deadlines = new ArrayList<>();

        @Override
        public Deadline create(Deadline.NewDeadline record) {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public List<Deadline> listByMatter(UUID firmId, UUID matterId) {
            return deadlines.stream().filter(d -> d.matterId().equals(matterId)).toList();
        }

        @Override
        public Optional<Deadline> findById(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, DeadlinePriority priority, int notificationLeadDays) {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public List<Deadline> listUpcoming(UUID firmId, int days) {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public List<DeadlineWithFirm> listAllOpenWithFirm() {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }
    }

    private InMemoryMatterRepository repo;
    private InMemoryDeadlineRepository deadlineRepo;
    private MatterService service;
    private final UUID firm1 = UUID.randomUUID();
    private final UUID firm2 = UUID.randomUUID();
    private final UUID client1 = UUID.randomUUID();
    private final UUID client2 = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryMatterRepository();
        deadlineRepo = new InMemoryDeadlineRepository();
        service = new MatterService(repo, deadlineRepo);
    }

    @Test
    void createsAMatterAndPersistsItInTheRepository() {
        Matter matter = service.create(firm1, client1, "New Case");
        assertNotNull(matter.id());
        assertEquals(1, repo.matters.size());
    }

    @Test
    void rejectsAnInvalidMatterBeforeEverTouchingTheRepository() {
        assertThrows(InvalidMatterException.class, () -> service.create(firm1, null, "No Client"));
        assertEquals(0, repo.matters.size());
    }

    @Test
    void listsOnlyMattersBelongingToTheRequestedFirm_BR008() {
        service.create(firm1, client1, "Firm 1 Matter");
        service.create(firm2, client2, "Firm 2 Matter");

        List<Matter> firm1Matters = service.list(firm1, null, null);
        assertEquals(1, firm1Matters.size());
        assertEquals("Firm 1 Matter", firm1Matters.get(0).title());
    }

    @Test
    void listsOnlyMattersForAGivenClientWithinAFirm() {
        service.create(firm1, client1, "Client 1 Matter");
        service.create(firm1, client2, "Client 2 Matter");

        List<Matter> client1Matters = service.list(firm1, client1, null);
        assertEquals(1, client1Matters.size());
        assertEquals("Client 1 Matter", client1Matters.get(0).title());
    }

    // --- I-23: status filter ---

    @Test
    void filtersByStatus_WhenGiven() {
        Matter open = service.create(firm1, client1, "Open Matter");
        Matter toClose = service.create(firm1, client1, "Closed Matter");
        service.close(firm1, toClose.id());

        List<Matter> openOnly = service.list(firm1, null, com.legalai.backend.domain.MatterStatus.open);
        assertEquals(1, openOnly.size());
        assertEquals(open.id(), openOnly.get(0).id());

        List<Matter> closedOnly = service.list(firm1, null, com.legalai.backend.domain.MatterStatus.closed);
        assertEquals(1, closedOnly.size());
        assertEquals(toClose.id(), closedOnly.get(0).id());
    }

    @Test
    void combinesClientAndStatusFilters() {
        Matter c1Open = service.create(firm1, client1, "Client1 Open");
        Matter c1Closed = service.create(firm1, client1, "Client1 Closed");
        service.close(firm1, c1Closed.id());
        service.create(firm1, client2, "Client2 Open");

        List<Matter> result = service.list(firm1, client1, com.legalai.backend.domain.MatterStatus.open);
        assertEquals(1, result.size());
        assertEquals(c1Open.id(), result.get(0).id());
    }

    @Test
    void nullStatusReturnsMattersOfEveryStatus() {
        service.create(firm1, client1, "Open Matter");
        Matter toClose = service.create(firm1, client1, "Closed Matter");
        service.close(firm1, toClose.id());

        assertEquals(2, service.list(firm1, null, null).size());
    }

    @Test
    void returnsEmptyForAMatterOutsideTheCallersFirm_BR008() {
        Matter created = service.create(firm1, client1, "Private");
        assertTrue(service.get(firm2, created.id()).isEmpty());
    }

    @Test
    void renamesAMatter() {
        Matter created = service.create(firm1, client1, "Old Title");
        Optional<Matter> renamed = service.rename(firm1, created.id(), "New Title");
        assertEquals("New Title", renamed.orElseThrow().title());
    }

    @Test
    void rejectsRenamingToAnEmptyTitle() {
        Matter created = service.create(firm1, client1, "Old Title");
        assertThrows(InvalidMatterException.class, () -> service.rename(firm1, created.id(), "   "));
    }

    @Test
    void renamingAMatterOutsideTheCallersFirmReturnsEmptyNotAnError() {
        Matter created = service.create(firm1, client1, "Old Title");
        assertTrue(service.rename(firm2, created.id(), "Hijacked Title").isEmpty());
    }

    // --- REQ-010/BR-003: closing a Matter ---

    @Test
    void closesAMatterWithNoDeadlinesAtAll() {
        Matter created = service.create(firm1, client1, "No Deadlines");
        Matter closed = service.close(firm1, created.id()).orElseThrow();
        assertEquals(com.legalai.backend.domain.MatterStatus.closed, closed.status());
        assertNotNull(closed.closedAt());
    }

    @Test
    void closesAMatterWhoseDeadlinesAreAllComplete_BR003() {
        Matter created = service.create(firm1, client1, "All Done");
        deadlineRepo.deadlines.add(new Deadline(UUID.randomUUID(), created.id(), "Filed", LocalDate.now(), DeadlineStatus.complete, DeadlinePriority.standard, 3, null, null));

        Matter closed = service.close(firm1, created.id()).orElseThrow();
        assertEquals(com.legalai.backend.domain.MatterStatus.closed, closed.status());
    }

    @Test
    void blocksClosingAMatterWithAnOpenDeadline_BR003() {
        Matter created = service.create(firm1, client1, "Has Open Deadline");
        Deadline open = new Deadline(UUID.randomUUID(), created.id(), "File response", LocalDate.now().plusDays(5), DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlineRepo.deadlines.add(open);

        MatterService.MatterHasOpenDeadlinesException ex = assertThrows(
                MatterService.MatterHasOpenDeadlinesException.class,
                () -> service.close(firm1, created.id()));

        assertEquals(1, ex.openDeadlines().size());
        assertEquals("File response", ex.openDeadlines().get(0).title());
        // The Matter itself must be untouched — still open.
        assertEquals(com.legalai.backend.domain.MatterStatus.open, repo.findById(firm1, created.id()).orElseThrow().status());
    }

    @Test
    void closingAMatterOutsideTheCallersFirmReturnsEmptyNotAnError_BR008() {
        Matter created = service.create(firm1, client1, "Private");
        assertTrue(service.close(firm2, created.id()).isEmpty());
    }

    // --- I-35: reopening a Matter ---

    @Test
    void reopensAClosedMatter() {
        Matter created = service.create(firm1, client1, "Closed by mistake");
        service.close(firm1, created.id());

        Matter reopened = service.reopen(firm1, created.id()).orElseThrow();
        assertEquals(com.legalai.backend.domain.MatterStatus.open, reopened.status());
        assertNull(reopened.closedAt());
    }

    @Test
    void rejectsReopeningAMatterThatIsAlreadyOpen() {
        Matter created = service.create(firm1, client1, "Never closed");
        assertThrows(InvalidMatterException.class, () -> service.reopen(firm1, created.id()));
        // Untouched — still open, as it always was.
        assertEquals(com.legalai.backend.domain.MatterStatus.open, repo.findById(firm1, created.id()).orElseThrow().status());
    }

    @Test
    void reopeningAMatterOutsideTheCallersFirmReturnsEmptyNotAnError_BR008() {
        Matter created = service.create(firm1, client1, "Private");
        service.close(firm1, created.id());
        assertTrue(service.reopen(firm2, created.id()).isEmpty());
    }
}
