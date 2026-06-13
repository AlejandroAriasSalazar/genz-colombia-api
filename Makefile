# GenZ Colombia API - Makefile
# Comandos comunes para desarrollo

.PHONY: help install run seed test lint clean docker-up docker-down docker-seed

help: ## Mostrar ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Instalar dependencias
	pip install -r requirements.txt

run: ## Ejecutar API en modo desarrollo
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

seed: ## Ejecutar seed data
	python -m scripts.seed_data

create-key: ## Crear API key (usar: make create-key NAME="Mi App" TIER=pro)
	python -m scripts.create_api_keys --name "$(NAME)" --tier "$(TIER)"

test: ## Ejecutar tests
	pytest tests/ -v

test-cov: ## Ejecutar tests con cobertura
	pytest tests/ --cov=app --cov-report=html

lint: ## Ejecutar linting
	ruff check app/ tests/
	mypy app/

format: ## Formatear código
	ruff format app/ tests/

clean: ## Limpiar archivos temporales
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf htmlcov .coverage

docker-up: ## Levantar servicios con Docker Compose
	docker-compose up -d

docker-down: ## Detener servicios Docker
	docker-compose down

docker-seed: ## Ejecutar seed data en Docker
	docker-compose run --rm seed

docker-logs: ## Ver logs de Docker
	docker-compose logs -f

docker-build: ## Reconstruir imágenes Docker
	docker-compose build --no-cache

docker-restart: ## Reiniciar servicios Docker
	docker-compose restart

check-health: ## Verificar health de la API
	curl -s http://localhost:8000/health | python -m json.tool

check-docs: ## Abrir documentación en navegador
	open http://localhost:8000/docs

migrate-init: ## Inicializar Alembic
	alembic init alembic

migrate-create: ## Crear migración (usar: make migrate-create MSG="mensaje")
	alembic revision --autogenerate -m "$(MSG)"

migrate-apply: ## Aplicar migraciones
	alembic upgrade head

migrate-rollback: ## Revertir última migración
	alembic downgrade -1
