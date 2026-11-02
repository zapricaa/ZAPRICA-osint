# ==============================================================================
# ZAPRICA Hardened Linux Collector Sandbox
# Multi-stage reproducible Debian 12 (Bookworm) runtime for OSINT CLI execution
# ==============================================================================

# Stage 1: Build & Python Package Compilation
FROM python:3.12-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install approved OSINT collectors in clean isolation
RUN pip install --no-cache-dir --prefix=/install \
    sherlock-project \
    holehe \
    theHarvester

# Stage 2: Hardened, Unprivileged Runtime Container
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsutils \
    whois \
    openssl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled Python binaries and packages from builder stage
COPY --from=builder /install /usr/local

# Create unprivileged non-root user (10001:10001)
RUN groupadd -g 10001 zapricasandbox && \
    useradd -u 10001 -g zapricasandbox -s /bin/sh -m zapricasandbox

# Create isolated volatile workspace mountpoint
RUN mkdir -p /workspace && \
    chown -R zapricasandbox:zapricasandbox /workspace

WORKDIR /workspace
USER 10001:10001

CMD ["/bin/sh"]
