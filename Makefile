.PHONY: help install install-dev test lint format typecheck clean dev-api dev-services dev-web build docker-build docker-up docker-down setup-env

help:
	@echo "PRISM Development Commands"
	@echo "=========================="
	@echo "install          - Install production dependencies from requirements.txt"
	@echo "install-dev      - Install dev dependencies from requirements-dev.txt"
	@echo "install-editable - Install package in editable mode (for development)"
	@echo "setup-env        - Create .env file from .env.example"
	@echo "test             - Run all tests"
	@echo "lint             - Run linters (ruff)"
	@echo "format           - Format code (black, ruff, prettier)"
	@echo "typecheck        - Run type checking (mypy, tsc)"
	@echo "clean            - Clean build artifacts"
	@echo "dev-api          - Run API server in development mode"
	@echo "dev-services     - Start PostgreSQL and Redis via Docker"
	@echo "dev-web          - Run web app in development mode"
	@echo "build            - Build all packages"
	@echo "docker-build     - Build Docker images"
	@echo "docker-up        - Start all services with Docker Compose"
	@echo "docker-down      - Stop all Docker Compose services"

install:
	pip install -r requirements.txt
	cd frontend && pnpm install

install-dev:
	pip install -r requirements-dev.txt
	cd frontend && pnpm install

install-editable:
	pip install -e ".[dev]"
	cd frontend && pnpm install

setup-env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file from .env.example"; \
		echo "Please update .env with your API keys"; \
	else \
		echo ".env file already exists"; \
	fi

test:
	pytest
	cd frontend && pnpm test

lint:
	ruff check backend/
	cd frontend && pnpm lint

format:
	black backend/
	ruff check --fix backend/
	cd frontend && pnpm format

typecheck:
	mypy backend/
	cd frontend && pnpm typecheck

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	cd frontend && pnpm clean 2>/dev/null || true
	rm -rf dist/ build/ .coverage htmlcov/

dev-api:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup-env' first"; \
		exit 1; \
	fi
	uvicorn backend.apps.api.src.main:app --reload --host 0.0.0.0 --port 8000

dev-services:
	docker-compose up -d db redis
	@echo "PostgreSQL and Redis started"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"

dev-web:
	cd frontend/apps/web && pnpm dev

build:
	pip install build
	python -m build
	cd frontend && pnpm build

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "All services started"
	@echo "API: http://localhost:8000"
	@echo "Web: http://localhost:3000"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"

docker-down:
	docker-compose down
