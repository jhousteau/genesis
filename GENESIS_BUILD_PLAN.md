# FINAL COMPREHENSIVE GENESIS BUILD PLAN

## Critical Success Factors
Genesis must **demonstrate exactly what it automates**. Every setup step we do manually becomes a template for what Genesis will automate for future projects.

## Phase 0: Foundation (Genesis Eating Its Own Dog Food)
*These are the exact patterns Genesis will automate for others*

### 0.1 Create CLAUDE.md with Clear Context Separation
**Files to create:**
- `CLAUDE.md`

**Content structure:**
```markdown
# ⚠️ CONTEXT MODE: BUILDING GENESIS ⚠️
You are currently BUILDING Genesis, not using it.

## Context Detection Rules
- If EXTRACTION_PLAN.md exists → BUILDING MODE
- If old-bloated-code-read-only/ exists → BUILDING MODE
- If .genesis/ config exists → USING MODE

## Building vs Using Genesis
| NOW (Building)                | FUTURE (Using)                |
|-------------------------------|-------------------------------|
| Creating smart-commit.sh      | Running smart-commit.sh       |
| Building genesis CLI          | Running `genesis` commands    |
| Making shared-python/         | Importing from shared-python/ |
```

### 0.2 Environment Management Setup
**Files to create:**
- `.envrc` (direnv integration)
- `.env.example` (template with all variables)
- `.env.dev`, `.env.test`, `.env.prod`
- `environments/` directory structure

**Key environment variables:**
```bash
GENESIS_MODE=development
GENESIS_WORKSPACE_MAX_FILES=30
GENESIS_AI_SAFETY=enforced
GENESIS_LOG_LEVEL=info
PYTHON_VERSION=3.11
NODE_VERSION=20
```

### 0.3 Enhanced Ignore Files
**Files to update/create:**
- `.gitignore` (already exists - enhance)
- `.dockerignore` (new)
- `.npmignore` (new)
- `.gcloudignore` (new)

**Additional patterns needed:**
```gitignore
# Environment files
.env
.env.local
.env.*.local
!.env.example

# Direnv
.envrc.local

# Coverage reports
coverage/
htmlcov/
.coverage

# Dependencies
venv/
.venv/
node_modules/
vendor/

# Build artifacts
dist/
build/
*.egg-info/
```

### 0.4 Dependency Management
**Files to create:**
- `pyproject.toml` (root level for Genesis itself)
- `poetry.lock`
- `package.json` (root level)
- `package-lock.json`
- `go.mod`
- `requirements/` directory:
  - `requirements/base.txt`
  - `requirements/dev.txt`
  - `requirements/test.txt`

### 0.5 Build Automation (Makefile)
**File to create:** `Makefile` (root level)

**Essential targets:**
```makefile
.PHONY: setup test lint build clean help

setup:  ## Install all dependencies
	@echo "Setting up Genesis development environment..."
	poetry install
	npm install
	pre-commit install

test:  ## Run all tests
	pytest tests/ --cov=.
	npm test

lint:  ## Run all linters
	ruff check .
	black --check .
	mypy .

worktree-create:  ## Create AI-safe sparse worktree
	./worktree-tools/create-sparse-worktree.sh $(name) $(path)

file-check:  ## Verify AI safety file limits
	@find . -type f | wc -l
```

## Phase 1: Directory Structure Implementation

### 1.1 Create Component Directories
**Structure to implement:**
```
genesis/
├── docs/                     # Keep existing docs
├── genesis-cli/              # NEW: CLI component
├── smart-commit/             # MOVE from shared-infra/
├── bootstrap/                # NEW: Bootstrap component
├── shared-python/            # NEW: Python libraries
├── shared-typescript/        # NEW: TypeScript libraries
├── worktree-tools/          # NEW: Worktree management
├── templates/                # ENHANCE existing
├── testing/                  # NEW: Test infrastructure
├── .github/                  # ENHANCE existing
└── .genesis/                 # NEW: Genesis metadata
```

### 1.2 Component README Files
Each component needs:
- `README.md` with purpose and usage
- `.gitignore` for component-specific ignores
- Dependency files (pyproject.toml or package.json)

## Phase 2: CI/CD Pipeline

### 2.1 GitHub Actions Workflows
**Files to create in `.github/workflows/`:**
- `test.yml` - Run tests on PR
- `lint.yml` - Code quality checks
- `security.yml` - Security scanning
- `release.yml` - Automated releases
- `file-safety.yml` - AI safety file count checks

**Critical check for AI safety:**
```yaml
- name: Check file count for AI safety
  run: |
    count=$(find . -type f | wc -l)
    if [ $count -gt 100 ]; then
      echo "❌ Too many files ($count) for AI safety"
      exit 1
    fi
```

