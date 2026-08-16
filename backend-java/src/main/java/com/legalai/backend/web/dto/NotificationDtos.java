package com.legalai.backend.web.dto;

import com.legalai.backend.domain.Notification;

import java.time.Instant;
import java.util.UUID;

public class NotificationDtos {
    public record NotificationResponse(
            UUID id,
            UUID lawyerId,
            UUID deadlineId,
            String message,
            Instant sentAt,
            Instant readAt,
            Instant createdAt) {
        public static NotificationResponse from(Notification n) {
            return new NotificationResponse(n.id(), n.lawyerId(), n.deadlineId(), n.message(), n.sentAt(), n.readAt(), n.createdAt());
        }
    }
}
