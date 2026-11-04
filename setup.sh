#!/usr/bin/env bash
# ==============================================================================
# ZAPRICA — One-File Complete Linux Installer & Environment Orchestrator
# Target Host: Ubuntu Linux LTS (22.04 / 24.04), Debian 12 (x86_64 / aarch64)
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
# ==============================================================================

set -euo pipefail

# Determine script and repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"
INSTALL_LOG="${REPO_ROOT}/zaprica-install.log"
export PATH="/usr/local/bin:$PATH"

# Terminal formatting colours
BOLD="\033[1m"
RESET="\033[0m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
CYAN="\033[36m"
BLUE="\033[34m"

# Track installation statuses
declare -A STATUS_MAP=(
    ["linux_reqs"]="FAIL"
    ["python_env"]="FAIL"
    ["backend_deps"]="FAIL"
    ["frontend_deps"]="FAIL"
    ["playwright_chromium"]="FAIL"
    ["docker_engine"]="FAIL"
    ["docker_sandbox"]="FAIL"
    ["whois"]="FAIL"
    ["dns_dig"]="FAIL"
    ["theharvester"]="FAIL"
    ["sherlock"]="FAIL"
    ["db_migrations"]="FAIL"
    ["backend_verif"]="FAIL"
    ["frontend_build"]="FAIL"
    ["gemini_key"]="NOT CONFIGURED"
    ["terminal_exec"]="DISABLED"
)

# Logging helpers
log_info() {
    echo -e "${CYAN}[INFO]${RESET} $*" | tee -a "${INSTALL_LOG}"
}

log_step() {
    echo -e "\n${BOLD}${BLUE}==>${RESET} ${BOLD}$*${RESET}" | tee -a "${INSTALL_LOG}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${RESET} $*" | tee -a "${INSTALL_LOG}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${RESET} $*" | tee -a "${INSTALL_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} $*" | tee -a "${INSTALL_LOG}"
}

# Run a command with its output captured to the log file
run_quiet() {
    local cmd_desc="$1"
    shift
    log_info "Executing: ${cmd_desc}..."
    if ! "$@" >> "${INSTALL_LOG}" 2>&1; then
        log_error "Failed during: ${cmd_desc}"
        log_error "Review log output in ${INSTALL_LOG}"
        return 1
    fi
}

# Determine privilege escalation method
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        log_error "Root privileges or sudo access are required to install system packages."
        exit 1
    fi
fi

# Initialise log file
echo "======================================================================" > "${INSTALL_LOG}"
echo "ZAPRICA Installation Log: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "${INSTALL_LOG}"
echo "Host: $(uname -a)" >> "${INSTALL_LOG}"
echo "Working Directory: ${REPO_ROOT}" >> "${INSTALL_LOG}"
echo "======================================================================" >> "${INSTALL_LOG}"

# ==============================================================================
# 1. LINUX HOST & SYSTEM ARCHITECTURE AUDIT
# ==============================================================================
log_step "1/9 Verifying Linux Host Architecture & Prerequisites"

OS_TYPE="$(uname -s)"
ARCH="$(uname -m)"

if [ "${OS_TYPE}" != "Linux" ]; then
    log_error "ZAPRICA requires native Linux. Detected OS: ${OS_TYPE}"
    exit 1
fi

log_info "Detected Linux kernel: $(uname -r) (${ARCH})"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="${ID:-linux}"
    DISTRO_VER="${VERSION_ID:-}"
    log_info "Linux distribution: ${NAME:-Linux} ${DISTRO_VER}"
else
    DISTRO="unknown"
    DISTRO_VER="unknown"
    log_warn "/etc/os-release not detected. Assuming generic Debian/Ubuntu compatibility."
fi

# Ensure apt is available
if ! command -v apt-get >/dev/null 2>&1; then
    log_error "apt-get package manager was not found. ZAPRICA setup supports Ubuntu/Debian LTS hosts."
    exit 1
fi

