#!/usr/bin/env python3
"""
Automated Test Runner for Universal Project Platform
Comprehensive test execution with reporting, coverage analysis, and CI/CD integration
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Test configuration
TEST_CONFIG = {
    "test_suites": {
        "unit": {
            "files": ["test_cli_commands.py", "test_registry_operations.py"],
            "timeout": 300,
            "parallel": True,
        },
        "integration": {
            "files": [
                "test_terraform_integration.py",
                "test_monitoring_system.py",
                "test_deployment_pipeline.py",
                "test_cross_component_communication.py",
            ],
            "timeout": 600,
            "parallel": False,
        },
        "e2e": {
            "files": ["test_end_to_end_scenarios.py"],
            "timeout": 1800,
            "parallel": False,
        },
        "error_handling": {
            "files": ["test_error_handling_edge_cases.py"],
            "timeout": 900,
            "parallel": True,
        },
        "existing": {
            "files": [
                "test_complete_integration.py",
                "integration_tests.py",
                "end_to_end_tests.py",
                "comprehensive_validation.py",
            ],
            "timeout": 600,
            "parallel": False,
        },
    },
    "coverage": {
        "minimum_threshold": 80.0,
        "critical_threshold": 100.0,
        "exclude_patterns": [
            "*/tests/*",
            "*/venv/*",
            "*/__pycache__/*",
            "*/migrations/*",
        ],
    },
    "reporting": {
        "formats": ["console", "html", "json", "junit"],
        "output_dir": "test_reports",
    },
}


class TestRunner:
    """Automated test runner with comprehensive reporting"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or TEST_CONFIG
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
        self.reports_dir = self.test_dir / self.config["reporting"]["output_dir"]
        self.reports_dir.mkdir(exist_ok=True)

        # Test execution state
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.interrupted = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully"""
        print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
        self.interrupted = True

    def run_all_tests(
        self,
        suites: Optional[List[str]] = None,
        parallel: bool = True,
        coverage: bool = True,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """Run all test suites with comprehensive reporting"""

        print("🧪 Universal Project Platform Test Runner")
        print("=" * 80)

        self.start_time = datetime.now()

        # Determine which test suites to run
        if suites is None:
            suites = list(self.config["test_suites"].keys())

        print(f"📋 Running test suites: {', '.join(suites)}")
        print(f"⚡ Parallel execution: {parallel}")
        print(f"📊 Coverage analysis: {coverage}")
        print(f"🔍 Verbose output: {verbose}")
        print()

        # Setup test environment
        self._setup_test_environment()

        # Run test suites
        for suite_name in suites:
            if self.interrupted:
                break

            print(f"🏃 Running {suite_name} tests...")
            suite_result = self._run_test_suite(suite_name, verbose, coverage)
            self.test_results[suite_name] = suite_result

            # Print immediate results
            self._print_suite_results(suite_name, suite_result)
            print()

        self.end_time = datetime.now()

        # Generate comprehensive reports
        self._generate_reports()

        # Print final summary
        self._print_final_summary()

        return self.test_results

    def _setup_test_environment(self):
        """Setup test environment and dependencies"""
        print("🔧 Setting up test environment...")

        # Ensure pytest is available
        try:
            import pytest
        except ImportError:
            print("❌ pytest not found. Installing...")
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "pytest",
                    "pytest-cov",
                    "pytest-html",
                    "pytest-json-report",
                ]
            )

        # Setup Python path
        sys.path.insert(0, str(self.project_root))
        sys.path.insert(0, str(self.project_root / "lib" / "python"))
        sys.path.insert(0, str(self.project_root / "bin"))

        # Create temporary directories
        temp_dir = self.test_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        print("✅ Test environment ready")

    def _run_test_suite(
        self, suite_name: str, verbose: bool, coverage: bool
    ) -> Dict[str, Any]:
        """Run a specific test suite"""
        suite_config = self.config["test_suites"][suite_name]

        result = {
            "suite_name": suite_name,
            "start_time": datetime.now(),
            "end_time": None,
            "duration": None,
            "files": suite_config["files"],
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "coverage": None,
            "success": False,
            "output": "",
            "error_output": "",
        }

        try:
            # Build pytest command
            pytest_args = self._build_pytest_args(
                suite_config, verbose, coverage, suite_name
            )

            # Run tests
            start_time = time.time()
            process = subprocess.run(
                pytest_args,
                cwd=self.test_dir,
                capture_output=True,
                text=True,
                timeout=suite_config.get("timeout", 600),
            )
            end_time = time.time()

            result["end_time"] = datetime.now()
            result["duration"] = end_time - start_time
            result["output"] = process.stdout
            result["error_output"] = process.stderr
            result["return_code"] = process.returncode

            # Parse pytest output for test counts
            self._parse_pytest_output(result)

            # Load coverage data if available
            if coverage:
                result["coverage"] = self._load_coverage_data(suite_name)

            result["success"] = process.returncode == 0

        except subprocess.TimeoutExpired:
            result["end_time"] = datetime.now()
            result["duration"] = suite_config.get("timeout", 600)
            result["error_output"] = (
                f"Test suite timed out after {suite_config.get('timeout', 600)} seconds"
            )
            result["success"] = False

        except Exception as e:
            result["end_time"] = datetime.now()
            result["error_output"] = str(e)
            result["success"] = False

        return result

    def _build_pytest_args(
        self, suite_config: Dict, verbose: bool, coverage: bool, suite_name: str
    ) -> List[str]:
        """Build pytest command arguments"""
        args = [sys.executable, "-m", "pytest"]

        # Add test files
        for test_file in suite_config["files"]:
            test_path = self.test_dir / test_file
            if test_path.exists():
                args.append(str(test_path))

        # Verbosity
        if verbose:
            args.extend(["-v", "-s"])

        # Coverage
        if coverage:
            args.extend(
                [
                    "--cov=" + str(self.project_root),
                    "--cov-report=html:"
                    + str(self.reports_dir / f"coverage_{suite_name}"),
                    "--cov-report=json:"
                    + str(self.reports_dir / f"coverage_{suite_name}.json"),
                    "--cov-report=term",
                ]
            )

            # Add coverage exclusions
            for pattern in self.config["coverage"]["exclude_patterns"]:
                args.append(f"--cov-omit={pattern}")

        # Output formats
        args.extend(
            [
                "--html=" + str(self.reports_dir / f"report_{suite_name}.html"),
                "--json-report",
                "--json-report-file="
                + str(self.reports_dir / f"report_{suite_name}.json"),
                "--junit-xml=" + str(self.reports_dir / f"junit_{suite_name}.xml"),
            ]
        )

        # Parallel execution
        if suite_config.get("parallel", False):
            args.extend(["-n", "auto"])

        # Additional pytest arguments
        args.extend(["--tb=short", "--strict-markers", "--strict-config"])

        return args

    def _parse_pytest_output(self, result: Dict[str, Any]):
        """Parse pytest output for test statistics"""
        output = result["output"]

        # Look for pytest summary line
        lines = output.split("\n")
        for line in lines:
            if "failed" in line and "passed" in line:
                # Parse line like: "5 failed, 10 passed, 2 skipped in 30.0s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "failed," and i > 0:
                        result["failed"] = int(parts[i - 1])
                    elif part == "passed," and i > 0:
                        result["passed"] = int(parts[i - 1])
                    elif part == "skipped" and i > 0:
                        result["skipped"] = int(parts[i - 1])
                    elif part == "error," and i > 0:
                        result["errors"] = int(parts[i - 1])
                break
            elif "passed" in line and ("failed" not in line):
                # Handle "X passed in Y.Ys" format
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        result["passed"] = int(parts[i - 1])
                        break

    def _load_coverage_data(self, suite_name: str) -> Optional[Dict[str, Any]]:
        """Load coverage data from JSON report"""
        coverage_file = self.reports_dir / f"coverage_{suite_name}.json"

        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                return {
                    "total_coverage": coverage_data.get("totals", {}).get(
                        "percent_covered", 0
                    ),
                    "lines_covered": coverage_data.get("totals", {}).get(
                        "covered_lines", 0
                    ),
                    "lines_total": coverage_data.get("totals", {}).get(
                        "num_statements", 0
                    ),
                    "missing_lines": coverage_data.get("totals", {}).get(
                        "missing_lines", 0
                    ),
                    "files": len(coverage_data.get("files", {})),
                }
            except Exception as e:
                print(f"⚠️  Failed to load coverage data: {e}")

        return None

    def _print_suite_results(self, suite_name: str, result: Dict[str, Any]):
        """Print results for a test suite"""
        duration = result.get("duration", 0)

        if result["success"]:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"

        print(f"{status} {suite_name} ({duration:.1f}s)")
        print(
            f"   Tests: {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped"
        )

        if result.get("coverage"):
            cov = result["coverage"]
            coverage_pct = cov["total_coverage"]
            coverage_status = (
                "✅"
                if coverage_pct >= self.config["coverage"]["minimum_threshold"]
                else "⚠️ "
            )
            print(
                f"   Coverage: {coverage_status} {coverage_pct:.1f}% ({cov['lines_covered']}/{cov['lines_total']} lines)"
            )

        if result["failed"] > 0 or result["errors"] > 0:
            print(
                f"   ⚠️  Check detailed report: {self.reports_dir}/report_{suite_name}.html"
            )

    def _generate_reports(self):
        """Generate comprehensive test reports"""
        print("📊 Generating comprehensive reports...")

        # Generate summary report
        self._generate_summary_report()

        # Generate coverage report
        self._generate_coverage_report()

        # Generate CI/CD reports
        self._generate_ci_reports()

        print(f"📁 Reports generated in: {self.reports_dir}")

    def _generate_summary_report(self):
        """Generate HTML summary report"""
        total_duration = (
            (self.end_time - self.start_time).total_seconds()
            if self.end_time and self.start_time
            else 0
        )

        summary = {
            "execution_time": self.start_time.isoformat() if self.start_time else None,
            "total_duration": total_duration,
            "suites": len(self.test_results),
            "total_tests": sum(
                r["passed"] + r["failed"] + r["skipped"]
                for r in self.test_results.values()
            ),
            "total_passed": sum(r["passed"] for r in self.test_results.values()),
            "total_failed": sum(r["failed"] for r in self.test_results.values()),
            "total_skipped": sum(r["skipped"] for r in self.test_results.values()),
            "success_rate": 0,
            "suite_results": self.test_results,
        }

        if summary["total_tests"] > 0:
            summary["success_rate"] = (
                summary["total_passed"] / summary["total_tests"]
            ) * 100

        # Generate JSON report
        with open(self.reports_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        # Generate HTML report
        html_content = self._generate_html_summary(summary)
        with open(self.reports_dir / "summary.html", "w") as f:
            f.write(html_content)

    def _generate_html_summary(self, summary: Dict[str, Any]) -> str:
        """Generate HTML summary report"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Summary</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .metrics {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; flex: 1; }}
        .success {{ background: #d4edda; }}
        .warning {{ background: #fff3cd; }}
        .danger {{ background: #f8d7da; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #f8f9fa; }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .skipped {{ color: #6c757d; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Universal Project Platform Test Results</h1>
        <p>Execution Time: {summary["execution_time"]}</p>
        <p>Total Duration: {summary["total_duration"]:.1f} seconds</p>
    </div>
    
    <div class="metrics">
        <div class="metric {"success" if summary["success_rate"] >= 90 else "warning" if summary["success_rate"] >= 70 else "danger"}">
            <h3>Success Rate</h3>
            <p style="font-size: 24px; margin: 0;">{summary["success_rate"]:.1f}%</p>
        </div>
        <div class="metric">
            <h3>Total Tests</h3>
            <p style="font-size: 24px; margin: 0;">{summary["total_tests"]}</p>
        </div>
        <div class="metric success">
            <h3>Passed</h3>
            <p style="font-size: 24px; margin: 0;">{summary["total_passed"]}</p>
        </div>
        <div class="metric {"warning" if summary["total_failed"] > 0 else "success"}">
            <h3>Failed</h3>
            <p style="font-size: 24px; margin: 0;">{summary["total_failed"]}</p>
        </div>
        <div class="metric">
            <h3>Skipped</h3>
            <p style="font-size: 24px; margin: 0;">{summary["total_skipped"]}</p>
        </div>
    </div>
    
    <h2>Test Suite Results</h2>
    <table>
        <thead>
            <tr>
                <th>Suite</th>
                <th>Duration</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Skipped</th>
                <th>Coverage</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
        {self._generate_suite_rows(summary["suite_results"])}
        </tbody>
    </table>
</body>
</html>
        """

    def _generate_suite_rows(self, suite_results: Dict[str, Any]) -> str:
        """Generate HTML table rows for test suites"""
        rows = []

        for suite_name, result in suite_results.items():
            duration = result.get("duration", 0)
            coverage = result.get("coverage", {})
            coverage_pct = coverage.get("total_coverage", 0) if coverage else 0

            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            status_class = "passed" if result["success"] else "failed"

            row = f"""
            <tr>
                <td>{suite_name}</td>
                <td>{duration:.1f}s</td>
                <td class="passed">{result["passed"]}</td>
                <td class="failed">{result["failed"]}</td>
                <td class="skipped">{result["skipped"]}</td>
                <td>{coverage_pct:.1f}%</td>
                <td class="{status_class}">{status}</td>
            </tr>
            """
            rows.append(row)

        return "\n".join(rows)

    def _generate_coverage_report(self):
        """Generate combined coverage report"""
        # Combine coverage from all suites
        total_coverage = {
            "files": {},
            "totals": {"covered_lines": 0, "num_statements": 0, "percent_covered": 0},
        }

        for suite_name, result in self.test_results.items():
            coverage_file = self.reports_dir / f"coverage_{suite_name}.json"
            if coverage_file.exists():
                try:
                    with open(coverage_file) as f:
                        suite_coverage = json.load(f)

                    # Merge file coverage
                    for file_path, file_coverage in suite_coverage.get(
                        "files", {}
                    ).items():
                        if file_path not in total_coverage["files"]:
                            total_coverage["files"][file_path] = file_coverage
                        else:
                            # Merge coverage data (take maximum coverage)
                            existing = total_coverage["files"][file_path]
                            if file_coverage.get("summary", {}).get(
                                "percent_covered", 0
                            ) > existing.get("summary", {}).get("percent_covered", 0):
                                total_coverage["files"][file_path] = file_coverage

                    # Update totals
                    suite_totals = suite_coverage.get("totals", {})
                    total_coverage["totals"]["covered_lines"] += suite_totals.get(
                        "covered_lines", 0
                    )
                    total_coverage["totals"]["num_statements"] += suite_totals.get(
                        "num_statements", 0
                    )

                except Exception as e:
                    print(f"⚠️  Failed to merge coverage for {suite_name}: {e}")

        # Calculate combined percentage
        if total_coverage["totals"]["num_statements"] > 0:
            total_coverage["totals"]["percent_covered"] = (
                total_coverage["totals"]["covered_lines"]
                / total_coverage["totals"]["num_statements"]
            ) * 100

        # Save combined coverage
        with open(self.reports_dir / "coverage_combined.json", "w") as f:
            json.dump(total_coverage, f, indent=2)

    def _generate_ci_reports(self):
        """Generate CI/CD compatible reports"""
        # Generate GitHub Actions summary
        if os.getenv("GITHUB_ACTIONS"):
            self._generate_github_summary()

        # Generate GitLab CI report
        if os.getenv("GITLAB_CI"):
            self._generate_gitlab_report()

        # Generate Jenkins report
        self._generate_jenkins_report()

    def _generate_github_summary(self):
        """Generate GitHub Actions job summary"""
        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_file:
            total_tests = sum(
                r["passed"] + r["failed"] + r["skipped"]
                for r in self.test_results.values()
            )
            total_passed = sum(r["passed"] for r in self.test_results.values())
            total_failed = sum(r["failed"] for r in self.test_results.values())

            markdown_content = f"""
# 🧪 Test Execution Summary

## Overall Results
- **Total Tests:** {total_tests}
- **Passed:** ✅ {total_passed}
- **Failed:** ❌ {total_failed}
- **Success Rate:** {(total_passed / total_tests) * 100:.1f}%

## Suite Results
| Suite | Duration | Passed | Failed | Skipped | Status |
|-------|----------|--------|--------|---------|---------|
"""

            for suite_name, result in self.test_results.items():
                duration = result.get("duration", 0)
                status = "✅" if result["success"] else "❌"
                markdown_content += f"| {suite_name} | {duration:.1f}s | {result['passed']} | {result['failed']} | {result['skipped']} | {status} |\n"

            with open(summary_file, "w") as f:
                f.write(markdown_content)

    def _generate_gitlab_report(self):
        """Generate GitLab CI report"""
        # GitLab uses JUnit XML format, which we already generate
        pass

    def _generate_jenkins_report(self):
        """Generate Jenkins compatible report"""
        # Jenkins also uses JUnit XML format
        pass

    def _print_final_summary(self):
        """Print final test execution summary"""
        print("🏁 Test Execution Complete")
        print("=" * 80)

        if not self.test_results:
            print("❌ No tests were executed")
            return

        total_duration = (
            (self.end_time - self.start_time).total_seconds()
            if self.end_time and self.start_time
            else 0
        )
        total_tests = sum(
            r["passed"] + r["failed"] + r["skipped"] for r in self.test_results.values()
        )
        total_passed = sum(r["passed"] for r in self.test_results.values())
        total_failed = sum(r["failed"] for r in self.test_results.values())
        total_skipped = sum(r["skipped"] for r in self.test_results.values())

        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        print(f"⏱️  Total Duration: {total_duration:.1f} seconds")
        print("📊 Test Summary:")
        print(f"   Total: {total_tests}")
        print(f"   Passed: ✅ {total_passed}")
        print(f"   Failed: ❌ {total_failed}")
        print(f"   Skipped: ⏭️  {total_skipped}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print()

        # Coverage summary
        coverage_files = list(self.reports_dir.glob("coverage_*.json"))
        if coverage_files:
            print("📈 Coverage Summary:")
            for coverage_file in coverage_files:
                suite_name = coverage_file.stem.replace("coverage_", "")
                if suite_name == "combined":
                    continue

                try:
                    with open(coverage_file) as f:
                        coverage_data = json.load(f)

                    coverage_pct = coverage_data.get("totals", {}).get(
                        "percent_covered", 0
                    )
                    threshold = self.config["coverage"]["minimum_threshold"]
                    status = "✅" if coverage_pct >= threshold else "⚠️ "

                    print(f"   {suite_name}: {status} {coverage_pct:.1f}%")

                except Exception:
                    print(f"   {suite_name}: ❓ Coverage data unavailable")
            print()

        # Final status
        overall_success = all(r["success"] for r in self.test_results.values())

        if overall_success:
            print("🎉 ALL TESTS PASSED!")
            exit_code = 0
        else:
            print("💥 SOME TESTS FAILED!")
            failed_suites = [
                name
                for name, result in self.test_results.items()
                if not result["success"]
            ]
            print(f"   Failed suites: {', '.join(failed_suites)}")
            exit_code = 1

        print(f"📁 Detailed reports: {self.reports_dir}")
        print("=" * 80)

        return exit_code


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(
        description="Universal Project Platform Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--suites",
        nargs="+",
        choices=list(TEST_CONFIG["test_suites"].keys()) + ["all"],
        default=["all"],
        help="Test suites to run (default: all)",
    )

    parser.add_argument(
        "--no-coverage", action="store_true", help="Skip coverage analysis"
    )

    parser.add_argument(
        "--no-parallel", action="store_true", help="Disable parallel test execution"
    )

    parser.add_argument("--quiet", action="store_true", help="Minimal output")

    parser.add_argument(
        "--ci", action="store_true", help="CI/CD mode with optimized settings"
    )

    parser.add_argument(
        "--fast", action="store_true", help="Fast mode - skip slow tests"
    )

    args = parser.parse_args()

    # Configure based on arguments
    if "all" in args.suites:
        suites = list(TEST_CONFIG["test_suites"].keys())
    else:
        suites = args.suites

    # CI mode optimizations
    if args.ci:
        args.no_parallel = True  # More reliable in CI
        os.environ["CI"] = "true"

    # Fast mode - skip slow suites
    if args.fast:
        suites = [s for s in suites if s not in ["e2e", "error_handling"]]

    # Initialize and run tests
    runner = TestRunner(TEST_CONFIG)

    try:
        results = runner.run_all_tests(
            suites=suites,
            parallel=not args.no_parallel,
            coverage=not args.no_coverage,
            verbose=not args.quiet,
        )

        # Determine exit code
        overall_success = all(r["success"] for r in results.values())
        exit_code = 0 if overall_success else 1

    except KeyboardInterrupt:
        print("\n🛑 Test execution interrupted by user")
        exit_code = 130
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
