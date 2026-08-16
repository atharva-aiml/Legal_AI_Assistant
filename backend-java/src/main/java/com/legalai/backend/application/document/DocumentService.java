package com.legalai.backend.application.document;

import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.DocumentStatus;
import com.legalai.backend.domain.InvalidDocumentException;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class DocumentService {

    private final DocumentRepository repository;
    private final StorageService storage;
    private final IngestionTrigger ingestionTrigger;

    public DocumentService(DocumentRepository repository, StorageService storage, IngestionTrigger ingestionTrigger) {
        this.repository = repository;
        this.storage = storage;
        this.ingestionTrigger = ingestionTrigger;
    }

    public static class UploadFailedException extends RuntimeException {
        public UploadFailedException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /**
     * Stores the file, persists the Document row, then fires ingestion
     * (SD-004) without waiting for it — REQ-004's "queryable after upload"
     * is a property of the async pipeline, not of this call returning.
     */
    public Document upload(UUID matterId, UUID uploadedBy, String fileName, String mimeType, long sizeBytes, InputStream content) {
        // Validated before any storage I/O — an unsupported type never gets
        // written to storage in the first place, so there's no orphan file
        // to clean up if Document.create's validation fails below.
        if (!Document.isSupportedMimeType(mimeType)) {
            throw new InvalidDocumentException("Unsupported file type — only PDF, DOCX, and common image formats are accepted (REQ-003).");
        }

        String storageKey;
        try {
            storageKey = storage.store(fileName, content);
        } catch (IOException e) {
            throw new UploadFailedException("Couldn't store the uploaded file.", e);
        }

        Document.NewDocument draft = Document.create(matterId, uploadedBy, fileName, storageKey, mimeType, sizeBytes);
        Document created = repository.create(draft);
        repository.updateStatus(created.id(), DocumentStatus.processing, null);
        ingestionTrigger.triggerIngestion(created.id());
        return created;
    }

    public List<Document> list(UUID firmId, UUID matterId) {
        return repository.listByMatter(firmId, matterId);
    }

    public Optional<Document> get(UUID firmId, UUID id) {
        return repository.findById(firmId, id);
    }

    public Optional<InputStream> download(UUID firmId, UUID id) {
        Optional<Document> doc = repository.findById(firmId, id);
        if (doc.isEmpty()) return Optional.empty();
        try {
            return Optional.of(storage.retrieve(doc.get().storageKey()));
        } catch (IOException e) {
            throw new UploadFailedException("Couldn't read the stored file.", e);
        }
    }

    /**
     * REQ-027 — unrestricted by explicit user decision: not gated on
     * Matter status, unlike BR-007's "closed Matter data is retained"
     * language (that rule isn't reachable yet — Matter-closing is V0.5).
     * File is deleted first, then the row (whose deletion cascades
     * document_chunks at the DB level, System Architecture §3) — if row
     * deletion somehow failed after the file was gone, that's a safer
     * failure mode than an orphaned file with no DB record pointing at it.
     */
    public boolean delete(UUID firmId, UUID id) {
        Optional<Document> doc = repository.findById(firmId, id);
        if (doc.isEmpty()) return false;

        try {
            storage.delete(doc.get().storageKey());
        } catch (IOException e) {
            throw new UploadFailedException("Couldn't delete the stored file.", e);
        }

        return repository.delete(firmId, id);
    }
}
