.PHONY: setup test lint build clean help install-dev install-prod worktree-create file-check
.DEFAULT_GOAL := help

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Project detection
PROJECT_NAME := $(shell basename $(PWD))

setup: ## Install all dependencies and set up development environment
	@echo "$(GREEN)Setting up $(PROJECT_NAME) development environment...$(NC)"
	@if [ -f "pyproject.toml" ]; then \
		echo "$(BLUE)Installing Python dependencies with Poetry...$(NC)"; \
		poetry install; \
	fi
	@if [ -f "package.json" ]; then \
		echo "$(BLUE)Installing Node.js dependencies...$(NC)"; \
		npm install; \
	fi
	@if [ -f "go.mod" ]; then \
		echo "$(BLUE)Installing Go dependencies...$(NC)"; \
		go mod download; \
	fi
	@if [ -f ".pre-commit-config.yaml" ]; then \
		echo "$(BLUE)Installing pre-commit hooks...$(NC)"; \
		pre-commit install; \
	fi
	@echo "$(GREEN)✓ Setup complete!$(NC)"

install-dev: ## Install development dependencies only
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	@if [ -f "requirements/dev.txt" ]; then \
		pip install -r requirements/dev.txt; \
	elif [ -f "pyproject.toml" ]; then \
		poetry install --with dev; \
	fi

install-prod: ## Install production dependencies only
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	@if [ -f "requirements/base.txt" ]; then \
		pip install -r requirements/base.txt; \
	elif [ -f "pyproject.toml" ]; then \
		poetry install --without dev,test; \
	fi
	@if [ -f "package.json" ]; then \
		npm ci --only=production; \
	fi

test: ## Run all tests with coverage
	@echo "$(BLUE)Running tests for $(PROJECT_NAME)...$(NC)"
	@if [ -f "pyproject.toml" ] || [ -f "pytest.ini" ]; then \
		echo "$(BLUE)Running Python tests...$(NC)"; \
		pytest tests/ --cov=. --cov-report=term-missing; \
	fi
	@if [ -f "package.json" ] && [ -d "node_modules" ]; then \
		echo "$(BLUE)Running Node.js tests...$(NC)"; \
		npm test; \
	fi
	@if [ -f "go.mod" ]; then \
		echo "$(BLUE)Running Go tests...$(NC)"; \
		go test ./...; \
	fi

lint: ## Run all linters and formatters
	@echo "$(BLUE)Running linters for $(PROJECT_NAME)...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		echo "$(BLUE)Running ruff...$(NC)"; \
		ruff check .; \
	fi
	@if command -v black >/dev/null 2>&1; then \
		echo "$(BLUE)Running black...$(NC)"; \
		black --check .; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		echo "$(BLUE)Running mypy...$(NC)"; \
		mypy .; \
	fi
	@if [ -f "package.json" ] && command -v eslint >/dev/null 2>&1; then \
		echo "$(BLUE)Running eslint...$(NC)"; \
		npx eslint src/**/*.ts; \
	fi
	@if [ -f "go.mod" ]; then \
		echo "$(BLUE)Running go fmt and go vet...$(NC)"; \
		go fmt ./...; \
		go vet ./...; \
	fi

format: ## Auto-format all code
	@echo "$(BLUE)Formatting code for $(PROJECT_NAME)...$(NC)"
	@if command -v black >/dev/null 2>&1; then \
		echo "$(BLUE)Formatting Python with black...$(NC)"; \
		black .; \
	fi
	@if command -v ruff >/dev/null 2>&1; then \
		echo "$(BLUE)Auto-fixing with ruff...$(NC)"; \
		ruff check --fix .; \
	fi
	@if [ -f "package.json" ] && command -v prettier >/dev/null 2>&1; then \
		echo "$(BLUE)Formatting TypeScript with prettier...$(NC)"; \
		npx prettier --write src/**/*.ts; \
	fi
	@if [ -f "go.mod" ]; then \
		echo "$(BLUE)Formatting Go code...$(NC)"; \
		go fmt ./...; \
	fi

