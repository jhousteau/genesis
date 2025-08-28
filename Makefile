.PHONY: setup test lint build clean help install-dev install-prod worktree-create file-check bootstrap status commit sync ai-safety-report extraction-status genesis-cli genesis-lint genesis-lint-fix genesis-lint-fix-all genesis-format genesis-test genesis-quality
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

lint: ## Run all linters and formatters
	@echo "$(BLUE)Running linters for $(PROJECT_NAME)...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		echo "$(BLUE)Running ruff (respects .gitignore)...$(NC)"; \
		ruff check .; \
	fi
	@if command -v black >/dev/null 2>&1; then \
		echo "$(BLUE)Running black (respects .gitignore)...$(NC)"; \
		black --check .; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		echo "$(BLUE)Running mypy (respects .gitignore)...$(NC)"; \
		mypy .; \
	fi
	@if [ -f "package.json" ] && command -v eslint >/dev/null 2>&1; then \
		echo "$(BLUE)Running eslint...$(NC)"; \
		if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
			git ls-files --cached --others --exclude-standard | grep -E '\.(ts|js)$$' | xargs -r npx eslint; \
		else \
			npx eslint src/**/*.ts; \
		fi; \
	fi

format: ## Auto-format all code with Genesis AutoFixer
	@echo "$(BLUE)Formatting code for $(PROJECT_NAME) with Genesis AutoFixer...$(NC)"
	@if python -c "from genesis.core.autofix import AutoFixer" 2>/dev/null; then \
		echo "$(BLUE)Using Genesis AutoFixer for multi-stage formatting...$(NC)"; \
		python -c "from genesis.core.autofix import AutoFixer; fixer = AutoFixer(); result = fixer.run_stage_only(['formatter']); exit(0 if result.success else 1)"; \
	else \
		echo "$(YELLOW)Genesis AutoFixer not available, using legacy formatting...$(NC)"; \
		if command -v black >/dev/null 2>&1; then \
			echo "$(BLUE)Formatting Python with black (respects .gitignore)...$(NC)"; \
			black .; \
		fi; \
		if command -v ruff >/dev/null 2>&1; then \
			echo "$(BLUE)Auto-fixing with ruff (respects .gitignore)...$(NC)"; \
			ruff check --fix .; \
		fi; \
		if [ -f "package.json" ] && command -v prettier >/dev/null 2>&1; then \
			echo "$(BLUE)Formatting TypeScript with prettier...$(NC)"; \
			if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
				git ls-files --cached --others --exclude-standard | grep -E '\.(ts|js)$$' | xargs -r npx prettier --write; \
			else \
				npx prettier --write src/**/*.ts; \
			fi; \
		fi; \
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
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		file_count=$$(git ls-files --cached --others --exclude-standard | wc -l | tr -d ' '); \
		echo "$(BLUE)Current file count (respecting .gitignore): $$file_count$(NC)"; \
	else \
		file_count=$$(find . -type f -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./__pycache__/*" -not -path "./old-bloated-code-read-only/*" | wc -l | tr -d ' '); \
		echo "$(BLUE)Current file count (basic exclusions): $$file_count$(NC)"; \
	fi; \
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

genesis-cli: ## Install Genesis CLI for development
	@echo "$(BLUE)Installing Genesis CLI for development...$(NC)"
	@poetry install
	@echo "$(GREEN)✓ Genesis CLI installed!$(NC)"
	@echo "$(YELLOW)You can now use: poetry run python -m genesis.cli --help$(NC)"

genesis-lint: ## Lint Genesis Python components specifically
	@echo "$(BLUE)Linting Genesis Python components...$(NC)"
	@cd shared-python && poetry run ruff check .
	@poetry run ruff check genesis/
	@echo "$(GREEN)✓ Genesis linting complete$(NC)"

genesis-lint-fix: ## Lint and auto-fix Genesis Python components with AutoFixer
	@echo "$(BLUE)Running Genesis AutoFixer system...$(NC)"
	@if python -c "from genesis.core.autofix import AutoFixer" 2>/dev/null; then \
		echo "$(BLUE)Using Genesis AutoFixer with convergent fixing...$(NC)"; \
		python -c "from genesis.core.autofix import AutoFixer; fixer = AutoFixer(); result = fixer.run(); exit(0 if result.success else 1)"; \
	else \
		echo "$(YELLOW)Genesis AutoFixer not available, using legacy mode...$(NC)"; \
		cd shared-python && poetry run ruff check --fix . && cd .. && poetry run ruff check --fix genesis/; \
	fi
	@echo "$(GREEN)✓ Genesis auto-fix complete$(NC)"

genesis-lint-fix-all: ## Lint and auto-fix Genesis components (including unsafe fixes)
	@echo "$(BLUE)Linting and auto-fixing Genesis (including unsafe fixes)...$(NC)"
	@cd shared-python && poetry run ruff check --fix --unsafe-fixes .
	@poetry run ruff check --fix --unsafe-fixes genesis/
	@echo "$(GREEN)✓ Genesis comprehensive auto-fix complete$(NC)"

genesis-format: ## Format Genesis Python components specifically
	@echo "$(BLUE)Formatting Genesis Python components...$(NC)"
	@cd shared-python && poetry run black . && poetry run isort .
	@poetry run black genesis/ && poetry run isort genesis/
	@echo "$(GREEN)✓ Genesis formatting complete$(NC)"

genesis-test: ## Run Genesis-specific tests
	@echo "$(BLUE)Running Genesis test suite...$(NC)"
	@pytest -v --tb=short
	@echo "$(GREEN)✓ Genesis tests complete$(NC)"

genesis-quality: ## Run Genesis quality checks (format + lint-fix + test)
	@echo "$(BLUE)Running complete Genesis quality pipeline...$(NC)"
	@$(MAKE) genesis-format
	@$(MAKE) genesis-lint-fix
	@$(MAKE) genesis-test
	@echo "$(GREEN)✅ Genesis quality pipeline complete!$(NC)"

bootstrap: ## Create new project with Genesis (usage: make bootstrap name=my-project type=python-api)
ifndef name
	$(error Missing required parameter: name. Usage: make bootstrap name=<name> [type=python-api])
endif
	@echo "$(BLUE)Bootstrapping new project: $(name)...$(NC)"
	@source .envrc && poetry run python -m genesis.cli bootstrap $(name) --type $(or $(type),python-api)

status: ## Check Genesis project status
	@echo "$(BLUE)Checking Genesis project status...$(NC)"
	@source .envrc && poetry run python -m genesis.cli status

commit: ## Smart commit with Genesis quality gates
	@echo "$(BLUE)Running Genesis smart commit...$(NC)"
	@source .envrc && poetry run python -m genesis.cli commit --message "feat: Remove hardcoded defaults and enforce fail-fast configuration"

sync: ## Sync Genesis components
	@echo "$(BLUE)Syncing Genesis components...$(NC)"
	@source .envrc && poetry run python -m genesis.cli sync

ai-safety-report: ## Generate comprehensive AI safety report
	@echo "$(BLUE)Generating AI safety report...$(NC)"
	@python -c "from testing.utilities import print_ai_safety_report; from pathlib import Path; print_ai_safety_report(Path('.'))" 2>/dev/null || echo "$(YELLOW)⚠️  Install testing utilities first: make setup$(NC)"

extraction-status: ## Show Genesis extraction progress
	@echo "$(BLUE)Genesis Extraction Progress:$(NC)"
	@echo "$(GREEN)✅ Phase 0: Foundation - Complete$(NC)"
	@echo "$(GREEN)✅ Phase 1: Structure - Complete$(NC)"
	@echo "$(GREEN)✅ Phase 2: Components - Complete$(NC)"
	@echo "$(GREEN)✅ Phase 3: Testing & Templates - Complete$(NC)"
	@echo ""
	@echo "$(BLUE)Components Status:$(NC)"
	@for component in bootstrap genesis-cli shared-python smart-commit worktree-tools testing; do \
		if [ -d "$$component" ]; then \
			files=$$(find $$component -type f | wc -l | tr -d ' '); \
			if [ $$files -le 30 ]; then \
				echo "$(GREEN)✅ $$component: $$files files (AI safe)$(NC)"; \
			else \
				echo "$(YELLOW)⚠️  $$component: $$files files (check limits)$(NC)"; \
			fi; \
		else \
			echo "$(RED)❌ $$component: Missing$(NC)"; \
		fi; \
	done
	@echo ""
	@echo "$(BLUE)🎯 Status: Ready for production use$(NC)"

help: ## Show this help message
	@echo "$(BLUE)Genesis Development Toolkit$(NC)"
	@echo "$(BLUE)============================$(NC)"
	@echo ""
	@echo "$(YELLOW)Core Development:$(NC)"
	@grep -E '^(setup|test|lint|format|build|clean):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Genesis Commands:$(NC)"
	@grep -E '^(genesis-cli|genesis-lint|genesis-lint-fix|genesis-lint-fix-all|genesis-format|genesis-test|bootstrap|status|commit|sync|ai-safety-report|extraction-status):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Utilities:$(NC)"
	@grep -E '^(worktree-create|file-check|security|version):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make setup                          # Initial Genesis setup"
	@echo "  make genesis-cli                    # Install Genesis CLI"
	@echo "  make test                           # Run all tests"
	@echo "  make bootstrap name=my-api type=python-api"
	@echo "  make ai-safety-report               # Check AI safety"
	@echo "  make worktree-create name=fix-bug path=src/bug.py"
