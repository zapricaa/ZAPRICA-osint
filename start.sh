#!/usr/bin/env bash
# ==============================================================================
# ZAPRICA — One-Command Application Launcher
# Starts both Backend (FastAPI) and Frontend (Next.js) concurrently.
# Press [CTRL + C] anytime to cleanly terminate all services.
#
# Usage:
#   chmod +x start.sh
#   ./start.sh
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"

BOLD="\033[1m"
RESET="\033[0m"
GREEN="\033[32m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo -e "${YELLOW}[ZAPRICA] Shutting down services...${RESET}"
    if [ -n "${BACKEND_PID}" ] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
        kill -SIGTERM "${BACKEND_PID}" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID}" ] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
        kill -SIGTERM "${FRONTEND_PID}" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo -e "${GREEN}[ZAPRICA] All services stopped cleanly.${RESET}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${BOLD}${CYAN}"
echo "=================================================="
echo "         ZAPRICA OSINT APPLICATION LAUNCHER       "
echo "=================================================="
echo -e "${RESET}"

# 1. Verify Prerequisites
if [ ! -d "${REPO_ROOT}/backend/.venv" ]; then
    echo -e "${RED}[ERROR] Backend virtual environment not found at backend/.venv!${RESET}"
    echo "Please run './setup.sh' first to set up the environment."
    exit 1
fi

if [ ! -d "${REPO_ROOT}/frontend/node_modules" ]; then
    echo -e "${YELLOW}[WARN] frontend/node_modules not found. Installing dependencies...${RESET}"
    (cd "${REPO_ROOT}/frontend" && npm install)
fi

# 2. Check for port conflicts and clear if necessary
for port in 8000 3000; do
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${port}/tcp" 2>/dev/null || true
    fi
done

# 3. Start Backend
echo -e "${CYAN}[1/2] Starting Backend API Server (FastAPI / Uvicorn)...${RESET}"
"${REPO_ROOT}/backend/.venv/bin/uvicorn" app.main:app \
    --app-dir "${REPO_ROOT}/backend" \
    --host 0.0.0.0 \
    --port 8000 \
    --reload &
BACKEND_PID=$!

# 4. Start Frontend
echo -e "${CYAN}[2/2] Starting Frontend Web Dashboard (Next.js)...${RESET}"
(
    cd "${REPO_ROOT}/frontend"
    npm run dev
) &
FRONTEND_PID=$!

# Wait briefly for startup
sleep 3

echo ""
echo -e "${BOLD}${GREEN}=================================================="
echo "          ZAPRICA SERVICES ARE ONLINE!            "
echo "=================================================="
echo -e "${RESET}"
echo -e "  ${BOLD}• Web Dashboard:${RESET}    ${CYAN}http://localhost:3000${RESET}"
echo -e "  ${BOLD}• Backend API:${RESET}      ${CYAN}http://localhost:8000${RESET}"
echo -e "  ${BOLD}• API Docs:${RESET}         ${CYAN}http://localhost:8000/v1/docs${RESET}"
echo ""
echo -e "${YELLOW}Press [CTRL + C] anytime to stop all services.${RESET}"
echo "=================================================="
echo ""

# Wait on both background processes
wait "${BACKEND_PID}" "${FRONTEND_PID}"

