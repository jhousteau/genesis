# Genesis Project Templates

Project templates for the Genesis bootstrap system. Each template provides a complete, working project structure with best practices, testing, and tooling.

## Available Templates

### 1. Python API (`python-api`)
FastAPI-based REST API with comprehensive tooling:
- **Framework**: FastAPI with Uvicorn
- **Package Management**: Poetry
- **Testing**: pytest with async support and coverage
- **Code Quality**: Black, isort, mypy, pre-commit hooks
- **Features**: Auto-generated OpenAPI docs, health checks, structured logging

### 2. CLI Tool (`cli-tool`) 
Click-based command-line application:
- **Framework**: Click with Rich for beautiful output
- **Package Management**: Poetry
- **Testing**: pytest with Click's test runner
- **Code Quality**: Black, isort, mypy, pre-commit hooks
- **Features**: Multiple commands, styled output, help generation

### 3. TypeScript Service (`typescript-service`)
Express-based TypeScript web service:
- **Framework**: Express.js with TypeScript
- **Package Management**: npm/yarn
- **Testing**: Jest with Supertest for API testing
- **Code Quality**: ESLint, Prettier, TypeScript strict mode
- **Features**: Health checks, security middleware, error handling

## Template Structure

Each template directory contains:
- `template.json` - Template metadata and variable definitions
- `*.template` files - Template files with variable substitution
- Directory structure matching the target project layout

### Template Variables

Templates support variable substitution using `{{variable_name}}` syntax:

**Common Variables:**
- `project_name` - Name of the project (used for package names, imports)
- `project_description` - Brief description of the project
- `author_name` - Author's full name
- `author_email` - Author's email address

**Language-Specific Variables:**
- `python_version` - Python version requirement (default: 3.11)
- `node_version` - Node.js version requirement (default: 18)
- `command_name` - CLI command name (for CLI tools)

## Using Templates

Templates are used by the Genesis bootstrap command:

```bash
# Create Python API project
genesis bootstrap my-api --type python-api

# Create CLI tool
genesis bootstrap my-tool --type cli-tool

# Create TypeScript service  
genesis bootstrap my-service --type typescript-service
```

The bootstrap process:
1. Copies template files to target directory
2. Substitutes variables in file names and content
3. Renames `__project_name__` directories to actual project name
4. Initializes git repository (unless `--skip-git` is used)
5. Runs initial setup (install dependencies, etc.)

## Template Features

### All Templates Include:
- Complete project structure
- Dependency management configuration
- Testing framework setup
- Code quality tools (linting, formatting, type checking)
- Makefile with common tasks
- Comprehensive README with usage instructions
- Environment configuration examples
- CI/CD ready structure

### Python Templates Include:
- Poetry for dependency management
- pytest with coverage reporting
- Black + isort for code formatting
- mypy for type checking
- pre-commit hooks

### TypeScript Templates Include:
- Full TypeScript configuration
- Jest for testing with Supertest
- ESLint + Prettier for code quality
- Hot reload development setup
- Express.js with security middleware

## Creating Custom Templates

To create a new template:

1. **Create template directory**: `templates/my-template/`
2. **Add template.json**: Define template metadata and variables
3. **Create template files**: Use `.template` extension for files needing substitution
4. **Use variable syntax**: `{{variable_name}}` for substitution
5. **Add to CLI choices**: Update bootstrap command in `genesis-cli/src/genesis.py`

### Example template.json:
```json
{
  "name": "My Template",
  "description": "Description of what this template creates",
  "variables": {
    "project_name": "string",
    "project_description": "string",
    "author_name": "string",
    "custom_variable": "string"
  },
  "files": [
    {
      "src": "source.template",
      "dest": "destination",
      "substitute": true
    }
  ]
}
```

## Template Best Practices

1. **Keep templates minimal but complete** - Include what's necessary, avoid bloat
2. **Follow language conventions** - Use standard project structures
3. **Include comprehensive testing** - Every template should have working tests
4. **Provide clear documentation** - README should explain how to use the generated project
5. **Use consistent variable names** - Stick to common variables across templates
6. **Test template generation** - Ensure bootstrapped projects work out of the box
7. **Include quality tooling** - Linting, formatting, type checking as appropriate
8. **Make it runnable immediately** - `npm install && npm start` or `poetry install && poetry run` should work

## Template Validation

Templates are validated to ensure they:
- Create working projects out of the box
- Include proper dependency management
- Have passing tests
- Follow security best practices
- Meet Genesis AI safety requirements (file count limits)
- Include appropriate documentation