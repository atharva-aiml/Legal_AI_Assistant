package com.legalai.backend.application.matter;

import com.legalai.backend.application.chat.ChatMessageRepository;
import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.application.document.DocumentService;
import com.legalai.backend.application.matterview.MatterViewRepository;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.Document;
import com.legalai.backend.domain.Matter;
import com.legalai.backend.domain.MatterStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Application layer — one Spring @Service consolidating what the original
 * TypeScript version split into four single-method use-case files
 * (create/list/get/rename-matter.ts). Same behavior, more idiomatic Java:
 * a small service class is the standard Spring pattern for this layer,
 * where four one-method classes would just be ceremony.
 *
 * Depends on DeadlineRepository too (unlike every other entity's service,
 * which depends on exactly one repository) — BR-003 ("a Matter cannot be
 * marked Closed while it has one or more open Deadlines") is inherently
 * cross-entity: deciding whether a close is allowed requires the Matter's
 * Deadlines, not just the Matter itself.
 *
 * Also depends on DocumentService/ChatMessageRepository/MatterViewRepository
 * for deleteCascade() below — the single-Matter cascade-delete, originally
 * written inline inside ClientService.deleteCascade's per-Matter loop, then
 * extracted here so both a whole-Client delete and a single-Matter delete
 * share one implementation instead of two copies drifting apart.
 */
@Service
public class MatterService {

    private final MatterRepository repository;
    private final DeadlineRepository deadlineRepository;
    private final DocumentService documentService;
    private final ChatMessageRepository chatMessageRepository;
    private final MatterViewRepository matterViewRepository;

    public MatterService(MatterRepository repository, DeadlineRepository deadlineRepository, DocumentService documentService,
                          ChatMessageRepository chatMessageRepository, MatterViewRepository matterViewRepository) {
        this.repository = repository;
        this.deadlineRepository = deadlineRepository;
        this.documentService = documentService;
        this.chatMessageRepository = chatMessageRepository;
        this.matterViewRepository = matterViewRepository;
    }

    /** Validated by the domain layer before the repository is ever touched. */
    public Matter create(UUID firmId, UUID clientId, String title) {
        Matter.NewMatter draft = Matter.create(firmId, clientId, title);
        return repository.create(draft);
    }

    /** I-23: status is filtered here, in-memory, rather than a new repository query — the Firm's Matter volume never justifies pushing this to the database. */
    public List<Matter> list(UUID firmId, UUID clientId, MatterStatus status) {
        List<Matter> matters = clientId != null ? repository.listByClient(firmId, clientId) : repository.listByFirm(firmId);
        return status == null ? matters : matters.stream().filter(m -> m.status() == status).toList();
    }

    /** BR-008: a Matter outside the caller's Firm resolves to empty, not an error. */
    public Optional<Matter> get(UUID firmId, UUID id) {
        return repository.findById(firmId, id);
    }

    public Optional<Matter> rename(UUID firmId, UUID id, String title) {
        String validated = Matter.renameTitle(title);
        return repository.updateTitle(firmId, id, validated);
    }

    /**
     * REQ-010/BR-003: closes the Matter, unless it has one or more open
     * Deadlines — in which case it throws, naming exactly which ones,
     * rather than a generic failure the lawyer would have to go hunting
     * for. Empty Optional means the Matter itself wasn't found (BR-008).
     */
    public Optional<Matter> close(UUID firmId, UUID id) {
        if (repository.findById(firmId, id).isEmpty()) {
            return Optional.empty();
        }
        List<Deadline> openDeadlines = Deadline.openOnes(deadlineRepository.listByMatter(firmId, id));
        if (!openDeadlines.isEmpty()) {
            throw new MatterHasOpenDeadlinesException(openDeadlines);
        }
        return repository.close(firmId, id);
    }

    /**
     * I-35: the counterpart to close() — BR-008 first (empty means not
     * found/not this Firm's), then the domain-layer "must actually be
     * Closed" check, before the repository is ever touched.
     */
    public Optional<Matter> reopen(UUID firmId, UUID id) {
        Optional<Matter> existing = repository.findById(firmId, id);
        if (existing.isEmpty()) {
            return Optional.empty();
        }
        Matter.validateReopen(existing.get().status());
        return repository.reopen(firmId, id);
    }

    /**
     * Cascade-deletes a single Matter: its Documents (via
     * DocumentService.delete, not the repository directly — reuses
     * REQ-027's existing per-Document path so stored files are cleaned up
     * from /uploads (or R2), never orphaned), then Deadlines, then
     * chat_messages, then matter_views, then the Matter row itself.
     * document_chunks (cascades off Document), citations (cascades off
     * chat_messages) and notifications (cascades off Deadline) are all
     * handled automatically at the DB level and never touched directly
     * here. Same deletion order as, and now the single implementation
     * behind, ClientService.deleteCascade's per-Matter loop — see that
     * class's javadoc for the "no FK-level ON DELETE CASCADE" context.
     *
     * BR-008: returns false (no-op, nothing deleted) if the Matter doesn't
     * exist or belongs to a different Firm — callers map that to 404, same
     * as every other Matter operation.
     */
    @Transactional
    public boolean deleteCascade(UUID firmId, UUID matterId) {
        if (repository.findById(firmId, matterId).isEmpty()) {
            return false;
        }

        for (Document document : documentService.list(firmId, matterId)) {
            documentService.delete(firmId, document.id());
        }
        deadlineRepository.deleteByMatter(matterId);
        chatMessageRepository.deleteByMatter(matterId);
        matterViewRepository.deleteByMatter(matterId);
        return repository.delete(firmId, matterId);
    }

    /** Carries the specific blocking Deadlines so the API/UI can name them, not just say "blocked." */
    public static class MatterHasOpenDeadlinesException extends RuntimeException {
        private final List<Deadline> openDeadlines;

        public MatterHasOpenDeadlinesException(List<Deadline> openDeadlines) {
            super("Matter cannot be closed while it has open Deadlines (BR-003).");
            this.openDeadlines = openDeadlines;
        }

        public List<Deadline> openDeadlines() {
            return openDeadlines;
        }
    }
}
