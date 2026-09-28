"""Ops convenience: `uv run python scripts/run_notification_sweep.py`.

Runs one full tracking sweep — change detection, deadline-reminder/
change/unavailability notification generation, and (if configured)
email delivery — against whatever database `DATABASE_URL` points at.

Deliberately a script, not a running process: **nothing in this
codebase invokes this on a schedule today**. A real deployment invokes
it on a recurring basis via an external scheduler (cron, a systemd
timer, a managed platform's scheduled-job feature) — this script is the
safe, documented execution boundary that scheduler calls, per this
phase's explicit "do not pretend a recurring process is running when it
is not."
"""

import asyncio

from app.core.config import get_settings
from app.core.db import model_registry  # noqa: F401 -- see scripts/seed_job_fixtures.py
from app.core.db.session import get_sessionmaker
from app.notifications.email_provider import get_email_provider
from app.notifications.jobs import deliver_notification_emails, run_notification_sweep


async def main() -> None:
    settings = get_settings()
    session = get_sessionmaker()()
    try:
        summary = run_notification_sweep(
            session,
            reminder_days_before=settings.deadline_reminder_days_before,
            email_provider=None,
            email_max_attempts=settings.notification_delivery_max_attempts,
        )
        print(
            f"Change records detected: {summary.change_records_detected}\n"
            f"Deadline reminders created: {summary.deadline_reminders_created}\n"
            f"Change notifications created: {summary.change_notifications_created}\n"
            f"Unavailability notifications created: {summary.unavailability_notifications_created}"
        )

        email_provider = get_email_provider()
        delivery = await deliver_notification_emails(
            session,
            email_provider=email_provider,
            max_attempts=settings.notification_delivery_max_attempts,
        )
        if not delivery.provider_configured:
            print("Email delivery: no provider configured (EMAIL_PROVIDER=none) — skipped.")
        else:
            print(
                f"Email delivery: attempted={delivery.attempted} sent={delivery.sent} "
                f"failed={delivery.failed}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
