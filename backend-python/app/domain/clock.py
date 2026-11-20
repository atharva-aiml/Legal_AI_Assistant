from datetime import date, datetime, timezone

# The former Java backend ran its JVM with -Duser.timezone=UTC (CLAUDE.md §4's
# Asia/Calcutta gotcha), so every "today" it computed — BR-009's past-date
# check, the Upcoming widget's cutoff, the hourly notification scan — was the
# UTC calendar day, not this machine's local one. Kept identical here so the
# port didn't silently shift any of those day boundaries by 5.5 hours.


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_today() -> date:
    return utc_now().date()
