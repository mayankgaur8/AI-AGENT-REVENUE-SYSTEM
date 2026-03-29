#!/bin/bash
# Quick start script for local development

set -e

echo "==================================="
echo " Revenue AI Agent System - Start"
echo "==================================="

# Check prerequisites
command -v python3 >/dev/null || { echo "Python 3 required"; exit 1; }
command -v node >/dev/null || { echo "Node.js required"; exit 1; }

# Backend setup
echo ""
echo ">> Setting up backend..."
cd backend

if [ ! -f .env ]; then
  cp .env.example .env
  echo "   Created .env from example. Edit it to add your ANTHROPIC_API_KEY."
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

echo ">> Starting backend on http://localhost:8000"
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Frontend setup
cd ../frontend
echo ""
echo ">> Setting up frontend..."

if [ ! -d node_modules ]; then
  npm install
fi

echo ">> Starting frontend on http://localhost:3000"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "==================================="
echo " System running!"
echo " Backend:  http://localhost:8000"
echo " Frontend: http://localhost:3000"
echo " API Docs: http://localhost:8000/docs"
echo "==================================="
echo " Press Ctrl+C to stop"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
