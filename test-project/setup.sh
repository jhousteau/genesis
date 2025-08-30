#!/bin/bash
set -e

echo "🚀 Setting up test-project development environment..."

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Error: Not in project root directory (pyproject.toml not found)"
    exit 1
fi

# Install dependencies with Poetry
echo "📦 Installing dependencies..."
if command -v poetry >/dev/null 2>&1; then
    poetry install
else
    echo "❌ Error: Poetry not found. Please install Poetry first."
    echo "   Visit: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Install pre-commit hooks
echo "🔒 Installing pre-commit hooks..."
poetry run pre-commit install --install-hooks

# Check if direnv is available
if command -v direnv >/dev/null 2>&1; then
    echo "🌍 direnv detected - environment will auto-load when entering directory"
    direnv allow
else
    echo "⚠️  direnv not found - you can install it for automatic environment loading"
    echo "   Or manually source .envrc: source .envrc"
fi

# Initialize git hooks if needed
if [[ -d ".git" ]]; then
    echo "🔧 Git repository detected - pre-commit hooks installed"
else
    echo "ℹ️  No git repository found - hooks will be installed when you init git"
fi

# Test the setup
echo "🧪 Testing setup..."
poetry run python -c "print('✅ Python environment working')"
poetry run black --version >/dev/null && echo "✅ Code formatting tools ready"
poetry run pytest --version >/dev/null && echo "✅ Testing framework ready"

echo ""
echo "🎉 Setup complete! You can now:"
echo "   • Run tests: make test"
echo "   • Format code: make format"
echo "   • Start dev server: make run"
echo "   • Smart commit: genesis commit"
echo "   • See all commands: make help"
echo ""
echo "💡 Pro tip: Use 'genesis status' to check project health"
