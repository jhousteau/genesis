# Genesis Directory Structure Plan - Optimized for Worktree Isolation

## Core Design Principle: "Eat Our Own Dog Food"

Genesis must demonstrate the sparse worktree isolation it promotes. Each component should be independently workable with minimal file exposure.

## Proposed Directory Structure

```
genesis/                           # Main repository (human oversight only)
│
├── docs/                          # Centralized documentation (3-5 files)
│   ├── README.md                  # Entry point
│   ├── GENESIS.md                 # Architecture
│   └── SAFETY.md                  # AI safety rules
│
├── genesis-cli/                   # Component 1: CLI (15-20 files)
│   ├── src/
│   │   ├── __init__.py
│   │   ├── cli.py                # Main entry point
│   │   └── commands/              # One file per command
│   │       ├── __init__.py
│   │       ├── bootstrap.py      # Bootstrap command
│   │       ├── worktree.py       # Worktree management
│   │       ├── sync.py           # Sync shared components
│   │       └── status.py         # Status checking
│   ├── tests/
│   │   ├── test_bootstrap.py
│   │   ├── test_worktree.py
│   │   └── test_cli.py
│   ├── pyproject.toml
│   └── README.md
│
├── smart-commit/                  # Component 2: Smart Commit (8-10 files)
│   ├── src/
│   │   ├── smart_commit.sh       # Main script
│   │   └── lib/
│   │       ├── validators.sh     # Validation functions
│   │       └── formatters.sh     # Formatting functions
│   ├── tests/
│   │   └── test_smart_commit.sh
│   ├── .smart-commit.yaml        # Configuration
│   └── README.md
│
├── bootstrap/                     # Component 3: Bootstrap (10-12 files)
│   ├── src/
│   │   ├── bootstrap.sh          # Main script
│   │   └── templates/            # Project templates
│   │       ├── python-api/
│   │       ├── typescript-api/
│   │       └── cli-tool/
│   ├── tests/
│   │   └── test_bootstrap.sh
│   └── README.md
│
├── shared-python/                 # Component 4: Python Libraries (15-20 files)
│   ├── src/
│   │   └── shared_core/
│   │       ├── __init__.py
│   │       ├── config.py         # Configuration management
│   │       ├── logger.py         # Structured logging
│   │       ├── retry.py          # Retry logic
│   │       ├── errors.py         # Error handling
│   │       ├── cache.py          # Caching utilities
│   │       └── health.py         # Health checks
│   ├── tests/
│   │   ├── test_config.py
│   │   ├── test_logger.py
│   │   ├── test_retry.py
│   │   └── test_health.py
│   ├── pyproject.toml
│   └── README.md
│
├── shared-typescript/             # Component 5: TypeScript Libraries (15-20 files)
│   ├── src/
│   │   ├── index.ts
│   │   ├── config.ts
│   │   ├── logger.ts
│   │   ├── retry.ts
│   │   ├── errors.ts
│   │   ├── cache.ts
│   │   └── health.ts
│   ├── tests/
│   │   ├── config.test.ts
│   │   ├── logger.test.ts
│   │   └── retry.test.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
│
├── worktree-tools/               # Component 6: Worktree Management (5-8 files)
│   ├── src/
│   │   ├── create-worktree.sh   # Create sparse worktree
│   │   ├── verify-isolation.sh  # Verify file limits
│   │   └── cleanup-worktree.sh  # Clean up stale worktrees
│   ├── tests/
│   │   └── test_worktree.sh
│   └── README.md
│
├── templates/                     # Component 7: Project Templates (static files)
│   ├── gitignore.template
│   ├── pre-commit.template
│   ├── pyproject.template
│   ├── package.template
│   ├── makefile.template
│   └── README.md
│
├── testing/                       # Component 8: Test Infrastructure (8-10 files)
│   ├── pytest.ini                # Pytest configuration
│   ├── conftest.py               # Shared fixtures
│   ├── fixtures/
│   │   ├── mock_git.py
│   │   ├── mock_filesystem.py
│   │   └── mock_commands.py
│   └── README.md
│
├── .github/                       # CI/CD (not for worktrees)
│   └── workflows/
│       ├── test.yml
│       └── release.yml
│
└── .genesis/                      # Genesis metadata (not for worktrees)
    ├── config.yaml                # Genesis configuration
    └── worktree-map.json          # Tracks active worktrees
```

## Sparse Worktree Strategy

### Component Isolation Patterns

Each component can be checked out independently with minimal dependencies:

#### 1. CLI Development Worktree
```bash
git worktree add --no-checkout ../genesis-cli-work feature/cli
cd ../genesis-cli-work
git sparse-checkout init --cone
git sparse-checkout set genesis-cli/ shared-python/src/shared_core/
# Result: ~25 files (CLI + needed libraries)
```

#### 2. Smart Commit Worktree
```bash
git worktree add --no-checkout ../genesis-smart-commit-work feature/smart-commit
cd ../genesis-smart-commit-work
git sparse-checkout init --cone
git sparse-checkout set smart-commit/
# Result: ~10 files (completely independent)
```

#### 3. Python Library Development
```bash
git worktree add --no-checkout ../genesis-python-work feature/python-libs
cd ../genesis-python-work
git sparse-checkout init --cone
git sparse-checkout set shared-python/ testing/
# Result: ~25 files (libraries + test infrastructure)
```

#### 4. Bootstrap Development
```bash
git worktree add --no-checkout ../genesis-bootstrap-work feature/bootstrap
cd ../genesis-bootstrap-work
git sparse-checkout init --cone
git sparse-checkout set bootstrap/ templates/
# Result: ~15 files (bootstrap + templates)
```

