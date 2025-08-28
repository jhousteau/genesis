# Genesis Migration Guide

## Pre-Reorganization State (v1.0)

**Tagged Commit:** `pre-reorganization-v1` (801ae93)
**Branch:** `main`
**Date:** August 28, 2025

This document tracks the major reorganization from Genesis v1.0 to v2.0.

## Current Architecture (v1.0)

### Directory Structure
```
genesis/
├── genesis-cli/          # CLI tool package
├── shared-python/        # Core utilities package
├── bootstrap/            # Bootstrap functionality
├── smart-commit/         # Smart commit tool
├── worktree-tools/       # Worktree utilities
├── testing/              # Testing infrastructure
├── templates/            # Project templates
├── .github/workflows/    # CI/CD
└── old-bloated-code-read-only/  # Legacy code to extract from
```

### Current Packages
- **genesis-cli**: CLI entry point with basic commands
- **shared-python**: Core utilities (config, health, logger, retry)
- **bootstrap**: Project bootstrapping functionality
- Multiple disconnected components

### Current Features
- ✅ Basic CLI with 4 commands (bootstrap, commit, sync, worktree)
- ✅ Shared utilities (config, health, logger, retry)
- ✅ Testing infrastructure with pytest
- ✅ Project templates (CLI, Python API, TypeScript service)
- ✅ Smart commit functionality
- ✅ Worktree tools for AI-safe development
- ✅ CI/CD with GitHub Actions

### Current Limitations
- Multiple disconnected packages (not a proper Python package)
- Missing error framework and context management
- Basic retry without circuit breaker pattern
- No secrets management
- Missing sophisticated autofix system
- No Terraform modules for infrastructure
- Limited observability and resilience patterns

## Planned Changes (v2.0)

### New Architecture
```
genesis/
├── genesis/              # Unified Python package
│   ├── cli.py           # CLI entry point
│   ├── commands/        # All CLI commands
│   ├── core/            # Core utilities + new features
│   │   ├── config.py    # Existing
│   │   ├── health.py    # Existing
│   │   ├── logger.py    # Existing
│   │   ├── retry.py     # Enhanced with circuit breaker
│   │   ├── errors/      # NEW: Structured error handling
│   │   ├── context/     # NEW: Context management
│   │   ├── autofix/     # NEW: Multi-stage autofix system
│   │   └── secrets.py   # NEW: Basic secrets management
│   └── testing/         # Testing utilities
├── terraform/           # NEW: Infrastructure modules
│   ├── bootstrap/       # Project setup
│   ├── compute/         # GKE, Cloud Run
│   ├── networking/      # VPC, security
│   └── ... (10 modules total)
├── templates/           # Enhanced project templates
└── smart-commit/        # Enhanced with autofix
```

### Major Changes

#### 1. Unified Python Package Structure
- **Before**: Multiple packages (genesis-cli, shared-python, bootstrap)
- **After**: Single `genesis` package with proper structure
- **Impact**: `pip install -e .` installs everything
- **Breaking**: All import paths change

#### 2. Enhanced Error Framework
- **NEW**: 14 error categories (INFRASTRUCTURE, NETWORK, etc.)
- **NEW**: Correlation ID tracking
- **NEW**: Context preservation in errors
- **NEW**: Automatic error enrichment

#### 3. Circuit Breaker Resilience
- **Enhanced**: Retry module gets circuit breaker pattern
- **NEW**: Three states (CLOSED, OPEN, HALF_OPEN)
- **NEW**: Prevents cascading failures
- **NEW**: Thread-safe implementation

#### 4. Multi-Stage Autofix System
- **NEW**: Stage 1: Formatters (Black, Prettier)
- **NEW**: Stage 2: Linters (Ruff, ESLint)
- **NEW**: Stage 3: Convergent fixing
- **Enhanced**: Integration with smart-commit

#### 5. Infrastructure as Code
- **NEW**: 10 Terraform modules (~17,664 lines)
- **NEW**: bootstrap, compute, networking, data, security, etc.
- **NEW**: Complete GCP infrastructure patterns

#### 6. Context Management
- **NEW**: Thread-safe context storage
- **NEW**: Request tracking with correlation IDs
- **NEW**: Distributed tracing support

#### 7. Basic Secrets Management
- **NEW**: Environment variable validation
- **NEW**: Secret detection and sanitization
- **NEW**: Secure logging patterns

## Migration Path

### For Users

#### Import Changes
```python
# Before (v1.0)
from shared_core.config import Config
from shared_core.logger import get_logger

# After (v2.0)
from genesis.core.config import Config
from genesis.core.logger import get_logger
```

#### New Features Available
```python
# Error handling with context
from genesis.core.errors import handle_error, ErrorCategory

# Circuit breaker resilience
from genesis.core.retry import CircuitBreaker

# Autofix integration
from genesis.core.autofix import AutoFixer

# Secrets management
from genesis.core.secrets import secrets_manager
```

### For Developers

#### Testing Changes
- All test imports need updating for new package structure
- New tests for error framework, circuit breaker, autofix
- Integration tests for complete workflows

#### CI/CD Changes
- GitHub Actions paths updated
- Makefile targets updated
- New Terraform validation

## Rollback Strategy

If issues arise, rollback to pre-reorganization state:

```bash
# Return to safe state
git checkout main
git reset --hard pre-reorganization-v1

# Or cherry-pick specific commits
git checkout pre-reorganization-v1
git cherry-pick <specific-commits>
```

## Implementation Timeline

1. **Issue #71**: ✅ Preserve current state (COMPLETED)
2. **Issue #72**: Create unified package structure
3. **Issue #73**: Add error framework and context management
4. **Issue #74**: Enhance retry with circuit breaker
5. **Issue #75**: Add basic secrets manager
6. **Issue #76**: Implement multi-stage autofix system
7. **Issue #77**: Add selected Terraform modules
8. **Issue #78**: Update testing infrastructure
9. **Issue #79**: Update CI/CD and documentation
10. **Issue #80**: AI safety validation

**Estimated Timeline:** 3 weeks
**Breaking Changes:** Yes (import paths, package structure)
**Benefits:** Proper Python package, enhanced resilience, infrastructure automation, autofix system

## Success Metrics

- ✅ Single installable Python package
- ✅ All tests passing with new structure
- ✅ Autofix convergence working
- ✅ Circuit breaker preventing cascading failures
- ✅ Error context propagation working
- ✅ Terraform modules deployable
- ✅ AI safety limits maintained (<30 files per component)
- ✅ Genesis can bootstrap itself

---

**Status:** IN PROGRESS
**Current Phase:** Package reorganization
**Next:** Issue #72 - Create Unified Python Package Structure
