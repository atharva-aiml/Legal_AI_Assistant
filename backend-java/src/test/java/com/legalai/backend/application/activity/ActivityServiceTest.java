package com.legalai.backend.application.activity;

import com.legalai.backend.application.chat.ChatDtos.ChatHistoryDto;
import com.legalai.backend.application.chat.ChatDtos.ChatMessageDto;
import com.legalai.backend.application.chat.ChatDtos.PinToggleDto;
import com.legalai.backend.application.chat.ChatGateway;
import com.legalai.backend.application.chat.ChatService;
import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.application.document.DocumentRepository;
import com.legalai.backend.application.document.DocumentService;
import com.legalai.backend.application.deadline.DeadlineService;
import com.legalai.backend.application.document.IngestionTrigger;
import com.legalai.backend.application.document.StorageService;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.DocumentStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class ActivityServiceTest {

    static class InMemoryDocumentRepository implements DocumentRepository {
        final List<Document> documents = new ArrayList<>();

        @Override
        public Document create(Document.NewDocument record) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public Document createDraft(Document.NewDraftDocument record) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public List<Document> listByMatter(UUID firmId, UUID matterId) {
            return documents.stream().filter(d -> d.matterId().equals(matterId)).toList();
        }

        @Override
        public Optional<Document> findById(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public void updateStatus(UUID id, DocumentStatus status, String errorMessage) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public boolean delete(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }
    }

    static class InMemoryDeadlineRepository implements DeadlineRepository {
        final List<Deadline> deadlines = new ArrayList<>();

        @Override
        public Deadline create(Deadline.NewDeadline record) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public List<Deadline> listByMatter(UUID firmId, UUID matterId) {
            return deadlines.stream().filter(d -> d.matterId().equals(matterId)).toList();
        }

        @Override
        public Optional<Deadline> findById(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, DeadlinePriority priority, int notificationLeadDays) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public List<Deadline> listUpcoming(UUID firmId, int days) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public List<DeadlineWithFirm> listAllOpenWithFirm() {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }
    }

    static class NoopStorageService implements StorageService {
        @Override
        public String store(String originalFileName, java.io.InputStream content) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public java.io.InputStream retrieve(String storageKey) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public void delete(String storageKey) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }
    }

    static class NoopIngestionTrigger implements IngestionTrigger {
        @Override
        public void triggerIngestion(UUID documentId) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }
    }

    static class InMemoryChatGateway implements ChatGateway {
        ChatHistoryDto historyResponse = new ChatHistoryDto(List.of());
        RuntimeException historyException;

        @Override
        public ChatMessageDto ask(UUID matterId, UUID lawyerId, String question) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }

        @Override
        public ChatHistoryDto history(UUID matterId) {
            if (historyException != null) throw historyException;
            return historyResponse;
        }

        @Override
        public PinToggleDto togglePin(UUID matterId, UUID messageId, boolean pinned) {
            throw new UnsupportedOperationException("not needed for ActivityServiceTest");
        }
    }

    private InMemoryDocumentRepository documentRepo;
    private InMemoryDeadlineRepository deadlineRepo;
    private InMemoryChatGateway chatGateway;
    private ActivityService service;
    private final UUID firmId = UUID.randomUUID();
    private final UUID matterId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        documentRepo = new InMemoryDocumentRepository();
        deadlineRepo = new InMemoryDeadlineRepository();
        chatGateway = new InMemoryChatGateway();
        DocumentService documentService = new DocumentService(documentRepo, new NoopStorageService(), new NoopIngestionTrigger());
        DeadlineService deadlineService = new DeadlineService(deadlineRepo);
        ChatService chatService = new ChatService(chatGateway);
        service = new ActivityService(documentService, deadlineService, chatService);
    }

    @Test
    void combinesDocumentDeadlineAndChatQuestionEntriesMostRecentFirst() {
        Instant t1 = Instant.parse("2026-08-01T09:00:00Z"); // document uploaded
        Instant t2 = Instant.parse("2026-08-02T09:00:00Z"); // question asked
        Instant t3 = Instant.parse("2026-08-03T09:00:00Z"); // deadline completed (most recent)

        documentRepo.documents.add(new Document(UUID.randomUUID(), matterId, UUID.randomUUID(), "lease.pdf", "key", "application/pdf", 100, DocumentStatus.ready, false, null, null, t1));
        chatGateway.historyResponse = new ChatHistoryDto(List.of(
                new ChatMessageDto(UUID.randomUUID(), matterId, UUID.randomUUID(), "user", "What is the rent?", t2, List.of(), null, false)
        ));
        deadlineRepo.deadlines.add(new Deadline(UUID.randomUUID(), matterId, "File response", LocalDate.now(), DeadlineStatus.complete, DeadlinePriority.standard, 3, t1, t3));

        List<ActivityEntry> entries = service.forMatter(firmId, matterId);

        assertEquals(3, entries.size());
        assertEquals("deadline", entries.get(0).type());
        assertEquals("chat", entries.get(1).type());
        assertEquals("document", entries.get(2).type());
        assertTrue(entries.get(0).title().contains("completed"));
        assertTrue(entries.get(1).title().contains("What is the rent?"));
        assertTrue(entries.get(2).title().contains("lease.pdf"));
    }

    @Test
    void onlyUserChatMessagesBecomeEntries_notAssistantAnswers() {
        chatGateway.historyResponse = new ChatHistoryDto(List.of(
                new ChatMessageDto(UUID.randomUUID(), matterId, UUID.randomUUID(), "user", "What is the rent?", Instant.now(), List.of(), null, false),
                new ChatMessageDto(UUID.randomUUID(), matterId, null, "assistant", "Rs. 85,000 [1].", Instant.now(), List.of(), false, false)
        ));

        List<ActivityEntry> entries = service.forMatter(firmId, matterId);

        assertEquals(1, entries.size());
        assertEquals("chat", entries.get(0).type());
    }

    @Test
    void aChatServiceFailureOmitsChatEntriesButKeepsDocumentsAndDeadlines() {
        documentRepo.documents.add(new Document(UUID.randomUUID(), matterId, UUID.randomUUID(), "lease.pdf", "key", "application/pdf", 100, DocumentStatus.ready, false, null, null, Instant.now()));
        chatGateway.historyException = new ChatService.AssistantUnavailableException("down");

        List<ActivityEntry> entries = service.forMatter(firmId, matterId);

        assertEquals(1, entries.size());
        assertEquals("document", entries.get(0).type());
    }

    @Test
    void anEmptyMatterReturnsAnEmptyTimeline() {
        assertTrue(service.forMatter(firmId, matterId).isEmpty());
    }
}
