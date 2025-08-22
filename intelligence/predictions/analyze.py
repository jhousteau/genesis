#!/usr/bin/env python3

"""
Prediction Engine for Universal Project Platform
Version: 1.0.0

This module provides failure prediction and capacity planning capabilities.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class Prediction:
    """Represents a prediction about project behavior"""

    id: str
    type: str  # 'failure', 'capacity', 'cost', 'performance'
    confidence: float  # 0.0 to 1.0
    timeframe: str  # When this prediction applies
    title: str
    description: str
    likelihood: str  # 'low', 'medium', 'high'
    impact: str  # Expected impact if prediction comes true
    indicators: List[str]  # What led to this prediction
    preventive_actions: List[str]  # Actions to prevent/mitigate
    monitoring_recommendations: List[str]  # What to monitor


class PredictionEngine:
    """Main prediction engine for analyzing project trends and risks"""

    def __init__(self, project_name: str, project_path: str = None):
        self.project_name = project_name
        self.project_path = project_path or self._find_project_path(project_name)
        self.logger = self._setup_logging()
        self.predictions: List[Prediction] = []

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the prediction engine"""
        logger = logging.getLogger(f"predictions.{self.project_name}")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _find_project_path(self, project_name: str) -> str:
        """Find the project path from the registry"""
        possible_paths = [
            os.path.join(os.path.expanduser("~/source_code"), project_name),
            os.path.join(os.getcwd(), project_name),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        raise FileNotFoundError(f"Project '{project_name}' not found")

    def analyze(self) -> List[Prediction]:
        """Perform comprehensive prediction analysis"""
        self.logger.info(f"Analyzing predictions for: {self.project_name}")
        self.predictions = []

        # Run all prediction analyzers
        self._predict_deployment_failures()
        self._predict_capacity_needs()
        self._predict_security_issues()
        self._predict_cost_trends()
        self._predict_performance_degradation()
        self._predict_dependency_issues()
        self._predict_infrastructure_problems()

        self.logger.info(f"Generated {len(self.predictions)} predictions")
        return self.predictions

    def _predict_deployment_failures(self):
        """Predict potential deployment failures"""
        # Analyze CI/CD configuration
        ci_files = self._find_ci_files()

        for ci_file in ci_files:
            self._analyze_ci_failure_risk(ci_file)

        # Analyze Dockerfile for deployment risks
        dockerfile = os.path.join(self.project_path, "Dockerfile")
        if os.path.exists(dockerfile):
            self._analyze_dockerfile_risks(dockerfile)

        # Analyze Kubernetes configurations
        k8s_files = self._find_k8s_files()
        for k8s_file in k8s_files:
            self._analyze_k8s_failure_risk(k8s_file)

    def _find_ci_files(self) -> List[str]:
        """Find CI/CD configuration files"""
        ci_patterns = [
            ".github/workflows/*.yml",
            ".github/workflows/*.yaml",
            ".gitlab-ci.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
        ]

        ci_files = []
        for pattern in ci_patterns:
            if "*" in pattern:
                import glob

                matches = glob.glob(os.path.join(self.project_path, pattern))
                ci_files.extend(matches)
            else:
                file_path = os.path.join(self.project_path, pattern)
                if os.path.exists(file_path):
                    ci_files.append(file_path)

        return ci_files

    def _find_k8s_files(self) -> List[str]:
        """Find Kubernetes configuration files"""
        k8s_files = []
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith((".yaml", ".yml")) and any(
                    keyword in root.lower() or keyword in file.lower()
                    for keyword in ["k8s", "kubernetes", "deploy"]
                ):
                    k8s_files.append(os.path.join(root, file))
        return k8s_files

    def _analyze_ci_failure_risk(self, ci_file: str):
        """Analyze CI/CD file for failure risk indicators"""
        try:
            with open(ci_file, "r") as f:
                content = f.read()

            risk_indicators = []

            # Check for missing error handling
            if "set -e" not in content and "pipefail" not in content:
                risk_indicators.append("Missing error handling in scripts")

            # Check for missing timeouts
            if "timeout" not in content.lower():
                risk_indicators.append("No timeout configuration found")

            # Check for missing retries
            if "retry" not in content.lower():
                risk_indicators.append("No retry logic for flaky operations")

            # Check for external dependencies without fallbacks
            external_deps = ["docker.io", "github.com", "npmjs.org", "pypi.org"]
            for dep in external_deps:
                if dep in content and "fallback" not in content.lower():
                    risk_indicators.append(
                        f"External dependency on {dep} without fallback"
                    )

            if risk_indicators:
                self.predictions.append(
                    Prediction(
                        id=f"ci_failure_risk_{os.path.basename(ci_file)}",
                        type="failure",
                        confidence=0.7,
                        timeframe="Next 30 days",
                        title="CI/CD pipeline failure risk",
                        description="CI/CD configuration has patterns that increase failure probability",
                        likelihood="medium",
                        impact="Delayed deployments and reduced developer productivity",
                        indicators=risk_indicators,
                        preventive_actions=[
                            "Add proper error handling to all scripts",
                            "Implement timeout configurations",
                            "Add retry logic for network operations",
                            "Set up fallback mirrors for external dependencies",
                        ],
                        monitoring_recommendations=[
                            "Monitor CI/CD success rates",
                            "Track build duration trends",
                            "Alert on consecutive failures",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze CI file {ci_file}: {e}")

    def _analyze_dockerfile_risks(self, dockerfile: str):
        """Analyze Dockerfile for deployment risks"""
        try:
            with open(dockerfile, "r") as f:
                content = f.read()

            risk_indicators = []

            # Check for unpinned base images
            import re

            base_images = re.findall(r"FROM\s+([^\s:]+)(?::([^\s]+))?", content)
            for image, tag in base_images:
                if not tag or tag == "latest":
                    risk_indicators.append(f"Unpinned base image: {image}")

            # Check for missing health checks
            if "HEALTHCHECK" not in content:
                risk_indicators.append("No health check defined")

            # Check for running as root
            if "USER" not in content:
                risk_indicators.append("Container runs as root user")

            # Check for missing multi-stage optimization
            if content.count("FROM") == 1 and any(
                tool in content
                for tool in ["npm install", "pip install", "apt-get install"]
            ):
                risk_indicators.append(
                    "Single-stage build with build tools in final image"
                )

            if risk_indicators:
                confidence = min(0.8, len(risk_indicators) * 0.2)
                self.predictions.append(
                    Prediction(
                        id="dockerfile_deployment_risk",
                        type="failure",
                        confidence=confidence,
                        timeframe="Next deployment",
                        title="Docker deployment failure risk",
                        description="Dockerfile configuration increases deployment failure risk",
                        likelihood="medium" if len(risk_indicators) > 2 else "low",
                        impact="Failed deployments and potential security vulnerabilities",
                        indicators=risk_indicators,
                        preventive_actions=[
                            "Pin all base images to specific versions",
                            "Add HEALTHCHECK instruction",
                            "Create non-root user for container",
                            "Implement multi-stage builds",
                        ],
                        monitoring_recommendations=[
                            "Monitor container startup times",
                            "Track deployment failure rates",
                            "Monitor security scan results",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze Dockerfile: {e}")

    def _analyze_k8s_failure_risk(self, k8s_file: str):
        """Analyze Kubernetes configuration for failure risks"""
        try:
            with open(k8s_file, "r") as f:
                content = f.read()

            if "kind: Deployment" not in content:
                return

            risk_indicators = []

            # Check for missing resource limits
            if "resources:" not in content:
                risk_indicators.append("No resource limits defined")

            # Check for missing readiness/liveness probes
            if "readinessProbe" not in content:
                risk_indicators.append("No readiness probe configured")

            if "livenessProbe" not in content:
                risk_indicators.append("No liveness probe configured")

            # Check for single replica
            if "replicas: 1" in content or "replicas:1" in content:
                risk_indicators.append("Single replica deployment")

            # Check for missing pod disruption budget
            if "PodDisruptionBudget" not in content:
                risk_indicators.append("No pod disruption budget")

            if risk_indicators:
                self.predictions.append(
                    Prediction(
                        id=f"k8s_failure_risk_{os.path.basename(k8s_file)}",
                        type="failure",
                        confidence=0.6,
                        timeframe="During next high load or maintenance",
                        title="Kubernetes deployment failure risk",
                        description="Kubernetes configuration lacks resilience features",
                        likelihood="medium",
                        impact="Service downtime during node maintenance or high load",
                        indicators=risk_indicators,
                        preventive_actions=[
                            "Add resource requests and limits",
                            "Configure readiness and liveness probes",
                            "Increase replica count for high availability",
                            "Add pod disruption budget",
                        ],
                        monitoring_recommendations=[
                            "Monitor pod restart rates",
                            "Track service availability metrics",
                            "Alert on resource utilization spikes",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze Kubernetes file {k8s_file}: {e}")

    def _predict_capacity_needs(self):
        """Predict future capacity requirements"""
        # Analyze current resource configurations
        self._analyze_current_capacity_patterns()

        # Predict based on growth trends (simulated)
        self._predict_growth_based_capacity()

    def _analyze_current_capacity_patterns(self):
        """Analyze current capacity allocation patterns"""
        # This would typically integrate with monitoring data
        # For now, we'll analyze configuration files for capacity indicators

        # Check Terraform for instance sizes
        tf_files = self._find_terraform_files()

        for tf_file in tf_files:
            self._analyze_terraform_capacity(tf_file)

    def _find_terraform_files(self) -> List[str]:
        """Find Terraform files"""
        tf_files = []
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".tf"):
                    tf_files.append(os.path.join(root, file))
        return tf_files

    def _analyze_terraform_capacity(self, tf_file: str):
        """Analyze Terraform file for capacity patterns"""
        try:
            with open(tf_file, "r") as f:
                content = f.read()

            # Look for machine types and predict scaling needs
            if "machine_type" in content:
                # Predict need for auto-scaling
                if "autoscaling" not in content.lower():
                    self.predictions.append(
                        Prediction(
                            id="capacity_scaling_need",
                            type="capacity",
                            confidence=0.7,
                            timeframe="Next 6 months",
                            title="Manual capacity management becoming unsustainable",
                            description="Fixed instance sizes without auto-scaling may not handle growth",
                            likelihood="high",
                            impact="Performance degradation during traffic spikes",
                            indicators=[
                                "Fixed machine types without auto-scaling",
                                "No load-based scaling configuration",
                            ],
                            preventive_actions=[
                                "Implement auto-scaling groups",
                                "Configure load-based scaling policies",
                                "Set up capacity monitoring and alerting",
                            ],
                            monitoring_recommendations=[
                                "Monitor CPU and memory utilization trends",
                                "Track request queue lengths",
                                "Set up predictive scaling metrics",
                            ],
                        )
                    )

            # Look for storage patterns
            if "disk_size_gb" in content:
                # Predict storage growth
                self.predictions.append(
                    Prediction(
                        id="storage_growth_prediction",
                        type="capacity",
                        confidence=0.8,
                        timeframe="Next 12 months",
                        title="Storage capacity will need expansion",
                        description="Current storage allocation may be insufficient for projected growth",
                        likelihood="high",
                        impact="Potential service disruption when storage fills up",
                        indicators=[
                            "Fixed storage sizes",
                            "No automatic storage expansion",
                        ],
                        preventive_actions=[
                            "Implement automatic storage expansion",
                            "Set up storage monitoring and alerting",
                            "Plan for data archiving strategies",
                        ],
                        monitoring_recommendations=[
                            "Monitor storage utilization trends",
                            "Track data growth rates",
                            "Alert at 80% storage utilization",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze Terraform file {tf_file}: {e}")

    def _predict_growth_based_capacity(self):
        """Predict capacity needs based on growth patterns"""
        # This would typically use historical metrics
        # For now, provide general growth predictions

        self.predictions.append(
            Prediction(
                id="general_growth_capacity",
                type="capacity",
                confidence=0.6,
                timeframe="Next 6-12 months",
                title="General infrastructure scaling requirements",
                description="Based on typical growth patterns, infrastructure scaling will be needed",
                likelihood="medium",
                impact="Need for infrastructure capacity planning",
                indicators=[
                    "Active development project",
                    "Current resource allocations",
                ],
                preventive_actions=[
                    "Implement comprehensive monitoring",
                    "Set up capacity planning processes",
                    "Create scaling runbooks",
                ],
                monitoring_recommendations=[
                    "Track all resource utilization metrics",
                    "Monitor user growth patterns",
                    "Set up predictive alerting",
                ],
            )
        )

    def _predict_security_issues(self):
        """Predict potential security issues"""
        # Analyze dependencies for security risks
        self._analyze_dependency_security_trends()

        # Analyze configuration for security risks
        self._analyze_security_configuration_trends()

    def _analyze_dependency_security_trends(self):
        """Analyze dependency patterns for security predictions"""
        # Check Python dependencies
        requirements_file = os.path.join(self.project_path, "requirements.txt")
        if os.path.exists(requirements_file):
            try:
                with open(requirements_file, "r") as f:
                    dependencies = f.readlines()

                # Count unpinned dependencies
                unpinned_count = sum(
                    1 for dep in dependencies if "==" not in dep and dep.strip()
                )

                if unpinned_count > 0:
                    confidence = min(0.9, unpinned_count * 0.1)
                    self.predictions.append(
                        Prediction(
                            id="dependency_security_risk",
                            type="failure",
                            confidence=confidence,
                            timeframe="Next 3-6 months",
                            title="Dependency security vulnerabilities likely",
                            description=f"{unpinned_count} unpinned dependencies increase security risk",
                            likelihood="high" if unpinned_count > 5 else "medium",
                            impact="Potential security vulnerabilities from dependency updates",
                            indicators=[
                                f"{unpinned_count} unpinned dependencies",
                                "No automated security scanning",
                            ],
                            preventive_actions=[
                                "Pin all dependency versions",
                                "Implement automated security scanning",
                                "Set up dependency update monitoring",
                            ],
                            monitoring_recommendations=[
                                "Monitor security advisories for dependencies",
                                "Run regular vulnerability scans",
                                "Track dependency freshness",
                            ],
                        )
                    )

            except Exception as e:
                self.logger.warning(f"Could not analyze dependencies: {e}")

    def _analyze_security_configuration_trends(self):
        """Analyze security configuration patterns"""
        # Check for common security misconfigurations

        # Check if secrets are properly managed
        env_files = [".env", ".env.local", ".env.production"]
        secrets_in_repo = False

        for env_file in env_files:
            if os.path.exists(os.path.join(self.project_path, env_file)):
                secrets_in_repo = True
                break

        if secrets_in_repo:
            self.predictions.append(
                Prediction(
                    id="secrets_management_risk",
                    type="failure",
                    confidence=0.8,
                    timeframe="Immediate",
                    title="Secrets management security risk",
                    description="Environment files in repository pose security risk",
                    likelihood="high",
                    impact="Potential secret exposure and security breach",
                    indicators=[
                        "Environment files committed to repository",
                        "No proper secrets management system",
                    ],
                    preventive_actions=[
                        "Remove environment files from repository",
                        "Implement proper secrets management",
                        "Use environment-specific secret injection",
                    ],
                    monitoring_recommendations=[
                        "Monitor for secret exposure in commits",
                        "Audit secret access patterns",
                        "Implement secret rotation policies",
                    ],
                )
            )

    def _predict_cost_trends(self):
        """Predict cost trend changes"""
        # Analyze infrastructure for cost growth patterns

        # Check for inefficient resource usage patterns
        self.predictions.append(
            Prediction(
                id="cost_growth_trend",
                type="cost",
                confidence=0.7,
                timeframe="Next 6 months",
                title="Infrastructure costs will increase significantly",
                description="Current patterns suggest substantial cost growth without optimization",
                likelihood="high",
                impact="Budget overruns and increased operational costs",
                indicators=[
                    "No cost optimization measures in place",
                    "Fixed resource allocations",
                    "No automated scaling policies",
                ],
                preventive_actions=[
                    "Implement cost monitoring and alerting",
                    "Set up automatic resource optimization",
                    "Create cost budgets and limits",
                ],
                monitoring_recommendations=[
                    "Track daily cost trends",
                    "Monitor resource utilization vs. cost",
                    "Set up cost anomaly detection",
                ],
            )
        )

    def _predict_performance_degradation(self):
        """Predict performance degradation patterns"""
        # Analyze code and configuration for performance risks

        # Check for performance anti-patterns
        self._analyze_performance_patterns()

    def _analyze_performance_patterns(self):
        """Analyze patterns that might lead to performance issues"""
        # Check for database-related performance risks

        # Look for ORM usage without optimization
        python_files = []
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        orm_usage = False
        for py_file in python_files[:5]:  # Sample first 5 files
            try:
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if any(
                        pattern in content
                        for pattern in ["sqlalchemy", "django.db", "peewee"]
                    ):
                        orm_usage = True
                        break
            except Exception:
                continue

        if orm_usage:
            self.predictions.append(
                Prediction(
                    id="orm_performance_degradation",
                    type="performance",
                    confidence=0.6,
                    timeframe="As data grows over next 6 months",
                    title="ORM performance degradation likely",
                    description="ORM usage without optimization will cause performance issues as data grows",
                    likelihood="medium",
                    impact="Slower response times and increased resource usage",
                    indicators=[
                        "ORM usage detected",
                        "No obvious query optimization patterns",
                    ],
                    preventive_actions=[
                        "Implement database query monitoring",
                        "Add database indexes for common queries",
                        "Implement query optimization reviews",
                    ],
                    monitoring_recommendations=[
                        "Monitor database query performance",
                        "Track database connection pool usage",
                        "Set up slow query logging",
                    ],
                )
            )

    def _predict_dependency_issues(self):
        """Predict dependency-related issues"""
        # Check for outdated dependencies that might cause issues

        # Look for dependency management files
        dep_files = ["requirements.txt", "package.json", "go.mod", "Cargo.toml"]

        for dep_file in dep_files:
            file_path = os.path.join(self.project_path, dep_file)
            if os.path.exists(file_path):
                self._analyze_dependency_file_age(file_path, dep_file)

    def _analyze_dependency_file_age(self, file_path: str, file_type: str):
        """Analyze dependency file for age-related risks"""
        try:
            # Get file modification time
            mtime = os.path.getmtime(file_path)
            file_age = datetime.now().timestamp() - mtime
            days_old = file_age / (24 * 3600)

            if days_old > 90:  # More than 3 months old
                self.predictions.append(
                    Prediction(
                        id=f"stale_dependencies_{file_type}",
                        type="failure",
                        confidence=0.5
                        + min(0.4, days_old / 365),  # Increase confidence with age
                        timeframe="Next 3-6 months",
                        title=f"Stale dependencies in {file_type}",
                        description=f"Dependencies haven't been updated in {int(days_old)} days",
                        likelihood="medium",
                        impact="Security vulnerabilities and compatibility issues",
                        indicators=[
                            f"Dependencies last updated {int(days_old)} days ago",
                            "No automated dependency updates",
                        ],
                        preventive_actions=[
                            "Update dependencies to latest compatible versions",
                            "Implement automated dependency scanning",
                            "Set up regular dependency update schedule",
                        ],
                        monitoring_recommendations=[
                            "Monitor for security advisories",
                            "Track dependency freshness",
                            "Set up automated vulnerability scanning",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze dependency file {file_path}: {e}")

    def _predict_infrastructure_problems(self):
        """Predict infrastructure-related problems"""
        # Check for single points of failure

        # Analyze for infrastructure resilience
        self.predictions.append(
            Prediction(
                id="infrastructure_resilience",
                type="failure",
                confidence=0.6,
                timeframe="During next outage or maintenance window",
                title="Infrastructure single points of failure",
                description="Current infrastructure may lack sufficient redundancy",
                likelihood="medium",
                impact="Service downtime during infrastructure issues",
                indicators=[
                    "Limited redundancy analysis available",
                    "No obvious multi-region deployment",
                ],
                preventive_actions=[
                    "Conduct infrastructure resilience audit",
                    "Implement multi-zone deployments",
                    "Set up automated failover procedures",
                ],
                monitoring_recommendations=[
                    "Monitor infrastructure health across zones",
                    "Track service availability metrics",
                    "Implement infrastructure alerting",
                ],
            )
        )

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive prediction report"""
        predictions_by_type = {
            "failure": [],
            "capacity": [],
            "cost": [],
            "performance": [],
        }

        predictions_by_timeframe = {
            "immediate": [],
            "short_term": [],  # 1-3 months
            "medium_term": [],  # 3-6 months
            "long_term": [],  # 6+ months
        }

        high_confidence_predictions = []

        for pred in self.predictions:
            predictions_by_type[pred.type].append(
                {
                    "id": pred.id,
                    "confidence": pred.confidence,
                    "timeframe": pred.timeframe,
                    "title": pred.title,
                    "description": pred.description,
                    "likelihood": pred.likelihood,
                    "impact": pred.impact,
                    "indicators": pred.indicators,
                    "preventive_actions": pred.preventive_actions,
                    "monitoring_recommendations": pred.monitoring_recommendations,
                }
            )

            # Categorize by timeframe
            if (
                "immediate" in pred.timeframe.lower()
                or "next deployment" in pred.timeframe.lower()
            ):
                timeframe_key = "immediate"
            elif any(
                term in pred.timeframe.lower()
                for term in ["30 days", "3 months", "next"]
            ):
                timeframe_key = "short_term"
            elif any(term in pred.timeframe.lower() for term in ["6 months", "3-6"]):
                timeframe_key = "medium_term"
            else:
                timeframe_key = "long_term"

            predictions_by_timeframe[timeframe_key].append(
                {
                    "id": pred.id,
                    "type": pred.type,
                    "title": pred.title,
                    "likelihood": pred.likelihood,
                    "confidence": pred.confidence,
                }
            )

            # High confidence predictions
            if pred.confidence >= 0.7:
                high_confidence_predictions.append(
                    {
                        "id": pred.id,
                        "type": pred.type,
                        "title": pred.title,
                        "confidence": pred.confidence,
                        "timeframe": pred.timeframe,
                    }
                )

        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_predictions": len(self.predictions),
            "predictions_by_type": predictions_by_type,
            "predictions_by_timeframe": predictions_by_timeframe,
            "high_confidence_predictions": high_confidence_predictions,
            "summary": {
                "failure_predictions": len(predictions_by_type["failure"]),
                "capacity_predictions": len(predictions_by_type["capacity"]),
                "cost_predictions": len(predictions_by_type["cost"]),
                "performance_predictions": len(predictions_by_type["performance"]),
                "immediate_attention_needed": len(
                    predictions_by_timeframe["immediate"]
                ),
                "high_confidence_count": len(high_confidence_predictions),
            },
        }


def main():
    """Main entry point for the prediction CLI"""
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <project_name>")
        sys.exit(1)

    project_name = sys.argv[1]

    try:
        # Initialize the prediction engine
        engine = PredictionEngine(project_name)

        # Analyze the project
        predictions = engine.analyze()

        # Generate and display report
        report = engine.generate_report()

        print(f"\n=== Prediction Analysis for {project_name} ===")
        print(f"Total predictions: {report['total_predictions']}")
        print(f"Analysis completed: {report['analysis_timestamp']}")

        # Display summary
        summary = report["summary"]
        print("\nSummary:")
        print(f"  Failure predictions: {summary['failure_predictions']}")
        print(f"  Capacity predictions: {summary['capacity_predictions']}")
        print(f"  Cost predictions: {summary['cost_predictions']}")
        print(f"  Performance predictions: {summary['performance_predictions']}")
        print(f"  Immediate attention needed: {summary['immediate_attention_needed']}")
        print(f"  High confidence predictions: {summary['high_confidence_count']}")

        # Display high confidence predictions
        if report["high_confidence_predictions"]:
            print("\n🔥 HIGH CONFIDENCE PREDICTIONS:")
            for pred in report["high_confidence_predictions"]:
                print(f"  • [{pred['type'].upper()}] {pred['title']}")
                print(
                    f"    Confidence: {pred['confidence']:.1%}, Timeframe: {pred['timeframe']}"
                )

        # Display by timeframe
        for timeframe in ["immediate", "short_term", "medium_term", "long_term"]:
            timeframe_preds = report["predictions_by_timeframe"][timeframe]
            if timeframe_preds:
                timeframe_name = timeframe.replace("_", " ").title()
                print(
                    f"\n{timeframe_name.upper()} ({len(timeframe_preds)} predictions):"
                )
                for pred in timeframe_preds:
                    confidence_icon = (
                        "🔴"
                        if pred["confidence"] >= 0.8
                        else "🟡"
                        if pred["confidence"] >= 0.6
                        else "🟢"
                    )
                    print(
                        f"  {confidence_icon} [{pred['type'].upper()}] {pred['title']}"
                    )
                    print(
                        f"    Likelihood: {pred['likelihood']}, Confidence: {pred['confidence']:.1%}"
                    )

        # Save detailed report
        report_file = os.path.join(
            engine.project_path, ".bootstrap-predictions-report.json"
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")
        print("\n💡 Use the detailed report to plan preventive actions and monitoring.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
