from datetime import timedelta

from faststream import AckPolicy
from nats.js import api

# FastStream's NATS default is REJECT_ON_ERROR, which terminates a message on any
# unhandled exception — a transient DB blip would silently destroy a schedule
# change or a cancelled mailing, with no retry and no trace. Everything reaching
# these consumers is at-least-once by construction (the outbox relay only marks a
# row published once NATS acks it, and interactors derive deterministic ids so a
# redelivery upserts instead of duplicating), so redelivery is the right response
# to failure.
#
# This belongs on the *routers*, not on NatsBroker(ack_policy=...): a subscriber
# reads the policy once, at decoration time, from whatever it is declared on
# (faststream/_internal/endpoint/subscriber/usecase.py), so a broker-level
# default set before include_router() never reaches a router's subscribers and
# silently leaves them on REJECT_ON_ERROR. A subscriber's own ack_policy still
# wins over this, which is how the notification consumers keep MANUAL.
DEFAULT_ACK_POLICY = AckPolicy.NACK_ON_ERROR

# JetStream redelivers a message once ack_wait elapses, and nothing renews that
# lease while a handler runs: FastStream exposes msg.in_progress() but never
# calls it, so there is no heartbeat. The window therefore has to outlast the
# slowest handler rather than the typical one — the server default of 30s is
# shorter than a broadcast fan-out over the whole user table or an external
# vendor sync, and every message those handlers own would be processed twice
# concurrently. Deterministic notification ids keep that duplicate work
# harmless, but it is still duplicate work.
FAST_ACK_WAIT = timedelta(minutes=1).total_seconds()
SLOW_ACK_WAIT = timedelta(minutes=10).total_seconds()

# Bound the redelivery loop DEFAULT_ACK_POLICY opens up: without a ceiling a
# permanently failing message retries forever. JetStream stops after this many
# attempts and publishes a MAX_DELIVERIES advisory.
# Deliberately generous, not tight — the per-channel senders nack with the
# provider's own retry_after (VK flood control, push 429) and those spend from
# the same budget, so a low ceiling would drop notifications a vendor was
# merely rate-limiting.
MAX_DELIVER = 25


def consumer_config(*, ack_wait: float) -> api.ConsumerConfig:
    """Build the JetStream consumer config for one subscriber.

    Returns a fresh instance every call rather than exposing shared constants:
    FastStream writes `durable_name` into the object it is handed, so a shared
    config would pin every consumer to the durable of whichever subscriber
    registered first.

    Note this only takes effect when the durable is *created*. nats-py skips the
    config entirely for a durable that already exists, so changing these values
    does not reconfigure a deployed consumer — see docs/deployment.md.
    """
    return api.ConsumerConfig(ack_wait=ack_wait, max_deliver=MAX_DELIVER)
