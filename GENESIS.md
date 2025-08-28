# Genesis Architecture & Components

## Core Architecture

Genesis uses **sparse worktree isolation** to prevent AI contamination while enabling shared infrastructure.

### Problem Solved
- **Old way**: AI sees 3000+ files → accidental modifications, security risks
- **New way**: AI sees 5-30 files → safe, focused, fast development

### Directory Structure
```
genesis/                    # Main repo (human oversight only)
├── genesis_cli/           # CLI commands (21 files)
├── shared-infra/          # Shared components
│   ├── bootstrap/         # Project setup (16 files)
│   ├── smart-commit/      # Quality gates (35 files)
│   └── libs/              # Shared utilities (31 files)
└── tests/                 # Test suite

../genesis-cli/            # Sparse worktree (21 files)
../genesis-bootstrap/      # Sparse worktree (16 files)
../genesis-smart-commit/   # Sparse worktree (35 files)
../claude-workspace/       # Ultra-sparse for AI (5-10 files)
```

## Components

### 1. Genesis CLI (`genesis_cli/`)
**Purpose**: Unified command interface

**Commands**:
```bash
genesis bootstrap <name>    # Create new project
genesis worktree create     # Create sparse worktree
genesis sync               # Update shared components
genesis status             # Check project health
```

**Implementation**:
- Click-based CLI framework
- Modular command structure
- Built-in help and validation

### 2. Smart Commit (`shared-infra/smart-commit/`)
**Purpose**: Quality gates before commits

**Process**:
1. **Detect changes**: Analyze file modifications
2. **Run quality checks**: Format, lint, test
3. **Assess stability**: Calculate risk score
4. **Generate commit**: Format message, create commit

**Usage**:
```bash
cd shared-infra/smart-commit
poetry run smart-commit "feat: add authentication"
```

### 3. Bootstrap (`shared-infra/bootstrap/`)
**Purpose**: Automated project setup

**Templates**:
- `python-api`: FastAPI project
- `typescript-api`: Express.js project
- `cli-tool`: Click-based CLI
- `library`: Shared library template

**Process**:
```bash
genesis bootstrap my-project --template python-api
# Creates: structure, dependencies, configs, tests
```

### 4. Shared Libraries (`shared-infra/libs/`)

#### Python Libraries (`libs/python/shared_core/`)
- **Config**: Environment-aware configuration
- **Logger**: Structured logging with context
- **Errors**: Consistent error hierarchy
- **Retry**: Exponential backoff retry logic
- **Cache**: TTL-based caching utilities
- **Health**: Service health checking
- **Testing**: Test fixtures and helpers

#### TypeScript Libraries (`libs/typescript/`)
- **Parallel implementations** of Python utilities
- **Consistent API** across languages
- **Type-safe** interfaces

## Development Workflow

### 1. Create Sparse Worktree
```bash
# For CLI work
git worktree add --no-checkout ../genesis-cli feature/cli
cd ../genesis-cli
git sparse-checkout init --cone
git sparse-checkout set genesis_cli/ pyproject.toml
git checkout

# Verify isolation
find . -type f | wc -l  # Should be ~21 files
```

### 2. Make Changes
- Work in isolated environment
- AI only sees relevant files
- No risk of contaminating other components

### 3. Test Changes
```bash
# Run tests for your component
pytest tests/unit/test_cli.py -v

# Integration tests
pytest tests/integration/ -v
```

### 4. Smart Commit
```bash
# From sparse worktree
git add .
git commit -m "feat: add status command"

# Or use smart-commit for quality gates
cd ../genesis-smart-commit
poetry run smart-commit "feat: add status command"
```

### 5. Merge to Main
```bash
cd ../genesis  # Main repo
git merge feature/cli
```

## Shared Infrastructure Patterns

### Share, Don't Copy
```python
# Good: Import shared utilities
from shared_core import get_logger, Config, retry

# Bad: Copy-paste logging setup everywhere
```

### Single Source of Truth
- **One** smart-commit implementation
- **One** bootstrap system
- **One** configuration approach
- **One** testing framework (pytest)

