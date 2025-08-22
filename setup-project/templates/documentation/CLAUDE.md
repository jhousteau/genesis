# Claude AI Assistant Instructions for ${PROJECT_NAME}

## Project Context
- **Name**: ${PROJECT_NAME}
- **Type**: ${PROJECT_TYPE}
- **Language**: Primary development language varies
- **Cloud Provider**: Google Cloud Platform (GCP)
- **Architecture**: Cloud-native, serverless-first

## Project Standards
This project follows the Universal Project Platform standards:

### Development Workflow
- **Smart Commits**: Always use `make commit` or `./scripts/smart-commit.sh`
- **Testing**: All code changes require tests (`make test`)
- **Linting**: Code must pass linting (`make lint`)
- **Documentation**: Keep README.md and docs/ updated

### GCP Integration
- **Isolation**: Each project has its own GCP project and gcloud config
- **Authentication**: Use service account impersonation (no local keys)
- **Deployment**: Use `make deploy-{env}` commands
- **Monitoring**: Built-in Cloud Operations integration

### Security Requirements
- No hardcoded secrets (use Secret Manager)
- All temp files go in `temp/` directory
- Regular security scanning with `make test-security`
- Follow principle of least privilege

## AI Assistant Guidelines

### Always Do
1. **Check project health** before making changes:
   ```bash
   make validate
   ./scripts/validate-compliance.sh
   ```

2. **Use smart commits** for all changes:
   ```bash
   make commit
   ```

3. **Follow the Makefile targets** for common tasks:
   ```bash
   make help  # See all available commands
   ```

4. **Respect the project structure**:
   - Source code in `src/`
   - Tests in `tests/`
   - Documentation in `docs/`
   - Scripts in `scripts/`
   - Temporary files in `temp/`

5. **Use the deployment pipeline**:
   ```bash
   make deploy-dev    # For development
   make deploy-test   # For testing
   make deploy-stage  # For staging
   make deploy-prod   # For production (requires confirmation)
   ```

### Never Do
1. **Don't bypass quality gates**:
   - Don't use `git commit` directly
   - Don't skip tests or linting
   - Don't push untested code

2. **Don't hardcode values**:
   - No API keys, passwords, or secrets in code
   - Use environment variables or Secret Manager
   - No hardcoded URLs or project IDs

3. **Don't break isolation**:
   - Don't use global gcloud config
   - Don't cross-contaminate between projects
   - Don't share credentials between environments

4. **Don't ignore errors**:
   - Always check command exit codes
   - Handle errors gracefully
   - Log failures appropriately

### Code Quality Standards
- Follow language-specific best practices
- Write comprehensive tests (unit + integration)
- Document public APIs and complex logic
- Use type hints/annotations where available
- Keep functions small and focused

### Deployment Guidelines
- Always validate before deploying (`make validate`)
- Use canary deployments for production changes
- Monitor deployments and rollback if needed
- Document deployment procedures in `docs/DEPLOYMENT.md`

### Emergency Procedures
If something goes wrong:

1. **Check the logs**: `make logs`
2. **Validate the project**: `make validate`
3. **Rollback if needed**: `make rollback`
4. **Check monitoring**: `make monitor`

### Common Commands
```bash
# Setup and development
make setup          # Initial project setup
make dev           # Start development environment
make test          # Run all tests
make lint          # Run linters

# Deployment
make deploy-dev    # Deploy to development
make deploy-prod   # Deploy to production

# Maintenance
make clean         # Clean build artifacts
make validate      # Check compliance
make commit        # Smart commit with quality gates
make upgrade       # Upgrade to latest standards

# Troubleshooting
make logs          # View application logs
make monitor       # Open monitoring dashboard
make rollback      # Rollback deployment
```

### File Locations
- **Configuration**: `.project-config.yaml`
- **Environment**: `.envrc` (use direnv)
- **Dependencies**: `requirements.txt`, `package.json`, `go.mod`
- **CI/CD**: `.github/workflows/`
- **Infrastructure**: `infrastructure/` or use shared modules

### Integration Points
This project integrates with:
- **Bootstrap CLI**: `bootstrap` command for project management
- **Intelligence Layer**: AI-driven analysis and optimization
- **Monitoring**: Cloud Operations Suite
- **Secrets**: Google Secret Manager
- **Storage**: Cloud Storage with lifecycle policies
- **Compute**: Cloud Run, Cloud Functions, or GKE

### Project-Specific Notes
Add any project-specific instructions, quirks, or important context here.