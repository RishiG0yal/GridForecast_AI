#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

VENV_PYTHON=""
for p in venv/bin/python3.12 venv/bin/python3.11 venv/bin/python3.10 venv/bin/python3.14 venv/bin/python3 venv/bin/python; do
  if [ -f "$p" ]; then
    VENV_PYTHON="$p"
    break
  fi
done

if [ -z "$VENV_PYTHON" ]; then
  echo "venv not found. Run: bash scripts/setup.sh"
  exit 1
fi

echo -e "${BOLD}GridForecast AI — Starting...${NC}"
echo ""

# Start backend in background
echo -e "${BLUE}→${NC} Starting backend on http://localhost:8000"
"$VENV_PYTHON" -m uvicorn backend.api.main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!

# Wait for backend to be ready
echo -e "${BLUE}→${NC} Waiting for backend..."
for i in $(seq 1 15); do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend ready"
    break
  fi
  sleep 1
done

# Start frontend
echo -e "${BLUE}→${NC} Starting frontend on http://localhost:3000"
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${BOLD}${GREEN}Both services started!${NC}"
echo ""
echo -e "  Dashboard  : ${BOLD}http://localhost:3000${NC}"
echo -e "  API docs   : ${BOLD}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop both"
echo ""

trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