## Phase 3: Component Extraction & Building

### 3.1 Extract from Old Code
**Components to extract (in order):**

1. **smart-commit.sh** (140 → 100 lines)
   - Location: `smart-commit/smart-commit.sh`
   - Remove: Complex features, keep core flow

2. **create-sparse-worktree.sh** (230 → 150 lines)
   - Location: `worktree-tools/create-sparse-worktree.sh`
   - Keep: AI safety checks, file limits

3. **Python utilities** (each <50 lines):
   - `shared-python/src/shared_core/retry.py`
   - `shared-python/src/shared_core/logger.py`
   - `shared-python/src/shared_core/config.py`
   - `shared-python/src/shared_core/health.py`

4. **Bootstrap logic** (505 → 150 lines)
   - Location: `bootstrap/bootstrap.sh`
   - Remove: GCP coupling, keep project init

### 3.2 Build New Components

1. **Genesis CLI** (`genesis-cli/`)
   ```python
   # Commands to implement:
   - genesis bootstrap <name>     # Create project
   - genesis worktree create      # Sparse worktree
   - genesis sync                 # Update shared
   - genesis status              # Health check
   ```

2. **Project Templates** (`templates/`)
   - `python-api/` - FastAPI template
   - `cli-tool/` - Click CLI template
   - `library/` - Python library template

3. **TypeScript Libraries** (`shared-typescript/`)
   - Mirror Python utilities in TypeScript

## Phase 4: Testing Infrastructure

### 4.1 Pytest Setup
**Files to create:**
- `pytest.ini` (root)
- `conftest.py` (root)
- `testing/fixtures/` directory

### 4.2 Test Coverage Requirements
- Minimum 80% coverage
- Integration tests for each component
- E2E test: Genesis bootstraps itself

## Phase 5: Validation & Cleanup

### 5.1 Self-Bootstrap Test
Genesis must be able to:
1. Run `genesis bootstrap test-project`
2. Create project with all Genesis patterns
3. Set up sparse worktrees correctly
4. Configure all quality gates

### 5.2 Cleanup
- Remove `old-bloated-code-read-only/`
- Archive extraction documentation
- Update all READMEs

## Critical Missing Elements (Found in Review)

### Security & Compliance
- **Secret scanning** in pre-commit (exists ✓)
- **SAST scanning** in CI/CD (needs adding)
- **Dependency scanning** (needs adding)
- **License compliance** checking

### Developer Experience
- **Shell completion** for Genesis CLI
- **VS Code workspace** settings
- **Documentation generation** (Sphinx/MkDocs)

### Monitoring & Observability
- **Structured logging** format
- **Health check endpoints**
- **Performance benchmarks**

### Multi-Language Support
We have Python focus but need:
- **Go module** structure (for future components)
- **Rust workspace** preparation (future)

## GitHub Issues Breakdown (Prioritized)

### Critical Path (Must Do First)
1. **Issue #1**: Create CLAUDE.md with context separation
2. **Issue #2**: Set up environment management (.envrc, .env files)
3. **Issue #3**: Configure all ignore files
4. **Issue #4**: Set up dependency management (Poetry, npm)
5. **Issue #5**: Create root Makefile with automation

### Structure & Organization
6. **Issue #6**: Implement directory structure per plan
7. **Issue #7**: Set up CI/CD with GitHub Actions
8. **Issue #8**: Configure testing infrastructure

### Component Work
9. **Issue #9**: Extract smart-commit system
10. **Issue #10**: Extract sparse worktree creator
11. **Issue #11**: Extract Python utilities
12. **Issue #12**: Extract bootstrap logic
13. **Issue #13**: Build Genesis CLI
14. **Issue #14**: Create project templates
15. **Issue #15**: Build TypeScript libraries

### Validation
16. **Issue #16**: Security scanning setup
17. **Issue #17**: Performance benchmarks
18. **Issue #18**: Self-bootstrap validation
19. **Issue #19**: Remove old code & cleanup

## Issue Details Template

### Phase 0: Foundation Issues

#### Issue #1: Create CLAUDE.md with context separation
```markdown
**Title:** Add CLAUDE.md to clarify building vs using Genesis
**Priority:** Critical
**Labels:** documentation, developer-experience

**Description:**
- Create CLAUDE.md that distinguishes between building Genesis vs using Genesis
- Include context detection rules
- Add NOW vs FUTURE comparison tables
- Establish anti-confusion patterns

**Acceptance Criteria:**
- [ ] Clear separation of concerns documented
- [ ] Self-detection rules for AI context
- [ ] Examples of building vs using Genesis
- [ ] Visual markers for context mode
```

