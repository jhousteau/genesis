# Genesis Core

Core Genesis functionality including CLI, error handling, and utilities.

## Components

- `cli.py` - Main CLI interface
- `core/` - Core utilities (errors, retry, health, config)
- `commands/` - CLI command implementations  
- `testing/` - Testing utilities and AI safety

## Usage

```bash
# Install Genesis
pip install -e .

# Use CLI
genesis --help
genesis bootstrap my-project
```