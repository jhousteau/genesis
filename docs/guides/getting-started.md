# Genesis HOW TO Guide

Step-by-step guide to using Genesis for AI-safe development.

## Quick Start (5 Minutes)

### 1. Install Genesis

```bash
# Clone and install
git clone <repository-url>
cd genesis
pip install -e .

# Verify installation
genesis --help
```

### 2. Create Your First Project

```bash
# Create a Python API project
genesis bootstrap my-api --type python-api

# Create a CLI tool
genesis bootstrap my-cli --type cli-tool

# Create a TypeScript service
genesis bootstrap my-service --type typescript-service
```

### 3. Start Development

```bash
cd my-api
make setup    # Install dependencies
make test     # Run tests
make lint     # Check code quality
```

## Project Types

### Python API (`python-api`)
Complete FastAPI project with:
- FastAPI framework with auto-documentation
- Poetry for dependency management
- Pytest with async support and coverage
- Pre-commit hooks and quality gates
- Health endpoints and proper structure

**Created structure:**
```
my-api/
├── src/my_api/
│   ├── __init__.py
│   └── main.py        # FastAPI app
├── tests/
│   └── test_main.py   # Test suite
├── README.md          # Complete documentation
├── pyproject.toml     # Poetry config
├── Makefile          # Development commands
└── .gitignore        # Python ignores
```

### CLI Tool (`cli-tool`)
Feature-rich command-line application with:
- Click framework for commands
- Rich library for beautiful terminal output
- Poetry for dependency management
- Pytest with coverage reporting
- Type checking and code formatting

**Created structure:**
```
my-cli/
├── src/my_cli/
│   ├── __init__.py
│   ├── main.py        # Entry point
│   └── cli.py         # Click commands
├── tests/
│   └── test_cli.py    # CLI tests
├── README.md          # Installation and usage
├── pyproject.toml     # Dependencies and scripts
└── Makefile          # Dev commands
```

### TypeScript Service (`typescript-service`)
Modern TypeScript service with:
- Express.js framework
- Jest for testing
- ESLint and Prettier for code quality
- Health endpoints
- Docker ready

**Created structure:**
```
my-service/
├── src/
│   ├── app.ts         # Express app
│   ├── index.ts       # Server entry
│   └── routes/
│       └── health.ts  # Health checks
├── tests/
│   └── app.test.ts    # Test suite
├── package.json       # Dependencies
├── tsconfig.json      # TypeScript config
└── README.md          # Service documentation
```

## AI-Safe Development Workflow

### The Problem
AI tools struggle with large codebases (>100 files), leading to:
- Accidental modifications to unrelated files
- Security risks from exposing entire codebase
- Slow responses due to excessive context

### The Solution: Sparse Worktrees
Genesis creates isolated work environments with only 5-30 files:

```bash
# Create focused worktree for authentication feature
genesis worktree create feature-auth src/auth.py tests/test_auth.py

# AI now sees only these files, not entire codebase
cd ../feature-auth
find . -type f | wc -l  # Returns: 23 files (AI-safe!)
```

### Development Workflow

1. **Create worktree** for your specific task
2. **Work in isolation** with AI assistance
3. **Quality gates** prevent bad code
4. **Smart commit** with autofix
5. **Merge** back to main

## Smart Commit System

Genesis automatically fixes your code before committing:

```bash
# Smart commit with multi-stage autofix
genesis commit --message "feat: add user authentication"

# What happens automatically:
# 1. Format code (Black, Prettier)
# 2. Fix linting issues (Ruff, ESLint)
# 3. Run convergent fixing until stable
# 4. Run tests
# 5. Security scan
# 6. Create commit
```

## Command Reference

### Project Management
```bash
genesis bootstrap <name> --type <template>  # Create new project
genesis status                              # Check project health
genesis sync                               # Update dependencies
genesis clean                              # Clean artifacts
```

### AI-Safe Development
```bash
genesis worktree create <name> <files>     # Create sparse worktree
genesis commit --message "description"     # Smart commit with autofix
```

