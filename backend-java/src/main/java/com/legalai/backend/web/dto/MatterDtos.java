package com.legalai.backend.web.dto;

import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.Matter;
import com.legalai.backend.web.dto.DeadlineDtos.DeadlineResponse;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public class MatterDtos {
    public record CreateMatterRequest(String client_id, String title) {
    }

    public record RenameMatterRequest(String title) {
    }

    public record MatterResponse(
            UUID id,
            UUID firmId,
            UUID clientId,
            String title,
            String status,
            Instant closedAt,
            Instant createdAt,
            Instant updatedAt) {
        public static MatterResponse from(Matter m) {
            return new MatterResponse(m.id(), m.firmId(), m.clientId(), m.title(), m.status().name(), m.closedAt(), m.createdAt(), m.updatedAt());
        }
    }

    /** BR-003's 409: not a plain ApiError since the caller needs the specific blocking Deadlines, not just a message. */
    public record OpenDeadlinesError(ErrorWithDeadlines error) {
        public record ErrorWithDeadlines(String code, String message, List<DeadlineResponse> openDeadlines) {
        }

        public static OpenDeadlinesError of(String message, List<Deadline> openDeadlines) {
            return new OpenDeadlinesError(new ErrorWithDeadlines(
                    "OPEN_DEADLINES", message, openDeadlines.stream().map(DeadlineResponse::from).toList()));
        }
    }
}
