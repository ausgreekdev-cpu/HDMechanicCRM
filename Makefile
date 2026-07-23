.PHONY: help dev prod test lint clean deploy

help:
	@echo "HDMechanicCRM Commands:"
	@echo "  make dev      - Run development server"
	@echo "  make prod     - Run production server (gunicorn)"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run linter"
	@echo "  make clean    - Clean build artifacts"
	@echo "  make deploy   - Deploy with Docker"
	@echo "  make stop     - Stop Docker containers"
	@echo "  make logs     - View Docker logs"
	@echo "  make backup   - Backup database"

dev:
	python main.py

prod:
	gunicorn -c gunicorn.conf.py main:app

test:
	python -m pytest tests/ -v

lint:
	python -m py_compile main.py
	python -m py_compile app/__init__.py
	python -m py_compile app/database.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache build dist *.egg-info

deploy:
	bash deploy.sh

stop:
	docker compose down 2>/dev/null || docker-compose down

logs:
	docker compose logs -f web 2>/dev/null || docker-compose logs -f web

backup:
	@mkdir -p backups
	@cp data/crm.db backups/crm-$$(date +%Y%m%d-%H%M%S).db
	@echo "Database backed up to backups/"

restore:
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore FILE=backups/crm-YYYYMMDD.db"; exit 1; fi
	@cp $(FILE) data/crm.db
	@echo "Database restored from $(FILE)"
