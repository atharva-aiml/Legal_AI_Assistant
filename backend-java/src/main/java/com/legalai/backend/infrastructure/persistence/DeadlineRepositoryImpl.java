package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.infrastructure.persistence.entity.DeadlineEntity;
import com.legalai.backend.infrastructure.persistence.entity.MatterEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaDeadlineRepository;
import com.legalai.backend.infrastructure.persistence.jpa.JpaMatterRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class DeadlineRepositoryImpl implements DeadlineRepository {

    private final JpaDeadlineRepository jpa;
    private final JpaMatterRepository matters;

    public DeadlineRepositoryImpl(JpaDeadlineRepository jpa, JpaMatterRepository matters) {
        this.jpa = jpa;
        this.matters = matters;
    }

    @Override
    public Deadline create(Deadline.NewDeadline record) {
        DeadlineEntity entity = new DeadlineEntity();
        entity.setId(UUID.randomUUID());
        entity.setMatterId(record.matterId());
        entity.setTitle(record.title());
        entity.setDueDate(record.dueDate());
        entity.setStatus(DeadlineStatus.open);
        entity.setNotificationLeadDays(record.notificationLeadDays());
        Instant now = Instant.now();
        entity.setCreatedAt(now);
        entity.setUpdatedAt(now);
        return toDomain(jpa.save(entity));
    }

    @Override
    public List<Deadline> listByMatter(UUID firmId, UUID matterId) {
        return jpa.findByMatterIdAndFirmId(matterId, firmId).stream().map(DeadlineRepositoryImpl::toDomain).toList();
    }

    @Override
    public Optional<Deadline> findById(UUID firmId, UUID id) {
        return jpa.findByIdAndFirmId(id, firmId).map(DeadlineRepositoryImpl::toDomain);
    }

    @Override
    public Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, int notificationLeadDays) {
        return jpa.findByIdAndFirmId(id, firmId).map(entity -> {
            entity.setTitle(title);
            entity.setDueDate(dueDate);
            entity.setStatus(status);
            entity.setNotificationLeadDays(notificationLeadDays);
            entity.setUpdatedAt(Instant.now());
            return toDomain(jpa.save(entity));
        });
    }

    @Override
    public List<Deadline> listUpcoming(UUID firmId, int days) {
        LocalDate cutoff = LocalDate.now().plusDays(days);
        return jpa.findUpcoming(firmId, DeadlineStatus.open, cutoff).stream().map(DeadlineRepositoryImpl::toDomain).toList();
    }

    @Override
    public List<DeadlineWithFirm> listAllOpenWithFirm() {
        return jpa.findByStatus(DeadlineStatus.open).stream()
                .map(entity -> {
                    UUID firmId = matters.findById(entity.getMatterId()).map(MatterEntity::getFirmId).orElse(null);
                    return firmId == null ? null : new DeadlineWithFirm(toDomain(entity), firmId);
                })
                .filter(java.util.Objects::nonNull) // defensive: FK guarantees the Matter exists, but never trust that blindly in a cross-cutting scan
                .toList();
    }

    private static Deadline toDomain(DeadlineEntity e) {
        return new Deadline(e.getId(), e.getMatterId(), e.getTitle(), e.getDueDate(), e.getStatus(), e.getNotificationLeadDays(), e.getCreatedAt(), e.getUpdatedAt());
    }
}
