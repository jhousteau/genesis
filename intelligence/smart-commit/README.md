# Smart-Commit Workflow System

> 📖 **[Read the Unified Vision →](../../docs/vision/SOLVE_UNIFIED_VISION.md)** - Universal workflow automation supporting the graph-driven development platform.

**Smart-commit workflow that works across all technology stacks**

Smart-commit is a universal development pipeline that automatically detects your project type, selects appropriate tools, and runs them until convergence - ensuring consistent quality across Python, Node.js, Go, Rust, Terraform, Docker, and more.

## Features

- **🔍 Adaptive Project Detection**: Automatically identifies project types (Python, Node.js, Go, Rust, Terraform, Docker, etc.)
- **🔄 Convergent Stability Engine**: Runs tools until they reach a stable state, resolving formatter conflicts
- **🛠️ Universal Tool Matrix**: Technology-specific tool configurations with automatic selection
- **✅ Quality Gates**: Pre-execution checks for resources, permissions, dependencies, and state
- **🎯 Smart Git Integration**: Intelligent commit message generation based on changes
- **📦 Multi-Technology Support**: Works with polyglot projects and monorepos

## 🆕 Recent Improvements (Issue #82)

**Enhanced Error Reporting & Debugging**:
- **Complete Error Capture**: Tools now capture both stdout and stderr for comprehensive error reporting
- **Clear Status Display**: Visual indicators (✓/✗) show success/failure status for each tool
- **Real-time Output**: Verbose mode (`--verbose`) shows tool execution in real-time instead of progress spinner
- **Better Logging**: Hierarchical logging with always-visible tool status and detailed error messages
- **Improved Troubleshooting**: Enhanced error visibility makes debugging quality gate failures much easier

**Infrastructure Improvements**:
- **Pre-commit Integration**: Fixed TODO linter self-exclusion in pre-commit configuration
- **Import Organization**: Systematic cleanup and formatting across entire codebase
- **Performance**: Reduced processing time and improved stability
- **CLI Enhancements**: Better command-line experience with improved error handling

## Installation

```bash
# From the smart-commit package directory
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

```bash
# Detect project types and available tools
smart-commit detect

# Run autofix until convergence
smart-commit autofix

# Run complete pipeline with commit
smart-commit all "feat: add new feature"

# Check project status
smart-commit status

# Run quality gates
smart-commit quality --all
```

## Commands

### Core Commands

- **`smart-commit autofix [--dry-run] [message]`** - Run formatters and linters until stable
- **`smart-commit test [--dry-run]`** - Run tests for all detected project types
- **`smart-commit typecheck [--dry-run]`** - Run type checking across technologies
- **`smart-commit security [--dry-run]`** - Run security scans
- **`smart-commit all [--dry-run] [message]`** - Complete pipeline with optional commit

### Utility Commands

- **`smart-commit detect`** - Show detected project types and confidence scores
- **`smart-commit status`** - Display project status and available tools
- **`smart-commit quality [gate]`** - Check quality gates

## Supported Technologies

| Technology | Formatters | Linters | Type Checkers | Tests | Security |
|------------|------------|---------|---------------|-------|----------|
| **Python** | black, ruff | ruff, flake8, pylint | mypy, pyright | pytest | bandit, safety |
| **Node.js** | prettier | eslint | - | npm test, jest | npm audit |
| **TypeScript** | prettier | eslint | tsc | npm test, jest | npm audit |
| **Go** | gofmt, goimports | golangci-lint | go vet | go test | gosec |
| **Rust** | rustfmt | clippy | cargo check | cargo test | cargo audit |
| **Terraform** | terraform fmt | tflint | terraform validate | - | tfsec, checkov |
| **Docker** | - | hadolint | - | docker build | trivy |

## Architecture

### Convergent Stability Engine

The stability engine runs tools iteratively until no more changes occur:

```python
# Runs up to max_iterations until stable
result = stability_engine.run_until_stable(tools)
if result.converged:
    print(f"Converged in {result.iterations} iterations")