#### Issue #2: Set up environment management
```markdown
**Title:** Implement environment management for Genesis development
**Priority:** Critical
**Labels:** infrastructure, setup

**Description:**
- Create .envrc for direnv integration
- Set up .env.example with all needed variables
- Configure multiple environments (dev, test, prod)
- Add environment validation script

**Files to create:**
- .envrc
- .env.example
- .env.dev
- .env.test
- environments/

**Acceptance Criteria:**
- [ ] direnv working with .envrc
- [ ] Environment variables documented
- [ ] Multiple environment configs ready
- [ ] Validation script functional
```

#### Issue #3: Configure comprehensive ignore files
```markdown
**Title:** Set up all ignore files (.gitignore, .dockerignore, etc.)
**Priority:** Critical
**Labels:** infrastructure, security

**Description:**
- Update .gitignore with comprehensive patterns
- Add .dockerignore for container builds
- Create .npmignore for package publishing
- Add .gcloudignore for GCP deployments

**Acceptance Criteria:**
- [ ] No secrets can be accidentally committed
- [ ] Build artifacts excluded
- [ ] IDE files ignored
- [ ] OS-specific files excluded
- [ ] Environment files protected
```

#### Issue #4: Set up dependency management
```markdown
**Title:** Configure dependency management for multi-language project
**Priority:** Critical
**Labels:** infrastructure, setup

**Description:**
- Set up Poetry for Python dependencies
- Configure package.json for Node/TypeScript
- Add go.mod for Go components
- Create requirements/ directory structure
- Add dependency security scanning

**Files needed:**
- pyproject.toml
- poetry.lock
- package.json
- go.mod
- requirements/dev.txt
- requirements/prod.txt

**Acceptance Criteria:**
- [ ] All languages have dependency management
- [ ] Lock files created
- [ ] Security scanning configured
- [ ] Version constraints documented
```

#### Issue #5: Create Makefile for automation
```markdown
**Title:** Add build automation with Makefile
**Priority:** High
**Labels:** automation, developer-experience

**Description:**
- Create Makefile with standard targets
- Add targets: setup, test, lint, build, clean
- Include multi-language support
- Add help documentation
- Include worktree creation helpers

**Acceptance Criteria:**
- [ ] make setup installs all dependencies
- [ ] make test runs all test suites
- [ ] make lint runs all linters
- [ ] make help shows available commands
- [ ] make worktree-create works
```

### Phase 1: Structure Issues

#### Issue #6: Implement component-based directory structure
```markdown
**Title:** Reorganize repository into component-based structure
**Priority:** High
**Labels:** architecture, refactoring

**Description:**
- Create component directories per DIRECTORY_STRUCTURE_PLAN.md
- Move existing files to appropriate locations
- Set up component boundaries
- Ensure sparse-checkout compatibility

**Components to create:**
- genesis-cli/
- smart-commit/
- bootstrap/
- shared-python/
- shared-typescript/
- worktree-tools/
- templates/
- testing/

**Acceptance Criteria:**
- [ ] All components have own directory
- [ ] Each component < 30 files
- [ ] Dependencies documented
- [ ] Sparse checkout instructions work
```

## Success Metrics
- [ ] Total lines < 5,000 (from 250,000+)
- [ ] Each worktree < 30 files
- [ ] 80%+ test coverage
- [ ] Genesis can bootstrap itself
- [ ] All manual steps are automated
- [ ] File count validation automated
- [ ] Security scanning passing
- [ ] Documentation complete

## What Makes This Plan Complete

This plan ensures Genesis:
1. **Demonstrates what it automates** - Every manual setup step becomes automated
2. **Enforces AI safety** - File limits, sparse worktrees, safety checks
3. **Maintains simplicity** - <5,000 lines total
4. **Enables isolation** - Component-based, sparse-checkout ready
5. **Provides reusability** - Shared libraries for all projects
6. **Ensures quality** - Testing, linting, security built-in
7. **Supports growth** - Multi-language, extensible structure

## Execution Order

1. **Week 1**: Phase 0 (Foundation) - Issues #1-5
2. **Week 2**: Phase 1 (Structure) - Issues #6-8
3. **Week 3**: Phase 3 (Extraction) - Issues #9-12
4. **Week 4**: Phase 3 (Building) - Issues #13-15
5. **Week 5**: Phase 4-5 (Testing & Validation) - Issues #16-19

This plan is the complete blueprint for transforming Genesis from a 250,000+ line monolith into a lean, focused, 5,000 line toolkit that demonstrates and enforces best practices for AI-safe development.
