# Multi-stage Dockerfile for the Next.js 16 dashboard.
#
# Stage 1 installs deps. Stage 2 runs the build. Stage 3 is the
# runtime image — copies only the standalone output + static assets
# + public/, so the final image is ~150 MB instead of ~1 GB.
#
# NEXT_PUBLIC_API_URL must be baked in at BUILD time because Next.js
# inlines it into the client bundle. Passed as a --build-arg from
# fly.toml (see [build.args]).

# ---- Stage 1: deps ----------------------------------------------------
FROM node:20-alpine AS deps

WORKDIR /app

# Alpine's musl needs libc6-compat for some Next.js dependencies (sharp,
# etc.). Cheap to add.
RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

# ---- Stage 2: build ---------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# NEXT_PUBLIC_* env vars must be defined at build time — Next inlines
# them into the client bundle. Passed via `--build-arg NEXT_PUBLIC_API_URL=...`.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Turbopack (default in Next 16) tries to write to the home dir cache
# even in CI; setting NEXT_TELEMETRY_DISABLED=1 also suppresses the
# opt-in prompt on first build.
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

# ---- Stage 3: runtime -------------------------------------------------
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080 \
    HOSTNAME=0.0.0.0

# Non-root runtime user.
RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# Standalone output — the Next.js server + a curated slice of
# node_modules — plus static assets. See the Next 16 Docker guide.
COPY --from=build --chown=nextjs:nodejs /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080

# `server.js` is the standalone entrypoint produced by
# `output: 'standalone'`. HOSTNAME=0.0.0.0 makes Next listen on all
# interfaces so Fly's proxy can reach it.
CMD ["node", "server.js"]
