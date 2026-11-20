from app.application.crud_ports import LawyerPreferencesRepository
from app.domain.lawyer import LawyerPreferences


class LawyerPreferencesService:
    """I-52: which notification types a Lawyer wants to receive."""

    def __init__(self, repository: LawyerPreferencesRepository) -> None:
        self.repository = repository

    def get(self, lawyer_id: str) -> LawyerPreferences:
        return self.repository.find_by_lawyer_id(lawyer_id) or LawyerPreferences.default_for(lawyer_id)

    def update(self, lawyer_id: str, deadline_reminders_enabled: bool) -> LawyerPreferences:
        return self.repository.upsert(lawyer_id, deadline_reminders_enabled)
