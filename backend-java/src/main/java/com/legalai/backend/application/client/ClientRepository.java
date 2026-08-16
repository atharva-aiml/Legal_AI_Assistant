package com.legalai.backend.application.client;

import com.legalai.backend.domain.Client;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ClientRepository {
    Client create(Client.NewClient record);

    List<Client> listByFirm(UUID firmId);

    Optional<Client> findById(UUID firmId, UUID id);
}
