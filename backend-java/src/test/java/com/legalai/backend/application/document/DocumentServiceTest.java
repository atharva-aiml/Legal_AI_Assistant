package com.legalai.backend.application.document;

import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.DocumentStatus;
import com.legalai.backend.domain.InvalidDocumentException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.time.Instant;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class DocumentServiceTest {

    /**
     * In-memory fake. Real BR-008 isolation for Documents is enforced via a
     * SQL JOIN to `matters` in the real repository (Document has no firm_id
     * column of its own — only matter_id) — an in-memory fake can't
     * meaningfully replicate that join, so isolation is instead proven at
     * the live-regression level (like V0.2's cross-firm 404 check).
     */
    static class InMemoryDocumentRepository implements DocumentRepository {
        final List<Document> documents = new ArrayList<>();

        @Override
        public Document create(Document.NewDocument r) {
            Document doc = new Document(UUID.randomUUID(), r.matterId(), r.uploadedBy(), r.fileName(), r.storageKey(),
                    r.mimeType(), r.sizeBytes(), DocumentStatus.uploading, false, null, null, Instant.now());
            documents.add(doc);
            return doc;
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
            return documents.stream().filter(d -> d.matterId().equals(matterId)).toList();
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
            return documents.removeIf(d -> d.id().equals(id));
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

    private InMemoryDocumentRepository repo;
    private InMemoryStorageService storage;
    private InMemoryIngestionTrigger ingestion;
    private DocumentService service;
    private final UUID matterId = UUID.randomUUID();
    private final UUID lawyerId = UUID.randomUUID();
    private final UUID firmId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryDocumentRepository();
        storage = new InMemoryStorageService();
        ingestion = new InMemoryIngestionTrigger();
        service = new DocumentService(repo, storage, ingestion);
    }

    @Test
    void uploadStoresTheFileCreatesTheDocumentAndTriggersIngestion() {
        InputStream content = new ByteArrayInputStream("%PDF-1.4 fake content".getBytes());
        Document created = service.upload(matterId, lawyerId, "lease.pdf", "application/pdf", 21, content);

        assertEquals(matterId, created.matterId());
        assertTrue(storage.storeCalled);
        assertEquals(1, repo.documents.size());
        // upload() advances status to 'processing' right after storing, before ingestion runs (REQ-004).
        assertEquals(DocumentStatus.processing, repo.documents.get(0).status());
        assertEquals(List.of(created.id()), ingestion.triggered);
    }

    @Test
    void rejectsAnUnsupportedMimeTypeBeforeTouchingStorage_REQ003() {
        InputStream content = new ByteArrayInputStream("bad".getBytes());
        assertThrows(InvalidDocumentException.class,
                () -> service.upload(matterId, lawyerId, "malware.exe", "application/x-msdownload", 3, content));

        assertFalse(storage.storeCalled, "an unsupported type must never reach storage I/O");
        assertTrue(repo.documents.isEmpty());
        assertTrue(ingestion.triggered.isEmpty());
    }

    @Test
    void listsDocumentsForAMatter() {
        service.upload(matterId, lawyerId, "a.pdf", "application/pdf", 3, new ByteArrayInputStream("abc".getBytes()));
        UUID otherMatter = UUID.randomUUID();
        service.upload(otherMatter, lawyerId, "b.pdf", "application/pdf", 3, new ByteArrayInputStream("abc".getBytes()));

        List<Document> forMatter = service.list(firmId, matterId);
        assertEquals(1, forMatter.size());
        assertEquals("a.pdf", forMatter.get(0).fileName());
    }

    @Test
    void getReturnsEmptyForAnUnknownDocument() {
        assertTrue(service.get(firmId, UUID.randomUUID()).isEmpty());
    }

    @Test
    void downloadReturnsTheExactStoredBytes() throws IOException {
        Document created = service.upload(matterId, lawyerId, "a.pdf", "application/pdf", 5, new ByteArrayInputStream("hello".getBytes()));
        Optional<InputStream> stream = service.download(firmId, created.id());
        assertTrue(stream.isPresent());
        assertArrayEquals("hello".getBytes(), stream.get().readAllBytes());
    }

    @Test
    void deleteRemovesTheDocumentAndItsStoredFile_REQ027() {
        Document created = service.upload(matterId, lawyerId, "a.pdf", "application/pdf", 5, new ByteArrayInputStream("hello".getBytes()));
        String storageKey = created.storageKey();
        assertTrue(storage.files.containsKey(storageKey));

        boolean deleted = service.delete(firmId, created.id());

        assertTrue(deleted);
        assertTrue(repo.documents.isEmpty());
        assertFalse(storage.files.containsKey(storageKey), "the stored file must be removed too, not just the DB row");
        assertTrue(service.get(firmId, created.id()).isEmpty());
    }

    @Test
    void deleteReturnsFalseForAnUnknownDocument() {
        assertFalse(service.delete(firmId, UUID.randomUUID()));
    }

    @Test
    void deleteIsUnrestrictedByMatterStatus_explicitUserDecision() {
        // No Matter lookup happens in DocumentService.delete at all — this
        // test documents that choice as intentional (REQ-027 addendum),
        // not an oversight, so a future change doesn't "fix" it by accident.
        Document created = service.upload(matterId, lawyerId, "a.pdf", "application/pdf", 5, new ByteArrayInputStream("hello".getBytes()));
        assertTrue(service.delete(firmId, created.id()));
    }
}
