#!/usr/bin/env python3
"""
Genesis Documentation Update Hook
Automatically updates documentation when files are modified.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


def log(message: str, level: str = "INFO"):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"📚 [{timestamp}] {message}")


def get_project_version() -> str:
    """Get current version from pyproject.toml."""
    try:
        with open("pyproject.toml") as f:
            content = f.read()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            return match.group(1) if match else "0.1.0"
    except FileNotFoundError:
        return "0.1.0"


def should_update_docs(tool_input: dict) -> bool:
    """Determine if this file change should trigger documentation updates."""
    file_path = tool_input.get("file_path", "")

    # Skip if we're already updating documentation files
    doc_patterns = ["CHANGELOG.md", "docs/releases/", ".claude/", "README.md"]

    for pattern in doc_patterns:
        if pattern in file_path:
            return False

    # Update docs for source code changes
    update_patterns = ["src/", "pyproject.toml", ".py", "main.py", "__init__.py"]

    return any(pattern in file_path for pattern in update_patterns)


def detect_change_type(tool_input: dict) -> str | None:
    """Detect what type of change is being made based on file content."""
    content = tool_input.get("content", "") or tool_input.get("new_string", "")
    file_path = tool_input.get("file_path", "")

    # Check for API changes
    if "src/" in file_path and any(
        keyword in content.lower()
        for keyword in ["@app.", "def ", "class ", "fastapi", "endpoint"]
    ):
        if "break" in content.lower() or "deprecated" in content.lower():
            return "BREAKING CHANGE"
        elif any(
            keyword in content.lower()
            for keyword in ["def ", "class ", "@app.post", "@app.put", "new"]
        ):
            return "feat"
        else:
            return "fix"

    # Check for configuration changes
    if "pyproject.toml" in file_path:
        return "chore"

    # Default to fix for other changes
    return "fix"


def update_changelog(change_type: str, file_path: str, description: str):
    """Update CHANGELOG.md with the detected change."""
    changelog_path = Path("CHANGELOG.md")

    if not changelog_path.exists():
        log("CHANGELOG.md not found, skipping update")
        return

    try:
        with open(changelog_path) as f:
            content = f.read()

        # Find the [Unreleased] section
        unreleased_pattern = r"(## \[Unreleased\].*?)(## \[)"
        match = re.search(unreleased_pattern, content, re.DOTALL)

        if not match:
            log("Could not find [Unreleased] section in CHANGELOG.md")
            return

        # Map change types to sections
        section_map = {
            "feat": "### Added",
            "BREAKING CHANGE": "### Changed",
            "fix": "### Fixed",
            "chore": "### Changed",
            "docs": "### Changed",
        }

        section_header = section_map.get(change_type, "### Changed")

        # Check if section already exists in unreleased
        unreleased_content = match.group(1)

        if section_header in unreleased_content:
            # Add to existing section
            section_pattern = f"({re.escape(section_header)}.*?)((?=### |## \\[|$))"
            section_match = re.search(section_pattern, unreleased_content, re.DOTALL)

            if section_match:
                new_entry = f"- Updated {Path(file_path).name}: {description}\\n"
                new_section = (
                    section_match.group(1) + new_entry + section_match.group(2)
                )
                new_unreleased = unreleased_content.replace(
                    section_match.group(0), new_section
                )
            else:
                new_unreleased = unreleased_content
        else:
            # Add new section
            file_name = Path(file_path).name
            new_entry = f"\\n{section_header}\\n- Updated {file_name}: {description}\\n"
            # Insert before the next ## section
            next_section_pos = unreleased_content.find("\\n## [")
            if next_section_pos == -1:
                new_unreleased = unreleased_content + new_entry
            else:
                new_unreleased = (
                    unreleased_content[:next_section_pos]
                    + new_entry
                    + unreleased_content[next_section_pos:]
                )

        # Replace in full content
        new_content = content.replace(match.group(1), new_unreleased)

        with open(changelog_path, "w") as f:
            f.write(new_content)

        log(f"Updated CHANGELOG.md with {change_type} entry")

    except Exception as e:
        log(f"Error updating CHANGELOG.md: {e}")


def update_version_refs(file_path: str):
    """Update version references in documentation files if needed."""
    version = get_project_version()

    # Update README.md version badges if they exist
    readme_path = Path("README.md")
    if readme_path.exists() and "src/" in file_path:
        try:
            with open(readme_path) as f:
                content = f.read()

            # Update version badges (basic pattern matching)
            version_patterns = [
                (r"(version-)[0-9]+\\.[0-9]+\\.[0-9]+", f"\\1{version}"),
                (r"(Version\\s+)[0-9]+\\.[0-9]+\\.[0-9]+", f"\\1{version}"),
            ]

            updated = False
            for pattern, replacement in version_patterns:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    updated = True

            if updated:
                with open(readme_path, "w") as f:
                    f.write(content)
                log("Updated version references in README.md")

        except Exception as e:
            log(f"Error updating README.md: {e}")


def main():
    """Main hook execution."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Only process Write/Edit operations
        if tool_name not in ["Write", "Edit", "MultiEdit"]:
            sys.exit(0)

        file_path = tool_input.get("file_path", "")

        # Check if this change should trigger documentation updates
        if not should_update_docs(tool_input):
            sys.exit(0)

        log(f"Processing documentation updates for: {file_path}")

        # Detect the type of change being made
        change_type = detect_change_type(tool_input)
        if not change_type:
            sys.exit(0)

        # Generate description based on file path and change
        file_name = Path(file_path).name
        if "main.py" in file_name:
            description = "API endpoint or core functionality changes"
        elif "__init__.py" in file_name:
            description = "Module initialization updates"
        elif "pyproject.toml" in file_name:
            description = "Project configuration changes"
        else:
            description = f"Updates to {file_name}"

        # Update documentation
        update_changelog(change_type, file_path, description)
        update_version_refs(file_path)

        log(f"Documentation updates completed for {change_type} change")

        # Exit with 0 to allow the original Write/Edit to proceed
        sys.exit(0)

    except json.JSONDecodeError as e:
        log(f"Error parsing hook input: {e}")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
