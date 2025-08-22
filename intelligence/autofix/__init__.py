"""
Comprehensive autofix/autocommit system for the SOLVE methodology.

This module implements a three-stage autofix system:
1. AutoFixerRunner - Automated fixes (free, <1 second)
2. ValidationRunner - Issue identification
3. ManualFixOrchestrator - LLM-powered fixes for complex issues

Based on ADR-004: Comprehensive Autofix/Autocommit System Architecture
"""

from .backup import BackupManager
from .eval_adapter import AutofixEvalAdapter
from .fixers import (EndOfFileFixer, RuffAutoFixer, RuffFormatter,
                     TrailingWhitespaceFixer)
from .llm_fixer import (ContextBuilder, ErrorGrouper, ManualFixOrchestrator,
                        XMLPromptFormatter)
from .metrics import MetricsCollector
from .models import AutofixConfig, FixResult, ValidationResult
from .runner import AutoFixerRunner
from .validation import ValidationRunner
from .validators import MypyChecker, PytestRunner, RuffChecker, SecurityChecker

__all__ = [
    "AutoFixerRunner",
    "ValidationRunner",
    "ManualFixOrchestrator",
    "AutofixConfig",
    "FixResult",
    "ValidationResult",
    "TrailingWhitespaceFixer",
    "EndOfFileFixer",
    "RuffAutoFixer",
    "RuffFormatter",
    "RuffChecker",
    "MypyChecker",
    "SecurityChecker",
    "PytestRunner",
    "ErrorGrouper",
    "ContextBuilder",
    "XMLPromptFormatter",
    "BackupManager",
    "MetricsCollector",
    "AutofixEvalAdapter",
]
