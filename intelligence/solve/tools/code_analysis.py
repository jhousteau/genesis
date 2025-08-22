"""
Real Code Analysis Tool for SOLVE Agents

Implements actual AST parsing and code analysis with safety mechanisms.
Based on best practices from docs/best-practices/2-llm-code-editing-best-practices.md

NO MOCKS, NO STUBS - REAL AST PARSING AND ANALYSIS ONLY
"""

import ast
import builtins
import logging
import re
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

logger = logging.getLogger(__name__)


@dataclass
class CodeAnalysisResult:
    """Result of a code analysis operation."""

    success: bool
    file_path: str
    operation: str
    message: str
    analysis_data: dict[str, Any]
    execution_time: float
    warnings: list[str]


@dataclass
class SecurityIssue:
    """Security vulnerability found in code."""

    severity: str  # 'low', 'medium', 'high', 'critical'
    issue_type: str
    line_number: int
    description: str
    recommendation: str


@dataclass
class QualityIssue:
    """Code quality issue found."""

    severity: str  # 'info', 'warning', 'error'
    issue_type: str
    line_number: int
    description: str
    suggestion: str


@dataclass
class ComplexityMetrics:
    """Code complexity metrics."""

    cyclomatic_complexity: int
    cognitive_complexity: int
    lines_of_code: int
    maintainability_index: float


@dataclass
class FunctionInfo:
    """Information about a function."""

    name: str
    line_number: int
    end_line: int
    parameters: list[str]
    return_annotation: str | None
    docstring: str | None
    complexity: ComplexityMetrics
    is_async: bool
    decorators: list[str]


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    line_number: int
    end_line: int
    base_classes: list[str]
    methods: list[FunctionInfo]
    docstring: str | None
    decorators: list[str]


@dataclass
class ImportInfo:
    """Information about imports."""

    module: str
    names: list[str]
    line_number: int
    is_from_import: bool
    alias: str | None


@dataclass
class SafetyConfig:
    """Safety configuration for code analysis."""

    max_file_size: int  # bytes
    timeout_seconds: int
    max_memory_mb: int
    allowed_file_extensions: list[str]
    forbidden_patterns: list[str]


class CodeComplexityVisitor(ast.NodeVisitor):
    """AST visitor to calculate code complexity metrics."""

    def __init__(self) -> None:
        self.complexity = 1  # Base complexity
        self.cognitive_complexity = 0
        self.nesting_level = 0

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.cognitive_complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.cognitive_complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.cognitive_complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_Try(self, node: ast.Try) -> None:
        self.complexity += len(node.handlers)
        self.cognitive_complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.cognitive_complexity += 1 + self.nesting_level
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.cognitive_complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Continue(self, node: ast.Continue) -> None:
        self.cognitive_complexity += 1

    def visit_Break(self, node: ast.Break) -> None:
        self.cognitive_complexity += 1


