# syntax=docker/dockerfile:1@sha256:572cebbc2b15e6f84c077742952674889cb63cd5e9b80abdffcbe587b6f19183
FROM node:26.13.1-alpine@sha256:6bd9ab43c0ec0190ca7b2d193906cb8b7edf6e7f4afa43ddeccd6452710bffb5 AS base

ENV PNPM_HOME=/pnpm
ENV PATH=/pnpm:$PATH
WORKDIR /app

COPY package.json ./
# packageManager supplies the exact npm install spec.
# hadolint ignore=DL3016
RUN npm install -g "$(node -p 'require("./package.json").packageManager.split("+")[0]')"

COPY pnpm-lock.yaml pnpm-workspace.yaml ./

FROM base AS dev

# prepare needs the message catalog and SvelteKit configuration.
COPY . .

RUN --mount=type=cache,target=/pnpm/store \
	pnpm install --frozen-lockfile

ENV NODE_ENV=development

EXPOSE 3000

CMD ["sh", "-c", "pnpm exec svelte-kit sync && pnpm dev --host 0.0.0.0"]

FROM base AS build

COPY . .

RUN --mount=type=cache,target=/pnpm/store \
	pnpm install --frozen-lockfile

ARG PUBLIC_API_URL
ARG PUBLIC_SITE_URL
ARG PUBLIC_TIMEZONE
ARG PUBLIC_VAPID_KEY
ARG PUBLIC_SENTRY_DSN
ARG PUBLIC_SENTRY_ENVIRONMENT
ARG PUBLIC_SENTRY_TRACES_SAMPLE_RATE
ARG PUBLIC_UMAMI_SCRIPT_URL
ARG PUBLIC_UMAMI_WEBSITE_ID
ARG PUBLIC_VK_GROUP_ID
ARG PUBLIC_TELEGRAM_BOT_USERNAME
ENV PUBLIC_API_URL=$PUBLIC_API_URL \
	PUBLIC_SITE_URL=$PUBLIC_SITE_URL \
	PUBLIC_TIMEZONE=$PUBLIC_TIMEZONE \
	PUBLIC_VAPID_KEY=$PUBLIC_VAPID_KEY \
	PUBLIC_SENTRY_DSN=$PUBLIC_SENTRY_DSN \
	PUBLIC_SENTRY_ENVIRONMENT=$PUBLIC_SENTRY_ENVIRONMENT \
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE=$PUBLIC_SENTRY_TRACES_SAMPLE_RATE \
	PUBLIC_UMAMI_SCRIPT_URL=$PUBLIC_UMAMI_SCRIPT_URL \
	PUBLIC_UMAMI_WEBSITE_ID=$PUBLIC_UMAMI_WEBSITE_ID \
	PUBLIC_VK_GROUP_ID=$PUBLIC_VK_GROUP_ID \
	PUBLIC_TELEGRAM_BOT_USERNAME=$PUBLIC_TELEGRAM_BOT_USERNAME

ARG SENTRY_URL
ARG SENTRY_ORG
ARG SENTRY_PROJECT
ENV SENTRY_URL=$SENTRY_URL \
	SENTRY_ORG=$SENTRY_ORG \
	SENTRY_PROJECT=$SENTRY_PROJECT

ARG APP_VERSION
ARG APP_BUILD

RUN --mount=type=secret,id=sentry_auth_token,env=SENTRY_AUTH_TOKEN \
	pnpm exec svelte-kit sync && pnpm build

FROM nginx:1.31-alpine-slim@sha256:f45171d36c76a8b2f5ef97108a3a8a2294248a6578a0a180edc2d78f7d2edc26 AS prod

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD ["wget", "-qO-", "http://127.0.0.1:80/healthz"]

CMD ["nginx", "-g", "daemon off;"]
