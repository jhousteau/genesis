#!/usr/bin/env bash
# Debug script to test patterns

set -euo pipefail

cd /tmp

echo "Testing pattern on test_bad.py:"
echo "================================"
rg --line-number --no-heading 'def [^(]*\([^)]*=\s*"[^"]+"|def [^(]*\([^)]*=\s*'\''[^'\'']+'\''' test_bad.py || echo "No matches"

echo
echo "Files in current directory:"
ls -la *.py 2>/dev/null || echo "No .py files found"

echo
echo "Testing with explicit file pattern:"
rg --line-number --no-heading 'def [^(]*\([^)]*=\s*"[^"]+"|def [^(]*\([^)]*=\s*'\''[^'\'']+'\''' . || echo "No matches in current directory"