class SecurityAnalyzer(ast.NodeVisitor):
    """AST visitor to detect security vulnerabilities."""

    def __init__(self) -> None:
        self.issues: list[SecurityIssue] = []

        # Dangerous functions that should be flagged
        self.dangerous_functions = {
            "eval": "critical",
            "exec": "critical",
            "compile": "high",
            "__import__": "high",
            "open": "medium",
            "input": "low",
            "raw_input": "medium",
        }

        # Dangerous modules
        self.dangerous_modules = {
            "os": "medium",
            "subprocess": "high",
            "pickle": "high",
            "marshal": "medium",
            "shelve": "medium",
        }

    def visit_Call(self, node: ast.Call) -> None:
        # Check for dangerous function calls
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.dangerous_functions:
                severity = self.dangerous_functions[func_name]
                self.issues.append(
                    SecurityIssue(
                        severity=severity,
                        issue_type="dangerous_function",
                        line_number=node.lineno,
                        description=f"Use of potentially dangerous function '{func_name}'",
                        recommendation=(
                            f"Avoid using '{func_name}' or ensure proper input validation"
                        ),
                    ),
                )

        # Check for SQL injection patterns
        if isinstance(node.func, ast.Attribute):
            if (
                hasattr(node.func.value, "id")
                and node.func.attr in ["execute", "executemany"]
                and any(
                    isinstance(arg, ast.BinOp)
                    and isinstance(arg.op, (ast.Add, ast.Mod))
                    for arg in node.args
                )
            ):
                self.issues.append(
                    SecurityIssue(
                        severity="high",
                        issue_type="sql_injection",
                        line_number=node.lineno,
                        description="Potential SQL injection vulnerability",
                        recommendation="Use parameterized queries instead of string concatenation",
                    ),
                )

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in self.dangerous_modules:
                severity = self.dangerous_modules[alias.name]
                self.issues.append(
                    SecurityIssue(
                        severity=severity,
                        issue_type="dangerous_import",
                        line_number=node.lineno,
                        description=f"Import of potentially dangerous module '{alias.name}'",
                        recommendation=f"Ensure safe usage of '{alias.name}' module",
                    ),
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module in self.dangerous_modules:
            severity = self.dangerous_modules[node.module]
            self.issues.append(
                SecurityIssue(
                    severity=severity,
                    issue_type="dangerous_import",
                    line_number=node.lineno,
                    description=f"Import from potentially dangerous module '{node.module}'",
                    recommendation=f"Ensure safe usage of '{node.module}' module",
                ),
            )
        self.generic_visit(node)


class QualityAnalyzer(ast.NodeVisitor):
    """AST visitor to detect code quality issues."""

    def __init__(self, source_lines: list[str]) -> None:
        self.issues: list[QualityIssue] = []
        self.source_lines = source_lines
        self.variables: dict[str, list[int]] = defaultdict(
            list
        )  # var_name -> [line_numbers]
        self.used_variables: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            # Variable assignment
            self.variables[node.id].append(node.lineno)
        elif isinstance(node.ctx, ast.Load):
            # Variable usage
            self.used_variables.add(node.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Check function length
        func_length = (
            (node.end_lineno - node.lineno + 1)
            if (hasattr(node, "end_lineno") and node.end_lineno is not None)
            else 0
        )
        if func_length > 50:
            self.issues.append(
                QualityIssue(
                    severity="warning",
                    issue_type="long_function",
                    line_number=node.lineno,
                    description=f"Function '{node.name}' is {func_length} lines long",
                    suggestion="Consider breaking this function into smaller functions",
                ),
            )

        # Check parameter count
        if len(node.args.args) > 5:
            self.issues.append(
                QualityIssue(
                    severity="warning",
                    issue_type="too_many_parameters",
                    line_number=node.lineno,
                    description=f"Function '{node.name}' has {len(node.args.args)} parameters",
                    suggestion="Consider using a configuration object or breaking the function",
                ),
            )

        # Check for missing docstring
        if not ast.get_docstring(node):
            self.issues.append(
                QualityIssue(
                    severity="info",
                    issue_type="missing_docstring",
                    line_number=node.lineno,
                    description=f"Function '{node.name}' is missing a docstring",
                    suggestion="Add a docstring describing the function's purpose and parameters",
                ),
            )

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Check for missing docstring
        if not ast.get_docstring(node):
            self.issues.append(
                QualityIssue(
                    severity="info",
                    issue_type="missing_docstring",
                    line_number=node.lineno,
                    description=f"Class '{node.name}' is missing a docstring",
                    suggestion="Add a docstring describing the class's purpose",
                ),
            )

        self.generic_visit(node)

    def finalize_analysis(self) -> None:
        """Called after visiting all nodes to check for unused variables."""
        builtin_names = set(dir(builtins))

        for var_name, line_numbers in self.variables.items():
            if (
                var_name not in self.used_variables
                and var_name not in builtin_names
                and not var_name.startswith("_")
            ):  # Ignore private variables
                self.issues.append(
                    QualityIssue(
                        severity="warning",
                        issue_type="unused_variable",
                        line_number=line_numbers[0],
                        description=f"Variable '{var_name}' is assigned but never used",
                        suggestion="Remove the unused variable or use it in the code",
                    ),
                )


class CodeAnalysisTool:
    """
    Real code analysis with AST parsing and safety mechanisms.

    CRITICAL: This performs ACTUAL code analysis - no mocking.
    """

    def __init__(self, safety_config: SafetyConfig | None = None) -> None:
        """Initialize with safety configuration."""
        self.safety_config = safety_config or self._default_safety_config()
        self.analysis_log: list[CodeAnalysisResult] = []

    def _default_safety_config(self) -> SafetyConfig:
        """Create default safety configuration."""
        return SafetyConfig(
            max_file_size=5 * 1024 * 1024,  # 5MB
            timeout_seconds=30,
            max_memory_mb=100,
            allowed_file_extensions=[".py"],
            forbidden_patterns=[
                r"__import__\s*\(",
                r"eval\s*\(",
                r"exec\s*\(",
                r"os\.system\s*\(",
                r"subprocess\.call\s*\(",
            ],
        )

    def _validate_file(self, file_path: str) -> bool:
        """Validate file for safety."""
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            raise ValueError(f"File does not exist: {file_path}")

        # Check file extension
        if path.suffix not in self.safety_config.allowed_file_extensions:
            raise ValueError(f"File extension {path.suffix} not allowed")

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.safety_config.max_file_size:
            raise ValueError(
                f"File size {file_size} exceeds limit {self.safety_config.max_file_size}",
            )

        return True

    def _check_forbidden_patterns(self, source_code: str) -> list[str]:
        """Check for forbidden patterns in source code."""
        warnings = []
        for pattern in self.safety_config.forbidden_patterns:
            if re.search(pattern, source_code, re.IGNORECASE):
                warnings.append(f"Forbidden pattern detected: {pattern}")
        return warnings

    def _log_analysis(
        self,
        operation: str,
        file_path: str,
        success: bool,
        message: str,
        analysis_data: dict[str, Any],
        execution_time: float,
        warnings: list[str] | None = None,
    ) -> CodeAnalysisResult:
        """Log analysis operation for audit trail."""
        result = CodeAnalysisResult(
            success=success,
            file_path=file_path,
            operation=operation,
            message=message,
            analysis_data=analysis_data,
            execution_time=execution_time,
            warnings=warnings or [],
        )
        self.analysis_log.append(result)

        if success:
            logger.info(
                f"CodeAnalysis {operation}: {file_path} - {message} ({execution_time:.2f}s)",
            )
        else:
            logger.error(f"CodeAnalysis {operation} FAILED: {file_path} - {message}")

        return result

    def analyze_file(self, file_path: str) -> CodeAnalysisResult:
        """
        Perform comprehensive analysis of a Python file.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            CodeAnalysisResult with comprehensive analysis data
        """
        start_time = time.time()

        try:
            # Validate file
            self._validate_file(file_path)

            # Read file content
            with open(file_path, encoding="utf-8") as f:
                source_code = f.read()

            # Check for forbidden patterns
            warnings = self._check_forbidden_patterns(source_code)

            # Parse AST
            try:
                tree = ast.parse(source_code, filename=file_path)
            except SyntaxError as e:
                execution_time = time.time() - start_time
                return self._log_analysis(
                    "analyze_file",
                    file_path,
                    False,
                    f"Syntax error: {str(e)}",
                    {},
                    execution_time,
                    warnings,
                )

            # Perform analysis
            analysis_data = self._analyze_ast(tree, source_code.splitlines())

            execution_time = time.time() - start_time

            return self._log_analysis(
                "analyze_file",
                file_path,
                True,
                "Analysis completed successfully",
                analysis_data,
                execution_time,
                warnings,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return self._log_analysis(
                "analyze_file",
                file_path,
                False,
                f"Analysis failed: {str(e)}",
                {},
                execution_time,
            )

    def _analyze_ast(self, tree: ast.AST, source_lines: list[str]) -> dict[str, Any]:
        """Perform comprehensive AST analysis."""

        # Extract functions
        functions = []
        classes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = self._extract_function_info(node, source_lines)
                functions.append(func_info)
            elif isinstance(node, ast.AsyncFunctionDef):
                func_info = self._extract_function_info(
                    node, source_lines, is_async=True
                )
                functions.append(func_info)
            elif isinstance(node, ast.ClassDef):
                class_info = self._extract_class_info(node, source_lines)
                classes.append(class_info)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                import_info = self._extract_import_info(node)
                imports.append(import_info)

        # Security analysis
        security_analyzer = SecurityAnalyzer()
        security_analyzer.visit(tree)

        # Quality analysis
        quality_analyzer = QualityAnalyzer(source_lines)
        quality_analyzer.visit(tree)
        quality_analyzer.finalize_analysis()

        # Overall complexity
        complexity_visitor = CodeComplexityVisitor()
        complexity_visitor.visit(tree)

        # Type annotation coverage
        type_coverage = self._calculate_type_coverage(functions)

        # Code metrics
        metrics = {
            "total_lines": len(source_lines),
            "blank_lines": sum(1 for line in source_lines if not line.strip()),
            "comment_lines": sum(
                1 for line in source_lines if line.strip().startswith("#")
            ),
            "code_lines": len(
                [
                    line
                    for line in source_lines
                    if line.strip() and not line.strip().startswith("#")
                ]
            ),
        }

        # Convert dataclasses to dictionaries for serialization
        functions_dict = []
        for func in functions:
            func_dict = func.__dict__.copy()
            func_dict["complexity"] = func.complexity.__dict__
            functions_dict.append(func_dict)

        classes_dict = []
        for cls in classes:
            cls_dict = cls.__dict__.copy()
            cls_dict["methods"] = [
                {**method.__dict__, "complexity": method.complexity.__dict__}
                for method in cls.methods
            ]
            classes_dict.append(cls_dict)

        return {
            "functions": functions_dict,
            "classes": classes_dict,
            "imports": [imp.__dict__ for imp in imports],
            "security_issues": [issue.__dict__ for issue in security_analyzer.issues],
            "quality_issues": [issue.__dict__ for issue in quality_analyzer.issues],
            "overall_complexity": {
                "cyclomatic_complexity": complexity_visitor.complexity,
                "cognitive_complexity": complexity_visitor.cognitive_complexity,
            },
            "type_coverage": type_coverage,
            "metrics": metrics,
        }

    def _extract_function_info(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_lines: list[str],
        is_async: bool = False,
    ) -> FunctionInfo:
        """Extract information about a function."""
        # Calculate complexity
        complexity_visitor = CodeComplexityVisitor()
        complexity_visitor.visit(node)

        # Calculate lines of code
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        loc = end_line - start_line + 1

        # Calculate maintainability index (simplified)
        # MI = 171 - 5.2 * ln(Halstead Volume) - 0.23 * (Cyclomatic Complexity)
        # - 16.2 * ln(Lines of Code)
        # Simplified version focusing on complexity and LOC
        mi = max(0, 100 - complexity_visitor.complexity * 2 - loc * 0.5)

        complexity = ComplexityMetrics(
            cyclomatic_complexity=complexity_visitor.complexity,
            cognitive_complexity=complexity_visitor.cognitive_complexity,
            lines_of_code=loc,
            maintainability_index=mi,
        )

        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param_str = arg.arg
            if arg.annotation:
                param_str += f": {ast.unparse(arg.annotation)}"
            parameters.append(param_str)

        # Extract return annotation
        return_annotation = None
        if node.returns:
            return_annotation = ast.unparse(node.returns)

        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(ast.unparse(decorator))

        return FunctionInfo(
            name=node.name,
            line_number=start_line,
            end_line=end_line,
            parameters=parameters,
            return_annotation=return_annotation,
            docstring=ast.get_docstring(node),
            complexity=complexity,
            is_async=is_async,
            decorators=decorators,
        )

    def _extract_class_info(
        self, node: ast.ClassDef, source_lines: list[str]
    ) -> ClassInfo:
        """Extract information about a class."""
        # Extract base classes
        base_classes = []
        for base in node.bases:
            base_classes.append(ast.unparse(base))

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._extract_function_info(item, source_lines)
                methods.append(method_info)
            elif isinstance(item, ast.AsyncFunctionDef):
                method_info = self._extract_function_info(
                    item, source_lines, is_async=True
                )
                methods.append(method_info)

        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(ast.unparse(decorator))

        return ClassInfo(
            name=node.name,
            line_number=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            base_classes=base_classes,
            methods=methods,
            docstring=ast.get_docstring(node),
            decorators=decorators,
        )

    def _extract_import_info(
        self, node: Union[ast.Import, ast.ImportFrom]
    ) -> ImportInfo | None:
        """Extract information about an import."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                return ImportInfo(
                    module=alias.name,
                    names=[alias.name],
                    line_number=node.lineno,
                    is_from_import=False,
                    alias=alias.asname,
                )
        else:  # ImportFrom
            names = [alias.name for alias in node.names]
            return ImportInfo(
                module=node.module or "",
                names=names,
                line_number=node.lineno,
                is_from_import=True,
                alias=None,
            )
        return None

    def _calculate_type_coverage(
        self, functions: list[FunctionInfo]
    ) -> dict[str, float]:
        """Calculate type annotation coverage."""
        if not functions:
            return {
                "function_return_coverage": 0.0,
                "parameter_coverage": 0.0,
                "overall_coverage": 0.0,
            }

        # Function return type coverage
        functions_with_return_types = sum(
            1 for func in functions if func.return_annotation
        )
        return_coverage = functions_with_return_types / len(functions) * 100

        # Parameter type coverage
        total_params = sum(len(func.parameters) for func in functions)
        if total_params == 0:
            param_coverage = 100.0
        else:
            typed_params = sum(
                sum(1 for param in func.parameters if ":" in param)
                for func in functions
            )
            param_coverage = typed_params / total_params * 100

        # Overall coverage
        overall_coverage = (return_coverage + param_coverage) / 2

        return {
            "function_return_coverage": return_coverage,
            "parameter_coverage": param_coverage,
            "overall_coverage": overall_coverage,
        }

    def get_analysis_log(self) -> list[CodeAnalysisResult]:
        """Get the analysis log for audit purposes."""
        return self.analysis_log.copy()

    def clear_analysis_log(self) -> None:
        """Clear the analysis log."""
        self.analysis_log.clear()


# Test function to verify real analysis
def test_code_analysis_tool() -> None:
    """Test CodeAnalysisTool with real analysis."""

    logger.info("🔍 Testing Real CodeAnalysisTool")
    logger.info("=" * 50)

    # Create a test Python file
    test_code = '''
"""Test module for code analysis."""

import os
import subprocess
from typing import List, Optional

def unsafe_function(user_input: Any) -> None:
    # This is a security issue
    return eval(user_input)

class TestClass:
    """A test class."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.unused_var = "never used"

    def long_method_with_many_parameters(
        self, a: Any, b: Any, c: Any, d: Any, e: Any, f: Any, g: Any
    ) -> None:
        """This method has too many parameters and is quite long."""
        if a > 0:
            if b > 0:
                if c > 0:
                    for i in range(10):
                        if d > i:
                            while e > 0:
                                try:
                                    result = a + b + c + d + e + f + g
                                    if result > 100:
                                        break
                                    else:
                                        continue
                                except Exception:
                                    pass
                                finally:
                                    e -= 1
        return "complex result"

    async def async_method(self) -> Optional[str]:
        """An async method with proper typing."""
        return self.name

def function_without_docstring() -> None:
    pass

def typed_function(items: list[str]) -> int:
    """A properly typed function."""
    return len(items)
'''

    # Write test file using secure tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        test_file = f.name

    try:
        # Create analyzer
        tool = CodeAnalysisTool()

        # Analyze the test file
        logger.info(f"📁 Analyzing: {test_file}")
        result = tool.analyze_file(test_file)

        logger.info(f"\n📊 Analysis Result: {'✅' if result.success else '❌'}")
        logger.info(f"   Message: {result.message}")
        logger.info(f"   Execution Time: {result.execution_time:.2f}s")

        if result.warnings:
            logger.info(f"   ⚠️ Warnings: {len(result.warnings)}")
            for warning in result.warnings:
                logger.info(f"      - {warning}")

        if result.success:
            data = result.analysis_data

            # Functions
            logger.info(f"\n🔧 Functions Found: {len(data['functions'])}")
            for func in data["functions"]:
                logger.info(
                    f"   - {func['name']} (lines {func['line_number']}-{func['end_line']})"
                )
                logger.info(
                    f"     Complexity: {func['complexity']['cyclomatic_complexity']}"
                )
                logger.info(f"     Parameters: {len(func['parameters'])}")
                logger.info(f"     Return Type: {func['return_annotation'] or 'None'}")

            # Classes
            logger.info(f"\n🏗️ Classes Found: {len(data['classes'])}")
            for cls in data["classes"]:
                logger.info(f"   - {cls['name']} (line {cls['line_number']})")
                logger.info(f"     Methods: {len(cls['methods'])}")
                logger.info(f"     Base Classes: {cls['base_classes']}")

            # Security Issues
            logger.info(f"\n🛡️ Security Issues: {len(data['security_issues'])}")
            for issue in data["security_issues"]:
                logger.info(
                    f"   - {issue['severity'].upper()}: {issue['description']} "
                    f"(line {issue['line_number']})",
                )

            # Quality Issues
            logger.info(f"\n📈 Quality Issues: {len(data['quality_issues'])}")
            for issue in data["quality_issues"]:
                logger.info(
                    f"   - {issue['severity'].upper()}: {issue['description']} "
                    f"(line {issue['line_number']})",
                )

            # Type Coverage
            logger.info("\n📝 Type Coverage:")
            coverage = data["type_coverage"]
            logger.info(
                f"   - Function Returns: {coverage['function_return_coverage']:.1f}%"
            )
            logger.info(f"   - Parameters: {coverage['parameter_coverage']:.1f}%")
            logger.info(f"   - Overall: {coverage['overall_coverage']:.1f}%")

            # Metrics
            logger.info("\n📊 Code Metrics:")
            metrics = data["metrics"]
            logger.info(f"   - Total Lines: {metrics['total_lines']}")
            logger.info(f"   - Code Lines: {metrics['code_lines']}")
            logger.info(f"   - Comment Lines: {metrics['comment_lines']}")
            logger.info(f"   - Blank Lines: {metrics['blank_lines']}")

            # Overall Complexity
            logger.info("\n🧮 Overall Complexity:")
            complexity = data["overall_complexity"]
            logger.info(f"   - Cyclomatic: {complexity['cyclomatic_complexity']}")
            logger.info(f"   - Cognitive: {complexity['cognitive_complexity']}")

        logger.info("\n🎯 Analysis completed successfully!")

    finally:
        # Clean up
        if Path(test_file).exists():
            Path(test_file).unlink()


if __name__ == "__main__":
    test_code_analysis_tool()
