package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.chat.ChatMessageRepository;
import com.legalai.backend.infrastructure.persistence.jpa.JpaChatMessageRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

/** Real ChatMessageRepository, backed by Postgres via Spring Data JPA. Cascade-delete cleanup only, see the port. */
@Repository
public class ChatMessageRepositoryImpl implements ChatMessageRepository {

    private final JpaChatMessageRepository jpa;

    public ChatMessageRepositoryImpl(JpaChatMessageRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public void deleteByMatter(UUID matterId) {
        jpa.deleteByMatterId(matterId);
    }
}
