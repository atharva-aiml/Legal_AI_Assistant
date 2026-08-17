package com.legalai.backend.application.client;

import com.legalai.backend.domain.Client;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class ClientService {

    private final ClientRepository repository;

    public ClientService(ClientRepository repository) {
        this.repository = repository;
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
}