### Minimal Dependencies
```toml
# pyproject.toml - Only essential dependencies
[tool.poetry.dependencies]
python = "^3.11"
click = "^8.0.0"        # CLI framework
pytest = "^8.0.0"       # Testing
pyyaml = "^6.0"         # Configuration
```

## Configuration

### Environment Variables
```bash
# Development
export GENESIS_ENV=development
export LOG_LEVEL=debug

# Production
export GENESIS_ENV=production
export LOG_LEVEL=warning
```

### Configuration Files
```yaml
# config/base.yaml
logging:
  level: info
  format: json

database:
  pool_size: 10
  timeout: 30
```

## Testing Strategy

### Test Structure
```
tests/
├── unit/          # Fast, isolated tests
├── integration/   # Cross-component tests
└── e2e/          # End-to-end workflows
```

### Test Patterns
```python
# Unit test example
def test_bootstrap_creates_project():
    bootstrap = Bootstrap()
    project = bootstrap.create("test-project")
    assert project.exists()

# Integration test example
def test_cli_bootstrap_integration():
    result = runner.invoke(cli, ['bootstrap', 'test'])
    assert result.exit_code == 0
```

### Coverage Requirements
- **Unit tests**: 90%+ coverage
- **Integration tests**: Happy path + error cases
- **E2E tests**: Complete workflows

## Templates & Scaffolding

### Project Templates
Located in `templates/`:
- **python-api/**: FastAPI template
- **typescript-api/**: Express template
- **cli-tool/**: Click CLI template

### Template Structure
```
templates/python-api/
├── src/
├── tests/
├── pyproject.toml
├── README.md
└── .gitignore
```

### Using Templates
```bash
genesis bootstrap my-api --template python-api
# Copies template, replaces variables, initializes git
```

## Performance & Scalability

### Sparse Worktree Benefits
- **Faster AI responses**: Less context to process
- **Reduced memory usage**: Only relevant files loaded
- **Faster git operations**: Smaller working directory

### Caching Strategy
```python
from shared_core import cache

@cache(ttl=300)  # 5 minutes
def expensive_operation():
    return compute_result()
```

### Resource Management
- Connection pooling in shared libraries
- Retry mechanisms with exponential backoff
- Circuit breakers for external services

## Security Considerations

### Secret Management
```python
# Good: Environment variables
api_key = os.getenv("API_KEY")

# Bad: Hardcoded secrets
api_key = "sk-123456789"  # Never do this
```

### Access Control
- Sparse worktrees limit file access
- No secrets in main repository
- Environment-based configuration

### Dependency Scanning
- Pre-commit hooks scan for vulnerabilities
- Regular dependency updates
- License compliance checking

## Deployment

### Simple Deployment
```bash
# Docker deployment
docker build -t genesis-app .
docker run -p 8000:8000 genesis-app

# Direct deployment
pip install -e .
genesis serve --port 8000
```

### Environment Promotion
```bash
# Development → Staging
genesis deploy --env staging

# Staging → Production
genesis deploy --env production --confirm
```

## Monitoring

### Health Checks
```python
from shared_core import HealthChecker

health = HealthChecker()
health.add_check("database", check_db)
health.add_check("cache", check_redis)
status = health.run_all()
```

### Logging
```python
from shared_core import get_logger

logger = get_logger(__name__)
logger.info("Operation completed", user_id=123, duration=0.5)
```

### Metrics
- Request/response times
- Error rates
- Component health status
- Resource utilization

## Migration from Old Code

### What We Kept
- **Smart commit concept**: Quality gates before commits
- **Bootstrap automation**: Project initialization
- **Shared libraries**: Common utilities
- **Testing structure**: Unit/integration/e2e

### What We Removed
- Multiple deployment strategies → Simple docker/k8s
- VM orchestration → Cloud Run/simple instances
- 631 README files → Single documentation
- 50 shell test scripts → pytest only
- 3 smart-commit systems → 1 implementation

### Lessons Applied
- **YAGNI**: You aren't gonna need it
- **Single responsibility**: One tool, one job
- **Share, don't copy**: Reuse > duplication
- **Documentation minimalism**: Show > tell
