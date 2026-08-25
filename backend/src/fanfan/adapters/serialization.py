from adaptix import Retort

# Central factory for the default adaptix Retort used across adapters to
# (de)serialize plain dataclass domain models to/from JSON-compatible
# structures (DB JSONB columns, NATS payloads, external API bodies).
#
# Adaptix caches per-type morphers inside a Retort, so a Retort is meant to
# be created once and reused — not instantiated per call. This factory keeps
# the base recipe in one place; a specialized configuration would extend the
# same idea behind its own NewType so dependency injection can tell them apart.


def create_retort() -> Retort:
    return Retort()
