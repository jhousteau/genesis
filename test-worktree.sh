#!/usr/bin/env bash
cd /Users/jameshousteau/source_code/genesis
echo "Current directory: $(pwd)"
echo "Testing worktree creation..."
/Users/jameshousteau/source_code/genesis/worktree-tools/src/create-sparse-worktree.sh bootstrap-branch bootstrap/ --max-files 10
