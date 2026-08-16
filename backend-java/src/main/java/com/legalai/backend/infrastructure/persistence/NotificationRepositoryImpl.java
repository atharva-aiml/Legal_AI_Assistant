package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.notification.NotificationRepository;
import com.legalai.backend.domain.Notification;
import com.legalai.backend.infrastructure.persistence.entity.NotificationEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaNotificationRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class NotificationRepositoryImpl implements NotificationRepository {

    private final JpaNotificationRepository jpa;

    public NotificationRepositoryImpl(JpaNotificationRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public List<Notification> listByLawyer(UUID lawyerId) {
        return jpa.findByLawyerIdOrderByCreatedAtDesc(lawyerId).stream().map(NotificationRepositoryImpl::toDomain).toList();
    }

    @Override
    public Optional<Notification> markRead(UUID lawyerId, UUID id) {
        return jpa.findByIdAndLawyerId(id, lawyerId).map(entity -> {
            entity.setReadAt(Instant.now());
            return toDomain(jpa.save(entity));
        });
    }

    @Override
    public Notification create(Notification.NewNotification record) {
        NotificationEntity entity = new NotificationEntity();
        entity.setId(UUID.randomUUID());
        entity.setLawyerId(record.lawyerId());
        entity.setDeadlineId(record.deadlineId());
        entity.setMessage(record.message());
        Instant now = Instant.now();
        entity.setSentAt(now); // in-app only for now (Build Plan V0.5 scope note) — "sent" the moment it's created
        entity.setCreatedAt(now);
        return toDomain(jpa.save(entity));
    }

    @Override
    public boolean existsForDeadlineAndLawyerOnDay(UUID deadlineId, UUID lawyerId, LocalDate day) {
        // Java-side "same day" check, deliberately not a DB ::date CAST —
        // see JpaNotificationRepository's comment on why.
        return jpa.findByDeadlineIdAndLawyerId(deadlineId, lawyerId).stream()
                .anyMatch(n -> n.getCreatedAt().atZone(ZoneOffset.UTC).toLocalDate().equals(day));
    }

    private static Notification toDomain(NotificationEntity e) {
        return new Notification(e.getId(), e.getLawyerId(), e.getDeadlineId(), e.getMessage(), e.getSentAt(), e.getReadAt(), e.getCreatedAt());
    }
}
