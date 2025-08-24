"""CLI interface for smart-commit."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .git_integration import CommitType
from .orchestrator import ExecutionMode, SmartCommitConfig, SmartCommitOrchestrator

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--version", is_flag=True, help="Show version")
def cli(ctx, version):
    """Smart-commit workflow system.

    Quality-gated commit workflow that works across all technology stacks.
    """
    if version:
        from . import __version__

        console.print(f"smart-commit version {__version__}")
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        # Show help if no subcommand
        console.print(ctx.get_help())


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--max-iterations", default=10, help="Maximum convergence iterations")
@click.option("--skip", multiple=True, help="Tools to skip")
@click.option("--no-quality-gates", is_flag=True, help="Skip quality gate checks")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.argument("message", required=False)
def autofix(dry_run, max_iterations, skip, no_quality_gates, verbose, message):
    """Run automatic fixes until convergence."""
    config = SmartCommitConfig(
        dry_run=dry_run,
        max_iterations=max_iterations,
        skip_tools=set(skip),
        quality_gates_enabled=not no_quality_gates,
        verbose=verbose,
        commit_message=message,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Detecting project types...", total=None)

        orchestrator = SmartCommitOrchestrator(config)

        progress.update(task, description="Running autofix...")
        result = orchestrator.execute(ExecutionMode.AUTOFIX)

    # Display results
    if result.success:
        console.print("[green]✓[/green] Autofix completed successfully!")
        if result.convergence_result:
            console.print(
                f"  Converged in {result.convergence_result.iterations} iterations"
            )
            console.print(f"  Time: {result.execution_time:.2f}s")
        if result.commit_sha:
            console.print(f"  Commit: {result.commit_sha[:8]}")
    else:
        console.print("[red]✗[/red] Autofix failed")
        if result.error_message:
            console.print(f"  Error: {result.error_message}")

    sys.exit(0 if result.success else 1)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview without running")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test(dry_run, verbose):
    """Run tests for detected project types."""
    config = SmartCommitConfig(dry_run=dry_run, verbose=verbose)
    orchestrator = SmartCommitOrchestrator(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        _ = progress.add_task("Running tests...", total=None)
        result = orchestrator.execute(ExecutionMode.TEST)

    if result.success:
        console.print("[green]✓[/green] All tests passed!")
    else:
        console.print("[red]✗[/red] Tests failed")

    sys.exit(0 if result.success else 1)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview without running")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def typecheck(dry_run, verbose):
    """Run type checking for detected project types."""
    config = SmartCommitConfig(dry_run=dry_run, verbose=verbose)
    orchestrator = SmartCommitOrchestrator(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        _ = progress.add_task("Running type checks...", total=None)
        result = orchestrator.execute(ExecutionMode.TYPECHECK)

    if result.success:
        console.print("[green]✓[/green] Type checking passed!")
    else:
        console.print("[red]✗[/red] Type checking failed")

    sys.exit(0 if result.success else 1)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview without running")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def security(dry_run, verbose):
    """Run security scans for detected project types."""
    config = SmartCommitConfig(dry_run=dry_run, verbose=verbose)
    orchestrator = SmartCommitOrchestrator(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        _ = progress.add_task("Running security scans...", total=None)
        result = orchestrator.execute(ExecutionMode.SECURITY)

    if result.success:
        console.print("[green]✓[/green] Security scans passed!")
    else:
        console.print("[red]✗[/red] Security issues found")

    sys.exit(0 if result.success else 1)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option(
    "--type",
    "commit_type",
    type=click.Choice([t.value for t in CommitType]),
    default="chore",
    help="Commit type for conventional commits",
)
@click.option("--skip", multiple=True, help="Tools to skip")
@click.option("--no-quality-gates", is_flag=True, help="Skip quality gate checks")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.argument("message", required=False)
def all(dry_run, commit_type, skip, no_quality_gates, verbose, message):
    """Run complete pipeline: autofix, test, typecheck, security."""
    config = SmartCommitConfig(
        dry_run=dry_run,
        skip_tools=set(skip),
        quality_gates_enabled=not no_quality_gates,
        verbose=verbose,
        commit_message=message,
        commit_type=CommitType(commit_type),
    )

    orchestrator = SmartCommitOrchestrator(config)

    # Don't use progress spinner if verbose mode - show all output
    if verbose:
        console.print("[bold]Starting smart-commit pipeline...[/bold]")
        console.print("Mode: ALL")
        console.print(f"Project: {config.project_root}")
        console.print(f"Commit type: {commit_type}")
        console.print(f"Message: {message}\n")
        result = orchestrator.execute(ExecutionMode.ALL)
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            _ = progress.add_task("Running complete pipeline...", total=None)
            result = orchestrator.execute(ExecutionMode.ALL)

    # Display results
    console.print()  # Add spacing
    if result.success:
        console.print("[green bold]✓ Pipeline completed successfully![/green bold]")
        console.print(
            f"  Detected types: {', '.join(t.value for t in result.detected_types)}"
        )
        console.print(f"  Tools run: {len(result.tools_run)}")
        console.print(f"  Time: {result.execution_time:.2f}s")
        if result.commit_sha:
            console.print(f"  Commit: {result.commit_sha[:8]}")
    else:
        console.print("[red bold]✗ Pipeline failed[/red bold]")
        if result.error_message:
            console.print("\n[yellow]Error details:[/yellow]")
            error_lines = result.error_message.strip().split("\n")
            for line in error_lines[:10]:  # Show first 10 lines
                if line.strip():
                    console.print(f"  {line}")
            if len(error_lines) > 10:
                console.print(f"  ... ({len(error_lines) - 10} more lines)")

        # Show quality gate failures
        if result.quality_gate_results:
            failed_gates = [
                g for g, passed in result.quality_gate_results.items() if not passed
            ]
            if failed_gates:
                console.print("\n[yellow]Failed quality gates:[/yellow]")
                for gate in failed_gates:
                    console.print(f"    - {gate}")

        # Show failed tools
        if hasattr(result, "failed_tools") and result.failed_tools:
            console.print("\n[yellow]Failed tools:[/yellow]")
            for tool_name, error in result.failed_tools.items():
                console.print(
                    (
                        f"    - {tool_name}: {error[:100]}..."
                        if len(error) > 100
                        else f"    - {tool_name}: {error}"
                    ),
                )

    sys.exit(0 if result.success else 1)


@cli.command()
def status():
    """Show project status and available tools."""
    orchestrator = SmartCommitOrchestrator()
    status = orchestrator.get_status()

    # Project info
    console.print("\n[bold]Project Status[/bold]")
    console.print(f"Root: {status['project_root']}")
    console.print(f"Types: {', '.join(status['detected_types'])}")

    # Git status
    git = status["git_status"]
    console.print("\n[bold]Git Status[/bold]")
    console.print(f"Branch: {git['branch']}")
    console.print(f"Commits: {git['commit_count']}")
    console.print(
        f"Changes: {'Yes' if git['has_changes'] else 'No'} ({git['change_count']} files)"
    )

    # Available tools
    console.print("\n[bold]Available Tools[/bold]")
    tools = status["available_tools"]

    table = Table(show_header=True, header_style="bold")
    table.add_column("Category")
    table.add_column("Tools")

    for category, tool_list in sorted(tools.items()):
        if tool_list:
            table.add_row(category, ", ".join(tool_list))

    console.print(table)

    # Quality gates
    console.print("\n[bold]Quality Gates[/bold]")
    gates = status["quality_gates"]
    console.print(f"Available: {', '.join(gates)}")


@cli.command()
def detect():
    """Detect and display project types."""
    from .detector import ProjectDetector

    detector = ProjectDetector()
    scores = detector.detect_project_types()
    tools = detector.detect_tools()

    # Display detected types
    console.print("\n[bold]Detected Project Types[/bold]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Type")
    table.add_column("Confidence", justify="right")
    table.add_column("Status")

    for project_type, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        if score > 0:
            confidence = f"{score * 100:.1f}%"
            status = (
                "Primary"
                if score == max(scores.values())
                else "Secondary" if score > 0.3 else "Minor"
            )
            table.add_row(project_type.value, confidence, status)

    console.print(table)

    # Display available tools
    console.print("\n[bold]System Tools[/bold]")

    available = [tool for tool, is_available in tools.items() if is_available]
    unavailable = [tool for tool, is_available in tools.items() if not is_available]

    if available:
        console.print(f"[green]Available:[/green] {', '.join(sorted(available))}")
    if unavailable:
        console.print(
            f"[yellow]Not Available:[/yellow] {', '.join(sorted(unavailable))}"
        )


@cli.command()
@click.option("--all", "run_all", is_flag=True, help="Run all quality gates")
@click.argument("gate", required=False)
def quality(run_all, gate):
    """Check quality gates."""
    from .quality import QualityGate, QualityGateRunner

    runner = QualityGateRunner(Path.cwd())

    if run_all:
        results = runner.run_all_gates()

        console.print("\n[bold]Quality Gate Results[/bold]\n")

        for gate_name, result in results.items():
            if result.passed:
                console.print(f"[green]✓[/green] {gate_name}")
            else:
                console.print(f"[red]✗[/red] {gate_name}")
                for check_name in result.failed_checks:
                    console.print(f"    - {check_name} failed")

    elif gate:
        try:
            gate_type = QualityGate(gate)
            result = runner.run_gate(gate_type)

            console.print(f"\n[bold]{gate_type.value}[/bold]\n")

            for check in result.checks:
                if check.passed:
                    console.print(
                        f"[green]✓[/green] {check.check_name}: {check.message}"
                    )
                else:
                    console.print(f"[red]✗[/red] {check.check_name}: {check.message}")

            if result.passed:
                console.print("\n[green]Quality gate passed![/green]")
            else:
                console.print("\n[red]Quality gate failed![/red]")
        except ValueError:
            console.print(f"[red]Unknown gate: {gate}[/red]")
            console.print(f"Available gates: {', '.join(g.value for g in QualityGate)}")
            sys.exit(1)

    else:
        console.print("Available quality gates:")
        for gate in QualityGate:
            console.print(f"  - {gate.value}")


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
