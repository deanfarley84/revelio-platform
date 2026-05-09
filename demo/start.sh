#!/bin/bash
# ============================================================
# Revelio Demo Launcher
# Usage: ./demo/start.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
AMBER='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}Revelio — Demo Mode${NC}"
echo "============================================"
echo ""

# Check ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
  if [ -f ".env" ]; then
    export $(grep ANTHROPIC_API_KEY .env | xargs) 2>/dev/null || true
  fi
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo -e "${RED}Missing ANTHROPIC_API_KEY${NC}"
  echo ""
  echo "Set it before running:"
  echo "  export ANTHROPIC_API_KEY=sk-ant-your-key-here"
  echo "  ./demo/start.sh"
  echo ""
  exit 1
fi

echo -e "${GREEN}✓${NC} API key found"

# Check Docker
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Docker is not running. Start Docker Desktop and try again.${NC}"
  exit 1
fi
echo -e "${GREEN}✓${NC} Docker running"
echo ""

# Clean previous demo state
echo -e "${AMBER}Cleaning previous demo state...${NC}"
docker-compose -f docker-compose.demo.yml down --volumes 2>/dev/null || true
echo ""

# Build and start
echo -e "${BLUE}Starting Revelio demo...${NC}"
echo "(First build takes 2–3 minutes)"
echo ""

ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY docker-compose -f docker-compose.demo.yml up --build -d

echo ""
echo -e "${AMBER}Waiting for services to start...${NC}"
sleep 8

# Wait for backend health
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo ""
echo "============================================"
echo -e "${GREEN}${BOLD}Revelio is running!${NC}"
echo "============================================"
echo ""
echo -e "  ${BOLD}Platform:${NC}  http://localhost:3000"
echo -e "  ${BOLD}API docs:${NC}  http://localhost:8000/docs"
echo ""
echo -e "${BOLD}Demo accounts:${NC}"
echo ""
echo -e "  ${BLUE}OPERATOR (Admin)${NC}"
echo "  admin@revelio.io / Demo1234!"
echo ""
echo -e "  ${GREEN}CLIENT — Acme Retail (Released report)${NC}"
echo "  james@acmeretail.com / Demo1234!"
echo ""
echo -e "  ${AMBER}CLIENT — Volta Subscriptions (Pending approval)${NC}"
echo "  sarah@voltaapp.com / Demo1234!"
echo ""
echo -e "  ${BLUE}CLIENT — Kestrel Marketplace (In review)${NC}"
echo "  tom@kestrelmarket.io / Demo1234!"
echo ""
echo -e "${BOLD}Demo script:${NC} ./demo/DEMO_SCRIPT.md"
echo ""
echo -e "${AMBER}To stop:${NC} docker-compose -f docker-compose.demo.yml down"
echo ""

# Open browser
sleep 2
if command -v open > /dev/null; then
  open http://localhost:3000
elif command -v xdg-open > /dev/null; then
  xdg-open http://localhost:3000
fi
