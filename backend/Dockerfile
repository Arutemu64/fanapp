# syntax=docker/dockerfile:1
# An example of using standalone Python builds with multistage images.

# First, build the application in the `/app` directory
FROM ghcr.io/astral-sh/uv:0.12.0-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Configure the Python directory so it is consistent
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

WORKDIR /app

# Install Python before the project for caching. The exact version is read from
# .python-version — the single source Renovate's `python` group already bumps —
# so the image tracks the project pin automatically instead of hard-coding the
# patch here, which was invisible to Renovate and silently drifted. It must
# still be a version this uv release ships (`uv python list --managed-python`);
# a Python bump that outruns the pinned uv needs the uv bump alongside it.
COPY .python-version .
RUN uv python install
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Then, use a final image without uv
FROM debian:trixie-slim

# ca-certificates are necessary for web pushes. Deliberately left unpinned: we
# want the newest CA bundle on every rebuild, so pinning a version (DL3008)
# would freeze the trust store and defeat the point.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Setup a non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy the Python version
COPY --from=builder /python /python

# Copy the application from the builder
COPY --from=builder --chown=nonroot:nonroot /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Without a TTY, Python block-buffers stdout, so print() diagnostics can lag or
# vanish on crash; unbuffered output reaches the container log immediately.
ENV PYTHONUNBUFFERED=1

# Commit SHA of this build, read back by EnvConfig.build and reported as the
# Sentry release. Declared this late on purpose: it changes on every commit, and
# only the metadata-only layers below it are invalidated when it does. Empty for
# a local build from source — the app treats that as "unknown build".
ARG APP_BUILD
ENV APP_BUILD=$APP_BUILD

# Use the non-root user to run our application
USER nonroot

# Use `/app` as the working directory
WORKDIR /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/debug/health', timeout=3)"]

# Run the FastAPI application by default
CMD ["uvicorn", "--factory", "fanfan.presentation.web.factory:create_app"]
