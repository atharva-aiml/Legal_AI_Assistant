package com.legalai.backend.infrastructure.scheduling;

import com.legalai.backend.application.notification.NotificationScanService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDate;

/**
 * SD-006's clock trigger: runs the notification scan hourly. Idempotency
 * lives in NotificationScanService/NotificationRepository (per deadline,
 * lawyer, day), so a missed tick or a restart mid-hour can never double-send
 * — this class only decides *when* to call scan(), not whether it's safe to.
 */
@Component
public class NotificationScanScheduler {

    private static final Logger log = LoggerFactory.getLogger(NotificationScanScheduler.class);

    private final NotificationScanService scanService;

    public NotificationScanScheduler(NotificationScanService scanService) {
        this.scanService = scanService;
    }

    @Scheduled(fixedRate = 60 * 60 * 1000, initialDelay = 60 * 1000)
    public void run() {
        int created = scanService.scan(LocalDate.now());
        if (created > 0) {
            log.info("Deadline notification scan created {} notification(s).", created);
        }
    }
}
