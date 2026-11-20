from sqlalchemy import text

from app.domain.template import Template
from app.infrastructure.persistence.connection import connection
from app.infrastructure.persistence.mappers import to_template


class SqlTemplateRepository:
    def list_available(self, firm_id: str) -> list[Template]:
        with connection() as conn:
            rows = conn.execute(
                text("SELECT * FROM templates WHERE firm_id IS NULL OR firm_id = :firm_id ORDER BY name"), {"firm_id": firm_id}
            ).mappings().all()
        return [to_template(r) for r in rows]

    def find_available(self, firm_id: str, template_id: str) -> Template | None:
        with connection() as conn:
            row = conn.execute(
                text("SELECT * FROM templates WHERE id = :id AND (firm_id IS NULL OR firm_id = :firm_id)"), {"id": template_id, "firm_id": firm_id}
            ).mappings().first()
        return to_template(row) if row else None
