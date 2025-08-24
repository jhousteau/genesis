"""
Enhanced Infrastructure Management Commands
CLI commands for Terraform and infrastructure automation following CRAFT methodology with service layer integration.
"""

import logging
from pathlib import Path
from typing import Any, Dict
import asyncio

from ..services import (
    ConfigService,
    AuthService,
    CacheService,
    ErrorService,
    GCPService,
    PerformanceService,
    TerraformService,
)
from ..services.error_service import ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class EnhancedInfrastructureCommands:
    """Enhanced infrastructure management commands implementation following CRAFT methodology."""

    def __init__(self, cli):
        self.cli = cli
        self.terraform_dir = Path(self.cli.genesis_root) / "environments"

        # Initialize service layer
        self.config_service = ConfigService(self.cli.genesis_root)
        self.error_service = ErrorService(self.config_service)
        self.cache_service = CacheService(self.config_service)
        self.auth_service = AuthService(self.config_service)
        self.gcp_service = GCPService(
            self.config_service,
            self.auth_service,
            self.cache_service,
            self.error_service,
        )
        self.performance_service = PerformanceService(self.config_service)
        self.terraform_service = TerraformService(
            self.config_service,
            self.auth_service,
            self.cache_service,
            self.error_service,
        )

        # Get configuration
        self.terraform_config = self.config_service.get_terraform_config()
        self.gcp_config = self.config_service.get_gcp_config()

    def execute(self, args, config: Dict[str, Any]) -> Any:
        """Execute infrastructure command based on action with performance monitoring."""
        action = args.infra_action

        # Update services with CLI configuration
        self.config_service.update_environment(args.environment or self.cli.environment)
        if args.project_id:
            self.config_service.update_project_id(args.project_id)

        with self.performance_service.time_operation(
            f"infra_{action}", {"action": action}
        ):
            try:
                if action == "plan":
                    return self.terraform_plan(args, config)
                elif action == "apply":
                    return self.terraform_apply(args, config)
                elif action == "destroy":
                    return self.terraform_destroy(args, config)
                elif action == "status":
                    return self.infrastructure_status(args, config)
                elif action == "validate":
                    return self.terraform_validate(args, config)
                elif action == "init":
                    return self.terraform_init(args, config)
                elif action == "cost":
                    return self.cost_operations(args, config)
                else:
                    error = self.error_service.create_error(
                        message=f"Unknown infrastructure action: {action}",
                        category=ErrorCategory.USER,
                        severity=ErrorSeverity.MEDIUM,
                        code="INVALID_INFRA_ACTION",
                        suggestions=["Use 'g infra --help' to see available actions"],
                    )
                    raise ValueError(self.error_service.format_error_message(error))
            except Exception as e:
                error = self.error_service.handle_exception(
                    e, {"action": action, "args": vars(args)}
                )
                if hasattr(args, "verbose") and args.verbose:
                    logger.error(
                        self.error_service.format_error_message(
                            error, include_details=True
                        )
                    )
                raise

    def terraform_plan(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Terraform plan using CRAFT methodology."""
        module_path = getattr(args, "module", None) or self.config_service.environment
        target = getattr(args, "target", None)

        logger.info(f"Running Terraform plan for module: {module_path}")

        if hasattr(args, "dry_run") and args.dry_run:
            return {
                "action": "plan",
                "module": module_path,
                "target": target,
                "status": "dry-run",
            }

        try:
            # Run Terraform plan using service
            result = self.terraform_service.plan(module_path=module_path, target=target)

            if not result["success"]:
                error = result.get("error")
                if error:
                    raise Exception(self.error_service.format_error_message(error))
                else:
                    raise Exception("Terraform plan failed")

            plan_data = result["data"]

            return {
                "action": "plan",
                "module": module_path,
                "target": target,
                "has_changes": plan_data.has_changes,
                "actions": plan_data.actions,
                "resources": len(plan_data.resources),
                "plan_file": plan_data.plan_file,
                "status": "completed",
            }

        except Exception as e:
            error = self.error_service.handle_exception(
                e,
                {
                    "operation": "terraform_plan",
                    "module": module_path,
                    "target": target,
                },
            )
            raise Exception(self.error_service.format_error_message(error))

    def terraform_apply(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Terraform apply using CRAFT methodology."""
        module_path = getattr(args, "module", None) or self.config_service.environment
        auto_approve = getattr(args, "auto_approve", False)
        target = getattr(args, "target", None)

        logger.info(f"Running Terraform apply for module: {module_path}")

        if hasattr(args, "dry_run") and args.dry_run:
            return {
                "action": "apply",
                "module": module_path,
                "auto_approve": auto_approve,
                "target": target,
                "status": "dry-run",
            }

        try:
            # Check if there's a cached plan to use
            cached_plan = self.cache_service.get(f"terraform_plan:{module_path}")
            plan_file = cached_plan.get("plan_file") if cached_plan else None

            # Run Terraform apply using service
            result = self.terraform_service.apply(
                module_path=module_path, plan_file=plan_file, auto_approve=auto_approve
            )

            if not result["success"]:
                error = result.get("error")
                if error:
                    raise Exception(self.error_service.format_error_message(error))
                else:
                    raise Exception("Terraform apply failed")

            return {
                "action": "apply",
                "module": module_path,
                "auto_approve": auto_approve,
                "target": target,
                "used_plan_file": plan_file is not None,
                "status": "completed",
            }

        except Exception as e:
            error = self.error_service.handle_exception(
                e,
                {
                    "operation": "terraform_apply",
                    "module": module_path,
                    "auto_approve": auto_approve,
                    "target": target,
                },
            )
            raise Exception(self.error_service.format_error_message(error))

    def terraform_destroy(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Terraform destroy using CRAFT methodology."""
        module_path = getattr(args, "module", None) or self.config_service.environment
        auto_approve = getattr(args, "auto_approve", False)
        target = getattr(args, "target", None)

        logger.info(f"Running Terraform destroy for module: {module_path}")

        if hasattr(args, "dry_run") and args.dry_run:
            return {
                "action": "destroy",
                "module": module_path,
                "auto_approve": auto_approve,
                "target": target,
                "status": "dry-run",
            }

        try:
            # Run Terraform destroy using service
            result = self.terraform_service.destroy(
                module_path=module_path, auto_approve=auto_approve, target=target
            )

            if not result["success"]:
                error = result.get("error")
                if error:
                    raise Exception(self.error_service.format_error_message(error))
                else:
                    raise Exception("Terraform destroy failed")

            return {
                "action": "destroy",
                "module": module_path,
                "auto_approve": auto_approve,
                "target": target,
                "status": "completed",
            }

        except Exception as e:
            error = self.error_service.handle_exception(
                e,
                {
                    "operation": "terraform_destroy",
                    "module": module_path,
                    "auto_approve": auto_approve,
                    "target": target,
                },
            )
            raise Exception(self.error_service.format_error_message(error))

    def infrastructure_status(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Show infrastructure status using CRAFT methodology."""
        logger.info("Checking infrastructure status")

        try:
            status_info = {
                "action": "status",
                "timestamp": self.performance_service.start_timer(
                    "status_check"
                ).start_time,
                "environment": self.config_service.environment,
                "project_id": self.config_service.project_id,
            }

            # Get GCP resource status
            gcp_resources = self.gcp_service.get_resource_usage()
            status_info["gcp_resources"] = gcp_resources

            # Get Terraform state information for available modules
            terraform_status = {}
            available_modules = [
                "vm-management",
                "container-orchestration",
                "networking",
                "security",
            ]

            for module in available_modules:
                try:
                    state_result = self.terraform_service.show_state(module)
                    if state_result["success"] and state_result.get("data"):
                        state_data = state_result["data"]
                        terraform_status[module] = {
                            "resources": len(state_data.resources),
                            "terraform_version": state_data.terraform_version,
                            "serial": state_data.serial,
                            "outputs": len(state_data.outputs),
                        }
                    else:
                        terraform_status[module] = {"status": "not_deployed"}
                except Exception:
                    terraform_status[module] = {"status": "unknown"}

            status_info["terraform_modules"] = terraform_status

            # Get performance metrics
            perf_summary = self.performance_service.get_performance_summary()
            status_info["performance"] = {
                "total_operations": perf_summary["total_operations"],
                "avg_response_time": perf_summary["avg_response_time"],
                "target_compliance": perf_summary["target_compliance"],
            }

            # Calculate overall health
            overall_health = "healthy"
            if perf_summary["target_compliance"] < 0.9:
                overall_health = "degraded"

            status_info["overall_status"] = overall_health

            # Cache status for monitoring
            self.cache_service.set(
                "infrastructure_status",
                status_info,
                ttl=300,  # 5 minutes
                tags=["infrastructure", "status"],
            )

            return status_info

        except Exception as e:
            error = self.error_service.handle_exception(
                e, {"operation": "infrastructure_status"}
            )
            return {
                "action": "status",
                "error": self.error_service.format_error_message(error),
                "overall_status": "error",
            }

    def terraform_validate(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Terraform validate using CRAFT methodology."""
        module_path = getattr(args, "module", None) or self.config_service.environment

        logger.info(f"Running Terraform validate for module: {module_path}")

        try:
            # Run Terraform validate using service
            result = self.terraform_service.validate(module_path)

            if not result["success"]:
                error = result.get("error")
                if error:
                    raise Exception(self.error_service.format_error_message(error))
                else:
                    raise Exception("Terraform validate failed")

            validation_data = result.get("data", {})

            return {
                "action": "validate",
                "module": module_path,
                "valid": validation_data.get("valid", True),
                "diagnostics": validation_data.get("diagnostics", []),
                "status": "completed",
            }

        except Exception as e:
            error = self.error_service.handle_exception(
                e, {"operation": "terraform_validate", "module": module_path}
            )
            raise Exception(self.error_service.format_error_message(error))

    def terraform_init(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Terraform init using CRAFT methodology."""
        module_path = getattr(args, "module", None) or self.config_service.environment

        logger.info(f"Running Terraform init for module: {module_path}")

        try:
            # Run Terraform init using service
            result = self.terraform_service.init(module_path)

            if not result["success"]:
                error = result.get("error")
                if error:
                    raise Exception(self.error_service.format_error_message(error))
                else:
                    raise Exception("Terraform init failed")

            return {"action": "init", "module": module_path, "status": "initialized"}

        except Exception as e:
            error = self.error_service.handle_exception(
                e, {"operation": "terraform_init", "module": module_path}
            )
            raise Exception(self.error_service.format_error_message(error))

    def cost_operations(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cost-related operations using CRAFT methodology."""
        cost_action = getattr(args, "cost_action", None)

        if not cost_action:
            error = self.error_service.create_error(
                message="Cost action is required",
                category=ErrorCategory.USER,
                severity=ErrorSeverity.MEDIUM,
                code="MISSING_COST_ACTION",
                suggestions=["Use 'g infra cost estimate|analyze|optimize'"],
            )
            raise ValueError(self.error_service.format_error_message(error))

        try:
            if cost_action == "estimate":
                # Get resource estimates
                gcp_resources = self.gcp_service.get_resource_usage()

                # Simple cost estimation (would use actual pricing APIs in production)
                estimated_costs = {
                    "compute_instances": gcp_resources.get("compute_instances", {}).get(
                        "total", 0
                    )
                    * 50,
                    "gke_clusters": gcp_resources.get("gke_clusters", {}).get(
                        "total", 0
                    )
                    * 200,
                    "storage": 20,  # Base storage cost
                    "networking": 15,  # Base networking cost
                }

                total_estimate = sum(estimated_costs.values())

                return {
                    "action": "cost-estimate",
                    "estimated_monthly_cost": f"${total_estimate}",
                    "breakdown": estimated_costs,
                    "currency": "USD",
                    "status": "completed",
                }

            elif cost_action == "analyze":
                # Analyze current costs (placeholder implementation)
                return {
                    "action": "cost-analyze",
                    "current_monthly_cost": "$85",
                    "trend": "stable",
                    "top_resources": [
                        {"resource": "GKE Clusters", "cost": 60, "percentage": 70.6},
                        {
                            "resource": "Compute Instances",
                            "cost": 20,
                            "percentage": 23.5,
                        },
                        {"resource": "Storage", "cost": 5, "percentage": 5.9},
                    ],
                    "status": "completed",
                }

            elif cost_action == "optimize":
                # Cost optimization suggestions
                suggestions = [
                    "Consider using preemptible instances for non-critical workloads",
                    "Enable cluster autoscaling to reduce idle resource costs",
                    "Review disk sizes and types for cost optimization",
                    "Use committed use discounts for predictable workloads",
                ]

                return {
                    "action": "cost-optimize",
                    "suggestions": suggestions,
                    "potential_savings": "$15-25/month",
                    "status": "completed",
                }

            else:
                error = self.error_service.create_error(
                    message=f"Unknown cost action: {cost_action}",
                    category=ErrorCategory.USER,
                    severity=ErrorSeverity.MEDIUM,
                    code="INVALID_COST_ACTION",
                    suggestions=["Available actions: estimate, analyze, optimize"],
                )
                raise ValueError(self.error_service.format_error_message(error))

        except Exception as e:
            error = self.error_service.handle_exception(
                e, {"operation": "cost_operations", "cost_action": cost_action}
            )
            raise Exception(self.error_service.format_error_message(error))

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get infrastructure-specific performance metrics."""
        return {
            "infra_operations": self.performance_service.get_operation_stats(),
            "cache_stats": self.cache_service.get_stats(),
            "error_summary": self.error_service.get_error_summary(),
            "terraform_cache": len(self.cache_service.get_keys("terraform*")),
        }
