package com.legalai.backend.domain;

import java.time.Instant;
import java.util.UUID;

public record Notification(
        UUID id,
        UUID lawyerId,
        UUID deadlineId,
        String message,
        Instant sentAt,
        Instant readAt,
        Instant createdAt) {

    public record NewNotification(UUID lawyerId, UUID deadlineId, String message) {
    }

    /** REQ-009: a Notification always names a recipient Lawyer and the Deadline it's about. */
    public static NewNotification create(UUID lawyerId, UUID deadlineId, String message) {
        if (lawyerId == null) {
            throw new InvalidNotificationException("A Notification must have a recipient Lawyer.");
        }
        if (deadlineId == null) {
            throw new InvalidNotificationException("A Notification must reference a Deadline.");
        }
        String trimmed = message == null ? "" : message.trim();
        if (trimmed.isEmpty()) {
            throw new InvalidNotificationException("A Notification message is required.");
        }
        return new NewNotification(lawyerId, deadlineId, trimmed);
    }
}
