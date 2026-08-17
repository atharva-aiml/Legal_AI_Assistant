package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.auth.LawyerRepository;
import com.legalai.backend.domain.Firm;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.infrastructure.persistence.entity.FirmEntity;
import com.legalai.backend.infrastructure.persistence.entity.LawyerEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaFirmRepository;
import com.legalai.backend.infrastructure.persistence.jpa.JpaLawyerRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static com.legalai.backend.domain.LawyerRole.owner;

@Repository
public class LawyerRepositoryImpl implements LawyerRepository {

    private final JpaLawyerRepository lawyers;
    private final JpaFirmRepository firms;

    public LawyerRepositoryImpl(JpaLawyerRepository lawyers, JpaFirmRepository firms) {
        this.lawyers = lawyers;
        this.firms = firms;
    }

    @Override
    public Optional<LawyerWithHash> findByEmailWithHash(String email) {
        return lawyers.findByEmail(email).map(e -> new LawyerWithHash(toDomain(e), e.getPasswordHash()));
    }

    @Override
    public Optional<Lawyer> findById(UUID id) {
        return lawyers.findById(id).map(LawyerRepositoryImpl::toDomain);
    }

    @Override
    public Optional<LawyerWithHash> findByIdWithHash(UUID id) {
        return lawyers.findById(id).map(e -> new LawyerWithHash(toDomain(e), e.getPasswordHash()));
    }

    @Override
    public List<Lawyer> listByFirm(UUID firmId) {
        return lawyers.findByFirmId(firmId).stream().map(LawyerRepositoryImpl::toDomain).toList();
    }

    @Override
    public LawyerWithHash create(UUID firmId, String name, String email, String passwordHash) {
        LawyerEntity entity = new LawyerEntity();
        entity.setId(UUID.randomUUID());
        entity.setFirmId(firmId);
        entity.setName(name);
        entity.setEmail(email);
        entity.setPasswordHash(passwordHash);
        entity.setRole(owner);
        entity.setCreatedAt(Instant.now());
        LawyerEntity saved = lawyers.save(entity);
        return new LawyerWithHash(toDomain(saved), saved.getPasswordHash());
    }

    @Override
    public Firm createFirm(String name) {
        FirmEntity entity = new FirmEntity();
        entity.setId(UUID.randomUUID());
        entity.setName(name);
        entity.setCreatedAt(Instant.now());
        FirmEntity saved = firms.save(entity);
        return new Firm(saved.getId(), saved.getName(), saved.getCreatedAt());
    }

    @Override
    public Optional<Lawyer> updateName(UUID id, String name) {
        return lawyers.findById(id).map(entity -> {
            entity.setName(name);
            return toDomain(lawyers.save(entity));
        });
    }

    @Override
    public void updatePassword(UUID id, String newPasswordHash) {
        lawyers.findById(id).ifPresent(entity -> {
            entity.setPasswordHash(newPasswordHash);
            lawyers.save(entity);
        });
    }

    private static Lawyer toDomain(LawyerEntity e) {
        return new Lawyer(e.getId(), e.getFirmId(), e.getName(), e.getEmail(), e.getRole(), e.getCreatedAt());
    }
}
