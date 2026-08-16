package com.legalai.backend.application.document;

import com.legalai.backend.application.template.TemplateRepository;
import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.DocumentStatus;
import com.legalai.backend.domain.InvalidTemplateException;
import com.legalai.backend.domain.Template;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;

/**
 * SD-007: renders a Template with lawyer-supplied field values into a new
 * Document (is_draft=true), then hands it to the same ingestion pipeline
 * every uploaded Document goes through (REQ-015) — mirrors DocumentService
 * .upload()'s shape: validate -> store -> create row -> mark processing ->
 * trigger ingestion, with a rendered draft instead of an uploaded file as
 * the content source. Matter ownership is checked by the controller before
 * this is ever called, same as DocumentService.upload.
 */
@Service
public class DraftGenerationService {

    private final TemplateRepository templateRepository;
    private final DocumentRepository documentRepository;
    private final StorageService storage;
    private final IngestionTrigger ingestionTrigger;

    public DraftGenerationService(TemplateRepository templateRepository, DocumentRepository documentRepository,
                                   StorageService storage, IngestionTrigger ingestionTrigger) {
        this.templateRepository = templateRepository;
        this.documentRepository = documentRepository;
        this.storage = storage;
        this.ingestionTrigger = ingestionTrigger;
    }

    public static class DraftGenerationFailedException extends RuntimeException {
        public DraftGenerationFailedException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    public Document generate(UUID firmId, UUID matterId, UUID lawyerId, UUID templateId, Map<String, String> fields) {
        Template template = templateRepository.findAvailable(firmId, templateId)
                .orElseThrow(() -> new InvalidTemplateException("Template not found."));

        // Rendered (and its placeholder-completeness check) before any
        // storage I/O — same "validate before writing" ordering as
        // DocumentService.upload's mime-type check.
        String rendered = template.render(fields);
        byte[] bytes = rendered.getBytes(StandardCharsets.UTF_8);
        String fileName = template.name() + ".txt";

        String storageKey;
        try {
            storageKey = storage.store(fileName, new ByteArrayInputStream(bytes));
        } catch (IOException e) {
            throw new DraftGenerationFailedException("Couldn't save the generated draft.", e);
        }

        Document.NewDraftDocument draft = Document.createDraft(matterId, lawyerId, fileName, storageKey, "text/plain", bytes.length, template.id());
        Document created = documentRepository.createDraft(draft);
        documentRepository.updateStatus(created.id(), DocumentStatus.processing, null);
        ingestionTrigger.triggerIngestion(created.id());
        return created;
    }
}
