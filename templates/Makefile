.PHONY: help install test lint format clean build

help: ## Show help message
	@echo "Genesis Project Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install
	poetry run pre-commit install

test: ## Run tests
	poetry run pytest tests/ -v --cov=src --cov-report=html

lint: ## Run linting
	poetry run ruff check .
	poetry run mypy src/

format: ## Format code
	poetry run black .
	poetry run ruff check . --fix

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/
	rm -rf .coverage htmlcov/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/

build: ## Build package
	poetry build

dev: ## Start development server
	poetry run PROJECT_NAME serve --dev

deploy: ## Deploy application
	poetry run PROJECT_NAME deploy