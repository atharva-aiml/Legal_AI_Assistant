package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.preferences.LawyerPreferencesRepository;
import com.legalai.backend.domain.LawyerPreferences;
import com.legalai.backend.infrastructure.persistence.entity.LawyerPreferencesEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaLawyerPreferencesRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;
import java.util.UUID;

/** Real LawyerPreferencesRepository, backed by Postgres via Spring Data JPA. */
@Repository
public class LawyerPreferencesRepositoryImpl implements LawyerPreferencesRepository {

    private final JpaLawyerPreferencesRepository jpa;

    public LawyerPreferencesRepositoryImpl(JpaLawyerPreferencesRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public Optional<LawyerPreferences> findByLawyerId(UUID lawyerId) {
        return jpa.findByLawyerId(lawyerId).map(LawyerPreferencesRepositoryImpl::toDomain);
    }

    @Override
    @Transactional
    public LawyerPreferences upsert(UUID lawyerId, boolean deadlineRemindersEnabled) {
        jpa.upsertPreferences(lawyerId, deadlineRemindersEnabled);
        return toDomain(jpa.findByLawyerId(lawyerId).orElseThrow());
    }

    private static LawyerPreferences toDomain(LawyerPreferencesEntity e) {
        return new LawyerPreferences(e.getLawyerId(), e.isDeadlineRemindersEnabled());
    }
}
