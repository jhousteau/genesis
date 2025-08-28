# Genesis Extraction & Build Plan

## Overview
This document maps what valuable components to harvest from the old 250,000+ line codebase vs. what to build fresh.

## 1. HARVEST: High-Value Components to Extract

### ✅ Smart Commit System
**Source**: `old-bloated-code-read-only/genesis-old/smart-commit.sh` (168 lines)
**Why Keep**: Clean, focused implementation with good quality gates
**Modifications Needed**:
- Remove over-complex features
- Simplify to ~100 lines
- Focus on: format, lint, test, commit
**Target**: `shared-infra/smart-commit/smart-commit.sh`

### ✅ Sparse Worktree Creator
**Source**: `old-bloated-code-read-only/genesis-old/scripts/create-sparse-worktree.sh`
**Why Keep**: Already implements AI safety principles
**Modifications Needed**:
- Simplify file counting logic
- Remove over-engineering
- Keep core safety features
**Target**: `shared-infra/scripts/create-sparse-worktree.sh`

### ✅ Bootstrap Core Logic
**Source**: `old-bloated-code-read-only/genesis-old/scripts/bootstrap.sh` (400+ lines)
**Why Keep**: Good project initialization patterns
**Modifications Needed**:
- Extract only project setup logic
- Remove GCP-specific coupling
- Make cloud-agnostic
- Reduce to ~150 lines
**Target**: `shared-infra/bootstrap/bootstrap.sh`

### ✅ Retry Utility
**Source**: `old-bloated-code-read-only/genesis-old/core/retry/retry.py`
**Why Keep**: Well-designed retry logic with backoff
**Modifications Needed**:
- Simplify to essential retry decorator
- Remove complex policies
- Keep exponential backoff
**Target**: `shared-infra/libs/python/shared_core/retry.py`

### ✅ Logger Utility
**Source**: `old-bloated-code-read-only/genesis-old/core/logging/logger.py`
**Why Keep**: Structured logging with context
**Modifications Needed**:
- Simplify to basic structured logger
- Remove complex handlers
- Keep JSON output capability
**Target**: `shared-infra/libs/python/shared_core/logger.py`

### ✅ Config Management
**Source**: `old-bloated-code-read-only/genesis-old/core/config/`
**Why Keep**: Environment-aware configuration
**Modifications Needed**:
- Simplify to YAML + env vars
- Remove complex inheritance
- Keep override hierarchy
**Target**: `shared-infra/libs/python/shared_core/config.py`

### ✅ Health Check Framework
**Source**: `old-bloated-code-read-only/genesis-old/core/health/`
**Why Keep**: Good health check patterns
**Modifications Needed**:
- Extract basic health checker
- Remove complex monitoring
- Keep simple status checks
**Target**: `shared-infra/libs/python/shared_core/health.py`

## 2. BUILD NEW: Components to Create Fresh

### 🔨 Genesis CLI
**Why Build New**: Old CLIs are over-engineered with too many commands
**Requirements**:
- Click-based CLI
- 4 commands only: bootstrap, worktree, sync, status
- ~200 lines total
**Target**: `genesis_cli/`

### 🔨 Test Framework
**Why Build New**: Old tests are bloated with 50+ shell scripts
**Requirements**:
- pytest only
- Simple conftest.py
- unit/integration/e2e structure
- No shell scripts
**Target**: `tests/`

### 🔨 Pre-commit Configuration
**Why Build New**: Need modern, lean configuration
**Requirements**:
- Black, ruff, mypy for Python
- Basic security checks
- No complex validators
**Target**: `.pre-commit-config.yaml`

### 🔨 Project Templates
**Why Build New**: Old templates are too complex
**Requirements**:
- Simple Python API template
- Simple CLI template
- Basic library template
- Each <50 files
**Target**: `templates/`

### 🔨 TypeScript Libraries
**Why Build New**: Need parallel implementation of Python utils
**Requirements**:
- Mirror Python shared_core functionality
- Modern TypeScript patterns
- Type-safe interfaces
**Target**: `shared-infra/libs/typescript/`

## 3. IGNORE: Components to Leave Behind

