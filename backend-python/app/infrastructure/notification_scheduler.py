import logging
import threading

from app.application.notification_service import NotificationScanService
from app.domain.clock import utc_today

log = logging.getLogger(__name__)

INITIAL_DELAY_SECONDS = 60
INTERVAL_SECONDS = 60 * 60


class NotificationScanScheduler:
    """SD-006's clock trigger: runs the scan 60s after startup, then hourly
    (same cadence as the former Java @Scheduled job). Idempotency lives in
    NotificationScanService/NotificationRepository (per deadline, lawyer, UTC
    day), so a missed tick or a restart mid-hour can never double-send — this
    only decides *when* to call scan()."""

    def __init__(self, scan_service: NotificationScanService) -> None:
        self.scan_service = scan_service
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="notification-scan", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        if self._stop.wait(INITIAL_DELAY_SECONDS):
            return
        while True:
            self.run_once()
            if self._stop.wait(INTERVAL_SECONDS):
                return

    def run_once(self) -> int:
        try:
            created = self.scan_service.scan(utc_today())
        except Exception:
            log.exception("Deadline notification scan failed")
            return 0
        if created > 0:
            log.info("Deadline notification scan created %d notification(s).", created)
        return created
