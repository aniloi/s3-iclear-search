.PHONY: help install install-dev build-frontend build dev test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: build-frontend ## Install the package with UI dependencies
	pip install -e ".[ui]"

install-dev: build-frontend ## Install with all dev dependencies
	pip install -e ".[dev]"

build-frontend: ## Build the React frontend
	cd frontend && npm install && npm run build

build: build-frontend ## Full build (frontend + pip install)
	pip install -e ".[ui]"

dev-backend: ## Run the FastAPI backend in dev mode
	uvicorn s3_search.api.app:app --reload --port 8080

dev-frontend: ## Run the Vite dev server (proxies to backend)
	cd frontend && npm run dev

test: ## Run all tests
	pytest -v

test-backend: ## Run backend tests only
	pytest -v tests/test_api_*.py

test-cli: ## Run CLI tests only
	pytest -v tests/test_*.py --ignore=tests/test_api_models.py --ignore=tests/test_api_profiles.py --ignore=tests/test_api_executor.py --ignore=tests/test_api_app.py

clean: ## Clean build artifacts
	rm -rf src/s3_search/static
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf src/s3_fintrans_search.egg-info
