package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class DeadlineTest {

    private final UUID matterId = UUID.randomUUID();

    @Test
    void createsADeadlineWithStatusOpenByDefault() {
        Deadline.NewDeadline deadline = Deadline.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        assertEquals(matterId, deadline.matterId());
        assertEquals("File response", deadline.title());
        assertEquals(LocalDate.of(2026, 9, 1), deadline.dueDate());
    }

    @Test
    void defaultsNotificationLeadDaysToThree_REQ009() {
        Deadline.NewDeadline deadline = Deadline.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        assertEquals(3, deadline.notificationLeadDays());
    }

    @Test
    void acceptsACustomNotificationLeadTime_REQ016() {
        Deadline.NewDeadline deadline = Deadline.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, 7);
        assertEquals(7, deadline.notificationLeadDays());
    }

    @Test
    void trimsWhitespaceFromTheTitle() {
        Deadline.NewDeadline deadline = Deadline.create(matterId, "  Padded Title  ", LocalDate.of(2026, 9, 1), null, null);
        assertEquals("Padded Title", deadline.title());
    }

    @Test
    void rejectsADeadlineWithNoTitle() {
        assertThrows(InvalidDeadlineException.class, () -> Deadline.create(matterId, "   ", LocalDate.of(2026, 9, 1), null, null));
    }

    @Test
    void rejectsADeadlineWithNoMatter_BR004() {
        assertThrows(InvalidDeadlineException.class, () -> Deadline.create(null, "File response", LocalDate.of(2026, 9, 1), null, null));
    }

    @Test
    void rejectsADeadlineWithNoDueDate_BR004() {
        assertThrows(InvalidDeadlineException.class, () -> Deadline.create(matterId, "File response", null, null, null));
    }

    @Test
    void rejectsANegativeNotificationLeadTime() {
        assertThrows(InvalidDeadlineException.class, () -> Deadline.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, -1));
    }

    @Test
    void rejectsADeadlineWithADueDateInThePast_BR009() {
        assertThrows(InvalidDeadlineException.class, () -> Deadline.create(matterId, "File response", LocalDate.now().minusDays(1), null, null));
    }

    @Test
    void acceptsADeadlineDueToday_BR009() {
        Deadline.NewDeadline deadline = Deadline.create(matterId, "File response", LocalDate.now(), null, null);
        assertEquals(LocalDate.now(), deadline.dueDate());
    }

    @Test
    void validateDueDateRejectsPastDatesAndAllowsTodayOrLater_BR009() {
        assertEquals(LocalDate.now(), Deadline.validateDueDate(LocalDate.now()));
        assertEquals(LocalDate.now().plusDays(1), Deadline.validateDueDate(LocalDate.now().plusDays(1)));
        assertThrows(InvalidDeadlineException.class, () -> Deadline.validateDueDate(LocalDate.now().minusDays(1)));
    }

    @Test
    void validateTitleTrimsAndRejectsEmpty() {
        assertEquals("New Title", Deadline.validateTitle("  New Title  "));
        assertThrows(InvalidDeadlineException.class, () -> Deadline.validateTitle("   "));
    }

    @Test
    void validateLeadDaysRejectsNegative() {
        assertEquals(5, Deadline.validateLeadDays(5));
        assertThrows(InvalidDeadlineException.class, () -> Deadline.validateLeadDays(-1));
    }

    // --- I-40: priority ---

    @Test
    void defaultsPriorityToStandardWhenNotSpecified() {
        Deadline.NewDeadline deadline = Deadline.create(matterId, "File response", LocalDate.of(2026, 9, 1), null, null);
        assertEquals(DeadlinePriority.standard, deadline.priority());
    }

    @Test
    void acceptsAnExplicitCriticalPriority() {
        Deadline.NewDeadline deadline = Deadline.create(matterId, "File response", LocalDate.of(2026, 9, 1), DeadlinePriority.critical, null);
        assertEquals(DeadlinePriority.critical, deadline.priority());
    }

    @Test
    void resolvePriorityDefaultsNullToStandard() {
        assertEquals(DeadlinePriority.standard, Deadline.resolvePriority(null));
        assertEquals(DeadlinePriority.critical, Deadline.resolvePriority(DeadlinePriority.critical));
    }

    // --- REQ-009: notification timing ---

    private Deadline deadlineDueOn(LocalDate dueDate, int leadDays) {
        return new Deadline(UUID.randomUUID(), matterId, "File response", dueDate, DeadlineStatus.open, DeadlinePriority.standard, leadDays, null, null);
    }

    @Test
    void notificationIsDueOnTheLeadDaysBeforeTheDueDate_REQ009() {
        Deadline deadline = deadlineDueOn(LocalDate.of(2026, 9, 10), 3);
        assertTrue(deadline.isNotificationDueOn(LocalDate.of(2026, 9, 7)));
    }

    @Test
    void notificationIsDueOnTheDueDateItself_REQ009() {
        Deadline deadline = deadlineDueOn(LocalDate.of(2026, 9, 10), 3);
        assertTrue(deadline.isNotificationDueOn(LocalDate.of(2026, 9, 10)));
    }

    @Test
    void notificationIsNotDueOnAnUnrelatedDay() {
        Deadline deadline = deadlineDueOn(LocalDate.of(2026, 9, 10), 3);
        assertFalse(deadline.isNotificationDueOn(LocalDate.of(2026, 9, 8)));
        assertFalse(deadline.isNotificationDueOn(LocalDate.of(2026, 9, 11)));
    }

    @Test
    void notificationTimingRespectsACustomLeadTime_REQ016() {
        Deadline deadline = deadlineDueOn(LocalDate.of(2026, 9, 10), 7);
        assertTrue(deadline.isNotificationDueOn(LocalDate.of(2026, 9, 3)));
        assertFalse(deadline.isNotificationDueOn(LocalDate.of(2026, 9, 7))); // the old default's lead day, not this one's
    }

    // --- BR-003: which Deadlines block a Matter from closing ---

    @Test
    void openOnesReturnsOnlyDeadlinesStillOpen_BR003() {
        Deadline open = new Deadline(UUID.randomUUID(), matterId, "Open one", LocalDate.now(), DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        Deadline complete = new Deadline(UUID.randomUUID(), matterId, "Done one", LocalDate.now(), DeadlineStatus.complete, DeadlinePriority.standard, 3, null, null);

        List<Deadline> blocking = Deadline.openOnes(List.of(open, complete));

        assertEquals(1, blocking.size());
        assertEquals("Open one", blocking.get(0).title());
    }

    @Test
    void openOnesIsEmptyWhenEveryDeadlineIsComplete_BR003() {
        Deadline complete = new Deadline(UUID.randomUUID(), matterId, "Done one", LocalDate.now(), DeadlineStatus.complete, DeadlinePriority.standard, 3, null, null);
        assertTrue(Deadline.openOnes(List.of(complete)).isEmpty());
    }
}
