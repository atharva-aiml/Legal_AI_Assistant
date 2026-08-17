package com.legalai.backend.application.notification;

import com.legalai.backend.application.auth.LawyerRepository;
import com.legalai.backend.application.deadline.DeadlineRepository;
import com.legalai.backend.application.preferences.LawyerPreferencesRepository;
import com.legalai.backend.domain.Deadline;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.domain.LawyerPreferences;
import com.legalai.backend.domain.Notification;
import org.springframework.stereotype.Service;

import java.time.LocalDate;

/**
 * SD-006: the notification scanner's actual logic — separated from the
 * {@code @Scheduled} trigger (infrastructure/scheduling) so it's callable
 * directly from a test or an on-demand admin action, not just the clock.
 * Every Lawyer in the Deadline's Matter's Firm is notified (REQ-014's
 * sharing model), not just whoever created the Deadline — the schema
 * doesn't track a Deadline's creator, and the Firm is the natural
 * ownership boundary for "who should know about this." I-52: except a
 * Lawyer who has explicitly turned Deadline reminders off for themselves —
 * still skipped per-Lawyer, not per-Firm, so the rest of the Firm is unaffected.
 */
@Service
public class NotificationScanService {

    private final DeadlineRepository deadlineRepository;
    private final NotificationRepository notificationRepository;
    private final LawyerRepository lawyerRepository;
    private final LawyerPreferencesRepository preferencesRepository;

    public NotificationScanService(DeadlineRepository deadlineRepository, NotificationRepository notificationRepository,
                                    LawyerRepository lawyerRepository, LawyerPreferencesRepository preferencesRepository) {
        this.deadlineRepository = deadlineRepository;
        this.notificationRepository = notificationRepository;
        this.lawyerRepository = lawyerRepository;
        this.preferencesRepository = preferencesRepository;
    }

    /** @return how many new Notification rows were created — logged by the scheduled caller. */
    public int scan(LocalDate today) {
        int created = 0;
        for (DeadlineRepository.DeadlineWithFirm entry : deadlineRepository.listAllOpenWithFirm()) {
            Deadline deadline = entry.deadline();
            if (!deadline.isNotificationDueOn(today)) {
                continue;
            }

            String message = buildMessage(deadline, today);
            for (Lawyer lawyer : lawyerRepository.listByFirm(entry.firmId())) {
                LawyerPreferences prefs = preferencesRepository.findByLawyerId(lawyer.id())
                        .orElseGet(() -> LawyerPreferences.defaultFor(lawyer.id()));
                if (!prefs.deadlineRemindersEnabled()) {
                    continue;
                }
                if (notificationRepository.existsForDeadlineAndLawyerOnDay(deadline.id(), lawyer.id(), today)) {
                    continue;
                }
                notificationRepository.create(Notification.create(lawyer.id(), deadline.id(), message));
                created++;
            }
        }
        return created;
    }

    private static String buildMessage(Deadline deadline, LocalDate today) {
        if (deadline.dueDate().equals(today)) {
            return "\"" + deadline.title() + "\" is due today.";
        }
        return "\"" + deadline.title() + "\" is due on " + deadline.dueDate() + ".";
    }
}
