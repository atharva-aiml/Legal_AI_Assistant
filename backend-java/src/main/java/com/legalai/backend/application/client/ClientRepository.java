package com.legalai.backend.application.client;

import com.legalai.backend.domain.Client;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ClientRepository {
    Client create(Client.NewClient record);

    List<Client> listByFirm(UUID firmId);

    Optional<Client> findById(UUID firmId, UUID id);

    /** I-17: caller (ClientService) has already validated the fields — empty Optional means the Client wasn't found (BR-008). */
    Optional<Client> update(UUID firmId, UUID id, String name, String contactEmail, String contactPhone, String notes);
}