### Available Templates
- `python-api` - FastAPI service (default)
- `cli-tool` - Command-line application  
- `typescript-service` - Express.js service
- `terraform-project` - Infrastructure project

## Multi-Stage Autofix

Genesis uses convergent fixing to ensure code quality:

### Stage 1: Formatters
- **Black**: Python code formatting
- **Prettier**: TypeScript/JavaScript formatting  
- **isort**: Python import organization

### Stage 2: Linters
- **Ruff**: Fast Python linter with auto-fixes
- **ESLint**: TypeScript/JavaScript linting

### Stage 3: Convergence
- Runs stages repeatedly until code is stable
- Maximum 10 iterations to prevent infinite loops
- Stops when no more changes are made

## Error Handling & Resilience

Genesis provides production-ready error handling:

```python
from genesis.core.errors import handle_error, ErrorCategory
from genesis.core.retry import CircuitBreaker

# Structured error handling with context
try:
    risky_operation()
except Exception as e:
    handle_error(e, ErrorCategory.NETWORK, {"operation": "api_call"})

# Circuit breaker prevents cascading failures
breaker = CircuitBreaker(failure_threshold=5, timeout=60)
result = breaker.call(potentially_failing_function)
```

## Infrastructure Automation

Deploy complete infrastructure with Terraform:

```bash
# Create infrastructure project
genesis bootstrap my-infra --type terraform-project

# Deploy with Genesis modules
cd my-infra
terraform init
terraform plan
terraform apply
```

Available Terraform modules:
- `bootstrap` - Project setup and APIs
- `project-setup` - IAM and service accounts
- `state-backend` - Terraform state storage
- `service-accounts` - Service account management

## Best Practices

### 1. Always Use Sparse Worktrees
```bash
# ❌ DON'T: Work in main repository (3000+ files)
cd genesis
# AI sees everything, security risk!

# ✅ DO: Create focused worktree (5-30 files)
genesis worktree create fix-auth src/auth.py tests/test_auth.py
cd ../fix-auth
# AI sees only relevant files, safe!
```

### 2. Use Smart Commits
```bash
# ❌ DON'T: Manual commits without quality checks
git add .
git commit -m "fix stuff"

# ✅ DO: Smart commits with autofix and quality gates
genesis commit --message "fix: resolve authentication timeout issue"
```

### 3. Follow File Limits
- **Main repo**: Keep under 100 files for AI safety
- **Worktrees**: Maximum 30 files per worktree
- **Components**: Each component under 30 files

### 4. Template-Driven Development
```bash
# ✅ Start with templates for consistency
genesis bootstrap my-api --type python-api

# ❌ Don't start from scratch
mkdir my-api && cd my-api  # Missing patterns, tooling
```

## Troubleshooting

### Genesis Not Found
```bash
# Check you're in Genesis directory
genesis status  # Should show Genesis root

# Or install from source
git clone <repo> && cd genesis && pip install -e .
```

### Bootstrap Fails
```bash
# Check available templates
ls templates/  # Should show: python-api, cli-tool, etc.

# Try with different type
genesis bootstrap test --type cli-tool
```

### Worktree Issues
```bash
# Check if worktree tools exist
ls worktree-tools/src/create-sparse-worktree.sh

# Manual worktree creation
git worktree add ../feature-name -b feature-name
cd ../feature-name
git sparse-checkout init --cone
git sparse-checkout set src/specific.py
```

### Smart Commit Fails
```bash
# Check smart-commit exists
ls smart-commit/src/smart-commit.sh

# Manual quality checks
make lint
make format
make test
git add . && git commit -m "message"
```

## Getting Help

```bash
# Command help
genesis --help
genesis bootstrap --help

# Check project status
genesis status --verbose

# Clean and retry
genesis clean --all
```

## Next Steps

1. **Create your first project**: `genesis bootstrap my-project`
2. **Set up sparse worktree**: `genesis worktree create feature src/feature.py`
3. **Develop with AI assistance** in isolated environment
4. **Smart commit changes**: `genesis commit --message "feat: description"`
5. **Deploy infrastructure**: Use Terraform templates for production

Genesis ensures your development is **AI-safe**, **quality-first**, and **production-ready** from day one.