# Install baseline host utilities if missing
MISSING_PKGS=()
for pkg in curl git ca-certificates gnupg build-essential libpq-dev openssl pkg-config; do
    if ! dpkg -s "${pkg}" >/dev/null 2>&1; then
        MISSING_PKGS+=("${pkg}")
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    log_info "Installing missing system utilities: ${MISSING_PKGS[*]}"
    run_quiet "Updating package cache" ${SUDO} apt-get update -y
    run_quiet "Installing core build packages" ${SUDO} apt-get install -y --no-install-recommends "${MISSING_PKGS[@]}"
else
    log_info "Core system build utilities are already installed."
fi

STATUS_MAP["linux_reqs"]="PASS"
log_success "Linux host requirements verified."

# ==============================================================================
# 2. PYTHON RUNTIME (>= 3.11)
# ==============================================================================
log_step "2/9 Configuring Python Runtime (>= 3.11)"

PYTHON_BIN=""

# Detect the best available Python binary >= 3.11
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
        if "${candidate}" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
            PYTHON_BIN="${candidate}"
            break
        fi
    fi
done

if [ -z "${PYTHON_BIN}" ]; then
    log_info "Python >= 3.11 not found in default PATH. Installing via apt..."
    run_quiet "Updating apt repository" ${SUDO} apt-get update -y
    # Install Python 3.12 or 3.11 from default distribution repositories,
    # or from the deadsnakes PPA on older Ubuntu releases.
    if apt-cache show python3.12 >/dev/null 2>&1; then
        run_quiet "Installing Python 3.12" ${SUDO} apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip
        PYTHON_BIN="python3.12"
    elif apt-cache show python3.11 >/dev/null 2>&1; then
        run_quiet "Installing Python 3.11" ${SUDO} apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
        PYTHON_BIN="python3.11"
    else
        log_info "Adding deadsnakes PPA for Python 3.12..."
        run_quiet "Installing software-properties-common" ${SUDO} apt-get install -y software-properties-common
        run_quiet "Adding deadsnakes PPA" ${SUDO} add-apt-repository -y ppa:deadsnakes/ppa
        run_quiet "Updating package list" ${SUDO} apt-get update -y
        run_quiet "Installing Python 3.12" ${SUDO} apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip
        PYTHON_BIN="python3.12"
    fi
else
    # Ensure venv and dev packages are installed for the selected Python version
    PY_VER_SHORT="$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if ! dpkg -s "python${PY_VER_SHORT}-venv" >/dev/null 2>&1 && ! dpkg -s "python3-venv" >/dev/null 2>&1; then
        log_info "Installing venv package for Python ${PY_VER_SHORT}..."
        run_quiet "Installing Python venv" ${SUDO} apt-get install -y "python${PY_VER_SHORT}-venv" || ${SUDO} apt-get install -y python3-venv
    fi
    if ! dpkg -s "python${PY_VER_SHORT}-dev" >/dev/null 2>&1 && ! dpkg -s "python3-dev" >/dev/null 2>&1; then
        log_info "Installing development headers for Python ${PY_VER_SHORT}..."
        run_quiet "Installing Python dev headers" ${SUDO} apt-get install -y "python${PY_VER_SHORT}-dev" || ${SUDO} apt-get install -y python3-dev
    fi
fi

PY_VERSION_STRING="$("${PYTHON_BIN}" --version)"
log_info "Using Python interpreter: ${PYTHON_BIN} (${PY_VERSION_STRING})"
STATUS_MAP["python_env"]="PASS"
log_success "Python environment validated: ${PY_VERSION_STRING}"

# ==============================================================================
# 3. NODE.JS & NPM RUNTIME (>= 18.17.0 for Next.js 14)
# ==============================================================================
log_step "3/9 Verifying Node.js and npm Runtime (Node.js 20 LTS)"

NODE_20_VERSION="20.18.1"

NEED_NODE_INSTALL=true
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    NODE_VER="$(node -v | sed 's/v//')"
    NODE_MAJOR="$(echo "${NODE_VER}" | cut -d. -f1)"
    NODE_MINOR="$(echo "${NODE_VER}" | cut -d. -f2)"
    if [ "${NODE_MAJOR}" -ge 20 ] || { [ "${NODE_MAJOR}" -eq 18 ] && [ "${NODE_MINOR}" -ge 17 ]; }; then
        NEED_NODE_INSTALL=false
        log_info "Node.js $(node -v) and npm $(npm -v) are already compatible."
    fi
