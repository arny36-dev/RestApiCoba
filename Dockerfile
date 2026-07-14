# syntax=docker/dockerfile:1

##############################################################################
# Stage 1 — builder: compile/collect dependency wheels.
# Build tooling lives ONLY here so it never reaches the runtime image.
##############################################################################
FROM python:3.11.4-slim AS builder

# MariaDB + general compilation dependencies. aiomysql itself is pure Python,
# but these guarantee any dependency without a prebuilt wheel for this platform
# (or an added C/Rust package such as cryptography) can still be built here.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only the lock first: this layer stays cached until requirements change.
COPY requirements.txt .

# Build every dependency into /wheels so the runtime stage installs offline.
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

##############################################################################
# Stage 2 — runtime: minimal image with only what is needed to run the API.
##############################################################################
FROM python:3.11.4-slim AS runtime

ENV TZ=Europe/Bratislava \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Timezone Europe/Bratislava (tzdata only; no build tools, no editors).
RUN apt-get update && apt-get install -y --no-install-recommends \
        tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Dedicated non-root user.
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --no-create-home app

WORKDIR /app

# Install dependencies from the prebuilt wheels — no compilers in this image.
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Application code last (the layer that changes most often).
COPY app ./app

# Log directory (app writes logs/app.log) owned by the non-root user.
RUN mkdir -p /app/logs && chown -R app:app /app

USER app

EXPOSE 8000

# Liveness probe against the unauthenticated /health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else 1)"

# Production command — no --reload.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
