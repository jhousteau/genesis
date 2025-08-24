"""
ADK-Compliant Code Analysis Tool for SOLVE Agents

Implements real AST parsing and code analysis following the Google ADK BaseTool pattern.
Based on adk-python/src/google/adk/tools/base_tool.py and best practices.

NO MOCKS, NO STUBS - REAL AST PARSING AND ANALYSIS ONLY
"""

import ast
import builtins
import logging
import re
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Union

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

logger = logging.getLogger(__name__)


class CodeAnalysisADKTool(BaseTool):
    """
    ADK-compliant code analysis tool with real AST parsing and metrics.

    This tool provides comprehensive Python code analysis including:
    - AST parsing and structure extraction
    - Cyclomatic and cognitive complexity metrics
    - Security vulnerability detection
    - Code quality issue identification
    - Type annotation coverage analysis
    - Import dependency tracking
    """

    def __init__(self) -> None:
        """Initialize the code analysis tool."""
        super().__init__(
            name="code_analysis",
            description="""Analyze Python code files to extract structure, metrics, and issues.

            This tool performs comprehensive static analysis on Python source files including:
            - Function and class extraction with complexity metrics
            - Security vulnerability detection (eval, exec, SQL injection, etc.)
            - Code quality issues (long functions, missing docstrings, unused variables)
            - Type annotation coverage statistics
            - Import dependency analysis
            - Lines of code metrics

            Returns a detailed analysis report with actionable insights.""",
        )

        # Safety configuration
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.allowed_extensions = [".py"]
        self.forbidden_patterns = [
            r"__import__\s*\(",
            r"eval\s*\(",
            r"exec\s*\(",
            r"os\.system\s*\(",
            r"subprocess\.call\s*\(",
        ]

        # Analysis history for context
        self.analysis_history: list[dict[str, Any]] = []

    def _get_declaration(self) -> types.FunctionDeclaration | None:
        """Get the function declaration for this tool."""
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_path": types.Schema(
                        type=types.Type.STRING,
                        description="The absolute path to the Python file to analyze",
                    ),
                    "analysis_type": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Type of analysis to perform (optional). Options: 'full' "
                            "(default), 'security', 'quality', 'structure', 'metrics'"
                        ),
                        enum=["full", "security", "quality", "structure", "metrics"],
                    ),
                    "include_source": types.Schema(
                        type=types.Type.BOOLEAN,
                        description=(
                            "Whether to include source code snippets in issues (default: false)"
                        ),
                    ),
                },
                required=["file_path"],
            ),
        )

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """
        Run the code analysis tool.

        Args:
            args: Dictionary containing:
                - file_path: Path to the Python file to analyze
                - analysis_type: Type of analysis
                  ('full', 'security', 'quality', 'structure', 'metrics')
                - include_source: Whether to include source snippets
            tool_context: Optional ADK tool context with history and state

        Returns:
            Dictionary with analysis results or error information
        """
        file_path = args.get("file_path")
        if not file_path:
            return {"error": "file_path is required"}

        analysis_type = args.get("analysis_type", "full")
        include_source = args.get("include_source", False)

        start_time = time.time()

        try:
            # Validate file
            path = Path(file_path)
            if not path.exists():
                return {"error": f"File does not exist: {file_path}"}

            if path.suffix not in self.allowed_extensions:
                return {
                    "error": (
                        f"File extension {path.suffix} not allowed. Only .py files are supported."
                    ),
                }

            file_size = path.stat().st_size
            if file_size > self.max_file_size:
                return {
                    "error": f"File size {file_size} exceeds limit {self.max_file_size}"
                }

            # Read and parse file
            with open(file_path, encoding="utf-8") as f:
                source_code = f.read()

            # Check for forbidden patterns
            warnings = []
            for pattern in self.forbidden_patterns:
                if re.search(pattern, source_code, re.IGNORECASE):
                    warnings.append(
                        f"Potentially dangerous pattern detected: {pattern}"
                    )

            # Parse AST
            try:
                tree = ast.parse(source_code, filename=file_path)
            except SyntaxError as e:
                return {
                    "error": f"Syntax error in file: {str(e)}",
                    "line": e.lineno,
                    "offset": e.offset,
                    "text": e.text,
                }

            source_lines = source_code.splitlines()

            # Perform requested analysis
            result = {
                "file_path": file_path,
                "analysis_type": analysis_type,
                "execution_time": 0,  # Will be set at the end
                "warnings": warnings,
            }

            if analysis_type in ["full", "structure"]:
                result.update(self._analyze_structure(tree, source_lines))

            if analysis_type in ["full", "security"]:
                result["security_issues"] = self._analyze_security(
                    tree,
                    source_lines,
                    include_source,
                )

            if analysis_type in ["full", "quality"]:
                result["quality_issues"] = self._analyze_quality(
                    tree, source_lines, include_source
                )

            if analysis_type in ["full", "metrics"]:
                result["metrics"] = self._analyze_metrics(tree, source_lines)
                result["complexity"] = self._analyze_complexity(tree)

            # Calculate execution time
            execution_time = time.time() - start_time
            result["execution_time"] = round(execution_time, 3)

            # Store in history for context
            self.analysis_history.append(
                {
                    "timestamp": time.time(),
                    "file_path": file_path,
                    "analysis_type": analysis_type,
                    "issues_found": len(result.get("security_issues", []))
                    + len(result.get("quality_issues", [])),
                },
            )

            # Keep only last 10 analyses in history
            if len(self.analysis_history) > 10:
                self.analysis_history = self.analysis_history[-10:]

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "error": f"Analysis failed: {str(e)}",
                "file_path": file_path,
                "execution_time": round(execution_time, 3),
            }

    def _analyze_structure(
        self, tree: ast.AST, source_lines: list[str]
    ) -> dict[str, Any]:
        """Extract structural information from the AST."""
        functions = []
        classes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(self._extract_function_info(node))
            elif isinstance(node, ast.AsyncFunctionDef):
                func_info = self._extract_function_info(node)
                func_info["is_async"] = True
                functions.append(func_info)
            elif isinstance(node, ast.ClassDef):
                classes.append(self._extract_class_info(node))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                import_info = self._extract_import_info(node)
                if import_info:
                    imports.append(import_info)

        # Calculate type coverage
        type_coverage = self._calculate_type_coverage(functions)

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "type_coverage": type_coverage,
        }

    def _analyze_security(
        self,
        tree: ast.AST,
        source_lines: list[str],
        include_source: bool,
    ) -> list[dict[str, Any]]:
        """Analyze code for security vulnerabilities."""
        issues = []

        # Dangerous function calls
        dangerous_functions = {
            "eval": "critical",
            "exec": "critical",
            "compile": "high",
            "__import__": "high",
            "open": "medium",
            "input": "low",
            "pickle.loads": "critical",
            "pickle.load": "critical",
            "yaml.load": "high",
        }

        # Dangerous imports
        dangerous_modules = {
            "os": "medium",
            "subprocess": "high",
            "pickle": "high",
            "marshal": "medium",
            "shelve": "medium",
        }

        class SecurityVisitor(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call) -> None:
                # Check dangerous function calls
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        func_name = f"{node.func.value.id}.{node.func.attr}"

                if func_name and func_name in dangerous_functions:
                    issue = {
                        "severity": dangerous_functions[func_name],
                        "type": "dangerous_function",
                        "line": node.lineno,
                        "column": node.col_offset,
                        "function": func_name,
                        "description": f"Use of potentially dangerous function '{func_name}'",
                        "recommendation": (
                            f"Avoid using '{func_name}' or ensure proper input validation"
                        ),
                    }
                    if include_source and node.lineno <= len(source_lines):
                        issue["source"] = source_lines[node.lineno - 1].strip()
                    issues.append(issue)

                # Check for SQL injection patterns
                if isinstance(node.func, ast.Attribute) and node.func.attr in [
                    "execute",
                    "executemany",
                ]:
                    for arg in node.args:
                        if isinstance(
                            arg,
                            (ast.BinOp, ast.JoinedStr),
                        ) and self._contains_string_formatting(arg):
                            issue = {
                                "severity": "high",
                                "type": "sql_injection",
                                "line": node.lineno,
                                "column": node.col_offset,
                                "description": "Potential SQL injection vulnerability",
                                "recommendation": (
                                    "Use parameterized queries instead of string concatenation"
                                ),
                            }
                            if include_source and node.lineno <= len(source_lines):
                                issue["source"] = source_lines[node.lineno - 1].strip()
                            issues.append(issue)

                self.generic_visit(node)

            def _contains_string_formatting(self, node: ast.AST) -> bool:
                """Check if node contains string formatting that could be dangerous."""
                if isinstance(node, ast.BinOp) and isinstance(
                    node.op, (ast.Add, ast.Mod)
                ):
                    return True
                return isinstance(node, ast.JoinedStr)  # f-string

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    if alias.name in dangerous_modules:
                        issue = {
                            "severity": dangerous_modules[alias.name],
                            "type": "dangerous_import",
                            "line": node.lineno,
                            "column": node.col_offset,
                            "module": alias.name,
                            "description": f"Import of potentially dangerous module '{alias.name}'",
                            "recommendation": f"Ensure safe usage of '{alias.name}' module",
                        }
                        if include_source and node.lineno <= len(source_lines):
                            issue["source"] = source_lines[node.lineno - 1].strip()
                        issues.append(issue)
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                if node.module and node.module in dangerous_modules:
                    issue = {
                        "severity": dangerous_modules[node.module],
                        "type": "dangerous_import",
                        "line": node.lineno,
                        "column": node.col_offset,
                        "module": node.module,
                        "description": f"Import from potentially dangerous module '{node.module}'",
                        "recommendation": f"Ensure safe usage of '{node.module}' module",
                    }
                    if include_source and node.lineno <= len(source_lines):
                        issue["source"] = source_lines[node.lineno - 1].strip()
                    issues.append(issue)
                self.generic_visit(node)

        visitor = SecurityVisitor()
        visitor.visit(tree)

        return issues

    def _analyze_quality(
        self,
        tree: ast.AST,
        source_lines: list[str],
        include_source: bool,
    ) -> list[dict[str, Any]]:
        """Analyze code quality issues."""
        issues = []

        # Track variable usage
        variables = defaultdict(list)  # var_name -> [(line, is_assignment)]
        used_variables = set()

        class QualityVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.current_function: str | None = None
                self.function_stack: list[str] = []

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._check_function(node)
                self.function_stack.append(node.name)
                self.current_function = node.name
                self.generic_visit(node)
                self.function_stack.pop()
                self.current_function = (
                    self.function_stack[-1] if self.function_stack else None
                )

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._check_function(node)
                self.function_stack.append(node.name)
                self.current_function = node.name
                self.generic_visit(node)
                self.function_stack.pop()
                self.current_function = (
                    self.function_stack[-1] if self.function_stack else None
                )

            def _check_function(
                self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
            ) -> None:
                # Check function length
                if hasattr(node, "end_lineno") and node.end_lineno is not None:
                    func_length = node.end_lineno - node.lineno + 1
                    if func_length > 50:
                        issue = {
                            "severity": "warning",
                            "type": "long_function",
                            "line": node.lineno,
                            "column": node.col_offset,
                            "function": node.name,
                            "length": func_length,
                            "description": f"Function '{node.name}' is {func_length} lines long",
                            "recommendation": (
                                "Consider breaking this function into smaller functions"
                            ),
                        }
                        if include_source:
                            issue["source_preview"] = (
                                f"def {node.name}(...): # {func_length} lines"
                            )
                        issues.append(issue)

                # Check parameter count
                param_count = (
                    len(node.args.args)
                    + len(node.args.posonlyargs)
                    + len(node.args.kwonlyargs)
                )
                if param_count > 5:
                    issue = {
                        "severity": "warning",
                        "type": "too_many_parameters",
                        "line": node.lineno,
                        "column": node.col_offset,
                        "function": node.name,
                        "parameter_count": param_count,
                        "description": f"Function '{node.name}' has {param_count} parameters",
                        "recommendation": (
                            "Consider using a configuration object or breaking the function"
                        ),
                    }
                    issues.append(issue)

                # Check for missing docstring
                if not ast.get_docstring(node):
                    issue = {
                        "severity": "info",
                        "type": "missing_docstring",
                        "line": node.lineno,
                        "column": node.col_offset,
                        "function": node.name,
                        "description": f"Function '{node.name}' is missing a docstring",
                        "recommendation": (
                            "Add a docstring describing the function's purpose and parameters"
                        ),
                    }
                    issues.append(issue)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                # Check for missing docstring
                if not ast.get_docstring(node):
                    issue = {
                        "severity": "info",
                        "type": "missing_docstring",
                        "line": node.lineno,
                        "column": node.col_offset,
                        "class": node.name,
                        "description": f"Class '{node.name}' is missing a docstring",
                        "recommendation": "Add a docstring describing the class's purpose",
                    }
                    issues.append(issue)
                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Store):
                    # Variable assignment
                    variables[node.id].append((node.lineno, True))
                elif isinstance(node.ctx, ast.Load):
                    # Variable usage
                    used_variables.add(node.id)
                self.generic_visit(node)

        visitor = QualityVisitor()
        visitor.visit(tree)

        # Check for unused variables
        builtin_names = set(dir(builtins))
        for var_name, occurrences in variables.items():
            if (
                var_name not in used_variables
                and var_name not in builtin_names
                and not var_name.startswith("_")
                and var_name not in ["self", "cls"]
            ):
                first_line = occurrences[0][0]
                issue = {
                    "severity": "warning",
                    "type": "unused_variable",
                    "line": first_line,
                    "variable": var_name,
                    "description": f"Variable '{var_name}' is assigned but never used",
                    "recommendation": "Remove the unused variable or use it in the code",
                }
                if include_source and first_line <= len(source_lines):
                    issue["source"] = source_lines[first_line - 1].strip()
                issues.append(issue)

        return issues

    def _analyze_metrics(
        self, tree: ast.AST, source_lines: list[str]
    ) -> dict[str, Any]:
        """Calculate code metrics."""
        total_lines = len(source_lines)
        blank_lines = sum(1 for line in source_lines if not line.strip())
        comment_lines = sum(1 for line in source_lines if line.strip().startswith("#"))
        code_lines = total_lines - blank_lines - comment_lines

        # Count docstrings
        docstring_lines = 0
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
            ):
                docstring = ast.get_docstring(node)
                if docstring:
                    docstring_lines += len(docstring.splitlines())

        return {
            "total_lines": total_lines,
            "code_lines": code_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "docstring_lines": docstring_lines,
            "code_to_comment_ratio": round(
                code_lines / max(comment_lines + docstring_lines, 1), 2
            ),
        }

    def _analyze_complexity(self, tree: ast.AST) -> dict[str, Any]:
        """Calculate complexity metrics for the entire module."""

        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.complexity = 1  # Base complexity
                self.cognitive_complexity = 0
                self.nesting_level = 0
                self.max_nesting = 0

            def visit_If(self, node: ast.If) -> None:
                self.complexity += 1
                self.cognitive_complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.max_nesting = max(self.max_nesting, self.nesting_level)
                self.generic_visit(node)
                self.nesting_level -= 1

            def visit_While(self, node: ast.While) -> None:
                self.complexity += 1
                self.cognitive_complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.max_nesting = max(self.max_nesting, self.nesting_level)
                self.generic_visit(node)
                self.nesting_level -= 1

            def visit_For(self, node: ast.For) -> None:
                self.complexity += 1
                self.cognitive_complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.max_nesting = max(self.max_nesting, self.nesting_level)
                self.generic_visit(node)
                self.nesting_level -= 1

            def visit_Try(self, node: ast.Try) -> None:
                self.complexity += len(node.handlers)
                self.cognitive_complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.max_nesting = max(self.max_nesting, self.nesting_level)
                self.generic_visit(node)
                self.nesting_level -= 1

            def visit_With(self, node: ast.With) -> None:
                self.complexity += 1
                self.cognitive_complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.max_nesting = max(self.max_nesting, self.nesting_level)
                self.generic_visit(node)
                self.nesting_level -= 1

            def visit_BoolOp(self, node: ast.BoolOp) -> None:
                self.complexity += len(node.values) - 1
                self.generic_visit(node)

        visitor = ComplexityVisitor()
        visitor.visit(tree)

        return {
            "cyclomatic_complexity": visitor.complexity,
            "cognitive_complexity": visitor.cognitive_complexity,
            "max_nesting_depth": visitor.max_nesting,
        }

    def _extract_function_info(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
    ) -> dict[str, Any]:
        """Extract information about a function."""

        # Calculate complexity for this function
        class FunctionComplexityVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.complexity = 1
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

            def visit_BoolOp(self, node: ast.BoolOp) -> None:
                self.complexity += len(node.values) - 1
                self.generic_visit(node)

        complexity_visitor = FunctionComplexityVisitor()
        complexity_visitor.visit(node)

        # Extract parameters with type annotations
        parameters = []
        defaults_start = len(node.args.args) - len(node.args.defaults)

        for i, arg in enumerate(node.args.args):
            param_info = {"name": arg.arg}
            if arg.annotation:
                param_info["type"] = ast.unparse(arg.annotation)
            if i >= defaults_start:
                default_idx = i - defaults_start
                param_info["default"] = ast.unparse(node.args.defaults[default_idx])
            parameters.append(param_info)

        # Extract return type
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        # Extract decorators
        decorators = [ast.unparse(dec) for dec in node.decorator_list]

        return {
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "parameters": parameters,
            "return_type": return_type,
            "decorators": decorators,
            "docstring": ast.get_docstring(node),
            "complexity": {
                "cyclomatic": complexity_visitor.complexity,
                "cognitive": complexity_visitor.cognitive_complexity,
            },
        }

    def _extract_class_info(self, node: ast.ClassDef) -> dict[str, Any]:
        """Extract information about a class."""
        # Extract base classes
        base_classes = [ast.unparse(base) for base in node.bases]

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function_info(item))

        # Extract decorators
        decorators = [ast.unparse(dec) for dec in node.decorator_list]

        # Extract class variables
        class_vars = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                var_info = {"name": item.target.id}
                if item.annotation:
                    var_info["type"] = ast.unparse(item.annotation)
                if item.value:
                    var_info["default"] = ast.unparse(item.value)
                class_vars.append(var_info)

        return {
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "base_classes": base_classes,
            "decorators": decorators,
            "docstring": ast.get_docstring(node),
            "methods": methods,
            "class_variables": class_vars,
        }

    def _extract_import_info(
        self,
        node: Union[ast.Import, ast.ImportFrom],
    ) -> dict[str, Any] | None:
        """Extract import information."""
        if isinstance(node, ast.Import):
            imports = []
            for alias in node.names:
                imports.append({"name": alias.name, "alias": alias.asname})
            return {"type": "import", "line": node.lineno, "imports": imports}
        else:  # ImportFrom
            names = []
            for alias in node.names:
                names.append({"name": alias.name, "alias": alias.asname})
            return {
                "type": "from_import",
                "line": node.lineno,
                "module": node.module or "",
                "level": node.level,  # Number of dots (relative import)
                "names": names,
            }

    def _calculate_type_coverage(
        self, functions: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Calculate type annotation coverage statistics."""
        if not functions:
            return {
                "functions_with_return_type": 0.0,
                "parameters_with_type": 0.0,
                "overall_coverage": 0.0,
            }

        # Return type coverage
        functions_with_return = sum(1 for f in functions if f.get("return_type"))
        return_coverage = (functions_with_return / len(functions)) * 100

        # Parameter type coverage
        total_params = 0
        typed_params = 0
        for func in functions:
            for param in func.get("parameters", []):
                total_params += 1
                if "type" in param:
                    typed_params += 1

        param_coverage = (typed_params / max(total_params, 1)) * 100

        return {
            "functions_with_return_type": round(return_coverage, 1),
            "parameters_with_type": round(param_coverage, 1),
            "overall_coverage": round((return_coverage + param_coverage) / 2, 1),
        }


# Direct function for use with FunctionTool if needed
async def analyze_code(
    file_path: str,
    analysis_type: str = "full",
    include_source: bool = False,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Analyze Python code using the ADK Code Analysis Tool.

    Args:
        file_path: Path to the Python file to analyze
        analysis_type: Type of analysis ('full', 'security', 'quality', 'structure', 'metrics')
        include_source: Whether to include source code snippets in issues
        tool_context: Optional ADK tool context

    Returns:
        Analysis results dictionary
    """
    tool = CodeAnalysisADKTool()

    # If no context provided, use the tool directly without context
    if tool_context is None:
        # Direct invocation without ADK context
        return await tool.run_async(
            args={
                "file_path": file_path,
                "analysis_type": analysis_type,
                "include_source": include_source,
            },
            tool_context=None,  # Will be handled internally
        )

    return await tool.run_async(
        args={
            "file_path": file_path,
            "analysis_type": analysis_type,
            "include_source": include_source,
        },
        tool_context=tool_context,
    )


# Test function
def test_code_analysis_adk_tool() -> None:
    """Test the ADK-compliant code analysis tool."""
    import asyncio

    # Create test code with various issues
    test_code = '''"""Test module for ADK code analysis."""

import os
import subprocess
from typing import List, Optional
import pickle

def unsafe_function(user_input):
    """This function has security issues."""
    # Direct eval - critical security issue
    result = eval(user_input)

    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + str(user_input)
    cursor.execute(query)

    return result

class TestClass:
    """A test class with various issues."""

    name: str
    unused_var: int = 42

    def __init__(self, name: str):
        self.name = name
        self.another_unused = "never used"

    def long_method_with_many_parameters(self, a, b, c, d, e, f, g):
        """This method has too many parameters and high complexity."""
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

    async def typed_async_method(self, items: List[str]) -> Optional[int]:
        """A properly typed async method."""
        if items:
            return len(items)
        return None

def function_without_docstring():
    unused_local = "This variable is never used"
    pass

@property
def typed_function(items: List[str]) -> int:
    """A properly typed function with decorator."""
    return len(items)

# Load pickle - security issue
with open("data.pkl", "rb") as f:
    data = pickle.load(f)
'''

    # Write test file using secure temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        test_file = temp_file.name
        temp_file.write(test_code)

    try:
        # Create tool
        tool = CodeAnalysisADKTool()

        # Test full analysis
        async def run_test() -> None:
            # Test with full analysis
            result = await tool.run_async(
                args={
                    "file_path": test_file,
                    "analysis_type": "full",
                    "include_source": True,
                },
                tool_context=None,  # No context needed for testing
            )

            if "error" in result:
                return

            # Display structure
            if "functions" in result:
                for _func in result["functions"]:
                    pass

            if "classes" in result:
                for _cls in result["classes"]:
                    pass

            # Display issues
            if "security_issues" in result:
                for issue in result["security_issues"][:5]:  # Show first 5
                    if "source" in issue:
                        pass

            if "quality_issues" in result:
                for _ in result["quality_issues"][:5]:  # Show first 5
                    pass

            # Display metrics
            if "metrics" in result:
                result["metrics"]

            if "complexity" in result:
                result["complexity"]

            if "type_coverage" in result:
                result["type_coverage"]

            # Test security-only analysis

            security_result = await tool.run_async(
                args={"file_path": test_file, "analysis_type": "security"},
                tool_context=None,  # No context needed for testing
            )

            if "security_issues" in security_result:
                pass

        # Run the async test
        asyncio.run(run_test())

    finally:
        # Clean up
        if Path(test_file).exists():
            Path(test_file).unlink()


if __name__ == "__main__":
    test_code_analysis_adk_tool()
