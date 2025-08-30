# test-project Scripts

This directory contains executable utility scripts for the project.

## Script Guidelines

- All scripts should be executable: `chmod +x script-name.sh`
- Include `--help` option with usage information
- Use naming pattern: `action-target.sh`
- Include shebang: `#!/bin/bash`

## Common Scripts

Scripts are typically added as development progresses:
- `setup-dev.sh` - Development environment setup
- `run-tests.sh` - Test execution with custom parameters
- `deploy-staging.sh` - Staging deployment automation
