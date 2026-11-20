import pytest

from app.domain.client import Client, InvalidClientError
from app.domain.lawyer import InvalidLawyerError, Lawyer, LawyerPreferences
from app.domain.matter import InvalidMatterError, Matter, MatterStatus

# ---------------------------------------------------------------- Client (BR-008, I-17)


def test_creates_a_client_with_trimmed_name():
    c = Client.create("firm", "  Acme Corp  ", "a@acme.test", "123", "VIP")
    assert c.name == "Acme Corp"
    assert c.firm_id == "firm"


def test_blank_optional_fields_become_none_not_empty_strings():
    c = Client.create("firm", "Acme", "", "   ", None)
    assert c.contact_email is None and c.contact_phone is None and c.notes is None


@pytest.mark.parametrize("name", [None, "", "   "])
def test_rejects_a_client_with_no_name(name):
    with pytest.raises(InvalidClientError, match="Name is required"):
        Client.create("firm", name, None, None, None)


def test_rejects_a_client_with_no_firm_br008():
    with pytest.raises(InvalidClientError, match="BR-008"):
        Client.create(None, "Acme", None, None, None)


def test_update_returns_trimmed_fields_with_blanks_normalized_to_none():
    u = Client.update("  Acme Two ", " ", "555", "")
    assert (u.name, u.contact_email, u.contact_phone, u.notes) == ("Acme Two", None, "555", None)


def test_update_rejects_an_empty_name_same_invariant_as_create():
    with pytest.raises(InvalidClientError):
        Client.update("  ", None, None, None)


# ---------------------------------------------------------------- Matter (BR-001, I-35)


def test_creates_a_matter_with_status_open_by_default():
    m = Matter.create("firm", "client", "Lease review")
    assert m.status == MatterStatus.open


def test_matter_trims_whitespace_from_the_title():
    assert Matter.create("firm", "client", "  Lease review  ").title == "Lease review"


@pytest.mark.parametrize("title", [None, "", "  "])
def test_rejects_a_matter_with_no_title(title):
    with pytest.raises(InvalidMatterError, match="title is required"):
        Matter.create("firm", "client", title)


def test_rejects_a_matter_with_no_client_br001():
    with pytest.raises(InvalidMatterError, match="BR-001"):
        Matter.create("firm", None, "Lease review")


def test_rejects_a_matter_with_no_firm_br008():
    with pytest.raises(InvalidMatterError, match="BR-008"):
        Matter.create(None, "client", "Lease review")


def test_rename_returns_the_trimmed_title():
    assert Matter.rename_title("  New title ") == "New title"


def test_rename_rejects_an_empty_title():
    with pytest.raises(InvalidMatterError):
        Matter.rename_title("   ")


def test_validate_reopen_allows_a_closed_matter():
    Matter.validate_reopen(MatterStatus.closed)


def test_validate_reopen_rejects_an_already_open_matter():
    with pytest.raises(InvalidMatterError, match="Only a Closed Matter"):
        Matter.validate_reopen(MatterStatus.open)


# ---------------------------------------------------------------- Lawyer (I-51) / preferences (I-52)


def test_lawyer_name_is_trimmed():
    assert Lawyer.validate_name("  Ada ") == "Ada"


@pytest.mark.parametrize("name", [None, "", "   "])
def test_rejects_a_blank_or_missing_lawyer_name(name):
    with pytest.raises(InvalidLawyerError, match="Name is required"):
        Lawyer.validate_name(name)


def test_accepts_an_eight_character_password():
    assert Lawyer.validate_new_password("12345678") == "12345678"


@pytest.mark.parametrize("password", [None, "", "1234567"])
def test_rejects_a_missing_or_short_password(password):
    with pytest.raises(InvalidLawyerError, match="at least 8"):
        Lawyer.validate_new_password(password)


def test_default_preferences_are_enabled():
    assert LawyerPreferences.default_for("lawyer").deadline_reminders_enabled is True


def test_rejects_preferences_with_no_lawyer():
    with pytest.raises(InvalidLawyerError):
        LawyerPreferences.default_for(None)
