# ── Stage 1: Build frontend ──
FROM node:20-slim AS builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: Serve with Nginx ──
FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built frontend
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80
