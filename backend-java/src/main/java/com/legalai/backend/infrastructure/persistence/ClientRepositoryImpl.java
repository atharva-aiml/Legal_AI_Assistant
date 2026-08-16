package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.client.ClientRepository;
import com.legalai.backend.domain.Client;
import com.legalai.backend.infrastructure.persistence.entity.ClientEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaClientRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class ClientRepositoryImpl implements ClientRepository {

    private final JpaClientRepository jpa;

    public ClientRepositoryImpl(JpaClientRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public Client create(Client.NewClient record) {
        ClientEntity entity = new ClientEntity();
        entity.setId(UUID.randomUUID());
        entity.setFirmId(record.firmId());
        entity.setName(record.name());
        entity.setContactEmail(record.contactEmail());
        entity.setContactPhone(record.contactPhone());
        entity.setNotes(record.notes());
        Instant now = Instant.now();
        entity.setCreatedAt(now);
        entity.setUpdatedAt(now);
        return toDomain(jpa.save(entity));
    }

    @Override
    public List<Client> listByFirm(UUID firmId) {
        return jpa.findByFirmId(firmId).stream().map(ClientRepositoryImpl::toDomain).toList();
    }

    @Override
    public Optional<Client> findById(UUID firmId, UUID id) {
        return jpa.findByIdAndFirmId(id, firmId).map(ClientRepositoryImpl::toDomain);
    }

    static Client toDomain(ClientEntity e) {
        return new Client(e.getId(), e.getFirmId(), e.getName(), e.getContactEmail(), e.getContactPhone(), e.getNotes(), e.getCreatedAt(), e.getUpdatedAt());
    }
}
