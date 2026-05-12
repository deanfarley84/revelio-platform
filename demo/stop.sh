#!/bin/bash
echo ""
echo "Stopping Vyre demo..."
docker-compose -f docker-compose.demo.yml down
echo ""
echo "Demo stopped. All demo data removed."
echo "Run ./demo/start.sh to restart with fresh data."
echo ""
