from __future__ import annotations

from datetime import date

from app.application.crud_ports import DeadlineRepository
from app.domain.deadline import Deadline, DeadlinePriority, DeadlineStatus


class DeadlineService:
    """Depends only on its own repository — Matter existence/ownership is
    checked by the web layer before this is ever called."""

    def __init__(self, repository: DeadlineRepository) -> None:
        self.repository = repository

    def create(self, matter_id: str, title: str | None, due_date: date | None, priority: DeadlinePriority | None, notification_lead_days: int | None) -> Deadline:
        """Validated by the domain layer (BR-004/BR-009) before the repository is ever touched."""
        return self.repository.create(Deadline.create(matter_id, title, due_date, priority, notification_lead_days))

    def list(self, firm_id: str, matter_id: str) -> list[Deadline]:
        return self.repository.list_by_matter(firm_id, matter_id)

    def get(self, firm_id: str, deadline_id: str) -> Deadline | None:
        return self.repository.find_by_id(firm_id, deadline_id)

    def update(
        self,
        firm_id: str,
        deadline_id: str,
        title: str | None,
        due_date: date | None,
        status: DeadlineStatus | None,
        priority: DeadlinePriority | None,
        notification_lead_days: int | None,
    ) -> Deadline | None:
        """PATCH semantics — omitted (None) fields keep their current value.
        Only a newly supplied due date is checked against BR-009, so marking an
        already-overdue Deadline complete is still allowed."""
        current = self.repository.find_by_id(firm_id, deadline_id)
        if current is None:
            return None
        return self.repository.update(
            firm_id,
            deadline_id,
            Deadline.validate_title(title) if title is not None else current.title,
            Deadline.validate_due_date(due_date) if due_date is not None else current.due_date,
            status if status is not None else current.status,
            priority if priority is not None else current.priority,
            Deadline.validate_lead_days(notification_lead_days) if notification_lead_days is not None else current.notification_lead_days,
        )

    def upcoming(self, firm_id: str, days: int) -> list[Deadline]:
        return self.repository.list_upcoming(firm_id, days)
