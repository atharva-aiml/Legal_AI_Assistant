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
    public record CitationDto(UUID id, UUID documentId, String fileName, Integer pageNumber, String section, String excerpt) {
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
            // RAG-Pipeline-Development-History.md gap #7: true when every Ready chunk
            // was considered (a genuine completeness guarantee), false when ranked
            // retrieval was used instead (best-effort). Null on history responses,
            // same as lowConfidence — both are ephemeral, computed only for the
            // question that produced them, not persisted.
            Boolean fullContext,
            Boolean pinned,
            // Edit-a-previous-message branching: null for a root-level message.
            String parentId,
            // Ordered ids of every message sharing this message's parentId, itself
            // included — a "‹ 2/3 ›" edit-arrow UI is built directly from this list
            // (index/count derived on the frontend, not sent as a separate field).
            List<String> siblingIds) {
    }

    public record ChatHistoryDto(List<ChatMessageDto> messages) {
    }

    /** I-34: a dedicated, minimal response shape — the pin toggle doesn't touch citations, so reusing the full ChatMessageDto would just leave that field null and imply more than actually changed. */
    public record PinToggleDto(UUID id, boolean pinned) {
    }
}