build: ## Build the project
	@echo "$(BLUE)Building $(PROJECT_NAME)...$(NC)"
	@if [ -f "pyproject.toml" ]; then \
		echo "$(BLUE)Building Python package...$(NC)"; \
		poetry build; \
	fi
	@if [ -f "package.json" ]; then \
		echo "$(BLUE)Building TypeScript...$(NC)"; \
		npm run build; \
	fi
	@if [ -f "go.mod" ]; then \
		echo "$(BLUE)Building Go binary...$(NC)"; \
		go build -o bin/$(PROJECT_NAME) .; \
	fi

clean: ## Clean build artifacts and caches
	@echo "$(BLUE)Cleaning $(PROJECT_NAME)...$(NC)"
	@rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	@rm -rf node_modules/.cache/ .next/ out/
	@rm -rf bin/ target/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete!$(NC)"

worktree-create: ## Create AI-safe sparse worktree (requires name and path)
ifndef name
	$(error Missing required parameter: name. Usage: make worktree-create name=<name> path=<path>)
endif
ifndef path
	$(error Missing required parameter: path. Usage: make worktree-create name=<name> path=<path>)
endif
	@if [ -f "./worktree-tools/create-sparse-worktree.sh" ]; then \
		echo "$(BLUE)Creating sparse worktree: $(name) for $(path)...$(NC)"; \
		./worktree-tools/create-sparse-worktree.sh $(name) $(path); \
	else \
		echo "$(YELLOW)worktree-tools/create-sparse-worktree.sh not found. Creating basic worktree...$(NC)"; \
		git worktree add ../$(name) -b $(name); \
		echo "$(YELLOW)⚠️  Basic worktree created. Consider implementing sparse worktree tools.$(NC)"; \
	fi

file-check: ## Verify AI safety file limits
	@echo "$(BLUE)Checking file count for AI safety...$(NC)"
	@file_count=$$(find . -type f | wc -l); \
	echo "$(BLUE)Current file count: $$file_count$(NC)"; \
	if [ $$file_count -gt 100 ]; then \
		echo "$(RED)❌ WARNING: $$file_count files exceeds recommended limit of 100$(NC)"; \
		echo "$(YELLOW)Consider using sparse worktrees for AI-safe development$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ File count within AI safety limits$(NC)"; \
	fi

security: ## Run security checks
	@echo "$(BLUE)Running security checks for $(PROJECT_NAME)...$(NC)"
	@if command -v safety >/dev/null 2>&1; then \
		echo "$(BLUE)Checking Python dependencies for vulnerabilities...$(NC)"; \
		safety check; \
	fi
	@if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then \
		echo "$(BLUE)Checking Node.js dependencies for vulnerabilities...$(NC)"; \
		npm audit; \
	fi
	@if command -v detect-secrets >/dev/null 2>&1; then \
		echo "$(BLUE)Scanning for secrets...$(NC)"; \
		detect-secrets scan --all-files; \
	fi

version: ## Show project version information
	@echo "$(BLUE)$(PROJECT_NAME) version information:$(NC)"
	@if [ -f "pyproject.toml" ]; then \
		echo "Python: $$(poetry version 2>/dev/null || echo 'unknown')"; \
	fi
	@if [ -f "package.json" ]; then \
		echo "Node.js: $$(node -p "require('./package.json').version" 2>/dev/null || echo 'unknown')"; \
	fi
	@if [ -f "go.mod" ]; then \
		echo "Go: $$(go list -m 2>/dev/null || echo 'unknown')"; \
	fi

help: ## Show this help message
	@echo "$(BLUE)$(PROJECT_NAME) - Available commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make setup                          # Initial project setup"
	@echo "  make test                           # Run all tests"
	@echo "  make lint format                    # Lint and format code"
	@echo "  make worktree-create name=fix-bug path=src/bug.py"
	@echo "  make file-check                     # Check AI safety limits"