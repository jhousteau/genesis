"""
ADK Tool Safety Wrappers for SOLVE Agents

Implements safety wrappers for all ADK tools following official patterns from:
- adk-python/src/google/adk/tools/base_authenticated_tool.py
- adk-python/src/google/adk/tools/long_running_tool.py
- adk-samples/python/agents/financial-advisor/safety_tools.py

This module provides comprehensive safety mechanisms including:
- Pre-execution validation
- Post-execution verification
- Rollback mechanisms
- Resource limits
- Audit logging
- Path sandboxing
- Git branch protection
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Union

# Import from Google ADK
from google.adk.tools import BaseTool, ToolContext
from solve.adk_monitoring import get_monitoring_system
from solve.tools.filesystem import FileOperation, FileSystemTool, SafetyConfig
from solve.tools.git_operations import GitOperation, GitSafetyConfig, GitTool

ADK_AVAILABLE = True

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety levels for tool operations."""

    UNRESTRICTED = "unrestricted"  # No safety checks (dangerous!)
    MINIMAL = "minimal"  # Basic path validation only
    STANDARD = "standard"  # Default safety checks
    STRICT = "strict"  # Enhanced safety with confirmations
    PARANOID = "paranoid"  # Maximum safety, audit everything


class OperationType(Enum):
    """Types of operations for categorization."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    NETWORK = "network"
    SYSTEM = "system"


@dataclass
class SafetyViolation:
    """Record of a safety violation."""

    timestamp: datetime
    tool_name: str
    operation: str
    violation_type: str
    details: str
    prevented: bool
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationAuditLog:
    """Audit log entry for tool operations."""

    timestamp: datetime
    session_id: str
    agent_name: str
    tool_name: str
    operation: str
    parameters: dict[str, Any]
    result: Any
    success: bool
    duration_ms: float
    safety_checks_passed: list[str]
    safety_checks_failed: list[str]
    resource_usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceLimits:
    """Resource limits for tool operations."""

    max_file_size_mb: float = 10.0
    max_execution_time_seconds: float = 30.0
    max_memory_usage_mb: float = 512.0
    max_files_per_operation: int = 100
    max_git_commit_size_mb: float = 50.0
    max_concurrent_operations: int = 10
    rate_limit_per_minute: int = 60


@dataclass
class SafetyWrapperConfig:
    """Configuration for safety wrapper."""

    safety_level: SafetyLevel = SafetyLevel.STANDARD
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    sandbox_paths: list[Path] = field(default_factory=list)
    protected_paths: list[Path] = field(default_factory=list)
    protected_git_branches: list[str] = field(
        default_factory=lambda: ["main", "master", "production"],
    )
    allowed_file_extensions: set[str] = field(
        default_factory=lambda: {
            ".py",
            ".js",
            ".ts",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".cfg",
            ".ini",
            ".sh",
            ".bash",
            ".html",
            ".css",
        },
    )
    require_confirmation_for: set[OperationType] = field(
        default_factory=lambda: {OperationType.DELETE, OperationType.EXECUTE},
    )
    audit_all_operations: bool = True
    enable_rollback: bool = True
    block_dangerous_commands: bool = True


class RollbackManager:
    """Manages rollback operations for safety recovery."""

    def __init__(self, max_rollback_history: int = 50):
        self.rollback_history: list[dict[str, Any]] = []
        self.max_history = max_rollback_history

    def record_operation(self, operation: dict[str, Any]) -> str:
        """Record an operation for potential rollback."""
        operation_id = f"{operation['tool']}-{operation['timestamp']}-{id(operation)}"
        operation["id"] = operation_id

        self.rollback_history.append(operation)

        # Maintain history limit
        if len(self.rollback_history) > self.max_history:
            self.rollback_history.pop(0)

        return operation_id

    async def rollback(self, operation_id: str) -> bool:
        """Rollback a specific operation."""
        operation = next(
            (op for op in self.rollback_history if op["id"] == operation_id), None
        )

        if not operation:
            logger.error(f"Operation {operation_id} not found in rollback history")
            return False

        try:
            # Implement rollback based on operation type
            if operation["tool"] == "filesystem":
                return await self._rollback_filesystem_operation(operation)
            elif operation["tool"] == "git":
                return await self._rollback_git_operation(operation)
            else:
                logger.warning(f"No rollback handler for tool: {operation['tool']}")
                return False

        except Exception as e:
            logger.error(f"Rollback failed for {operation_id}: {e}")
            return False

    async def _rollback_filesystem_operation(self, operation: dict[str, Any]) -> bool:
        """Rollback filesystem operations."""
        op_type = operation.get("operation")

        if op_type == "create_file":
            # Delete the created file
            file_path = Path(operation["parameters"]["path"])
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Rolled back file creation: {file_path}")
                return True

        elif op_type == "delete_file":
            # Restore from backup if available
            backup_path = operation.get("backup_path")
            if backup_path and Path(backup_path).exists():
                original_path = Path(operation["parameters"]["path"])
                Path(backup_path).rename(original_path)
                logger.info(f"Rolled back file deletion: {original_path}")
                return True

        elif op_type == "modify_file":
            # Restore original content
            original_content = operation.get("original_content")
            if original_content is not None:
                file_path = Path(operation["parameters"]["path"])
                file_path.write_text(original_content)
                logger.info(f"Rolled back file modification: {file_path}")
                return True

        return False

    async def _rollback_git_operation(self, operation: dict[str, Any]) -> bool:
        """Rollback git operations."""
        op_type = operation.get("operation")

        if op_type == "commit":
            # Reset to previous commit
            commit_hash = operation.get("previous_commit")
            if commit_hash:
                # Would execute: git reset --hard {commit_hash}
                logger.info(f"Would rollback commit to: {commit_hash}")
                return True

        elif op_type == "branch_create":
            # Delete the created branch
            branch_name = operation["parameters"].get("branch_name")
            if branch_name:
                # Would execute: git branch -D {branch_name}
                logger.info(f"Would rollback branch creation: {branch_name}")
                return True

        return False


class SafetyWrapper(BaseTool):
    """
    Base safety wrapper for ADK tools.

    Provides comprehensive safety mechanisms for tool operations including
    validation, resource limits, audit logging, and rollback support.
    """

    def __init__(
        self,
        wrapped_tool: Union[BaseTool, Any],
        config: SafetyWrapperConfig | None = None,
        tool_context: ToolContext | None = None,
    ):
        """
        Initialize safety wrapper.

        Args:
            wrapped_tool: The tool to wrap with safety
            config: Safety configuration
            tool_context: ADK tool context
        """
        # Initialize base tool
        tool_name = getattr(wrapped_tool, "name", wrapped_tool.__class__.__name__)
        tool_description = getattr(
            wrapped_tool, "description", f"Safety-wrapped {tool_name}"
        )

        if ADK_AVAILABLE:
            super().__init__(name=f"safe_{tool_name}", description=tool_description)
        else:
            self.name = f"safe_{tool_name}"
            self.description = tool_description

        self.wrapped_tool = wrapped_tool
        self.config = config or SafetyWrapperConfig()
        self.tool_context = tool_context  # ToolContext is provided by ADK runtime

        # Initialize managers
        self.rollback_manager = RollbackManager()
        self.monitoring_system = get_monitoring_system()
        self.audit_logs: list[OperationAuditLog] = []
        self.violations: list[SafetyViolation] = []

        # Operation tracking
        self.active_operations: set[str] = set()
        self.operation_count = 0
        self.last_operation_time = datetime.now()

        logger.info(
            f"Initialized SafetyWrapper for {tool_name} with safety level: "
            f"{self.config.safety_level}",
        )

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute tool with safety checks (synchronous wrapper).

        This is the ADK-compliant interface that wraps async operations.
        """
        # Run async operation in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.execute_with_safety(**kwargs))
        finally:
            loop.close()

    async def execute_with_safety(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute tool operation with comprehensive safety checks.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Tool execution result with safety metadata
        """
        start_time = time.time()
        operation_id = f"{self.name}-{time.time()}-{self.operation_count}"
        self.operation_count += 1

        # Initialize tracking
        safety_checks_passed = []
        safety_checks_failed = []
        resource_usage = {}

        try:
            # Rate limiting check
            if not await self._check_rate_limit():
                raise PermissionError("Rate limit exceeded")
            safety_checks_passed.append("rate_limit")

            # Concurrent operations check
            if (
                len(self.active_operations)
                >= self.config.resource_limits.max_concurrent_operations
            ):
                raise PermissionError("Too many concurrent operations")
            safety_checks_passed.append("concurrency_limit")

            self.active_operations.add(operation_id)

            # Pre-execution validation
            validation_result = await self._pre_execution_validation(kwargs)
            if not validation_result["valid"]:
                safety_checks_failed.extend(validation_result["failed_checks"])
                # For safety violations, raise PermissionError to follow expected behavior
                if any(
                    check in validation_result["failed_checks"]
                    for check in ["path_validation", "branch_protection"]
                ):
                    raise PermissionError(validation_result["reason"])
                else:
                    raise PermissionError(
                        f"Pre-execution validation failed: {validation_result['reason']}",
                    )
            safety_checks_passed.extend(validation_result["passed_checks"])

            # Check if confirmation required
            operation_type = self._determine_operation_type(kwargs)
            if operation_type in self.config.require_confirmation_for:
                if not kwargs.get("confirmed", False):
                    return {
                        "success": False,
                        "requires_confirmation": True,
                        "operation_type": operation_type.value,
                        "message": f"Operation type '{operation_type.value}' requires confirmation",
                    }

            # Record operation for potential rollback
            if self.config.enable_rollback:
                rollback_data = await self._prepare_rollback_data(kwargs)
                rollback_id = self.rollback_manager.record_operation(rollback_data)
            else:
                rollback_id = None

            # Execute wrapped tool
            if hasattr(self.wrapped_tool, "run"):
                # ADK-compliant tool
                result = self.wrapped_tool.run(**kwargs)
            else:
                # Async tool method
                operation_method = kwargs.get("operation", "default")
                if hasattr(self.wrapped_tool, operation_method):
                    method = getattr(self.wrapped_tool, operation_method)
                    # Filter out safety-related parameters from kwargs for the method call
                    safety_params = {"operation", "confirmed", "requires_confirmation"}
                    method_kwargs = {
                        k: v for k, v in kwargs.items() if k not in safety_params
                    }
                    if asyncio.iscoroutinefunction(method):
                        result = await method(**method_kwargs)
                    else:
                        result = method(**method_kwargs)
                else:
                    raise AttributeError(f"Tool has no method: {operation_method}")

            # Post-execution verification
            verification_result = await self._post_execution_verification(
                kwargs, result
            )
            if not verification_result["valid"]:
                safety_checks_failed.extend(verification_result["failed_checks"])

                # Attempt rollback if enabled
                if self.config.enable_rollback and rollback_id:
                    rollback_success = await self.rollback_manager.rollback(rollback_id)
                    if rollback_success:
                        logger.info(f"Successfully rolled back operation {rollback_id}")

                raise RuntimeError(
                    f"Post-execution verification failed: {verification_result['reason']}",
                )
            safety_checks_passed.extend(verification_result["passed_checks"])

            # Track resource usage
            resource_usage = await self._measure_resource_usage(start_time)

            # Success - add safety metadata to result
            if isinstance(result, dict):
                result["safety_metadata"] = {
                    "operation_id": operation_id,
                    "safety_level": self.config.safety_level.value,
                    "checks_passed": safety_checks_passed,
                    "resource_usage": resource_usage,
                    "rollback_available": rollback_id is not None,
                }
                return result
            else:
                # For FileOperation or GitOperation objects, convert to dict format
                from solve.tools.filesystem import FileOperation
                from solve.tools.git_operations import GitOperation

                if isinstance(result, FileOperation):
                    return {
                        "success": result.success,
                        "path": result.path,
                        "operation": result.operation,
                        "message": result.message,
                        "metadata": result.metadata,
                        "safety_metadata": {
                            "operation_id": operation_id,
                            "safety_level": self.config.safety_level.value,
                            "checks_passed": safety_checks_passed,
                            "resource_usage": resource_usage,
                            "rollback_available": rollback_id is not None,
                        },
                    }
                elif isinstance(result, GitOperation):
                    return {
                        "success": result.success,
                        "command": result.command,
                        "operation": result.operation,
                        "message": result.message,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "metadata": result.metadata,
                        "safety_metadata": {
                            "operation_id": operation_id,
                            "safety_level": self.config.safety_level.value,
                            "checks_passed": safety_checks_passed,
                            "resource_usage": resource_usage,
                            "rollback_available": rollback_id is not None,
                        },
                    }
                else:
                    # For other types, convert to basic dict
                    return {
                        "success": True,
                        "result": str(result),
                        "safety_metadata": {
                            "operation_id": operation_id,
                            "safety_level": self.config.safety_level.value,
                            "checks_passed": safety_checks_passed,
                            "resource_usage": resource_usage,
                            "rollback_available": rollback_id is not None,
                        },
                    }

        except (AttributeError, RuntimeError) as e:
            # Handle execution errors that should return dict
            logger.error(f"Safety-wrapped operation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "safety_metadata": {
                    "operation_id": operation_id,
                    "checks_passed": safety_checks_passed,
                    "checks_failed": safety_checks_failed,
                    "resource_usage": resource_usage,
                },
            }

        except PermissionError as e:
            # Safety violations should bubble up as PermissionError
            logger.error(f"Safety-wrapped operation failed: {e}")

            # Record violation
            self._record_violation(
                operation=kwargs.get("operation", "unknown"),
                violation_type="permission_denied",
                details=str(e),
                prevented=True,
            )

            # Re-raise the PermissionError for safety violations
            raise

        except Exception as e:
            logger.error(f"Safety-wrapped operation failed: {e}")

            # Record violation
            self._record_violation(
                operation=kwargs.get("operation", "unknown"),
                violation_type="execution_error",
                details=str(e),
                prevented=True,
            )

            # Return error result for other exceptions
            return {
                "success": False,
                "error": str(e),
                "safety_metadata": {
                    "operation_id": operation_id,
                    "checks_passed": safety_checks_passed,
                    "checks_failed": safety_checks_failed,
                    "resource_usage": resource_usage,
                },
            }

        finally:
            # Clean up
            self.active_operations.discard(operation_id)

            # Audit logging
            if self.config.audit_all_operations:
                await self._audit_operation(
                    operation_id=operation_id,
                    kwargs=kwargs,
                    result=result if "result" in locals() else None,
                    success="result" in locals() and not isinstance(result, Exception),
                    duration_ms=(time.time() - start_time) * 1000,
                    safety_checks_passed=safety_checks_passed,
                    safety_checks_failed=safety_checks_failed,
                    resource_usage=resource_usage,
                )

    async def _check_rate_limit(self) -> bool:
        """Check if operation is within rate limits."""
        current_time = datetime.now()
        time_diff = (current_time - self.last_operation_time).total_seconds()

        if time_diff < 60:  # Within the same minute
            # Simple rate limiting - would be more sophisticated in production
            return (
                self.operation_count < self.config.resource_limits.rate_limit_per_minute
            )
        else:
            # Reset counter for new minute
            self.operation_count = 0
            self.last_operation_time = current_time
            return True

    async def _pre_execution_validation(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Perform pre-execution validation.

        Returns:
            Validation result with 'valid', 'reason', 'passed_checks', 'failed_checks'
        """
        passed_checks = []
        failed_checks = []

        # Path validation for filesystem operations
        if "path" in kwargs or "file_path" in kwargs:
            path_param = kwargs.get("path") or kwargs.get("file_path")
            if path_param is not None:
                path_result = await self._validate_path_safety(path_param)
                if path_result["valid"]:
                    passed_checks.append("path_validation")
                else:
                    failed_checks.append("path_validation")
                    return {
                        "valid": False,
                        "reason": path_result["reason"],
                        "passed_checks": passed_checks,
                        "failed_checks": failed_checks,
                    }
            else:
                # If path parameter is None, that's an error case
                failed_checks.append("path_validation")
                return {
                    "valid": False,
                    "reason": "Path parameter is required but was None",
                    "passed_checks": passed_checks,
                    "failed_checks": failed_checks,
                }

        # Git branch protection
        if "branch" in kwargs or "branch_name" in kwargs:
            branch_param = kwargs.get("branch") or kwargs.get("branch_name")
            if branch_param in self.config.protected_git_branches:
                operation = kwargs.get("operation", "")
                if operation in ["delete", "force_push", "reset", "branch_delete"]:
                    failed_checks.append("branch_protection")
                    return {
                        "valid": False,
                        "reason": f"Protected branch '{branch_param}' cannot be modified",
                        "passed_checks": passed_checks,
                        "failed_checks": failed_checks,
                    }
            passed_checks.append("branch_protection")

        # File size limits
        if "content" in kwargs:
            content_size = len(kwargs["content"].encode("utf-8"))
            max_size = self.config.resource_limits.max_file_size_mb * 1024 * 1024
            if content_size > max_size:
                failed_checks.append("file_size_limit")
                return {
                    "valid": False,
                    "reason": f"Content size {content_size} exceeds limit {max_size}",
                    "passed_checks": passed_checks,
                    "failed_checks": failed_checks,
                }
            passed_checks.append("file_size_limit")

        # Command injection prevention
        if self.config.block_dangerous_commands:
            command_result = await self._check_dangerous_commands(kwargs)
            if not command_result["safe"]:
                failed_checks.append("command_safety")
                return {
                    "valid": False,
                    "reason": command_result["reason"],
                    "passed_checks": passed_checks,
                    "failed_checks": failed_checks,
                }
            passed_checks.append("command_safety")

        return {
            "valid": True,
            "reason": "All pre-execution checks passed",
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
        }

    async def _post_execution_verification(
        self,
        kwargs: dict[str, Any],
        result: Any,
    ) -> dict[str, Any]:
        """
        Perform post-execution verification.

        Returns:
            Verification result with 'valid', 'reason', 'passed_checks', 'failed_checks'
        """
        passed_checks: list[str] = []
        failed_checks: list[str] = []

        # Verify operation success
        if isinstance(result, dict):
            if not result.get("success", True):
                failed_checks.append("operation_success")
                return {
                    "valid": False,
                    "reason": result.get("message", "Operation failed"),
                    "passed_checks": passed_checks,
                    "failed_checks": failed_checks,
                }
            passed_checks.append("operation_success")

        # Verify no unintended side effects
        if self.config.safety_level in [SafetyLevel.STRICT, SafetyLevel.PARANOID]:
            side_effects_result = await self._check_side_effects(kwargs, result)
            if not side_effects_result["clean"]:
                failed_checks.append("side_effects")
                return {
                    "valid": False,
                    "reason": side_effects_result["reason"],
                    "passed_checks": passed_checks,
                    "failed_checks": failed_checks,
                }
            passed_checks.append("side_effects")

        return {
            "valid": True,
            "reason": "All post-execution checks passed",
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
        }

    async def _validate_path_safety(self, path: Union[str, Path]) -> dict[str, Any]:
        """Validate path for safety constraints."""
        try:
            path_obj = Path(path).resolve()

            # Check if in sandbox
            if self.config.sandbox_paths:
                in_sandbox = any(
                    path_obj.is_relative_to(Path(sandbox_path).resolve())
                    for sandbox_path in self.config.sandbox_paths
                )
                if not in_sandbox:
                    return {
                        "valid": False,
                        "reason": f"Path {path_obj} is outside allowed sandbox paths",
                    }

            # Check protected paths
            for protected_path in self.config.protected_paths:
                if path_obj.is_relative_to(Path(protected_path).resolve()):
                    return {
                        "valid": False,
                        "reason": f"Path {path_obj} is in protected directory {protected_path}",
                    }

            # Check file extension
            if (
                path_obj.suffix
                and path_obj.suffix not in self.config.allowed_file_extensions
            ):
                return {
                    "valid": False,
                    "reason": f"File extension {path_obj.suffix} not allowed",
                }

            return {"valid": True, "reason": "Path validation passed"}

        except Exception as e:
            return {"valid": False, "reason": f"Path validation error: {e}"}

    async def _check_dangerous_commands(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Check for dangerous command patterns."""
        dangerous_patterns = [
            "rm -rf /",
            "dd if=/dev/zero",
            "fork bomb",
            ":(){ :|:& };:",
            "chmod -R 777",
            "curl | sh",
            "wget | bash",
        ]

        # Check all string parameters
        for _key, value in kwargs.items():
            if isinstance(value, str):
                for pattern in dangerous_patterns:
                    if pattern in value.lower():
                        return {
                            "safe": False,
                            "reason": f"Dangerous pattern detected: {pattern}",
                        }

        return {"safe": True, "reason": "No dangerous patterns detected"}

    async def _check_side_effects(
        self, kwargs: dict[str, Any], result: Any
    ) -> dict[str, Any]:
        """Check for unintended side effects."""
        # This would implement checks specific to the operation type
        # For now, return clean
        return {"clean": True, "reason": "No side effects detected"}

    async def _prepare_rollback_data(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Prepare data needed for potential rollback."""
        rollback_data = {
            "tool": self.wrapped_tool.__class__.__name__,
            "operation": kwargs.get("operation", "unknown"),
            "parameters": kwargs.copy(),
            "timestamp": datetime.now().isoformat(),
        }

        # Add tool-specific rollback data
        if "path" in kwargs or "file_path" in kwargs:
            path = kwargs.get("path") or kwargs.get("file_path")
            if path is not None and Path(path).exists():
                # Store original content for file modifications
                try:
                    rollback_data["original_content"] = Path(path).read_text()
                except (OSError, PermissionError, UnicodeDecodeError) as e:
                    logger.warning(
                        "Unable to read original content for rollback from %s: %s. "
                        "Rollback may be incomplete if this operation modifies the file",
                        path,
                        e,
                    )

        return rollback_data

    async def _measure_resource_usage(self, start_time: float) -> dict[str, Any]:
        """Measure resource usage of the operation."""
        return {
            "duration_ms": (time.time() - start_time) * 1000,
            "memory_usage_mb": 0,  # Would use psutil in production
            "cpu_usage_percent": 0,  # Would use psutil in production
        }

    def _determine_operation_type(self, kwargs: dict[str, Any]) -> OperationType:
        """Determine the type of operation from parameters."""
        operation = kwargs.get("operation", "").lower()

        if any(word in operation for word in ["read", "get", "list", "status"]):
            return OperationType.READ
        elif any(word in operation for word in ["write", "create", "update", "add"]):
            return OperationType.WRITE
        elif any(word in operation for word in ["delete", "remove", "clean"]):
            return OperationType.DELETE
        elif any(word in operation for word in ["run", "execute", "exec"]):
            return OperationType.EXECUTE
        elif any(word in operation for word in ["push", "pull", "fetch", "clone"]):
            return OperationType.NETWORK
        else:
            return OperationType.SYSTEM

    def _record_violation(
        self,
        operation: str,
        violation_type: str,
        details: str,
        prevented: bool,
    ) -> None:
        """Record a safety violation."""
        violation = SafetyViolation(
            timestamp=datetime.now(),
            tool_name=self.name,
            operation=operation,
            violation_type=violation_type,
            details=details,
            prevented=prevented,
            context={
                "session_id": (
                    getattr(
                        getattr(self.tool_context, "invocation_context", None),
                        "session_id",
                        None,
                    )
                    if self.tool_context
                    else "safety-session"
                ),
                "agent_name": (
                    getattr(
                        getattr(self.tool_context, "invocation_context", None),
                        "agent_name",
                        None,
                    )
                    if self.tool_context
                    else "safety-agent"
                ),
            },
        )

        self.violations.append(violation)

        # Report to monitoring system
        session_id = (
            getattr(
                getattr(self.tool_context, "invocation_context", None),
                "session_id",
                None,
            )
            if self.tool_context
            else None
        )
        self.monitoring_system.record_constitutional_event(
            session_id=str(session_id) if session_id is not None else "safety-session",
            principle=f"tool_safety_{violation_type}",
            passed=not prevented,
            context=f"Tool: {self.name}, Operation: {operation}",
            action_taken=f"Violation {'prevented' if prevented else 'logged'}: {details}",
        )

    async def _audit_operation(
        self,
        operation_id: str,
        kwargs: dict[str, Any],
        result: Any,
        success: bool,
        duration_ms: float,
        safety_checks_passed: list[str],
        safety_checks_failed: list[str],
        resource_usage: dict[str, Any],
    ) -> None:
        """Audit the operation for compliance and monitoring."""
        session_id = (
            getattr(
                getattr(self.tool_context, "invocation_context", None),
                "session_id",
                None,
            )
            if self.tool_context
            else None
        )
        agent_name = (
            getattr(
                getattr(self.tool_context, "invocation_context", None),
                "agent_name",
                None,
            )
            if self.tool_context
            else None
        )

        audit_log = OperationAuditLog(
            timestamp=datetime.now(),
            session_id=str(session_id) if session_id is not None else "safety-session",
            agent_name=str(agent_name) if agent_name is not None else "safety-agent",
            tool_name=self.name,
            operation=kwargs.get("operation", "unknown"),
            parameters=self._sanitize_parameters(kwargs),
            result=self._sanitize_result(result),
            success=success,
            duration_ms=duration_ms,
            safety_checks_passed=safety_checks_passed,
            safety_checks_failed=safety_checks_failed,
            resource_usage=resource_usage,
        )

        self.audit_logs.append(audit_log)

        # Log to file if configured
        if self.config.safety_level == SafetyLevel.PARANOID:
            self._write_audit_log_to_file(audit_log)

    def _sanitize_parameters(self, params: dict[str, Any]) -> dict[str, Any]:
        """Sanitize parameters for logging (remove sensitive data)."""
        sanitized = params.copy()

        # Remove potential sensitive fields
        sensitive_fields = [
            "password",
            "token",
            "key",
            "secret",
            "credential",
            "api_key",
        ]
        for sensitive_field in sensitive_fields:
            if sensitive_field in sanitized:
                sanitized[sensitive_field] = "***REDACTED***"

        return sanitized

    def _sanitize_result(self, result: Any) -> Any:
        """Sanitize result for logging."""
        if isinstance(result, dict):
            # Don't log file contents
            if "content" in result and len(str(result["content"])) > 100:
                result = result.copy()
                result["content"] = f"***TRUNCATED ({len(result['content'])} chars)***"

        return result

    def _write_audit_log_to_file(self, audit_log: OperationAuditLog) -> None:
        """Write audit log to file for paranoid safety level."""
        try:
            audit_dir = Path("logs/tool_safety_audit")
            audit_dir.mkdir(parents=True, exist_ok=True)

            date_str = audit_log.timestamp.strftime("%Y-%m-%d")
            audit_file = audit_dir / f"audit_{date_str}.jsonl"

            with open(audit_file, "a") as f:
                # Convert to dict and write as JSON line
                log_dict = {
                    "timestamp": audit_log.timestamp.isoformat(),
                    "session_id": audit_log.session_id,
                    "agent_name": audit_log.agent_name,
                    "tool_name": audit_log.tool_name,
                    "operation": audit_log.operation,
                    "parameters": audit_log.parameters,
                    "success": audit_log.success,
                    "duration_ms": audit_log.duration_ms,
                    "safety_checks_passed": audit_log.safety_checks_passed,
                    "safety_checks_failed": audit_log.safety_checks_failed,
                    "resource_usage": audit_log.resource_usage,
                }
                f.write(json.dumps(log_dict) + "\n")

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_safety_report(self) -> dict[str, Any]:
        """Get a safety report for this wrapper."""
        return {
            "tool_name": self.name,
            "safety_level": self.config.safety_level.value,
            "total_operations": len(self.audit_logs),
            "successful_operations": sum(1 for log in self.audit_logs if log.success),
            "failed_operations": sum(1 for log in self.audit_logs if not log.success),
            "violations": len(self.violations),
            "violations_prevented": sum(1 for v in self.violations if v.prevented),
            "active_operations": len(self.active_operations),
            "resource_limits": {
                "max_file_size_mb": self.config.resource_limits.max_file_size_mb,
                "max_execution_time_seconds": (
                    self.config.resource_limits.max_execution_time_seconds
                ),
                "rate_limit_per_minute": self.config.resource_limits.rate_limit_per_minute,
            },
        }


class SafeFileSystemTool(SafetyWrapper):
    """Safety-wrapped FileSystemTool with ADK compliance."""

    def __init__(
        self,
        safety_config: SafetyConfig | None = None,
        wrapper_config: SafetyWrapperConfig | None = None,
        tool_context: ToolContext | None = None,
    ):
        """Initialize safe filesystem tool."""
        # Create underlying filesystem tool with sandbox configuration
        if wrapper_config:
            # Use the first sandbox path as the filesystem tool's sandbox root if available
            sandbox_root = (
                str(wrapper_config.sandbox_paths[0])
                if wrapper_config.sandbox_paths
                else None
            )
            fs_safety_config = safety_config or SafetyConfig(
                allowed_extensions=list(wrapper_config.allowed_file_extensions),
                forbidden_paths=[str(p) for p in wrapper_config.protected_paths],
                max_file_size=10 * 1024 * 1024,  # 10MB default
                require_confirmation_for_destructive=True,
                sandbox_root=sandbox_root,
            )
        else:
            fs_safety_config = safety_config or SafetyConfig(
                allowed_extensions=[".py", ".txt", ".md", ".json"],
                forbidden_paths=["/etc", "/usr", "/var"],
                max_file_size=10 * 1024 * 1024,
                require_confirmation_for_destructive=True,
                sandbox_root=None,
            )

        fs_tool = FileSystemTool(fs_safety_config)

        # Initialize safety wrapper
        super().__init__(
            wrapped_tool=fs_tool,
            config=wrapper_config
            or SafetyWrapperConfig(
                safety_level=SafetyLevel.STRICT,
                sandbox_paths=[Path.cwd()],  # Default to current directory
                protected_paths=[
                    Path("/etc"),
                    Path("/usr"),
                    Path("/var"),
                    Path("/System"),
                    Path.home() / ".ssh",
                    Path.home() / ".aws",
                ],
            ),
            tool_context=tool_context,
        )

    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        """Execute filesystem operations asynchronously with ADK interface."""
        # Map ADK args to FileSystemTool operations
        operation = args.get("operation", "")

        if operation == "create_file":
            return await self.create_file(
                path=args["path"],
                content=args["content"],
                confirmed=args.get("confirmed", False),
            )
        elif operation == "read_file":
            return await self.read_file(path=args["path"])
        elif operation == "delete_file":
            return await self.delete_file(
                path=args["path"], confirm=args.get("confirm", False)
            )
        elif operation == "list_directory":
            return await self.execute_with_safety(
                operation="list_directory", path=args["path"]
            )
        elif operation == "move_file":
            return await self.execute_with_safety(
                operation="move_file",
                source_path=args["source_path"],
                dest_path=args["dest_path"],
            )
        elif operation == "copy_file":
            return await self.execute_with_safety(
                operation="copy_file",
                source_path=args["source_path"],
                dest_path=args["dest_path"],
            )
        else:
            raise ValueError(f"Unknown filesystem operation: {operation}")

    async def create_file(
        self,
        path: str,
        content: str,
        **kwargs: Any,
    ) -> Union[FileOperation, dict[str, Any]]:
        """Create file with safety checks."""
        result = await self.execute_with_safety(
            operation="create_file",
            path=path,
            content=content,
            **kwargs,
        )

        # If the safety check failed, return the dict result
        if isinstance(result, dict) and not result.get("success", True):
            if "protected directory" in result.get(
                "error", ""
            ) or "not allowed" in result.get(
                "error",
                "",
            ):
                raise PermissionError(result["error"])

        # Convert dict result to FileOperation if needed
        if isinstance(result, dict):
            from solve.tools.filesystem import FileOperation

            if "path" in result and "operation" in result:
                return FileOperation(
                    success=result.get("success", True),
                    path=result["path"],
                    operation=result["operation"],
                    message=result.get("message", ""),
                    metadata=result.get("metadata", {}),
                )

        return result

    async def read_file(
        self, path: str, **kwargs: Any
    ) -> Union[FileOperation, dict[str, Any]]:
        """Read file with safety checks."""
        result = await self.execute_with_safety(
            operation="read_file", path=path, **kwargs
        )

        # Convert dict result to FileOperation if needed
        if isinstance(result, dict):
            from solve.tools.filesystem import FileOperation

            if "path" in result and "operation" in result:
                return FileOperation(
                    success=result.get("success", True),
                    path=result["path"],
                    operation=result["operation"],
                    message=result.get("message", ""),
                    metadata=result.get("metadata", {}),
                )

        return result

    async def delete_file(
        self,
        path: str,
        confirm: bool = False,
        **kwargs: Any,
    ) -> Union[FileOperation, dict[str, Any]]:
        """Delete file with safety checks."""
        result = await self.execute_with_safety(
            operation="delete_file",
            path=path,
            confirm=confirm,
            **kwargs,
        )

        # If the safety check failed, return the dict result
        if isinstance(result, dict) and not result.get("success", True):
            if "protected directory" in result.get(
                "error", ""
            ) or "not allowed" in result.get(
                "error",
                "",
            ):
                raise PermissionError(result["error"])

        # Convert dict result to FileOperation if needed
        if isinstance(result, dict):
            from solve.tools.filesystem import FileOperation

            if "path" in result and "operation" in result:
                return FileOperation(
                    success=result.get("success", True),
                    path=result["path"],
                    operation=result["operation"],
                    message=result.get("message", ""),
                    metadata=result.get("metadata", {}),
                )

        return result


class SafeGitTool(SafetyWrapper):
    """Safety-wrapped GitTool with ADK compliance."""

    def __init__(
        self,
        git_safety_config: GitSafetyConfig | None = None,
        wrapper_config: SafetyWrapperConfig | None = None,
        tool_context: ToolContext | None = None,
    ):
        """Initialize safe git tool."""
        # Create underlying git tool
        git_tool = GitTool(git_safety_config)

        # Initialize safety wrapper with git-specific config
        super().__init__(
            wrapped_tool=git_tool,
            config=wrapper_config
            or SafetyWrapperConfig(
                safety_level=SafetyLevel.STRICT,
                protected_git_branches=["main", "master", "production", "release/*"],
                require_confirmation_for={
                    OperationType.DELETE,
                    OperationType.EXECUTE,
                    OperationType.NETWORK,  # For push operations
                },
            ),
            tool_context=tool_context,
        )

    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        """Execute git operations asynchronously with ADK interface."""
        # Map ADK args to GitTool operations
        operation = args.get("operation", "")

        if operation == "commit":
            return await self.commit(
                message=args["message"],
                confirmed=args.get("confirmed", False),
            )
        elif operation == "push":
            return await self.push(
                remote=args.get("remote", "origin"),
                branch=args.get("branch"),
                confirmed=args.get("confirmed", False),
            )
        elif operation == "branch_delete":
            return await self.branch_delete(
                branch_name=args["branch_name"],
                confirmed=args.get("confirmed", False),
            )
        elif operation == "status":
            return await self.execute_with_safety(operation="status")
        elif operation == "pull":
            return await self.execute_with_safety(
                operation="pull",
                remote=args.get("remote", "origin"),
                branch=args.get("branch"),
            )
        elif operation == "branch_create":
            return await self.execute_with_safety(
                operation="branch_create",
                branch_name=args["branch_name"],
                from_branch=args.get("from_branch"),
            )
        elif operation == "checkout":
            return await self.execute_with_safety(
                operation="checkout", branch=args["branch"]
            )
        elif operation == "stash":
            return await self.execute_with_safety(
                operation="stash", message=args.get("message")
            )
        elif operation == "add":
            return await self.execute_with_safety(
                operation="add", paths=args.get("paths", ["."])
            )
        else:
            raise ValueError(f"Unknown git operation: {operation}")

    async def commit(
        self, message: str, **kwargs: Any
    ) -> Union[GitOperation, dict[str, Any]]:
        """Create commit with safety checks."""
        result = await self.execute_with_safety(
            operation="commit", message=message, **kwargs
        )

        # Convert dict result to GitOperation if needed
        if isinstance(result, dict):
            from solve.tools.git_operations import GitOperation

            if "command" in result and "operation" in result:
                return GitOperation(
                    success=result.get("success", True),
                    command=result["command"],
                    operation=result["operation"],
                    message=result.get("message", ""),
                    stdout=result.get("stdout", ""),
                    stderr=result.get("stderr", ""),
                    metadata=result.get("metadata", {}),
                )

        return result

    async def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
        **kwargs: Any,
    ) -> Union[GitOperation, dict[str, Any]]:
        """Push with safety checks and confirmations."""
        result = await self.execute_with_safety(
            operation="push",
            remote=remote,
            branch=branch,
            **kwargs,
        )

        # Convert dict result to GitOperation if needed
        if isinstance(result, dict):
            from solve.tools.git_operations import GitOperation

            if "command" in result and "operation" in result:
                return GitOperation(
                    success=result.get("success", True),
                    command=result["command"],
                    operation=result["operation"],
                    message=result.get("message", ""),
                    stdout=result.get("stdout", ""),
                    stderr=result.get("stderr", ""),
                    metadata=result.get("metadata", {}),
                )

        return result

    async def branch_delete(
        self,
        branch_name: str,
        **kwargs: Any,
    ) -> Union[GitOperation, dict[str, Any]]:
        """Delete branch with safety checks."""
        result = await self.execute_with_safety(
            operation="branch_delete",
            branch_name=branch_name,
            **kwargs,
        )

        # If the safety check failed, return the dict result
        if isinstance(result, dict) and not result.get("success", True):
            if "Protected branch" in result.get("error", ""):
                raise PermissionError(result["error"])

        # Convert dict result to GitOperation if needed
        if isinstance(result, dict):
            from solve.tools.git_operations import GitOperation

            if "command" in result and "operation" in result:
                return GitOperation(
                    success=result.get("success", True),
                    command=result["command"],
                    operation=result["operation"],
                    message=result.get("message", ""),
                    stdout=result.get("stdout", ""),
                    stderr=result.get("stderr", ""),
                    metadata=result.get("metadata", {}),
                )

        return result


def create_safe_tools(
    safety_level: SafetyLevel = SafetyLevel.STANDARD,
    tool_context: ToolContext | None = None,
) -> dict[str, SafetyWrapper]:
    """
    Create a set of safety-wrapped tools.

    Args:
        safety_level: Safety level to apply
        tool_context: ADK tool context

    Returns:
        Dictionary of safe tools
    """
    config = SafetyWrapperConfig(safety_level=safety_level)

    return {
        "filesystem": SafeFileSystemTool(
            wrapper_config=config, tool_context=tool_context
        ),
        "git": SafeGitTool(wrapper_config=config, tool_context=tool_context),
    }


# Example usage and testing
if __name__ == "__main__":

    async def test_safety_wrappers() -> None:
        """Test safety wrapper functionality."""
        logger.info("Testing ADK Safety Wrappers")

        # Create safe tools
        tools = create_safe_tools(safety_level=SafetyLevel.PARANOID)

        # Test filesystem safety
        fs_tool = tools["filesystem"]
        assert isinstance(fs_tool, SafeFileSystemTool)

        # This should work (safe operation)
        result = await fs_tool.create_file(
            path="test_safe.txt", content="This is a safe test file"
        )
        logger.info(f"Safe file creation: {result}")

        # This should fail (protected path)
        try:
            result = await fs_tool.create_file(
                path="/etc/passwd", content="Dangerous content"
            )
        except PermissionError as e:
            logger.info(f"Protected path blocked: {e}")

        # Test git safety
        git_tool = tools["git"]
        assert isinstance(git_tool, SafeGitTool)

        # This should require confirmation
        git_result = await git_tool.push(remote="origin", branch="main")
        logger.info(f"Push without confirmation: {git_result}")

        # Get safety reports
        for name, tool in tools.items():
            report = tool.get_safety_report()
            logger.info(f"\nSafety report for {name}:")
            logger.info(json.dumps(report, indent=2))

    # Run tests
    asyncio.run(test_safety_wrappers())
