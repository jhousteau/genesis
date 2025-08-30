# test-project Code Standards & Quality

This directory contains coding standards, quality requirements, and development practices.

## Code Quality Standards

### Python Standards
- **Style**: Follow PEP 8, enforced by flake8
- **Type Hints**: Required for all function signatures
- **Docstrings**: Required for all public functions and classes
- **Line Length**: 88 characters (Black formatter standard)

### Security Standards
- **No Hardcoded Secrets**: All credentials via environment variables
- **Input Validation**: Validate all external inputs with Pydantic
- **Error Handling**: Never expose internal details in error responses
- **Dependency Security**: Regular security scanning with Bandit

### Configuration Standards
```python
# ✅ REQUIRED - Fail-fast configuration
def get_required_env(var_name: str) -> str:
    value = os.environ.get(var_name)
    if not value:
        raise ValueError(f"{var_name} environment variable is required")
    return value

# ❌ FORBIDDEN - Silent fallbacks
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/app")
```

## Testing Standards

### Test Coverage
- **Minimum Coverage**: 80% for all new code
- **Unit Tests**: Test business logic in isolation
- **Integration Tests**: Test API endpoints end-to-end
- **Test Data**: Use factories, avoid hardcoded test data

### Test Structure
```python
# ✅ REQUIRED - Clear test structure
def test_create_user_with_valid_data():
    # Arrange
    user_data = {"email": "test@example.com", "name": "Test User"}

    # Act
    response = client.post("/users", json=user_data)

    # Assert
    assert response.status_code == 201
    assert response.json()["email"] == user_data["email"]
```

## Development Workflow

### Pre-commit Requirements
All code must pass these checks before commit:
- **Linting**: flake8, pylint
- **Formatting**: black, isort
- **Security**: bandit, gitleaks
- **Tests**: pytest with coverage

### Code Review Standards
- **Single Responsibility**: Each PR addresses one concern
- **Test Coverage**: New code includes appropriate tests
- **Documentation**: Public APIs documented
- **Security Review**: Changes reviewed for security implications

## API Standards

### Request/Response Format
```python
# ✅ REQUIRED - Structured responses
class CreateUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    created_at: datetime

# ❌ FORBIDDEN - Untyped responses
def create_user():
    return {"result": "ok", "data": some_dict}
```

### Error Responses
```python
# ✅ REQUIRED - Structured error responses
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

# ❌ FORBIDDEN - Raw exception exposure
raise Exception("Database connection failed")
```

## Performance Standards

### Response Time Requirements
- **Health Check**: < 100ms
- **Simple CRUD**: < 500ms
- **Complex Operations**: < 2s
- **File Operations**: < 10s

### Resource Limits
- **Memory**: < 512MB per instance
- **CPU**: < 80% sustained usage
- **Database Connections**: < 20 per instance

## Documentation Standards

### Code Documentation
- **Module Docstrings**: Purpose and usage examples
- **Function Docstrings**: Parameters, return values, exceptions
- **Class Docstrings**: Purpose and key methods
- **Inline Comments**: Explain complex business logic only

### API Documentation
- **OpenAPI**: Automatically generated from Pydantic models
- **Examples**: Include request/response examples
- **Error Codes**: Document all possible error responses

## Versioning & Release Standards

### Semantic Versioning
Follow [semver.org](https://semver.org) for version numbers:
- **MAJOR**: Breaking API changes (1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (1.0.0 → 1.0.1)

### Conventional Commits
Use standardized commit messages for automatic changelog generation:
```bash
feat: add user authentication endpoint
fix: resolve race condition in health check
docs: update API documentation
chore: bump dependencies
BREAKING CHANGE: remove deprecated /v1/users endpoint
```

### Release Process
1. **Development**: Work in feature branches, merge via PRs
2. **CHANGELOG.md**: Automatically updated from conventional commits
3. **Tagging**: `git tag v1.0.0` triggers automated release
4. **GitHub Actions**: Builds, tests, creates release with notes
5. **Archive**: Release notes saved to `docs/releases/v1.0.0.md`

### Release Documentation
- **CHANGELOG.md**: Complete technical history for developers
- **docs/releases/**: User-focused highlights archived by version
- **GitHub Releases**: Public release announcements with binaries

### Version Workflow
```bash
# 1. Make changes with conventional commits
git commit -m "feat: add new API endpoint"

# 2. Tag when ready to release
git tag v1.1.0
git push origin v1.1.0

# 3. GitHub Actions automatically:
#    - Updates pyproject.toml version
#    - Extracts changelog section
#    - Creates GitHub release
#    - Archives release notes
```

---

**Context for AI Assistants**: Enforce these standards in all code changes. Use conventional commits, maintain CHANGELOG.md, follow semantic versioning. Reject implementations that violate security, performance, or quality requirements.
