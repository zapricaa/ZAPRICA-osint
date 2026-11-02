# Hardened Alpine Sandbox for ZAPRICA Terminal Head
FROM alpine:3.20

# Install approved network inspection and metadata extraction utilities
RUN apk add --no-cache \
    bind-tools \
    whois \
    openssl \
    perl \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# Create non-root unprivileged execution user and group (10001:10001)
RUN addgroup -g 10001 sandboxgroup && \
    adduser -u 10001 -G sandboxgroup -D -s /bin/sh sandboxuser

# Create isolated volatile workspace mountpoint
RUN mkdir -p /workspace && \
    chown -R sandboxuser:sandboxgroup /workspace

WORKDIR /workspace
USER 10001:10001

# Default no-op entrypoint
CMD ["/bin/sh"]
