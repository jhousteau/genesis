"""
Dynamic Configuration Manager for Universal Platform Monitoring
Automatically manages and updates monitoring configurations based on service discovery.
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

try:
    import jinja2

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("Jinja2 not available, template rendering disabled")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Requests not available, API updates disabled")


@dataclass
class ConfigUpdate:
    """Represents a configuration update operation."""

    config_type: str  # prometheus, grafana, alertmanager, etc.
    file_path: str
    content: str
    backup_path: Optional[str] = None
    applied_at: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None


class ConfigurationManager:
    """Manages dynamic configuration updates for monitoring stack."""

    def __init__(self, config_file: str = "config-manager.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
        self.template_env = self._setup_templates()
        self.update_history: List[ConfigUpdate] = []

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.get("log_level", "INFO")),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration manager settings."""
        default_config = {
            "log_level": "INFO",
            "backup_enabled": True,
            "backup_retention_days": 7,
            "dry_run": False,
            "templates_dir": "templates",
            "configurations": {
                "prometheus": {
                    "config_file": "/etc/prometheus/prometheus.yml",
                    "reload_url": "http://prometheus:9090/-/reload",
                    "template": "prometheus.yml.j2",
                    "backup_dir": "/var/backups/prometheus",
                },
                "grafana": {
                    "provisioning_dir": "/etc/grafana/provisioning",
                    "dashboards_dir": "/etc/grafana/provisioning/dashboards",
                    "datasources_dir": "/etc/grafana/provisioning/datasources",
                    "reload_url": "http://grafana:3000/api/admin/provisioning/dashboards/reload",
                    "backup_dir": "/var/backups/grafana",
                },
                "alertmanager": {
                    "config_file": "/etc/alertmanager/alertmanager.yml",
                    "reload_url": "http://alertmanager:9093/-/reload",
                    "template": "alertmanager.yml.j2",
                    "backup_dir": "/var/backups/alertmanager",
                },
                "jaeger": {
                    "config_file": "/etc/jaeger/jaeger.yml",
                    "template": "jaeger.yml.j2",
                    "backup_dir": "/var/backups/jaeger",
                },
            },
            "service_discovery": {
                "registry_file": "/var/lib/monitoring/services.json",
                "targets_file": "/etc/prometheus/targets/services.json",
            },
            "notification": {
                "webhook_urls": [],
                "slack_channels": [],
                "email_recipients": [],
            },
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._deep_update(default_config, user_config)
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")

        return default_config

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> Dict:
        """Recursively update nested dictionaries."""
        for key, value in update_dict.items():
            if (
                isinstance(value, dict)
                and key in base_dict
                and isinstance(base_dict[key], dict)
            ):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
        return base_dict

    def _setup_templates(self) -> Optional[jinja2.Environment]:
        """Setup Jinja2 template environment."""
        if not JINJA2_AVAILABLE:
            return None

        templates_dir = self.config.get("templates_dir", "templates")
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir, exist_ok=True)
            self._create_default_templates(templates_dir)

        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            autoescape=jinja2.select_autoescape(["yml", "yaml"]),
        )

    def _create_default_templates(self, templates_dir: str):
        """Create default configuration templates."""
        # Prometheus template
        prometheus_template = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "/etc/prometheus/rules/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # File-based service discovery
  - job_name: 'file-sd'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.json'
        refresh_interval: 30s

{% for service in services %}
  {% if service.monitoring_enabled %}
  - job_name: '{{ service.name }}-{{ service.environment }}'
    static_configs:
      - targets: ['{{ service.host }}:{{ service.port }}']
        labels:
          service: '{{ service.name }}'
          environment: '{{ service.environment }}'
          team: '{{ service.team }}'
          type: '{{ service.type }}'
          language: '{{ service.language }}'
          framework: '{{ service.framework }}'
    metrics_path: '{{ service.metrics_path }}'
    scrape_interval: 30s
    scrape_timeout: 10s
  {% endif %}
{% endfor %}

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
"""

        # Alertmanager template
        alertmanager_template = """
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alertmanager@universal-platform.com'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
{% for team in teams %}
    - match:
        team: '{{ team.name }}'
      receiver: '{{ team.name }}-alerts'
{% endfor %}

receivers:
  - name: 'default'
    slack_configs:
      - api_url: '{{ default_slack_webhook }}'
        channel: '#alerts'
        title: 'Universal Platform Alert'
        text: '{{ "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}" }}'

