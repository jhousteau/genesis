#!/usr/bin/env python3

"""
Optimization Engine for Universal Project Platform
Version: 1.0.0

This module provides automated optimization analysis for cost and performance.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class OptimizationRecommendation:
    """Represents an optimization recommendation"""

    id: str
    category: str  # 'cost', 'performance', 'resource', 'security'
    priority: str  # 'low', 'medium', 'high', 'critical'
    title: str
    description: str
    impact: str  # Expected impact description
    effort: str  # Implementation effort: 'low', 'medium', 'high'
    savings_estimate: Optional[str] = None  # Cost savings estimate
    performance_impact: Optional[str] = None  # Performance improvement estimate
    implementation_steps: List[str] = None
    automation_available: bool = False


class OptimizationEngine:
    """Main optimization engine for analyzing projects"""

    def __init__(self, project_name: str, project_path: str = None):
        self.project_name = project_name
        self.project_path = project_path or self._find_project_path(project_name)
        self.logger = self._setup_logging()
        self.recommendations: List[OptimizationRecommendation] = []

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the optimization engine"""
        logger = logging.getLogger(f"optimization.{self.project_name}")
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

    def analyze(self) -> List[OptimizationRecommendation]:
        """Perform comprehensive optimization analysis"""
        self.logger.info(
            f"Analyzing optimization opportunities for: {self.project_name}"
        )
        self.recommendations = []

        # Run all optimization analyzers
        self._analyze_infrastructure_cost()
        self._analyze_container_optimization()
        self._analyze_dependency_optimization()
        self._analyze_build_optimization()
        self._analyze_resource_utilization()
        self._analyze_security_optimization()
        self._analyze_deployment_optimization()

        self.logger.info(
            f"Found {len(self.recommendations)} optimization opportunities"
        )
        return self.recommendations

    def _analyze_infrastructure_cost(self):
        """Analyze infrastructure for cost optimization opportunities"""
        # Check Terraform configurations for cost optimization
        tf_files = self._find_terraform_files()

        if not tf_files:
            return

        for tf_file in tf_files:
            self._analyze_terraform_cost(tf_file)

    def _find_terraform_files(self) -> List[str]:
        """Find all Terraform files in the project"""
        tf_files = []
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".tf"):
                    tf_files.append(os.path.join(root, file))
        return tf_files

    def _analyze_terraform_cost(self, tf_file: str):
        """Analyze a Terraform file for cost optimization"""
        try:
            with open(tf_file, "r") as f:
                content = f.read()

            # Check for oversized instances
            if "machine_type" in content:
                # Look for potentially oversized GCP instances
                oversized_patterns = [
                    "n1-standard-16",
                    "n1-standard-32",
                    "n1-highmem-16",
                    "n1-highmem-32",
                ]

                for pattern in oversized_patterns:
                    if pattern in content:
                        self.recommendations.append(
                            OptimizationRecommendation(
                                id=f"oversized_instance_{pattern}",
                                category="cost",
                                priority="high",
                                title=f"Potentially oversized instance: {pattern}",
                                description=f"Large instance type {pattern} detected. Consider rightsizing based on actual usage.",
                                impact="Potential cost savings of 30-70%",
                                effort="medium",
                                savings_estimate="$500-2000/month",
                                implementation_steps=[
                                    "Monitor current CPU and memory utilization",
                                    "Identify peak usage patterns",
                                    "Test with smaller instance types",
                                    "Implement auto-scaling if needed",
                                ],
                            )
                        )

            # Check for unoptimized storage
            if "disk_type" in content and "pd-ssd" in content:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="ssd_storage_optimization",
                        category="cost",
                        priority="medium",
                        title="SSD storage optimization opportunity",
                        description="Consider using pd-standard for non-performance-critical workloads",
                        impact="Potential cost savings of 60% on storage",
                        effort="low",
                        savings_estimate="$50-500/month",
                        implementation_steps=[
                            "Identify workloads that don't require SSD performance",
                            "Migrate to pd-standard for appropriate workloads",
                            "Use pd-balanced for balanced performance/cost",
                        ],
                    )
                )

            # Check for missing committed use discounts
            if "google_compute_instance" in content:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="committed_use_discounts",
                        category="cost",
                        priority="medium",
                        title="Consider committed use discounts",
                        description="Long-running instances could benefit from committed use discounts",
                        impact="Up to 57% discount on compute costs",
                        effort="low",
                        savings_estimate="$200-1000/month",
                        implementation_steps=[
                            "Analyze usage patterns for predictable workloads",
                            "Purchase 1-year or 3-year committed use contracts",
                            "Apply to sustained usage workloads",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze {tf_file}: {e}")

    def _analyze_container_optimization(self):
        """Analyze container configurations for optimization"""
        dockerfile_path = os.path.join(self.project_path, "Dockerfile")

        if not os.path.exists(dockerfile_path):
            return

        try:
            with open(dockerfile_path, "r") as f:
                content = f.read()

            # Check for multi-stage builds
            if "FROM" in content and content.count("FROM") == 1:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="dockerfile_multistage",
                        category="performance",
                        priority="medium",
                        title="Consider multi-stage Docker build",
                        description="Multi-stage builds can significantly reduce image size",
                        impact="50-80% reduction in image size",
                        effort="medium",
                        performance_impact="Faster deployments, reduced bandwidth",
                        implementation_steps=[
                            "Separate build dependencies from runtime dependencies",
                            "Use slim base images for final stage",
                            "Copy only necessary artifacts between stages",
                        ],
                    )
                )

            # Check for base image optimization
            if "FROM ubuntu" in content or "FROM debian" in content:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="dockerfile_base_image",
                        category="performance",
                        priority="medium",
                        title="Optimize base image choice",
                        description="Consider using Alpine or distroless images for smaller size",
                        impact="60-90% reduction in image size",
                        effort="medium",
                        performance_impact="Faster pulls, reduced attack surface",
                        implementation_steps=[
                            "Evaluate Alpine Linux compatibility",
                            "Consider Google's distroless images",
                            "Test application compatibility",
                        ],
                    )
                )

            # Check for package cache cleanup
            if (
                "apt-get install" in content
                and "rm -rf /var/lib/apt/lists/*" not in content
            ):
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="dockerfile_cache_cleanup",
                        category="performance",
                        priority="low",
                        title="Clean package manager cache",
                        description="Remove package manager cache to reduce image size",
                        impact="10-50MB reduction in image size",
                        effort="low",
                        implementation_steps=[
                            "Add cache cleanup commands after package installation",
                            "Combine install and cleanup in single RUN command",
                        ],
                        automation_available=True,
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze Dockerfile: {e}")

    def _analyze_dependency_optimization(self):
        """Analyze dependencies for optimization opportunities"""
        # Python dependencies
        requirements_file = os.path.join(self.project_path, "requirements.txt")
        if os.path.exists(requirements_file):
            self._analyze_python_dependencies(requirements_file)

        # Node.js dependencies
        package_file = os.path.join(self.project_path, "package.json")
        if os.path.exists(package_file):
            self._analyze_node_dependencies(package_file)

    def _analyze_python_dependencies(self, requirements_file: str):
        """Analyze Python dependencies for optimization"""
        try:
            with open(requirements_file, "r") as f:
                dependencies = f.readlines()

            # Check for heavy dependencies that might have lighter alternatives
            heavy_deps = {
                "pandas": "Consider polars for better performance",
                "requests": "Consider httpx for async support",
                "pillow": "Consider pillow-simd for better performance",
                "numpy": "Ensure you're using optimized BLAS libraries",
            }

            for dep_line in dependencies:
                dep_name = dep_line.split("==")[0].split(">=")[0].strip()
                if dep_name.lower() in heavy_deps:
                    self.recommendations.append(
                        OptimizationRecommendation(
                            id=f"python_dep_{dep_name}",
                            category="performance",
                            priority="low",
                            title=f"Optimize {dep_name} usage",
                            description=heavy_deps[dep_name.lower()],
                            impact="Potential performance improvements",
                            effort="medium",
                            implementation_steps=[
                                f"Evaluate alternatives to {dep_name}",
                                "Benchmark performance differences",
                                "Consider migration if benefits are significant",
                            ],
                        )
                    )

            # Check for development dependencies in production
            dev_deps = ["pytest", "black", "flake8", "mypy", "jupyter"]
            production_dev_deps = []

            for dep_line in dependencies:
                dep_name = dep_line.split("==")[0].split(">=")[0].strip()
                if dep_name.lower() in dev_deps:
                    production_dev_deps.append(dep_name)

            if production_dev_deps:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="python_dev_deps_in_prod",
                        category="performance",
                        priority="medium",
                        title="Development dependencies in production",
                        description=f"Development tools found in requirements.txt: {', '.join(production_dev_deps)}",
                        impact="Reduced image size and deployment time",
                        effort="low",
                        implementation_steps=[
                            "Create requirements-dev.txt for development dependencies",
                            "Remove development tools from main requirements.txt",
                            "Update CI/CD to use appropriate requirements file",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze Python dependencies: {e}")

    def _analyze_node_dependencies(self, package_file: str):
        """Analyze Node.js dependencies for optimization"""
        try:
            with open(package_file, "r") as f:
                package_data = json.load(f)

            dependencies = package_data.get("dependencies", {})
            dev_dependencies = package_data.get("devDependencies", {})

            # Check for lodash optimization
            if "lodash" in dependencies:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="node_lodash_optimization",
                        category="performance",
                        priority="medium",
                        title="Optimize lodash usage",
                        description="Use individual lodash functions instead of entire library",
                        impact="Significant bundle size reduction",
                        effort="medium",
                        performance_impact="Faster load times",
                        implementation_steps=[
                            "Replace 'lodash' with individual function imports",
                            "Use lodash-webpack-plugin for tree shaking",
                            "Consider native ES6+ alternatives",
                        ],
                    )
                )

            # Check for moment.js optimization
            if "moment" in dependencies:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="node_moment_optimization",
                        category="performance",
                        priority="high",
                        title="Replace moment.js with lighter alternative",
                        description="Moment.js is heavy and deprecated. Consider day.js or date-fns",
                        impact="90% bundle size reduction for date handling",
                        effort="medium",
                        performance_impact="Significantly faster load times",
                        implementation_steps=[
                            "Migrate to day.js or date-fns",
                            "Update date manipulation code",
                            "Remove moment.js dependency",
                        ],
                    )
                )

            # Check bundle size
            total_deps = len(dependencies) + len(dev_dependencies)
            if total_deps > 50:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="node_dependency_bloat",
                        category="performance",
                        priority="medium",
                        title=f"High dependency count: {total_deps}",
                        description="Large number of dependencies may impact build and load times",
                        impact="Faster builds and deployments",
                        effort="high",
                        implementation_steps=[
                            "Audit dependencies for unused packages",
                            "Combine similar functionality packages",
                            "Consider implementing simple functions natively",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze Node.js dependencies: {e}")

    def _analyze_build_optimization(self):
        """Analyze build processes for optimization opportunities"""
        # Check for CI/CD optimization
        ci_files = [
            ".github/workflows/*.yml",
            ".gitlab-ci.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
        ]

        for pattern in ci_files:
            if "*" in pattern:
                # Handle wildcard patterns
                import glob

                matches = glob.glob(os.path.join(self.project_path, pattern))
                for match in matches:
                    self._analyze_ci_file(match)
            else:
                ci_file = os.path.join(self.project_path, pattern)
                if os.path.exists(ci_file):
                    self._analyze_ci_file(ci_file)

    def _analyze_ci_file(self, ci_file: str):
        """Analyze CI/CD file for optimization opportunities"""
        try:
            with open(ci_file, "r") as f:
                content = f.read()

            # Check for caching opportunities
            if "cache" not in content.lower():
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="ci_missing_cache",
                        category="performance",
                        priority="medium",
                        title="CI/CD missing dependency caching",
                        description="Build times could be improved with dependency caching",
                        impact="30-70% faster build times",
                        effort="low",
                        performance_impact="Significantly faster CI/CD",
                        implementation_steps=[
                            "Add dependency caching to CI configuration",
                            "Cache Docker layers",
                            "Cache package manager downloads",
                        ],
                    )
                )

            # Check for parallel job opportunities
            if "parallel" not in content.lower() and "matrix" not in content.lower():
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="ci_no_parallel_jobs",
                        category="performance",
                        priority="low",
                        title="Consider parallel CI/CD jobs",
                        description="Tests and builds could potentially run in parallel",
                        impact="Faster feedback on builds",
                        effort="medium",
                        implementation_steps=[
                            "Identify independent test suites",
                            "Configure parallel job execution",
                            "Optimize job dependencies",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze CI file {ci_file}: {e}")

    def _analyze_resource_utilization(self):
        """Analyze resource utilization patterns"""
        # This would typically integrate with monitoring systems
        # For now, provide general recommendations

        # Check for resource limits in Kubernetes
        k8s_files = []
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith((".yaml", ".yml")) and "k8s" in root.lower():
                    k8s_files.append(os.path.join(root, file))

        for k8s_file in k8s_files:
            self._analyze_k8s_resources(k8s_file)

    def _analyze_k8s_resources(self, k8s_file: str):
        """Analyze Kubernetes resource configurations"""
        try:
            with open(k8s_file, "r") as f:
                content = f.read()

            # Check for missing resource limits
            if "kind: Deployment" in content and "resources:" not in content:
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="k8s_missing_resource_limits",
                        category="resource",
                        priority="high",
                        title="Missing Kubernetes resource limits",
                        description="Containers without resource limits can cause cluster instability",
                        impact="Better resource utilization and stability",
                        effort="low",
                        implementation_steps=[
                            "Add CPU and memory limits to containers",
                            "Set appropriate requests based on actual usage",
                            "Monitor and adjust limits based on performance",
                        ],
                    )
                )

            # Check for HPA configuration
            if (
                "kind: Deployment" in content
                and "HorizontalPodAutoscaler" not in content
            ):
                self.recommendations.append(
                    OptimizationRecommendation(
                        id="k8s_missing_hpa",
                        category="resource",
                        priority="medium",
                        title="Consider Horizontal Pod Autoscaling",
                        description="Automatic scaling could optimize resource usage",
                        impact="Better resource efficiency and cost optimization",
                        effort="medium",
                        implementation_steps=[
                            "Implement HorizontalPodAutoscaler",
                            "Define appropriate scaling metrics",
                            "Test scaling behavior under load",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze Kubernetes file {k8s_file}: {e}")

    def _analyze_security_optimization(self):
        """Analyze security configurations for optimization"""
        # Check for security scanning in CI/CD
        self.recommendations.append(
            OptimizationRecommendation(
                id="security_automated_scanning",
                category="security",
                priority="medium",
                title="Implement automated security scanning",
                description="Regular security scanning can prevent vulnerabilities",
                impact="Improved security posture",
                effort="medium",
                implementation_steps=[
                    "Add dependency vulnerability scanning to CI/CD",
                    "Implement container image scanning",
                    "Set up security policy enforcement",
                ],
            )
        )

    def _analyze_deployment_optimization(self):
        """Analyze deployment processes for optimization"""
        # Check for blue-green deployment capability
        self.recommendations.append(
            OptimizationRecommendation(
                id="deployment_zero_downtime",
                category="performance",
                priority="medium",
                title="Implement zero-downtime deployments",
                description="Blue-green or rolling deployments can eliminate downtime",
                impact="Better user experience and availability",
                effort="high",
                implementation_steps=[
                    "Implement health checks",
                    "Configure rolling deployment strategy",
                    "Set up automated rollback on failure",
                ],
            )
        )

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive optimization report"""
        recommendations_by_category = {
            "cost": [],
            "performance": [],
            "resource": [],
            "security": [],
        }

        recommendations_by_priority = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        total_estimated_savings = 0

        for rec in self.recommendations:
            recommendations_by_category[rec.category].append(
                {
                    "id": rec.id,
                    "priority": rec.priority,
                    "title": rec.title,
                    "description": rec.description,
                    "impact": rec.impact,
                    "effort": rec.effort,
                    "savings_estimate": rec.savings_estimate,
                    "performance_impact": rec.performance_impact,
                    "implementation_steps": rec.implementation_steps,
                    "automation_available": rec.automation_available,
                }
            )

            recommendations_by_priority[rec.priority].append(
                {
                    "id": rec.id,
                    "category": rec.category,
                    "title": rec.title,
                    "description": rec.description,
                    "impact": rec.impact,
                    "effort": rec.effort,
                }
            )

        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_recommendations": len(self.recommendations),
            "recommendations_by_category": recommendations_by_category,
            "recommendations_by_priority": recommendations_by_priority,
            "summary": {
                "cost_optimizations": len(recommendations_by_category["cost"]),
                "performance_optimizations": len(
                    recommendations_by_category["performance"]
                ),
                "resource_optimizations": len(recommendations_by_category["resource"]),
                "security_optimizations": len(recommendations_by_category["security"]),
                "high_priority_items": len(recommendations_by_priority["high"]),
                "automation_available": len(
                    [r for r in self.recommendations if r.automation_available]
                ),
            },
        }


def main():
    """Main entry point for the optimization CLI"""
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <project_name>")
        sys.exit(1)

    project_name = sys.argv[1]

    try:
        # Initialize the optimization engine
        engine = OptimizationEngine(project_name)

        # Analyze the project
        recommendations = engine.analyze()

        # Generate and display report
        report = engine.generate_report()

        print(f"\n=== Optimization Analysis for {project_name} ===")
        print(f"Total recommendations: {report['total_recommendations']}")
        print(f"Analysis completed: {report['analysis_timestamp']}")

        # Display summary
        summary = report["summary"]
        print("\nSummary:")
        print(f"  Cost optimizations: {summary['cost_optimizations']}")
        print(f"  Performance optimizations: {summary['performance_optimizations']}")
        print(f"  Resource optimizations: {summary['resource_optimizations']}")
        print(f"  Security optimizations: {summary['security_optimizations']}")
        print(f"  High priority items: {summary['high_priority_items']}")
        print(f"  Automation available: {summary['automation_available']}")

        # Display recommendations by priority
        for priority in ["critical", "high", "medium", "low"]:
            priority_recs = report["recommendations_by_priority"][priority]
            if priority_recs:
                print(f"\n{priority.upper()} PRIORITY ({len(priority_recs)} items):")
                for rec in priority_recs:
                    print(f"  • [{rec['category'].upper()}] {rec['title']}")
                    print(f"    {rec['description']}")
                    print(f"    Impact: {rec['impact']}")
                    print(f"    Effort: {rec['effort']}")
                    print()

        # Save detailed report
        report_file = os.path.join(
            engine.project_path, ".bootstrap-optimization-report.json"
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
