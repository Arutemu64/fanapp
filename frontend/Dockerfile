FROM node:lts-bookworm-slim AS base

ENV PNPM_HOME=/pnpm
ENV PATH=/pnpm:$PATH

RUN corepack enable

WORKDIR /app

FROM base AS deps

COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/pnpm/store \
	corepack prepare pnpm@latest --activate \
	&& pnpm install --frozen-lockfile

FROM deps AS dev

ENV NODE_ENV=development

COPY . .

EXPOSE 5173

CMD ["sh", "-c", "pnpm exec svelte-kit sync && pnpm dev --host 0.0.0.0 --port 5173"]

FROM deps AS build

ENV NODE_ENV=production

COPY . .
RUN pnpm exec svelte-kit sync && pnpm build

FROM base AS prod-deps

COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/pnpm/store \
	corepack prepare pnpm@latest --activate \
	&& pnpm install --prod --frozen-lockfile

FROM node:lts-bookworm-slim AS prod

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=5173

WORKDIR /app

COPY --from=prod-deps /app/node_modules ./node_modules
COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./package.json

EXPOSE 5173

CMD ["node", "build"]
