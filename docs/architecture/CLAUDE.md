# Genesis Architecture Context

This directory contains Genesis system architecture, design patterns, and technical constraints.

## System Architecture

### Technology Stack
- **Core Language**: Python 3.11+ with Poetry for dependency management
- **CLI Framework**: Click for command-line interface
- **Template Engine**: Jinja2 for variable substitution in templates
- **Quality Gates**: Pre-commit hooks with flake8, bandit, gitleaks
- **Testing**: Pytest with coverage requirements
- **Documentation**: Markdown with specialized CLAUDE.md context files

### Component Architecture
Genesis is organized into focused components:
- **genesis/**: Core CLI and business logic
- **smart-commit/**: Quality gates and commit automation
- **templates/**: Project templates (python-api, typescript-service, etc.)
- **shared-python/**: Reusable utilities (retry, logger, config, health)
- **worktree-tools/**: AI-safe sparse worktree creation
- **scripts/**: Development and maintenance utilities

### Service Boundaries
What Genesis owns vs external dependencies:
- **Owns**: Project creation, quality enforcement, template processing, sparse worktrees
- **External**: Git operations, package managers (Poetry, npm), CI/CD platforms, security scanners

## Design Patterns & Principles

### Required Patterns
- **Component Isolation**: Each component <30 files for AI safety
- **Fail-Fast Configuration**: Environment variables with clear error messages
- **Template-Driven**: All project structure via configurable templates
- **Quality Gates**: Automated enforcement of security and code standards
- **Hierarchical Context**: Specialized documentation for AI assistants

### Forbidden Patterns
- **Hardcoded Values**: No embedded paths, URLs, or configuration
- **Silent Failures**: Always fail fast with actionable error messages
- **Tight Coupling**: Components should work independently
- **Manual Setup**: Everything must be automated via bootstrap

## Template System Design

### Template Structure
```
templates/project-type/
├── template.json           # File mapping and substitution rules
├── files.template          # Template files with {{variables}}
└── .claude/               # AI context and automation
    ├── settings.json      # Claude Code hooks configuration
    └── hooks/             # Documentation update automation
```

### Template Processing
1. **Variable Collection**: Gather project name, description, author info
2. **File Processing**: Copy and substitute variables in template files
3. **Directory Creation**: Create standard project structure
4. **Git Initialization**: Initialize repo with initial commit
5. **Environment Setup**: Install dependencies and configure tools

## Quality Gate Architecture

### Pre-Commit Hook Chain
```bash
1. Code Formatting (black, isort)
2. Linting (flake8, pylint)
3. Security Scanning (bandit)
4. Secret Detection (gitleaks)
5. File Organization (custom script)
6. Hardcoded Value Detection (custom script)
```

### Smart-Commit Workflow
```bash
1. AutoFixer (convergent code repair)
2. Pre-commit validation
3. Test execution (with continue option)
4. Documentation updates (CHANGELOG.md, version bumps)
5. Atomic commit (code + docs + metadata)
```

## AI Safety Architecture

### File Count Limits
- **Genesis Total**: <5,000 lines across all components
- **Individual Components**: <30 files each for AI context windows
- **Template Deployments**: <30 files per worktree for AI safety

### Context Management
- **Root CLAUDE.md**: Global constraints and principles
- **Component CLAUDE.md**: Specialized context per directory
- **Dynamic Loading**: Context loaded based on working directory
- **Hierarchical Organization**: Prevents information overload

## Security Architecture

### Configuration Security
- **No Hardcoded Secrets**: All sensitive values via environment variables
- **Fail-Fast Validation**: Missing configuration causes immediate failure
- **Template Security**: Generated projects inherit security patterns
- **Scan Integration**: Bandit and Gitleaks in all workflows

### Development Security
- **Secret Detection**: Pre-commit and smart-commit scan for leaked credentials
- **Dependency Scanning**: Poetry audit for known vulnerabilities
- **File Organization**: Enforce secure file placement patterns

## Performance Requirements

### Bootstrap Performance
- Project creation: <30 seconds including dependency installation
- Template processing: <5 seconds for file generation
- Git operations: <10 seconds for initialization and initial commit

### Development Workflow Performance
- Smart-commit: <2 minutes including all quality gates
- Pre-commit hooks: <30 seconds for validation
- Documentation updates: <5 seconds for changelog/version updates

## Development Constraints

### Code Organization
```
genesis/
├── cli.py              # Main CLI entry point
├── commands/           # CLI command implementations
├── core/               # Shared business logic
└── testing/            # Test utilities and fixtures
```

### Quality Requirements
- **Test Coverage**: 80%+ for all new code
- **Type Hints**: Required for all public functions
- **Documentation**: CLAUDE.md context for all major directories
- **Security**: Pass all automated security scans

---

**Context for AI Assistants**: Follow these architectural patterns when modifying Genesis. Maintain component isolation, enforce security patterns, and preserve AI safety constraints. When adding features, ensure they integrate with existing quality gates and template systems.
