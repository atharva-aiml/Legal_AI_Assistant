package com.legalai.backend.web.dto;

import com.legalai.backend.domain.Deadline;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

public class DeadlineDtos {
    public record CreateDeadlineRequest(String title, LocalDate dueDate, String priority, Integer notificationLeadDays) {
    }

    /** All fields optional — PATCH semantics, omitted fields keep their current value. */
    public record UpdateDeadlineRequest(String title, LocalDate dueDate, String status, String priority, Integer notificationLeadDays) {
    }

    public record DeadlineResponse(
            UUID id,
            UUID matterId,
            String title,
            LocalDate dueDate,
            String status,
            String priority,
            int notificationLeadDays,
            Instant createdAt,
            Instant updatedAt) {
        public static DeadlineResponse from(Deadline d) {
            return new DeadlineResponse(d.id(), d.matterId(), d.title(), d.dueDate(), d.status().name(), d.priority().name(), d.notificationLeadDays(), d.createdAt(), d.updatedAt());
        }
    }
}
