from __future__ import annotations

from datetime import date

from app.application.crud_ports import (
    DeadlineRepository,
    LawyerPreferencesRepository,
    LawyerRepository,
    NotificationRepository,
)
from app.domain.deadline import Deadline
from app.domain.lawyer import LawyerPreferences
from app.domain.notification import Notification


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self.repository = repository

    def list(self, lawyer_id: str) -> list[Notification]:
        return self.repository.list_by_lawyer(lawyer_id)

    def mark_read(self, lawyer_id: str, notification_id: str) -> Notification | None:
        return self.repository.mark_read(lawyer_id, notification_id)

    def mark_all_read(self, lawyer_id: str) -> int:
        return self.repository.mark_all_read(lawyer_id)


class NotificationScanService:
    """SD-006: the notification scanner's logic, separate from its clock
    trigger (infrastructure/notification_scheduler.py) so it's callable from
    a test or an on-demand admin action. Every Lawyer in the Deadline's
    Matter's Firm is notified (REQ-014's sharing model) — except, per I-52, a
    Lawyer who has turned Deadline reminders off for themselves."""

    def __init__(
        self,
        deadline_repository: DeadlineRepository,
        notification_repository: NotificationRepository,
        lawyer_repository: LawyerRepository,
        preferences_repository: LawyerPreferencesRepository,
    ) -> None:
        self.deadline_repository = deadline_repository
        self.notification_repository = notification_repository
        self.lawyer_repository = lawyer_repository
        self.preferences_repository = preferences_repository

    def scan(self, today: date) -> int:
        """Returns how many new Notification rows were created."""
        created = 0
        for entry in self.deadline_repository.list_all_open_with_firm():
            deadline = entry.deadline
            if not deadline.is_notification_due_on(today):
                continue

            message = _build_message(deadline, today)
            for lawyer in self.lawyer_repository.list_by_firm(entry.firm_id):
                prefs = self.preferences_repository.find_by_lawyer_id(lawyer.id) or LawyerPreferences.default_for(lawyer.id)
                if not prefs.deadline_reminders_enabled:
                    continue
                if self.notification_repository.exists_for_deadline_and_lawyer_on_day(deadline.id, lawyer.id, today):
                    continue
                self.notification_repository.create(Notification.create(lawyer.id, deadline.id, message))
                created += 1
        return created


def _build_message(deadline: Deadline, today: date) -> str:
    if deadline.due_date == today:
        return f'"{deadline.title}" is due today.'
    return f'"{deadline.title}" is due on {deadline.due_date.isoformat()}.'
