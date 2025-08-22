#!/usr/bin/env python3

"""
Self-Healing System for Universal Project Platform
Advanced AI automation for automatic issue detection and resolution
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add the lib directory to the path for common utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "python"))


@dataclass
class HealingAction:
    """Represents a self-healing action"""

    id: str
    trigger: str  # What triggered this action
    action_type: str  # 'fix', 'optimize', 'alert', 'rollback'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    automated: bool  # Whether this can be done automatically
    commands: List[str]  # Commands to execute
    validation_commands: List[str]  # Commands to validate success
    rollback_commands: List[str]  # Commands to rollback if needed
    max_retries: int = 3
    timeout: int = 300  # 5 minutes default


@dataclass
class HealingResult:
    """Result of a healing action"""

    action_id: str
    success: bool
    timestamp: str
    execution_time: float
    output: str
    error: Optional[str] = None
    retries_used: int = 0
    validation_passed: bool = False


class SelfHealingEngine:
    """Main self-healing engine that monitors and automatically fixes issues"""

    def __init__(self, project_name: str = None, project_path: str = None):
        self.project_name = project_name
        self.project_path = project_path
        self.logger = self._setup_logging()
        self.healing_history = []
        self.monitoring_active = False
        self.monitoring_thread = None
        self.healing_actions = self._load_healing_actions()
        self.auto_heal_enabled = True
        self.healing_lock = threading.Lock()

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the self-healing engine"""
        logger = logging.getLogger(f"self_healing.{self.project_name or 'system'}")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _load_healing_actions(self) -> Dict[str, HealingAction]:
        """Load predefined healing actions"""
        actions = {}

        # Infrastructure healing actions
        actions["fix_docker_permission"] = HealingAction(
            id="fix_docker_permission",
            trigger="docker_permission_denied",
            action_type="fix",
            severity="medium",
            description="Fix Docker permission issues",
            automated=True,
            commands=["sudo usermod -aG docker $USER", "sudo systemctl restart docker"],
            validation_commands=["docker version"],
            rollback_commands=[],
        )

        actions["fix_disk_space"] = HealingAction(
            id="fix_disk_space",
            trigger="low_disk_space",
            action_type="fix",
            severity="high",
            description="Clean up disk space automatically",
            automated=True,
            commands=[
                "docker system prune -f",
                "sudo apt-get clean",
                "sudo journalctl --vacuum-time=7d",
            ],
            validation_commands=['df -h | grep -v "100%"'],
            rollback_commands=[],
        )

        actions["restart_failed_service"] = HealingAction(
            id="restart_failed_service",
            trigger="service_failure",
            action_type="fix",
            severity="high",
            description="Restart failed systemd services",
            automated=True,
            commands=["sudo systemctl restart {service_name}"],
            validation_commands=["sudo systemctl is-active {service_name}"],
            rollback_commands=[],
        )

        # Development environment healing
        actions["fix_python_dependencies"] = HealingAction(
            id="fix_python_dependencies",
            trigger="import_error",
            action_type="fix",
            severity="medium",
            description="Install missing Python dependencies",
            automated=True,
            commands=["pip install -r requirements.txt", "pip install --upgrade pip"],
            validation_commands=['python -c "import sys; print(sys.version)"'],
            rollback_commands=[],
        )

        actions["fix_node_dependencies"] = HealingAction(
            id="fix_node_dependencies",
            trigger="module_not_found",
            action_type="fix",
            severity="medium",
            description="Install missing Node.js dependencies",
            automated=True,
            commands=["npm install", "npm audit fix"],
            validation_commands=["npm list --depth=0"],
            rollback_commands=[],
        )

        # Security healing
        actions["rotate_expired_certificates"] = HealingAction(
            id="rotate_expired_certificates",
            trigger="certificate_expired",
            action_type="fix",
            severity="critical",
            description="Rotate expired SSL certificates",
            automated=False,  # Requires manual intervention for security
            commands=["certbot renew --dry-run", "certbot renew"],
            validation_commands=[
                'openssl x509 -in /etc/ssl/certs/cert.pem -text -noout | grep "Not After"'
            ],
            rollback_commands=[],
        )

        actions["fix_security_vulnerability"] = HealingAction(
            id="fix_security_vulnerability",
            trigger="security_scan_failed",
            action_type="fix",
            severity="critical",
            description="Update packages with security vulnerabilities",
            automated=True,
            commands=[
                "sudo apt-get update",
                "sudo apt-get upgrade -y",
                "npm audit fix",
                "pip install --upgrade -r requirements.txt",
            ],
            validation_commands=["npm audit", "pip check"],
            rollback_commands=[],
        )

        # Performance healing
        actions["optimize_memory_usage"] = HealingAction(
            id="optimize_memory_usage",
            trigger="high_memory_usage",
            action_type="optimize",
            severity="medium",
            description="Optimize memory usage",
            automated=True,
            commands=[
                "docker system prune -f",
                "sync && echo 3 > /proc/sys/vm/drop_caches",
            ],
            validation_commands=["free -h"],
            rollback_commands=[],
        )

        actions["restart_high_cpu_process"] = HealingAction(
            id="restart_high_cpu_process",
            trigger="high_cpu_usage",
            action_type="fix",
            severity="medium",
            description="Restart processes using excessive CPU",
            automated=True,
            commands=["sudo systemctl restart {process_name}"],
            validation_commands=["ps aux | grep {process_name} | grep -v grep"],
            rollback_commands=[],
        )

        # Database healing
        actions["repair_database_corruption"] = HealingAction(
            id="repair_database_corruption",
            trigger="database_corruption",
            action_type="fix",
            severity="critical",
            description="Repair database corruption",
            automated=False,  # Requires careful manual intervention
            commands=[
                "sudo systemctl stop postgresql",
                "sudo -u postgres pg_resetwal /var/lib/postgresql/data",
                "sudo systemctl start postgresql",
            ],
            validation_commands=['sudo -u postgres psql -c "SELECT version();"'],
            rollback_commands=[
                "sudo systemctl stop postgresql",
                "sudo -u postgres pg_restore /backup/latest_backup.sql",
                "sudo systemctl start postgresql",
            ],
        )

        return actions

    def start_monitoring(self, interval: int = 60):
        """Start continuous monitoring for issues"""
        if self.monitoring_active:
            self.logger.warning("Monitoring is already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, args=(interval,), daemon=True
        )
        self.monitoring_thread.start()
        self.logger.info(f"Started self-healing monitoring with {interval}s interval")

    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        self.logger.info("Stopped self-healing monitoring")

    def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self._check_system_health()
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)

    def _check_system_health(self):
        """Check system health and trigger healing actions if needed"""
        health_checks = [
            self._check_disk_space,
            self._check_memory_usage,
            self._check_cpu_usage,
            self._check_service_status,
            self._check_docker_health,
            self._check_database_health,
            self._check_security_status,
            self._check_application_health,
        ]

        for check in health_checks:
            try:
                issues = check()
                for issue in issues:
                    self._trigger_healing_action(issue)
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")

    def _check_disk_space(self) -> List[Dict[str, Any]]:
        """Check disk space and return issues if found"""
        issues = []

        try:
            result = subprocess.run(
                ["df", "-h"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        usage_str = parts[4].rstrip("%")
                        if usage_str.isdigit():
                            usage = int(usage_str)
                            if usage > 90:
                                issues.append(
                                    {
                                        "trigger": "low_disk_space",
                                        "severity": "high" if usage > 95 else "medium",
                                        "details": f"Disk usage at {usage}% on {parts[5]}",
                                        "filesystem": parts[5],
                                    }
                                )
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")

        return issues

    def _check_memory_usage(self) -> List[Dict[str, Any]]:
        """Check memory usage and return issues if found"""
        issues = []

        try:
            result = subprocess.run(
                ["free", "-m"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                memory_line = lines[1]  # Memory line
                parts = memory_line.split()

                if len(parts) >= 3:
                    total = int(parts[1])
                    used = int(parts[2])
                    usage_percent = (used / total) * 100

                    if usage_percent > 90:
                        issues.append(
                            {
                                "trigger": "high_memory_usage",
                                "severity": "high" if usage_percent > 95 else "medium",
                                "details": f"Memory usage at {usage_percent:.1f}%",
                                "usage_percent": usage_percent,
                            }
                        )
        except Exception as e:
            self.logger.warning(f"Could not check memory usage: {e}")

        return issues

    def _check_cpu_usage(self) -> List[Dict[str, Any]]:
        """Check CPU usage and return issues if found"""
        issues = []

        try:
            # Get 1-minute load average
            result = subprocess.run(
                ["uptime"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if "load average:" in output:
                    load_part = output.split("load average:")[1].strip()
                    load_values = load_part.split(",")
                    if load_values:
                        load_1min = float(load_values[0].strip())

                        # Get number of CPU cores
                        cpu_count_result = subprocess.run(
                            ["nproc"], capture_output=True, text=True, timeout=5
                        )

                        if cpu_count_result.returncode == 0:
                            cpu_count = int(cpu_count_result.stdout.strip())
                            load_ratio = load_1min / cpu_count

                            if load_ratio > 2.0:  # Load more than 2x CPU cores
                                issues.append(
                                    {
                                        "trigger": "high_cpu_usage",
                                        "severity": (
                                            "high" if load_ratio > 3.0 else "medium"
                                        ),
                                        "details": f"High CPU load: {load_1min} (ratio: {load_ratio:.2f})",
                                        "load_average": load_1min,
                                        "load_ratio": load_ratio,
                                    }
                                )
        except Exception as e:
            self.logger.warning(f"Could not check CPU usage: {e}")

        return issues

    def _check_service_status(self) -> List[Dict[str, Any]]:
        """Check status of critical services"""
        issues = []

        critical_services = ["docker", "postgresql", "nginx", "redis-server"]

        for service in critical_services:
            try:
                result = subprocess.run(
                    ["sudo", "systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    issues.append(
                        {
                            "trigger": "service_failure",
                            "severity": "high",
                            "details": f"Service {service} is not active",
                            "service_name": service,
                        }
                    )
            except Exception:
                # Service might not be installed, which is okay
                continue

        return issues

    def _check_docker_health(self) -> List[Dict[str, Any]]:
        """Check Docker daemon health"""
        issues = []

        try:
            result = subprocess.run(
                ["docker", "version"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                if "permission denied" in result.stderr.lower():
                    issues.append(
                        {
                            "trigger": "docker_permission_denied",
                            "severity": "medium",
                            "details": "Docker permission denied - user not in docker group",
                        }
                    )
                else:
                    issues.append(
                        {
                            "trigger": "docker_daemon_failed",
                            "severity": "high",
                            "details": "Docker daemon is not responding",
                        }
                    )
        except Exception:
            # Docker might not be installed
            pass

        return issues

    def _check_database_health(self) -> List[Dict[str, Any]]:
        """Check database health"""
        issues = []

        # Check PostgreSQL if available
        try:
            result = subprocess.run(
                ["sudo", "-u", "postgres", "psql", "-c", "SELECT version();"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                issues.append(
                    {
                        "trigger": "database_connection_failed",
                        "severity": "high",
                        "details": "Cannot connect to PostgreSQL database",
                    }
                )
        except Exception:
            # PostgreSQL might not be installed
            pass

        return issues

    def _check_security_status(self) -> List[Dict[str, Any]]:
        """Check security status"""
        issues = []

        # Check for security updates
        try:
            result = subprocess.run(
                ["apt", "list", "--upgradable"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                output = result.stdout
                if "security" in output.lower():
                    security_updates = len(
                        [
                            line
                            for line in output.split("\n")
                            if "security" in line.lower()
                        ]
                    )
                    if security_updates > 0:
                        issues.append(
                            {
                                "trigger": "security_updates_available",
                                "severity": "medium",
                                "details": f"{security_updates} security updates available",
                                "update_count": security_updates,
                            }
                        )
        except Exception:
            # apt might not be available on non-Debian systems
            pass

        return issues

    def _check_application_health(self) -> List[Dict[str, Any]]:
        """Check application-specific health"""
        issues = []

        if self.project_path and os.path.exists(self.project_path):
            # Check if requirements.txt dependencies are satisfied
            requirements_file = os.path.join(self.project_path, "requirements.txt")
            if os.path.exists(requirements_file):
                try:
                    result = subprocess.run(
                        ["pip", "check"],
                        cwd=self.project_path,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if result.returncode != 0:
                        issues.append(
                            {
                                "trigger": "dependency_conflict",
                                "severity": "medium",
                                "details": "Python dependency conflicts detected",
                                "pip_check_output": result.stdout,
                            }
                        )
                except Exception:
                    pass

            # Check package.json if it exists
            package_file = os.path.join(self.project_path, "package.json")
            if os.path.exists(package_file):
                try:
                    result = subprocess.run(
                        ["npm", "audit"],
                        cwd=self.project_path,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if result.returncode != 0:
                        issues.append(
                            {
                                "trigger": "npm_vulnerabilities",
                                "severity": "medium",
                                "details": "npm security vulnerabilities detected",
                                "audit_output": result.stdout,
                            }
                        )
                except Exception:
                    pass

        return issues

    def _trigger_healing_action(self, issue: Dict[str, Any]):
        """Trigger appropriate healing action for an issue"""
        trigger = issue.get("trigger")

        if trigger in self.healing_actions:
            action = self.healing_actions[trigger]

            if action.automated and self.auto_heal_enabled:
                self.logger.info(f"Triggering automated healing action: {action.id}")
                result = self.execute_healing_action(action, issue)

                if result.success:
                    self.logger.info(
                        f"Healing action {action.id} completed successfully"
                    )
                else:
                    self.logger.error(
                        f"Healing action {action.id} failed: {result.error}"
                    )
            else:
                self.logger.warning(
                    f"Manual intervention required for: {action.description}"
                )
                # Could send alert/notification here
        else:
            self.logger.warning(f"No healing action defined for trigger: {trigger}")

    def execute_healing_action(
        self, action: HealingAction, issue: Dict[str, Any] = None
    ) -> HealingResult:
        """Execute a healing action"""
        with self.healing_lock:
            start_time = time.time()
            result = HealingResult(
                action_id=action.id,
                success=False,
                timestamp=datetime.now().isoformat(),
                execution_time=0.0,
                output="",
                retries_used=0,
            )

            self.logger.info(f"Executing healing action: {action.id}")

            # Substitute variables in commands if issue provides context
            commands = action.commands.copy()
            validation_commands = action.validation_commands.copy()
            rollback_commands = action.rollback_commands.copy()

            if issue:
                for i, cmd in enumerate(commands):
                    for key, value in issue.items():
                        commands[i] = cmd.replace(f"{{{key}}}", str(value))

                for i, cmd in enumerate(validation_commands):
                    for key, value in issue.items():
                        validation_commands[i] = cmd.replace(f"{{{key}}}", str(value))

            # Execute commands with retries
            for attempt in range(action.max_retries):
                try:
                    result.retries_used = attempt

                    # Execute healing commands
                    for cmd in commands:
                        self.logger.debug(f"Executing command: {cmd}")

                        cmd_result = subprocess.run(
                            cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=action.timeout,
                            cwd=self.project_path,
                        )

                        result.output += f"Command: {cmd}\n"
                        result.output += f"Output: {cmd_result.stdout}\n"

                        if cmd_result.returncode != 0:
                            result.error = (
                                f"Command failed: {cmd}\nError: {cmd_result.stderr}"
                            )
                            self.logger.warning(
                                f"Command failed (attempt {attempt + 1}): {cmd}"
                            )
                            break

                    else:
                        # All commands succeeded, now validate
                        validation_success = True

                        for cmd in validation_commands:
                            self.logger.debug(f"Validating with command: {cmd}")

                            val_result = subprocess.run(
                                cmd,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=30,
                                cwd=self.project_path,
                            )

                            if val_result.returncode != 0:
                                validation_success = False
                                result.error = f"Validation failed: {cmd}\nError: {val_result.stderr}"
                                break

                        if validation_success:
                            result.success = True
                            result.validation_passed = True
                            break
                        else:
                            self.logger.warning(
                                f"Validation failed (attempt {attempt + 1})"
                            )

                except subprocess.TimeoutExpired:
                    result.error = (
                        f"Healing action timed out after {action.timeout} seconds"
                    )
                    self.logger.error(f"Healing action {action.id} timed out")
                except Exception as e:
                    result.error = f"Unexpected error: {str(e)}"
                    self.logger.error(
                        f"Unexpected error in healing action {action.id}: {e}"
                    )

                # If not successful and not the last attempt, wait before retry
                if not result.success and attempt < action.max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff

            # If all attempts failed and we have rollback commands, execute them
            if not result.success and rollback_commands:
                self.logger.warning(
                    f"Healing action {action.id} failed, attempting rollback"
                )

                try:
                    for cmd in rollback_commands:
                        subprocess.run(
                            cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=action.timeout,
                            cwd=self.project_path,
                        )
                    self.logger.info(f"Rollback completed for {action.id}")
                except Exception as e:
                    self.logger.error(f"Rollback failed for {action.id}: {e}")

            result.execution_time = time.time() - start_time
            self.healing_history.append(result)

            return result

    def get_healing_history(self, limit: int = 50) -> List[HealingResult]:
        """Get recent healing history"""
        return self.healing_history[-limit:]

    def get_available_actions(self) -> Dict[str, HealingAction]:
        """Get all available healing actions"""
        return self.healing_actions.copy()

    def add_custom_action(self, action: HealingAction):
        """Add a custom healing action"""
        self.healing_actions[action.id] = action
        self.logger.info(f"Added custom healing action: {action.id}")

    def enable_auto_healing(self):
        """Enable automatic healing"""
        self.auto_heal_enabled = True
        self.logger.info("Automatic healing enabled")

    def disable_auto_healing(self):
        """Disable automatic healing"""
        self.auto_heal_enabled = False
        self.logger.info("Automatic healing disabled")

    def force_healing_action(
        self, action_id: str, issue_context: Dict[str, Any] = None
    ) -> HealingResult:
        """Force execution of a specific healing action"""
        if action_id not in self.healing_actions:
            raise ValueError(f"Unknown healing action: {action_id}")

        action = self.healing_actions[action_id]
        return self.execute_healing_action(action, issue_context)

    def generate_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_name": self.project_name,
            "monitoring_active": self.monitoring_active,
            "auto_heal_enabled": self.auto_heal_enabled,
            "system_health": {},
            "recent_healing_actions": [],
            "available_actions": len(self.healing_actions),
            "recommendations": [],
        }

        # Run all health checks
        all_issues = []
        health_checks = [
            ("disk_space", self._check_disk_space),
            ("memory_usage", self._check_memory_usage),
            ("cpu_usage", self._check_cpu_usage),
            ("service_status", self._check_service_status),
            ("docker_health", self._check_docker_health),
            ("database_health", self._check_database_health),
            ("security_status", self._check_security_status),
            ("application_health", self._check_application_health),
        ]

        for check_name, check_func in health_checks:
            try:
                issues = check_func()
                report["system_health"][check_name] = {
                    "status": "healthy" if not issues else "issues_found",
                    "issues": issues,
                }
                all_issues.extend(issues)
            except Exception as e:
                report["system_health"][check_name] = {
                    "status": "check_failed",
                    "error": str(e),
                }

        # Add recent healing actions
        recent_actions = self.get_healing_history(10)
        report["recent_healing_actions"] = [
            {
                "action_id": action.action_id,
                "success": action.success,
                "timestamp": action.timestamp,
                "execution_time": action.execution_time,
            }
            for action in recent_actions
        ]

        # Generate recommendations
        if all_issues:
            report["recommendations"] = [
                f"Found {len(all_issues)} issues that need attention",
                "Consider enabling automatic healing for automated fixes",
                "Review healing history for patterns",
            ]

            critical_issues = [
                issue for issue in all_issues if issue.get("severity") == "critical"
            ]
            if critical_issues:
                report["recommendations"].insert(
                    0,
                    f"URGENT: {len(critical_issues)} critical issues require immediate attention",
                )
        else:
            report["recommendations"] = ["System appears healthy"]

        return report


def main():
    """Main entry point for the self-healing CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="Self-Healing System for Projects")
    parser.add_argument(
        "command",
        choices=["monitor", "check", "heal", "report"],
        help="Command to execute",
    )
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--project-path", help="Project path")
    parser.add_argument("--action", help="Specific healing action to execute")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Monitoring interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--auto-heal", action="store_true", help="Enable automatic healing"
    )
    parser.add_argument(
        "--no-auto-heal", action="store_true", help="Disable automatic healing"
    )

    args = parser.parse_args()

    # Initialize self-healing engine
    engine = SelfHealingEngine(args.project, args.project_path)

    if args.auto_heal:
        engine.enable_auto_healing()
    elif args.no_auto_heal:
        engine.disable_auto_healing()

    if args.command == "monitor":
        print(f"Starting self-healing monitoring for {args.project or 'system'}")
        print(f"Monitoring interval: {args.interval} seconds")
        print("Press Ctrl+C to stop")

        try:
            engine.start_monitoring(args.interval)
            # Keep the main thread alive
            while engine.monitoring_active:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
            engine.stop_monitoring()

    elif args.command == "check":
        print(f"Running health check for {args.project or 'system'}")
        engine._check_system_health()
        print("Health check completed")

    elif args.command == "heal":
        if not args.action:
            print("Error: --action is required for heal command")
            sys.exit(1)

        print(f"Executing healing action: {args.action}")
        try:
            result = engine.force_healing_action(args.action)
            print(f"Result: {'Success' if result.success else 'Failed'}")
            print(f"Execution time: {result.execution_time:.2f} seconds")
            if result.error:
                print(f"Error: {result.error}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.command == "report":
        print(f"Generating health report for {args.project or 'system'}")
        report = engine.generate_health_report()
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
