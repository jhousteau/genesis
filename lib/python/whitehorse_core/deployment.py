"""
Deployment Manager Module

Provides comprehensive deployment management with GCP integration,
multi-environment orchestration, and rollback capabilities.
"""

import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .config import get_config
from .errors import ExternalServiceError, ValidationError
from .logging import get_logger
from .registry import ProjectRegistry

logger = get_logger(__name__)


class DeploymentStatus(Enum):
    """Deployment status values."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"


class DeploymentStrategy(Enum):
    """Deployment strategy types."""

    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"


@dataclass
class DeploymentTarget:
    """Deployment target configuration."""

    name: str
    environment: str
    gcp_project: str
    region: str
    cluster: Optional[str] = None
    namespace: Optional[str] = None
    service_account: Optional[str] = None
    config_overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentJob:
    """Deployment job information."""

    id: str
    project_name: str
    target: DeploymentTarget
    strategy: DeploymentStrategy
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    logs: List[str] = field(default_factory=list)
    rollback_info: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeploymentManager:
    """
    Central deployment manager for orchestrating deployments across environments.
    Integrates with GCP services and provides rollback capabilities.
    """

    def __init__(self, registry: Optional[ProjectRegistry] = None):
        """
        Initialize deployment manager.

        Args:
            registry: Project registry instance
        """
        self.config = get_config()
        self.registry = registry or ProjectRegistry()
        self.active_deployments: Dict[str, DeploymentJob] = {}
        self.deployment_history: List[DeploymentJob] = []
        self.deployment_lock = threading.Lock()
        self.deploy_scripts_path = self._find_deploy_scripts_path()

    def _find_deploy_scripts_path(self) -> str:
        """Find deployment scripts directory."""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "deploy"),
            "/opt/bootstrap/deploy",
            os.path.expanduser("~/.bootstrap/deploy"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)

        raise FileNotFoundError("Deploy scripts directory not found")

    def get_deployment_targets(self, project_name: str) -> List[DeploymentTarget]:
        """
        Get available deployment targets for a project.

        Args:
            project_name: Name of the project

        Returns:
            List of deployment targets
        """
        try:
            project = self.registry.get_project(project_name)
            if not project:
                raise ValidationError(f"Project {project_name} not found")

            environments = project.get("environments", {})
            targets = []

            for env_name, env_config in environments.items():
                target = DeploymentTarget(
                    name=f"{project_name}-{env_name}",
                    environment=env_name,
                    gcp_project=env_config.get("gcp_project", ""),
                    region=env_config.get("region", "us-central1"),
                    cluster=env_config.get("cluster"),
                    namespace=env_config.get("namespace"),
                    service_account=env_config.get("service_account"),
                    config_overrides=env_config.get("config_overrides", {}),
                )
                targets.append(target)

            return targets

        except Exception as e:
            logger.error(f"Failed to get deployment targets for {project_name}: {e}")
            raise ExternalServiceError(f"Failed to get deployment targets: {e}")

    def deploy(
        self,
        project_name: str,
        target: DeploymentTarget,
        strategy: DeploymentStrategy = DeploymentStrategy.ROLLING,
        wait_for_completion: bool = True,
        **kwargs,
    ) -> DeploymentJob:
        """
        Deploy project to target environment.

        Args:
            project_name: Name of the project to deploy
            target: Deployment target configuration
            strategy: Deployment strategy to use
            wait_for_completion: Whether to wait for deployment completion
            **kwargs: Additional deployment parameters

        Returns:
            DeploymentJob instance
        """
        import uuid

        deployment_id = str(uuid.uuid4())

        with self.deployment_lock:
            deployment_job = DeploymentJob(
                id=deployment_id,
                project_name=project_name,
                target=target,
                strategy=strategy,
                status=DeploymentStatus.PENDING,
                started_at=datetime.utcnow(),
            )

            self.active_deployments[deployment_id] = deployment_job

        logger.info(
            f"Starting deployment {deployment_id}",
            project=project_name,
            target=target.name,
            strategy=strategy.value,
        )

        try:
            # Validate deployment prerequisites
            self._validate_deployment(project_name, target)

            # Update status to running
            deployment_job.status = DeploymentStatus.RUNNING

            # Execute deployment based on strategy
            if strategy == DeploymentStrategy.ROLLING:
                self._execute_rolling_deployment(deployment_job, **kwargs)
            elif strategy == DeploymentStrategy.BLUE_GREEN:
                self._execute_blue_green_deployment(deployment_job, **kwargs)
            elif strategy == DeploymentStrategy.CANARY:
                self._execute_canary_deployment(deployment_job, **kwargs)
            elif strategy == DeploymentStrategy.RECREATE:
                self._execute_recreate_deployment(deployment_job, **kwargs)
            else:
                raise ValidationError(f"Unsupported deployment strategy: {strategy}")

            if wait_for_completion:
                self._wait_for_deployment_completion(deployment_job)

            return deployment_job

        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed: {e}")
            deployment_job.status = DeploymentStatus.FAILED
            deployment_job.completed_at = datetime.utcnow()
            deployment_job.logs.append(f"Deployment failed: {str(e)}")

            # Move to history
            with self.deployment_lock:
                if deployment_id in self.active_deployments:
                    del self.active_deployments[deployment_id]
                self.deployment_history.append(deployment_job)

            raise ExternalServiceError(f"Deployment failed: {e}")

    def _validate_deployment(self, project_name: str, target: DeploymentTarget) -> None:
        """Validate deployment prerequisites."""
        # Check if project exists
        project = self.registry.get_project(project_name)
        if not project:
            raise ValidationError(f"Project {project_name} not found")

        # Check if target environment is configured
        environments = project.get("environments", {})
        if target.environment not in environments:
            raise ValidationError(
                f"Environment {target.environment} not configured for project {project_name}"
            )

        # Check GCP project access
        if target.gcp_project:
            try:
                # This would check actual GCP access
                logger.info(f"Validating access to GCP project {target.gcp_project}")
            except Exception as e:
                raise ValidationError(
                    f"Cannot access GCP project {target.gcp_project}: {e}"
                )

    def _execute_rolling_deployment(
        self, deployment_job: DeploymentJob, **kwargs
    ) -> None:
        """Execute rolling deployment strategy."""
        try:
            rolling_script = os.path.join(
                self.deploy_scripts_path, "strategies", "rolling", "deploy-rolling.sh"
            )

            if not os.path.exists(rolling_script):
                raise FileNotFoundError("Rolling deployment script not found")

            # Prepare deployment command
            cmd = [
                "bash",
                rolling_script,
                deployment_job.project_name,
                deployment_job.target.environment,
                deployment_job.target.gcp_project,
                deployment_job.target.region,
            ]

            # Add optional parameters
            if deployment_job.target.cluster:
                cmd.extend(["--cluster", deployment_job.target.cluster])
            if deployment_job.target.namespace:
                cmd.extend(["--namespace", deployment_job.target.namespace])

            logger.info(f"Executing rolling deployment command: {' '.join(cmd)}")

            # Execute deployment
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
            )

            deployment_job.logs.extend(process.stdout.split("\n"))
            if process.stderr:
                deployment_job.logs.extend(process.stderr.split("\n"))

            if process.returncode == 0:
                deployment_job.status = DeploymentStatus.SUCCESS
                logger.info(
                    f"Rolling deployment {deployment_job.id} completed successfully"
                )
            else:
                deployment_job.status = DeploymentStatus.FAILED
                logger.error(
                    f"Rolling deployment {deployment_job.id} failed with exit code {process.returncode}"
                )

        except subprocess.TimeoutExpired:
            deployment_job.status = DeploymentStatus.FAILED
            deployment_job.logs.append("Deployment timed out after 30 minutes")
            logger.error(f"Rolling deployment {deployment_job.id} timed out")
        except Exception as e:
            deployment_job.status = DeploymentStatus.FAILED
            deployment_job.logs.append(f"Deployment error: {str(e)}")
            logger.error(f"Rolling deployment {deployment_job.id} error: {e}")

    def _execute_blue_green_deployment(
        self, deployment_job: DeploymentJob, **kwargs
    ) -> None:
        """Execute blue-green deployment strategy."""
        try:
            blue_green_script = os.path.join(
                self.deploy_scripts_path,
                "strategies",
                "blue-green",
                "deploy-blue-green.sh",
            )

            if not os.path.exists(blue_green_script):
                raise FileNotFoundError("Blue-green deployment script not found")

            # Store rollback information for blue-green
            deployment_job.rollback_info = {
                "strategy": "blue_green",
                "previous_version": kwargs.get("current_version"),
                "switch_timestamp": None,
            }

            cmd = [
                "bash",
                blue_green_script,
                deployment_job.project_name,
                deployment_job.target.environment,
                deployment_job.target.gcp_project,
                deployment_job.target.region,
            ]

            logger.info(f"Executing blue-green deployment command: {' '.join(cmd)}")

            process = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            deployment_job.logs.extend(process.stdout.split("\n"))
            if process.stderr:
                deployment_job.logs.extend(process.stderr.split("\n"))

            if process.returncode == 0:
                deployment_job.status = DeploymentStatus.SUCCESS
                deployment_job.rollback_info["switch_timestamp"] = (
                    datetime.utcnow().isoformat()
                )
                logger.info(
                    f"Blue-green deployment {deployment_job.id} completed successfully"
                )
            else:
                deployment_job.status = DeploymentStatus.FAILED
                logger.error(f"Blue-green deployment {deployment_job.id} failed")

        except Exception as e:
            deployment_job.status = DeploymentStatus.FAILED
            deployment_job.logs.append(f"Blue-green deployment error: {str(e)}")
            logger.error(f"Blue-green deployment {deployment_job.id} error: {e}")

    def _execute_canary_deployment(
        self, deployment_job: DeploymentJob, **kwargs
    ) -> None:
        """Execute canary deployment strategy."""
        try:
            canary_script = os.path.join(
                self.deploy_scripts_path, "strategies", "canary", "deploy-canary.sh"
            )

            if not os.path.exists(canary_script):
                raise FileNotFoundError("Canary deployment script not found")

            # Get canary configuration
            canary_percentage = kwargs.get("canary_percentage", 10)
            canary_duration = kwargs.get("canary_duration", 300)  # 5 minutes

            deployment_job.rollback_info = {
                "strategy": "canary",
                "canary_percentage": canary_percentage,
                "canary_duration": canary_duration,
                "promotion_timestamp": None,
            }

            cmd = [
                "bash",
                canary_script,
                deployment_job.project_name,
                deployment_job.target.environment,
                deployment_job.target.gcp_project,
                deployment_job.target.region,
                "--canary-percentage",
                str(canary_percentage),
                "--canary-duration",
                str(canary_duration),
            ]

            logger.info(f"Executing canary deployment command: {' '.join(cmd)}")

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout for canary
            )

            deployment_job.logs.extend(process.stdout.split("\n"))
            if process.stderr:
                deployment_job.logs.extend(process.stderr.split("\n"))

            if process.returncode == 0:
                deployment_job.status = DeploymentStatus.SUCCESS
                deployment_job.rollback_info["promotion_timestamp"] = (
                    datetime.utcnow().isoformat()
                )
                logger.info(
                    f"Canary deployment {deployment_job.id} completed successfully"
                )
            else:
                deployment_job.status = DeploymentStatus.FAILED
                logger.error(f"Canary deployment {deployment_job.id} failed")

        except Exception as e:
            deployment_job.status = DeploymentStatus.FAILED
            deployment_job.logs.append(f"Canary deployment error: {str(e)}")
            logger.error(f"Canary deployment {deployment_job.id} error: {e}")

    def _execute_recreate_deployment(
        self, deployment_job: DeploymentJob, **kwargs
    ) -> None:
        """Execute recreate deployment strategy."""
        try:
            # For recreate strategy, we use the general deployment runner
            deploy_runner = os.path.join(
                self.deploy_scripts_path, "strategies", "deploy-runner.sh"
            )

            if not os.path.exists(deploy_runner):
                raise FileNotFoundError("Deploy runner script not found")

            cmd = [
                "bash",
                deploy_runner,
                deployment_job.project_name,
                deployment_job.target.environment,
                deployment_job.target.gcp_project,
                "--strategy",
                "recreate",
            ]

            logger.info(f"Executing recreate deployment command: {' '.join(cmd)}")

            process = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            deployment_job.logs.extend(process.stdout.split("\n"))
            if process.stderr:
                deployment_job.logs.extend(process.stderr.split("\n"))

            if process.returncode == 0:
                deployment_job.status = DeploymentStatus.SUCCESS
                logger.info(
                    f"Recreate deployment {deployment_job.id} completed successfully"
                )
            else:
                deployment_job.status = DeploymentStatus.FAILED
                logger.error(f"Recreate deployment {deployment_job.id} failed")

        except Exception as e:
            deployment_job.status = DeploymentStatus.FAILED
            deployment_job.logs.append(f"Recreate deployment error: {str(e)}")
            logger.error(f"Recreate deployment {deployment_job.id} error: {e}")

    def _wait_for_deployment_completion(self, deployment_job: DeploymentJob) -> None:
        """Wait for deployment to complete."""
        max_wait_time = 3600  # 1 hour
        check_interval = 10  # 10 seconds
        waited_time = 0

        while (
            deployment_job.status == DeploymentStatus.RUNNING
            and waited_time < max_wait_time
        ):
            time.sleep(check_interval)
            waited_time += check_interval

            # Log progress
            if waited_time % 60 == 0:  # Every minute
                logger.info(
                    f"Deployment {deployment_job.id} still running",
                    elapsed_minutes=waited_time // 60,
                )

        if deployment_job.status == DeploymentStatus.RUNNING:
            logger.warning(
                f"Deployment {deployment_job.id} did not complete within {max_wait_time} seconds"
            )

        # Mark completion time
        deployment_job.completed_at = datetime.utcnow()

        # Move to history
        with self.deployment_lock:
            if deployment_job.id in self.active_deployments:
                del self.active_deployments[deployment_job.id]
            self.deployment_history.append(deployment_job)

    def rollback(
        self, deployment_id: str, target_version: Optional[str] = None
    ) -> DeploymentJob:
        """
        Rollback a deployment.

        Args:
            deployment_id: ID of deployment to rollback
            target_version: Optional specific version to rollback to

        Returns:
            DeploymentJob for rollback operation
        """
        import uuid

        # Find the deployment to rollback
        deployment_to_rollback = None

        # Check active deployments first
        if deployment_id in self.active_deployments:
            deployment_to_rollback = self.active_deployments[deployment_id]
        else:
            # Check deployment history
            for deployment in self.deployment_history:
                if deployment.id == deployment_id:
                    deployment_to_rollback = deployment
                    break

        if not deployment_to_rollback:
            raise ValidationError(f"Deployment {deployment_id} not found")

        if deployment_to_rollback.status != DeploymentStatus.SUCCESS:
            raise ValidationError(
                f"Cannot rollback deployment {deployment_id} with status {deployment_to_rollback.status}"
            )

        # Create rollback deployment job
        rollback_id = str(uuid.uuid4())
        rollback_job = DeploymentJob(
            id=rollback_id,
            project_name=deployment_to_rollback.project_name,
            target=deployment_to_rollback.target,
            strategy=deployment_to_rollback.strategy,
            status=DeploymentStatus.ROLLING_BACK,
            started_at=datetime.utcnow(),
            metadata={"rollback_from": deployment_id, "target_version": target_version},
        )

        with self.deployment_lock:
            self.active_deployments[rollback_id] = rollback_job

        logger.info(
            f"Starting rollback {rollback_id} for deployment {deployment_id}",
            project=rollback_job.project_name,
            target=rollback_job.target.name,
        )

        try:
            self._execute_rollback(rollback_job, deployment_to_rollback, target_version)

            rollback_job.completed_at = datetime.utcnow()

            # Move to history
            with self.deployment_lock:
                if rollback_id in self.active_deployments:
                    del self.active_deployments[rollback_id]
                self.deployment_history.append(rollback_job)

            return rollback_job

        except Exception as e:
            logger.error(f"Rollback {rollback_id} failed: {e}")
            rollback_job.status = DeploymentStatus.FAILED
            rollback_job.completed_at = datetime.utcnow()
            rollback_job.logs.append(f"Rollback failed: {str(e)}")

            with self.deployment_lock:
                if rollback_id in self.active_deployments:
                    del self.active_deployments[rollback_id]
                self.deployment_history.append(rollback_job)

            raise ExternalServiceError(f"Rollback failed: {e}")

    def _execute_rollback(
        self,
        rollback_job: DeploymentJob,
        original_deployment: DeploymentJob,
        target_version: Optional[str],
    ) -> None:
        """Execute rollback operation."""
        try:
            rollback_script = os.path.join(
                self.deploy_scripts_path,
                "rollback",
                "infrastructure",
                "rollback-infrastructure.sh",
            )

            if not os.path.exists(rollback_script):
                raise FileNotFoundError("Rollback script not found")

            cmd = [
                "bash",
                rollback_script,
                rollback_job.project_name,
                rollback_job.target.environment,
                rollback_job.target.gcp_project,
                "--deployment-id",
                original_deployment.id,
            ]

            if target_version:
                cmd.extend(["--target-version", target_version])

            if original_deployment.rollback_info:
                # Add strategy-specific rollback parameters
                strategy = original_deployment.rollback_info.get("strategy")
                if strategy:
                    cmd.extend(["--strategy", strategy])

            logger.info(f"Executing rollback command: {' '.join(cmd)}")

            process = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            rollback_job.logs.extend(process.stdout.split("\n"))
            if process.stderr:
                rollback_job.logs.extend(process.stderr.split("\n"))

            if process.returncode == 0:
                rollback_job.status = DeploymentStatus.SUCCESS
                logger.info(f"Rollback {rollback_job.id} completed successfully")
            else:
                rollback_job.status = DeploymentStatus.FAILED
                logger.error(
                    f"Rollback {rollback_job.id} failed with exit code {process.returncode}"
                )

        except Exception as e:
            rollback_job.status = DeploymentStatus.FAILED
            rollback_job.logs.append(f"Rollback error: {str(e)}")
            logger.error(f"Rollback {rollback_job.id} error: {e}")

    def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentJob]:
        """
        Get status of a deployment.

        Args:
            deployment_id: ID of deployment

        Returns:
            DeploymentJob or None if not found
        """
        # Check active deployments
        if deployment_id in self.active_deployments:
            return self.active_deployments[deployment_id]

        # Check deployment history
        for deployment in self.deployment_history:
            if deployment.id == deployment_id:
                return deployment

        return None

    def list_deployments(
        self,
        project_name: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[DeploymentStatus] = None,
        limit: int = 50,
    ) -> List[DeploymentJob]:
        """
        List deployments with optional filtering.

        Args:
            project_name: Filter by project name
            environment: Filter by environment
            status: Filter by status
            limit: Maximum number of deployments to return

        Returns:
            List of DeploymentJob instances
        """
        all_deployments = (
            list(self.active_deployments.values()) + self.deployment_history
        )

        # Apply filters
        filtered_deployments = []
        for deployment in all_deployments:
            if project_name and deployment.project_name != project_name:
                continue
            if environment and deployment.target.environment != environment:
                continue
            if status and deployment.status != status:
                continue

            filtered_deployments.append(deployment)

        # Sort by started_at descending and limit
        filtered_deployments.sort(key=lambda d: d.started_at, reverse=True)
        return filtered_deployments[:limit]

    def cancel_deployment(self, deployment_id: str) -> bool:
        """
        Cancel an active deployment.

        Args:
            deployment_id: ID of deployment to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        if deployment_id not in self.active_deployments:
            return False

        deployment = self.active_deployments[deployment_id]

        if deployment.status not in [
            DeploymentStatus.PENDING,
            DeploymentStatus.RUNNING,
        ]:
            return False

        try:
            # Update status
            deployment.status = DeploymentStatus.CANCELLED
            deployment.completed_at = datetime.utcnow()
            deployment.logs.append("Deployment cancelled by user")

            # Move to history
            with self.deployment_lock:
                del self.active_deployments[deployment_id]
                self.deployment_history.append(deployment)

            logger.info(f"Deployment {deployment_id} cancelled")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel deployment {deployment_id}: {e}")
            return False

    def get_deployment_logs(self, deployment_id: str) -> List[str]:
        """
        Get logs for a deployment.

        Args:
            deployment_id: ID of deployment

        Returns:
            List of log lines
        """
        deployment = self.get_deployment_status(deployment_id)
        if deployment:
            return deployment.logs
        return []

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on deployment manager.

        Returns:
            Health check results
        """
        try:
            health = {
                "status": "healthy",
                "deploy_scripts_path": self.deploy_scripts_path,
                "scripts_available": os.path.exists(self.deploy_scripts_path),
                "active_deployments": len(self.active_deployments),
                "total_deployments": len(self.deployment_history)
                + len(self.active_deployments),
                "deployment_strategies": {
                    "rolling": os.path.exists(
                        os.path.join(self.deploy_scripts_path, "strategies", "rolling")
                    ),
                    "blue_green": os.path.exists(
                        os.path.join(
                            self.deploy_scripts_path, "strategies", "blue-green"
                        )
                    ),
                    "canary": os.path.exists(
                        os.path.join(self.deploy_scripts_path, "strategies", "canary")
                    ),
                },
            }

            # Check for any failed deployments in last hour
            recent_failures = [
                d
                for d in self.deployment_history[-10:]  # Last 10 deployments
                if d.status == DeploymentStatus.FAILED
                and d.completed_at
                and (datetime.utcnow() - d.completed_at).total_seconds() < 3600
            ]

            if recent_failures:
                health["status"] = "degraded"
                health["recent_failures"] = len(recent_failures)

            return health

        except Exception as e:
            logger.error(f"Deployment manager health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "deploy_scripts_path": getattr(self, "deploy_scripts_path", None),
                "scripts_available": False,
            }
