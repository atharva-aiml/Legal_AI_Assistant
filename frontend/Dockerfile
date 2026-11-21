# Production image for the Next.js frontend (UI only — talks to the backend over HTTP).
FROM node:22-slim

ENV NEXT_TELEMETRY_DISABLED=1
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

# NEXT_PUBLIC_* is inlined into the browser bundle at BUILD time, so the public
# URL has to be known here, not just at runtime. In production it's the site's
# own origin — Caddy routes /api/* on that origin to the backend.
ARG NEXT_PUBLIC_JAVA_API_URL
ENV NEXT_PUBLIC_JAVA_API_URL=${NEXT_PUBLIC_JAVA_API_URL}
RUN pnpm build

ENV NODE_ENV=production
EXPOSE 3000
CMD ["pnpm", "start", "-H", "0.0.0.0", "-p", "3000"]
