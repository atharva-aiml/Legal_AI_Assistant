package com.legalai.backend.domain;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public record Deadline(
        UUID id,
        UUID matterId,
        String title,
        LocalDate dueDate,
        DeadlineStatus status,
        int notificationLeadDays,
        Instant createdAt,
        Instant updatedAt) {

    /** REQ-009: "default: 3 days before + day-of." */
    private static final int DEFAULT_NOTIFICATION_LEAD_DAYS = 3;

    public record NewDeadline(UUID matterId, String title, LocalDate dueDate, int notificationLeadDays) {
    }

    /**
     * BR-004: "A Deadline always has a due date and a linked Matter — it
     * cannot exist standalone." Enforced here as "matterId/dueDate are
     * required," the domain-layer half of the invariant; the real
     * repository's FK/NOT NULL constraints are the storage-layer half.
     * A new Deadline always starts "open."
     */
    public static NewDeadline create(UUID matterId, String title, LocalDate dueDate, Integer notificationLeadDays) {
        if (matterId == null) {
            throw new InvalidDeadlineException("A Deadline must belong to a Matter (BR-004).");
        }
        String trimmed = title == null ? "" : title.trim();
        if (trimmed.isEmpty()) {
            throw new InvalidDeadlineException("A Deadline title is required.");
        }
        validateDueDate(dueDate);
        int leadDays = notificationLeadDays != null ? notificationLeadDays : DEFAULT_NOTIFICATION_LEAD_DAYS;
        if (leadDays < 0) {
            throw new InvalidDeadlineException("Notification lead time can't be negative.");
        }
        return new NewDeadline(matterId, trimmed, dueDate, leadDays);
    }

    /** Same "non-empty title" invariant as creation; a due date can be rescheduled, subject to BR-009. */
    public static String validateTitle(String title) {
        String trimmed = title == null ? "" : title.trim();
        if (trimmed.isEmpty()) {
            throw new InvalidDeadlineException("A Deadline title is required.");
        }
        return trimmed;
    }

    /**
     * BR-009: "A Deadline's due date cannot be in the past — enforced at
     * creation and at edit, not just at initial entry." Shared by create()
     * and by DeadlineService.update() whenever a caller supplies a new
     * dueDate, so rescheduling to a past date is blocked the same way
     * creating one is.
     */
    public static LocalDate validateDueDate(LocalDate dueDate) {
        if (dueDate == null) {
            throw new InvalidDeadlineException("A Deadline must have a due date (BR-004).");
        }
        if (dueDate.isBefore(LocalDate.now())) {
            throw new InvalidDeadlineException("The due date can't be in the past (BR-009).");
        }
        return dueDate;
    }

    public static int validateLeadDays(int leadDays) {
        if (leadDays < 0) {
            throw new InvalidDeadlineException("Notification lead time can't be negative.");
        }
        return leadDays;
    }

    /**
     * REQ-009: "System sends a Notification ahead of an approaching
     * Deadline (default: 3 days before + day-of)." Pure function — no I/O —
     * the application-layer scanner (SD-006) is what actually persists a
     * Notification once this says today is a reminder day; whether one was
     * already sent today is a separate idempotency check, not this rule's
     * concern.
     */
    public boolean isNotificationDueOn(LocalDate today) {
        return today.equals(dueDate.minusDays(notificationLeadDays)) || today.equals(dueDate);
    }

    /**
     * BR-003: "A Matter cannot be marked Closed while it has one or more
     * open (incomplete) Deadlines." Pure function operating on
     * already-fetched Deadlines — the application layer owns fetching them
     * for a Matter; this just decides which ones are blocking.
     */
    public static List<Deadline> openOnes(List<Deadline> deadlines) {
        return deadlines.stream().filter(d -> d.status() == DeadlineStatus.open).toList();
    }
}
