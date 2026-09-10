# Vulture whitelist — simulated usage of names vulture flags as dead but which
# are reachable in ways a static pass cannot see (and that a [tool.vulture]
# ignore_decorators/ignore_names rule cannot express). Each line "uses" a name
# so vulture stops reporting it. Passed to vulture as an extra path via
# [tool.vulture] paths in pyproject.toml. Regenerate/extend with:
#   uv run vulture src/fanfan --make-whitelist
# then keep only genuine false positives — do NOT paste real dead code here.

# These imports are used only inside cast("<Name>", ...) string literals, which
# ruff resolves (no F401) but vulture cannot see into. Keep in sync if the
# cast() sites move or go away.
CursorResult  # cast() in adapters/db/gateways/{notifications,outbox}.py
AnyHttpUrl  # cast() in adapters/push/client.py
