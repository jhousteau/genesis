"""
Intelligence Coordinator Module
Orchestrates all intelligence layer components and provides system integration
"""

import json
import logging
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from .registry import ProjectRegistry


@dataclass
class IntelligenceReport:
    """Represents a comprehensive intelligence analysis report"""

    project_name: str
    timestamp: str
    analysis_type: str
    status: str
    summary: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    raw_data: Dict[str, Any]


@dataclass
class SystemIntegrationStatus:
    """Represents the status of system integration across components"""

    components_online: List[str]
    components_offline: List[str]
    integration_health: str  # 'healthy', 'degraded', 'critical'
    last_coordination_check: str
    coordination_errors: List[str]


class IntelligenceCoordinator:
    """Coordinates all intelligence layer operations and system integration"""

    def __init__(self, registry: ProjectRegistry = None):
        self.registry = registry or ProjectRegistry()
        self.logger = logging.getLogger(f"{__name__}.IntelligenceCoordinator")
        self.intelligence_path = self._find_intelligence_path()
        self.analysis_cache = {}
        self.coordination_lock = threading.Lock()
        self.system_components = {
            "setup-project": "/Users/jameshousteau/source_code/bootstrapper/setup-project",
            "deploy": "/Users/jameshousteau/source_code/bootstrapper/deploy",
            "governance": "/Users/jameshousteau/source_code/bootstrapper/governance",
            "isolation": "/Users/jameshousteau/source_code/bootstrapper/isolation",
            "monitoring": "/Users/jameshousteau/source_code/bootstrapper/monitoring",
            "intelligence": "/Users/jameshousteau/source_code/bootstrapper/intelligence",
        }

    def _find_intelligence_path(self) -> str:
        """Find the intelligence layer directory"""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "intelligence"),
            "/opt/bootstrap/intelligence",
            os.path.expanduser("~/.bootstrap/intelligence"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)

        raise FileNotFoundError("Intelligence layer not found")

    def run_auto_fix(self, project_name: str) -> Dict[str, Any]:
        """Run auto-fix analysis for a project"""
        # Check if auto-fix is enabled for this project
        intelligence_config = self.registry.get_intelligence_config(project_name)
        if not intelligence_config.get("auto_fix_enabled", False):
            return {
                "status": "disabled",
                "message": "Auto-fix is disabled for this project",
            }

        try:
            auto_fix_script = os.path.join(self.intelligence_path, "auto-fix", "fix.py")
            if not os.path.exists(auto_fix_script):
                raise FileNotFoundError("Auto-fix script not found")

            self.logger.info(f"Running auto-fix for project: {project_name}")

            result = subprocess.run(
                [sys.executable, auto_fix_script, project_name],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                # Try to load JSON report if available
                project = self.registry.get_project(project_name)
                project_path = project.get("path", "")
                report_file = os.path.join(
                    project_path, ".bootstrap-autofix-report.json"
                )

                report_data = {}
                if os.path.exists(report_file):
                    try:
                        with open(report_file, "r") as f:
                            report_data = json.load(f)
                    except Exception as e:
                        self.logger.warning(f"Could not load auto-fix report: {e}")

                return {
                    "status": "success",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "report": report_data,
                }
            else:
                return {
                    "status": "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "message": "Auto-fix analysis timed out after 5 minutes",
            }
        except Exception as e:
            self.logger.error(f"Auto-fix failed for {project_name}: {e}")
            return {"status": "error", "message": str(e)}

    def run_optimization_analysis(self, project_name: str) -> Dict[str, Any]:
        """Run optimization analysis for a project"""
        intelligence_config = self.registry.get_intelligence_config(project_name)
        if not intelligence_config.get("optimization_enabled", False):
            return {
                "status": "disabled",
                "message": "Optimization analysis is disabled for this project",
            }

        try:
            optimization_script = os.path.join(
                self.intelligence_path, "optimization", "analyze.py"
            )
            if not os.path.exists(optimization_script):
                raise FileNotFoundError("Optimization script not found")

            self.logger.info(
                f"Running optimization analysis for project: {project_name}"
            )

            result = subprocess.run(
                [sys.executable, optimization_script, project_name],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                project = self.registry.get_project(project_name)
                project_path = project.get("path", "")
                report_file = os.path.join(
                    project_path, ".bootstrap-optimization-report.json"
                )

                report_data = {}
                if os.path.exists(report_file):
                    try:
                        with open(report_file, "r") as f:
                            report_data = json.load(f)
                    except Exception as e:
                        self.logger.warning(f"Could not load optimization report: {e}")

                return {
                    "status": "success",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "report": report_data,
                }
            else:
                return {
                    "status": "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                }

        except Exception as e:
            self.logger.error(f"Optimization analysis failed for {project_name}: {e}")
            return {"status": "error", "message": str(e)}

    def run_predictions_analysis(self, project_name: str) -> Dict[str, Any]:
        """Run predictions analysis for a project"""
        intelligence_config = self.registry.get_intelligence_config(project_name)
        if not intelligence_config.get("predictions_enabled", False):
            return {
                "status": "disabled",
                "message": "Predictions analysis is disabled for this project",
            }

        try:
            predictions_script = os.path.join(
                self.intelligence_path, "predictions", "analyze.py"
            )
            if not os.path.exists(predictions_script):
                raise FileNotFoundError("Predictions script not found")

            self.logger.info(
                f"Running predictions analysis for project: {project_name}"
            )

            result = subprocess.run(
                [sys.executable, predictions_script, project_name],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                project = self.registry.get_project(project_name)
                project_path = project.get("path", "")
                report_file = os.path.join(
                    project_path, ".bootstrap-predictions-report.json"
                )

                report_data = {}
                if os.path.exists(report_file):
                    try:
                        with open(report_file, "r") as f:
                            report_data = json.load(f)
                    except Exception as e:
                        self.logger.warning(f"Could not load predictions report: {e}")

                return {
                    "status": "success",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "report": report_data,
                }
            else:
                return {
                    "status": "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                }

        except Exception as e:
            self.logger.error(f"Predictions analysis failed for {project_name}: {e}")
            return {"status": "error", "message": str(e)}

    def run_recommendations_analysis(self, project_name: str) -> Dict[str, Any]:
        """Run recommendations analysis for a project"""
        intelligence_config = self.registry.get_intelligence_config(project_name)
        if not intelligence_config.get("recommendations_enabled", False):
            return {
                "status": "disabled",
                "message": "Recommendations analysis is disabled for this project",
            }

        try:
            recommendations_script = os.path.join(
                self.intelligence_path, "recommendations", "analyze.py"
            )
            if not os.path.exists(recommendations_script):
                raise FileNotFoundError("Recommendations script not found")

            self.logger.info(
                f"Running recommendations analysis for project: {project_name}"
            )

            result = subprocess.run(
                [sys.executable, recommendations_script, project_name],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                project = self.registry.get_project(project_name)
                project_path = project.get("path", "")
                report_file = os.path.join(
                    project_path, ".bootstrap-recommendations-report.json"
                )

                report_data = {}
                if os.path.exists(report_file):
                    try:
                        with open(report_file, "r") as f:
                            report_data = json.load(f)
                    except Exception as e:
                        self.logger.warning(
                            f"Could not load recommendations report: {e}"
                        )

                return {
                    "status": "success",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "report": report_data,
                }
            else:
                return {
                    "status": "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                }

        except Exception as e:
            self.logger.error(
                f"Recommendations analysis failed for {project_name}: {e}"
            )
            return {"status": "error", "message": str(e)}

    def run_full_analysis(self, project_name: str) -> Dict[str, Any]:
        """Run all enabled intelligence analyses for a project"""
        self.logger.info(
            f"Running full intelligence analysis for project: {project_name}"
        )

        results = {
            "project_name": project_name,
            "timestamp": "2024-08-20T00:00:00Z",  # In real implementation, use actual timestamp
            "analyses": {},
        }

        # Run each analysis if enabled
        intelligence_config = self.registry.get_intelligence_config(project_name)

        if intelligence_config.get("auto_fix_enabled", False):
            results["analyses"]["auto_fix"] = self.run_auto_fix(project_name)

        if intelligence_config.get("optimization_enabled", False):
            results["analyses"]["optimization"] = self.run_optimization_analysis(
                project_name
            )

        if intelligence_config.get("predictions_enabled", False):
            results["analyses"]["predictions"] = self.run_predictions_analysis(
                project_name
            )

        if intelligence_config.get("recommendations_enabled", False):
            results["analyses"]["recommendations"] = self.run_recommendations_analysis(
                project_name
            )

        # Calculate overall status
        statuses = [analysis.get("status") for analysis in results["analyses"].values()]
        if all(status == "success" for status in statuses):
            results["overall_status"] = "success"
        elif any(status == "error" for status in statuses):
            results["overall_status"] = "partial_failure"
        elif all(status == "disabled" for status in statuses):
            results["overall_status"] = "disabled"
        else:
            results["overall_status"] = "mixed"

        return results

    def get_analysis_summary(self, project_name: str) -> Dict[str, Any]:
        """Get summary of latest analysis results for a project"""
        project = self.registry.get_project(project_name)
        project_path = project.get("path", "")

        summary = {
            "project_name": project_name,
            "reports_found": [],
            "last_analysis": None,
            "issues_summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "recommendations_summary": {
                "immediate": 0,
                "short_term": 0,
                "long_term": 0,
            },
        }

        # Check for available reports
        report_files = {
            "auto_fix": ".bootstrap-autofix-report.json",
            "optimization": ".bootstrap-optimization-report.json",
            "predictions": ".bootstrap-predictions-report.json",
            "recommendations": ".bootstrap-recommendations-report.json",
        }

        for report_type, filename in report_files.items():
            report_path = os.path.join(project_path, filename)
            if os.path.exists(report_path):
                summary["reports_found"].append(report_type)

                try:
                    with open(report_path, "r") as f:
                        report_data = json.load(f)

                    # Extract summary information based on report type
                    if report_type == "auto_fix":
                        issues = report_data.get("issues_by_severity", {})
                        for severity, issue_list in issues.items():
                            if severity in summary["issues_summary"]:
                                summary["issues_summary"][severity] += len(issue_list)

                    elif report_type == "recommendations":
                        roadmap = report_data.get("implementation_roadmap", {})
                        summary["recommendations_summary"]["immediate"] = len(
                            roadmap.get("phase_1_immediate", [])
                        )
                        summary["recommendations_summary"]["short_term"] = len(
                            roadmap.get("phase_2_short_term", [])
                        )
                        summary["recommendations_summary"]["long_term"] = len(
                            roadmap.get("phase_3_long_term", [])
                        )

                    # Update last analysis timestamp
                    timestamp = report_data.get(
                        "analysis_timestamp"
                    ) or report_data.get("timestamp")
                    if timestamp and (
                        not summary["last_analysis"]
                        or timestamp > summary["last_analysis"]
                    ):
                        summary["last_analysis"] = timestamp

                except Exception as e:
                    self.logger.warning(f"Could not read {report_type} report: {e}")

        return summary

    def enable_intelligence_features(self, project_name: str, features: List[str]):
        """Enable specific intelligence features for a project"""
        valid_features = [
            "auto_fix_enabled",
            "optimization_enabled",
            "predictions_enabled",
            "recommendations_enabled",
        ]

        updates = {}
        intelligence_config = self.registry.get_intelligence_config(project_name)

        for feature in features:
            if feature in valid_features:
                intelligence_config[feature] = True

        updates["intelligence"] = intelligence_config
        self.registry.update_project(project_name, updates)

        self.logger.info(
            f"Enabled intelligence features for {project_name}: {features}"
        )

    def disable_intelligence_features(self, project_name: str, features: List[str]):
        """Disable specific intelligence features for a project"""
        valid_features = [
            "auto_fix_enabled",
            "optimization_enabled",
            "predictions_enabled",
            "recommendations_enabled",
        ]

        updates = {}
        intelligence_config = self.registry.get_intelligence_config(project_name)

        for feature in features:
            if feature in valid_features:
                intelligence_config[feature] = False

        updates["intelligence"] = intelligence_config
        self.registry.update_project(project_name, updates)

        self.logger.info(
            f"Disabled intelligence features for {project_name}: {features}"
        )

    def check_system_integration_status(self) -> SystemIntegrationStatus:
        """Check the health and status of all system components"""
        online_components = []
        offline_components = []
        errors = []

        for component_name, component_path in self.system_components.items():
            try:
                if os.path.exists(component_path):
                    # Additional health checks for each component
                    if self._check_component_health(component_name, component_path):
                        online_components.append(component_name)
                    else:
                        offline_components.append(component_name)
                        errors.append(
                            f"{component_name}: Component exists but health check failed"
                        )
                else:
                    offline_components.append(component_name)
                    errors.append(
                        f"{component_name}: Component directory not found at {component_path}"
                    )
            except Exception as e:
                offline_components.append(component_name)
                errors.append(f"{component_name}: Health check error - {str(e)}")

        # Determine overall health
        total_components = len(self.system_components)
        online_ratio = len(online_components) / total_components

        if online_ratio >= 0.9:
            health = "healthy"
        elif online_ratio >= 0.7:
            health = "degraded"
        else:
            health = "critical"

        return SystemIntegrationStatus(
            components_online=online_components,
            components_offline=offline_components,
            integration_health=health,
            last_coordination_check=datetime.now().isoformat(),
            coordination_errors=errors,
        )

    def _check_component_health(self, component_name: str, component_path: str) -> bool:
        """Check the health of a specific component"""
        try:
            if component_name == "intelligence":
                # Check if intelligence scripts are available
                required_scripts = [
                    "auto-fix/fix.py",
                    "optimization/analyze.py",
                    "predictions/analyze.py",
                    "recommendations/analyze.py",
                ]
                return all(
                    os.path.exists(os.path.join(component_path, script))
                    for script in required_scripts
                )

            elif component_name == "deploy":
                # Check if deployment orchestrator exists
                return os.path.exists(
                    os.path.join(component_path, "deploy-orchestrator.sh")
                )

            elif component_name == "governance":
                # Check governance configuration
                return os.path.exists(
                    os.path.join(component_path, "governance-config.yaml")
                )

            elif component_name == "isolation":
                # Check isolation scripts
                return os.path.exists(os.path.join(component_path, "gcp"))

            elif component_name == "monitoring":
                # Check monitoring configuration
                return os.path.exists(os.path.join(component_path, "configs"))

            elif component_name == "setup-project":
                # Check setup project scripts
                return os.path.exists(os.path.join(component_path, "setup.py"))

            return True

        except Exception as e:
            self.logger.warning(f"Health check failed for {component_name}: {e}")
            return False

    def run_parallel_analysis(
        self, project_names: List[str], analysis_types: List[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Run intelligence analysis in parallel for multiple projects"""
        if analysis_types is None:
            analysis_types = [
                "auto_fix",
                "optimization",
                "predictions",
                "recommendations",
            ]

        results = {}

        with ThreadPoolExecutor(max_workers=min(len(project_names), 4)) as executor:
            # Submit all analysis tasks
            future_to_project = {}

            for project_name in project_names:
                for analysis_type in analysis_types:
                    future = executor.submit(
                        self._run_single_analysis, project_name, analysis_type
                    )
                    future_to_project[future] = (project_name, analysis_type)

            # Collect results
            for future in as_completed(future_to_project):
                project_name, analysis_type = future_to_project[future]

                if project_name not in results:
                    results[project_name] = {}

                try:
                    result = future.result(timeout=300)  # 5 minute timeout per analysis
                    results[project_name][analysis_type] = result
                except Exception as e:
                    self.logger.error(
                        f"Analysis failed for {project_name}/{analysis_type}: {e}"
                    )
                    results[project_name][analysis_type] = {
                        "status": "error",
                        "error": str(e),
                    }

        return results

    def _run_single_analysis(
        self, project_name: str, analysis_type: str
    ) -> Dict[str, Any]:
        """Run a single analysis type for a project"""
        analysis_methods = {
            "auto_fix": self.run_auto_fix,
            "optimization": self.run_optimization_analysis,
            "predictions": self.run_predictions_analysis,
            "recommendations": self.run_recommendations_analysis,
        }

        if analysis_type not in analysis_methods:
            return {
                "status": "error",
                "error": f"Unknown analysis type: {analysis_type}",
            }

        return analysis_methods[analysis_type](project_name)

    def generate_cross_project_insights(
        self, project_names: List[str]
    ) -> Dict[str, Any]:
        """Generate insights across multiple projects"""
        self.logger.info(
            f"Generating cross-project insights for {len(project_names)} projects"
        )

        # Run analysis for all projects
        all_results = self.run_parallel_analysis(project_names)

        insights = {
            "analysis_timestamp": datetime.now().isoformat(),
            "projects_analyzed": project_names,
            "cross_project_patterns": {},
            "common_issues": {},
            "optimization_opportunities": {},
            "security_trends": {},
            "architecture_patterns": {},
            "recommendations_summary": {},
        }

        # Analyze patterns across projects
        insights["cross_project_patterns"] = self._analyze_cross_project_patterns(
            all_results
        )
        insights["common_issues"] = self._identify_common_issues(all_results)
        insights["optimization_opportunities"] = (
            self._identify_optimization_opportunities(all_results)
        )
        insights["security_trends"] = self._analyze_security_trends(all_results)
        insights["architecture_patterns"] = self._analyze_architecture_patterns(
            all_results
        )
        insights["recommendations_summary"] = self._summarize_recommendations(
            all_results
        )

        return insights

    def _analyze_cross_project_patterns(
        self, all_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze patterns that appear across multiple projects"""
        patterns = {
            "technology_stacks": {},
            "common_dependencies": {},
            "deployment_patterns": {},
            "infrastructure_patterns": {},
        }

        for project_name, project_results in all_results.items():
            # Analyze recommendations for technology patterns
            if (
                "recommendations" in project_results
                and project_results["recommendations"].get("status") == "success"
            ):
                rec_report = project_results["recommendations"].get("report", {})
                context = rec_report.get("project_context", {})

                # Track technology stacks
                languages = context.get("languages", [])
                frameworks = context.get("frameworks", [])

                for lang in languages:
                    patterns["technology_stacks"][lang] = (
                        patterns["technology_stacks"].get(lang, 0) + 1
                    )

                for framework in frameworks:
                    patterns["common_dependencies"][framework] = (
                        patterns["common_dependencies"].get(framework, 0) + 1
                    )

                # Track infrastructure patterns
                has_docker = context.get("has_dockerfile", False)
                has_k8s = context.get("has_k8s", False)
                has_terraform = context.get("has_terraform", False)

                if has_docker:
                    patterns["infrastructure_patterns"]["docker"] = (
                        patterns["infrastructure_patterns"].get("docker", 0) + 1
                    )
                if has_k8s:
                    patterns["infrastructure_patterns"]["kubernetes"] = (
                        patterns["infrastructure_patterns"].get("kubernetes", 0) + 1
                    )
                if has_terraform:
                    patterns["infrastructure_patterns"]["terraform"] = (
                        patterns["infrastructure_patterns"].get("terraform", 0) + 1
                    )

        return patterns

    def _identify_common_issues(
        self, all_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identify issues that appear across multiple projects"""
        issue_frequency = {}

        for project_name, project_results in all_results.items():
            # Analyze auto-fix results for common issues
            if (
                "auto_fix" in project_results
                and project_results["auto_fix"].get("status") == "success"
            ):
                autofix_report = project_results["auto_fix"].get("report", {})
                issues_by_severity = autofix_report.get("issues_by_severity", {})

                for severity, issues in issues_by_severity.items():
                    for issue in issues:
                        issue_id = issue.get("id", "unknown")
                        if issue_id not in issue_frequency:
                            issue_frequency[issue_id] = {
                                "count": 0,
                                "severity": severity,
                                "title": issue.get("title", "Unknown Issue"),
                                "projects": [],
                            }
                        issue_frequency[issue_id]["count"] += 1
                        issue_frequency[issue_id]["projects"].append(project_name)

        # Sort by frequency
        common_issues = dict(
            sorted(issue_frequency.items(), key=lambda x: x[1]["count"], reverse=True)
        )

        return {
            "most_common_issues": common_issues,
            "total_unique_issues": len(issue_frequency),
            "issues_affecting_multiple_projects": {
                k: v for k, v in common_issues.items() if v["count"] > 1
            },
        }

    def _identify_optimization_opportunities(
        self, all_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identify optimization opportunities across projects"""
        cost_savings = []
        performance_improvements = []
        resource_optimizations = []

        for project_name, project_results in all_results.items():
            if (
                "optimization" in project_results
                and project_results["optimization"].get("status") == "success"
            ):
                opt_report = project_results["optimization"].get("report", {})
                recommendations = opt_report.get("recommendations_by_category", {})

                # Extract cost optimization opportunities
                cost_recs = recommendations.get("cost", [])
                for rec in cost_recs:
                    if rec.get("savings_estimate"):
                        cost_savings.append(
                            {
                                "project": project_name,
                                "title": rec.get("title"),
                                "savings": rec.get("savings_estimate"),
                                "priority": rec.get("priority"),
                            }
                        )

                # Extract performance opportunities
                perf_recs = recommendations.get("performance", [])
                for rec in perf_recs:
                    if rec.get("performance_impact"):
                        performance_improvements.append(
                            {
                                "project": project_name,
                                "title": rec.get("title"),
                                "impact": rec.get("performance_impact"),
                                "priority": rec.get("priority"),
                            }
                        )

                # Extract resource opportunities
                resource_recs = recommendations.get("resource", [])
                for rec in resource_recs:
                    resource_optimizations.append(
                        {
                            "project": project_name,
                            "title": rec.get("title"),
                            "impact": rec.get("impact"),
                            "priority": rec.get("priority"),
                        }
                    )

        return {
            "cost_optimization_opportunities": cost_savings,
            "performance_improvement_opportunities": performance_improvements,
            "resource_optimization_opportunities": resource_optimizations,
            "total_cost_opportunities": len(cost_savings),
            "total_performance_opportunities": len(performance_improvements),
            "total_resource_opportunities": len(resource_optimizations),
        }

    def _analyze_security_trends(
        self, all_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze security trends across projects"""
        security_issues = []
        security_recommendations = []

        for project_name, project_results in all_results.items():
            # Check auto-fix for security issues
            if (
                "auto_fix" in project_results
                and project_results["auto_fix"].get("status") == "success"
            ):
                autofix_report = project_results["auto_fix"].get("report", {})
                issues_by_severity = autofix_report.get("issues_by_severity", {})

                for severity, issues in issues_by_severity.items():
                    for issue in issues:
                        if (
                            "security" in issue.get("id", "").lower()
                            or "secret" in issue.get("id", "").lower()
                        ):
                            security_issues.append(
                                {
                                    "project": project_name,
                                    "severity": severity,
                                    "title": issue.get("title"),
                                    "type": "vulnerability",
                                }
                            )

            # Check recommendations for security recommendations
            if (
                "recommendations" in project_results
                and project_results["recommendations"].get("status") == "success"
            ):
                rec_report = project_results["recommendations"].get("report", {})
                security_recs = rec_report.get("recommendations_by_category", {}).get(
                    "security", []
                )

                for rec in security_recs:
                    security_recommendations.append(
                        {
                            "project": project_name,
                            "priority": rec.get("priority"),
                            "title": rec.get("title"),
                            "type": "recommendation",
                        }
                    )

        return {
            "security_issues_found": security_issues,
            "security_recommendations": security_recommendations,
            "projects_with_security_issues": len(
                set(issue["project"] for issue in security_issues)
            ),
            "critical_security_issues": [
                issue for issue in security_issues if issue["severity"] == "critical"
            ],
            "high_priority_security_recs": [
                rec for rec in security_recommendations if rec["priority"] == "critical"
            ],
        }

    def _analyze_architecture_patterns(
        self, all_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze architecture patterns across projects"""
        patterns = {
            "monolith_vs_microservices": {
                "monolith": 0,
                "microservices": 0,
                "unknown": 0,
            },
            "containerization_adoption": {"containerized": 0, "not_containerized": 0},
            "iac_adoption": {"terraform": 0, "other_iac": 0, "manual": 0},
            "ci_cd_adoption": {"automated": 0, "manual": 0},
        }

        for project_name, project_results in all_results.items():
            if (
                "recommendations" in project_results
                and project_results["recommendations"].get("status") == "success"
            ):
                rec_report = project_results["recommendations"].get("report", {})
                context = rec_report.get("project_context", {})

                # Analyze containerization
                if context.get("has_dockerfile"):
                    patterns["containerization_adoption"]["containerized"] += 1
                else:
                    patterns["containerization_adoption"]["not_containerized"] += 1

                # Analyze IaC adoption
                if context.get("has_terraform"):
                    patterns["iac_adoption"]["terraform"] += 1
                else:
                    patterns["iac_adoption"]["manual"] += 1

                # Analyze CI/CD adoption
                if context.get("has_ci_cd"):
                    patterns["ci_cd_adoption"]["automated"] += 1
                else:
                    patterns["ci_cd_adoption"]["manual"] += 1

                # Analyze architecture (this is simplistic - would need more sophisticated analysis)
                project_size = context.get("project_size", "unknown")
                if project_size == "large":
                    patterns["monolith_vs_microservices"]["monolith"] += 1  # Assumption
                else:
                    patterns["monolith_vs_microservices"]["unknown"] += 1

        return patterns

    def _summarize_recommendations(
        self, all_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Summarize recommendations across all projects"""
        all_recommendations = []
        roadmap_summary = {
            "immediate_actions": 0,
            "short_term_actions": 0,
            "long_term_actions": 0,
        }

        category_summary = {
            "architecture": 0,
            "security": 0,
            "performance": 0,
            "maintainability": 0,
            "reliability": 0,
        }

        for project_name, project_results in all_results.items():
            if (
                "recommendations" in project_results
                and project_results["recommendations"].get("status") == "success"
            ):
                rec_report = project_results["recommendations"].get("report", {})

                # Count by category
                recs_by_category = rec_report.get("recommendations_by_category", {})
                for category, recs in recs_by_category.items():
                    if category in category_summary:
                        category_summary[category] += len(recs)

                # Count by roadmap phase
                roadmap = rec_report.get("implementation_roadmap", {})
                roadmap_summary["immediate_actions"] += len(
                    roadmap.get("phase_1_immediate", [])
                )
                roadmap_summary["short_term_actions"] += len(
                    roadmap.get("phase_2_short_term", [])
                )
                roadmap_summary["long_term_actions"] += len(
                    roadmap.get("phase_3_long_term", [])
                )

        return {
            "total_recommendations": sum(category_summary.values()),
            "by_category": category_summary,
            "implementation_roadmap": roadmap_summary,
            "projects_with_recommendations": len(
                [
                    p
                    for p, r in all_results.items()
                    if "recommendations" in r
                    and r["recommendations"].get("status") == "success"
                ]
            ),
        }

    def coordinate_system_wide_operations(
        self, operation: str, **kwargs
    ) -> Dict[str, Any]:
        """Coordinate operations across all system components"""
        with self.coordination_lock:
            self.logger.info(f"Coordinating system-wide operation: {operation}")

            coordination_result = {
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                "component_results": {},
                "overall_status": "success",
                "errors": [],
            }

            if operation == "health_check":
                coordination_result["component_results"] = (
                    self._coordinate_health_checks()
                )

            elif operation == "full_analysis":
                project_names = kwargs.get("project_names", [])
                coordination_result["component_results"] = (
                    self._coordinate_full_analysis(project_names)
                )

            elif operation == "system_optimization":
                coordination_result["component_results"] = (
                    self._coordinate_system_optimization()
                )

            elif operation == "security_audit":
                coordination_result["component_results"] = (
                    self._coordinate_security_audit()
                )

            else:
                coordination_result["overall_status"] = "error"
                coordination_result["errors"].append(f"Unknown operation: {operation}")

            return coordination_result

    def _coordinate_health_checks(self) -> Dict[str, Any]:
        """Coordinate health checks across all components"""
        health_results = {}

        # Check system integration status
        integration_status = self.check_system_integration_status()
        health_results["integration_status"] = {
            "status": integration_status.integration_health,
            "components_online": integration_status.components_online,
            "components_offline": integration_status.components_offline,
            "errors": integration_status.coordination_errors,
        }

        return health_results

    def _coordinate_full_analysis(self, project_names: List[str]) -> Dict[str, Any]:
        """Coordinate full analysis across projects"""
        if not project_names:
            # Get all projects from registry
            try:
                all_projects = self.registry.list_projects()
                project_names = list(all_projects.keys())
            except Exception as e:
                return {
                    "error": f"Could not retrieve project list: {e}",
                    "status": "failed",
                }

        analysis_results = self.run_parallel_analysis(project_names)
        cross_project_insights = self.generate_cross_project_insights(project_names)

        return {
            "projects_analyzed": len(project_names),
            "individual_results": analysis_results,
            "cross_project_insights": cross_project_insights,
            "status": "completed",
        }

    def _coordinate_system_optimization(self) -> Dict[str, Any]:
        """Coordinate system-wide optimization efforts"""
        optimization_results = {
            "infrastructure_optimization": {},
            "cost_optimization": {},
            "performance_optimization": {},
            "security_optimization": {},
        }

        # This would coordinate with other system components
        # For now, return placeholder structure
        optimization_results["status"] = "coordinated"
        optimization_results["timestamp"] = datetime.now().isoformat()

        return optimization_results

    def _coordinate_security_audit(self) -> Dict[str, Any]:
        """Coordinate security audit across all components"""
        security_results = {
            "governance_compliance": {},
            "isolation_security": {},
            "deployment_security": {},
            "monitoring_security": {},
        }

        # This would coordinate with governance and isolation components
        security_results["status"] = "coordinated"
        security_results["timestamp"] = datetime.now().isoformat()

        return security_results
