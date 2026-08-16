package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.SessionEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface JpaSessionRepository extends JpaRepository<SessionEntity, UUID> {
    Optional<SessionEntity> findByTokenHash(String tokenHash);

    void deleteByTokenHash(String tokenHash);
}
