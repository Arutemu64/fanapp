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

# ── Prod stage ───────────────────────────────────────────────────────────────
FROM base AS build

RUN --mount=type=cache,target=/pnpm/store \
	pnpm install --frozen-lockfile

COPY . .
RUN pnpm exec svelte-kit sync && pnpm build

FROM base AS prod-deps

RUN --mount=type=cache,target=/pnpm/store \
	pnpm install --prod --frozen-lockfile

FROM node:22.22-alpine AS prod

ENV NODE_ENV=production

WORKDIR /app

COPY --from=prod-deps --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/build ./build
COPY --from=build --chown=node:node /app/package.json ./package.json

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD ["wget", "-qO-", "http://127.0.0.1:3000/healthz"]

USER node

CMD ["node", "build"]
