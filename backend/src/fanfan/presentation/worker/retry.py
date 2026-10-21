from procrastinate import BaseRetryStrategy, RetryDecision
from procrastinate.jobs import Job

from fanfan.core.exceptions.notifications import NotificationRetryAfter

# Runs of a job (the first one included) before a failing job is given up on.
# Generous because the send tasks spend attempts on Telegram/VK flood-control
# retry-afters, which count like any other failure.
MAX_ATTEMPTS = 20

# Delay before each retry, by runs so far; the last one repeats. Short first
# steps ride out a blip, the 5-minute cap bounds how often a job that keeps
# failing costs a run.
_RETRY_DELAYS_SECONDS = (1, 5, 30, 120, 300)


class BoundedBackoff(BaseRetryStrategy):
    """Retry any failure with a growing delay, up to MAX_ATTEMPTS runs.

    A ``NotificationRetryAfter`` is retried after the delay the channel asked
    for instead, since retrying a flood-controlled send sooner only fails again.
    Procrastinate's own ``RetryStrategy`` has no such hook, hence the subclass
    (https://procrastinate.readthedocs.io/en/stable/howto/advanced/retry.html).
    """

    def get_retry_decision(
        self, *, exception: BaseException, job: Job
    ) -> RetryDecision | None:
        # job.attempts counts the runs before this one.
        runs = job.attempts + 1
        if runs >= MAX_ATTEMPTS:
            return None
        if isinstance(exception, NotificationRetryAfter):
            return RetryDecision(retry_in={"seconds": exception.retry_after})
        index = min(runs, len(_RETRY_DELAYS_SECONDS)) - 1
        return RetryDecision(retry_in={"seconds": _RETRY_DELAYS_SECONDS[index]})
