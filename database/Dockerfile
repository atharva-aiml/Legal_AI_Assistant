# One-shot migration runner: `docker compose run --rm migrate`.
FROM node:22-slim

RUN corepack enable && corepack prepare pnpm@9.15.4 --activate
WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
# migrate.ts reads .env.local unconditionally; DATABASE_URL comes from the
# container environment instead (it only fills vars that aren't already set).
RUN touch .env.local

CMD ["pnpm", "db:migrate"]