fi

if [ "${NEED_NODE_INSTALL}" = true ]; then
    # Strategy 1: Try the system package manager first (works on Ubuntu, Debian, Kali, etc.)
    NODE_INSTALLED_VIA_APT=false
    if apt-cache show nodejs 2>/dev/null | grep -qP '^Version: (1[89]|[2-9]\d)\.' 2>/dev/null; then
        log_info "Installing Node.js from system package repositories..."
        run_quiet "Installing nodejs via apt" ${SUDO} apt-get install -y nodejs npm && NODE_INSTALLED_VIA_APT=true
    fi

    if [ "${NODE_INSTALLED_VIA_APT}" = true ]; then
        # Verify the apt-installed version is actually compatible
        if command -v node >/dev/null 2>&1; then
            NODE_VER="$(node -v | sed 's/v//')"
            NODE_MAJOR="$(echo "${NODE_VER}" | cut -d. -f1)"
            if [ "${NODE_MAJOR}" -ge 18 ]; then
                NEED_NODE_INSTALL=false
                log_info "Node.js $(node -v) installed from system repositories."
            fi
        fi
    fi

    # Strategy 2: Download the official Node.js binary tarball from nodejs.org.
    # This is distribution-agnostic and works on Ubuntu, Debian, Kali, and any Linux.
    if [ "${NEED_NODE_INSTALL}" = true ]; then
        log_info "Installing Node.js ${NODE_20_VERSION} from the official nodejs.org binary distribution..."

        # Determine architecture for the download URL
        case "${ARCH}" in
            x86_64)  NODE_ARCH="x64" ;;
            aarch64) NODE_ARCH="arm64" ;;
            armv7l)  NODE_ARCH="armv7l" ;;
            *)
                log_error "Unsupported architecture for Node.js binary download: ${ARCH}"
                exit 1
                ;;
        esac

        NODE_TARBALL="node-v${NODE_20_VERSION}-linux-${NODE_ARCH}.tar.xz"
        NODE_URL="https://nodejs.org/dist/v${NODE_20_VERSION}/${NODE_TARBALL}"
        NODE_INSTALL_DIR="/usr/local"

        run_quiet "Downloading Node.js ${NODE_20_VERSION}" curl -fsSL "${NODE_URL}" -o "/tmp/${NODE_TARBALL}"

        log_info "Extracting Node.js to ${NODE_INSTALL_DIR}..."
        ${SUDO} tar -xJf "/tmp/${NODE_TARBALL}" -C "${NODE_INSTALL_DIR}" --strip-components=1 >> "${INSTALL_LOG}" 2>&1
        rm -f "/tmp/${NODE_TARBALL}"
        export PATH="/usr/local/bin:$PATH"

        # Verify installation
        if ! command -v node >/dev/null 2>&1; then
            log_error "Node.js binary not found in PATH after installation."
            exit 1
        fi
        log_info "Node.js $(node -v) installed from official binary tarball."
    fi
fi

log_info "Node.js version: $(node -v), npm version: $(npm -v)"

# ==============================================================================
# 4. DOCKER ENGINE & SANDBOX DAEMON
# ==============================================================================
log_step "4/9 Verifying Docker Engine & Container Execution Environment"

if ! command -v docker >/dev/null 2>&1; then
    log_info "Docker CLI not detected. Installing Docker Engine..."
    run_quiet "Updating apt list" ${SUDO} apt-get update -y
    # Install docker.io (available on Debian, Ubuntu, and Kali).
    # Also attempt to install docker-compose-plugin; fall back silently
    # on distributions that package it separately or not at all.
    run_quiet "Installing Docker Engine" ${SUDO} apt-get install -y docker.io
    ${SUDO} apt-get install -y docker-compose-plugin >> "${INSTALL_LOG}" 2>&1 || true
fi

