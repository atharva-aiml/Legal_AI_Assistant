package com.legalai.backend.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "matter_views")
public class MatterViewEntity {
    @Id
    private UUID id;

    @Column(name = "lawyer_id", nullable = false)
    private UUID lawyerId;

    @Column(name = "matter_id", nullable = false)
    private UUID matterId;

    @Column(name = "viewed_at", nullable = false)
    private Instant viewedAt;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getLawyerId() { return lawyerId; }
    public void setLawyerId(UUID lawyerId) { this.lawyerId = lawyerId; }
    public UUID getMatterId() { return matterId; }
    public void setMatterId(UUID matterId) { this.matterId = matterId; }
    public Instant getViewedAt() { return viewedAt; }
    public void setViewedAt(Instant viewedAt) { this.viewedAt = viewedAt; }
}
