from datetime import timedelta

import pytest

from app.domain.clock import utc_today
from app.domain.deadline import Deadline, DeadlinePriority, DeadlineStatus, InvalidDeadlineError

TODAY = utc_today()


def _deadline(due, lead=3, status=DeadlineStatus.open) -> Deadline:
    return Deadline("id", "matter", "File response", due, status, DeadlinePriority.standard, lead, None, None)


def test_creates_a_deadline_with_default_lead_time_and_priority():
    d = Deadline.create("matter", "File response", TODAY + timedelta(days=5), None, None)
    assert d.notification_lead_days == 3
    assert d.priority == DeadlinePriority.standard


def test_trims_whitespace_from_the_title():
    assert Deadline.create("matter", "  File  ", TODAY, None, None).title == "File"


@pytest.mark.parametrize("title", [None, "", "   "])
def test_rejects_a_deadline_with_no_title(title):
    with pytest.raises(InvalidDeadlineError, match="title is required"):
        Deadline.create("matter", title, TODAY, None, None)


def test_rejects_a_deadline_with_no_matter_br004():
    with pytest.raises(InvalidDeadlineError, match="BR-004"):
        Deadline.create(None, "File", TODAY, None, None)


def test_rejects_a_deadline_with_no_due_date_br004():
    with pytest.raises(InvalidDeadlineError, match="must have a due date"):
        Deadline.create("matter", "File", None, None, None)


def test_rejects_a_past_due_date_br009():
    with pytest.raises(InvalidDeadlineError, match="BR-009"):
        Deadline.create("matter", "File", TODAY - timedelta(days=1), None, None)


def test_accepts_a_due_date_of_today():
    assert Deadline.create("matter", "File", TODAY, None, None).due_date == TODAY


def test_rejects_a_negative_notification_lead_time():
    with pytest.raises(InvalidDeadlineError, match="negative"):
        Deadline.create("matter", "File", TODAY, None, -1)


def test_validate_title_trims_and_rejects_empty():
    assert Deadline.validate_title(" x ") == "x"
    with pytest.raises(InvalidDeadlineError):
        Deadline.validate_title(" ")


def test_validate_lead_days_rejects_negative():
    assert Deadline.validate_lead_days(0) == 0
    with pytest.raises(InvalidDeadlineError):
        Deadline.validate_lead_days(-1)


def test_accepts_an_explicit_critical_priority():
    assert Deadline.create("matter", "File", TODAY, DeadlinePriority.critical, None).priority == DeadlinePriority.critical


def test_resolve_priority_defaults_none_to_standard():
    assert Deadline.resolve_priority(None) == DeadlinePriority.standard


def test_notification_is_due_lead_days_before_and_on_the_day():
    d = _deadline(TODAY + timedelta(days=3), lead=3)
    assert d.is_notification_due_on(TODAY)
    assert d.is_notification_due_on(TODAY + timedelta(days=3))


def test_notification_is_not_due_on_an_unrelated_day():
    d = _deadline(TODAY + timedelta(days=3), lead=3)
    assert not d.is_notification_due_on(TODAY + timedelta(days=1))


def test_open_ones_keeps_only_open_deadlines_br003():
    open_one = _deadline(TODAY)
    done = _deadline(TODAY, status=DeadlineStatus.complete)
    assert Deadline.open_ones([open_one, done]) == [open_one]
