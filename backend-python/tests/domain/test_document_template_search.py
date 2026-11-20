from datetime import date

import pytest

from app.domain.document import Document, InvalidDocumentError
from app.domain.notification import InvalidNotificationError, Notification
from app.domain.search import InvalidSearchError, RecentSearch, SearchQuery
from app.domain.matter import MatterStatus
from app.domain.template import InvalidTemplateError, Template

PDF = "application/pdf"

# ---------------------------------------------------------------- Document (BR-002, REQ-003, SD-007)


def test_creates_a_document_ready_to_be_stored():
    d = Document.create("matter", "lawyer", "  lease.pdf ", "key.pdf", PDF, 10)
    assert d.file_name == "lease.pdf"


def test_rejects_an_unsupported_mime_type_req003():
    with pytest.raises(InvalidDocumentError, match="REQ-003"):
        Document.create("matter", "lawyer", "notes.txt", "key", "text/plain", 10)


def test_rejects_an_empty_file():
    with pytest.raises(InvalidDocumentError, match="empty"):
        Document.create("matter", "lawyer", "a.pdf", "key", PDF, 0)


def test_rejects_a_missing_file_name():
    with pytest.raises(InvalidDocumentError, match="file name"):
        Document.create("matter", "lawyer", "  ", "key", PDF, 10)


def test_rejects_a_document_with_no_matter_br002():
    with pytest.raises(InvalidDocumentError, match="BR-002"):
        Document.create(None, "lawyer", "a.pdf", "key", PDF, 10)


def test_a_draft_accepts_text_plain_outside_the_upload_allow_list():
    d = Document.create_draft("matter", "lawyer", "NDA.txt", "key", "text/plain", 10, "template")
    assert d.mime_type == "text/plain"


def test_rejects_a_draft_with_no_source_template():
    with pytest.raises(InvalidDocumentError, match="Template"):
        Document.create_draft("matter", "lawyer", "NDA.txt", "key", "text/plain", 10, None)


def test_rejects_a_draft_with_empty_content():
    with pytest.raises(InvalidDocumentError, match="empty"):
        Document.create_draft("matter", "lawyer", "NDA.txt", "key", "text/plain", 0, "template")


def test_rejects_a_draft_with_no_storage_key():
    with pytest.raises(InvalidDocumentError, match="storage location"):
        Document.create_draft("matter", "lawyer", "NDA.txt", " ", "text/plain", 10, "template")


# ---------------------------------------------------------------- Template (REQ-015)


def _template(body: str) -> Template:
    return Template("id", None, "NDA", None, body, None)


def test_creates_a_template_trimming_name_and_body():
    t = Template.create(None, "  NDA ", " desc ", "  body  ")
    assert (t.firm_id, t.name, t.description, t.body) == (None, "NDA", "desc", "body")


def test_blank_description_becomes_none():
    assert Template.create("firm", "NDA", "   ", "body").description is None


def test_rejects_a_blank_template_name_or_body():
    with pytest.raises(InvalidTemplateError):
        Template.create(None, " ", None, "body")
    with pytest.raises(InvalidTemplateError):
        Template.create(None, "NDA", None, "  ")


def test_placeholders_are_distinct_in_first_appearance_order():
    assert _template("{{b}} {{ a }} {{b}} {{c}}").placeholders() == ["b", "a", "c"]


def test_placeholders_is_empty_when_body_has_none():
    assert _template("plain").placeholders() == []


def test_repeated_placeholders_are_all_substituted_and_values_are_literal():
    assert _template("{{x}}-{{ x }}").render({"x": "$1\\n"}) == "$1\\n-$1\\n"


def test_renders_body_unchanged_when_there_are_no_placeholders():
    assert _template("plain body").render(None) == "plain body"


@pytest.mark.parametrize("fields", [None, {}, {"party": "  "}])
def test_rejects_rendering_when_a_placeholder_value_is_missing_or_blank(fields):
    with pytest.raises(InvalidTemplateError, match="Missing a value for: party"):
        _template("Between {{party}}").render(fields)


# ---------------------------------------------------------------- Notification (REQ-009)


def test_creates_a_notification_with_trimmed_message():
    assert Notification.create("lawyer", "deadline", "  due soon ").message == "due soon"


@pytest.mark.parametrize("lawyer, deadline, message", [(None, "d", "m"), ("l", None, "m"), ("l", "d", "  ")])
def test_rejects_an_incomplete_notification(lawyer, deadline, message):
    with pytest.raises(InvalidNotificationError):
        Notification.create(lawyer, deadline, message)


# ---------------------------------------------------------------- Search (REQ-011) / recent searches (I-48)


def test_parses_and_trims_a_plain_text_query():
    q = SearchQuery.parse("  lease ", None, None, None)
    assert q.q == "lease" and q.status is None


def test_rejects_an_unknown_status():
    with pytest.raises(InvalidSearchError, match="Unknown status: 'pending'"):
        SearchQuery.parse(None, "pending", None, None)


def test_rejects_a_date_range_where_start_is_after_end():
    with pytest.raises(InvalidSearchError, match="start can't be after"):
        SearchQuery.parse(None, None, date(2026, 2, 1), date(2026, 1, 1))


@pytest.mark.parametrize("q, status", [(None, None), ("  ", " ")])
def test_rejects_a_search_with_no_criteria_at_all(q, status):
    with pytest.raises(InvalidSearchError, match="REQ-011"):
        SearchQuery.parse(q, status, None, None)


def test_combines_query_status_and_dates():
    q = SearchQuery.parse("lease", " closed ", date(2026, 1, 1), date(2026, 1, 31))
    assert (q.q, q.status, q.from_date, q.to_date) == ("lease", MatterStatus.closed, date(2026, 1, 1), date(2026, 1, 31))


def test_recent_search_query_is_trimmed_and_blank_rejected():
    assert RecentSearch.validate_query("  acme ") == "acme"
    for blank in (None, "", "  "):
        with pytest.raises(InvalidSearchError):
            RecentSearch.validate_query(blank)
