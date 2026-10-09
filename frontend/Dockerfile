# syntax=docker/dockerfile:1
# Shared node pin (docs/dependencies.md): pin the full patch, not a bare `24.18`.
# The dockerfile manager reads FROM lines, but a `24.18` tag floats to the latest
# patch on its own, so a patch release produces no diff here and this site drops
# out of the grouped "node" Renovate PR — leaving it silently behind mise.toml
# and the CI setup-node input. The full patch keeps all three moving together.
FROM node:24.20.0-alpine AS base

# PNPM_HOME makes pnpm keep its content-addressable store under /pnpm/store,
# which is where the cache mounts below point.
ENV PNPM_HOME=/pnpm
ENV PATH=/pnpm:$PATH
# One site of the shared pnpm pin (docs/dependencies.md): it must equal
# mise.toml, package.json#packageManager and the CI `pnpm/action-setup` input.
# The annotation below is what keeps it in their bump PR — the dockerfile
# manager reads FROM lines only, so an ENV pin is invisible without it. It is
# read by the customManagers:dockerfileVersions preset (renovate.jsonc), which
# requires the comment on the line directly above the ENV.
# renovate: datasource=npm depName=pnpm versioning=npm
ENV PNPM_VERSION=12.3.4

# Installed standalone via npm (not Corepack): Node 25+ no longer ships
# Corepack, and pnpm now recommends standalone installs.
RUN npm install -g pnpm@${PNPM_VERSION}

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# ── Dev stage ────────────────────────────────────────────────────────────────
FROM base AS dev

RUN --mount=type=cache,target=/pnpm/store \
	pnpm install --frozen-lockfile

ENV NODE_ENV=development

COPY . .

# Default dev port; the actual port comes from FRONTEND_PORT via vite.config.ts.
EXPOSE 3000

# No --port flag: vite.config.ts reads FRONTEND_PORT (compose passes it in), so a
# single var drives the port and the flag can't silently override it.
CMD ["sh", "-c", "pnpm exec svelte-kit sync && pnpm dev --host 0.0.0.0"]

# ── Build stage ──────────────────────────────────────────────────────────────
FROM base AS build

RUN --mount=type=cache,target=/pnpm/store \
	pnpm install --frozen-lockfile

COPY . .

# PUBLIC_* values are read by `$app/env/public` and inlined into the bundle at
# build time (this is a static SPA — there is no server to inject them at
# runtime). They must therefore be supplied as build args. All are public,
# non-secret deploy constants.
ARG PUBLIC_API_URL
ARG PUBLIC_SITE_URL
ARG PUBLIC_TIMEZONE
ARG PUBLIC_VAPID_KEY
ARG PUBLIC_SENTRY_DSN
ARG PUBLIC_SENTRY_ENVIRONMENT
ARG PUBLIC_SENTRY_TRACES_SAMPLE_RATE
ARG PUBLIC_SMARTCAPTCHA_CLIENT_KEY
ARG PUBLIC_VK_GROUP_ID
ENV PUBLIC_API_URL=$PUBLIC_API_URL \
	PUBLIC_SITE_URL=$PUBLIC_SITE_URL \
	PUBLIC_TIMEZONE=$PUBLIC_TIMEZONE \
	PUBLIC_VAPID_KEY=$PUBLIC_VAPID_KEY \
	PUBLIC_SENTRY_DSN=$PUBLIC_SENTRY_DSN \
	PUBLIC_SENTRY_ENVIRONMENT=$PUBLIC_SENTRY_ENVIRONMENT \
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE=$PUBLIC_SENTRY_TRACES_SAMPLE_RATE \
	PUBLIC_SMARTCAPTCHA_CLIENT_KEY=$PUBLIC_SMARTCAPTCHA_CLIENT_KEY \
	PUBLIC_VK_GROUP_ID=$PUBLIC_VK_GROUP_ID

# Where the source maps are uploaded (Sentry SaaS or self-hosted GlitchTip).
# Build-time only — unlike the PUBLIC_* args above, these are read by
# vite.config.ts and never inlined into the bundle. Non-secret, and all optional:
# an empty URL/ORG/PROJECT means no upload. The release the maps upload under is
# APP_BUILD below.
ARG SENTRY_URL
ARG SENTRY_ORG
ARG SENTRY_PROJECT
ENV SENTRY_URL=$SENTRY_URL \
	SENTRY_ORG=$SENTRY_ORG \
	SENTRY_PROJECT=$SENTRY_PROJECT

# The build's identity, inlined by vite.config.ts `define`: the release number
# (backend/pyproject.toml) and the commit SHA, which also names the Sentry
# release. Both are passed in because the ./frontend context holds neither
# pyproject.toml nor .git. ARG, not ENV: `pnpm build` reads them as build-time
# environment variables, and nothing after this stage needs them. A local build
# gets APP_VERSION only; with no APP_BUILD it has no published identity to claim.
ARG APP_VERSION
ARG APP_BUILD

# SENTRY_AUTH_TOKEN (uploads source maps) is a real secret, so it enters as a
# BuildKit secret mount, not ARG/ENV — args persist in this stage's layer
# metadata and in exported build caches (see the SecretsUsedInArgOrEnv build
# check). The mount is optional: with no secret passed the variable is unset and
# vite.config.ts skips the source-map upload.
RUN --mount=type=secret,id=sentry_auth_token,env=SENTRY_AUTH_TOKEN \
	pnpm exec svelte-kit sync && pnpm build

# ── Prod stage ───────────────────────────────────────────────────────────────
# Serve the static bundle with NGINX. No Node runtime ships to production.
# The `-slim` variant drops optional modules (njs, geoip, image filter…); this
# config only needs core + gzip, and busybox wget stays for the healthcheck.
FROM nginx:1.31-alpine-slim AS prod

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

# Probe the dedicated /healthz location (nginx.conf), not /: it skips the SPA
# fallback and stays out of the access log.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD ["wget", "-qO-", "http://127.0.0.1:80/healthz"]

# nginx:alpine already drops to an unprivileged worker; the master needs root to
# bind :80 and read its config, matching the stock image's intended use.
CMD ["nginx", "-g", "daemon off;"]
