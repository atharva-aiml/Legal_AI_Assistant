package com.legalai.backend.application.matter;

import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.Matter;
import org.springframework.stereotype.Service;

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
 */
@Service
public class MatterService {

    private final MatterRepository repository;
    private final DeadlineRepository deadlineRepository;

    public MatterService(MatterRepository repository, DeadlineRepository deadlineRepository) {
        this.repository = repository;
        this.deadlineRepository = deadlineRepository;
    }

    /** Validated by the domain layer before the repository is ever touched. */
    public Matter create(UUID firmId, UUID clientId, String title) {
        Matter.NewMatter draft = Matter.create(firmId, clientId, title);
        return repository.create(draft);
    }

    public List<Matter> list(UUID firmId, UUID clientId) {
        return clientId != null ? repository.listByClient(firmId, clientId) : repository.listByFirm(firmId);
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
