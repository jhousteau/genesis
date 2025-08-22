#!/usr/bin/env python3

"""
Recommendation Engine for Universal Project Platform
Version: 1.0.0

This module provides best practice recommendations and improvements.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class Recommendation:
    """Represents a best practice recommendation"""

    id: str
    category: str  # 'architecture', 'security', 'performance', 'maintainability', 'reliability'
    priority: str  # 'low', 'medium', 'high', 'critical'
    title: str
    description: str
    rationale: str  # Why this recommendation matters
    benefits: List[str]  # Expected benefits
    implementation_guide: List[str]  # Step-by-step implementation
    resources: List[str]  # Links to documentation/resources
    effort_estimate: str  # 'low', 'medium', 'high'
    risk_level: str  # 'low', 'medium', 'high'
    dependencies: List[str] = None  # Other recommendations this depends on


class RecommendationEngine:
    """Main recommendation engine for providing best practice guidance"""

    def __init__(self, project_name: str, project_path: str = None):
        self.project_name = project_name
        self.project_path = project_path or self._find_project_path(project_name)
        self.logger = self._setup_logging()
        self.recommendations: List[Recommendation] = []
        self.project_context = self._analyze_project_context()

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the recommendation engine"""
        logger = logging.getLogger(f"recommendations.{self.project_name}")
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

    def _analyze_project_context(self) -> Dict[str, Any]:
        """Analyze project to understand its context and technology stack"""
        context = {
            "languages": [],
            "frameworks": [],
            "has_dockerfile": False,
            "has_k8s": False,
            "has_terraform": False,
            "has_ci_cd": False,
            "deployment_target": None,
            "project_size": "small",  # small, medium, large
        }

        # Detect languages
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".py"):
                    if "python" not in context["languages"]:
                        context["languages"].append("python")
                elif file.endswith((".js", ".ts")):
                    if "javascript" not in context["languages"]:
                        context["languages"].append("javascript")
                elif file.endswith(".go"):
                    if "go" not in context["languages"]:
                        context["languages"].append("go")
                elif file.endswith(".java"):
                    if "java" not in context["languages"]:
                        context["languages"].append("java")
                elif file == "Dockerfile":
                    context["has_dockerfile"] = True
                elif file.endswith(".tf"):
                    context["has_terraform"] = True
                elif (
                    file in [".gitlab-ci.yml", "Jenkinsfile"]
                    or "github/workflows" in root
                ):
                    context["has_ci_cd"] = True
                elif file.endswith((".yaml", ".yml")) and "k8s" in root.lower():
                    context["has_k8s"] = True

        # Detect frameworks
        if "python" in context["languages"]:
            self._detect_python_frameworks(context)
        if "javascript" in context["languages"]:
            self._detect_js_frameworks(context)

        # Estimate project size
        total_files = sum(len(files) for _, _, files in os.walk(self.project_path))
        if total_files > 100:
            context["project_size"] = "large"
        elif total_files > 30:
            context["project_size"] = "medium"

        return context

    def _detect_python_frameworks(self, context: Dict[str, Any]):
        """Detect Python frameworks in use"""
        requirements_file = os.path.join(self.project_path, "requirements.txt")
        if os.path.exists(requirements_file):
            try:
                with open(requirements_file, "r") as f:
                    content = f.read().lower()

                if "django" in content:
                    context["frameworks"].append("django")
                if "flask" in content:
                    context["frameworks"].append("flask")
                if "fastapi" in content:
                    context["frameworks"].append("fastapi")
                if "sqlalchemy" in content:
                    context["frameworks"].append("sqlalchemy")

            except Exception as e:
                self.logger.warning(f"Could not read requirements.txt: {e}")

    def _detect_js_frameworks(self, context: Dict[str, Any]):
        """Detect JavaScript frameworks in use"""
        package_file = os.path.join(self.project_path, "package.json")
        if os.path.exists(package_file):
            try:
                with open(package_file, "r") as f:
                    package_data = json.load(f)

                dependencies = {
                    **package_data.get("dependencies", {}),
                    **package_data.get("devDependencies", {}),
                }

                if "react" in dependencies:
                    context["frameworks"].append("react")
                if "vue" in dependencies:
                    context["frameworks"].append("vue")
                if "angular" in dependencies or "@angular/core" in dependencies:
                    context["frameworks"].append("angular")
                if "express" in dependencies:
                    context["frameworks"].append("express")
                if "next" in dependencies:
                    context["frameworks"].append("nextjs")

            except Exception as e:
                self.logger.warning(f"Could not read package.json: {e}")

    def analyze(self) -> List[Recommendation]:
        """Generate comprehensive recommendations"""
        self.logger.info(f"Generating recommendations for: {self.project_name}")
        self.recommendations = []

        # Generate recommendations by category
        self._recommend_architecture_improvements()
        self._recommend_security_enhancements()
        self._recommend_performance_optimizations()
        self._recommend_maintainability_improvements()
        self._recommend_reliability_enhancements()
        self._recommend_development_workflow_improvements()
        self._recommend_deployment_improvements()
        self._recommend_monitoring_and_observability()

        self.logger.info(f"Generated {len(self.recommendations)} recommendations")
        return self.recommendations

    def _recommend_architecture_improvements(self):
        """Recommend architectural improvements"""
        # Microservices vs Monolith recommendations
        if (
            self.project_context["project_size"] == "large"
            and len(self.project_context["languages"]) == 1
        ):
            self.recommendations.append(
                Recommendation(
                    id="consider_microservices_architecture",
                    category="architecture",
                    priority="medium",
                    title="Consider microservices architecture for large codebase",
                    description="Large monolithic applications can benefit from microservices decomposition",
                    rationale="Microservices enable better scalability, team autonomy, and technology diversity",
                    benefits=[
                        "Improved scalability and fault isolation",
                        "Better team autonomy and development velocity",
                        "Technology diversity and evolution flexibility",
                        "Easier testing and deployment of individual services",
                    ],
                    implementation_guide=[
                        "Identify bounded contexts in current application",
                        "Start with one or two well-defined services",
                        "Implement service communication patterns (REST/gRPC)",
                        "Set up service discovery and load balancing",
                        "Implement distributed tracing and monitoring",
                    ],
                    resources=[
                        "https://microservices.io/patterns/microservices.html",
                        "https://martinfowler.com/articles/microservices.html",
                    ],
                    effort_estimate="high",
                    risk_level="medium",
                )
            )

        # API Design recommendations
        if (
            "python" in self.project_context["languages"]
            or "javascript" in self.project_context["languages"]
        ):
            self.recommendations.append(
                Recommendation(
                    id="implement_api_versioning",
                    category="architecture",
                    priority="high",
                    title="Implement API versioning strategy",
                    description="Proper API versioning ensures backward compatibility and smooth evolution",
                    rationale="API versioning prevents breaking changes from affecting existing clients",
                    benefits=[
                        "Backward compatibility for existing clients",
                        "Smooth API evolution and feature rollout",
                        "Better client-server contract management",
                        "Reduced deployment risks",
                    ],
                    implementation_guide=[
                        "Choose versioning strategy (URL path, header, or query parameter)",
                        "Implement version routing in API gateway/framework",
                        "Create API documentation for each version",
                        "Set up deprecation policies and timelines",
                        "Implement automated API compatibility testing",
                    ],
                    resources=[
                        "https://restfulapi.net/versioning/",
                        "https://www.troyhunt.com/your-api-versioning-is-wrong-which-is/",
                    ],
                    effort_estimate="medium",
                    risk_level="low",
                )
            )

        # Database architecture recommendations
        if (
            "sqlalchemy" in self.project_context["frameworks"]
            or "database" in str(self.project_context).lower()
        ):
            self.recommendations.append(
                Recommendation(
                    id="implement_database_migrations",
                    category="architecture",
                    priority="high",
                    title="Implement proper database migration strategy",
                    description="Database schema changes should be versioned and automated",
                    rationale="Proper migrations ensure consistent database state across environments",
                    benefits=[
                        "Consistent database schema across environments",
                        "Trackable database changes",
                        "Automated deployment of schema updates",
                        "Rollback capabilities for schema changes",
                    ],
                    implementation_guide=[
                        "Set up migration framework (Alembic for Python, Flyway for Java)",
                        "Create migration scripts for all schema changes",
                        "Implement migration testing in CI/CD",
                        "Set up rollback procedures",
                        "Document migration best practices for team",
                    ],
                    resources=[
                        "https://alembic.sqlalchemy.org/",
                        "https://flywaydb.org/documentation/",
                    ],
                    effort_estimate="medium",
                    risk_level="low",
                )
            )

    def _recommend_security_enhancements(self):
        """Recommend security improvements"""
        # Secrets management
        env_files = [".env", ".env.local", ".env.production"]
        has_env_files = any(
            os.path.exists(os.path.join(self.project_path, f)) for f in env_files
        )

        if has_env_files:
            self.recommendations.append(
                Recommendation(
                    id="implement_proper_secrets_management",
                    category="security",
                    priority="critical",
                    title="Implement proper secrets management system",
                    description="Environment files in repository pose significant security risks",
                    rationale="Hardcoded secrets in version control can lead to security breaches",
                    benefits=[
                        "Eliminated risk of secret exposure in version control",
                        "Centralized secret management and rotation",
                        "Audit trail for secret access",
                        "Role-based access control for secrets",
                    ],
                    implementation_guide=[
                        "Remove all .env files from version control",
                        "Implement secrets management service (HashiCorp Vault, AWS Secrets Manager)",
                        "Update application to fetch secrets at runtime",
                        "Set up secret rotation policies",
                        "Implement secret access auditing",
                    ],
                    resources=[
                        "https://www.vaultproject.io/",
                        "https://aws.amazon.com/secrets-manager/",
                        "https://cloud.google.com/secret-manager",
                    ],
                    effort_estimate="high",
                    risk_level="low",
                )
            )

        # Authentication and authorization
        self.recommendations.append(
            Recommendation(
                id="implement_oauth2_authentication",
                category="security",
                priority="high",
                title="Implement OAuth2/OpenID Connect authentication",
                description="Modern authentication standards provide better security and user experience",
                rationale="OAuth2/OIDC provides secure, standardized authentication with SSO capabilities",
                benefits=[
                    "Industry-standard authentication security",
                    "Single sign-on (SSO) capabilities",
                    "Reduced password management burden",
                    "Better integration with identity providers",
                ],
                implementation_guide=[
                    "Choose OAuth2/OIDC provider (Auth0, Okta, Google, etc.)",
                    "Implement OAuth2 flow in application",
                    "Set up proper token validation and refresh",
                    "Implement role-based access control (RBAC)",
                    "Add session management and logout functionality",
                ],
                resources=[
                    "https://oauth.net/2/",
                    "https://openid.net/connect/",
                    "https://auth0.com/docs/",
                ],
                effort_estimate="medium",
                risk_level="low",
            )
        )

        # Input validation and sanitization
        self.recommendations.append(
            Recommendation(
                id="implement_input_validation",
                category="security",
                priority="high",
                title="Implement comprehensive input validation",
                description="All user inputs should be validated and sanitized to prevent injection attacks",
                rationale="Input validation is the first line of defense against injection attacks",
                benefits=[
                    "Protection against SQL injection and XSS attacks",
                    "Data integrity and application stability",
                    "Reduced security vulnerabilities",
                    "Better error handling and user feedback",
                ],
                implementation_guide=[
                    "Implement input validation library/framework",
                    "Validate all user inputs on both client and server side",
                    "Use parameterized queries for database operations",
                    "Implement output encoding for web applications",
                    "Set up automated security testing",
                ],
                resources=[
                    "https://owasp.org/www-project-top-ten/",
                    "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html",
                ],
                effort_estimate="medium",
                risk_level="low",
            )
        )

    def _recommend_performance_optimizations(self):
        """Recommend performance improvements"""
        # Caching strategy
        self.recommendations.append(
            Recommendation(
                id="implement_caching_strategy",
                category="performance",
                priority="medium",
                title="Implement comprehensive caching strategy",
                description="Caching at multiple levels can significantly improve application performance",
                rationale="Proper caching reduces database load and improves response times",
                benefits=[
                    "Significantly improved response times",
                    "Reduced database and API load",
                    "Better user experience",
                    "Reduced infrastructure costs",
                ],
                implementation_guide=[
                    "Identify cacheable data and operations",
                    "Implement application-level caching (Redis, Memcached)",
                    "Add database query result caching",
                    "Implement HTTP caching headers for web responses",
                    "Set up cache invalidation strategies",
                    "Monitor cache hit rates and performance",
                ],
                resources=[
                    "https://redis.io/documentation",
                    "https://memcached.org/",
                    "https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching",
                ],
                effort_estimate="medium",
                risk_level="low",
            )
        )

        # Database optimization
        if any(
            db in str(self.project_context).lower()
            for db in ["sql", "database", "postgres", "mysql"]
        ):
            self.recommendations.append(
                Recommendation(
                    id="optimize_database_performance",
                    category="performance",
                    priority="high",
                    title="Implement database performance optimization",
                    description="Database optimization is crucial for application performance",
                    rationale="Database bottlenecks are often the primary cause of performance issues",
                    benefits=[
                        "Faster query execution and response times",
                        "Reduced server resource usage",
                        "Better application scalability",
                        "Improved user experience",
                    ],
                    implementation_guide=[
                        "Analyze current query performance and identify slow queries",
                        "Add appropriate database indexes for common queries",
                        "Implement database connection pooling",
                        "Optimize ORM queries and reduce N+1 problems",
                        "Set up database monitoring and alerting",
                        "Consider read replicas for read-heavy workloads",
                    ],
                    resources=[
                        "https://use-the-index-luke.com/",
                        "https://www.postgresql.org/docs/current/performance-tips.html",
                    ],
                    effort_estimate="medium",
                    risk_level="low",
                )
            )

        # Front-end performance (if web application)
        if (
            "react" in self.project_context["frameworks"]
            or "vue" in self.project_context["frameworks"]
        ):
            self.recommendations.append(
                Recommendation(
                    id="optimize_frontend_performance",
                    category="performance",
                    priority="medium",
                    title="Implement front-end performance optimization",
                    description="Front-end optimization improves user experience and SEO",
                    rationale="Fast-loading web applications provide better user experience and rankings",
                    benefits=[
                        "Faster page load times and better user experience",
                        "Improved SEO rankings",
                        "Reduced bandwidth usage",
                        "Better mobile performance",
                    ],
                    implementation_guide=[
                        "Implement code splitting and lazy loading",
                        "Optimize bundle size and remove unused code",
                        "Implement image optimization and lazy loading",
                        "Add service worker for caching",
                        "Use CDN for static assets",
                        "Implement performance monitoring",
                    ],
                    resources=[
                        "https://web.dev/performance/",
                        "https://developers.google.com/web/fundamentals/performance",
                    ],
                    effort_estimate="medium",
                    risk_level="low",
                )
            )

    def _recommend_maintainability_improvements(self):
        """Recommend maintainability improvements"""
        # Code quality and linting
        self.recommendations.append(
            Recommendation(
                id="implement_code_quality_tools",
                category="maintainability",
                priority="high",
                title="Implement comprehensive code quality tools",
                description="Automated code quality tools ensure consistent, maintainable code",
                rationale="Code quality tools catch issues early and enforce consistent standards",
                benefits=[
                    "Consistent code style across team",
                    "Early detection of potential bugs",
                    "Improved code readability and maintainability",
                    "Reduced code review time",
                ],
                implementation_guide=[
                    "Set up linting tools (ESLint for JS, Black/Flake8 for Python)",
                    "Configure pre-commit hooks for automatic formatting",
                    "Implement static type checking (TypeScript, mypy)",
                    "Set up code coverage reporting",
                    "Integrate quality checks into CI/CD pipeline",
                    "Establish code review guidelines",
                ],
                resources=[
                    "https://eslint.org/",
                    "https://black.readthedocs.io/",
                    "https://pre-commit.com/",
                ],
                effort_estimate="low",
                risk_level="low",
            )
        )

        # Documentation
        self.recommendations.append(
            Recommendation(
                id="implement_comprehensive_documentation",
                category="maintainability",
                priority="medium",
                title="Implement comprehensive project documentation",
                description="Good documentation is essential for project maintainability",
                rationale="Documentation reduces onboarding time and improves long-term maintainability",
                benefits=[
                    "Faster developer onboarding",
                    "Reduced support burden",
                    "Better knowledge sharing",
                    "Improved project sustainability",
                ],
                implementation_guide=[
                    "Create comprehensive README with setup instructions",
                    "Document API endpoints and data models",
                    "Add inline code documentation",
                    "Create architecture decision records (ADRs)",
                    "Set up automated documentation generation",
                    "Maintain troubleshooting guides",
                ],
                resources=[
                    "https://www.writethedocs.org/",
                    "https://github.com/joelparkerhenderson/architecture_decision_record",
                ],
                effort_estimate="medium",
                risk_level="low",
            )
        )

        # Testing strategy
        self.recommendations.append(
            Recommendation(
                id="implement_comprehensive_testing",
                category="maintainability",
                priority="high",
                title="Implement comprehensive testing strategy",
                description="A solid testing strategy ensures code reliability and facilitates refactoring",
                rationale="Good tests catch regressions early and enable confident code changes",
                benefits=[
                    "Early detection of regressions",
                    "Confidence in code changes and refactoring",
                    "Better code design through test-driven development",
                    "Reduced production bugs",
                ],
                implementation_guide=[
                    "Implement unit tests for core business logic",
                    "Add integration tests for API endpoints",
                    "Set up end-to-end tests for critical user journeys",
                    "Implement test coverage reporting",
                    "Set up automated test execution in CI/CD",
                    "Establish testing guidelines and practices",
                ],
                resources=[
                    "https://pytest.org/",
                    "https://jestjs.io/",
                    "https://testing-library.com/",
                ],
                effort_estimate="high",
                risk_level="low",
            )
        )

    def _recommend_reliability_enhancements(self):
        """Recommend reliability improvements"""
        # Error handling and monitoring
        self.recommendations.append(
            Recommendation(
                id="implement_error_handling_monitoring",
                category="reliability",
                priority="high",
                title="Implement comprehensive error handling and monitoring",
                description="Proper error handling and monitoring are essential for reliable applications",
                rationale="Good error handling prevents cascading failures and improves user experience",
                benefits=[
                    "Better user experience during errors",
                    "Faster incident detection and resolution",
                    "Improved application stability",
                    "Better debugging and troubleshooting",
                ],
                implementation_guide=[
                    "Implement structured error handling throughout application",
                    "Set up centralized logging with structured logs",
                    "Implement application performance monitoring (APM)",
                    "Set up alerting for critical errors and performance issues",
                    "Create error dashboards and runbooks",
                    "Implement circuit breaker patterns for external dependencies",
                ],
                resources=[
                    "https://sentry.io/",
                    "https://www.datadoghq.com/",
                    "https://martinfowler.com/bliki/CircuitBreaker.html",
                ],
                effort_estimate="medium",
                risk_level="low",
            )
        )

        # Backup and disaster recovery
        self.recommendations.append(
            Recommendation(
                id="implement_backup_disaster_recovery",
                category="reliability",
                priority="high",
                title="Implement backup and disaster recovery strategy",
                description="Backup and disaster recovery plans are essential for business continuity",
                rationale="Data loss and extended downtime can be catastrophic for business operations",
                benefits=[
                    "Protection against data loss",
                    "Faster recovery from disasters",
                    "Business continuity assurance",
                    "Compliance with data protection regulations",
                ],
                implementation_guide=[
                    "Implement automated database backups",
                    "Set up cross-region data replication",
                    "Create disaster recovery runbooks",
                    "Implement infrastructure as code for quick recovery",
                    "Test backup and recovery procedures regularly",
                    "Document recovery time and point objectives (RTO/RPO)",
                ],
                resources=[
                    "https://aws.amazon.com/disaster-recovery/",
                    "https://cloud.google.com/architecture/disaster-recovery",
                ],
                effort_estimate="high",
                risk_level="medium",
            )
        )

        # Health checks and graceful shutdown
        if self.project_context["has_dockerfile"] or self.project_context["has_k8s"]:
            self.recommendations.append(
                Recommendation(
                    id="implement_health_checks_graceful_shutdown",
                    category="reliability",
                    priority="medium",
                    title="Implement health checks and graceful shutdown",
                    description="Health checks and graceful shutdown improve application reliability",
                    rationale="Proper health checks enable better load balancing and faster failure detection",
                    benefits=[
                        "Better load balancer health detection",
                        "Faster failure detection and recovery",
                        "Reduced connection errors during deployments",
                        "Improved application stability",
                    ],
                    implementation_guide=[
                        "Implement application health check endpoints",
                        "Add readiness and liveness probes for Kubernetes",
                        "Implement graceful shutdown handling",
                        "Set up health check monitoring and alerting",
                        "Test health checks under various failure scenarios",
                    ],
                    resources=[
                        "https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/",
                        "https://docs.docker.com/engine/reference/builder/#healthcheck",
                    ],
                    effort_estimate="low",
                    risk_level="low",
                )
            )

    def _recommend_development_workflow_improvements(self):
        """Recommend development workflow improvements"""
        # Git workflow
        self.recommendations.append(
            Recommendation(
                id="implement_git_workflow",
                category="maintainability",
                priority="medium",
                title="Implement structured Git workflow",
                description="A structured Git workflow improves collaboration and code quality",
                rationale="Good Git practices prevent conflicts and enable better collaboration",
                benefits=[
                    "Better collaboration and reduced conflicts",
                    "Cleaner commit history",
                    "Easier code reviews and rollbacks",
                    "Improved release management",
                ],
                implementation_guide=[
                    "Adopt Git flow or GitHub flow branching strategy",
                    "Set up branch protection rules",
                    "Implement commit message conventions",
                    "Set up automated branch cleanup",
                    "Create pull request templates",
                    "Establish code review guidelines",
                ],
                resources=[
                    "https://www.atlassian.com/git/tutorials/comparing-workflows",
                    "https://guides.github.com/introduction/flow/",
                ],
                effort_estimate="low",
                risk_level="low",
            )
        )

        # Development environment
        self.recommendations.append(
            Recommendation(
                id="standardize_development_environment",
                category="maintainability",
                priority="medium",
                title="Standardize development environment setup",
                description="Consistent development environments reduce setup time and bugs",
                rationale="Environment consistency eliminates 'works on my machine' problems",
                benefits=[
                    "Faster developer onboarding",
                    "Reduced environment-related bugs",
                    "Consistent behavior across team",
                    "Easier debugging and support",
                ],
                implementation_guide=[
                    "Create Docker-based development environment",
                    "Use dependency management tools (pipenv, npm, etc.)",
                    "Document environment setup process",
                    "Create development setup scripts",
                    "Use environment variables for configuration",
                    "Set up IDE/editor configurations",
                ],
                resources=[
                    "https://docs.docker.com/compose/",
                    "https://pipenv.pypa.io/",
                    "https://direnv.net/",
                ],
                effort_estimate="medium",
                risk_level="low",
            )
        )

    def _recommend_deployment_improvements(self):
        """Recommend deployment improvements"""
        # CI/CD pipeline
        if not self.project_context["has_ci_cd"]:
            self.recommendations.append(
                Recommendation(
                    id="implement_cicd_pipeline",
                    category="reliability",
                    priority="critical",
                    title="Implement CI/CD pipeline",
                    description="Automated CI/CD pipelines are essential for reliable deployments",
                    rationale="CI/CD reduces deployment risks and enables faster delivery",
                    benefits=[
                        "Faster and more reliable deployments",
                        "Reduced manual errors",
                        "Consistent deployment process",
                        "Faster feedback on code changes",
                    ],
                    implementation_guide=[
                        "Choose CI/CD platform (GitHub Actions, GitLab CI, Jenkins)",
                        "Set up automated testing in pipeline",
                        "Implement automated deployment to staging",
                        "Add deployment approval gates for production",
                        "Set up automated rollback on failure",
                        "Implement deployment monitoring and notifications",
                    ],
                    resources=[
                        "https://docs.github.com/en/actions",
                        "https://docs.gitlab.com/ee/ci/",
                        "https://www.jenkins.io/doc/",
                    ],
                    effort_estimate="high",
                    risk_level="low",
                )
            )

        # Infrastructure as Code
        if not self.project_context["has_terraform"]:
            self.recommendations.append(
                Recommendation(
                    id="implement_infrastructure_as_code",
                    category="reliability",
                    priority="high",
                    title="Implement Infrastructure as Code",
                    description="Infrastructure as Code enables repeatable and version-controlled infrastructure",
                    rationale="IaC reduces configuration drift and enables consistent environments",
                    benefits=[
                        "Repeatable infrastructure deployments",
                        "Version-controlled infrastructure changes",
                        "Reduced configuration drift",
                        "Faster disaster recovery",
                    ],
                    implementation_guide=[
                        "Choose IaC tool (Terraform, CloudFormation, Pulumi)",
                        "Define infrastructure requirements",
                        "Create infrastructure modules and templates",
                        "Set up infrastructure CI/CD pipeline",
                        "Implement infrastructure testing",
                        "Document infrastructure architecture",
                    ],
                    resources=[
                        "https://www.terraform.io/",
                        "https://aws.amazon.com/cloudformation/",
                        "https://www.pulumi.com/",
                    ],
                    effort_estimate="high",
                    risk_level="medium",
                )
            )

        # Container strategy
        if not self.project_context["has_dockerfile"]:
            self.recommendations.append(
                Recommendation(
                    id="implement_containerization",
                    category="reliability",
                    priority="medium",
                    title="Implement application containerization",
                    description="Containerization improves deployment consistency and portability",
                    rationale="Containers eliminate environment differences and improve scalability",
                    benefits=[
                        "Consistent runtime environment",
                        "Improved portability across platforms",
                        "Better resource utilization",
                        "Easier scaling and orchestration",
                    ],
                    implementation_guide=[
                        "Create optimized Dockerfile",
                        "Implement multi-stage builds",
                        "Set up container registry",
                        "Implement container security scanning",
                        "Create docker-compose for local development",
                        "Consider Kubernetes for orchestration",
                    ],
                    resources=[
                        "https://docs.docker.com/",
                        "https://kubernetes.io/docs/",
                    ],
                    effort_estimate="medium",
                    risk_level="low",
                )
            )

    def _recommend_monitoring_and_observability(self):
        """Recommend monitoring and observability improvements"""
        # Application monitoring
        self.recommendations.append(
            Recommendation(
                id="implement_application_monitoring",
                category="reliability",
                priority="high",
                title="Implement comprehensive application monitoring",
                description="Application monitoring provides visibility into system behavior and performance",
                rationale="Good monitoring enables proactive issue detection and faster resolution",
                benefits=[
                    "Proactive issue detection",
                    "Faster incident resolution",
                    "Better understanding of system behavior",
                    "Data-driven optimization decisions",
                ],
                implementation_guide=[
                    "Implement application metrics collection",
                    "Set up logging aggregation and analysis",
                    "Create performance dashboards",
                    "Set up alerting for critical metrics",
                    "Implement distributed tracing for microservices",
                    "Create monitoring runbooks",
                ],
                resources=[
                    "https://prometheus.io/",
                    "https://grafana.com/",
                    "https://www.elastic.co/elk-stack",
                ],
                effort_estimate="medium",
                risk_level="low",
            )
        )

        # Business metrics
        self.recommendations.append(
            Recommendation(
                id="implement_business_metrics_monitoring",
                category="reliability",
                priority="medium",
                title="Implement business metrics monitoring",
                description="Business metrics provide insights into application value and user behavior",
                rationale="Business metrics help measure success and guide product decisions",
                benefits=[
                    "Better understanding of user behavior",
                    "Data-driven product decisions",
                    "Early detection of business issues",
                    "Improved product-market fit",
                ],
                implementation_guide=[
                    "Identify key business metrics and KPIs",
                    "Implement event tracking and analytics",
                    "Create business dashboards",
                    "Set up alerting for business anomalies",
                    "Implement A/B testing framework",
                    "Create regular business metrics reports",
                ],
                resources=[
                    "https://analytics.google.com/",
                    "https://mixpanel.com/",
                    "https://amplitude.com/",
                ],
                effort_estimate="medium",
                risk_level="low",
            )
        )

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive recommendations report"""
        recommendations_by_category = {
            "architecture": [],
            "security": [],
            "performance": [],
            "maintainability": [],
            "reliability": [],
        }

        recommendations_by_priority = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        implementation_roadmap = {
            "phase_1_immediate": [],  # Critical and high priority, low effort
            "phase_2_short_term": [],  # High and medium priority, medium effort
            "phase_3_long_term": [],  # High priority, high effort + all others
        }

        for rec in self.recommendations:
            rec_data = {
                "id": rec.id,
                "category": rec.category,
                "priority": rec.priority,
                "title": rec.title,
                "description": rec.description,
                "rationale": rec.rationale,
                "benefits": rec.benefits,
                "implementation_guide": rec.implementation_guide,
                "resources": rec.resources,
                "effort_estimate": rec.effort_estimate,
                "risk_level": rec.risk_level,
                "dependencies": rec.dependencies or [],
            }

            recommendations_by_category[rec.category].append(rec_data)
            recommendations_by_priority[rec.priority].append(rec_data)

            # Categorize into implementation phases
            if rec.priority in ["critical", "high"] and rec.effort_estimate == "low":
                implementation_roadmap["phase_1_immediate"].append(rec_data)
            elif rec.priority in ["high", "medium"] and rec.effort_estimate == "medium":
                implementation_roadmap["phase_2_short_term"].append(rec_data)
            else:
                implementation_roadmap["phase_3_long_term"].append(rec_data)

        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "project_context": self.project_context,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_recommendations": len(self.recommendations),
            "recommendations_by_category": recommendations_by_category,
            "recommendations_by_priority": recommendations_by_priority,
            "implementation_roadmap": implementation_roadmap,
            "summary": {
                "architecture_recommendations": len(
                    recommendations_by_category["architecture"]
                ),
                "security_recommendations": len(
                    recommendations_by_category["security"]
                ),
                "performance_recommendations": len(
                    recommendations_by_category["performance"]
                ),
                "maintainability_recommendations": len(
                    recommendations_by_category["maintainability"]
                ),
                "reliability_recommendations": len(
                    recommendations_by_category["reliability"]
                ),
                "critical_priority": len(recommendations_by_priority["critical"]),
                "high_priority": len(recommendations_by_priority["high"]),
                "immediate_actions": len(implementation_roadmap["phase_1_immediate"]),
                "project_languages": self.project_context["languages"],
                "project_frameworks": self.project_context["frameworks"],
            },
        }


def main():
    """Main entry point for the recommendation CLI"""
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <project_name>")
        sys.exit(1)

    project_name = sys.argv[1]

    try:
        # Initialize the recommendation engine
        engine = RecommendationEngine(project_name)

        # Analyze the project
        recommendations = engine.analyze()

        # Generate and display report
        report = engine.generate_report()

        print(f"\n=== Best Practice Recommendations for {project_name} ===")
        print(f"Total recommendations: {report['total_recommendations']}")
        print(f"Analysis completed: {report['analysis_timestamp']}")

        # Display project context
        context = report["project_context"]
        print("\nProject Context:")
        print(
            f"  Languages: {', '.join(context['languages']) if context['languages'] else 'Not detected'}"
        )
        print(
            f"  Frameworks: {', '.join(context['frameworks']) if context['frameworks'] else 'Not detected'}"
        )
        print(f"  Size: {context['project_size']}")
        print(f"  Has Docker: {context['has_dockerfile']}")
        print(f"  Has K8s: {context['has_k8s']}")
        print(f"  Has Terraform: {context['has_terraform']}")
        print(f"  Has CI/CD: {context['has_ci_cd']}")

        # Display summary
        summary = report["summary"]
        print("\nRecommendations by Category:")
        print(f"  Architecture: {summary['architecture_recommendations']}")
        print(f"  Security: {summary['security_recommendations']}")
        print(f"  Performance: {summary['performance_recommendations']}")
        print(f"  Maintainability: {summary['maintainability_recommendations']}")
        print(f"  Reliability: {summary['reliability_recommendations']}")

        print("\nBy Priority:")
        print(f"  Critical: {summary['critical_priority']}")
        print(f"  High: {summary['high_priority']}")
        print(f"  Immediate actions needed: {summary['immediate_actions']}")

        # Display implementation roadmap
        roadmap = report["implementation_roadmap"]
        print("\n📋 IMPLEMENTATION ROADMAP:")

        if roadmap["phase_1_immediate"]:
            print(
                f"\n🚨 PHASE 1 - IMMEDIATE (Quick wins, {len(roadmap['phase_1_immediate'])} items):"
            )
            for rec in roadmap["phase_1_immediate"]:
                print(f"  • [{rec['category'].upper()}] {rec['title']}")
                print(
                    f"    Priority: {rec['priority']}, Effort: {rec['effort_estimate']}"
                )

        if roadmap["phase_2_short_term"]:
            print(
                f"\n⏳ PHASE 2 - SHORT TERM (1-3 months, {len(roadmap['phase_2_short_term'])} items):"
            )
            for rec in roadmap["phase_2_short_term"]:
                print(f"  • [{rec['category'].upper()}] {rec['title']}")
                print(
                    f"    Priority: {rec['priority']}, Effort: {rec['effort_estimate']}"
                )

        if roadmap["phase_3_long_term"]:
            print(
                f"\n🎯 PHASE 3 - LONG TERM (3+ months, {len(roadmap['phase_3_long_term'])} items):"
            )
            for rec in roadmap["phase_3_long_term"]:
                print(f"  • [{rec['category'].upper()}] {rec['title']}")
                print(
                    f"    Priority: {rec['priority']}, Effort: {rec['effort_estimate']}"
                )

        # Display critical recommendations in detail
        critical_recs = report["recommendations_by_priority"]["critical"]
        if critical_recs:
            print("\n🔥 CRITICAL RECOMMENDATIONS (IMMEDIATE ACTION REQUIRED):")
            for rec in critical_recs:
                print(f"\n• {rec['title']}")
                print(f"  {rec['description']}")
                print(f"  Why: {rec['rationale']}")
                print(f"  Benefits: {', '.join(rec['benefits'][:2])}...")
                print(f"  Effort: {rec['effort_estimate']}, Risk: {rec['risk_level']}")

        # Save detailed report
        report_file = os.path.join(
            engine.project_path, ".bootstrap-recommendations-report.json"
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")
        print(
            "\n💡 Use the detailed report for step-by-step implementation guides and resources."
        )

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