```

### Adaptive Detection

Smart-commit uses multiple signals to detect project types:

1. **File patterns** - `*.py`, `*.js`, `*.go`, etc.
2. **Marker files** - `package.json`, `Cargo.toml`, `go.mod`
3. **Content patterns** - Kubernetes manifests, Docker directives
4. **Priority scoring** - More specific patterns score higher

### Quality Gates

Pre-execution checks ensure system readiness:

- **Resource Gates** - CPU, memory, disk space
- **Permission Gates** - Write access, no exposed secrets
- **Dependency Gates** - Required tools available
- **Configuration Gates** - Config files present
- **State Gates** - No interfering processes

## Graph Integration

### Smart-Commit in Graph-Driven Development

Smart-commit plays a crucial role in the graph-driven development workflow as the quality gate before graph updates:

```python
from smart_commit import SmartCommitOrchestrator
from graph.repositories.gcp_repository import GCPRepository

# Graph-aware smart-commit workflow
graph_repo = GCPRepository()
orchestrator = SmartCommitOrchestrator()

# Get files associated with specific graph nodes
graph_id = "adr-001-auth-service"
node_files = await graph_repo.get_node_implementation_files(graph_id)

# Apply smart-commit to each node's files
for node_id, files in node_files.items():
    result = orchestrator.execute_on_files(files)
    if result.success:
        # Update graph database with clean code
        await graph_repo.update_node_status(node_id, "ready_for_deployment")
    else:
        # Block node until quality issues resolved
        await graph_repo.update_node_status(node_id, "blocked", result.issues)
```

### Terraform and Infrastructure Integration

Smart-commit handles Terraform files generated from graph templates:

```bash
# After graph generates Terraform modules
solve graph generate-terraform --graph-id adr-001

# Smart-commit ensures Terraform quality
smart-commit detect
# Detected: Terraform (95.2%), YAML (12.1%)

smart-commit all "feat: deploy auth service infrastructure"
# ✓ terraform fmt completed
# ✓ tflint validation passed
# ✓ tfsec security scan clean
# ✓ checkov compliance passed
# ✓ Committed and ready for deployment
```

### Multi-Node Development

Smart-commit coordinates quality across parallel development:

```python
from smart_commit import SmartCommitOrchestrator
from solve.parallel_execution import ParallelExecutionEngine

# Smart-commit across all graph nodes in parallel
parallel_engine = ParallelExecutionEngine()
quality_tasks = []

for node_id in graph_nodes:
    task = {
        "agent_type": "smart_commit",
        "node_id": node_id,
        "files": await graph_repo.get_node_files(node_id),
        "commit_message": f"feat: implement {node_id}"
    }
    quality_tasks.append(task)

# Execute quality gates across all nodes simultaneously
results = await parallel_engine.execute_tasks(quality_tasks)
```

## Configuration

Smart-commit works with zero configuration but can be customized:

```python
from smart_commit import SmartCommitOrchestrator, SmartCommitConfig

config = SmartCommitConfig(
    max_iterations=10,
    dry_run=False,
    verbose=True,
    skip_tools={'pylint'},  # Skip specific tools
    quality_gates_enabled=True,
    graph_integration=True,  # Enable graph-aware features
    node_id="api-service"    # Associate with specific graph node
)

orchestrator = SmartCommitOrchestrator(config)
result = orchestrator.execute(ExecutionMode.ALL)
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run type checking
mypy src/smart_commit/

# Format code
black src/smart_commit/
ruff format src/smart_commit/
```

## Why Smart-Commit?

Traditional approaches require:
- Different tools for each technology
- Manual tool configuration and coordination
- Dealing with formatter conflicts
- Inconsistent quality across projects

Smart-commit provides:
- **One command** for any project type
- **Automatic tool selection** based on detection
- **Conflict resolution** through convergence
- **Consistent quality** across all technologies

## Examples

### Python Project
```bash
$ smart-commit detect
Detected: Python (95.2%), Markdown (12.1%)

$ smart-commit all "fix: resolve type errors"
✓ Autofix completed (3 iterations)
✓ Tests passed (15 tests)
✓ Type checking passed
✓ Security scans clean
✓ Committed: a3f2b1c
```

### Multi-Technology Monorepo
```bash
$ smart-commit detect
Detected: TypeScript (78.3%), Python (65.2%), Docker (45.1%)

$ smart-commit autofix
Running: prettier, eslint, black, ruff, hadolint
Converged in 4 iterations
```

### Infrastructure Project
```bash
$ smart-commit detect
Detected: Terraform (92.1%), YAML (55.3%)

$ smart-commit security
Running: tfsec, checkov
✓ No security issues found
```

## License

MIT License - See LICENSE file for details
