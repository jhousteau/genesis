# Security Policy

Genesis follows security best practices and maintains a comprehensive security posture for all components.

## 🛡️ Security Framework

### Supported Versions

Only the latest version of Genesis receives security updates. We recommend staying current with releases.

| Version | Supported |
| ------- | --------- |
| Latest  | ✅        |
| < Latest| ❌        |

## 🔒 Security Measures

### Automated Security Scanning

Genesis implements multiple layers of automated security scanning:

#### 1. Secret Detection
- **Tool**: Gitleaks
- **Scope**: All commits and pull requests
- **Action**: Prevents secrets from being committed

#### 2. Dependency Scanning
- **Python**: Safety (vulnerability database scanning)
- **Node.js**: npm audit (vulnerability scanning)
- **Schedule**: Every dependency update and weekly scans
- **Auto-updates**: Dependabot manages security patches

#### 3. Static Application Security Testing (SAST)
- **Tool**: GitHub CodeQL + Bandit (Python)
- **Scope**: All code changes
- **Queries**: Security-extended and quality analysis

#### 4. Infrastructure Security
- **Pre-commit hooks**: Prevent insecure code from being committed
- **Branch protection**: Main branch requires reviews and passing checks
- **AI Safety**: File count limits prevent overwhelming AI assistants

### Security Policies

#### Branch Protection
- Main branch is protected
- Requires pull request reviews
- All status checks must pass
- No direct commits allowed

#### Dependency Management
- Weekly automated security updates
- Major version updates require manual review
- Vulnerability scanning on all dependencies
- Lock files committed for reproducible builds

#### Code Quality Gates
- All code must pass SAST scanning
- Secret detection must pass
- Pre-commit hooks enforced
- Test coverage requirements

## 🚨 Reporting Security Vulnerabilities

### Responsible Disclosure

If you discover a security vulnerability in Genesis:

1. **DO NOT** open a public issue
2. **DO NOT** discuss in public forums
3. **DO** email: [your-security-email]
4. **DO** include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Your contact information

### Response Timeline

- **24 hours**: Initial acknowledgment
- **7 days**: Preliminary analysis and severity assessment
- **30 days**: Resolution and patch release (if applicable)

### Security Advisory Process

1. Vulnerability reported privately
2. Genesis team validates and assesses impact
3. Fix developed and tested
4. Security advisory published
5. Patch released
6. Public disclosure after users have time to update

## 🔧 Security Configuration

### For Genesis Development

When contributing to Genesis:

```bash
# Install pre-commit hooks
pre-commit install

# Run security checks locally
poetry install
poetry run safety check
poetry run bandit -r .

# Verify no secrets in commits
gitleaks detect --source .
```

### For Generated Projects

Projects created by Genesis inherit security configurations:

- Pre-configured pre-commit hooks
- Dependency security scanning
- Secret detection
- Branch protection templates
- Security-focused CI/CD pipelines

## 📋 Security Checklist

### Before Committing
- [ ] Run pre-commit hooks
- [ ] No hardcoded secrets or credentials
- [ ] Dependencies are up to date
- [ ] Code passes SAST scanning
- [ ] Tests cover security-relevant functionality

### Before Releasing
- [ ] All security scans pass
- [ ] Dependency vulnerabilities resolved
- [ ] Security documentation updated
- [ ] Release notes include security fixes
- [ ] Automated security tests pass

### Regular Maintenance
- [ ] Weekly dependency updates reviewed
- [ ] Security scanning results analyzed
- [ ] Pre-commit hook versions updated
- [ ] Security policies reviewed quarterly

## 🛠️ Security Tools Integration

### IDE Integration
```bash
# VSCode extensions
- GitHub.vscode-github-actions
- ms-python.bandit

# Pre-commit integration
pre-commit install --install-hooks
```

### Local Development
```bash
# Quick security check
make security-check

# Full security suite
make security-full

# Check for secrets before commit
gitleaks protect --staged
```

## 🎯 Security Best Practices

### Genesis Principles Applied to Security

1. **Build Generic, Use Everywhere**: Security configurations work for Genesis and all generated projects
2. **Eat Our Own Dog Food**: Genesis uses its own security patterns
3. **AI Safety**: Secure by default, safe for AI-assisted development
4. **Lean Implementation**: Comprehensive security without bloat

### Secure Development Lifecycle

1. **Design**: Security requirements defined upfront
2. **Code**: SAST and secret detection prevent issues
3. **Build**: Dependency scanning and security tests
4. **Deploy**: Automated security validation
5. **Monitor**: Continuous dependency updates

## 📚 Additional Resources

- [GitHub Security Features](https://docs.github.com/en/code-security)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [Python Security Best Practices](https://python.org/dev/security/)
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/)

---

**Remember**: Security is everyone's responsibility. When in doubt, ask for a security review.
