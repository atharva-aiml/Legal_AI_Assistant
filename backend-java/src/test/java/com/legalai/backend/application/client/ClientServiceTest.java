package com.legalai.backend.application.client;

import com.legalai.backend.application.chat.ChatMessageRepository;
import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.application.document.DocumentRepository;
import com.legalai.backend.application.document.DocumentService;
import com.legalai.backend.application.document.IngestionTrigger;
import com.legalai.backend.application.document.StorageService;
import com.legalai.backend.application.matter.MatterRepository;
import com.legalai.backend.application.matter.MatterService;
import com.legalai.backend.application.matterview.MatterViewRepository;
import com.legalai.backend.domain.Client;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.DocumentStatus;
import com.legalai.backend.domain.InvalidClientException;
import com.legalai.backend.domain.Matter;
import com.legalai.backend.domain.MatterStatus;
import com.legalai.backend.domain.MatterView;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class ClientServiceTest {

    /** In-memory fake — satisfies the same ClientRepository port the real JPA-backed one does. */
    static class InMemoryClientRepository implements ClientRepository {
        final List<Client> clients = new ArrayList<>();

        @Override
        public Client create(Client.NewClient record) {
            Client client = new Client(UUID.randomUUID(), record.firmId(), record.name(), record.contactEmail(), record.contactPhone(), record.notes(), Instant.now(), Instant.now());
            clients.add(client);
            return client;
        }

        @Override
        public List<Client> listByFirm(UUID firmId) {
            return clients.stream().filter(c -> c.firmId().equals(firmId)).toList();
        }

        @Override
        public Optional<Client> findById(UUID firmId, UUID id) {
            return clients.stream().filter(c -> c.firmId().equals(firmId) && c.id().equals(id)).findFirst();
        }

        @Override
        public Optional<Client> update(UUID firmId, UUID id, String name, String contactEmail, String contactPhone, String notes) {
            for (int i = 0; i < clients.size(); i++) {
                Client c = clients.get(i);
                if (c.firmId().equals(firmId) && c.id().equals(id)) {
                    Client updated = new Client(c.id(), c.firmId(), name, contactEmail, contactPhone, notes, c.createdAt(), Instant.now());
                    clients.set(i, updated);
                    return Optional.of(updated);
                }
            }
            return Optional.empty();
        }

        @Override
        public boolean delete(UUID firmId, UUID id) {
            return clients.removeIf(c -> c.firmId().equals(firmId) && c.id().equals(id));
        }
    }

    /** In-memory fake — satisfies the same MatterRepository port the real JPA-backed one does. */
    static class InMemoryMatterRepository implements MatterRepository {
        final List<Matter> matters = new ArrayList<>();

        @Override
        public Matter create(Matter.NewMatter record) {
            Matter matter = new Matter(UUID.randomUUID(), record.firmId(), record.clientId(), record.title(), record.status(), null, Instant.now(), Instant.now());
            matters.add(matter);
            return matter;
        }

        @Override
        public List<Matter> listByFirm(UUID firmId) {
            return matters.stream().filter(m -> m.firmId().equals(firmId)).toList();
        }

        @Override
        public List<Matter> listByClient(UUID firmId, UUID clientId) {
            return matters.stream().filter(m -> m.firmId().equals(firmId) && m.clientId().equals(clientId)).toList();
        }

        @Override
        public Optional<Matter> findById(UUID firmId, UUID id) {
            return matters.stream().filter(m -> m.firmId().equals(firmId) && m.id().equals(id)).findFirst();
        }

        @Override
        public Optional<Matter> updateTitle(UUID firmId, UUID id, String title) {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public Optional<Matter> close(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public Optional<Matter> reopen(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public boolean delete(UUID firmId, UUID id) {
            return matters.removeIf(m -> m.firmId().equals(firmId) && m.id().equals(id));
        }

        Matter seed(UUID firmId, UUID clientId) {
            Matter matter = new Matter(UUID.randomUUID(), firmId, clientId, "Matter", MatterStatus.open, null, Instant.now(), Instant.now());
            matters.add(matter);
            return matter;
        }
    }

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
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
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
            // not needed for ClientServiceTest
        }

        @Override
        public boolean delete(UUID firmId, UUID id) {
            return documents.removeIf(d -> d.id().equals(id));
        }
    }

    static class InMemoryStorageService implements StorageService {
        final Map<String, byte[]> files = new HashMap<>();

        @Override
        public String store(String originalFileName, InputStream content) throws IOException {
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

    static class NoopIngestionTrigger implements IngestionTrigger {
        @Override
        public void triggerIngestion(UUID documentId) {
            // not needed for ClientServiceTest
        }
    }

    /** Minimal fake — ClientService only ever calls listByMatter/deleteByMatter on this port. */
    static class InMemoryDeadlineRepository implements DeadlineRepository {
        final List<Deadline> deadlines = new ArrayList<>();

        @Override
        public Deadline create(Deadline.NewDeadline record) {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public List<Deadline> listByMatter(UUID firmId, UUID matterId) {
            return deadlines.stream().filter(d -> d.matterId().equals(matterId)).toList();
        }

        @Override
        public Optional<Deadline> findById(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, DeadlinePriority priority, int notificationLeadDays) {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public List<Deadline> listUpcoming(UUID firmId, int days) {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public List<DeadlineWithFirm> listAllOpenWithFirm() {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public void deleteByMatter(UUID matterId) {
            deadlines.removeIf(d -> d.matterId().equals(matterId));
        }
    }

    static class InMemoryChatMessageRepository implements ChatMessageRepository {
        /** matterId -> how many "rows" are seeded for it, standing in for real chat_messages content Java never reads. */
        final Map<UUID, Integer> messageCountByMatter = new HashMap<>();

        @Override
        public void deleteByMatter(UUID matterId) {
            messageCountByMatter.remove(matterId);
        }
    }

    static class InMemoryMatterViewRepository implements MatterViewRepository {
        final List<MatterView> views = new ArrayList<>();

        @Override
        public void recordView(UUID lawyerId, UUID matterId) {
            views.add(new MatterView(lawyerId, matterId, Instant.now()));
        }

        @Override
        public List<MatterView> listRecentlyViewed(UUID lawyerId, int limit) {
            throw new UnsupportedOperationException("not needed for ClientServiceTest");
        }

        @Override
        public void deleteByMatter(UUID matterId) {
            views.removeIf(v -> v.matterId().equals(matterId));
        }
    }

    private InMemoryClientRepository repo;
    private InMemoryMatterRepository matterRepo;
    private InMemoryDocumentRepository documentRepo;
    private InMemoryStorageService storage;
    private InMemoryDeadlineRepository deadlineRepo;
    private InMemoryChatMessageRepository chatMessageRepo;
    private InMemoryMatterViewRepository matterViewRepo;
    private ClientService service;
    private final UUID firm1 = UUID.randomUUID();
    private final UUID firm2 = UUID.randomUUID();

    /**
     * ClientService now depends on MatterService (not the 4 repositories
     * directly) — same shape as ClientService depending on a real
     * DocumentService built from in-memory fakes below: construct the real
     * MatterService against in-memory fakes of its own dependencies, then
     * hand that real service into ClientService, rather than faking
     * MatterService itself.
     */
    @BeforeEach
    void setUp() {
        repo = new InMemoryClientRepository();
        matterRepo = new InMemoryMatterRepository();
        documentRepo = new InMemoryDocumentRepository();
        storage = new InMemoryStorageService();
        deadlineRepo = new InMemoryDeadlineRepository();
        chatMessageRepo = new InMemoryChatMessageRepository();
        matterViewRepo = new InMemoryMatterViewRepository();
        DocumentService documentService = new DocumentService(documentRepo, storage, new NoopIngestionTrigger());
        MatterService matterService = new MatterService(matterRepo, deadlineRepo, documentService, chatMessageRepo, matterViewRepo);
        service = new ClientService(repo, matterRepo, matterService);
    }

    @Test
    void updatesAClientsFields() {
        Client created = service.create(firm1, "Old Name", "old@b.com", null, null);
        Client updated = service.update(firm1, created.id(), "New Name", "new@b.com", "555-0001", "Updated notes").orElseThrow();

        assertEquals("New Name", updated.name());
        assertEquals("new@b.com", updated.contactEmail());
        assertEquals("555-0001", updated.contactPhone());
        assertEquals("Updated notes", updated.notes());
    }

    @Test
    void updatePersistsInTheRepository_notJustTheReturnedValue() {
        Client created = service.create(firm1, "Old Name", null, null, null);
        service.update(firm1, created.id(), "New Name", null, null, null);

        assertEquals("New Name", service.get(firm1, created.id()).orElseThrow().name());
    }

    @Test
    void rejectsUpdatingToAnEmptyName_beforeEverTouchingTheRepository() {
        Client created = service.create(firm1, "Old Name", null, null, null);
        assertThrows(InvalidClientException.class, () -> service.update(firm1, created.id(), "   ", null, null, null));

        assertEquals("Old Name", service.get(firm1, created.id()).orElseThrow().name());
    }

    @Test
    void updatingAClientOutsideTheCallersFirmReturnsEmptyNotAnError_BR008() {
        Client created = service.create(firm1, "Private Client", null, null, null);
        assertTrue(service.update(firm2, created.id(), "Hijacked Name", null, null, null).isEmpty());
        assertEquals("Private Client", service.get(firm1, created.id()).orElseThrow().name());
    }

    // --- deleteCascade: irreversible cascade delete ---

    @Test
    void deleteCascadeRemovesTheClientItselfWhenItHasNoMattersAtAll() {
        Client created = service.create(firm1, "Empty Client", null, null, null);

        assertTrue(service.deleteCascade(firm1, created.id()));

        assertTrue(service.get(firm1, created.id()).isEmpty());
        assertTrue(repo.clients.isEmpty());
    }

    @Test
    void deleteCascadeRemovesEveryMatterUnderTheClient() {
        Client created = service.create(firm1, "Client With Matters", null, null, null);
        Matter matter1 = matterRepo.seed(firm1, created.id());
        Matter matter2 = matterRepo.seed(firm1, created.id());

        assertTrue(service.deleteCascade(firm1, created.id()));

        assertTrue(matterRepo.findById(firm1, matter1.id()).isEmpty());
        assertTrue(matterRepo.findById(firm1, matter2.id()).isEmpty());
        assertTrue(matterRepo.matters.isEmpty());
    }

    @Test
    void deleteCascadeDeletesEachDocumentThroughDocumentService_soStoredFilesAreCleanedUpToo() {
        Client created = service.create(firm1, "Client With Docs", null, null, null);
        Matter matter = matterRepo.seed(firm1, created.id());
        Document doc1 = documentRepo.create(new Document.NewDocument(matter.id(), UUID.randomUUID(), "a.pdf", "keyA", "application/pdf", 10));
        Document doc2 = documentRepo.create(new Document.NewDocument(matter.id(), UUID.randomUUID(), "b.pdf", "keyB", "application/pdf", 20));
        storage.files.put("keyA", "hello".getBytes());
        storage.files.put("keyB", "world".getBytes());

        service.deleteCascade(firm1, created.id());

        assertTrue(documentRepo.documents.isEmpty(), "Document rows must be gone");
        assertFalse(storage.files.containsKey("keyA"), "stored file for doc1 must be cleaned up, not orphaned");
        assertFalse(storage.files.containsKey("keyB"), "stored file for doc2 must be cleaned up, not orphaned");
    }

    @Test
    void deleteCascadeRemovesDeadlinesForEveryMatter() {
        Client created = service.create(firm1, "Client With Deadlines", null, null, null);
        Matter matter = matterRepo.seed(firm1, created.id());
        deadlineRepo.deadlines.add(new Deadline(UUID.randomUUID(), matter.id(), "File response", LocalDate.now(), DeadlineStatus.open, DeadlinePriority.standard, 3, Instant.now(), Instant.now()));

        service.deleteCascade(firm1, created.id());

        assertTrue(deadlineRepo.deadlines.isEmpty());
    }

    @Test
    void deleteCascadeRemovesChatHistoryForEveryMatter() {
        Client created = service.create(firm1, "Client With Chat", null, null, null);
        Matter matter = matterRepo.seed(firm1, created.id());
        chatMessageRepo.messageCountByMatter.put(matter.id(), 5);

        service.deleteCascade(firm1, created.id());

        assertFalse(chatMessageRepo.messageCountByMatter.containsKey(matter.id()));
    }

    @Test
    void deleteCascadeRemovesMatterViewsForEveryMatter() {
        Client created = service.create(firm1, "Client With Recent Views", null, null, null);
        Matter matter = matterRepo.seed(firm1, created.id());
        matterViewRepo.recordView(UUID.randomUUID(), matter.id());

        service.deleteCascade(firm1, created.id());

        assertTrue(matterViewRepo.views.isEmpty());
    }

    @Test
    void deleteCascadeReturnsFalseForAnUnknownClient() {
        assertFalse(service.deleteCascade(firm1, UUID.randomUUID()));
    }

    @Test
    void deleteCascadeOnAClientOutsideTheCallersFirmReturnsFalseAndDeletesNothing_BR008() {
        Client created = service.create(firm1, "Private Client", null, null, null);
        Matter matter = matterRepo.seed(firm1, created.id());
        Document doc = documentRepo.create(new Document.NewDocument(matter.id(), UUID.randomUUID(), "a.pdf", "keyA", "application/pdf", 10));
        storage.files.put("keyA", "hello".getBytes());
        deadlineRepo.deadlines.add(new Deadline(UUID.randomUUID(), matter.id(), "File response", LocalDate.now(), DeadlineStatus.open, DeadlinePriority.standard, 3, Instant.now(), Instant.now()));

        // firm2 attempting to delete firm1's Client — must 404-equivalent (false), not leak existence via a partial delete.
        assertFalse(service.deleteCascade(firm2, created.id()));

        assertTrue(service.get(firm1, created.id()).isPresent(), "the Client must be untouched");
        assertTrue(matterRepo.findById(firm1, matter.id()).isPresent(), "its Matter must be untouched");
        assertTrue(documentRepo.documents.stream().anyMatch(d -> d.id().equals(doc.id())), "its Document must be untouched");
        assertTrue(storage.files.containsKey("keyA"), "its stored file must be untouched");
        assertFalse(deadlineRepo.deadlines.isEmpty(), "its Deadlines must be untouched");
    }
}
