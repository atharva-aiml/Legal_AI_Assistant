package com.legalai.backend.application.notification;

import com.legalai.backend.domain.Notification;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface NotificationRepository {
    List<Notification> listByLawyer(UUID lawyerId);

    Optional<Notification> markRead(UUID lawyerId, UUID id);

    Notification create(Notification.NewNotification record);

    /**
     * SD-006 idempotency (System Architecture §7): "checks for an existing
     * Notification on that Deadline for the day before creating another, so
     * a worker restart can't double-send." Scoped per (deadline, lawyer,
     * day) rather than just (deadline, day) — a Firm can have multiple
     * Lawyers, and a scan interrupted partway through must be able to
     * resume without re-sending to lawyers who already got one.
     */
    boolean existsForDeadlineAndLawyerOnDay(UUID deadlineId, UUID lawyerId, LocalDate day);
}
