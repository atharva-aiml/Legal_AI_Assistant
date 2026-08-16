package com.legalai.backend.application.deadline;

import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlineStatus;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Port the application layer depends on. Deadline carries no firm_id of its
 * own (only matter_id) — same shape as Document — so BR-008 isolation is
 * enforced via a join to matters in the real implementation, not a direct column.
 */
public interface DeadlineRepository {
    Deadline create(Deadline.NewDeadline record);

    List<Deadline> listByMatter(UUID firmId, UUID matterId);

    Optional<Deadline> findById(UUID firmId, UUID id);

    Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, int notificationLeadDays);

    /** REQ-017: Dashboard Upcoming widget — every open Deadline due within `days`, across all the Firm's Matters. */
    List<Deadline> listUpcoming(UUID firmId, int days);

    /**
     * SD-006 scanner only — intentionally unscoped (no firmId), since the
     * notification scan is a trusted internal system process across every
     * Firm, never reachable from a controller/API endpoint.
     */
    List<DeadlineWithFirm> listAllOpenWithFirm();

    record DeadlineWithFirm(Deadline deadline, UUID firmId) {
    }
}
