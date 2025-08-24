#!/usr/bin/env python3
"""
Genesis CLI - Secret Management Commands
SHIELD Methodology CLI Interface for Secret Operations

Provides comprehensive command-line interface for secret management operations
supporting both development and production workflows.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple

import click
import yaml

# Import Genesis secret management components
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from config.unified_config import get_config
from core.secrets import (
    SecretAccessDeniedError,
    SecretError,
    SecretManager,
    SecretNotFoundError,
    SecretRotationError,
    SecretValidationError,
    get_secret_manager,
)
from core.secrets.iam import AccessRequest, IAMSecretAccessManager


@click.group()
@click.pass_context
def secret(ctx: click.Context) -> None:
    """Secret management commands using SHIELD methodology"""
    # Initialize context
    ctx.ensure_object(dict)

    # Load configuration
    try:
        project_id = get_config("system.project_id") or os.getenv("PROJECT_ID")
        environment = get_config("system.environment") or os.getenv(
            "ENVIRONMENT", "development"
        )

        if not project_id:
            click.echo("Error: PROJECT_ID must be set", err=True)
            sys.exit(1)

        # Initialize secret manager
        ctx.obj["secret_manager"] = get_secret_manager(
            project_id=project_id,
            environment=environment,
        )
        ctx.obj["project_id"] = project_id
        ctx.obj["environment"] = environment

    except Exception as e:
        click.echo(f"Error initializing secret manager: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "table"]),
    default="table",
    help="Output format",
)
@click.option(
    "--filter", "filters", multiple=True, help="Filter secrets (format: key=value)"
)
@click.option("--environment", help="Filter by environment")
@click.option("--service", help="Filter by service")
@click.pass_context
def scan(
    ctx: click.Context,
    format: str,
    filters: Tuple[str, ...],
    environment: Optional[str],
    service: Optional[str],
) -> None:
    """SHIELD S: Scan and discover secrets"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    try:
        # Build filters
        filter_dict = {}
        for filter_item in filters:
            if "=" in filter_item:
                key, value = filter_item.split("=", 1)
                filter_dict[key] = value

        if environment:
            filter_dict["environment"] = environment
        if service:
            filter_dict["service"] = service

        # Scan secrets
        click.echo(f"🔍 Scanning secrets in project {ctx.obj['project_id']}...")
        secrets = secret_manager.scan_secrets(filter_dict if filter_dict else None)

        if not secrets:
            click.echo("No secrets found matching the criteria")
            return

        # Format output
        if format == "json":
            click.echo(
                json.dumps(
                    [
                        {
                            "name": s.name,
                            "version": s.version,
                            "environment": s.environment,
                            "created_at": (
                                s.created_at.isoformat() if s.created_at else None
                            ),
                            "tags": s.tags,
                        }
                        for s in secrets
                    ],
                    indent=2,
                )
            )
        elif format == "yaml":
            click.echo(
                yaml.dump(
                    [
                        {
                            "name": s.name,
                            "version": s.version,
                            "environment": s.environment,
                            "created_at": (
                                s.created_at.isoformat() if s.created_at else None
                            ),
                            "tags": s.tags,
                        }
                        for s in secrets
                    ],
                    default_flow_style=False,
                )
            )
        else:  # table format
            click.echo(f"\n📋 Found {len(secrets)} secrets:")
            click.echo("-" * 80)
            click.echo(
                f"{'Name':<30} {'Version':<10} {'Environment':<15} {'Created':<20}"
            )
            click.echo("-" * 80)

            for secret in secrets:
                created_str = (
                    secret.created_at.strftime("%Y-%m-%d %H:%M")
                    if secret.created_at
                    else "Unknown"
                )
                click.echo(
                    f"{secret.name:<30} {secret.version:<10} {secret.environment:<15} {created_str:<20}"
                )

    except SecretError as e:
        click.echo(f"❌ Secret scan failed: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("secret_name")
@click.option("--version", default="latest", help="Secret version to retrieve")
@click.option("--no-cache", is_flag=True, help="Skip cache lookup")
@click.option("--service", help="Requesting service identity")
@click.option(
    "--format",
    type=click.Choice(["value", "json"]),
    default="value",
    help="Output format",
)
@click.pass_context
def get(
    ctx: click.Context,
    secret_name: str,
    version: str,
    no_cache: bool,
    service: Optional[str],
    format: str,
) -> None:
    """SHIELD H: Get secret value securely"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    try:
        click.echo(f"🔐 Retrieving secret: {secret_name} (version: {version})")

        value = secret_manager.get_secret(
            secret_name=secret_name,
            version=version,
            use_cache=not no_cache,
        )

        if format == "json":
            click.echo(
                json.dumps(
                    {
                        "secret_name": secret_name,
                        "version": version,
                        "retrieved_at": datetime.utcnow().isoformat(),
                        "value": value,
                    },
                    indent=2,
                )
            )
        else:
            click.echo(value)

    except SecretNotFoundError:
        click.echo(f"❌ Secret '{secret_name}' not found", err=True)
        sys.exit(1)
    except SecretAccessDeniedError:
        click.echo(f"❌ Access denied to secret '{secret_name}'", err=True)
        sys.exit(1)
    except SecretError as e:
        click.echo(f"❌ Failed to retrieve secret: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("secret_name")
@click.option(
    "--value",
    prompt=True,
    hide_input=True,
    help="Secret value (will prompt securely if not provided)",
)
@click.option(
    "--label", "labels", multiple=True, help="Labels for the secret (format: key=value)"
)
@click.option("--environment", help="Environment for the secret")
@click.option("--service", help="Service that owns the secret")
@click.option("--no-validate", is_flag=True, help="Skip secret validation")
@click.pass_context
def create(
    ctx: click.Context,
    secret_name: str,
    value: str,
    labels: Tuple[str, ...],
    environment: Optional[str],
    service: Optional[str],
    no_validate: bool,
) -> None:
    """SHIELD I: Create secret with isolation controls"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    try:
        # Build labels
        label_dict = {}
        for label in labels:
            if "=" in label:
                key, val = label.split("=", 1)
                label_dict[key] = val

        if environment:
            label_dict["environment"] = environment
        if service:
            label_dict["service"] = service

        click.echo(f"🔒 Creating secret: {secret_name}")

        success = secret_manager.create_secret(
            secret_name=secret_name,
            secret_value=value,
            labels=label_dict if label_dict else None,
            validate=not no_validate,
        )

        if success:
            click.echo(f"✅ Secret '{secret_name}' created successfully")
        else:
            click.echo(f"❌ Failed to create secret '{secret_name}'", err=True)
            sys.exit(1)

    except SecretValidationError as e:
        click.echo(f"❌ Secret validation failed: {e}", err=True)
        sys.exit(1)
    except SecretError as e:
        click.echo(f"❌ Failed to create secret: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("secret_name")
@click.option("--new-value", help="New secret value (auto-generated if not provided)")
@click.option("--no-validate", is_flag=True, help="Skip validation of new secret")
@click.option("--force", is_flag=True, help="Force rotation even if not due")
@click.pass_context
def rotate(
    ctx: click.Context,
    secret_name: str,
    new_value: Optional[str],
    no_validate: bool,
    force: bool,
) -> None:
    """SHIELD E: Rotate secret with encryption"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    try:
        click.echo(f"🔄 Rotating secret: {secret_name}")

        if new_value:
            new_version = secret_manager.rotate_secret(
                secret_name=secret_name,
                new_value=new_value,
                validate=not no_validate,
            )
        else:
            new_version = secret_manager.rotate_secret(
                secret_name=secret_name,
                validate=not no_validate,
            )

        click.echo(
            f"✅ Secret '{secret_name}' rotated successfully to version: {new_version}"
        )

    except SecretNotFoundError:
        click.echo(f"❌ Secret '{secret_name}' not found", err=True)
        sys.exit(1)
    except SecretRotationError as e:
        click.echo(f"❌ Secret rotation failed: {e}", err=True)
        sys.exit(1)
    except SecretError as e:
        click.echo(f"❌ Failed to rotate secret: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option("--secret-name", help="Filter by specific secret")
@click.option("--start-time", help="Start time (ISO format)")
@click.option("--end-time", help="End time (ISO format)")
@click.option("--operation", help="Filter by operation type")
@click.option("--status", help="Filter by operation status")
@click.option("--limit", default=100, help="Maximum number of entries")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def audit(
    ctx: click.Context,
    secret_name: Optional[str],
    start_time: Optional[str],
    end_time: Optional[str],
    operation: Optional[str],
    status: Optional[str],
    limit: int,
    format: str,
) -> None:
    """SHIELD L: View audit logs"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    try:
        # Parse time filters
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        audit_logs = secret_manager.get_secret_audit_log(
            secret_name=secret_name,
            start_time=start_dt,
            end_time=end_dt,
        )

        if not audit_logs:
            click.echo("No audit log entries found matching the criteria")
            return

        if format == "json":
            click.echo(json.dumps(audit_logs, indent=2))
        else:
            click.echo(f"\n📋 Found {len(audit_logs)} audit log entries:")
            click.echo("-" * 120)
            click.echo(
                f"{'Timestamp':<20} {'Operation':<15} {'Status':<10} {'Secret':<25} {'User':<20} {'Risk':<8}"
            )
            click.echo("-" * 120)

            for entry in audit_logs:
                timestamp_str = entry["timestamp"][:19]  # Truncate to seconds
                secret_display = entry.get("secret_name", "N/A")[:24]
                user_display = entry.get("user_identity", "N/A")[:19]
                risk_display = f"{entry.get('risk_score', 0):.2f}"

                click.echo(
                    f"{timestamp_str:<20} {entry['operation']:<15} {entry['status']:<10} "
                    f"{secret_display:<25} {user_display:<20} {risk_display:<8}"
                )

    except SecretError as e:
        click.echo(f"❌ Failed to retrieve audit logs: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def health(ctx: click.Context, format: str) -> None:
    """SHIELD D: Validate secret health and security posture"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    try:
        click.echo("🏥 Validating secret health...")
        health_report = secret_manager.validate_secret_health()

        if format == "json":
            click.echo(json.dumps(health_report, indent=2))
        else:
            click.echo("\n🏥 Secret Health Report")
            click.echo("=" * 60)
            click.echo(f"Project: {health_report['project_id']}")
            click.echo(f"Environment: {health_report['environment']}")
            click.echo(f"Timestamp: {health_report['timestamp']}")
            click.echo()

            click.echo("📊 Summary:")
            click.echo(f"  Secrets Discovered: {health_report['secrets_discovered']}")
            click.echo(f"  Secrets Validated: {health_report['secrets_validated']}")
            click.echo(
                f"  Validation Failures: {len(health_report['validation_failures'])}"
            )
            click.echo(f"  Security Issues: {len(health_report['security_issues'])}")
            click.echo()

            if health_report["validation_failures"]:
                click.echo("❌ Validation Failures:")
                for failure in health_report["validation_failures"]:
                    click.echo(f"  - {failure['secret_name']}: {failure['error']}")
                click.echo()

            if health_report["security_issues"]:
                click.echo("⚠️  Security Issues:")
                for issue in health_report["security_issues"]:
                    severity_icon = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢",
                    }.get(issue["severity"], "⚪")

                    click.echo(
                        f"  {severity_icon} {issue['message']} ({issue['severity']})"
                    )
                click.echo()

            if health_report["recommendations"]:
                click.echo("💡 Recommendations:")
                for rec in health_report["recommendations"]:
                    click.echo(f"  - {rec}")

    except SecretError as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("secret_name")
@click.option("--force", is_flag=True, help="Force deletion (required for production)")
@click.confirmation_option(prompt="Are you sure you want to delete this secret?")
@click.pass_context
def delete(ctx: click.Context, secret_name: str, force: bool) -> None:
    """Delete a secret (use with extreme caution)"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    try:
        click.echo(f"🗑️  Deleting secret: {secret_name}")

        success = secret_manager.delete_secret(
            secret_name=secret_name,
            force=force,
        )

        if success:
            click.echo(f"✅ Secret '{secret_name}' deleted successfully")
        else:
            click.echo(f"❌ Failed to delete secret '{secret_name}'", err=True)
            sys.exit(1)

    except SecretNotFoundError:
        click.echo(f"❌ Secret '{secret_name}' not found", err=True)
        sys.exit(1)
    except SecretError as e:
        click.echo(f"❌ Failed to delete secret: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option(
    "--auto-rotate", is_flag=True, help="Perform automatic rotation for due secrets"
)
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def rotation_status(ctx: click.Context, auto_rotate: bool, format: str) -> None:
    """Check rotation status and perform auto-rotation"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    if not secret_manager.rotator:
        click.echo("❌ Secret rotation is disabled", err=True)
        sys.exit(1)

    try:
        # Check which secrets need rotation
        rotation_needed = secret_manager.rotator.check_rotation_needed()

        if format == "json":
            result = {
                "rotation_needed": rotation_needed,
                "auto_rotate_performed": False,
                "rotation_results": [],
            }

            if auto_rotate and rotation_needed:
                rotation_results = secret_manager.rotator.auto_rotate_secrets()
                result["auto_rotate_performed"] = True
                result["rotation_results"] = rotation_results

            click.echo(json.dumps(result, indent=2))
        else:
            if rotation_needed:
                click.echo(f"⚠️  {len(rotation_needed)} secrets need rotation:")
                click.echo("-" * 80)
                click.echo(
                    f"{'Secret Name':<30} {'Age (days)':<12} {'Overdue (days)':<15}"
                )
                click.echo("-" * 80)

                for item in rotation_needed:
                    click.echo(
                        f"{item['secret_name']:<30} {item['age_days']:<12} {item['overdue_days']:<15}"
                    )

                if auto_rotate:
                    click.echo("\n🔄 Performing automatic rotation...")
                    rotation_results = secret_manager.rotator.auto_rotate_secrets()

                    click.echo("✅ Rotation completed:")
                    click.echo(
                        f"  - Successful: {rotation_results['rotations_successful']}"
                    )
                    click.echo(f"  - Failed: {rotation_results['rotations_failed']}")

                    if rotation_results["errors"]:
                        click.echo("\n❌ Errors:")
                        for error in rotation_results["errors"]:
                            click.echo(f"  - {error}")
            else:
                click.echo("✅ All secrets are up to date with rotation policies")

    except SecretError as e:
        click.echo(f"❌ Rotation check failed: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option("--start-time", help="Start time for metrics (ISO format)")
@click.option("--end-time", help="End time for metrics (ISO format)")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def metrics(
    ctx: click.Context, start_time: Optional[str], end_time: Optional[str], format: str
) -> None:
    """View security metrics and statistics"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    if not secret_manager.monitor:
        click.echo("❌ Secret monitoring is disabled", err=True)
        sys.exit(1)

    try:
        # Parse time filters
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        metrics = secret_manager.monitor.get_security_metrics(start_dt, end_dt)

        if format == "json":
            click.echo(json.dumps(metrics, indent=2))
        else:
            click.echo("\n📊 Security Metrics")
            click.echo("=" * 60)
            click.echo(
                f"Time Range: {metrics['time_range']['start']} to {metrics['time_range']['end']}"
            )
            click.echo()

            click.echo("🔢 Operation Summary:")
            click.echo(f"  Total Operations: {metrics['total_operations']}")
            click.echo(f"  Unique Secrets: {metrics['unique_secrets_accessed']}")
            click.echo(f"  Unique Users: {metrics['unique_users']}")
            click.echo(f"  Unique Services: {metrics['unique_services']}")
            click.echo()

            if metrics["operations_by_status"]:
                click.echo("📈 Operations by Status:")
                for status, count in metrics["operations_by_status"].items():
                    click.echo(f"  {status}: {count}")
                click.echo()

            click.echo("⚠️  Risk Distribution:")
            click.echo(f"  Low Risk: {metrics['risk_distribution']['low']}")
            click.echo(f"  Medium Risk: {metrics['risk_distribution']['medium']}")
            click.echo(f"  High Risk: {metrics['risk_distribution']['high']}")
            click.echo()

            alerts = metrics["security_alerts"]
            click.echo("🚨 Security Alerts:")
            click.echo(f"  Total: {alerts['total']}")
            click.echo(f"  Resolved: {alerts['resolved']}")
            click.echo(f"  Unresolved: {alerts['unresolved']}")

            if alerts["by_level"]:
                click.echo("  By Level:")
                for level, count in alerts["by_level"].items():
                    click.echo(f"    {level}: {count}")

    except SecretError as e:
        click.echo(f"❌ Failed to retrieve metrics: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option(
    "--export-format", type=click.Choice(["json", "csv", "yaml"]), default="json"
)
@click.option("--output-file", help="Output file path")
@click.option(
    "--include-values", is_flag=True, help="Include secret values (DANGEROUS)"
)
@click.pass_context
def export_secrets(
    ctx: click.Context,
    export_format: str,
    output_file: Optional[str],
    include_values: bool,
) -> None:
    """Export secrets metadata (SHIELD: LOG)"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    if include_values:
        click.confirm(
            "⚠️  WARNING: This will export secret values in plain text. Continue?",
            abort=True,
        )

    try:
        click.echo("📤 Exporting secrets metadata...")
        secrets = secret_manager.scan_secrets()

        export_data = []
        for secret in secrets:
            data = {
                "name": secret.name,
                "version": secret.version,
                "environment": secret.environment,
                "created_at": (
                    secret.created_at.isoformat() if secret.created_at else None
                ),
                "updated_at": (
                    secret.updated_at.isoformat() if secret.updated_at else None
                ),
                "tags": secret.tags,
            }

            if include_values:
                try:
                    data["value"] = secret_manager.get_secret(secret.name)
                except Exception as e:
                    data["value_error"] = str(e)

            export_data.append(data)

        # Format and output
        if export_format == "json":
            output_content = json.dumps(export_data, indent=2)
        elif export_format == "yaml":
            output_content = yaml.dump(export_data, default_flow_style=False)
        else:  # csv
            import csv
            import io

            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
            output_content = output.getvalue()

        if output_file:
            with open(output_file, "w") as f:
                f.write(output_content)
            click.echo(f"✅ Exported {len(export_data)} secrets to {output_file}")
        else:
            click.echo(output_content)

    except SecretError as e:
        click.echo(f"❌ Export failed: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("config_file")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--force", is_flag=True, help="Force apply changes")
@click.pass_context
def sync_config(
    ctx: click.Context, config_file: str, dry_run: bool, force: bool
) -> None:
    """Sync secrets from configuration file (SHIELD: DEFEND)"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    try:
        click.echo(f"📋 Loading configuration from: {config_file}")

        with open(config_file, "r") as f:
            if config_file.endswith(".yaml") or config_file.endswith(".yml"):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)

        secrets_config = config.get("secrets", [])
        click.echo(f"🔍 Found {len(secrets_config)} secrets in configuration")

        changes = []

        for secret_config in secrets_config:
            secret_name = secret_config["name"]

            try:
                # Check if secret exists
                existing_secret = secret_manager.get_secret(secret_name)
                action = "UPDATE"
            except SecretNotFoundError:
                action = "CREATE"

            changes.append(
                {"action": action, "secret_name": secret_name, "config": secret_config}
            )

        if dry_run:
            click.echo("\n🔍 Dry run - Changes that would be applied:")
            click.echo("-" * 60)
            for change in changes:
                click.echo(f"{change['action']: <8} {change['secret_name']}")
            return

        if not force:
            click.confirm(f"Apply {len(changes)} changes?", abort=True)

        # Apply changes
        applied = 0
        for change in changes:
            try:
                secret_config = change["config"]

                if change["action"] == "CREATE":
                    success = secret_manager.create_secret(
                        secret_name=secret_config["name"],
                        secret_value=secret_config["value"],
                        labels=secret_config.get("labels"),
                    )
                    if success:
                        applied += 1
                        click.echo(f"✅ Created: {secret_config['name']}")
                else:
                    # For updates, create new version
                    secret_manager._add_secret_version(
                        secret_config["name"], secret_config["value"]
                    )
                    applied += 1
                    click.echo(f"✅ Updated: {secret_config['name']}")

            except Exception as e:
                click.echo(f"❌ Failed {change['secret_name']}: {e}")

        click.echo(f"\n✅ Applied {applied}/{len(changes)} changes successfully")

    except FileNotFoundError:
        click.echo(f"❌ Configuration file not found: {config_file}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Sync failed: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option(
    "--threat-level",
    type=click.Choice(["info", "warning", "error", "critical"]),
    help="Filter by threat level",
)
@click.option(
    "--resolved/--unresolved", default=None, help="Filter by resolution status"
)
@click.option("--limit", default=50, help="Maximum number of alerts")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def security_alerts(
    ctx: click.Context,
    threat_level: Optional[str],
    resolved: Optional[bool],
    limit: int,
    format: str,
) -> None:
    """View security alerts and threats (SHIELD: DEFEND)"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    if not secret_manager.monitor:
        click.echo("❌ Security monitoring is disabled", err=True)
        sys.exit(1)

    try:
        # Convert threat_level to enum if provided
        from core.secrets.monitoring import AlertLevel

        alert_level = AlertLevel(threat_level) if threat_level else None

        alerts = secret_manager.monitor.get_security_alerts(
            alert_level=alert_level,
            resolved=resolved,
            limit=limit,
        )

        if not alerts:
            click.echo("No security alerts found matching the criteria")
            return

        if format == "json":
            click.echo(json.dumps(alerts, indent=2))
        else:
            click.echo(f"\n🚨 Found {len(alerts)} security alerts:")
            click.echo("-" * 120)
            click.echo(
                f"{'Alert ID':<20} {'Level':<10} {'Type':<20} {'Secret':<25} {'Status':<10} {'Timestamp':<20}"
            )
            click.echo("-" * 120)

            for alert in alerts:
                timestamp_str = alert["timestamp"][:19]
                status_str = "✅ Resolved" if alert["resolved"] else "⚠️  Active"

                # Severity emoji
                level_emoji = {
                    "critical": "🔴",
                    "error": "🟠",
                    "warning": "🟡",
                    "info": "🔵",
                }.get(alert["alert_level"], "⚪")

                click.echo(
                    f"{alert['alert_id']:<20} {level_emoji} {alert['alert_level']:<8} "
                    f"{alert['threat_type']:<20} {alert.get('secret_name', 'N/A'):<25} "
                    f"{status_str:<10} {timestamp_str:<20}"
                )

                # Show description for critical/error alerts
                if alert["alert_level"] in ["critical", "error"]:
                    click.echo(f"   📝 {alert['description']}")

                    if alert["recommended_actions"]:
                        click.echo(
                            f"   💡 Actions: {', '.join(alert['recommended_actions'][:2])}"
                        )

    except Exception as e:
        click.echo(f"❌ Failed to retrieve security alerts: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("alert_id")
@click.option("--notes", help="Resolution notes")
@click.pass_context
def resolve_alert(ctx: click.Context, alert_id: str, notes: Optional[str]) -> None:
    """Resolve a security alert"""
    secret_manager: SecretManager = ctx.obj["secret_manager"]

    if not secret_manager.monitor:
        click.echo("❌ Security monitoring is disabled", err=True)
        sys.exit(1)

    try:
        click.echo(f"✅ Resolving security alert: {alert_id}")
        success = secret_manager.monitor.resolve_alert(
            alert_id, notes or "Resolved via CLI"
        )

        if success:
            click.echo(f"✅ Alert {alert_id} resolved successfully")
        else:
            click.echo(f"❌ Alert {alert_id} not found", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Failed to resolve alert: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("secret_name")
@click.option(
    "--user-identity", required=True, help="User or service account requesting access"
)
@click.option("--duration-hours", default=24, help="Duration of access in hours")
@click.option("--justification", help="Justification for access request")
@click.pass_context
def request_access(
    ctx: click.Context,
    secret_name: str,
    user_identity: str,
    duration_hours: int,
    justification: Optional[str],
) -> None:
    """Request temporary access to a secret (JIT access)"""
    try:
        # Initialize IAM manager
        iam_manager = IAMSecretAccessManager(
            project_id=ctx.obj["project_id"], enable_jit_access=True
        )

        # Create access request
        access_request = AccessRequest(
            secret_name=secret_name,
            user_identity=user_identity,
            duration_hours=duration_hours,
            justification=justification,
            temporary=True,
        )

        click.echo(f"🔑 Requesting temporary access to secret: {secret_name}")
        grant_id = iam_manager.request_temporary_access(access_request)

        click.echo(f"✅ Temporary access granted: {grant_id}")
        click.echo(f"   Duration: {duration_hours} hours")
        click.echo(
            f"   Expires: {(datetime.utcnow() + timedelta(hours=duration_hours)).isoformat()}"
        )

    except SecretError as e:
        click.echo(f"❌ Access request failed: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("grant_id")
@click.pass_context
def revoke_access(ctx: click.Context, grant_id: str) -> None:
    """Revoke temporary access grant"""
    try:
        iam_manager = IAMSecretAccessManager(
            project_id=ctx.obj["project_id"], enable_jit_access=True
        )

        click.echo(f"🔒 Revoking access grant: {grant_id}")
        success = iam_manager.revoke_temporary_access(grant_id)

        if success:
            click.echo(f"✅ Access grant {grant_id} revoked successfully")
        else:
            click.echo(f"❌ Failed to revoke access grant {grant_id}", err=True)
            sys.exit(1)

    except SecretError as e:
        click.echo(f"❌ Access revocation failed: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.argument("secret_name")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def iam_policy(ctx: click.Context, secret_name: str, format: str) -> None:
    """View IAM policy for a secret"""
    try:
        iam_manager = IAMSecretAccessManager(project_id=ctx.obj["project_id"])

        click.echo(f"🔍 Getting IAM policy for secret: {secret_name}")
        policy = iam_manager.get_secret_iam_policy(secret_name)

        if format == "json":
            click.echo(json.dumps(policy, indent=2))
        else:
            click.echo(f"\n🛡️  IAM Policy for {secret_name}")
            click.echo("=" * 60)

            if not policy["bindings"]:
                click.echo("No IAM bindings found")
            else:
                for i, binding in enumerate(policy["bindings"], 1):
                    click.echo(f"\nBinding {i}:")
                    click.echo(f"  Role: {binding['role']}")
                    click.echo(f"  Members: {', '.join(binding['members'])}")

                    if "condition" in binding:
                        click.echo(f"  Condition: {binding['condition']['title']}")
                        click.echo(
                            f"  Expression: {binding['condition']['expression']}"
                        )

    except SecretError as e:
        click.echo(f"❌ Failed to get IAM policy: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option("--cleanup-expired", is_flag=True, help="Clean up expired access grants")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def access_summary(ctx: click.Context, cleanup_expired: bool, format: str) -> None:
    """View access grants summary and optionally cleanup expired grants"""
    try:
        iam_manager = IAMSecretAccessManager(
            project_id=ctx.obj["project_id"], enable_jit_access=True
        )

        if cleanup_expired:
            click.echo("🧹 Cleaning up expired access grants...")
            cleaned_up = iam_manager.cleanup_expired_grants()
            click.echo(f"✅ Cleaned up {cleaned_up} expired grants")

        summary = iam_manager.get_access_summary()

        if format == "json":
            click.echo(json.dumps(summary, indent=2))
        else:
            click.echo("\n📊 Access Grants Summary")
            click.echo("=" * 60)
            click.echo(f"Project ID: {summary['project_id']}")
            click.echo(f"JIT Access Enabled: {summary['jit_access_enabled']}")
            click.echo(f"Total Grants: {summary['total_grants']}")
            click.echo(f"Active Grants: {summary['active_grants']}")
            click.echo(f"Expired Grants: {summary['expired_grants']}")
            click.echo(f"Generated At: {summary['summary_generated_at']}")

    except SecretError as e:
        click.echo(f"❌ Failed to get access summary: {e}", err=True)
        sys.exit(1)


@secret.command()
@click.option("--secret-name", help="Filter by specific secret")
@click.option("--start-time", help="Start time (ISO format)")
@click.option("--end-time", help="End time (ISO format)")
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def iam_audit(
    ctx: click.Context,
    secret_name: Optional[str],
    start_time: Optional[str],
    end_time: Optional[str],
    format: str,
) -> None:
    """Audit IAM-based secret access"""
    try:
        iam_manager = IAMSecretAccessManager(project_id=ctx.obj["project_id"])

        # Parse time filters
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        audit_entries = iam_manager.audit_secret_access(
            secret_name=secret_name,
            start_time=start_dt,
            end_time=end_dt,
        )

        if not audit_entries:
            click.echo("No IAM access entries found matching the criteria")
            return

        if format == "json":
            click.echo(json.dumps(audit_entries, indent=2))
        else:
            click.echo(f"\n📋 Found {len(audit_entries)} IAM access entries:")
            click.echo("-" * 120)
            click.echo(
                f"{'Grant ID':<20} {'Secret':<25} {'User':<30} {'Requested':<20} {'Duration':<10}"
            )
            click.echo("-" * 120)

            for entry in audit_entries:
                requested_str = entry["requested_at"][:19]  # Truncate to seconds
                click.echo(
                    f"{entry['grant_id']:<20} {entry['secret_name']:<25} "
                    f"{entry['user_identity']:<30} {requested_str:<20} {entry['duration_hours']:<10}"
                )

    except SecretError as e:
        click.echo(f"❌ Failed to retrieve IAM audit: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    secret()
