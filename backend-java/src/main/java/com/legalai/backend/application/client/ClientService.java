package com.legalai.backend.application.client;

import com.legalai.backend.application.matter.MatterRepository;
import com.legalai.backend.application.matter.MatterService;
import com.legalai.backend.domain.Client;
import com.legalai.backend.domain.Matter;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * deleteCascade() below is a real product decision — deleting a Client
 * cascade-deletes everything under it — but the per-Matter cascade logic
 * itself (Documents/Deadlines/chat_messages/matter_views, in that order)
 * lives in MatterService.deleteCascade, not here: this Service only needs
 * MatterRepository to list the Matters under the Client, then delegates
 * each one's actual cascade to MatterService, the same single
 * implementation a direct single-Matter delete uses.
 */
@Service
public class ClientService {

    private final ClientRepository repository;
    private final MatterRepository matterRepository;
    private final MatterService matterService;

    public ClientService(ClientRepository repository, MatterRepository matterRepository, MatterService matterService) {
        this.repository = repository;
        this.matterRepository = matterRepository;
        this.matterService = matterService;
    }

    public Client create(UUID firmId, String name, String contactEmail, String contactPhone, String notes) {
        Client.NewClient draft = Client.create(firmId, name, contactEmail, contactPhone, notes);
        return repository.create(draft);
    }

    public List<Client> list(UUID firmId) {
        return repository.listByFirm(firmId);
    }

    public Optional<Client> get(UUID firmId, UUID id) {
        return repository.findById(firmId, id);
    }

    /** Validated by the domain layer before the repository is ever touched, same as create(). */
    public Optional<Client> update(UUID firmId, UUID id, String name, String contactEmail, String contactPhone, String notes) {
        Client.UpdatedFields validated = Client.update(name, contactEmail, contactPhone, notes);
        return repository.update(firmId, id, validated.name(), validated.contactEmail(), validated.contactPhone(), validated.notes());
    }

    /**
     * Explicit, already-made product decision: deleting a Client
     * cascade-deletes every Matter under it, and every Document/Deadline/
     * chat-message/matter_view row under each of those Matters —
     * irreversible, high blast radius, no confirmation logic here (that's
     * the frontend's job before this is ever called).
     *
     * No FK-level ON DELETE CASCADE exists from clients -> matters, or from
     * matters -> documents/deadlines/chat_messages/matter_views
     * (database/schema/schema.ts — those are plain, unqualified
     * references()), so this deletes children in dependency order inside
     * one transaction rather than relying on the database to do it, or a
     * partial cascade would leave orphaned rows and/or an FK violation
     * half-way through.
     *
     * Each Matter's own cascade (Documents via DocumentService.delete, then
     * Deadlines, then chat_messages, then matter_views, then the Matter row
     * itself) is delegated to MatterService.deleteCascade — see that
     * method's javadoc for the full deletion-order rationale.
     * document_chunks (cascades off Document), citations (cascades off
     * chat_messages) and notifications (cascades off Deadline) are all
     * handled automatically at the DB level and never touched directly
     * here.
     *
     * BR-008: returns false (no-op, nothing deleted) if the Client doesn't
     * exist or belongs to a different Firm — the controller maps that to
     * 404, same as every other Client operation.
     */
    @Transactional
    public boolean deleteCascade(UUID firmId, UUID clientId) {
        if (repository.findById(firmId, clientId).isEmpty()) {
            return false;
        }

        for (Matter matter : matterRepository.listByClient(firmId, clientId)) {
            matterService.deleteCascade(firmId, matter.id());
        }

        return repository.delete(firmId, clientId);
    }
}