### ❌ Deployment Strategies
- 6 deployment strategies (rolling, blue-green, canary, etc.)
- Complex orchestrators
- **Replace with**: Simple docker-compose or k8s manifest

### ❌ VM Management
- Complex VM orchestration
- Auto-scaling logic
- **Replace with**: Cloud Run or simple compute instance

### ❌ Security Theater
- 5+ security scanners
- Complex validation pipelines
- **Replace with**: Pre-commit hooks + basic scanning

### ❌ Intelligence Systems
- "Solve" system
- "Autofix" system
- Complex AI orchestration
- **Replace with**: Nothing - not needed

### ❌ Monitoring Stack
- Complex observability
- Custom dashboards
- **Replace with**: Basic logging + health checks

### ❌ Governance Framework
- Compliance automation
- Policy engines
- **Replace with**: Simple .gitignore + pre-commit

### ❌ Multiple Config Systems
- unified_config.py
- YAML validators
- Complex inheritance
- **Replace with**: Single config.py with env vars

## 4. Extraction Priority & Effort

### Phase 1: Core Utilities (2 hours)
1. Extract smart-commit.sh (30 min)
2. Extract sparse worktree creator (30 min)
3. Extract Python retry utility (20 min)
4. Extract Python logger (20 min)
5. Extract Python config (20 min)

### Phase 2: Bootstrap & CLI (2 hours)
1. Extract bootstrap core logic (45 min)
2. Build new Genesis CLI structure (45 min)
3. Create CLI commands (30 min)

### Phase 3: Testing & Templates (1 hour)
1. Setup pytest structure (20 min)
2. Create project templates (20 min)
3. Create pre-commit config (20 min)

### Phase 4: TypeScript Libraries (2 hours)
1. Port retry logic to TypeScript (30 min)
2. Port logger to TypeScript (30 min)
3. Port config to TypeScript (30 min)
4. Port health checks to TypeScript (30 min)

## 5. File Count Targets

### Current (Bloated)
- **250,000+ lines** across 3 projects
- **631 README files**
- **230 shell scripts**
- **191 YAML files**

### Target (Lean)
- **~5,000 lines** total
- **15-20 source files** in shared-infra
- **5-10 files** per worktree
- **4 template files**
- **10 test files**

## 6. Success Metrics

### Extraction Success
- [ ] Each extracted component <200 lines
- [ ] No dependencies on old code
- [ ] All components have tests
- [ ] Documentation in code, not separate files

### Build Success
- [ ] CLI works with 4 commands
- [ ] Templates create working projects
- [ ] Tests run with pytest only
- [ ] TypeScript mirrors Python functionality

### Overall Success
- [ ] Total codebase <5,000 lines
- [ ] AI can understand entire system in one session
- [ ] No duplicate functionality
- [ ] Everything has a single purpose

## 7. Anti-Patterns to Avoid During Extraction

### DON'T
- Copy entire files without reviewing
- Bring complex dependencies
- Keep "universal" or "adaptive" features
- Preserve multiple ways to do same thing
- Keep commented-out code
- Preserve TODO comments
- Keep complex error hierarchies

### DO
- Extract only the essential logic
- Simplify while extracting
- Remove all comments except critical ones
- Flatten complex hierarchies
- Use standard Python/TS patterns
- Keep functions under 20 lines
- Maintain single responsibility

## 8. Validation Checklist

Before considering extraction complete:

- [ ] Old bloated code directory deleted
- [ ] All extracted components tested
- [ ] File count under targets
- [ ] No shell scripts except smart-commit and bootstrap
- [ ] Documentation only in README.md, GENESIS.md, SAFETY.md
- [ ] All components follow single-responsibility
- [ ] Sparse worktrees work correctly
- [ ] Smart commit enforces quality
- [ ] Bootstrap creates minimal projects
- [ ] Tests pass with >80% coverage

## Summary

**Harvest**: 7 components (~1,500 lines extracted, simplified to ~800 lines)
**Build New**: 5 components (~1,200 lines)
**Ignore**: Everything else (248,000+ lines)

**Total New Codebase**: ~2,000 lines of high-value, focused code
