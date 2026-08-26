package com.legalai.backend.application.matter;

import com.legalai.backend.application.chat.ChatMessageRepository;
import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.application.document.DocumentRepository;
import com.legalai.backend.application.document.DocumentService;
import com.legalai.backend.application.document.IngestionTrigger;
import com.legalai.backend.application.document.StorageService;
import com.legalai.backend.application.matterview.MatterViewRepository;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.DocumentStatus;
import com.legalai.backend.domain.InvalidMatterException;
import com.legalai.backend.domain.Matter;
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

/**
 * Direct port of the original TypeScript matter-use-cases.test.ts — same
 * in-memory-fake approach, same cases, now exercising MatterService instead
 * of four separate use-case functions (Java-idiomatic consolidation, see
 * MatterService's class comment).
 */
class MatterServiceTest {

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
            for (int i = 0; i < matters.size(); i++) {
                Matter m = matters.get(i);
                if (m.firmId().equals(firmId) && m.id().equals(id)) {
                    Matter renamed = new Matter(m.id(), m.firmId(), m.clientId(), title, m.status(), m.closedAt(), m.createdAt(), Instant.now());
                    matters.set(i, renamed);
                    return Optional.of(renamed);
                }
            }
            return Optional.empty();
        }

        @Override
        public Optional<Matter> close(UUID firmId, UUID id) {
            for (int i = 0; i < matters.size(); i++) {
                Matter m = matters.get(i);
                if (m.firmId().equals(firmId) && m.id().equals(id)) {
                    Matter closed = new Matter(m.id(), m.firmId(), m.clientId(), m.title(), com.legalai.backend.domain.MatterStatus.closed, Instant.now(), m.createdAt(), Instant.now());
                    matters.set(i, closed);
                    return Optional.of(closed);
                }
            }
            return Optional.empty();
        }

        @Override
        public Optional<Matter> reopen(UUID firmId, UUID id) {
            for (int i = 0; i < matters.size(); i++) {
                Matter m = matters.get(i);
                if (m.firmId().equals(firmId) && m.id().equals(id)) {
                    Matter reopened = new Matter(m.id(), m.firmId(), m.clientId(), m.title(), com.legalai.backend.domain.MatterStatus.open, null, m.createdAt(), Instant.now());
                    matters.set(i, reopened);
                    return Optional.of(reopened);
                }
            }
            return Optional.empty();
        }

        @Override
        public boolean delete(UUID firmId, UUID id) {
            return matters.removeIf(m -> m.firmId().equals(firmId) && m.id().equals(id));
        }
    }

    /** Minimal fake — MatterService only ever calls listByMatter on this port. */
    static class InMemoryDeadlineRepository implements DeadlineRepository {
        final List<Deadline> deadlines = new ArrayList<>();

        @Override
        public Deadline create(Deadline.NewDeadline record) {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public List<Deadline> listByMatter(UUID firmId, UUID matterId) {
            return deadlines.stream().filter(d -> d.matterId().equals(matterId)).toList();
        }

        @Override
        public Optional<Deadline> findById(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, DeadlinePriority priority, int notificationLeadDays) {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public List<Deadline> listUpcoming(UUID firmId, int days) {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public List<DeadlineWithFirm> listAllOpenWithFirm() {
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public void deleteByMatter(UUID matterId) {
            deadlines.removeIf(d -> d.matterId().equals(matterId));
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
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
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
            // not needed for MatterServiceTest
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
            // not needed for MatterServiceTest
        }
    }

    /** Minimal fake — MatterService only ever calls deleteByMatter on this port. */
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
            throw new UnsupportedOperationException("not needed for MatterServiceTest");
        }

        @Override
        public void deleteByMatter(UUID matterId) {
            views.removeIf(v -> v.matterId().equals(matterId));
        }
    }

    private InMemoryMatterRepository repo;
    private InMemoryDeadlineRepository deadlineRepo;
    private InMemoryDocumentRepository documentRepo;
    private InMemoryStorageService storage;
    private InMemoryChatMessageRepository chatMessageRepo;
    private InMemoryMatterViewRepository matterViewRepo;
    private MatterService service;
    private final UUID firm1 = UUID.randomUUID();
    private final UUID firm2 = UUID.randomUUID();
    private final UUID client1 = UUID.randomUUID();
    private final UUID client2 = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryMatterRepository();
        deadlineRepo = new InMemoryDeadlineRepository();
        documentRepo = new InMemoryDocumentRepository();
        storage = new InMemoryStorageService();
        chatMessageRepo = new InMemoryChatMessageRepository();
        matterViewRepo = new InMemoryMatterViewRepository();
        DocumentService documentService = new DocumentService(documentRepo, storage, new NoopIngestionTrigger());
        service = new MatterService(repo, deadlineRepo, documentService, chatMessageRepo, matterViewRepo);
    }

    @Test
    void createsAMatterAndPersistsItInTheRepository() {
        Matter matter = service.create(firm1, client1, "New Case");
        assertNotNull(matter.id());
        assertEquals(1, repo.matters.size());
    }

    @Test
    void rejectsAnInvalidMatterBeforeEverTouchingTheRepository() {
        assertThrows(InvalidMatterException.class, () -> service.create(firm1, null, "No Client"));
        assertEquals(0, repo.matters.size());
    }

    @Test
    void listsOnlyMattersBelongingToTheRequestedFirm_BR008() {
        service.create(firm1, client1, "Firm 1 Matter");
        service.create(firm2, client2, "Firm 2 Matter");

        List<Matter> firm1Matters = service.list(firm1, null, null);
        assertEquals(1, firm1Matters.size());
        assertEquals("Firm 1 Matter", firm1Matters.get(0).title());
    }

    @Test
    void listsOnlyMattersForAGivenClientWithinAFirm() {
        service.create(firm1, client1, "Client 1 Matter");
        service.create(firm1, client2, "Client 2 Matter");

        List<Matter> client1Matters = service.list(firm1, client1, null);
        assertEquals(1, client1Matters.size());
        assertEquals("Client 1 Matter", client1Matters.get(0).title());
    }

    // --- I-23: status filter ---

    @Test
    void filtersByStatus_WhenGiven() {
        Matter open = service.create(firm1, client1, "Open Matter");
        Matter toClose = service.create(firm1, client1, "Closed Matter");
        service.close(firm1, toClose.id());

        List<Matter> openOnly = service.list(firm1, null, com.legalai.backend.domain.MatterStatus.open);
        assertEquals(1, openOnly.size());
        assertEquals(open.id(), openOnly.get(0).id());

        List<Matter> closedOnly = service.list(firm1, null, com.legalai.backend.domain.MatterStatus.closed);
        assertEquals(1, closedOnly.size());
        assertEquals(toClose.id(), closedOnly.get(0).id());
    }

    @Test
    void combinesClientAndStatusFilters() {
        Matter c1Open = service.create(firm1, client1, "Client1 Open");
        Matter c1Closed = service.create(firm1, client1, "Client1 Closed");
        service.close(firm1, c1Closed.id());
        service.create(firm1, client2, "Client2 Open");

        List<Matter> result = service.list(firm1, client1, com.legalai.backend.domain.MatterStatus.open);
        assertEquals(1, result.size());
        assertEquals(c1Open.id(), result.get(0).id());
    }

    @Test
    void nullStatusReturnsMattersOfEveryStatus() {
        service.create(firm1, client1, "Open Matter");
        Matter toClose = service.create(firm1, client1, "Closed Matter");
        service.close(firm1, toClose.id());

        assertEquals(2, service.list(firm1, null, null).size());
    }

    @Test
    void returnsEmptyForAMatterOutsideTheCallersFirm_BR008() {
        Matter created = service.create(firm1, client1, "Private");
        assertTrue(service.get(firm2, created.id()).isEmpty());
    }

    @Test
    void renamesAMatter() {
        Matter created = service.create(firm1, client1, "Old Title");
        Optional<Matter> renamed = service.rename(firm1, created.id(), "New Title");
        assertEquals("New Title", renamed.orElseThrow().title());
    }

    @Test
    void rejectsRenamingToAnEmptyTitle() {
        Matter created = service.create(firm1, client1, "Old Title");
        assertThrows(InvalidMatterException.class, () -> service.rename(firm1, created.id(), "   "));
    }

    @Test
    void renamingAMatterOutsideTheCallersFirmReturnsEmptyNotAnError() {
        Matter created = service.create(firm1, client1, "Old Title");
        assertTrue(service.rename(firm2, created.id(), "Hijacked Title").isEmpty());
    }

    // --- REQ-010/BR-003: closing a Matter ---

    @Test
    void closesAMatterWithNoDeadlinesAtAll() {
        Matter created = service.create(firm1, client1, "No Deadlines");
        Matter closed = service.close(firm1, created.id()).orElseThrow();
        assertEquals(com.legalai.backend.domain.MatterStatus.closed, closed.status());
        assertNotNull(closed.closedAt());
    }

    @Test
    void closesAMatterWhoseDeadlinesAreAllComplete_BR003() {
        Matter created = service.create(firm1, client1, "All Done");
        deadlineRepo.deadlines.add(new Deadline(UUID.randomUUID(), created.id(), "Filed", LocalDate.now(), DeadlineStatus.complete, DeadlinePriority.standard, 3, null, null));

        Matter closed = service.close(firm1, created.id()).orElseThrow();
        assertEquals(com.legalai.backend.domain.MatterStatus.closed, closed.status());
    }

    @Test
    void blocksClosingAMatterWithAnOpenDeadline_BR003() {
        Matter created = service.create(firm1, client1, "Has Open Deadline");
        Deadline open = new Deadline(UUID.randomUUID(), created.id(), "File response", LocalDate.now().plusDays(5), DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlineRepo.deadlines.add(open);

        MatterService.MatterHasOpenDeadlinesException ex = assertThrows(
                MatterService.MatterHasOpenDeadlinesException.class,
                () -> service.close(firm1, created.id()));

        assertEquals(1, ex.openDeadlines().size());
        assertEquals("File response", ex.openDeadlines().get(0).title());
        // The Matter itself must be untouched — still open.
        assertEquals(com.legalai.backend.domain.MatterStatus.open, repo.findById(firm1, created.id()).orElseThrow().status());
    }

    @Test
    void closingAMatterOutsideTheCallersFirmReturnsEmptyNotAnError_BR008() {
        Matter created = service.create(firm1, client1, "Private");
        assertTrue(service.close(firm2, created.id()).isEmpty());
    }

    // --- I-35: reopening a Matter ---

    @Test
    void reopensAClosedMatter() {
        Matter created = service.create(firm1, client1, "Closed by mistake");
        service.close(firm1, created.id());

        Matter reopened = service.reopen(firm1, created.id()).orElseThrow();
        assertEquals(com.legalai.backend.domain.MatterStatus.open, reopened.status());
        assertNull(reopened.closedAt());
    }

    @Test
    void rejectsReopeningAMatterThatIsAlreadyOpen() {
        Matter created = service.create(firm1, client1, "Never closed");
        assertThrows(InvalidMatterException.class, () -> service.reopen(firm1, created.id()));
        // Untouched — still open, as it always was.
        assertEquals(com.legalai.backend.domain.MatterStatus.open, repo.findById(firm1, created.id()).orElseThrow().status());
    }

    @Test
    void reopeningAMatterOutsideTheCallersFirmReturnsEmptyNotAnError_BR008() {
        Matter created = service.create(firm1, client1, "Private");
        service.close(firm1, created.id());
        assertTrue(service.reopen(firm2, created.id()).isEmpty());
    }

    // --- deleteCascade: irreversible per-Matter cascade delete ---

    @Test
    void deleteCascadeRemovesTheMatterItself() {
        Matter created = service.create(firm1, client1, "No children");

        assertTrue(service.deleteCascade(firm1, created.id()));

        assertTrue(service.get(firm1, created.id()).isEmpty());
        assertTrue(repo.matters.isEmpty());
    }

    @Test
    void deleteCascadeDeletesEachDocumentThroughDocumentService_soStoredFilesAreCleanedUpToo() {
        Matter matter = service.create(firm1, client1, "Matter With Docs");
        Document doc1 = documentRepo.create(new Document.NewDocument(matter.id(), UUID.randomUUID(), "a.pdf", "keyA", "application/pdf", 10));
        Document doc2 = documentRepo.create(new Document.NewDocument(matter.id(), UUID.randomUUID(), "b.pdf", "keyB", "application/pdf", 20));
        storage.files.put("keyA", "hello".getBytes());
        storage.files.put("keyB", "world".getBytes());

        service.deleteCascade(firm1, matter.id());

        assertTrue(documentRepo.documents.isEmpty(), "Document rows must be gone");
        assertFalse(storage.files.containsKey("keyA"), "stored file for doc1 must be cleaned up, not orphaned");
        assertFalse(storage.files.containsKey("keyB"), "stored file for doc2 must be cleaned up, not orphaned");
    }

    @Test
    void deleteCascadeRemovesDeadlinesForTheMatter() {
        Matter matter = service.create(firm1, client1, "Matter With Deadlines");
        deadlineRepo.deadlines.add(new Deadline(UUID.randomUUID(), matter.id(), "File response", LocalDate.now(), DeadlineStatus.open, DeadlinePriority.standard, 3, Instant.now(), Instant.now()));

        service.deleteCascade(firm1, matter.id());

        assertTrue(deadlineRepo.deadlines.isEmpty());
    }

    @Test
    void deleteCascadeRemovesChatHistoryForTheMatter() {
        Matter matter = service.create(firm1, client1, "Matter With Chat");
        chatMessageRepo.messageCountByMatter.put(matter.id(), 5);

        service.deleteCascade(firm1, matter.id());

        assertFalse(chatMessageRepo.messageCountByMatter.containsKey(matter.id()));
    }

    @Test
    void deleteCascadeRemovesMatterViewsForTheMatter() {
        Matter matter = service.create(firm1, client1, "Matter With Recent Views");
        matterViewRepo.recordView(UUID.randomUUID(), matter.id());

        service.deleteCascade(firm1, matter.id());

        assertTrue(matterViewRepo.views.isEmpty());
    }

    @Test
    void deleteCascadeReturnsFalseForAnUnknownMatter() {
        assertFalse(service.deleteCascade(firm1, UUID.randomUUID()));
    }

    @Test
    void deleteCascadeOnAMatterOutsideTheCallersFirmReturnsFalseAndDeletesNothing_BR008() {
        Matter matter = service.create(firm1, client1, "Private Matter");
        Document doc = documentRepo.create(new Document.NewDocument(matter.id(), UUID.randomUUID(), "a.pdf", "keyA", "application/pdf", 10));
        storage.files.put("keyA", "hello".getBytes());
        deadlineRepo.deadlines.add(new Deadline(UUID.randomUUID(), matter.id(), "File response", LocalDate.now(), DeadlineStatus.open, DeadlinePriority.standard, 3, Instant.now(), Instant.now()));

        // firm2 attempting to delete firm1's Matter — must 404-equivalent (false), not leak existence via a partial delete.
        assertFalse(service.deleteCascade(firm2, matter.id()));

        assertTrue(service.get(firm1, matter.id()).isPresent(), "the Matter must be untouched");
        assertTrue(documentRepo.documents.stream().anyMatch(d -> d.id().equals(doc.id())), "its Document must be untouched");
        assertTrue(storage.files.containsKey("keyA"), "its stored file must be untouched");
        assertFalse(deadlineRepo.deadlines.isEmpty(), "its Deadlines must be untouched");
    }
}
