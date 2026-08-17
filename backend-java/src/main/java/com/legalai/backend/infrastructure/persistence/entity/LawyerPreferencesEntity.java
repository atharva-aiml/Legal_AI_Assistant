package com.legalai.backend.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "lawyer_preferences")
public class LawyerPreferencesEntity {
    @Id
    private UUID id;

    @Column(name = "lawyer_id", nullable = false)
    private UUID lawyerId;

    @Column(name = "deadline_reminders_enabled", nullable = false)
    private boolean deadlineRemindersEnabled;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getLawyerId() { return lawyerId; }
    public void setLawyerId(UUID lawyerId) { this.lawyerId = lawyerId; }
    public boolean isDeadlineRemindersEnabled() { return deadlineRemindersEnabled; }
    public void setDeadlineRemindersEnabled(boolean deadlineRemindersEnabled) { this.deadlineRemindersEnabled = deadlineRemindersEnabled; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
