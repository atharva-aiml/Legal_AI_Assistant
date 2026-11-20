from __future__ import annotations

from app.application.crud_ports import TemplateRepository
from app.domain.template import Template


class TemplateService:
    """SD-007: system Templates plus the caller's Firm's own."""

    def __init__(self, repository: TemplateRepository) -> None:
        self.repository = repository

    def list(self, firm_id: str) -> list[Template]:
        return self.repository.list_available(firm_id)

    def get(self, firm_id: str, template_id: str) -> Template | None:
        return self.repository.find_available(firm_id, template_id)
