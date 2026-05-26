# ── Stage 1: Builder ──
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Runtime ──
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd -r bot && useradd -r -g bot -d /app -s /bin/false bot

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create data directory with proper permissions
RUN mkdir -p data && chown -R bot:bot data

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

USER bot

# Expose webhook port
EXPOSE 8443

# Default: runs in webhook mode via FastAPI
# Override CMD for polling: ["python", "-m", "bot.main"]
CMD ["python", "-m", "web.asgi"]