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
            Boolean lowConfidence,
            Boolean pinned) {
    }

    public record ChatHistoryDto(List<ChatMessageDto> messages) {
    }

    /** I-34: a dedicated, minimal response shape — the pin toggle doesn't touch citations, so reusing the full ChatMessageDto would just leave that field null and imply more than actually changed. */
    public record PinToggleDto(UUID id, boolean pinned) {
    }
}
