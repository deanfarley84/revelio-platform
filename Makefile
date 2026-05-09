.PHONY: up down build seed logs shell-backend shell-db

up:
	docker-compose up

build:
	docker-compose up --build

down:
	docker-compose down

seed:
	python scripts/setup.py

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-worker:
	docker-compose logs -f worker

shell-backend:
	docker-compose exec backend bash

shell-db:
	docker-compose exec db psql -U revelio -d revelio

restart-worker:
	docker-compose restart worker

format:
	cd backend && black app/

test:
	cd backend && pytest tests/ -v
