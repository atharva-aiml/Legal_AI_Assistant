package com.legalai.backend.application.notification;

import com.legalai.backend.application.auth.LawyerRepository;
import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.application.preferences.LawyerPreferencesRepository;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.DeadlinePriority;
import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.domain.Firm;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.domain.LawyerPreferences;
import com.legalai.backend.domain.LawyerRole;
import com.legalai.backend.domain.Notification;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class NotificationScanServiceTest {

    static class InMemoryDeadlineRepository implements DeadlineRepository {
        final List<DeadlineWithFirm> openDeadlines = new ArrayList<>();

        @Override
        public Deadline create(Deadline.NewDeadline record) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public List<Deadline> listByMatter(UUID firmId, UUID matterId) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public Optional<Deadline> findById(UUID firmId, UUID id) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public Optional<Deadline> update(UUID firmId, UUID id, String title, LocalDate dueDate, DeadlineStatus status, DeadlinePriority priority, int notificationLeadDays) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public List<Deadline> listUpcoming(UUID firmId, int days) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public List<DeadlineWithFirm> listAllOpenWithFirm() {
            return openDeadlines;
        }
    }

    static class InMemoryNotificationRepository implements NotificationRepository {
        final List<Notification> notifications = new ArrayList<>();

        @Override
        public List<Notification> listByLawyer(UUID lawyerId) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public Optional<Notification> markRead(UUID lawyerId, UUID id) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public Notification create(Notification.NewNotification record) {
            Notification created = new Notification(UUID.randomUUID(), record.lawyerId(), record.deadlineId(), record.message(), Instant.now(), null, Instant.now());
            notifications.add(created);
            return created;
        }

        @Override
        public boolean existsForDeadlineAndLawyerOnDay(UUID deadlineId, UUID lawyerId, LocalDate day) {
            return notifications.stream().anyMatch(n ->
                    n.deadlineId().equals(deadlineId)
                            && n.lawyerId().equals(lawyerId)
                            && n.createdAt().atZone(ZoneOffset.UTC).toLocalDate().equals(day));
        }

        @Override
        public int markAllRead(UUID lawyerId) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }
    }

    static class InMemoryLawyerRepository implements LawyerRepository {
        final java.util.Map<UUID, List<Lawyer>> firmLawyers = new java.util.HashMap<>();

        @Override
        public Optional<LawyerWithHash> findByEmailWithHash(String email) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public Optional<Lawyer> findById(UUID id) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public List<Lawyer> listByFirm(UUID firmId) {
            return firmLawyers.getOrDefault(firmId, List.of());
        }

        @Override
        public LawyerWithHash create(UUID firmId, String name, String email, String passwordHash) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public Firm createFirm(String name) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public Optional<LawyerWithHash> findByIdWithHash(UUID id) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public Optional<Lawyer> updateName(UUID id, String name) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }

        @Override
        public void updatePassword(UUID id, String newPasswordHash) {
            throw new UnsupportedOperationException("not needed for the scan test");
        }
    }

    /** I-52: defaults every Lawyer to enabled, same "no row yet" semantics as the real repository. */
    static class InMemoryLawyerPreferencesRepository implements LawyerPreferencesRepository {
        final Map<UUID, LawyerPreferences> byLawyer = new HashMap<>();

        @Override
        public Optional<LawyerPreferences> findByLawyerId(UUID lawyerId) {
            return Optional.ofNullable(byLawyer.get(lawyerId));
        }

        @Override
        public LawyerPreferences upsert(UUID lawyerId, boolean deadlineRemindersEnabled) {
            LawyerPreferences updated = new LawyerPreferences(lawyerId, deadlineRemindersEnabled);
            byLawyer.put(lawyerId, updated);
            return updated;
        }
    }

    private InMemoryDeadlineRepository deadlines;
    private InMemoryNotificationRepository notifications;
    private InMemoryLawyerRepository lawyers;
    private InMemoryLawyerPreferencesRepository preferences;
    private NotificationScanService scanService;
    private final UUID firmId = UUID.randomUUID();
    private final UUID matterId = UUID.randomUUID();
    private final LocalDate today = LocalDate.of(2026, 9, 10);

    private Lawyer aLawyer() {
        return new Lawyer(UUID.randomUUID(), firmId, "Test Lawyer", "lawyer@example.com", LawyerRole.owner, Instant.now());
    }

    @BeforeEach
    void setUp() {
        deadlines = new InMemoryDeadlineRepository();
        notifications = new InMemoryNotificationRepository();
        lawyers = new InMemoryLawyerRepository();
        preferences = new InMemoryLawyerPreferencesRepository();
        scanService = new NotificationScanService(deadlines, notifications, lawyers, preferences);
    }

    @Test
    void createsANotificationForEveryLawyerInTheFirmWhenADeadlineIsDueToday_REQ009() {
        Deadline dueToday = new Deadline(UUID.randomUUID(), matterId, "File response", today, DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlines.openDeadlines.add(new DeadlineRepository.DeadlineWithFirm(dueToday, firmId));
        Lawyer lawyer1 = aLawyer();
        Lawyer lawyer2 = aLawyer();
        lawyers.firmLawyers.put(firmId, List.of(lawyer1, lawyer2));

        int created = scanService.scan(today);

        assertEquals(2, created);
        assertEquals(2, notifications.notifications.size());
        assertTrue(notifications.notifications.stream().anyMatch(n -> n.lawyerId().equals(lawyer1.id())));
        assertTrue(notifications.notifications.stream().anyMatch(n -> n.lawyerId().equals(lawyer2.id())));
    }

    @Test
    void createsANotificationOnTheLeadDaysBeforeCutoff_REQ009() {
        Deadline dueInThreeDays = new Deadline(UUID.randomUUID(), matterId, "File response", today.plusDays(3), DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlines.openDeadlines.add(new DeadlineRepository.DeadlineWithFirm(dueInThreeDays, firmId));
        lawyers.firmLawyers.put(firmId, List.of(aLawyer()));

        int created = scanService.scan(today);

        assertEquals(1, created);
    }

    @Test
    void createsNothingWhenTodayIsNotANotificationDay() {
        Deadline dueFarAway = new Deadline(UUID.randomUUID(), matterId, "File response", today.plusDays(20), DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlines.openDeadlines.add(new DeadlineRepository.DeadlineWithFirm(dueFarAway, firmId));
        lawyers.firmLawyers.put(firmId, List.of(aLawyer()));

        assertEquals(0, scanService.scan(today));
        assertTrue(notifications.notifications.isEmpty());
    }

    @Test
    void isIdempotentWithinTheSameDay_noDoubleSendOnARepeatScan() {
        // Real bug caught here: idempotency is checked against a
        // Notification's real createdAt timestamp (Instant.now()), not
        // against the simulated `today` used elsewhere in this test file —
        // exactly like production, where the @Scheduled caller always
        // passes LocalDate.now(), so this test does the same rather than
        // the fixed `today` constant.
        LocalDate now = LocalDate.now();
        Deadline dueToday = new Deadline(UUID.randomUUID(), matterId, "File response", now, DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlines.openDeadlines.add(new DeadlineRepository.DeadlineWithFirm(dueToday, firmId));
        lawyers.firmLawyers.put(firmId, List.of(aLawyer()));

        int firstRun = scanService.scan(now);
        int secondRun = scanService.scan(now); // simulates a worker restart re-running the same hourly scan

        assertEquals(1, firstRun);
        assertEquals(0, secondRun, "a second scan the same day must not create a duplicate Notification");
        assertEquals(1, notifications.notifications.size());
    }

    @Test
    void aFirmWithNoLawyersProducesNoNotifications() {
        Deadline dueToday = new Deadline(UUID.randomUUID(), matterId, "File response", today, DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlines.openDeadlines.add(new DeadlineRepository.DeadlineWithFirm(dueToday, firmId));
        // lawyers.firmLawyers left empty for this firm

        assertEquals(0, scanService.scan(today));
    }

    // --- I-52: per-Lawyer opt-out ---

    @Test
    void skipsALawyerWhoHasTurnedDeadlineRemindersOff() {
        Deadline dueToday = new Deadline(UUID.randomUUID(), matterId, "File response", today, DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlines.openDeadlines.add(new DeadlineRepository.DeadlineWithFirm(dueToday, firmId));
        Lawyer optedOut = aLawyer();
        lawyers.firmLawyers.put(firmId, List.of(optedOut));
        preferences.upsert(optedOut.id(), false);

        int created = scanService.scan(today);

        assertEquals(0, created);
        assertTrue(notifications.notifications.isEmpty());
    }

    @Test
    void stillNotifiesOtherFirmMembersWhoseReminderIsStillOn() {
        Deadline dueToday = new Deadline(UUID.randomUUID(), matterId, "File response", today, DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlines.openDeadlines.add(new DeadlineRepository.DeadlineWithFirm(dueToday, firmId));
        Lawyer optedOut = aLawyer();
        Lawyer stillOn = aLawyer();
        lawyers.firmLawyers.put(firmId, List.of(optedOut, stillOn));
        preferences.upsert(optedOut.id(), false);

        int created = scanService.scan(today);

        assertEquals(1, created);
        assertTrue(notifications.notifications.stream().anyMatch(n -> n.lawyerId().equals(stillOn.id())));
        assertTrue(notifications.notifications.stream().noneMatch(n -> n.lawyerId().equals(optedOut.id())));
    }

    @Test
    void aLawyerWhoNeverSetAPreferenceStillGetsNotified_defaultsToEnabled() {
        Deadline dueToday = new Deadline(UUID.randomUUID(), matterId, "File response", today, DeadlineStatus.open, DeadlinePriority.standard, 3, null, null);
        deadlines.openDeadlines.add(new DeadlineRepository.DeadlineWithFirm(dueToday, firmId));
        lawyers.firmLawyers.put(firmId, List.of(aLawyer())); // preferences repo never touched for this lawyer

        assertEquals(1, scanService.scan(today));
    }
}
