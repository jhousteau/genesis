# Genesis Safety Guidelines

AI safety and sparse worktree rules to prevent contamination and security issues.

## Core Safety Rules

### Rule #1: AI Never Sees Main Repository
```bash
# ❌ NEVER: Give AI access to main repo
cd /Users/jameshousteau/source_code/genesis
# AI sees 3000+ files → disaster waiting to happen

# ✅ ALWAYS: Use sparse worktree
cd /Users/jameshousteau/source_code/genesis-cli
# AI sees 21 files → safe, focused work
```

### Rule #2: 5-30 Files Per Worktree
```bash
# Check file count before AI work
find . -type f | wc -l

# If > 30 files, narrow the sparse-checkout
git sparse-checkout set specific/component/only/
```

### Rule #3: Review Before Merge
- **All AI changes** must be human-reviewed
- **Show git diff** before accepting changes
- **Test thoroughly** in sparse environment
- **Never auto-merge** AI pull requests

## Sparse Worktree Setup

### Basic Setup
```bash
# Create focused worktree
git worktree add --no-checkout ../genesis-component feature/work
cd ../genesis-component
git sparse-checkout init --cone
git sparse-checkout set path/to/component/
git checkout

# Verify file count
find . -type f | wc -l  # Should be < 30
```

### Common Patterns
```bash
# CLI work (21 files)
git sparse-checkout set genesis_cli/ pyproject.toml

# Smart commit work (35 files)
git sparse-checkout set shared-infra/smart-commit/

# Bootstrap work (16 files)
git sparse-checkout set shared-infra/bootstrap/

# Ultra-sparse for specific fixes (5-10 files)
git sparse-checkout set genesis_cli/commands/status.py tests/unit/test_status.py
```

### Worktree Management
```bash
# List active worktrees
git worktree list

# Remove finished worktree
git worktree remove ../genesis-component

# Clean up stale worktrees
git worktree prune
```

## AI Safety Protocols

### Before AI Session
1. **Create sparse worktree** for the task
2. **Verify file count** is reasonable (<30)
3. **Review files** AI will see
4. **Define clear scope** for AI work
5. **Set time boundaries** for session

### During AI Session
1. **Monitor file access** - AI should stay in scope
2. **Watch for red flags** - accessing config files, secrets
3. **Check intermediate results** - git diff frequently
4. **Stop if confused** - unclear requests = danger
5. **Ask for clarification** when scope seems broad

### After AI Session
1. **Review all changes** with git diff
2. **Test modified code** thoroughly
3. **Check for side effects** in other components
4. **Verify no secrets exposed** in commits
5. **Clean up temporary files**

### AI Communication Protocol
```bash
# Good AI request
"In the genesis-cli sparse worktree, add a status command to genesis_cli/commands/status.py that shows project health"

# Bad AI request
"Improve the entire Genesis project and fix any issues you find"
```

## Git Workflow

### Branch Strategy
```bash
# Feature branches from sparse worktrees
../genesis-component/  # feature/new-component
../genesis-fix/        # fix/specific-bug
../genesis-refactor/   # refactor/cleanup-logging
```

### Commit Standards
```bash
# Use conventional commits
feat: add status command to CLI
fix: resolve import error in shared_core
docs: update README with new examples
test: add integration tests for bootstrap

# Include component context
feat(cli): add health check command
fix(smart-commit): handle missing git config
```

### Merge Process
```bash
# 1. Review in sparse worktree
cd ../genesis-component
git diff --staged
git status

# 2. Test changes
pytest tests/ -v

# 3. Merge to main
cd ../genesis
git merge feature/new-component

# 4. Clean up
git worktree remove ../genesis-component
git branch -d feature/new-component
```

## Security Guidelines

### Secret Management
```bash
# ✅ Environment variables
export API_KEY="secret-value"
config = {"api_key": os.getenv("API_KEY")}

# ❌ Hardcoded secrets
config = {"api_key": "sk-123456"}  # Never commit this
```

### File Access Restrictions
```bash
# Files AI should NEVER access
.env*                    # Environment secrets
*.key, *.pem            # Private keys
credentials.json        # Service account keys
config/production.yaml  # Production configs
```

### Validation Checklist
Before merging AI changes:
- [ ] No secrets in git diff
- [ ] No unexpected file modifications
- [ ] Tests pass
- [ ] Code follows project conventions
- [ ] Changes match requested scope
- [ ] No TODO/FIXME comments added
- [ ] Documentation updated if needed

## Common Failure Patterns

### Over-Broad Sparse Checkout
```bash
# ❌ Too broad - AI sees everything
git sparse-checkout set .

# ✅ Focused - AI sees only what's needed
git sparse-checkout set genesis_cli/commands/status.py tests/unit/test_status.py
```

### Cross-Component Modifications
```bash
# ❌ AI modifies unrelated files
modified: genesis_cli/cli.py           # Expected
modified: shared-infra/bootstrap.py    # Unexpected!
modified: tests/integration/test_api.py # Red flag!

# ✅ AI stays in scope
modified: genesis_cli/commands/status.py   # Expected
modified: tests/unit/test_status.py        # Expected
```

### Secret Leakage
```bash
# ❌ AI accidentally logs secrets
print(f"Connecting with API key: {api_key}")

# ✅ AI uses safe logging
logger.info("Connecting to API", endpoint=endpoint)
```

## Recovery Procedures

### If AI Goes Rogue
```bash
# 1. Stop AI session immediately
# 2. Check what was modified
git status
git diff

# 3. Revert dangerous changes
git checkout -- path/to/problematic/file

# 4. Create new sparse worktree with tighter constraints
git worktree remove ../current-workspace
git worktree add --no-checkout ../safer-workspace feature/branch
cd ../safer-workspace
git sparse-checkout set very/specific/files/only
```

### If Secrets Exposed
```bash
# 1. Remove from git history
git filter-branch --tree-filter 'rm -f path/to/secret/file' HEAD

# 2. Force push (if safe)
git push --force-with-lease

# 3. Rotate compromised secrets
# 4. Review all AI session logs
```

## Best Practices

### Workspace Naming
```bash
# Include purpose in name
../genesis-cli-status/      # Adding status command
../genesis-fix-logging/     # Fix logging issue
../genesis-test-bootstrap/  # Add bootstrap tests
```

### Session Documentation
```markdown
# AI Session Log
- **Date**: 2024-01-15
- **Purpose**: Add status command to CLI
- **Files**: genesis_cli/commands/status.py, tests/unit/test_status.py
- **Changes**: 45 lines added, 0 deleted
- **Review**: All changes appropriate, tests pass
```

### Workspace Cleanup
```bash
# Daily cleanup routine
git worktree prune              # Remove stale worktrees
git branch -d completed-branch  # Delete merged branches
rm -rf ../old-workspace-*      # Clean up directories
```

## Success Metrics

### Safety Indicators
- **Zero secrets** in git history
- **Zero cross-component** contamination
- **100% review rate** for AI changes
- **All workspaces** under 30 files
- **No failed merges** due to AI changes

### Efficiency Metrics
- **Faster AI responses** (smaller context)
- **Reduced review time** (focused changes)
- **Lower error rate** (isolated scope)
- **Quick workspace setup** (<30 seconds)

## Emergency Contacts

If something goes seriously wrong:
1. **Stop all AI sessions** immediately
2. **Document the issue** with git status/diff
3. **Revert to last known good state**
4. **Review sparse worktree setup**
5. **Update safety guidelines** based on lessons learned

Remember: **When in doubt, err on the side of caution**. It's better to be overly restrictive than to allow AI contamination of the codebase.
