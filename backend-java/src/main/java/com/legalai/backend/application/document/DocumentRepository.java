package com.legalai.backend.application.document;

import com.legalai.backend.domain.Document;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DocumentRepository {
    Document create(Document.NewDocument record);

    /** SD-007: same write path as create(), but persists is_draft=true and source_template_id too. */
    Document createDraft(Document.NewDraftDocument record);

    List<Document> listByMatter(UUID firmId, UUID matterId);

    Optional<Document> findById(UUID firmId, UUID id);

    void updateStatus(UUID id, com.legalai.backend.domain.DocumentStatus status, String errorMessage);

    /** REQ-027. Deletes the row; document_chunks cascade at the DB level (System Architecture §3). Returns false if not found for this firm. */
    boolean delete(UUID firmId, UUID id);
}
