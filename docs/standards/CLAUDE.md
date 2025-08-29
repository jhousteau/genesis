# Genesis Code Standards & Quality

This directory contains Genesis coding standards, quality requirements, and development practices.

## Code Quality Standards

### Python Standards
- **Style**: Follow PEP 8, enforced by flake8 and black
- **Type Hints**: Required for all public function signatures and class attributes
- **Docstrings**: Required for all public functions, classes, and modules
- **Line Length**: 88 characters (Black formatter standard)
- **Import Organization**: isort with profile="black"

### Security Standards
- **No Hardcoded Secrets**: All credentials and sensitive values via environment variables
- **Fail-Fast Configuration**: Raise ValueError with clear messages for missing config
- **Input Validation**: Validate all external inputs (user input, file paths, template variables)
- **Path Security**: Check for path traversal attacks (../ sequences)
- **Dependency Security**: Regular updates and security scanning with bandit

### Configuration Standards
```python
# ✅ REQUIRED - Fail-fast configuration pattern
def get_required_env(var_name: str) -> str:
    """Get required environment variable with clear error message."""
    value = os.environ.get(var_name)
    if not value:
        raise ValueError(f"{var_name} environment variable is required but not set")
    return value

# ❌ FORBIDDEN - Silent fallbacks hide configuration issues
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///default.db")
```

## Testing Standards

### Test Coverage
- **Minimum Coverage**: 80% for all new code and modified functions
- **Unit Tests**: Test business logic in isolation with mocked dependencies
- **Integration Tests**: Test end-to-end workflows (bootstrap, smart-commit)
- **Template Tests**: Validate all template deployments create working projects

### Test Structure
```python
# ✅ REQUIRED - Clear Arrange/Act/Assert structure
def test_bootstrap_creates_valid_project():
    # Arrange
    project_name = "test-project"
    temp_dir = Path(tempfile.mkdtemp())

    # Act
    result = bootstrap_project(project_name, temp_dir, "python-api")

    # Assert
    assert result.success
    assert (temp_dir / project_name / "pyproject.toml").exists()
    assert (temp_dir / project_name / "CHANGELOG.md").exists()
```

## Development Workflow

### Pre-commit Requirements
All code must pass these automated checks:
- **Formatting**: black, isort for consistent code style
- **Linting**: flake8, pylint for code quality and PEP 8 compliance
- **Security**: bandit for Python security issues, gitleaks for secrets
- **Organization**: Custom scripts for file placement and hardcoded value detection
- **Tests**: pytest with coverage reporting

### Code Review Standards
- **Single Responsibility**: Each PR addresses one concern or feature
- **Test Coverage**: New functionality includes appropriate tests
- **Documentation**: Public APIs and complex logic documented
- **Security Review**: Changes reviewed for security implications and fail-fast patterns
- **Template Updates**: Changes to core patterns reflected in all relevant templates

## Genesis-Specific Standards

### Component Design
- **File Count Limit**: Each component <30 files for AI safety
- **Clear Boundaries**: Components should have minimal dependencies on each other
- **Context Documentation**: Every component directory has CLAUDE.md with specialized context
- **Template Consistency**: All templates follow identical patterns and quality standards

### CLI Design Standards
```python
# ✅ REQUIRED - Consistent CLI patterns
@click.command()
@click.argument('name', required=True)
@click.option('--type', type=click.Choice(['python-api', 'cli-tool']), required=True)
@click.option('--path', type=click.Path(), help='Directory to create project in')
def bootstrap(name: str, type: str, path: Optional[str]) -> None:
    """Create new project with Genesis patterns and tooling."""
    # Implementation with proper error handling
```

### Template Standards
- **Variable Substitution**: Use {{variable_name}} syntax consistently
- **File Organization**: Follow standard project structure in all templates
- **Quality Gates**: All templates include pre-commit hooks and security scanning
- **Documentation**: Include CLAUDE.md context and hierarchical docs structure

## Versioning & Release Standards

### Semantic Versioning
Follow [semver.org](https://semver.org) strictly:
- **MAJOR**: Breaking changes to CLI interface or template structure (1.0.0 → 2.0.0)
- **MINOR**: New features, additional templates, non-breaking enhancements (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, security updates, documentation improvements (1.0.0 → 1.0.1)

### Conventional Commits
Use standardized commit messages for automation:
```bash
feat: add TypeScript service template
fix: resolve template variable substitution bug
docs: update architecture documentation
chore: bump dependency versions for security
BREAKING CHANGE: modify CLI argument structure
```

### Release Process
1. **Development**: Feature branches with conventional commits
2. **Quality Gates**: All commits pass smart-commit validation
3. **Documentation**: CHANGELOG.md automatically updated from commits
4. **Version Bumps**: Automatic semantic version updates in smart-commit
5. **Release**: GitHub Actions creates releases from tags

## Error Handling Standards

### User-Facing Errors
```python
# ✅ REQUIRED - Clear, actionable error messages
if not project_path.parent.exists():
    raise ValueError(f"Parent directory does not exist: {project_path.parent}")

# ❌ FORBIDDEN - Vague or technical error messages
if not project_path.parent.exists():
    raise Exception("Invalid path")
```

### Internal Error Handling
- **Specific Exceptions**: Use specific exception types, not generic Exception
- **Error Context**: Include relevant context (file paths, user inputs) in error messages
- **Graceful Degradation**: Where possible, provide fallbacks with clear warnings
- **Logging**: Use structured logging for debugging without exposing internals to users

## Performance Standards

### CLI Response Times
- **Bootstrap command**: <30 seconds including dependency installation
- **Status/version commands**: <1 second
- **Template processing**: <5 seconds for standard templates
- **Smart-commit workflow**: <2 minutes for typical changesets

### Resource Usage
- **Memory**: <100MB peak usage during normal operations
- **Disk I/O**: Minimize unnecessary file operations, use efficient file copying
- **Network**: Only fetch dependencies when required, cache where appropriate

---

**Context for AI Assistants**: Enforce these standards in all Genesis development. Reject code that violates security, quality, or performance requirements. Suggest improvements when code doesn't meet these standards. Maintain consistency across all Genesis components and templates.
