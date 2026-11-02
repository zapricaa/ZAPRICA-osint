# ZAPRICA — Native Linux Deployment & Administration Guide

**Target OS**: Ubuntu 22.04 LTS / 24.04 LTS, Debian 12  
**Container Engine**: Docker Engine 24.0+ with Docker Compose v2  
**Target Architecture**: Native Linux (x86_64 / arm64)  

---

## 1. System Requirements & Prerequisites

### 1.1 Host Packages
```bash
sudo apt-get update && sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    git \
    python3 \
    python3-venv \
    python3-pip \
    nodejs \
    npm
```

### 1.2 Docker Engine Setup
```bash
# Add Docker GPG key and repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update && sudo apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add deploy user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

---

## 2. Environment Configuration

Inspect and configure the `.env` file in the project root:

```bash
chmod 600 .env
```

Configure `.env` with strong random secrets:

```bash
# Generate 64-char random hex secrets
SECRET_KEY=$(openssl rand -hex 32)
BOOTSTRAP_SECRET=$(openssl rand -hex 24)

# Set in .env
sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
sed -i "s|BOOTSTRAP_SECRET=.*|BOOTSTRAP_SECRET=$BOOTSTRAP_SECRET|" .env
```

---

## 3. Building the Sandbox Container Image

Before launching investigations requiring CLI tools (WHOIS, dig, theHarvester, Sherlock), build the hardened sandbox image:

```bash
docker build -t zaprica-sandbox:latest -f docker/sandbox/Dockerfile docker/sandbox
```

Verify unprivileged execution and binary availability:

```bash
docker run --rm zaprica-sandbox:latest whois --version
docker run --rm zaprica-sandbox:latest dig -v
docker run --rm zaprica-sandbox:latest sherlock --version
docker run --rm zaprica-sandbox:latest theHarvester -h
```

---

## 4. Multi-Service Stack Orchestration

Start the complete ZAPRICA platform (PostgreSQL, FastAPI Backend, Next.js Frontend):

```bash
docker compose up -d --build
```

Verify service health:

```bash
docker compose ps
curl -s http://localhost:8000/v1/health | jq .
```

---

## 5. First-Time System Bootstrap

Because ZAPRICA enforces an invite-only model, initialize the first `SUPER_ADMIN` account using the one-time bootstrap secret:

```bash
curl -X POST http://localhost:8000/v1/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin",
    "email": "admin@yourorg.internal",
    "display_name": "Lead Investigator",
    "password": "StrongPassword123!@#",
    "bootstrap_secret": "'"$BOOTSTRAP_SECRET"'",
    "workspace_name": "Primary Intelligence Unit"
  }'
```

---

## 6. Safe Startup Operation & Capabilities Activation

By default, ZAPRICA starts in **Safe Startup Mode**:
- `ZAPRICA_SAFE_MODE=true`
- `TERMINAL_EXECUTION_ENABLED=false`

To enable terminal execution for authorized investigators, the administrator activates terminal capabilities via the API or dashboard:

```bash
curl -X POST http://localhost:8000/v1/agents/terminal_head/state \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"state": "READY", "reason": "Authorized shift start"}'
```
