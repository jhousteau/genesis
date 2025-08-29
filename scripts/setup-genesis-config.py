#!/usr/bin/env python3
"""
Setup Genesis configuration by processing template files with project variables.
This applies Genesis patterns to Genesis itself.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

# Add genesis to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from genesis.core.config import ConfigLoader


def get_git_author_email() -> str:
    """Get author email from git config."""
    try:
        result = subprocess.run(
            ["git", "config", "user.email"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "genesis@example.com"


def process_template_file(
    template_path: Path, output_path: Path, variables: dict[str, Any]
) -> None:
    """Process a template file with variable substitution."""
    if not template_path.exists():
        print(f"Warning: Template file not found: {template_path}")
        return

    try:
        with open(template_path) as f:
            content = f.read()

        # Simple variable substitution
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(content)

        print(f"✅ Processed: {template_path.name} → {output_path.name}")

    except Exception as e:
        print(f"❌ Error processing {template_path}: {e}")


def main():
    """Main configuration setup."""
    print("🔧 Setting up Genesis configuration...")

    # Load Genesis config
    config_path = Path(__file__).parent.parent / "config" / "genesis.yml"
    loader = ConfigLoader("GENESIS_")

    # Load config with environment overrides
    config = loader.load(
        file_path=config_path, defaults={"author_email": get_git_author_email()}
    )

    print("📋 Loaded configuration:")
    print(f"   Project: {config['project_name']}")
    print(f"   Author: {config['author_name']} <{config['author_email']}>")
    print(f"   Version: {config['genesis_version']}")

    # Process template files in Genesis root
    root_path = Path(__file__).parent.parent
    template_files = [
        (".bandit", ".bandit"),
        (".flake8", ".flake8"),
        (".gitleaks.toml", ".gitleaks.toml"),
        (".pre-commit-config.yaml", ".pre-commit-config.yaml"),
    ]

    for template_name, output_name in template_files:
        template_path = root_path / template_name
        output_path = root_path / output_name

        # If file exists and has template variables, process it
        if template_path.exists():
            process_template_file(template_path, output_path, config)

    # Process Claude configuration
    claude_settings_template = root_path / ".claude" / "settings.json"
    if claude_settings_template.exists():
        process_template_file(
            claude_settings_template, claude_settings_template, config
        )

    print("✅ Genesis configuration setup complete!")
    print("\nNext steps:")
    print("  - Review generated config files")
    print("  - Run: pre-commit install --install-hooks")
    print("  - Test: python -m genesis.cli --help")


if __name__ == "__main__":
    main()
