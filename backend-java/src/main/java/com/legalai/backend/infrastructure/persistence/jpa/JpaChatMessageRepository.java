package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.ChatMessageEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.UUID;

public interface JpaChatMessageRepository extends JpaRepository<ChatMessageEntity, UUID> {
    /** Spring Data derived delete query — cascade-delete cleanup only, see ChatMessageRepository. */
    void deleteByMatterId(UUID matterId);
}
