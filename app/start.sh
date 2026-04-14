#!/bin/bash
# Start both backend and frontend servers for Kaelo.
# Usage: ./app/start.sh

set -e
cd "$(dirname "$0")/.."

echo "Starting backend (FastAPI) on http://localhost:8000 ..."
python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Starting frontend (Vite) on http://localhost:5173 ..."
cd app/frontend
npx vite --port 5173 &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000/api/health"
echo "  Frontend: http://localhost:5173"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