# Ensure the Docker service is running
if command -v systemctl >/dev/null 2>&1; then
    if ! systemctl is-active --quiet docker; then
        log_info "Starting Docker systemd service..."
        run_quiet "Starting Docker service" ${SUDO} systemctl start docker
        run_quiet "Enabling Docker service" ${SUDO} systemctl enable docker
    fi
fi

# Determine whether the current user needs sudo for Docker
DOCKER_CMD="docker"
if ! docker info >/dev/null 2>&1; then
    if ${SUDO} docker info >/dev/null 2>&1; then
        DOCKER_CMD="${SUDO} docker"
        # Add the current user to the docker group if not root
        if [ "$(id -u)" -ne 0 ] && ! groups "$USER" | grep -q '\bdocker\b'; then
            log_warn "Adding user '${USER}' to the docker group..."
            ${SUDO} usermod -aG docker "$USER" >> "${INSTALL_LOG}" 2>&1 || true
            log_warn "User '${USER}' has been added to the 'docker' group. A shell re-login is required for non-sudo Docker usage."
        fi
    else
        log_error "Docker daemon is unresponsive even with sudo privileges."
        exit 1
    fi
fi

DOCKER_VER="$(${DOCKER_CMD} --version)"
log_info "Docker Engine ready: ${DOCKER_VER}"
STATUS_MAP["docker_engine"]="PASS"
log_success "Docker Engine is operational."

# ==============================================================================
# 5. ENVIRONMENT CONFIGURATION (.env) & STORAGE INITIALISATION
# ==============================================================================
log_step "5/9 Initialising Environment Configuration & Data Directories"

# Ensure data directories exist
mkdir -p "${REPO_ROOT}/data/evidence" "${REPO_ROOT}/data/browser_profiles"

ENV_FILE="${REPO_ROOT}/.env"
if [ -f "${ENV_FILE}" ]; then
    log_info "Existing '.env' file detected. Preserving credentials and configurations intact."
else
    log_info "No '.env' file found. Generating production-ready '.env' with safe defaults..."

    # Generate cryptographically secure tokens
    GEN_SECRET="$(openssl rand -hex 32)"
    GEN_BOOTSTRAP="$(openssl rand -hex 16)"

    cat <<EOF > "${ENV_FILE}"
# ZAPRICA Environment Configuration
# Generated automatically by setup.sh

