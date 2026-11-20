import pytest

from app.application.auth_service import (
    AuthService,
    EmailTakenError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    SessionToken,
    ValidationError,
)
from app.domain.lawyer import InvalidLawyerError
from tests.application.crud_fakes import InMemoryLawyerRepository, InMemorySessionRepository, PlainTextPasswordHasher


@pytest.fixture
def lawyers():
    return InMemoryLawyerRepository()


@pytest.fixture
def service(lawyers):
    return AuthService(lawyers, InMemorySessionRepository(lawyers), PlainTextPasswordHasher())


def test_register_creates_a_firm_and_an_owner_and_a_resolvable_session(service, lawyers):
    result = service.register("  Ada  ", "  Ada@Example.COM ", "password1")
    assert result.lawyer.name == "Ada"
    assert result.lawyer.email == "ada@example.com"
    assert result.lawyer.role == "owner"
    assert lawyers.firms[result.lawyer.firm_id].name == "Ada's Firm"
    assert service.resolve_session(result.raw_session_token) == result.lawyer


@pytest.mark.parametrize("name, email, password", [("", "a@x.com", "password1"), ("A", " ", "password1"), ("A", "a@x.com", "short"), ("A", "a@x.com", None)])
def test_register_rejects_missing_fields_or_a_short_password(service, name, email, password):
    with pytest.raises(ValidationError):
        service.register(name, email, password)


def test_register_rejects_a_taken_email_case_insensitively(service):
    service.register("Ada", "ada@example.com", "password1")
    with pytest.raises(EmailTakenError):
        service.register("Other", "ADA@example.com", "password1")


def test_login_succeeds_with_the_right_password(service):
    registered = service.register("Ada", "ada@example.com", "password1")
    assert service.login(" ADA@example.com ", "password1").lawyer == registered.lawyer


@pytest.mark.parametrize("email, password", [("ada@example.com", "wrong-pass"), ("nobody@example.com", "password1"), ("", "password1"), ("ada@example.com", None)])
def test_login_gives_one_identical_error_for_every_failure(service, email, password):
    service.register("Ada", "ada@example.com", "password1")
    with pytest.raises(InvalidCredentialsError, match="Incorrect email or password."):
        service.login(email, password)


def test_logout_revokes_the_session_server_side(service):
    token = service.register("Ada", "ada@example.com", "password1").raw_session_token
    service.logout(token)
    assert service.resolve_session(token) is None


def test_an_unknown_or_missing_token_resolves_to_nobody(service):
    assert service.resolve_session(None) is None
    assert service.resolve_session("deadbeef") is None


def test_session_tokens_are_256_bit_random_and_stored_only_as_sha256():
    raw = SessionToken.generate_raw_token()
    assert len(raw) == 64 and raw != SessionToken.generate_raw_token()
    assert SessionToken.hash("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_reports_an_unregistered_email_as_available(service):
    assert service.is_email_available("new@example.com") is True


def test_availability_check_matches_register_normalization(service):
    service.register("Ada", "ada@example.com", "password1")
    assert service.is_email_available("  ADA@Example.com ") is False


@pytest.mark.parametrize("email", [None, "", "   "])
def test_treats_a_blank_email_as_unavailable_avoiding_a_false_available_hint(service, email):
    assert service.is_email_available(email) is False


def test_updates_and_trims_the_lawyers_name(service):
    lawyer = service.register("Ada", "ada@example.com", "password1").lawyer
    assert service.update_name(lawyer.id, "  Ada L. ").name == "Ada L."


def test_rejects_a_blank_new_name(service):
    lawyer = service.register("Ada", "ada@example.com", "password1").lawyer
    with pytest.raises(InvalidLawyerError):
        service.update_name(lawyer.id, " ")


def test_changes_the_password_when_the_current_password_is_correct(service):
    lawyer = service.register("Ada", "ada@example.com", "password1").lawyer
    service.change_password(lawyer.id, "password1", "password2")
    assert service.login("ada@example.com", "password2").lawyer.id == lawyer.id
    with pytest.raises(InvalidCredentialsError):
        service.login("ada@example.com", "password1")


def test_rejects_a_change_with_the_wrong_current_password(service):
    lawyer = service.register("Ada", "ada@example.com", "password1").lawyer
    with pytest.raises(IncorrectPasswordError):
        service.change_password(lawyer.id, "nope-nope", "password2")


def test_rejects_a_new_password_shorter_than_eight_characters(service):
    lawyer = service.register("Ada", "ada@example.com", "password1").lawyer
    with pytest.raises(InvalidLawyerError):
        service.change_password(lawyer.id, "password1", "short")


def test_lists_only_the_callers_firm_members(service, lawyers):
    a = service.register("Ada", "ada@example.com", "password1").lawyer
    service.register("Bob", "bob@example.com", "password1")
    assert [l.id for l in service.list_firm_members(a.firm_id)] == [a.id]
