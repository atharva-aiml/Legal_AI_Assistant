package com.legalai.backend.web.dto;

import com.legalai.backend.domain.Document;

import java.time.Instant;
import java.util.UUID;

public class DocumentDtos {
    public record DocumentResponse(
            UUID id,
            UUID matterId,
            String fileName,
            String mimeType,
            long sizeBytes,
            String status,
            boolean isDraft,
            String errorMessage,
            Instant createdAt) {
        public static DocumentResponse from(Document d) {
            return new DocumentResponse(d.id(), d.matterId(), d.fileName(), d.mimeType(), d.sizeBytes(),
                    d.status().name(), d.isDraft(), d.errorMessage(), d.createdAt());
        }
    }
}
