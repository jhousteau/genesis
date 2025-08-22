#!/usr/bin/env bash
# Example usage of the setup-project tool

# Create a test directory
TEST_DIR="/tmp/test-project-$(date +%s)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "Creating test project in: $TEST_DIR"
echo "================================"

# Initialize a new API project
python /Users/jameshousteau/source_code/setup-project/setup.py init \
    --name=example-api \
    --type=api \
    --language=python \
    --cloud=gcp

echo ""
echo "Project created! Structure:"
echo "================================"
tree -L 2 . 2>/dev/null || ls -la

echo ""
echo "Available commands:"
echo "================================"
echo "make help    # Show all commands"
echo "make setup   # Setup project"
echo "make dev     # Start development"
echo "make test    # Run tests"
echo "make deploy  # Deploy to environment"

echo ""
echo "To explore the project:"
echo "cd $TEST_DIR"