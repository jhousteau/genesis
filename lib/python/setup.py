#!/usr/bin/env python3
"""
Setup script for Whitehorse Core Library
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = (
    readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""
)

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split("\n")
    requirements = [
        req.strip() for req in requirements if req.strip() and not req.startswith("#")
    ]
else:
    requirements = []

# Core dependencies that are always required
core_requirements = [
    "pydantic>=1.8.0,<3.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.24.0",
    "psutil>=5.8.0",
    "cryptography>=3.4.0",
    "PyJWT>=2.4.0",
    "python-dotenv>=0.19.0",
    "click>=8.0.0",
    "typer>=0.7.0",
    "rich>=12.0.0",
    "structlog>=22.0.0",
]

# Optional dependencies for different cloud providers and features
extras_require = {
    "gcp": [
        "google-cloud-storage>=2.0.0",
        "google-cloud-secretmanager>=2.0.0",
        "google-cloud-logging>=3.0.0",
        "google-auth>=2.0.0",
    ],
    "aws": [
        "boto3>=1.20.0",
        "botocore>=1.23.0",
    ],
    "redis": [
        "redis>=4.0.0",
        "hiredis>=2.0.0",
    ],
    "database": [
        "sqlalchemy>=1.4.0,<3.0.0",
        "psycopg2-binary>=2.9.0",
        "asyncpg>=0.25.0",
        "alembic>=1.7.0",
    ],
    "monitoring": [
        "prometheus-client>=0.14.0",
        "opentelemetry-api>=1.12.0",
        "opentelemetry-sdk>=1.12.0",
        "opentelemetry-exporter-gcp-trace>=1.3.0",
        "opentelemetry-instrumentation>=0.33b0",
    ],
    "dev": [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.19.0",
        "pytest-cov>=3.0.0",
        "black>=22.0.0",
        "isort>=5.10.0",
        "flake8>=4.0.0",
        "mypy>=0.950",
        "pre-commit>=2.17.0",
        "pytest-mock>=3.7.0",
        "fakeredis>=1.8.0",
        "moto>=4.0.0",
    ],
    "docs": [
        "sphinx>=4.5.0",
        "sphinx-rtd-theme>=1.0.0",
        "sphinx-autodoc-typehints>=1.17.0",
        "myst-parser>=0.17.0",
    ],
    "yaml": [
        "PyYAML>=6.0",
    ],
    "async": [
        "aiofiles>=0.8.0",
        "aioredis>=2.0.0",
    ],
}

# All optional dependencies
extras_require["all"] = [
    req for extra_deps in extras_require.values() for req in extra_deps
]

setup(
    name="whitehorse-core",
    version="1.0.0",
    description="Industrial-strength core library for the Universal Project Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Whitehorse Platform Team",
    author_email="platform@whitehorse.dev",
    url="https://github.com/whitehorse/bootstrapper",
    project_urls={
        "Documentation": "https://whitehorse-platform.readthedocs.io/",
        "Source": "https://github.com/whitehorse/bootstrapper",
        "Tracker": "https://github.com/whitehorse/bootstrapper/issues",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    package_data={
        "whitehorse_core": ["py.typed"],
    },
    python_requires=">=3.8",
    install_requires=core_requirements + requirements,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "whitehorse=whitehorse_core.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Build Tools",
        "Typing :: Typed",
    ],
    keywords=[
        "cloud",
        "gcp",
        "aws",
        "azure",
        "microservices",
        "infrastructure",
        "devops",
        "platform",
        "library",
        "utilities",
        "observability",
        "monitoring",
        "logging",
        "security",
        "configuration",
        "storage",
        "api-client",
        "health-checks",
    ],
    zip_safe=False,
    test_suite="tests",
)
