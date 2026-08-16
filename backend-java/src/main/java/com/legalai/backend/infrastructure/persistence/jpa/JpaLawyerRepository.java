package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.LawyerEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface JpaLawyerRepository extends JpaRepository<LawyerEntity, UUID> {
    Optional<LawyerEntity> findByEmail(String email);

    List<LawyerEntity> findByFirmId(UUID firmId);
}
