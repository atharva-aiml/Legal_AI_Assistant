package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.matter.MatterRepository;
import com.legalai.backend.domain.Matter;
import com.legalai.backend.infrastructure.persistence.entity.MatterEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaMatterRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** Real MatterRepository, backed by Postgres via Spring Data JPA. */
@Repository
public class MatterRepositoryImpl implements MatterRepository {

    private final JpaMatterRepository jpa;

    public MatterRepositoryImpl(JpaMatterRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public Matter create(Matter.NewMatter record) {
        MatterEntity entity = new MatterEntity();
        entity.setId(UUID.randomUUID());
        entity.setFirmId(record.firmId());
        entity.setClientId(record.clientId());
        entity.setTitle(record.title());
        entity.setStatus(record.status());
        Instant now = Instant.now();
        entity.setCreatedAt(now);
        entity.setUpdatedAt(now);
        return toDomain(jpa.save(entity));
    }

    @Override
    public List<Matter> listByFirm(UUID firmId) {
        return jpa.findByFirmId(firmId).stream().map(MatterRepositoryImpl::toDomain).toList();
    }

    @Override
    public List<Matter> listByClient(UUID firmId, UUID clientId) {
        return jpa.findByFirmIdAndClientId(firmId, clientId).stream().map(MatterRepositoryImpl::toDomain).toList();
    }

    @Override
    public Optional<Matter> findById(UUID firmId, UUID id) {
        return jpa.findByIdAndFirmId(id, firmId).map(MatterRepositoryImpl::toDomain);
    }

    @Override
    public Optional<Matter> updateTitle(UUID firmId, UUID id, String title) {
        return jpa.findByIdAndFirmId(id, firmId).map(entity -> {
            entity.setTitle(title);
            entity.setUpdatedAt(Instant.now());
            return toDomain(jpa.save(entity));
        });
    }

    @Override
    public Optional<Matter> close(UUID firmId, UUID id) {
        return jpa.findByIdAndFirmId(id, firmId).map(entity -> {
            Instant now = Instant.now();
            entity.setStatus(com.legalai.backend.domain.MatterStatus.closed);
            entity.setClosedAt(now);
            entity.setUpdatedAt(now);
            return toDomain(jpa.save(entity));
        });
    }

    @Override
    public Optional<Matter> reopen(UUID firmId, UUID id) {
        return jpa.findByIdAndFirmId(id, firmId).map(entity -> {
            entity.setStatus(com.legalai.backend.domain.MatterStatus.open);
            entity.setClosedAt(null);
            entity.setUpdatedAt(Instant.now());
            return toDomain(jpa.save(entity));
        });
    }

    @Override
    public boolean delete(UUID firmId, UUID id) {
        Optional<MatterEntity> entity = jpa.findByIdAndFirmId(id, firmId);
        entity.ifPresent(jpa::delete);
        return entity.isPresent();
    }

    static Matter toDomain(MatterEntity e) {
        return new Matter(e.getId(), e.getFirmId(), e.getClientId(), e.getTitle(), e.getStatus(), e.getClosedAt(), e.getCreatedAt(), e.getUpdatedAt());
    }
}
