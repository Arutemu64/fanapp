FROM node:lts-bookworm-slim AS base

ENV PNPM_HOME=/pnpm
ENV PATH=/pnpm:$PATH

RUN corepack enable

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

# ── Dev stage ────────────────────────────────────────────────────────────────
FROM base AS dev

RUN --mount=type=cache,target=/pnpm/store \
	corepack prepare pnpm@latest --activate \
	&& pnpm install --frozen-lockfile

ENV NODE_ENV=development

COPY . .

EXPOSE 3000

CMD ["sh", "-c", "pnpm exec svelte-kit sync && pnpm dev --host 0.0.0.0 --port 3000"]

# ── Prod stage ───────────────────────────────────────────────────────────────
FROM base AS build

RUN --mount=type=cache,target=/pnpm/store \
	corepack prepare pnpm@latest --activate \
	&& pnpm install --frozen-lockfile

COPY . .
RUN pnpm exec svelte-kit sync && pnpm build

FROM base AS prod-deps

RUN --mount=type=cache,target=/pnpm/store \
	corepack prepare pnpm@latest --activate \
	&& pnpm install --prod --frozen-lockfile

FROM node:lts-bookworm-slim AS prod

ENV NODE_ENV=production

WORKDIR /app

COPY --from=prod-deps /app/node_modules ./node_modules
COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./package.json

EXPOSE 3000

CMD ["node", "build"]
