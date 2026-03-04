# Stage 1: Build Next.js static export
FROM node:20-slim AS frontend

WORKDIR /frontend
COPY garage-ai-command-center/package.json garage-ai-command-center/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY garage-ai-command-center/ .
ENV NEXT_OUTPUT=export
RUN pnpm build

# Stage 2: Python backend + static frontend
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy built frontend static files
COPY --from=frontend /frontend/out /app/static_frontend

# Cloud Run sets PORT env var (default 8080)
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn bridge.api:app --host 0.0.0.0 --port $PORT"]
