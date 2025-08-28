# Genesis

Modern development toolkit with AI-safe sparse worktree isolation and intelligent automation.

## Features

- **Unified Python Package**: Complete development toolkit in a single installable package
- **Smart Worktree Management**: AI-safe sparse worktrees with automatic file limits
- **Multi-Stage Autofix**: Convergent code fixing with formatters, linters, and quality gates
- **Error Framework**: Structured error handling with context management and correlation tracking
- **Circuit Breaker Resilience**: Prevents cascading failures with intelligent retry patterns  
- **Infrastructure Automation**: 10 Terraform modules for complete GCP infrastructure
- **Project Templates**: Bootstrap new projects with Python API, CLI, TypeScript service templates
- **Quality Gates**: Pre-commit hooks, security scanning, and continuous integration

## Installation

### Prerequisites

- Python 3.11+
- Poetry (for development)

### Install from Source

```bash
# Clone and install
git clone <repository-url>
cd genesis
pip install -e .
```

## Usage

After installation, you can use the `genesis` command:

```bash
# Show help
genesis --help

# Bootstrap new project
genesis bootstrap my-api --template python-api
genesis bootstrap my-cli --template cli-tool

# Create AI-safe worktree
genesis worktree create feature/auth --files src/auth.py tests/test_auth.py

# Smart commit with autofix
genesis commit --message "feat: add authentication system"

# Run multi-stage autofix
genesis fix src/ --convergent

# Show project status
genesis status
```

## Available Commands

- `bootstrap` - Create new project from templates
- `worktree` - Manage AI-safe sparse worktrees
- `commit` - Smart commit with quality gates and autofix
- `fix` - Multi-stage autofix with convergent fixing
- `status` - Show project and system status

## Development

```bash
# Install dependencies
pip install -e .

# Run tests
pytest tests/ --cov

# Format code
make format

# Lint code  
make lint

# Run all quality checks
make test
```

## Project Structure

```
genesis/
├── genesis/                 # Main Python package
│   ├── cli.py              # CLI entry point
│   ├── commands/           # CLI command implementations
│   ├── core/               # Core utilities
│   │   ├── autofix/        # Multi-stage autofix system
│   │   ├── errors/         # Error framework with context
│   │   ├── context/        # Context management
│   │   └── ...            # Config, health, logger, retry
│   └── testing/           # Testing utilities
├── terraform/             # Infrastructure modules (10 modules)
├── templates/             # Project templates
├── smart-commit/          # Smart commit tooling
└── tests/                # Test suite
```

## Architecture

Genesis follows the **"Build Generic, Use Everywhere"** principle:

1. **Unified Package**: Single `pip install -e .` gets everything
2. **AI Safety**: Sparse worktrees limit context to <30 files  
3. **Quality First**: Autofix convergence ensures code correctness
4. **Infrastructure Ready**: Terraform modules for production deployment
5. **Template Driven**: Consistent project bootstrapping

## Error Handling

Genesis provides structured error handling with 14 categories:

```python
from genesis.core.errors import handle_error, ErrorCategory

# Automatic context enrichment and correlation tracking
try:
    risky_operation()
except Exception as e:
    handle_error(e, ErrorCategory.NETWORK, {"operation": "api_call"})
```

## Circuit Breaker

Prevent cascading failures with intelligent retry patterns:

```python
from genesis.core.retry import CircuitBreaker

# Three states: CLOSED, OPEN, HALF_OPEN
breaker = CircuitBreaker(failure_threshold=5, timeout=60)
result = breaker.call(potentially_failing_function, arg1, arg2)
```

## Autofix System

Multi-stage convergent fixing:

```python
from genesis.core.autofix import AutoFixer

# Stage 1: Formatters (Black, Prettier)
# Stage 2: Linters (Ruff, ESLint)  
# Stage 3: Convergent fixing until stable
fixer = AutoFixer()
result = fixer.run()  # Runs all stages
```

## Infrastructure

Deploy complete infrastructure with Terraform modules:

```bash
# Bootstrap infrastructure
genesis bootstrap my-infra --template terraform-project

# Deploy with modules
cd my-infra
terraform init
terraform plan
terraform apply
```

## Testing

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run security checks
make security

# Run all quality checks
make quality
```

## Contributing

1. Create sparse worktree for your feature: `genesis worktree create feature/my-feature`
2. Make your changes in isolated environment (5-30 files only)
3. Add tests for new functionality
4. Use smart commit: `genesis commit --message "feat: description"`
5. Submit pull request

## AI Safety

Genesis enforces AI safety through:

- **File Limits**: Maximum 30 files per worktree context
- **Sparse Worktrees**: Automatic isolation of work areas
- **Context Boundaries**: Clear separation between components
- **Quality Gates**: Prevent corrupted or insecure code

## License

MIT License - see LICENSE file for details.