package com.legalai.backend.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.util.UUID;

/**
 * Minimal mapping, deliberately — Java never reads or writes chat_messages
 * content (SD-005: that's entirely Python's domain via HttpChatGateway).
 * This entity exists only so JpaChatMessageRepository can bulk-delete a
 * Matter's chat history as part of Client/Matter cascade-delete
 * (ClientService.deleteCascade), so only the columns that operation needs
 * are mapped — role/content/pinned/etc. are intentionally absent.
 */
@Entity
@Table(name = "chat_messages")
public class ChatMessageEntity {
    @Id
    private UUID id;

    @Column(name = "matter_id", nullable = false)
    private UUID matterId;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getMatterId() { return matterId; }
    public void setMatterId(UUID matterId) { this.matterId = matterId; }
}
