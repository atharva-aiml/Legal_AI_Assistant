package com.legalai.backend.infrastructure.persistence.entity;

import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "deadlines")
public class DeadlineEntity {
    @Id
    private UUID id;

    @Column(name = "matter_id", nullable = false)
    private UUID matterId;

    @Column(nullable = false)
    private String title;

    @Column(name = "due_date", nullable = false)
    private LocalDate dueDate;

    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    @Column(nullable = false)
    private DeadlineStatus status;

    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    @Column(nullable = false)
    private DeadlinePriority priority;

    @Column(name = "notification_lead_days", nullable = false)
    private int notificationLeadDays;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getMatterId() { return matterId; }
    public void setMatterId(UUID matterId) { this.matterId = matterId; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public LocalDate getDueDate() { return dueDate; }
    public void setDueDate(LocalDate dueDate) { this.dueDate = dueDate; }
    public DeadlineStatus getStatus() { return status; }
    public void setStatus(DeadlineStatus status) { this.status = status; }
    public DeadlinePriority getPriority() { return priority; }
    public void setPriority(DeadlinePriority priority) { this.priority = priority; }
    public int getNotificationLeadDays() { return notificationLeadDays; }
    public void setNotificationLeadDays(int notificationLeadDays) { this.notificationLeadDays = notificationLeadDays; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
