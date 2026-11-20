from app.application.crud_ports import MatterViewRepository
from app.domain.matter import MatterView

# I-07: "recent" is a short, dashboard-widget-sized list, not a full history.
RECENT_LIMIT = 5


class MatterViewService:
    def __init__(self, repository: MatterViewRepository) -> None:
        self.repository = repository

    def record_view(self, lawyer_id: str, matter_id: str) -> None:
        self.repository.record_view(lawyer_id, matter_id)

    def list_recently_viewed(self, lawyer_id: str) -> list[MatterView]:
        return self.repository.list_recently_viewed(lawyer_id, RECENT_LIMIT)
