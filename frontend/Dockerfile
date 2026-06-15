FROM node:22.22-alpine AS base

ENV PNPM_HOME=/pnpm
ENV PATH=/pnpm:$PATH
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV PNPM_VERSION=10.15.1

RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

# ── Dev stage ────────────────────────────────────────────────────────────────
FROM base AS dev

RUN --mount=type=cache,target=/pnpm/store \
	pnpm install --frozen-lockfile

ENV NODE_ENV=development

COPY . .

EXPOSE 3000

CMD ["sh", "-c", "pnpm exec svelte-kit sync && pnpm dev --host 0.0.0.0 --port 3000"]

# ── Build stage ──────────────────────────────────────────────────────────────
FROM base AS build

RUN --mount=type=cache,target=/pnpm/store \
	pnpm install --frozen-lockfile

COPY . .

# PUBLIC_* values are read by `$env/static/public` and inlined into the bundle at
# build time (this is a static SPA — there is no server to inject them at
# runtime). They must therefore be supplied as build args. All are public,
# non-secret deploy constants. SENTRY_AUTH_TOKEN is only used here to upload
# source maps and never reaches the published image.
ARG PUBLIC_API_URL
ARG PUBLIC_VAPID_KEY
ARG PUBLIC_SENTRY_DSN
ARG PUBLIC_TURNSTILE_SITE_KEY
ARG SENTRY_AUTH_TOKEN
ENV PUBLIC_API_URL=$PUBLIC_API_URL \
	PUBLIC_VAPID_KEY=$PUBLIC_VAPID_KEY \
	PUBLIC_SENTRY_DSN=$PUBLIC_SENTRY_DSN \
	PUBLIC_TURNSTILE_SITE_KEY=$PUBLIC_TURNSTILE_SITE_KEY \
	SENTRY_AUTH_TOKEN=$SENTRY_AUTH_TOKEN

RUN pnpm exec svelte-kit sync && pnpm build

# ── Prod stage ───────────────────────────────────────────────────────────────
# Serve the static bundle with NGINX. No Node runtime ships to production.
FROM nginx:1.27-alpine AS prod

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD ["wget", "-qO-", "http://127.0.0.1:80/"]

# nginx:alpine already drops to an unprivileged worker; the master needs root to
# bind :80 and read its config, matching the stock image's intended use.
CMD ["nginx", "-g", "daemon off;"]
