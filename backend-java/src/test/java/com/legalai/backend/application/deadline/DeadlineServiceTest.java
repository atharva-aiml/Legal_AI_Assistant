package com.legalai.backend.application.deadline;

import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.domain.InvalidDeadlineException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class DeadlineServiceTest {

    static class InMemoryDeadlineRepository implements DeadlineRepository {
        final List<Deadline> deadlines = new ArrayList<>();
        final java.util.Map<UUID, UUID> matterFirm = new java.util.HashMap<>(); // matterId -> firmId, for the upcoming/isolation tests

        @Override
        public Deadline create(Deadline.NewDeadline record) {
            Deadline deadline = new Deadline(UUID.randomUUID(), record.matterId(), record.title(), record.dueDate(), DeadlineStatus.open, record.priority(), record.notificationLeadDays(), Instant.now(), Instant.now());
            deadlines.add(deadline);
            return deadline;
        }

        @Override
        public List<Deadline> listByMatter(UUID firmId, UUID matterId) {
            if (!firmId.equals(matterFirm.get(matterId))) return List.of();
            return deadlines.stream().filter(d -> d.matterId().equals(matterId)).toList();
        }

        @Override
        public Optional<Deadline> findById(UUID firmId, UUID id) {
            return deadlines.stream()
                    .filter(d -> d.id().equals(id) && firmId.equals(matterFirm.get(d.matterId())))
                    .findFirst();
        }

        @Override
        public Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, DeadlinePriority priority, int notificationLeadDays) {
            for (int i = 0; i < deadlines.size(); i++) {
                Deadline d = deadlines.get(i);
                if (d.id().equals(id) && firmId.equals(matterFirm.get(d.matterId()))) {
                    Deadline updated = new Deadline(d.id(), d.matterId(), title, dueDate, status, priority, notificationLeadDays, d.createdAt(), Instant.now());
                    deadlines.set(i, updated);
                    return Optional.of(updated);
                }
            }
            return Optional.empty();
        }

        @Override
        public List<Deadline> listUpcoming(UUID firmId, int days) {
            LocalDate cutoff = LocalDate.now().plusDays(days);
            return deadlines.stream()
                    .filter(d -> d.status() == DeadlineStatus.open)
                    .filter(d -> firmId.equals(matterFirm.get(d.matterId())))
                    .filter(d -> !d.dueDate().isAfter(cutoff))
                    .toList();
        }

        @Override
        public List<DeadlineWithFirm> listAllOpenWithFirm() {
            return deadlines.stream()
                    .filter(d -> d.status() == DeadlineStatus.open)
                    .map(d -> new DeadlineWithFirm(d, matterFirm.get(d.matterId())))
                    .toList();
        }
    }

    private InMemoryDeadlineRepository repo;
    private DeadlineService service;
    private final UUID firm1 = UUID.randomUUID();
    private final UUID firm2 = UUID.randomUUID();
    private final UUID matterId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryDeadlineRepository();
        repo.matterFirm.put(matterId, firm1);
        service = new DeadlineService(repo);
    }

    @Test
    void createsADeadlineAndPersistsIt() {
        Deadline created = service.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        assertNotNull(created.id());
        assertEquals(DeadlineStatus.open, created.status());
        assertEquals(3, created.notificationLeadDays());
    }

    @Test
    void rejectsAnInvalidDeadlineBeforeTouchingTheRepository() {
        assertThrows(InvalidDeadlineException.class, () -> service.create(matterId, "", LocalDate.of(2026, 9, 1), null, null));
        assertEquals(0, repo.deadlines.size());
    }

    @Test
    void listsDeadlinesForAMatterWithinTheCallersFirm() {
        service.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        List<Deadline> listed = service.list(firm1, matterId);
        assertEquals(1, listed.size());
    }

    @Test
    void listingFromAnotherFirmReturnsEmpty_BR008() {
        service.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        assertTrue(service.list(firm2, matterId).isEmpty());
    }

    @Test
    void updatesOnlyTheFieldsProvided() {
        Deadline created = service.create(matterId, "Original", LocalDate.of(2026, 9, 1), null, 3);
        Deadline updated = service.update(firm1, created.id(), "Renamed", null, null, null, null).orElseThrow();

        assertEquals("Renamed", updated.title());
        assertEquals(LocalDate.of(2026, 9, 1), updated.dueDate()); // unchanged
        assertEquals(DeadlineStatus.open, updated.status()); // unchanged
        assertEquals(DeadlinePriority.standard, updated.priority()); // unchanged
        assertEquals(3, updated.notificationLeadDays()); // unchanged
    }

    @Test
    void marksADeadlineComplete() {
        Deadline created = service.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        Deadline completed = service.update(firm1, created.id(), null, null, DeadlineStatus.complete, null, null).orElseThrow();
        assertEquals(DeadlineStatus.complete, completed.status());
    }

    @Test
    void rejectsUpdatingToAnEmptyTitle() {
        Deadline created = service.create(matterId, "Original", LocalDate.of(2026, 9, 1), null, null);
        assertThrows(InvalidDeadlineException.class, () -> service.update(firm1, created.id(), "   ", null, null, null, null));
    }

    @Test
    void rejectsUpdatingTheDueDateToThePast_BR009() {
        Deadline created = service.create(matterId, "Original", LocalDate.now().plusDays(10), null, null);
        assertThrows(InvalidDeadlineException.class,
                () -> service.update(firm1, created.id(), null, LocalDate.now().minusDays(1), null, null, null));
    }

    @Test
    void updatingStatusWithoutTouchingDueDateIsAllowedEvenIfOverdue() {
        // Marking an already-overdue Deadline complete doesn't re-supply a
        // dueDate, so BR-009 shouldn't fire — only an explicit reschedule
        // to a past date is blocked.
        Deadline created = service.create(matterId, "Original", LocalDate.now().plusDays(1), null, null);
        // Simulate the Deadline having become overdue by directly updating its dueDate in the repo (bypassing the service).
        repo.update(firm1, created.id(), created.title(), LocalDate.now().minusDays(5), created.status(), created.priority(), created.notificationLeadDays());

        Deadline completed = service.update(firm1, created.id(), null, null, DeadlineStatus.complete, null, null).orElseThrow();
        assertEquals(DeadlineStatus.complete, completed.status());
    }

    @Test
    void updatingFromAnotherFirmReturnsEmpty_BR008() {
        Deadline created = service.create(matterId, "Original", LocalDate.of(2026, 9, 1), null, null);
        assertTrue(service.update(firm2, created.id(), "Hijacked", null, null, null, null).isEmpty());
    }

    @Test
    void upcomingReturnsOnlyOpenDeadlinesWithinTheWindow_REQ017() {
        service.create(matterId, "Soon", LocalDate.now().plusDays(5), null, null);
        Deadline farAway = service.create(matterId, "Far", LocalDate.now().plusDays(30), null, null);
        service.update(firm1, farAway.id(), null, null, null, null, null); // no-op, just confirms update path works too

        List<Deadline> upcoming = service.upcoming(firm1, 14);
        assertEquals(1, upcoming.size());
        assertEquals("Soon", upcoming.get(0).title());
    }

    // --- I-40: priority ---

    @Test
    void createsADeadlineWithStandardPriorityByDefault() {
        Deadline created = service.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        assertEquals(DeadlinePriority.standard, created.priority());
    }

    @Test
    void createsADeadlineWithAnExplicitCriticalPriority() {
        Deadline created = service.create(matterId, "File response", LocalDate.of(2026, 9, 1), DeadlinePriority.critical, null);
        assertEquals(DeadlinePriority.critical, created.priority());
    }

    @Test
    void updatesJustThePriority_leavingEverythingElseUntouched() {
        Deadline created = service.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        Deadline updated = service.update(firm1, created.id(), null, null, null, DeadlinePriority.critical, null).orElseThrow();

        assertEquals(DeadlinePriority.critical, updated.priority());
        assertEquals("File response", updated.title());
        assertEquals(DeadlineStatus.open, updated.status());
    }

    @Test
    void priorityTagSurvivesMarkingAsCompleteOrGoingOverdue() {
        // Critical priority is independent of status — completing (or leaving
        // overdue) a Deadline must never silently clear it.
        Deadline created = service.create(matterId, "File response", LocalDate.now().plusDays(1), DeadlinePriority.critical, null);
        Deadline completed = service.update(firm1, created.id(), null, null, DeadlineStatus.complete, null, null).orElseThrow();
        assertEquals(DeadlinePriority.critical, completed.priority());
    }
}
