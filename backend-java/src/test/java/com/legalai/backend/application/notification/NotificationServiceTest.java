package com.legalai.backend.application.notification;

import com.legalai.backend.domain.Notification;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class NotificationServiceTest {

    static class InMemoryNotificationRepository implements NotificationRepository {
        final List<Notification> notifications = new ArrayList<>();

        @Override
        public List<Notification> listByLawyer(UUID lawyerId) {
            return notifications.stream().filter(n -> n.lawyerId().equals(lawyerId)).toList();
        }

        @Override
        public Optional<Notification> markRead(UUID lawyerId, UUID id) {
            for (int i = 0; i < notifications.size(); i++) {
                Notification n = notifications.get(i);
                if (n.id().equals(id) && n.lawyerId().equals(lawyerId)) {
                    Notification read = new Notification(n.id(), n.lawyerId(), n.deadlineId(), n.message(), n.sentAt(), Instant.now(), n.createdAt());
                    notifications.set(i, read);
                    return Optional.of(read);
                }
            }
            return Optional.empty();
        }

        @Override
        public Notification create(Notification.NewNotification record) {
            Notification created = new Notification(UUID.randomUUID(), record.lawyerId(), record.deadlineId(), record.message(), Instant.now(), null, Instant.now());
            notifications.add(created);
            return created;
        }

        @Override
        public int markAllRead(UUID lawyerId) {
            int count = 0;
            for (int i = 0; i < notifications.size(); i++) {
                Notification n = notifications.get(i);
                if (n.lawyerId().equals(lawyerId) && n.readAt() == null) {
                    notifications.set(i, new Notification(n.id(), n.lawyerId(), n.deadlineId(), n.message(), n.sentAt(), Instant.now(), n.createdAt()));
                    count++;
                }
            }
            return count;
        }

        @Override
        public boolean existsForDeadlineAndLawyerOnDay(UUID deadlineId, UUID lawyerId, LocalDate day) {
            return notifications.stream().anyMatch(n -> n.deadlineId().equals(deadlineId) && n.lawyerId().equals(lawyerId));
        }
    }

    private InMemoryNotificationRepository repo;
    private NotificationService service;
    private final UUID lawyer1 = UUID.randomUUID();
    private final UUID lawyer2 = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repo = new InMemoryNotificationRepository();
        service = new NotificationService(repo);
    }

    @Test
    void listsOnlyTheCallingLawyersNotifications() {
        repo.create(Notification.create(lawyer1, UUID.randomUUID(), "Reminder for lawyer 1"));
        repo.create(Notification.create(lawyer2, UUID.randomUUID(), "Reminder for lawyer 2"));

        List<Notification> listed = service.list(lawyer1);
        assertEquals(1, listed.size());
        assertEquals("Reminder for lawyer 1", listed.get(0).message());
    }

    @Test
    void marksANotificationRead() {
        Notification created = repo.create(Notification.create(lawyer1, UUID.randomUUID(), "Reminder"));
        assertNull(created.readAt());

        Notification read = service.markRead(lawyer1, created.id()).orElseThrow();
        assertNotNull(read.readAt());
    }

    @Test
    void markingAnotherLawyersNotificationReadReturnsEmptyNotAnError() {
        Notification created = repo.create(Notification.create(lawyer1, UUID.randomUUID(), "Reminder"));
        assertTrue(service.markRead(lawyer2, created.id()).isEmpty());
    }

    // --- I-44: mark all as read ---

    @Test
    void marksEveryUnreadNotificationForTheCallingLawyer() {
        repo.create(Notification.create(lawyer1, UUID.randomUUID(), "First"));
        repo.create(Notification.create(lawyer1, UUID.randomUUID(), "Second"));

        int marked = service.markAllRead(lawyer1);

        assertEquals(2, marked);
        assertTrue(service.list(lawyer1).stream().allMatch(n -> n.readAt() != null));
    }

    @Test
    void markAllReadNeverTouchesAnotherLawyersNotifications() {
        Notification other = repo.create(Notification.create(lawyer2, UUID.randomUUID(), "Not yours"));

        service.markAllRead(lawyer1);

        assertNull(service.list(lawyer2).stream().filter(n -> n.id().equals(other.id())).findFirst().orElseThrow().readAt());
    }

    @Test
    void markAllReadIsIdempotent_alreadyReadOnesDontCountAgain() {
        Notification created = repo.create(Notification.create(lawyer1, UUID.randomUUID(), "Reminder"));
        service.markRead(lawyer1, created.id());

        int markedSecondTime = service.markAllRead(lawyer1);

        assertEquals(0, markedSecondTime, "nothing left unread, so a repeat call marks nothing");
    }
}