{% for team in teams %}
  - name: '{{ team.name }}-alerts'
    {% if team.slack_channel %}
    slack_configs:
      - api_url: '{{ team.slack_webhook }}'
        channel: '{{ team.slack_channel }}'
        title: '{{ team.name }} Service Alert'
        text: '{{ "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}" }}'
    {% endif %}
    {% if team.email_addresses %}
    email_configs:
      {% for email in team.email_addresses %}
      - to: '{{ email }}'
        subject: '{{ team.name }} Service Alert'
        body: '{{ "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}" }}'
      {% endfor %}
    {% endif %}
{% endfor %}

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster', 'service']
"""

        # Jaeger template
        jaeger_template = """
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: universal-platform-jaeger
spec:
  strategy: production
  storage:
    type: elasticsearch
    elasticsearch:
      nodeCount: 3
      storage:
        storageClassName: fast-ssd
        size: 100Gi

  collector:
    resources:
      limits:
        cpu: 1000m
        memory: 1Gi
      requests:
        cpu: 500m
        memory: 512Mi

  query:
    resources:
      limits:
        cpu: 500m
        memory: 512Mi
      requests:
        cpu: 250m
        memory: 256Mi

{% for service in services %}
  {% if service.type in ['api_service', 'web_application'] %}
  # Auto-instrument {{ service.name }}
  {% endif %}
{% endfor %}
"""

        # Write templates
        templates = {
            "prometheus.yml.j2": prometheus_template,
            "alertmanager.yml.j2": alertmanager_template,
            "jaeger.yml.j2": jaeger_template,
        }

        for filename, content in templates.items():
            template_path = os.path.join(templates_dir, filename)
            with open(template_path, "w") as f:
                f.write(content.strip())

        self.logger.info(f"Created default templates in {templates_dir}")

    def load_services(self) -> List[Dict[str, Any]]:
        """Load discovered services from registry."""
        registry_file = self.config["service_discovery"]["registry_file"]

        if not os.path.exists(registry_file):
            self.logger.warning(f"Service registry not found: {registry_file}")
            return []

        try:
            with open(registry_file, "r") as f:
                registry = json.load(f)

            services = list(registry.values())
            self.logger.info(f"Loaded {len(services)} services from registry")
            return services

        except Exception as e:
            self.logger.error(f"Failed to load services: {e}")
            return []

    def generate_prometheus_config(self, services: List[Dict[str, Any]]) -> str:
        """Generate Prometheus configuration from services."""
        if not self.template_env:
            self.logger.error("Template environment not available")
            return ""

        try:
            template = self.template_env.get_template("prometheus.yml.j2")

            # Filter services for Prometheus monitoring
            prometheus_services = [
                s for s in services if s.get("monitoring_enabled", False)
            ]

            config_content = template.render(
                services=prometheus_services, generated_at=datetime.now().isoformat()
            )

            return config_content

        except Exception as e:
            self.logger.error(f"Failed to generate Prometheus config: {e}")
            return ""

    def generate_alertmanager_config(self, services: List[Dict[str, Any]]) -> str:
        """Generate Alertmanager configuration from services."""
        if not self.template_env:
            self.logger.error("Template environment not available")
            return ""

        try:
            template = self.template_env.get_template("alertmanager.yml.j2")

            # Extract unique teams and their notification preferences
            teams = {}
            for service in services:
                team_name = service.get("team", "unknown")
                if team_name not in teams:
                    teams[team_name] = {
                        "name": team_name,
                        "slack_channel": service.get("labels", {}).get("slack_channel"),
                        "slack_webhook": service.get("labels", {}).get("slack_webhook"),
                        "email_addresses": [],
                    }

                # Add email addresses from service annotations
                if "annotations" in service:
                    emails = service["annotations"].get("team_emails", "")
                    if emails:
                        email_list = [e.strip() for e in emails.split(",")]
                        teams[team_name]["email_addresses"].extend(email_list)

            config_content = template.render(
                teams=list(teams.values()),
                default_slack_webhook=self.config.get("notification", {}).get(
                    "default_slack_webhook", ""
                ),
                generated_at=datetime.now().isoformat(),
            )

            return config_content

        except Exception as e:
            self.logger.error(f"Failed to generate Alertmanager config: {e}")
            return ""

    def generate_grafana_datasources(
        self, services: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate Grafana datasource configuration."""
        datasources = {
            "apiVersion": 1,
            "datasources": [
                {
                    "name": "Prometheus",
                    "type": "prometheus",
                    "url": "http://prometheus:9090",
                    "access": "proxy",
                    "isDefault": True,
                    "editable": False,
                },
                {
                    "name": "Jaeger",
                    "type": "jaeger",
                    "url": "http://jaeger-query:16686",
                    "access": "proxy",
                    "editable": False,
                },
                {
                    "name": "Loki",
                    "type": "loki",
                    "url": "http://loki:3100",
                    "access": "proxy",
                    "editable": False,
                },
            ],
        }

        # Add environment-specific datasources
        environments = set(s.get("environment", "unknown") for s in services)

        for env in environments:
            if env != "unknown":
                datasources["datasources"].append(
                    {
                        "name": f"Prometheus-{env}",
                        "type": "prometheus",
                        "url": f"http://prometheus-{env}:9090",
                        "access": "proxy",
                        "editable": False,
                    }
                )

        return datasources

    def backup_configuration(self, config_type: str, file_path: str) -> Optional[str]:
        """Create backup of existing configuration."""
        if not self.config.get("backup_enabled", True):
            return None

        backup_config = self.config["configurations"].get(config_type, {})
        backup_dir = backup_config.get("backup_dir", f"/var/backups/{config_type}")

        if not os.path.exists(file_path):
            return None

        try:
            # Ensure backup directory exists
            os.makedirs(backup_dir, exist_ok=True)

            # Create timestamped backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{os.path.basename(file_path)}.{timestamp}.bak"
            backup_path = os.path.join(backup_dir, backup_filename)

            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")

            # Cleanup old backups
            self._cleanup_old_backups(backup_dir)

            return backup_path

        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None

    def _cleanup_old_backups(self, backup_dir: str):
        """Remove old backup files based on retention policy."""
        retention_days = self.config.get("backup_retention_days", 7)
        cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 3600)

        try:
            for filename in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, filename)
                if os.path.isfile(file_path) and filename.endswith(".bak"):
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        self.logger.debug(f"Removed old backup: {filename}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old backups: {e}")

    def apply_configuration(self, config_type: str, content: str) -> ConfigUpdate:
        """Apply new configuration and reload service."""
        config_info = self.config["configurations"].get(config_type)

        if not config_info:
            return ConfigUpdate(
                config_type=config_type,
                file_path="",
                content=content,
                success=False,
                error_message=f"Unknown configuration type: {config_type}",
            )

        file_path = config_info.get("config_file")
        if not file_path:
            return ConfigUpdate(
                config_type=config_type,
                file_path="",
                content=content,
                success=False,
                error_message=f"No config file defined for {config_type}",
            )

        # Create configuration update record
        update = ConfigUpdate(
            config_type=config_type, file_path=file_path, content=content
        )

        try:
            # Create backup
            backup_path = self.backup_configuration(config_type, file_path)
            update.backup_path = backup_path

            # Validate configuration if possible
            if not self._validate_configuration(config_type, content):
                update.error_message = "Configuration validation failed"
                return update

            if self.config.get("dry_run", False):
                self.logger.info(f"DRY RUN: Would update {file_path}")
                update.success = True
                return update

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write new configuration
            with open(file_path, "w") as f:
                f.write(content)

            # Reload service
            reload_success = self._reload_service(config_type)

            update.applied_at = datetime.now()
            update.success = reload_success

            if reload_success:
                self.logger.info(f"Successfully updated {config_type} configuration")
            else:
                update.error_message = "Service reload failed"
                # Restore backup if reload failed
                if backup_path and os.path.exists(backup_path):
                    shutil.copy2(backup_path, file_path)
                    self.logger.warning("Restored backup due to reload failure")

        except Exception as e:
            update.error_message = str(e)
            self.logger.error(f"Failed to apply {config_type} configuration: {e}")

        self.update_history.append(update)
        return update

    def _validate_configuration(self, config_type: str, content: str) -> bool:
        """Validate configuration content before applying."""
        try:
            if config_type in ["prometheus", "alertmanager"]:
                # Validate YAML syntax
                yaml.safe_load(content)
                return True
            elif config_type == "grafana":
                # Validate JSON syntax for grafana configs
                if content.strip().startswith("{"):
                    json.loads(content)
                else:
                    yaml.safe_load(content)
                return True
            else:
                # Basic YAML validation for others
                yaml.safe_load(content)
                return True

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    def _reload_service(self, config_type: str) -> bool:
        """Reload monitoring service after configuration update."""
        if not REQUESTS_AVAILABLE:
            self.logger.warning("Requests not available, cannot reload services")
            return True  # Assume success if we can't check

        config_info = self.config["configurations"].get(config_type, {})
        reload_url = config_info.get("reload_url")

        if not reload_url:
            self.logger.info(f"No reload URL configured for {config_type}")
            return True

        try:
            response = requests.post(reload_url, timeout=30)
            response.raise_for_status()
            self.logger.info(f"Successfully reloaded {config_type}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reload {config_type}: {e}")
            return False

    def update_all_configurations(self):
        """Update all monitoring configurations based on current service registry."""
        services = self.load_services()

        if not services:
            self.logger.warning("No services found, skipping configuration updates")
            return

        self.logger.info(f"Updating configurations for {len(services)} services")

        # Update Prometheus configuration
        prometheus_config = self.generate_prometheus_config(services)
        if prometheus_config:
            update = self.apply_configuration("prometheus", prometheus_config)
            if not update.success:
                self.logger.error(f"Prometheus update failed: {update.error_message}")

        # Update Alertmanager configuration
        alertmanager_config = self.generate_alertmanager_config(services)
        if alertmanager_config:
            update = self.apply_configuration("alertmanager", alertmanager_config)
            if not update.success:
                self.logger.error(f"Alertmanager update failed: {update.error_message}")

        # Update Grafana datasources
        grafana_config = self.config["configurations"].get("grafana", {})
        datasources_dir = grafana_config.get("datasources_dir")

        if datasources_dir:
            datasources = self.generate_grafana_datasources(services)
            datasources_file = os.path.join(datasources_dir, "universal-platform.yml")

            try:
                os.makedirs(datasources_dir, exist_ok=True)
                with open(datasources_file, "w") as f:
                    yaml.dump(datasources, f, default_flow_style=False)
                self.logger.info("Updated Grafana datasources")
            except Exception as e:
                self.logger.error(f"Failed to update Grafana datasources: {e}")

        # Send notifications about updates
        self._send_update_notifications()

    def _send_update_notifications(self):
        """Send notifications about configuration updates."""
        notification_config = self.config.get("notification", {})

        recent_updates = [
            u
            for u in self.update_history
            if u.applied_at and (datetime.now() - u.applied_at).seconds < 300
        ]

        if not recent_updates:
            return

        message = (
            f"Configuration updates applied to {len(recent_updates)} components:\n"
        )
        for update in recent_updates:
            status = "✅ Success" if update.success else "❌ Failed"
            message += f"  {status} {update.config_type}\n"

        # Send to webhook URLs
        for webhook_url in notification_config.get("webhook_urls", []):
            try:
                requests.post(webhook_url, json={"text": message}, timeout=10)
            except Exception as e:
                self.logger.error(f"Failed to send webhook notification: {e}")

        # Log notification
        self.logger.info(f"Sent notifications for {len(recent_updates)} updates")

    def get_update_status(self) -> Dict[str, Any]:
        """Get status of recent configuration updates."""
        recent_updates = [
            u
            for u in self.update_history
            if u.applied_at and (datetime.now() - u.applied_at).seconds < 3600
        ]

        return {
            "total_updates": len(self.update_history),
            "recent_updates": len(recent_updates),
            "successful_updates": len([u for u in recent_updates if u.success]),
            "failed_updates": len([u for u in recent_updates if not u.success]),
            "last_update": (
                recent_updates[-1].applied_at.isoformat() if recent_updates else None
            ),
            "updates": [
                {
                    "config_type": u.config_type,
                    "applied_at": u.applied_at.isoformat() if u.applied_at else None,
                    "success": u.success,
                    "error_message": u.error_message,
                }
                for u in recent_updates
            ],
        }


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Universal Platform Configuration Manager"
    )
    parser.add_argument(
        "--config", default="config-manager.yaml", help="Configuration file path"
    )
    parser.add_argument(
        "--update-all", action="store_true", help="Update all monitoring configurations"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without applying changes",
    )
    parser.add_argument("--status", action="store_true", help="Show update status")

    args = parser.parse_args()

    # Initialize configuration manager
    manager = ConfigurationManager(args.config)

    if args.dry_run:
        manager.config["dry_run"] = True

    if args.status:
        status = manager.get_update_status()
        print(json.dumps(status, indent=2))
    elif args.update_all:
        manager.update_all_configurations()
    else:
        print("Use --update-all to update configurations or --status to check status")
        parser.print_help()
