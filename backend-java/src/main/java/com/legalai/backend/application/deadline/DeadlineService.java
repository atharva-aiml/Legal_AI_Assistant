package com.legalai.backend.application.deadline;

import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Mirrors DocumentService's shape: depends only on its own repository —
 * Matter existence/ownership is checked by the controller before this is
 * ever called, exactly like DocumentController does for uploads.
 */
@Service
public class DeadlineService {

    private final DeadlineRepository repository;

    public DeadlineService(DeadlineRepository repository) {
        this.repository = repository;
    }

    /** Validated by the domain layer (BR-004) before the repository is ever touched. */
    public Deadline create(UUID matterId, String title, LocalDate dueDate, DeadlinePriority priority, Integer notificationLeadDays) {
        Deadline.NewDeadline draft = Deadline.create(matterId, title, dueDate, priority, notificationLeadDays);
        return repository.create(draft);
    }

    public List<Deadline> list(UUID firmId, UUID matterId) {
        return repository.listByMatter(firmId, matterId);
    }

    public Optional<Deadline> get(UUID firmId, UUID id) {
        return repository.findById(firmId, id);
    }

    /** Partial update (PATCH semantics) — omitted fields keep their current value. */
    public Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, DeadlinePriority priority, Integer notificationLeadDays) {
        Optional<Deadline> existing = repository.findById(firmId, id);
        if (existing.isEmpty()) {
            return Optional.empty();
        }
        Deadline current = existing.get();
        String newTitle = title != null ? Deadline.validateTitle(title) : current.title();
        LocalDate newDueDate = dueDate != null ? Deadline.validateDueDate(dueDate) : current.dueDate();
        DeadlineStatus newStatus = status != null ? status : current.status();
        DeadlinePriority newPriority = priority != null ? priority : current.priority();
        int newLeadDays = notificationLeadDays != null ? Deadline.validateLeadDays(notificationLeadDays) : current.notificationLeadDays();
        return repository.update(firmId, id, newTitle, newDueDate, newStatus, newPriority, newLeadDays);
    }

    public List<Deadline> upcoming(UUID firmId, int days) {
        return repository.listUpcoming(firmId, days);
    }
}
