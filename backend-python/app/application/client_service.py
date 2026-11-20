from __future__ import annotations

from app.application.crud_ports import ClientRepository, MatterRepository, UnitOfWork
from app.application.matter_service import MatterService
from app.domain.client import Client


class ClientService:
    """delete_cascade() is a real product decision — deleting a Client
    cascade-deletes everything under it — but each Matter's own cascade lives
    in MatterService.delete_cascade, the same single implementation a direct
    single-Matter delete uses."""

    def __init__(self, repository: ClientRepository, matter_repository: MatterRepository, matter_service: MatterService, unit_of_work: UnitOfWork) -> None:
        self.repository = repository
        self.matter_repository = matter_repository
        self.matter_service = matter_service
        self.unit_of_work = unit_of_work

    def create(self, firm_id: str, name: str | None, contact_email: str | None, contact_phone: str | None, notes: str | None) -> Client:
        return self.repository.create(Client.create(firm_id, name, contact_email, contact_phone, notes))

    def list(self, firm_id: str) -> list[Client]:
        return self.repository.list_by_firm(firm_id)

    def get(self, firm_id: str, client_id: str) -> Client | None:
        return self.repository.find_by_id(firm_id, client_id)

    def update(self, firm_id: str, client_id: str, name: str | None, contact_email: str | None, contact_phone: str | None, notes: str | None) -> Client | None:
        """Validated by the domain layer before the repository is ever touched, same as create()."""
        validated = Client.update(name, contact_email, contact_phone, notes)
        return self.repository.update(firm_id, client_id, validated.name, validated.contact_email, validated.contact_phone, validated.notes)

    def delete_cascade(self, firm_id: str, client_id: str) -> bool:
        """Irreversible: deletes every Matter under the Client (each via
        MatterService.delete_cascade), then the Client — all in one transaction,
        since no FK-level ON DELETE CASCADE exists from clients -> matters.
        No confirmation logic here; that's the frontend's job.

        BR-008: returns False (nothing deleted) for an unknown/other-Firm Client."""
        with self.unit_of_work.transaction():
            if self.repository.find_by_id(firm_id, client_id) is None:
                return False

            for matter in self.matter_repository.list_by_client(firm_id, client_id):
                self.matter_service.delete_cascade(firm_id, matter.id)

            return self.repository.delete(firm_id, client_id)
