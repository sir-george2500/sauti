# Sauti web image — Next.js standalone server.
#
# Build context is the repo root (see deploy/docker-compose.yml + .dockerignore).
# `output: "standalone"` in apps/web/next.config.ts makes Next emit a
# self-contained server.js plus only the node_modules it actually traced, so the
# runtime layer never ships the ~700 MB dev node_modules tree.
#
# NEXT_PUBLIC_* is inlined at BUILD time, so NEXT_PUBLIC_API_BASE_URL is a build
# arg, not a runtime env var: changing it means rebuilding this image.

# ---------- stage 1: dependencies ----------
FROM node:22-alpine AS deps

RUN corepack enable && corepack prepare pnpm@11.15.1 --activate
WORKDIR /app

COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml apps/web/.npmrc ./
RUN pnpm install --frozen-lockfile

# ---------- stage 2: build ----------
FROM node:22-alpine AS builder

RUN corepack enable && corepack prepare pnpm@11.15.1 --activate
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./

# Baked into the client bundle: the browser talks to the API through the proxy.
ARG NEXT_PUBLIC_API_BASE_URL=http://sauti.localhost/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

RUN pnpm run build

# ---------- stage 3: runtime ----------
FROM node:22-alpine AS runner

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 10001 nodejs && adduser -u 10001 -G nodejs -D -h /app nextjs
WORKDIR /app

# standalone/ already contains the traced node_modules and package.json;
# static/ is served by the standalone server but is not traced into it.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1

CMD ["node", "server.js"]
