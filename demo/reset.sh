#!/bin/bash
# Wipes demo data and restarts with fresh seed
echo ""
echo "Resetting Revelio demo (fresh data)..."
docker-compose -f docker-compose.demo.yml down --volumes
echo "Restarting..."
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY docker-compose -f docker-compose.demo.yml up --build -d
echo ""
echo "Demo reset complete. Fresh data loading..."
echo "Open http://localhost:3000 in ~30 seconds"
echo ""
