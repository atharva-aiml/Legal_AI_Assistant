from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.application.notification_service import NotificationScanService, NotificationService
from app.application.preferences_service import LawyerPreferencesService
from app.domain.clock import utc_today
from app.domain.deadline import DeadlineStatus
from app.domain.matter import MatterStatus, NewMatter
from tests.application.crud_fakes import (
    InMemoryDeadlineRepository,
    InMemoryLawyerRepository,
    InMemoryMatterRepository,
    InMemoryNotificationRepository,
    InMemoryPreferencesRepository,
)

TODAY = utc_today()
FIRM = "firm-a"


# ---------------------------------------------------------------- NotificationService (in-app inbox, I-44)


@pytest.fixture
def inbox():
    repo = InMemoryNotificationRepository()
    return SimpleNamespace(repo=repo, service=NotificationService(repo))


def test_lists_only_the_calling_lawyers_notifications_newest_first(inbox):
    older = inbox.repo.add("ada")
    newer = inbox.repo.add("ada")
    inbox.repo.add("bob")
    assert inbox.service.list("ada") == [newer, older]


def test_marks_a_notification_read(inbox):
    n = inbox.repo.add("ada")
    assert inbox.service.mark_read("ada", n.id).read_at is not None


def test_marking_another_lawyers_notification_read_returns_none(inbox):
    n = inbox.repo.add("bob")
    assert inbox.service.mark_read("ada", n.id) is None
    assert inbox.repo.notifications[n.id].read_at is None


def test_mark_all_read_counts_only_the_callers_unread_ones_and_is_idempotent(inbox):
    inbox.repo.add("ada")
    inbox.repo.add("ada")
    inbox.repo.add("ada", read=True)
    bobs = inbox.repo.add("bob")
    assert inbox.service.mark_all_read("ada") == 2
    assert inbox.service.mark_all_read("ada") == 0
    assert inbox.repo.notifications[bobs.id].read_at is None


# ---------------------------------------------------------------- NotificationScanService (SD-006, REQ-009, I-52)


@pytest.fixture
def scan():
    matters = InMemoryMatterRepository()
    matter = matters.create(NewMatter(FIRM, "client", "Lease", MatterStatus.open))
    deadlines = InMemoryDeadlineRepository(matters)
    lawyers = InMemoryLawyerRepository()
    notifications = InMemoryNotificationRepository()
    prefs = InMemoryPreferencesRepository()
    return SimpleNamespace(
        matter=matter, deadlines=deadlines, lawyers=lawyers, notifications=notifications, prefs=prefs,
        service=NotificationScanService(deadlines, notifications, lawyers, prefs),
    )


def test_notifies_every_firm_lawyer_on_the_lead_day_and_the_due_day(scan):
    ada, bob = scan.lawyers.add(FIRM), scan.lawyers.add(FIRM)
    scan.lawyers.add("other-firm")
    scan.deadlines.add(scan.matter.id, "Serve notice", due_date=TODAY + timedelta(days=3), lead_days=3)
    scan.deadlines.add(scan.matter.id, "Call client", due_date=TODAY, lead_days=5)

    assert scan.service.scan(TODAY) == 4
    messages = sorted(n.message for n in scan.notifications.list_by_lawyer(ada.id))
    assert messages == ['"Call client" is due today.', f'"Serve notice" is due on {(TODAY + timedelta(days=3)).isoformat()}.']
    assert len(scan.notifications.list_by_lawyer(bob.id)) == 2


def test_creates_nothing_when_today_is_not_a_notification_day(scan):
    scan.lawyers.add(FIRM)
    scan.deadlines.add(scan.matter.id, due_date=TODAY + timedelta(days=2), lead_days=3)
    assert scan.service.scan(TODAY) == 0


def test_skips_completed_deadlines(scan):
    scan.lawyers.add(FIRM)
    scan.deadlines.add(scan.matter.id, due_date=TODAY, status=DeadlineStatus.complete)
    assert scan.service.scan(TODAY) == 0


def test_is_idempotent_within_the_same_day_no_double_send_on_a_repeat_scan(scan):
    scan.lawyers.add(FIRM)
    scan.deadlines.add(scan.matter.id, due_date=TODAY)
    assert scan.service.scan(TODAY) == 1
    assert scan.service.scan(TODAY) == 0


def test_a_firm_with_no_lawyers_produces_no_notifications(scan):
    scan.deadlines.add(scan.matter.id, due_date=TODAY)
    assert scan.service.scan(TODAY) == 0


def test_skips_a_lawyer_who_turned_reminders_off_but_still_notifies_the_rest(scan):
    opted_out, still_on = scan.lawyers.add(FIRM), scan.lawyers.add(FIRM)
    scan.prefs.upsert(opted_out.id, False)
    scan.deadlines.add(scan.matter.id, due_date=TODAY)
    assert scan.service.scan(TODAY) == 1
    assert scan.notifications.list_by_lawyer(opted_out.id) == []
    assert len(scan.notifications.list_by_lawyer(still_on.id)) == 1


def test_a_lawyer_who_never_set_a_preference_still_gets_notified(scan):
    lawyer = scan.lawyers.add(FIRM)
    scan.deadlines.add(scan.matter.id, due_date=TODAY)
    scan.service.scan(TODAY)
    assert len(scan.notifications.list_by_lawyer(lawyer.id)) == 1


# ---------------------------------------------------------------- LawyerPreferencesService (I-52)


def test_preferences_default_to_enabled_persist_and_never_leak_between_lawyers():
    service = LawyerPreferencesService(InMemoryPreferencesRepository())
    assert service.get("ada").deadline_reminders_enabled is True
    assert service.update("ada", False).deadline_reminders_enabled is False
    assert service.get("ada").deadline_reminders_enabled is False
    assert service.get("bob").deadline_reminders_enabled is True
    assert service.update("ada", True).deadline_reminders_enabled is True
