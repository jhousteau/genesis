# test-project Release Notes

This directory contains user-focused release notes for each version of test-project.

## Release Process

### Automated Release Flow
1. **Tag a release**: `git tag v1.0.0 && git push origin v1.0.0`
2. **GitHub Actions**: Automatically creates release notes from CHANGELOG.md
3. **Archive created**: Release notes saved to `docs/releases/v1.0.0.md`
4. **GitHub Release**: Published with generated notes

### Manual Release Flow
1. **Update CHANGELOG.md**: Add changes under `[Unreleased]` section
2. **Trigger workflow**: Use GitHub Actions "Release" workflow dispatch
3. **Review and publish**: GitHub Release created as draft for final review

## Release Note Structure

Each release note file contains:
- **What's New**: User-facing features and improvements
- **Breaking Changes**: API changes requiring user action
- **Bug Fixes**: Issues resolved in this release
- **Dependencies**: Updated dependencies and security fixes

## Version History

Release notes are automatically generated from CHANGELOG.md and archived here:

- [v0.1.0](v0.1.0.md) - Initial release

## Changelog vs Release Notes

- **CHANGELOG.md**: Complete technical history for developers
- **docs/releases/**: User-focused highlights for each version
