package com.legalai.backend.domain;

import java.time.Instant;
import java.util.Set;
import java.util.UUID;

public record Document(
        UUID id,
        UUID matterId,
        UUID uploadedBy,
        String fileName,
        String storageKey,
        String mimeType,
        long sizeBytes,
        DocumentStatus status,
        boolean isDraft,
        UUID sourceTemplateId,
        String errorMessage,
        Instant createdAt) {

    /** REQ-003: "PDF, DOCX, scanned images." */
    private static final Set<String> ALLOWED_MIME_TYPES = Set.of(
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/png",
            "image/jpeg",
            "image/tiff",
            "image/webp");

    public record NewDocument(UUID matterId, UUID uploadedBy, String fileName, String storageKey, String mimeType, long sizeBytes) {
    }

    /** SD-007: a generated draft's mime type is controlled internally (DraftGenerationService), not REQ-003's upload allow-list, so it isn't checked against {@link #ALLOWED_MIME_TYPES}. */
    public record NewDraftDocument(UUID matterId, UUID uploadedBy, String fileName, String storageKey, String mimeType, long sizeBytes, UUID sourceTemplateId) {
    }

    public static boolean isSupportedMimeType(String mimeType) {
        return mimeType != null && ALLOWED_MIME_TYPES.contains(mimeType);
    }

    /**
     * BR-002: a Document must belong to exactly one Matter — enforced here
     * as "matterId is required," the domain-layer half of the invariant;
     * the real repository's FK constraint is the storage-layer half.
     * A new Document always starts "uploading" — it becomes "processing"
     * once the file is actually stored, and "ready" only after SD-004's
     * ingestion pipeline succeeds (REQ-004) — never set directly here.
     */
    public static NewDocument create(UUID matterId, UUID uploadedBy, String fileName, String storageKey, String mimeType, long sizeBytes) {
        if (matterId == null) {
            throw new InvalidDocumentException("A Document must belong to a Matter (BR-002).");
        }
        if (uploadedBy == null) {
            throw new InvalidDocumentException("A Document must record who uploaded it.");
        }
        String trimmedName = fileName == null ? "" : fileName.trim();
        if (trimmedName.isEmpty()) {
            throw new InvalidDocumentException("A file name is required.");
        }
        if (mimeType == null || !ALLOWED_MIME_TYPES.contains(mimeType)) {
            throw new InvalidDocumentException("Unsupported file type — only PDF, DOCX, and common image formats are accepted (REQ-003).");
        }
        if (sizeBytes <= 0) {
            throw new InvalidDocumentException("Uploaded file is empty.");
        }
        if (storageKey == null || storageKey.isBlank()) {
            throw new InvalidDocumentException("A Document must have a storage location.");
        }
        return new NewDocument(matterId, uploadedBy, trimmedName, storageKey, mimeType, sizeBytes);
    }

    /**
     * SD-007: a generated draft is a Document like any other (REQ-015) —
     * same BR-002/required-fields invariants as {@link #create}, plus it
     * must record which Template produced it. Always starts "uploading"
     * just like an uploaded Document (the repository/service layer, not
     * this factory, advances it to "processing" once actually stored).
     */
    public static NewDraftDocument createDraft(UUID matterId, UUID uploadedBy, String fileName, String storageKey, String mimeType, long sizeBytes, UUID sourceTemplateId) {
        if (matterId == null) {
            throw new InvalidDocumentException("A Document must belong to a Matter (BR-002).");
        }
        if (uploadedBy == null) {
            throw new InvalidDocumentException("A Document must record who uploaded it.");
        }
        String trimmedName = fileName == null ? "" : fileName.trim();
        if (trimmedName.isEmpty()) {
            throw new InvalidDocumentException("A file name is required.");
        }
        if (mimeType == null || mimeType.isBlank()) {
            throw new InvalidDocumentException("A generated draft must have a content type.");
        }
        if (sizeBytes <= 0) {
            throw new InvalidDocumentException("Generated draft content is empty.");
        }
        if (storageKey == null || storageKey.isBlank()) {
            throw new InvalidDocumentException("A Document must have a storage location.");
        }
        if (sourceTemplateId == null) {
            throw new InvalidDocumentException("A generated draft must record which Template it came from.");
        }
        return new NewDraftDocument(matterId, uploadedBy, trimmedName, storageKey, mimeType, sizeBytes, sourceTemplateId);
    }
}
