# Genesis Vision & Context

This directory contains Genesis project vision, goals, and strategic context that should guide all development decisions.

## Project Vision

**Mission**: Genesis is a development toolkit that enforces professional standards and security best practices while enabling rapid, high-quality software development.

## Target Users

Define our primary user personas and their needs:
- **Solo Developer**: Building personal projects with professional standards
- **Development Team**: Collaborating on production applications with consistent quality
- **DevOps Engineer**: Deploying and maintaining applications with automated quality gates
- **Security-Conscious Developer**: Building applications with built-in security scanning and fail-fast configuration

## Success Metrics

How we measure Genesis success:
- **Developer Velocity**: Projects created in <2 minutes with full tooling
- **Quality Gates**: 100% enforcement of security and code quality standards
- **AI Safety**: All worktrees <30 files, sparse checkout working seamlessly
- **Zero Configuration**: No manual setup steps for new developers
- **Professional Output**: All generated projects pass enterprise security scans

## Core Constraints

Fundamental constraints that shape all Genesis decisions:
- **Security First**: No hardcoded secrets, fail-fast configuration, mandatory security scanning
- **AI Safety**: File count limits, sparse worktrees, organized documentation context
- **Zero Manual Setup**: Everything automated via bootstrap and quality gates
- **Professional Standards**: Enterprise-ready code quality and security practices
- **Eat Our Own Dog Food**: Genesis uses Genesis patterns throughout

## Strategic Priorities

Rank our priorities when making tradeoffs:
1. **Security & Quality** - Never compromise on security or code quality enforcement
2. **Developer Experience** - Automated setup, clear error messages, helpful guidance
3. **AI Safety & Collaboration** - Support for AI-assisted development workflows
4. **Maintainability** - Clean abstractions, well-documented patterns, extensible design

## Non-Goals

What Genesis will NOT do to maintain focus:
- **General-purpose project management** (focused on development toolkit)
- **Language-specific optimization** (patterns work across languages)
- **Enterprise authentication integration** (local development focus)
- **Custom CI/CD platforms** (GitHub Actions focus)

## Key Principles

### "Build Generic, Use Everywhere"
Nothing should be Genesis-specific unless absolutely necessary. All patterns, configurations, and templates must work for ANY project type.

### Fail-Fast Configuration
Applications should immediately fail with clear error messages when configuration is missing or invalid. No silent fallbacks or mysterious defaults.

### Hierarchical Context
Documentation and configuration should be organized hierarchically with specialized context for AI assistants working in different areas.

### Atomic Operations
All operations (commits, deployments, configuration changes) should be atomic - everything succeeds or everything fails together.

---

**Context for AI Assistants**: Use this vision to guide Genesis development decisions, architectural choices, and feature implementations. When in doubt, prioritize the strategic priorities and key principles listed above.
