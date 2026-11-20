import re
from dataclasses import dataclass
from datetime import datetime


class InvalidTemplateError(ValueError):
    pass


PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


@dataclass(frozen=True)
class NewTemplate:
    firm_id: str | None
    name: str
    description: str | None
    body: str


@dataclass(frozen=True)
class Template:
    """SD-007: a pre-authored, placeholder-bearing document template.
    firm_id None means a system template available to every Firm; a real value
    means a Firm-custom template visible only to that Firm. create() exists for
    completeness — today's only Templates come from a one-time SQL seed."""

    id: str
    firm_id: str | None
    name: str
    description: str | None
    body: str
    created_at: datetime

    @staticmethod
    def create(firm_id: str | None, name: str | None, description: str | None, body: str | None) -> NewTemplate:
        trimmed_name = (name or "").strip()
        if not trimmed_name:
            raise InvalidTemplateError("A Template name is required.")
        trimmed_body = (body or "").strip()
        if not trimmed_body:
            raise InvalidTemplateError("A Template must have body content.")
        trimmed_description = description.strip() if description is not None else None
        return NewTemplate(firm_id, trimmed_name, trimmed_description or None, trimmed_body)

    def placeholders(self) -> list[str]:
        """Distinct {{placeholder}} names referenced in the body, in first-appearance order."""
        return list(dict.fromkeys(PLACEHOLDER.findall(self.body)))

    def render(self, fields: dict[str, str | None] | None) -> str:
        """REQ-015: substitutes every placeholder with its supplied value. Every
        placeholder the body references must have a non-blank value — a legal
        draft with a literal "{{counterparty_name}}" left in it is worse than
        refusing to generate, so this fails loudly and names what's missing."""
        missing = [name for name in self.placeholders() if not ((fields or {}).get(name) or "").strip()]
        if missing:
            raise InvalidTemplateError("Missing a value for: " + ", ".join(missing))
        return PLACEHOLDER.sub(lambda m: fields[m.group(1)], self.body)
