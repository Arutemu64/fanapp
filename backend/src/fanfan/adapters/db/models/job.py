from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.application.dto.jobs import JobStatus


class JobORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    """One handler's run of a domain event, queued for the worker.

    Rows are written inside the same transaction as the aggregate change (the
    transactional outbox), one per handler of the event, then claimed and run
    by the worker (see presentation/worker).
    """

    __tablename__ = "jobs"
    __table_args__ = (
        # Partial index: the worker only ever scans pending jobs by due time, so
        # the hot set stays tiny no matter how big the table grows.
        Index(
            "ix_jobs_pending_run_at",
            "run_at",
            postgresql_where="status = 'pending'",
        ),
        # Serves the retention sweep (delete_finished_before), which filters the
        # exact complement of the index above and so could not use it.
        Index("ix_jobs_finished_at", "finished_at"),
    )

    # The handler that runs the job (presentation/worker/routes).
    name: Mapped[str] = mapped_column(Text())
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB())
    status: Mapped[JobStatus] = str_enum_column(
        JobStatus, name="jobstatus", server_default=JobStatus.PENDING.value
    )
    # When a pending job may next be claimed: at insert, now; after a failure,
    # its retry time; while it runs, the end of its lease. One column for all
    # three keeps the claim a single index range scan.
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Attempts so far, counted at claim time so a worker that died mid-run uses
    # one up too. Every settle names the attempt it belongs to, which stops a
    # worker whose lease lapsed from overwriting a later attempt's outcome.
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Sentry propagation headers of the request or task that wrote the event,
    # so the job's work joins the producer's trace even though the worker runs
    # outside it. NULL when nothing was traced.
    trace_headers: Mapped[dict[str, str] | None] = mapped_column(JSONB())
