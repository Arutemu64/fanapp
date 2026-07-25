from importlib.metadata import version

# The release version of the whole repo — frontend included — not just the
# backend. pyproject.toml holds the number (it is the only manifest that must
# carry a version and can be read back at runtime), and the `vX.Y.Z` git tag
# mirrors it. Reading it from the installed distribution rather than restating
# it here is what stops the two from drifting apart.
#
# This is NOT the identity of a running deploy — that is the commit SHA in
# APP_BUILD. See docs/dependencies.md for how the two are used.
APP_VERSION = version("fanfan")
