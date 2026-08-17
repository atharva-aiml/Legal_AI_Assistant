package com.legalai.backend.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "recent_searches")
public class RecentSearchEntity {
    @Id
    private UUID id;

    @Column(name = "lawyer_id", nullable = false)
    private UUID lawyerId;

    @Column(name = "query", nullable = false)
    private String query;

    @Column(name = "searched_at", nullable = false)
    private Instant searchedAt;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getLawyerId() { return lawyerId; }
    public void setLawyerId(UUID lawyerId) { this.lawyerId = lawyerId; }
    public String getQuery() { return query; }
    public void setQuery(String query) { this.query = query; }
    public Instant getSearchedAt() { return searchedAt; }
    public void setSearchedAt(Instant searchedAt) { this.searchedAt = searchedAt; }
}
