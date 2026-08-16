package com.legalai.backend.application.chat;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Mirrors the JSON shape Python's chat router (SD-005) returns — Java owns
 * no chat domain model of its own here, it just relays what Python already
 * built and persisted (System Architecture §2's module-ownership table:
 * chat_messages/citations belong to Python, not Java).
 */
public class ChatDtos {
    public record CitationDto(UUID id, UUID documentId, String fileName, Integer pageNumber, String excerpt) {
    }

    public record ChatMessageDto(
            UUID id,
            UUID matterId,
            UUID lawyerId,
            String role,
            String content,
            Instant createdAt,
            List<CitationDto> citations,
            Boolean lowConfidence) {
    }

    public record ChatHistoryDto(List<ChatMessageDto> messages) {
    }
}
