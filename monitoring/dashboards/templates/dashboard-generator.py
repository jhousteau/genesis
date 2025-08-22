"""
Dashboard Generator for Universal Platform Monitoring
Automatically generates dashboards based on service discovery and metrics.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import yaml

try:
    import jinja2

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("Jinja2 not available, template rendering will be limited")


class DashboardType(Enum):
    """Types of dashboards that can be generated."""

    SERVICE_OVERVIEW = "service_overview"
    INFRASTRUCTURE = "infrastructure"
    BUSINESS_METRICS = "business_metrics"
    SECURITY = "security"
    COST_OPTIMIZATION = "cost_optimization"
    SLO_TRACKING = "slo_tracking"


class PanelType(Enum):
    """Types of panels available for dashboards."""

    TIMESERIES = "timeseries"
    STAT = "stat"
    BARGAUGE = "bargauge"
    TABLE = "table"
    HEATMAP = "heatmap"
    WORLDMAP = "worldmap"
    PIECHART = "piechart"


@dataclass
class ServiceMetadata:
    """Metadata about a service for dashboard generation."""

    name: str
    type: str  # web, api, worker, database, etc.
    language: str  # python, nodejs, go, etc.
    framework: str  # django, flask, express, gin, etc.
    team: str
    environment: str
    has_database: bool = False
    has_cache: bool = False
    has_queue: bool = False
    custom_metrics: List[str] = field(default_factory=list)
    business_metrics: List[str] = field(default_factory=list)
    slos: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PanelConfig:
    """Configuration for a dashboard panel."""

    title: str
    type: PanelType
    query: str
    description: str = ""
    unit: str = "none"
    thresholds: List[Tuple[str, float]] = field(default_factory=list)  # (color, value)
    width: int = 12
    height: int = 8
    position: Tuple[int, int] = (0, 0)  # (x, y)
    legend_placement: str = "bottom"
    alert_rule: Optional[Dict[str, Any]] = None


class DashboardGenerator:
    """Generates Grafana dashboards based on service metadata."""

    def __init__(self, template_dir: str = "templates", output_dir: str = "generated"):
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.templates = {}

        if JINJA2_AVAILABLE:
            self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_dir),
                autoescape=jinja2.select_autoescape(["html", "xml"]),
            )

        self._ensure_directories()
        self._load_templates()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_templates(self):
        """Load dashboard templates from files."""
        template_files = {
            DashboardType.SERVICE_OVERVIEW: "service-overview.json.j2",
            DashboardType.INFRASTRUCTURE: "infrastructure.json.j2",
            DashboardType.BUSINESS_METRICS: "business-metrics.json.j2",
            DashboardType.SECURITY: "security.json.j2",
            DashboardType.COST_OPTIMIZATION: "cost-optimization.json.j2",
            DashboardType.SLO_TRACKING: "slo-tracking.json.j2",
        }

        for dashboard_type, filename in template_files.items():
            template_path = os.path.join(self.template_dir, filename)
            if os.path.exists(template_path):
                if JINJA2_AVAILABLE:
                    self.templates[dashboard_type] = self.jinja_env.get_template(
                        filename
                    )
                else:
                    with open(template_path, "r") as f:
                        self.templates[dashboard_type] = f.read()
            else:
                logging.warning(f"Template not found: {template_path}")

    def generate_service_dashboard(
        self,
        service: ServiceMetadata,
        dashboard_type: DashboardType = DashboardType.SERVICE_OVERVIEW,
    ) -> Optional[Dict[str, Any]]:
        """Generate a dashboard for a specific service."""
        if dashboard_type not in self.templates:
            logging.error(f"Template not available for {dashboard_type}")
            return None

        # Build dashboard context
        context = self._build_dashboard_context(service, dashboard_type)

        # Generate panels based on service characteristics
        panels = self._generate_panels(service, dashboard_type)
        context["panels"] = panels

        # Render dashboard from template
        if JINJA2_AVAILABLE:
            template = self.templates[dashboard_type]
            dashboard_json = template.render(context)
            return json.loads(dashboard_json)
        else:
            # Basic string replacement for simple templates
            template_content = self.templates[dashboard_type]
            for key, value in context.items():
                if isinstance(value, str):
                    template_content = template_content.replace(f"{{{{{key}}}}}", value)
            return json.loads(template_content)

    def _build_dashboard_context(
        self, service: ServiceMetadata, dashboard_type: DashboardType
    ) -> Dict[str, Any]:
        """Build context variables for dashboard template rendering."""
        return {
            "service_name": service.name,
            "service_type": service.type,
            "language": service.language,
            "framework": service.framework,
            "team": service.team,
            "environment": service.environment,
            "dashboard_title": f"{service.name.title()} - {dashboard_type.value.replace('_', ' ').title()}",
            "dashboard_uid": f"{service.name}-{dashboard_type.value}-{service.environment}",
            "dashboard_tags": [
                "universal-platform",
                service.name,
                service.team,
                service.environment,
                dashboard_type.value,
            ],
            "generated_at": datetime.now().isoformat(),
            "has_database": service.has_database,
            "has_cache": service.has_cache,
            "has_queue": service.has_queue,
            "custom_metrics": service.custom_metrics,
            "business_metrics": service.business_metrics,
            "slos": service.slos,
        }

    def _generate_panels(
        self, service: ServiceMetadata, dashboard_type: DashboardType
    ) -> List[Dict[str, Any]]:
        """Generate panels based on service characteristics and dashboard type."""
        panels = []
        panel_id = 1
        y_position = 0

        if dashboard_type == DashboardType.SERVICE_OVERVIEW:
            panels.extend(self._generate_overview_panels(service, panel_id, y_position))
        elif dashboard_type == DashboardType.INFRASTRUCTURE:
            panels.extend(
                self._generate_infrastructure_panels(service, panel_id, y_position)
            )
        elif dashboard_type == DashboardType.BUSINESS_METRICS:
            panels.extend(self._generate_business_panels(service, panel_id, y_position))
        elif dashboard_type == DashboardType.SECURITY:
            panels.extend(self._generate_security_panels(service, panel_id, y_position))
        elif dashboard_type == DashboardType.SLO_TRACKING:
            panels.extend(self._generate_slo_panels(service, panel_id, y_position))

        return panels

    def _generate_overview_panels(
        self, service: ServiceMetadata, start_id: int, start_y: int
    ) -> List[Dict[str, Any]]:
        """Generate standard overview panels."""
        panels = []

        # Service status panel
        panels.append(
            self._create_panel(
                id=start_id,
                title="Service Status",
                type=PanelType.STAT,
                query=f'up{{job="{service.name}",environment="{service.environment}"}}',
                description="Current service availability status",
                width=6,
                height=8,
                position=(0, start_y),
                thresholds=[("red", 0), ("green", 1)],
                unit="none",
            )
        )

        # Request rate panel
        panels.append(
            self._create_panel(
                id=start_id + 1,
                title="Request Rate",
                type=PanelType.TIMESERIES,
                query=f'sum(rate(http_requests_total{{job="{service.name}",environment="{service.environment}"}}[5m]))',
                description="Requests per second",
                width=18,
                height=8,
                position=(6, start_y),
                unit="reqps",
            )
        )

        # Error rate panel
        panels.append(
            self._create_panel(
                id=start_id + 2,
                title="Error Rate",
                type=PanelType.TIMESERIES,
                query=f'100 * sum(rate(http_requests_total{{job="{service.name}",environment="{service.environment}",code=~"5.."}}[5m])) / sum(rate(http_requests_total{{job="{service.name}",environment="{service.environment}"}}[5m]))',
                description="Percentage of requests resulting in errors",
                width=12,
                height=8,
                position=(0, start_y + 8),
                thresholds=[("green", 0), ("yellow", 1), ("red", 5)],
                unit="percent",
            )
        )

        # Response time panel
        panels.append(
            self._create_panel(
                id=start_id + 3,
                title="Response Time (95th percentile)",
                type=PanelType.TIMESERIES,
                query=f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service.name}",environment="{service.environment}"}}[5m])) by (le)) * 1000',
                description="95th percentile response time in milliseconds",
                width=12,
                height=8,
                position=(12, start_y + 8),
                thresholds=[("green", 0), ("yellow", 500), ("red", 1000)],
                unit="ms",
            )
        )

        return panels

    def _generate_infrastructure_panels(
        self, service: ServiceMetadata, start_id: int, start_y: int
    ) -> List[Dict[str, Any]]:
        """Generate infrastructure monitoring panels."""
        panels = []

        # CPU usage
        panels.append(
            self._create_panel(
                id=start_id,
                title="CPU Usage",
                type=PanelType.TIMESERIES,
                query=f'100 - (avg(irate(node_cpu_seconds_total{{mode="idle",job="{service.name}",environment="{service.environment}"}}[5m])) * 100)',
                description="CPU utilization percentage",
                width=8,
                height=8,
                position=(0, start_y),
                thresholds=[("green", 0), ("yellow", 70), ("red", 85)],
                unit="percent",
            )
        )

        # Memory usage
        panels.append(
            self._create_panel(
                id=start_id + 1,
                title="Memory Usage",
                type=PanelType.TIMESERIES,
                query=f'100 * (1 - node_memory_MemAvailable_bytes{{job="{service.name}",environment="{service.environment}"}} / node_memory_MemTotal_bytes{{job="{service.name}",environment="{service.environment}"}})',
                description="Memory utilization percentage",
                width=8,
                height=8,
                position=(8, start_y),
                thresholds=[("green", 0), ("yellow", 75), ("red", 90)],
                unit="percent",
            )
        )

        # Disk usage
        panels.append(
            self._create_panel(
                id=start_id + 2,
                title="Disk Usage",
                type=PanelType.TIMESERIES,
                query=f'100 * (1 - node_filesystem_avail_bytes{{job="{service.name}",environment="{service.environment}",fstype!="tmpfs"}} / node_filesystem_size_bytes{{job="{service.name}",environment="{service.environment}",fstype!="tmpfs"}})',
                description="Disk utilization percentage",
                width=8,
                height=8,
                position=(16, start_y),
                thresholds=[("green", 0), ("yellow", 80), ("red", 95)],
                unit="percent",
            )
        )

        return panels

    def _generate_business_panels(
        self, service: ServiceMetadata, start_id: int, start_y: int
    ) -> List[Dict[str, Any]]:
        """Generate business metrics panels."""
        panels = []

        for i, metric in enumerate(service.business_metrics):
            panels.append(
                self._create_panel(
                    id=start_id + i,
                    title=metric.replace("_", " ").title(),
                    type=PanelType.TIMESERIES,
                    query=f'{metric}{{job="{service.name}",environment="{service.environment}"}}',
                    description=f"Business metric: {metric}",
                    width=12,
                    height=8,
                    position=(0 if i % 2 == 0 else 12, start_y + (i // 2) * 8),
                    unit="short",
                )
            )

        return panels

    def _generate_security_panels(
        self, service: ServiceMetadata, start_id: int, start_y: int
    ) -> List[Dict[str, Any]]:
        """Generate security monitoring panels."""
        panels = []

        # Authentication failures
        panels.append(
            self._create_panel(
                id=start_id,
                title="Authentication Failures",
                type=PanelType.TIMESERIES,
                query=f'sum(rate(authentication_failures_total{{job="{service.name}",environment="{service.environment}"}}[5m]))',
                description="Rate of authentication failures",
                width=12,
                height=8,
                position=(0, start_y),
                thresholds=[("green", 0), ("yellow", 5), ("red", 20)],
                unit="reqps",
            )
        )

        # Security events
        panels.append(
            self._create_panel(
                id=start_id + 1,
                title="Security Events",
                type=PanelType.TABLE,
                query=f'security_events_total{{job="{service.name}",environment="{service.environment}"}}',
                description="Recent security events by type",
                width=12,
                height=8,
                position=(12, start_y),
                unit="short",
            )
        )

        return panels

    def _generate_slo_panels(
        self, service: ServiceMetadata, start_id: int, start_y: int
    ) -> List[Dict[str, Any]]:
        """Generate SLO tracking panels."""
        panels = []

        for i, slo in enumerate(service.slos):
            panels.append(
                self._create_panel(
                    id=start_id + i,
                    title=f"SLO: {slo['name']}",
                    type=PanelType.STAT,
                    query=slo["query"],
                    description=f"SLO tracking for {slo['name']} (target: {slo['target']}%)",
                    width=8,
                    height=8,
                    position=((i % 3) * 8, start_y + (i // 3) * 8),
                    thresholds=[
                        ("red", 0),
                        ("yellow", slo["target"] * 0.9),
                        ("green", slo["target"]),
                    ],
                    unit="percent",
                )
            )

        return panels

    def _create_panel(
        self,
        id: int,
        title: str,
        type: PanelType,
        query: str,
        description: str = "",
        width: int = 12,
        height: int = 8,
        position: Tuple[int, int] = (0, 0),
        thresholds: List[Tuple[str, float]] = None,
        unit: str = "none",
    ) -> Dict[str, Any]:
        """Create a dashboard panel configuration."""
        thresholds = thresholds or []
        x, y = position

        panel = {
            "id": id,
            "title": title,
            "type": type.value,
            "targets": [
                {"expr": query, "legendFormat": "{{ instance }}", "refId": "A"}
            ],
            "gridPos": {"h": height, "w": width, "x": x, "y": y},
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": color, "value": value}
                            for color, value in thresholds
                        ],
                    },
                }
            },
        }

        if description:
            panel["description"] = description

        return panel

    def save_dashboard(self, dashboard: Dict[str, Any], filename: str = None) -> str:
        """Save generated dashboard to file."""
        if filename is None:
            filename = f"{dashboard.get('uid', 'dashboard')}.json"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w") as f:
            json.dump(dashboard, f, indent=2, separators=(",", ": "))

        logging.info(f"Dashboard saved to {filepath}")
        return filepath

    def generate_from_service_discovery(
        self, prometheus_url: str = "http://localhost:9090"
    ) -> List[str]:
        """Generate dashboards from Prometheus service discovery."""
        # This would typically query Prometheus for available services
        # and automatically generate appropriate dashboards
        generated_files = []

        # Placeholder implementation - would integrate with actual service discovery
        logging.warning("Service discovery integration not yet implemented")

        return generated_files


def load_service_metadata(config_file: str) -> List[ServiceMetadata]:
    """Load service metadata from configuration file."""
    if not os.path.exists(config_file):
        logging.warning(f"Service metadata file not found: {config_file}")
        return []

    try:
        with open(config_file, "r") as f:
            if config_file.endswith(".yaml") or config_file.endswith(".yml"):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)

        services = []
        for service_config in config.get("services", []):
            service = ServiceMetadata(
                name=service_config["name"],
                type=service_config.get("type", "web"),
                language=service_config.get("language", "unknown"),
                framework=service_config.get("framework", "unknown"),
                team=service_config.get("team", "unknown"),
                environment=service_config.get("environment", "development"),
                has_database=service_config.get("has_database", False),
                has_cache=service_config.get("has_cache", False),
                has_queue=service_config.get("has_queue", False),
                custom_metrics=service_config.get("custom_metrics", []),
                business_metrics=service_config.get("business_metrics", []),
                slos=service_config.get("slos", []),
            )
            services.append(service)

        logging.info(f"Loaded metadata for {len(services)} services")
        return services

    except Exception as e:
        logging.error(f"Failed to load service metadata: {e}")
        return []


# CLI interface for dashboard generation
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Grafana dashboards for Universal Platform services"
    )
    parser.add_argument(
        "--config", default="services.yaml", help="Service metadata configuration file"
    )
    parser.add_argument(
        "--template-dir", default="templates", help="Template directory"
    )
    parser.add_argument(
        "--output-dir",
        default="generated",
        help="Output directory for generated dashboards",
    )
    parser.add_argument(
        "--service", help="Generate dashboard for specific service only"
    )
    parser.add_argument(
        "--type",
        choices=[t.value for t in DashboardType],
        default=DashboardType.SERVICE_OVERVIEW.value,
        help="Dashboard type to generate",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Load service metadata
    services = load_service_metadata(args.config)

    if not services:
        logging.error("No services found in configuration")
        exit(1)

    # Filter services if specific service requested
    if args.service:
        services = [s for s in services if s.name == args.service]
        if not services:
            logging.error(f"Service '{args.service}' not found in configuration")
            exit(1)

    # Initialize dashboard generator
    generator = DashboardGenerator(args.template_dir, args.output_dir)

    # Generate dashboards
    dashboard_type = DashboardType(args.type)
    generated_files = []

    for service in services:
        logging.info(f"Generating {dashboard_type.value} dashboard for {service.name}")

        dashboard = generator.generate_service_dashboard(service, dashboard_type)
        if dashboard:
            filename = (
                f"{service.name}-{dashboard_type.value}-{service.environment}.json"
            )
            filepath = generator.save_dashboard(dashboard, filename)
            generated_files.append(filepath)
        else:
            logging.error(f"Failed to generate dashboard for {service.name}")

    logging.info(f"Generated {len(generated_files)} dashboards:")
    for filepath in generated_files:
        print(f"  {filepath}")
