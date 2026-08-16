package com.legalai.backend.infrastructure.persistence.entity;

import jakarta.persistence.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "notifications")
public class NotificationEntity {
    @Id
    private UUID id;

    @Column(name = "lawyer_id", nullable = false)
    private UUID lawyerId;

    @Column(name = "deadline_id", nullable = false)
    private UUID deadlineId;

    @Column(nullable = false)
    private String message;

    @Column(name = "sent_at")
    private Instant sentAt;

    @Column(name = "read_at")
    private Instant readAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getLawyerId() { return lawyerId; }
    public void setLawyerId(UUID lawyerId) { this.lawyerId = lawyerId; }
    public UUID getDeadlineId() { return deadlineId; }
    public void setDeadlineId(UUID deadlineId) { this.deadlineId = deadlineId; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public Instant getSentAt() { return sentAt; }
    public void setSentAt(Instant sentAt) { this.sentAt = sentAt; }
    public Instant getReadAt() { return readAt; }
    public void setReadAt(Instant readAt) { this.readAt = readAt; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
