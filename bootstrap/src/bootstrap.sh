#!/usr/bin/env bash
# Genesis Project Bootstrap - Generic project initialization
# Extracted and simplified from old Genesis (505→148 lines)

set -euo pipefail

# Colors and helpers
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log() { echo -e "${2:-$BLUE}$1${NC}"; }
error_exit() { log "❌ $1" "$RED" >&2; exit 1; }

# Find Genesis root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENESIS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATES_DIR="$GENESIS_ROOT/templates"

copy_genesis_tooling() {
    local template_type="$1"
    local project_path="$2"
    local template_path="$TEMPLATES_DIR/$template_type"

    if [ ! -d "$template_path" ]; then
        log "⚠️  Template directory not found: $template_path" "$RED"
        return 0
    fi

    log "🔧 Copying Genesis tooling files..."

    # Copy scripts directory from Genesis root
    if [ -d "$GENESIS_ROOT/scripts" ]; then
        cp -r "$GENESIS_ROOT/scripts" "$project_path/"
        chmod +x "$project_path/scripts"/*.sh 2>/dev/null || true
        log "  ✅ Scripts directory copied"
    fi

    # Copy .claude directory if it exists in template
    if [ -d "$template_path/.claude" ]; then
        mkdir -p "$project_path/.claude"
        cp -r "$template_path/.claude"/* "$project_path/.claude/"

        # Process template variables in .claude files
        find "$project_path/.claude" -name "*.template" -type f | while read -r template_file; do
            output_file="${template_file%.template}"
            sed "s/__project_name__/$PROJECT_NAME/g" "$template_file" > "$output_file"
            rm "$template_file"
        done
        log "  ✅ Claude configuration copied"
    fi

    # Copy additional template files from the specific project type
    if [ -d "$template_path/scripts" ]; then
        cp -r "$template_path/scripts"/* "$project_path/scripts/" 2>/dev/null || true
        chmod +x "$project_path/scripts"/*.sh 2>/dev/null || true
        log "  ✅ Template-specific scripts copied"
    fi

    # Copy config directory if it exists
    if [ -d "$template_path/config" ]; then
        mkdir -p "$project_path/config"
        cp -r "$template_path/config"/* "$project_path/config/" 2>/dev/null || true
        log "  ✅ Configuration templates copied"
    fi

    # Copy and process .envrc template if it exists
    if [ -f "$template_path/.envrc.template" ]; then
        sed "s/{{project_name}}/$PROJECT_NAME/g" "$template_path/.envrc.template" > "$project_path/.envrc"
        log "  ✅ Environment configuration (.envrc) created"
    fi
}

show_usage() {
    cat << EOF
Usage: $0 <project-name> [--type <type>] [--path <path>] [--skip-git]

Bootstrap project with structure and tooling.

Arguments:
  project-name     Project to create

Options:
  --type <type>    python-api, typescript-service, cli-tool (default: python-api)
  --path <path>    Directory to create in (default: current directory)
  --skip-git       Skip Git initialization
  --help          Show help

Examples: $0 my-api --type python-api --path ~/projects/
EOF
}

create_project() {
    log "📁 Creating $PROJECT_TYPE project..."
    mkdir -p "$PROJECT_PATH"/{src,tests,docs/{api,guides,architecture},scripts,scratch}
    command -v git &>/dev/null || error_exit "Git is required"

    case "$PROJECT_TYPE" in
        python-api)
            cat > "$PROJECT_PATH/pyproject.toml" << EOF
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
[tool.poetry]
name = "$PROJECT_NAME"
version = "0.1.0"
description = "Python API"
authors = ["Your Name <email@example.com>"]
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^24.8.0"
ruff = "^0.6.0"
mypy = "^1.8.0"
EOF
            echo '"""Python API."""' > "$PROJECT_PATH/src/__init__.py" ;;
        typescript-service)
            cat > "$PROJECT_PATH/package.json" << EOF
{"name":"$PROJECT_NAME","version":"0.1.0","description":"TypeScript service","main":"dist/index.js","scripts":{"build":"tsc","start":"node dist/index.js","dev":"ts-node src/index.ts","test":"jest"},"dependencies":{"express":"^4.18.0"},"devDependencies":{"@types/express":"^4.17.0","@types/node":"^20.0.0","typescript":"^5.0.0","ts-node":"^10.9.0","jest":"^29.7.0"}}
EOF
            echo 'console.log("TypeScript service");' > "$PROJECT_PATH/src/index.ts" ;;
        cli-tool)
            cat > "$PROJECT_PATH/pyproject.toml" << EOF
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
[tool.poetry]
name = "$PROJECT_NAME"
version = "0.1.0"
description = "CLI tool"
[tool.poetry.dependencies]
python = "^3.11"
click = "^8.1.0"
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
EOF
            echo -e '#!/usr/bin/env python3\nprint("CLI tool")' > "$PROJECT_PATH/src/cli.py" ;;
    esac

    # Common files
    cat > "$PROJECT_PATH/README.md" << EOF
# $PROJECT_NAME

$PROJECT_TYPE project with structure and tooling.

## Quick Start
\`\`\`bash
make setup  # Install dependencies
make test   # Run tests
make dev    # Start development
\`\`\`

## Development
Quality gates, testing, and CI/CD ready.
EOF

    cat > "$PROJECT_PATH/.gitignore" << 'EOF'
node_modules/
venv/
.venv/
__pycache__/
*.egg-info/
dist/
build/
.coverage
coverage/
.env
.env.local
scratch/
EOF

    cat > "$PROJECT_PATH/Makefile" << 'EOF'
.PHONY: setup test lint build clean dev help
setup: ## Install dependencies
	@if [ -f "pyproject.toml" ]; then poetry install; fi
	@if [ -f "package.json" ]; then npm install; fi
test: ## Run tests
	@if [ -f "pyproject.toml" ]; then pytest; fi
	@if [ -f "package.json" ]; then npm test; fi
lint: ## Run linters and formatters
	@if command -v ruff >/dev/null; then ruff check --fix .; fi
	@if command -v black >/dev/null; then black .; fi
dev: ## Start development server
	@if [ -f "pyproject.toml" ]; then poetry run uvicorn src.main:app --reload || echo "Add uvicorn to start dev server"; fi
	@if [ -f "package.json" ]; then npm run dev; fi
build: ## Build project
	@if [ -f "pyproject.toml" ]; then poetry build; fi
	@if [ -f "package.json" ]; then npm run build; fi
clean: ## Clean build artifacts
	@rm -rf dist/ build/ *.egg-info/ .coverage coverage/
help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
EOF

    # Copy Genesis tooling files
    copy_genesis_tooling "$PROJECT_TYPE" "$PROJECT_PATH"

    # Initialize git if requested
    [[ "$SKIP_GIT" == "true" ]] && return
    log "🔧 Initializing Git..."
    cd "$PROJECT_PATH"
    git init
    git add .
    git commit -m "feat: Initial bootstrap

Project: $PROJECT_NAME ($PROJECT_TYPE)
Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

Structure, dependencies, quality gates, and testing ready"
}

# Parse arguments
[[ $# -lt 1 ]] && { show_usage; exit 1; }
[[ "$1" == "--help" ]] && { show_usage; exit 0; }
PROJECT_NAME="$1"; PROJECT_TYPE="python-api"; PROJECT_PATH="$PWD/$PROJECT_NAME"; SKIP_GIT="false"
shift
while [[ $# -gt 0 ]]; do
    case "$1" in
        --type) PROJECT_TYPE="$2"; shift 2 ;;
        --path) PROJECT_PATH="$2/$PROJECT_NAME"; shift 2 ;;
        --skip-git) SKIP_GIT="true"; shift ;;
        --help) show_usage; exit 0 ;;
        *) error_exit "Unknown option: $1" ;;
    esac
done

# Main execution
log "🚀 Project Bootstrap" "$GREEN"
log "Creating: $PROJECT_NAME ($PROJECT_TYPE) at $PROJECT_PATH"
create_project
log "✅ Bootstrap complete! Next: cd $PROJECT_PATH && make setup" "$GREEN"
