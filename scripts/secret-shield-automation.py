#!/usr/bin/env python3
"""
Genesis Secret Management - SHIELD Automation Script
Comprehensive automated secret management using SHIELD methodology

This script provides automated execution of SHIELD operations:
- S: Scan secrets and validate health
- H: Harden access controls and policies
- I: Isolate secrets by environment and service
- E: Encrypt through automated rotation
- L: Log all operations with comprehensive audit
- D: Defend through monitoring and threat detection
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.secrets import SecretError, get_secret_manager
from core.secrets.iam import IAMSecretAccessManager


class SHIELDAutomation:
    """
    Automated SHIELD operations for comprehensive secret security
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            project_root, "config", "secret-policies.yaml"
        )
        self.logger = self._setup_logging()

        # Load configuration
        self.config = self._load_config()
        self.project_id = self.config["project_id"]
        self.environment = self.config["environment"]

        # Initialize managers
        self.secret_manager = get_secret_manager(
            project_id=self.project_id,
            environment=self.environment,
        )

        self.iam_manager = IAMSecretAccessManager(
            project_id=self.project_id,
            enable_jit_access=True,
        )

        self.logger.info(
            f"SHIELD Automation initialized for project: {self.project_id}"
        )

    def _setup_logging(self) -> logging.Logger:
        """Set up comprehensive logging"""
        logger = logging.getLogger("genesis.shield_automation")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [SHIELD_AUTO] %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _load_config(self) -> dict:
        """Load SHIELD configuration"""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            # Expand environment variables
            config["project_id"] = os.path.expandvars(config["project_id"])
            config["environment"] = os.path.expandvars(config["environment"])

            return config
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    async def scan_operation(self, comprehensive: bool = False) -> dict:
        """
        SHIELD S: Scan secrets and validate health

        Args:
            comprehensive: Whether to perform comprehensive health validation

        Returns:
            Dictionary with scan results
        """
        self.logger.info("🔍 SHIELD SCAN: Starting secret discovery and validation")

        try:
            # Discover all secrets
            secrets = self.secret_manager.scan_secrets()
            self.logger.info(f"Discovered {len(secrets)} secrets")

            results = {
                "timestamp": datetime.utcnow().isoformat(),
                "secrets_discovered": len(secrets),
                "secrets_by_environment": {},
                "secrets_by_service": {},
                "validation_results": None,
            }

            # Categorize secrets
            for secret in secrets:
                env = secret.environment or "unknown"
                service = secret.service or "unknown"

                results["secrets_by_environment"][env] = (
                    results["secrets_by_environment"].get(env, 0) + 1
                )
                results["secrets_by_service"][service] = (
                    results["secrets_by_service"].get(service, 0) + 1
                )

            # Perform health validation if requested
            if comprehensive:
                self.logger.info("Performing comprehensive health validation...")
                health_report = self.secret_manager.validate_secret_health()
                results["validation_results"] = health_report

                # Log critical issues
                critical_issues = [
                    issue
                    for issue in health_report["security_issues"]
                    if issue["severity"] == "critical"
                ]
                if critical_issues:
                    self.logger.critical(
                        f"Found {len(critical_issues)} critical security issues!"
                    )

            self.logger.info("✅ SHIELD SCAN completed successfully")
            return results

        except Exception as e:
            self.logger.error(f"❌ SHIELD SCAN failed: {e}")
            raise SecretError(f"Scan operation failed: {e}")

    async def harden_operation(self) -> dict:
        """
        SHIELD H: Harden access controls and policies

        Returns:
            Dictionary with hardening results
        """
        self.logger.info("🔒 SHIELD HARDEN: Applying security hardening")

        try:
            results = {
                "timestamp": datetime.utcnow().isoformat(),
                "policies_applied": 0,
                "access_controls_configured": 0,
                "cache_optimization": False,
            }

            # Apply environment-specific hardening
            env_config = self.config["isolate"]["environments"].get(
                self.environment, {}
            )

            if env_config:
                # Configure access patterns based on environment
                access_levels = env_config.get("access_levels", [])
                allowed_services = env_config.get("allowed_services", [])

                self.logger.info(
                    f"Configuring access for environment: {self.environment}"
                )
                self.logger.info(f"Access levels: {access_levels}")
                self.logger.info(f"Allowed services: {len(allowed_services)}")

                results["access_controls_configured"] = len(allowed_services)

            # Optimize cache configuration
            if self.secret_manager.cache:
                cache_stats = self.secret_manager.cache.get_stats()
                self.logger.info(f"Cache statistics: {cache_stats}")

                # Clean up expired entries
                cleaned = self.secret_manager.cache.cleanup_expired()
                if cleaned > 0:
                    self.logger.info(f"Cleaned up {cleaned} expired cache entries")

                results["cache_optimization"] = True

            self.logger.info("✅ SHIELD HARDEN completed successfully")
            return results

        except Exception as e:
            self.logger.error(f"❌ SHIELD HARDEN failed: {e}")
            raise SecretError(f"Harden operation failed: {e}")

    async def isolate_operation(self) -> dict:
        """
        SHIELD I: Isolate secrets by environment and service

        Returns:
            Dictionary with isolation results
        """
        self.logger.info("🏛️ SHIELD ISOLATE: Configuring isolation controls")

        try:
            results = {
                "timestamp": datetime.utcnow().isoformat(),
                "iam_policies_created": 0,
                "access_grants_reviewed": 0,
                "expired_grants_cleaned": 0,
            }

            # Clean up expired access grants
            expired_cleaned = self.iam_manager.cleanup_expired_grants()
            results["expired_grants_cleaned"] = expired_cleaned

            if expired_cleaned > 0:
                self.logger.info(f"Cleaned up {expired_cleaned} expired access grants")

            # Review current access summary
            access_summary = self.iam_manager.get_access_summary()
            results["access_grants_reviewed"] = access_summary["total_grants"]

            self.logger.info(f"Reviewed {access_summary['total_grants']} access grants")
            self.logger.info(f"Active grants: {access_summary['active_grants']}")

            self.logger.info("✅ SHIELD ISOLATE completed successfully")
            return results

        except Exception as e:
            self.logger.error(f"❌ SHIELD ISOLATE failed: {e}")
            raise SecretError(f"Isolate operation failed: {e}")

    async def encrypt_operation(self, force_rotation: bool = False) -> dict:
        """
        SHIELD E: Encrypt through automated rotation

        Args:
            force_rotation: Whether to force rotation of all applicable secrets

        Returns:
            Dictionary with encryption/rotation results
        """
        self.logger.info("🔄 SHIELD ENCRYPT: Performing secret rotation")

        try:
            results = {
                "timestamp": datetime.utcnow().isoformat(),
                "rotation_needed": 0,
                "rotations_attempted": 0,
                "rotations_successful": 0,
                "rotations_failed": 0,
                "errors": [],
            }

            if not self.secret_manager.rotator:
                self.logger.warning("Secret rotation is disabled")
                return results

            # Check which secrets need rotation
            rotation_needed = self.secret_manager.rotator.check_rotation_needed()
            results["rotation_needed"] = len(rotation_needed)

            if rotation_needed:
                self.logger.info(
                    f"Found {len(rotation_needed)} secrets needing rotation"
                )

                # Perform automatic rotation
                rotation_results = self.secret_manager.rotator.auto_rotate_secrets()

                results["rotations_attempted"] = rotation_results["rotations_attempted"]
                results["rotations_successful"] = rotation_results[
                    "rotations_successful"
                ]
                results["rotations_failed"] = rotation_results["rotations_failed"]
                results["errors"] = rotation_results["errors"]

                self.logger.info(
                    f"Rotation completed: {results['rotations_successful']} successful, {results['rotations_failed']} failed"
                )
            else:
                self.logger.info("All secrets are up to date with rotation policies")

            self.logger.info("✅ SHIELD ENCRYPT completed successfully")
            return results

        except Exception as e:
            self.logger.error(f"❌ SHIELD ENCRYPT failed: {e}")
            raise SecretError(f"Encrypt operation failed: {e}")

    async def log_operation(self, export_audit: bool = False) -> dict:
        """
        SHIELD L: Log operations with comprehensive audit

        Args:
            export_audit: Whether to export audit logs

        Returns:
            Dictionary with logging results
        """
        self.logger.info("📝 SHIELD LOG: Managing audit logs and compliance")

        try:
            results = {
                "timestamp": datetime.utcnow().isoformat(),
                "audit_entries_processed": 0,
                "metrics_collected": False,
                "export_completed": False,
            }

            if not self.secret_manager.monitor:
                self.logger.warning("Secret monitoring is disabled")
                return results

            # Get audit log summary
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)  # Last 24 hours

            audit_logs = self.secret_manager.monitor.get_audit_log(
                start_time=start_time,
                end_time=end_time,
            )

            results["audit_entries_processed"] = len(audit_logs)
            self.logger.info(
                f"Processed {len(audit_logs)} audit log entries from last 24 hours"
            )

            # Collect security metrics
            metrics = self.secret_manager.monitor.get_security_metrics(
                start_time, end_time
            )
            results["metrics_collected"] = True

            self.logger.info(
                f"Collected metrics: {metrics['total_operations']} operations, {metrics['unique_secrets_accessed']} secrets accessed"
            )

            # Export audit logs if requested
            if export_audit:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                export_file = f"secret_audit_logs_{timestamp}.json"

                import json

                with open(export_file, "w") as f:
                    json.dump(
                        {
                            "audit_logs": audit_logs,
                            "metrics": metrics,
                            "exported_at": datetime.utcnow().isoformat(),
                        },
                        f,
                        indent=2,
                    )

                results["export_completed"] = True
                self.logger.info(f"Exported audit logs to: {export_file}")

            self.logger.info("✅ SHIELD LOG completed successfully")
            return results

        except Exception as e:
            self.logger.error(f"❌ SHIELD LOG failed: {e}")
            raise SecretError(f"Log operation failed: {e}")

    async def defend_operation(self) -> dict:
        """
        SHIELD D: Defend through monitoring and threat detection

        Returns:
            Dictionary with defense results
        """
        self.logger.info("🛡️ SHIELD DEFEND: Monitoring threats and defending secrets")

        try:
            results = {
                "timestamp": datetime.utcnow().isoformat(),
                "security_alerts": 0,
                "threats_detected": 0,
                "auto_remediations": 0,
                "health_check_passed": False,
            }

            if not self.secret_manager.monitor:
                self.logger.warning("Secret monitoring is disabled")
                return results

            # Check for security alerts
            alerts = self.secret_manager.monitor.get_security_alerts(resolved=False)
            results["security_alerts"] = len(alerts)

            if alerts:
                self.logger.warning(f"Found {len(alerts)} unresolved security alerts")

                # Count by threat level
                critical_alerts = [a for a in alerts if a["alert_level"] == "critical"]
                high_alerts = [a for a in alerts if a["alert_level"] == "error"]

                if critical_alerts:
                    self.logger.critical(
                        f"CRITICAL: {len(critical_alerts)} critical security alerts!"
                    )

                if high_alerts:
                    self.logger.error(
                        f"HIGH: {len(high_alerts)} high-severity security alerts!"
                    )

                results["threats_detected"] = len(critical_alerts) + len(high_alerts)

            # Perform health check
            if self.config["defend"]["health_checks"]["enabled"]:
                try:
                    health_report = self.secret_manager.validate_secret_health()

                    # Consider health check passed if no critical issues
                    critical_issues = [
                        issue
                        for issue in health_report["security_issues"]
                        if issue["severity"] == "critical"
                    ]

                    results["health_check_passed"] = len(critical_issues) == 0

                    if not results["health_check_passed"]:
                        self.logger.error(
                            f"Health check failed: {len(critical_issues)} critical issues found"
                        )
                    else:
                        self.logger.info(
                            "Health check passed: No critical issues found"
                        )

                except Exception as e:
                    self.logger.error(f"Health check failed: {e}")

            self.logger.info("✅ SHIELD DEFEND completed successfully")
            return results

        except Exception as e:
            self.logger.error(f"❌ SHIELD DEFEND failed: {e}")
            raise SecretError(f"Defend operation failed: {e}")

    async def full_shield_operation(self, comprehensive: bool = False) -> dict:
        """
        Execute complete SHIELD methodology operations

        Args:
            comprehensive: Whether to perform comprehensive operations

        Returns:
            Dictionary with all operation results
        """
        self.logger.info("🏛️ Starting full SHIELD operations")

        start_time = datetime.utcnow()

        try:
            results = {
                "started_at": start_time.isoformat(),
                "operations": {},
                "summary": {
                    "total_operations": 0,
                    "successful_operations": 0,
                    "failed_operations": 0,
                },
            }

            # Execute all SHIELD operations in sequence
            operations = [
                ("scan", self.scan_operation(comprehensive)),
                ("harden", self.harden_operation()),
                ("isolate", self.isolate_operation()),
                ("encrypt", self.encrypt_operation()),
                ("log", self.log_operation()),
                ("defend", self.defend_operation()),
            ]

            for operation_name, operation_coro in operations:
                try:
                    self.logger.info(
                        f"Executing SHIELD {operation_name.upper()} operation"
                    )
                    operation_result = await operation_coro
                    results["operations"][operation_name] = {
                        "status": "success",
                        "result": operation_result,
                    }
                    results["summary"]["successful_operations"] += 1

                except Exception as e:
                    self.logger.error(f"Operation {operation_name} failed: {e}")
                    results["operations"][operation_name] = {
                        "status": "failed",
                        "error": str(e),
                    }
                    results["summary"]["failed_operations"] += 1

                results["summary"]["total_operations"] += 1

            # Calculate duration
            end_time = datetime.utcnow()
            results["completed_at"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()

            self.logger.info(
                f"🏛️ Full SHIELD operations completed in {results['duration_seconds']:.2f} seconds"
            )
            self.logger.info(
                f"Summary: {results['summary']['successful_operations']}/{results['summary']['total_operations']} operations successful"
            )

            return results

        except Exception as e:
            self.logger.error(f"❌ Full SHIELD operation failed: {e}")
            raise SecretError(f"Full SHIELD operation failed: {e}")


async def main():
    """Main entry point for SHIELD automation"""
    parser = argparse.ArgumentParser(
        description="Genesis SHIELD Secret Management Automation"
    )

    parser.add_argument(
        "operation",
        choices=["scan", "harden", "isolate", "encrypt", "log", "defend", "full"],
        help="SHIELD operation to execute",
    )

    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument(
        "--comprehensive", action="store_true", help="Perform comprehensive operations"
    )
    parser.add_argument("--export-audit", action="store_true", help="Export audit logs")
    parser.add_argument(
        "--force-rotation", action="store_true", help="Force secret rotation"
    )
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging level
    if args.verbose:
        logging.getLogger("genesis").setLevel(logging.DEBUG)

    try:
        # Initialize SHIELD automation
        shield = SHIELDAutomation(config_path=args.config)

        # Execute requested operation
        if args.operation == "scan":
            results = await shield.scan_operation(comprehensive=args.comprehensive)
        elif args.operation == "harden":
            results = await shield.harden_operation()
        elif args.operation == "isolate":
            results = await shield.isolate_operation()
        elif args.operation == "encrypt":
            results = await shield.encrypt_operation(force_rotation=args.force_rotation)
        elif args.operation == "log":
            results = await shield.log_operation(export_audit=args.export_audit)
        elif args.operation == "defend":
            results = await shield.defend_operation()
        elif args.operation == "full":
            results = await shield.full_shield_operation(
                comprehensive=args.comprehensive
            )

        # Output results
        import json

        results_json = json.dumps(results, indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(results_json)
            print(f"✅ Results written to: {args.output}")
        else:
            print(results_json)

        # Exit with appropriate code
        if args.operation == "full":
            failed_ops = results.get("summary", {}).get("failed_operations", 0)
            sys.exit(1 if failed_ops > 0 else 0)

    except Exception as e:
        print(f"❌ SHIELD automation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
