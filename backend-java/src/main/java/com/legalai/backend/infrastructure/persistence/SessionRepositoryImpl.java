package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.auth.SessionRepository;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.infrastructure.persistence.entity.LawyerEntity;
import com.legalai.backend.infrastructure.persistence.entity.SessionEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaLawyerRepository;
import com.legalai.backend.infrastructure.persistence.jpa.JpaSessionRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

@Repository
public class SessionRepositoryImpl implements SessionRepository {

    private final JpaSessionRepository sessions;
    private final JpaLawyerRepository lawyers;

    public SessionRepositoryImpl(JpaSessionRepository sessions, JpaLawyerRepository lawyers) {
        this.sessions = sessions;
        this.lawyers = lawyers;
    }

    @Override
    public void create(UUID lawyerId, String tokenHash, Instant expiresAt) {
        SessionEntity entity = new SessionEntity();
        entity.setId(UUID.randomUUID());
        entity.setLawyerId(lawyerId);
        entity.setTokenHash(tokenHash);
        entity.setExpiresAt(expiresAt);
        entity.setCreatedAt(Instant.now());
        sessions.save(entity);
    }

    @Override
    public Optional<Lawyer> findLawyerByValidTokenHash(String tokenHash) {
        return sessions.findByTokenHash(tokenHash)
                .filter(session -> session.getExpiresAt().isAfter(Instant.now()))
                .flatMap(session -> lawyers.findById(session.getLawyerId()))
                .map(SessionRepositoryImpl::toDomain);
    }

    @Override
    @Transactional
    public void deleteByTokenHash(String tokenHash) {
        sessions.deleteByTokenHash(tokenHash);
    }

    private static Lawyer toDomain(LawyerEntity e) {
        return new Lawyer(e.getId(), e.getFirmId(), e.getName(), e.getEmail(), e.getRole(), e.getCreatedAt());
    }
}