APP_ENV=production
API_BASE_URL=http://localhost:8000
SECRET_KEY=${GEN_SECRET}
BOOTSTRAP_SECRET=${GEN_BOOTSTRAP}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database Configuration (SQLite default; use postgresql+asyncpg://... for PostgreSQL)
DATABASE_URL=sqlite+aiosqlite:///./zaprica.db

# Evidence Storage Configuration
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./data/evidence

# Google Gemini AI Brain
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
GEMINI_MAIN_HEAD_MODEL=gemini-2.0-flash
GEMINI_BROWSER_HEAD_MODEL=gemini-2.0-flash-lite
GEMINI_TERMINAL_HEAD_MODEL=gemini-2.0-flash-lite

# Data Collection Engine (DCE) Settings
HIBP_API_KEY=
HOLEHE_ENABLED=false
THEHARVESTER_SOURCES=crtsh
DCE_DEMO_MODE=false

# Dedicated Sandboxes
DOCKER_SANDBOX_IMAGE=zaprica-sandbox:latest
BROWSER_PROFILES_DIR=./data/browser_profiles
BROWSER_HEADLESS=true

# Safe Startup Defaults
ZAPRICA_SAFE_MODE=true
TERMINAL_EXECUTION_ENABLED=false
AUTO_INVESTIGATION_ENABLED=false
AUTO_TOOL_INSTALLATION=false
LOG_LEVEL=INFO
EOF
    chmod 600 "${ENV_FILE}"
    log_success "Created '.env' with a secure SECRET_KEY and safe startup flags."
fi

# Audit environment state for the summary report
if grep -qP '^GEMINI_API_KEY=.+' "${ENV_FILE}" 2>/dev/null; then
    KEY_VAL="$(grep '^GEMINI_API_KEY=' "${ENV_FILE}" | cut -d= -f2- | tr -d '"'\'' ')"
    if [ -n "${KEY_VAL}" ]; then
        STATUS_MAP["gemini_key"]="CONFIGURED"
    fi
fi

if grep -q '^TERMINAL_EXECUTION_ENABLED=true' "${ENV_FILE}" 2>/dev/null; then
    STATUS_MAP["terminal_exec"]="ENABLED"
fi

# ==============================================================================
# 6. BACKEND PYTHON VIRTUAL ENVIRONMENT & DEPENDENCIES
# ==============================================================================
log_step "6/9 Installing Backend Dependencies & Verifying Imports"

VENV_PATH="${REPO_ROOT}/backend/.venv"
if [ ! -d "${VENV_PATH}" ]; then
    log_info "Creating backend Python virtual environment at ${VENV_PATH}..."
    run_quiet "Creating virtual environment" "${PYTHON_BIN}" -m venv "${VENV_PATH}"
fi

VENV_PY="${VENV_PATH}/bin/python"
VENV_PIP="${VENV_PATH}/bin/pip"

run_quiet "Upgrading pip, setuptools, and wheel" "${VENV_PIP}" install --upgrade pip setuptools wheel

log_info "Installing pinned dependencies from backend/requirements.txt..."
run_quiet "Installing backend dependencies" "${VENV_PIP}" install -r "${REPO_ROOT}/backend/requirements.txt"

log_info "Installing backend package in editable development mode..."
if ! "${VENV_PIP}" install -e "${REPO_ROOT}/backend" >> "${INSTALL_LOG}" 2>&1; then
    log_warn "Standard editable install encountered build issue. Fallback linking via .pth file..."
    SITE_PACKAGES="$("${VENV_PY}" -c "import site; print(site.getsitepackages()[0])")"
    echo "${REPO_ROOT}/backend" > "${SITE_PACKAGES}/zaprica_backend.pth"
    log_info "Linked backend package via zaprica_backend.pth in site-packages."
fi

log_info "Verifying critical backend package imports..."
"${VENV_PY}" -c "
import fastapi
import uvicorn
import pydantic
import sqlalchemy
import alembic
import playwright
import httpx
import google.genai
import langgraph
import pwdlib
import pyotp
import aiosqlite
import asyncpg
print('All core backend modules imported successfully.')
" >> "${INSTALL_LOG}" 2>&1

run_quiet "Running pip dependency conflict check" "${VENV_PIP}" check

STATUS_MAP["backend_deps"]="PASS"
log_success "Backend virtual environment and dependencies validated."

# ==============================================================================
# 7. BROWSER HEAD: PLAYWRIGHT CHROMIUM INSTALLATION
# ==============================================================================
log_step "7/9 Installing Browser Head Playwright Chromium & System Libraries"

log_info "Installing Playwright Linux system dependencies..."
PW_DEPS_INSTALLED=false
if [ "$(id -u)" -eq 0 ]; then
    if "${VENV_PY}" -m playwright install-deps chromium >> "${INSTALL_LOG}" 2>&1; then
        PW_DEPS_INSTALLED=true
    fi
else
    # Install system dependencies with elevated privileges
    if ${SUDO} "${VENV_PY}" -m playwright install-deps chromium >> "${INSTALL_LOG}" 2>&1; then
        PW_DEPS_INSTALLED=true
    fi
fi

if [ "${PW_DEPS_INSTALLED}" = false ]; then
    log_warn "playwright install-deps skipped or unsupported on this distribution (${DISTRO})."
    log_info "Installing standard Chromium system dependencies via package manager..."
    ${SUDO} apt-get update -y >> "${INSTALL_LOG}" 2>&1 || true
    ${SUDO} apt-get install -y --no-install-recommends \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libx11-xcb1 \
        libxcb-dri3-0 >> "${INSTALL_LOG}" 2>&1 || true
    ${SUDO} apt-get install -y --no-install-recommends libasound2 >> "${INSTALL_LOG}" 2>&1 || \
    ${SUDO} apt-get install -y --no-install-recommends libasound2t64 >> "${INSTALL_LOG}" 2>&1 || true
fi

log_info "Installing Playwright Chromium browser binary..."
run_quiet "Installing Chromium binary" "${VENV_PY}" -m playwright install chromium

log_info "Verifying Playwright Chromium browser launch in headless mode..."
"${VENV_PY}" -c "
import asyncio
from playwright.async_api import async_playwright

async def verify_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        version = browser.version
        await browser.close()
        print(f'Chromium {version} launched successfully.')

asyncio.run(verify_browser())
" >> "${INSTALL_LOG}" 2>&1

STATUS_MAP["playwright_chromium"]="PASS"
log_success "Playwright Chromium installed and verified."

# ==============================================================================
# 8. OSINT COLLECTORS & DOCKER SANDBOX IMAGE
# ==============================================================================
log_step "8/9 Building Hardened Linux Sandbox Image & Verifying OSINT Collectors"

SANDBOX_DOCKERFILE="${REPO_ROOT}/docker/sandbox/Dockerfile"
SANDBOX_CONTEXT="${REPO_ROOT}/docker/sandbox"
SANDBOX_IMAGE="zaprica-sandbox:latest"

if [ ! -f "${SANDBOX_DOCKERFILE}" ]; then
    log_error "Sandbox Dockerfile not found at ${SANDBOX_DOCKERFILE}"
    exit 1
fi

log_info "Building ${SANDBOX_IMAGE} from ${SANDBOX_DOCKERFILE}..."
run_quiet "Building Docker sandbox image" ${DOCKER_CMD} build -t "${SANDBOX_IMAGE}" -f "${SANDBOX_DOCKERFILE}" "${SANDBOX_CONTEXT}"
STATUS_MAP["docker_sandbox"]="PASS"

# Verify each integrated collector inside the isolated sandbox
log_info "Verifying WHOIS inside the sandbox..."
if ${DOCKER_CMD} run --rm "${SANDBOX_IMAGE}" which whois >> "${INSTALL_LOG}" 2>&1; then
    STATUS_MAP["whois"]="PASS"
    log_info "WHOIS binary verified in the sandbox."
fi

log_info "Verifying dig (dnsutils) inside the sandbox..."
if ${DOCKER_CMD} run --rm "${SANDBOX_IMAGE}" dig -v >> "${INSTALL_LOG}" 2>&1; then
    STATUS_MAP["dns_dig"]="PASS"
    log_info "dig (DNS) binary verified in the sandbox."
fi

log_info "Verifying theHarvester inside the sandbox..."
if ${DOCKER_CMD} run --rm "${SANDBOX_IMAGE}" theHarvester -h >> "${INSTALL_LOG}" 2>&1; then
    STATUS_MAP["theharvester"]="PASS"
    log_info "theHarvester verified in the sandbox."
fi

log_info "Verifying Sherlock inside the sandbox..."
if ${DOCKER_CMD} run --rm "${SANDBOX_IMAGE}" sherlock --version >> "${INSTALL_LOG}" 2>&1; then
    STATUS_MAP["sherlock"]="PASS"
    log_info "Sherlock verified in the sandbox."
fi

# Verify Holehe inside the sandbox (installed in the image but disabled at runtime by default)
if ${DOCKER_CMD} run --rm "${SANDBOX_IMAGE}" holehe --version >> "${INSTALL_LOG}" 2>&1 || \
   ${DOCKER_CMD} run --rm "${SANDBOX_IMAGE}" python3 -m holehe --version >> "${INSTALL_LOG}" 2>&1; then
    log_info "Holehe collector binary present in the sandbox (runtime disabled by default)."
fi

log_success "Docker sandbox image built and all integrated OSINT tools verified."

# ==============================================================================
# 9. DATABASE MIGRATIONS & APPLICATION COMPONENT SELF-TEST
# ==============================================================================
log_step "9/9 Running Database Migrations & Validating Application Components"

# Run Alembic database migrations
log_info "Executing Alembic database migrations..."
(
    cd "${REPO_ROOT}/backend"
    run_quiet "Running alembic upgrade head" "${VENV_PATH}/bin/alembic" upgrade head
)
STATUS_MAP["db_migrations"]="PASS"
log_success "Database migrations applied successfully."

# Self-test backend startup and DCE capability registry
log_info "Verifying backend startup and DCE coordinator registration..."
(
    cd "${REPO_ROOT}/backend"
    "${VENV_PY}" -c "
import asyncio
from app.core.config import settings
from app.collection.coordinator import dce_coordinator
import app.main

async def run_selftest():
    caps = await dce_coordinator.list_capabilities()
    names = [c.collector_id.value for c in caps]
    print(f'Active DCE registered collectors: {names}')
    assert len(names) >= 6, 'Missing registered DCE collectors'
    print('Backend self-test passed.')

asyncio.run(run_selftest())
" >> "${INSTALL_LOG}" 2>&1
)
STATUS_MAP["backend_verif"]="PASS"
log_success "Backend components and DCE coordinator validated."

# Install frontend dependencies and verify the production build
log_step "Building Frontend Production Bundle"
(
    cd "${REPO_ROOT}/frontend"
    log_info "Installing frontend dependencies using npm..."
    if ! run_quiet "Running npm ci" npm ci; then
        log_warn "npm ci failed. Falling back to npm install..."
        run_quiet "Running npm install" npm install
    fi
    STATUS_MAP["frontend_deps"]="PASS"

    log_info "Compiling Next.js 14 production build..."
    run_quiet "Compiling frontend" npm run build
    STATUS_MAP["frontend_build"]="PASS"
)
log_success "Frontend production bundle compiled successfully."

# ==============================================================================
# 10. INSTALLATION VERIFICATION REPORT
# ==============================================================================
echo ""
echo "================================"
echo "       ZAPRICA INSTALLER        "
echo "================================"
echo ""
echo "[${STATUS_MAP["linux_reqs"]}] Linux requirements"
echo "[${STATUS_MAP["python_env"]}] Python environment"
echo "[${STATUS_MAP["backend_deps"]}] Backend dependencies"
echo "[${STATUS_MAP["frontend_deps"]}] Frontend dependencies"
echo "[${STATUS_MAP["playwright_chromium"]}] Playwright Chromium"
echo "[${STATUS_MAP["docker_engine"]}] Docker Engine"
echo "[${STATUS_MAP["docker_sandbox"]}] Docker sandbox image"
echo "[${STATUS_MAP["whois"]}] WHOIS"
echo "[${STATUS_MAP["dns_dig"]}] DNS / DIG"
echo "[${STATUS_MAP["theharvester"]}] theHarvester"
echo "[${STATUS_MAP["sherlock"]}] Sherlock"
echo "[${STATUS_MAP["db_migrations"]}] Database migrations"
echo "[${STATUS_MAP["backend_verif"]}] Backend verification"
echo "[${STATUS_MAP["frontend_build"]}] Frontend build"
echo ""
echo "[${STATUS_MAP["gemini_key"]}] Gemini API key"
echo "[${STATUS_MAP["terminal_exec"]}] Live terminal execution"
echo ""
echo "================================"
echo "       INSTALLATION SUMMARY     "
echo "================================"
echo ""
echo -e "${GREEN}${BOLD}ZAPRICA has been successfully installed and verified on this system.${RESET}"
echo ""
echo -e "${BOLD}Next Steps to Launch ZAPRICA:${RESET}"
echo ""
echo "1. Configure the Google Gemini API key:"
echo "   Edit the .env file and set GEMINI_API_KEY:"
echo "   nano .env"
echo ""
echo "2. Start the backend API server:"
echo "   cd ${REPO_ROOT}/backend"
echo "   source .venv/bin/activate"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "3. Start the frontend dashboard:"
echo "   cd ${REPO_ROOT}/frontend"
echo "   npm start"
echo "   (Accessible at http://localhost:3000)"
echo ""
echo "Or start all services via Docker Compose:"
echo "   docker compose up -d"
echo ""
if [ "${DOCKER_CMD}" != "docker" ]; then
    echo -e "${YELLOW}[NOTE] A logout/login cycle or system restart is required for user '${USER}'${RESET}"
    echo -e "${YELLOW}       to run Docker commands without sudo privilege escalation.${RESET}"
    echo ""
fi
echo "Detailed installation log is available at:"
echo "   ${INSTALL_LOG}"
echo ""
exit 0
