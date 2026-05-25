.PHONY: help install dev dev-webhook docker-up docker-down lint test seed backup

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

dev:  ## Run bot in polling mode (local development)
	python -m bot.main

dev-webhook:  ## Run bot in webhook mode via FastAPI (local, requires tunnel)
	python -m web.asgi

docker-up:  ## Build & run with Docker
	docker compose -f docker/docker-compose.yml up --build -d

docker-down:  ## Stop Docker containers
	docker compose -f docker/docker-compose.yml down

webhook-set:  ## Register webhook URL with Telegram
	python scripts/set_webhook.py

webhook-delete:  ## Delete webhook (revert to polling)
	python scripts/delete_webhook.py

seed:  ## Re-seed default templates
	python scripts/seed_templates.py

test:  ## Run tests
	pytest tests/ -v

lint:  ## Lint check
	ruff check bot/ database/ web/ tests/
	ruff format --check bot/ database/ web/ tests/

backup:  ## Backup SQLite database
	bash scripts/backup_db.sh