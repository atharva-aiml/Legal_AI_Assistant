package com.legalai.backend.domain;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class NotificationTest {

    private final UUID lawyerId = UUID.randomUUID();
    private final UUID deadlineId = UUID.randomUUID();

    @Test
    void createsANotificationWithARecipientAndMessage() {
        Notification.NewNotification notification = Notification.create(lawyerId, deadlineId, "File response is due in 3 days.");
        assertEquals(lawyerId, notification.lawyerId());
        assertEquals(deadlineId, notification.deadlineId());
        assertEquals("File response is due in 3 days.", notification.message());
    }

    @Test
    void trimsWhitespaceFromTheMessage() {
        Notification.NewNotification notification = Notification.create(lawyerId, deadlineId, "  Padded  ");
        assertEquals("Padded", notification.message());
    }

    @Test
    void rejectsANotificationWithNoRecipient() {
        assertThrows(InvalidNotificationException.class, () -> Notification.create(null, deadlineId, "Reminder"));
    }

    @Test
    void rejectsANotificationWithNoDeadline() {
        assertThrows(InvalidNotificationException.class, () -> Notification.create(lawyerId, null, "Reminder"));
    }

    @Test
    void rejectsANotificationWithNoMessage() {
        assertThrows(InvalidNotificationException.class, () -> Notification.create(lawyerId, deadlineId, "   "));
    }
}
