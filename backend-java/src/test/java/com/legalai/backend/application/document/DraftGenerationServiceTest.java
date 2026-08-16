package com.legalai.backend.application.document;

import com.legalai.backend.application.template.TemplateRepository;
import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.DocumentStatus;
import com.legalai.backend.domain.InvalidTemplateException;
import com.legalai.backend.domain.Template;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class DraftGenerationServiceTest {

    static class InMemoryTemplateRepository implements TemplateRepository {
        final List<Template> templates = new ArrayList<>();

        @Override
        public List<Template> listAvailable(UUID firmId) {
            return templates.stream().filter(t -> t.firmId() == null || t.firmId().equals(firmId)).toList();
        }

        @Override
        public Optional<Template> findAvailable(UUID firmId, UUID id) {
            return templates.stream()
                    .filter(t -> t.id().equals(id) && (t.firmId() == null || t.firmId().equals(firmId)))
                    .findFirst();
        }
    }

    static class InMemoryDocumentRepository implements DocumentRepository {
        final List<Document> documents = new ArrayList<>();

        @Override
        public Document create(Document.NewDocument r) {
            throw new UnsupportedOperationException("not needed for the draft-generation test");
        }

        @Override
        public Document createDraft(Document.NewDraftDocument r) {
            Document doc = new Document(UUID.randomUUID(), r.matterId(), r.uploadedBy(), r.fileName(), r.storageKey(),
                    r.mimeType(), r.sizeBytes(), DocumentStatus.uploading, true, r.sourceTemplateId(), null, Instant.now());
            documents.add(doc);
            return doc;
        }

        @Override
        public List<Document> listByMatter(UUID firmId, UUID matterId) {
            throw new UnsupportedOperationException("not needed for the draft-generation test");
        }

        @Override
        public Optional<Document> findById(UUID firmId, UUID id) {
            return documents.stream().filter(d -> d.id().equals(id)).findFirst();
        }

        @Override
        public void updateStatus(UUID id, DocumentStatus status, String errorMessage) {
            for (int i = 0; i < documents.size(); i++) {
                Document d = documents.get(i);
                if (d.id().equals(id)) {
                    documents.set(i, new Document(d.id(), d.matterId(), d.uploadedBy(), d.fileName(), d.storageKey(),
                            d.mimeType(), d.sizeBytes(), status, d.isDraft(), d.sourceTemplateId(), errorMessage, d.createdAt()));
                }
            }
        }

        @Override
        public boolean delete(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for the draft-generation test");
        }
    }

    static class InMemoryStorageService implements StorageService {
        final Map<String, byte[]> files = new HashMap<>();
        boolean storeCalled = false;

        @Override
        public String store(String originalFileName, InputStream content) throws IOException {
            storeCalled = true;
            String key = UUID.randomUUID().toString();
            files.put(key, content.readAllBytes());
            return key;
        }

        @Override
        public InputStream retrieve(String storageKey) {
            return new ByteArrayInputStream(files.get(storageKey));
        }

        @Override
        public void delete(String storageKey) {
            files.remove(storageKey);
        }
    }

    static class InMemoryIngestionTrigger implements IngestionTrigger {
        final List<UUID> triggered = new ArrayList<>();

        @Override
        public void triggerIngestion(UUID documentId) {
            triggered.add(documentId);
        }
    }

    private InMemoryTemplateRepository templateRepo;
    private InMemoryDocumentRepository documentRepo;
    private InMemoryStorageService storage;
    private InMemoryIngestionTrigger ingestion;
    private DraftGenerationService service;
    private final UUID firm1 = UUID.randomUUID();
    private final UUID firm2 = UUID.randomUUID();
    private final UUID matterId = UUID.randomUUID();
    private final UUID lawyerId = UUID.randomUUID();

    private Template template(UUID firmId, String body) {
        return new Template(UUID.randomUUID(), firmId, "NDA", "A test NDA", body, Instant.now());
    }

    @BeforeEach
    void setUp() {
        templateRepo = new InMemoryTemplateRepository();
        documentRepo = new InMemoryDocumentRepository();
        storage = new InMemoryStorageService();
        ingestion = new InMemoryIngestionTrigger();
        service = new DraftGenerationService(templateRepo, documentRepo, storage, ingestion);
    }

    @Test
    void generatesADraftDocumentFromATemplate_REQ015() {
        Template t = template(null, "Dear {{counterparty_name}}, re: {{matter_title}}.");
        templateRepo.templates.add(t);

        Document created = service.generate(firm1, matterId, lawyerId, t.id(),
                Map.of("counterparty_name", "Northgate Logistics", "matter_title", "Vasquez v. Northgate"));

        assertEquals(matterId, created.matterId());
        assertTrue(created.isDraft());
        assertEquals(t.id(), created.sourceTemplateId());
        // created is a snapshot from before updateStatus() runs (same shape
        // as DocumentService.upload) — check the repo's stored copy instead.
        assertEquals(DocumentStatus.processing, documentRepo.documents.get(0).status());
        assertTrue(storage.storeCalled);
        assertEquals(List.of(created.id()), ingestion.triggered);

        byte[] stored = storage.files.get(created.storageKey());
        assertEquals("Dear Northgate Logistics, re: Vasquez v. Northgate.", new String(stored, StandardCharsets.UTF_8));
    }

    @Test
    void rejectsGenerationWhenTheTemplateIsNotFound() {
        assertThrows(InvalidTemplateException.class,
                () -> service.generate(firm1, matterId, lawyerId, UUID.randomUUID(), Map.of()));
        assertFalse(storage.storeCalled);
        assertTrue(ingestion.triggered.isEmpty());
    }

    @Test
    void rejectsGenerationForAnotherFirmsCustomTemplate_BR008() {
        Template firm2Custom = template(firm2, "Body {{x}}");
        templateRepo.templates.add(firm2Custom);

        assertThrows(InvalidTemplateException.class,
                () -> service.generate(firm1, matterId, lawyerId, firm2Custom.id(), Map.of("x", "value")));
        assertFalse(storage.storeCalled);
    }

    @Test
    void rejectsGenerationWithAMissingPlaceholderValue_beforeAnyStorageIO() {
        Template t = template(null, "Dear {{counterparty_name}}.");
        templateRepo.templates.add(t);

        assertThrows(InvalidTemplateException.class, () -> service.generate(firm1, matterId, lawyerId, t.id(), Map.of()));

        assertFalse(storage.storeCalled, "an unresolved placeholder must never reach storage I/O");
        assertTrue(documentRepo.documents.isEmpty());
        assertTrue(ingestion.triggered.isEmpty());
    }

    @Test
    void generatedFileNameIsBasedOnTheTemplateName() {
        Template t = template(null, "No placeholders.");
        templateRepo.templates.add(t);

        Document created = service.generate(firm1, matterId, lawyerId, t.id(), Map.of());

        assertEquals("NDA.txt", created.fileName());
    }
}
