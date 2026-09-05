#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
step() { echo -e "\n${BOLD}$1${NC}"; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════╗"
echo "║        GridForecast AI  —  Setup             ║"
echo "║   Delhi Electricity Demand Forecasting       ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
info "Project directory: $PROJECT_DIR"

# ── Step 1: Python version check ─────────────────────────────
step "[1/8] Checking Python..."
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    MAJOR=$(echo $VER | cut -d. -f1)
    MINOR=$(echo $VER | cut -d. -f2)
    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; then
      PYTHON="$cmd"
      ok "Found Python $VER ($cmd)"
      if [ "$MINOR" -ge 13 ]; then
        warn "Python $VER detected. TensorFlow (CNN/LSTM) requires Python ≤3.12."
        warn "All other models (XGBoost, RandomForest, etc.) will work fine."
      fi
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  fail "Python 3.10+ not found. Install from https://python.org"
fi

# ── Step 2: Node.js check ────────────────────────────────────
step "[2/8] Checking Node.js..."
if ! command -v node &>/dev/null; then
  fail "Node.js not found. Install from https://nodejs.org (v18+)"
fi
NODE_VER=$(node --version)
ok "Found Node.js $NODE_VER"
if ! command -v npm &>/dev/null; then
  fail "npm not found. Install Node.js from https://nodejs.org"
fi

# ── Step 3: Python virtualenv ────────────────────────────────
step "[3/8] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
  info "Creating venv..."
  "$PYTHON" -m venv venv
  ok "venv created"
else
  ok "venv already exists"
fi

VENV_PYTHON="venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
  VENV_PYTHON="venv/bin/python"
fi

# ── Step 4: Install Python dependencies ─────────────────────
step "[4/8] Installing Python dependencies..."
info "This may take 2–3 minutes on first run..."

"$VENV_PYTHON" -m pip install --upgrade pip -q 2>&1 | grep -v "^$" || true

PACKAGES=(
  "fastapi" "uvicorn[standard]" "python-multipart" "starlette"
  "pandas" "numpy" "pyarrow" "openpyxl"
  "scikit-learn" "xgboost" "scipy" "joblib"
  "prophet" "statsmodels" "holidays"
  "httpx" "requests" "beautifulsoup4" "lxml" "playwright"
  "sqlalchemy" "aiosqlite" "aiofiles"
  "pydantic" "pydantic-settings" "python-dotenv"
  "apscheduler" "ruff"
)

"$VENV_PYTHON" -m pip install "${PACKAGES[@]}" --no-user -q 2>&1 | tail -3
ok "Python packages installed"

# Install Playwright browser
info "Installing Playwright browser (needed for Delhi SLDC scraping)..."
"$VENV_PYTHON" -m playwright install chromium --with-deps 2>&1 | tail -3
ok "Playwright browser installed"

# Try TensorFlow (only works on Python ≤3.12)
"$VENV_PYTHON" -m pip install tensorflow --no-user -q 2>&1 | tail -2 || warn "TensorFlow not available for this Python version (CNN/LSTM will be skipped)"

# ── Step 5: Create directories ───────────────────────────────
step "[5/8] Creating data directories..."
mkdir -p data/{raw,processed,models} logs
ok "Directories created"

# ── Step 6: Copy .env ────────────────────────────────────────
step "[6/8] Setting up configuration..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  ok ".env created from .env.example"
else
  ok ".env already exists"
fi

# ── Step 7: Download real data ───────────────────────────────
step "[7/8] Downloading real Delhi demand + weather data..."
info "Fetching real data from delhisldc.org and Open-Meteo..."
info "This downloads ~600 days of real 5-minute demand readings..."
"$VENV_PYTHON" scripts/download_real_data.py
ok "Real data downloaded and processed"

# ── Step 8: Frontend ─────────────────────────────────────────
step "[8/8] Installing frontend dependencies..."
cd frontend
npm install --legacy-peer-deps --silent 2>&1 | tail -3
cd ..
ok "Frontend dependencies installed"

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════╗"
echo "║           Setup Complete!                    ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "Start the system with ${BOLD}two terminal windows${NC}:"
echo ""
echo -e "  ${BOLD}Terminal 1 — Backend:${NC}"
echo -e "  ${BLUE}cd $PROJECT_DIR${NC}"
echo -e "  ${BLUE}venv/bin/python3 -m uvicorn backend.api.main:app --reload --port 8000${NC}"
echo ""
echo -e "  ${BOLD}Terminal 2 — Frontend:${NC}"
echo -e "  ${BLUE}cd $PROJECT_DIR/frontend${NC}"
echo -e "  ${BLUE}npm start${NC}"
echo ""
echo -e "  Then open ${BOLD}http://localhost:3000${NC}"
echo ""
echo -e "  Or use the quick-start script: ${BOLD}./scripts/start.sh${NC}"
echo ""