#### 5. Ultra-Sparse Bug Fix
```bash
git worktree add --no-checkout ../genesis-fix-logger fix/logger-bug
cd ../genesis-fix-logger
git sparse-checkout init --cone
git sparse-checkout set shared-python/src/shared_core/logger.py shared-python/tests/test_logger.py
# Result: 2 files only
```

## Component Boundaries & Dependencies

### Dependency Rules

1. **NO circular dependencies**
2. **Minimal cross-component dependencies**
3. **Clear dependency direction**

### Dependency Graph
```
docs/                → (no dependencies)
templates/           → (no dependencies)
worktree-tools/      → (no dependencies)
testing/             → (no dependencies)

shared-python/       → (no dependencies)
shared-typescript/   → (no dependencies)

smart-commit/        → (no dependencies - standalone)
bootstrap/           → templates/

genesis-cli/         → shared-python/
                     → worktree-tools/ (via subprocess)
                     → bootstrap/ (via subprocess)
                     → smart-commit/ (via subprocess)
```

### Component Characteristics

| Component | Files | Dependencies | Standalone? | AI-Safe Size? |
|-----------|-------|-------------|------------|---------------|
| docs/ | 3 | None | ✅ Yes | ✅ 3 files |
| genesis-cli/ | 15-20 | shared-python | ⚠️ Partial | ✅ <30 files |
| smart-commit/ | 8-10 | None | ✅ Yes | ✅ <10 files |
| bootstrap/ | 10-12 | templates | ✅ Yes | ✅ <15 files |
| shared-python/ | 15-20 | None | ✅ Yes | ✅ <20 files |
| shared-typescript/ | 15-20 | None | ✅ Yes | ✅ <20 files |
| worktree-tools/ | 5-8 | None | ✅ Yes | ✅ <10 files |
| templates/ | 5-6 | None | ✅ Yes | ✅ <10 files |
| testing/ | 8-10 | None | ✅ Yes | ✅ <10 files |

## File Count Analysis

### Per-Component File Counts
- **docs/**: 3 files
- **genesis-cli/**: 15-20 files  
- **smart-commit/**: 8-10 files
- **bootstrap/**: 10-12 files
- **shared-python/**: 15-20 files
- **shared-typescript/**: 15-20 files
- **worktree-tools/**: 5-8 files
- **templates/**: 5-6 files
- **testing/**: 8-10 files
- **.github/**: 2-3 files
- **.genesis/**: 2 files

**Total Repository**: ~100-120 files

### Worktree File Exposure
- **Minimum**: 2 files (ultra-sparse fix)
- **Typical**: 10-25 files (component work)
- **Maximum**: 30 files (cross-component work)
- **Never**: >50 files (violates AI safety)

## Implementation Benefits

### 1. True Component Isolation
- Each component is physically separated
- Can't accidentally modify other components
- Clear ownership boundaries

### 2. AI Safety by Design
- Maximum 30 files per worktree
- Most worktrees are 10-20 files
- Ultra-sparse mode for specific fixes

### 3. Parallel Development
- Multiple developers can work on different components
- No merge conflicts between components
- Independent testing and releases

### 4. Progressive Enhancement
- Start with one component
- Add components as needed
- Each component is optional

## Migration Path from Current Structure

### Current Issues
- Everything mixed in single directory
- No clear component boundaries
- Hard to create focused worktrees

### Migration Steps

1. **Phase 1: Create Component Directories**
   - Move CLI files → genesis-cli/
   - Move smart-commit → smart-commit/
   - Move bootstrap → bootstrap/
   
2. **Phase 2: Establish Boundaries**
   - Add component-specific README files
   - Create component-specific tests
   - Remove cross-component imports

3. **Phase 3: Validate Isolation**
   - Create worktree for each component
   - Verify file counts
   - Test independent operation

## Success Criteria

### Component Independence
- [ ] Each component has own README
- [ ] Each component has own tests
- [ ] Each component can be developed independently
- [ ] No circular dependencies

### Worktree Safety
- [ ] All worktrees <30 files
- [ ] Most worktrees <20 files
- [ ] Ultra-sparse mode works (2-5 files)
- [ ] File count verification automated

### Developer Experience
- [ ] Can create worktree in <30 seconds
- [ ] Clear which files belong to which component
- [ ] Easy to understand component boundaries
- [ ] Simple to add new components

## Anti-Patterns to Avoid

### ❌ DON'T: Mix Components
```
# Bad - mixed concerns
src/
├── cli.py
├── smart_commit.sh
├── logger.py
└── bootstrap.sh
```

### ❌ DON'T: Deep Nesting
```
# Bad - too deep
shared/
└── infrastructure/
    └── libraries/
        └── python/
            └── core/
                └── utilities/
                    └── logger.py
```

### ❌ DON'T: Unclear Boundaries
```
# Bad - what belongs where?
utils/
common/
shared/
lib/
```

### ✅ DO: Clear, Flat Components
```
# Good - clear ownership
genesis-cli/
smart-commit/
shared-python/
```

## Conclusion

This directory structure embodies the Genesis philosophy:
- **Radical simplicity**: Clear, flat structure
- **Component isolation**: Each piece stands alone
- **AI safety**: Enforced file limits
- **Dog-fooding**: We use what we preach

By organizing Genesis this way, we demonstrate that sparse worktree development is not just possible but preferable for maintaining clean, focused, and safe development practices.