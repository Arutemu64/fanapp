#!/bin/bash
#
# Rebuild counter: 1
#
# THIS is the file to paste into the cloud environment's "Setup script" field -
# not setup.sh. It finds the repo clone and runs the branch's own
# .claude/setup.sh, so the real setup script lives in git, is reviewed like any
# other code, and can never drift from what the environment actually ran.
#
# Bump the counter above to force a snapshot rebuild. The snapshot is rebuilt
# only when this FIELD changes (or after ~7 days); editing .claude/setup.sh in
# the repo does not touch the field, so a setup.sh change reaches an existing
# environment only after the cache expires - or when you bump the counter and
# save. The SessionStart hook warns whenever the two have diverged.
#
# Keep this file short and stable: it is the one piece of the setup that is
# still copied by hand.
set -uo pipefail

# The repo is cloned before the setup script runs, but this phase does not run
# inside the clone and does not set CLAUDE_PROJECT_DIR, so search the standard
# clone locations.
for candidate in /home/*/*/.claude/setup.sh /workspace/*/.claude/setup.sh; do
  if [ -f "$candidate" ]; then
    echo "[bootstrap] Running $candidate"
    # Deliberately not `exec`: a non-zero exit from the setup script would fail
    # session start for the whole environment. The setup script records what it
    # managed to install, and the SessionStart hook reports anything missing at
    # the start of every session - a session that comes up and says what is
    # broken beats an environment that refuses to build.
    bash "$candidate" \
      || echo "[bootstrap] WARN: setup script exited non-zero; the SessionStart hook will report what is missing."
    exit 0
  fi
done

echo "[bootstrap] WARN: no .claude/setup.sh found in the clone; skipping project setup."
exit 0
