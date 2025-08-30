# Bootstrap - Generic Project Initialization

Generic project bootstrapper creating project structure and tooling for Python APIs, TypeScript services, and CLI tools.

## Features

**Core Bootstrap Features:**
- ✅ Multi-language project templates (Python API, TypeScript service, CLI tool)
- ✅ Automatic dependency management (Poetry, npm)
- ✅ Quality gates (Makefile, linting, testing)
- ✅ Git initialization with conventional commits
- ✅ Generic, reusable project structure

**Simplifications from Original (505→166 lines):**
- Consolidated template creation into single function
- Removed GCP-specific coupling and cloud deployment logic
- Streamlined file generation with inline templates
- Simplified argument parsing and validation
- Removed verbose logging while maintaining essential feedback
- Preserved all core project initialization features

## Usage

```bash
# Create Python API project
./src/bootstrap.sh my-api --type python-api

# Create TypeScript service with custom path
./src/bootstrap.sh my-service --type typescript-service --path ~/projects/

# Create CLI tool without Git initialization
./src/bootstrap.sh my-cli --type cli-tool --skip-git

# Get help
./src/bootstrap.sh --help
```

## Project Templates

### Python API (`python-api`)
Creates a FastAPI-based Python project with:
- Poetry dependency management (`pyproject.toml`)
- FastAPI, Uvicorn for web services
- Black, Ruff, MyPy for code quality
- pytest for testing
- Makefile with common targets

### TypeScript Service (`typescript-service`)
Creates an Express-based TypeScript service with:
- npm dependency management (`package.json`)
- Express for web framework
- TypeScript with proper types
- Jest for testing
- Build and development scripts

### CLI Tool (`cli-tool`)
Creates a Python CLI application with:
- Poetry dependency management
- Click framework for CLI interfaces
- pytest for testing
- Executable entry point

## Generated Structure

All project types include:
```
<project-name>/
├── src/                    # Source code
├── tests/                  # Test files
├── docs/                   # Documentation
├── README.md              # Project documentation
├── Makefile              # Common build targets
├── .gitignore            # VCS ignore patterns
└── <config-file>         # pyproject.toml or package.json
```

## Makefile Targets

Each bootstrapped project includes these targets:
- `make setup` - Install dependencies
- `make test` - Run test suite
- `make lint` - Run linters and formatters
- `make dev` - Start development server
- `make build` - Build project artifacts
- `make clean` - Clean build outputs
- `make help` - Show available targets

## Integration with Genesis Workflow

**Works with Genesis development patterns:**
- Compatible with smart-commit quality gates
- Follows Genesis project structure conventions
- Integrates with sparse worktree creation
- Supports AI-safe development workflows
- Generic patterns work for any project type

**Quality Gates:**
- Automatic dependency management setup
- Pre-configured linting and formatting
- Test structure ready for immediate use
- Git initialization with proper ignore patterns
- Makefile automation for common tasks

## Development (AI-Safe Sparse Worktree)

```bash
# Work on bootstrap component in isolation
git worktree add ../bootstrap-work feature/bootstrap-improvements
cd ../bootstrap-work
git sparse-checkout set bootstrap/

# Component has <5 files for AI safety:
# bootstrap/
# ├── README.md
# ├── src/bootstrap.sh           # 166 lines
# └── tests/test_bootstrap.py
```

## Testing

```bash
# Run component tests
pytest bootstrap/tests/ -v

# Test script functionality
cd bootstrap/
./src/bootstrap.sh test-project --type python-api --path /tmp --skip-git

# Test all project types
for type in python-api typescript-service cli-tool; do
    ./src/bootstrap.sh "test-$type" --type "$type" --path /tmp --skip-git
done
```

## Configuration

The script automatically:
- Detects project type and creates appropriate configuration
- Sets up dependency management (Poetry for Python, npm for TypeScript)
- Creates proper directory structure with src/, tests/, docs/
- Generates appropriate .gitignore for each project type
- Initializes Git with conventional commit structure
- Creates Makefile with language-appropriate targets

No additional configuration required - works out of the box for all supported project types.
