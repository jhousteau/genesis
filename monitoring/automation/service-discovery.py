"""
Service Discovery for Universal Platform Monitoring
Automatically discovers services and configures monitoring.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

try:
    import kubernetes
    from kubernetes import client, config

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    print("Kubernetes client not available, k8s discovery disabled")

try:
    import consul

    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False
    print("Consul client not available, consul discovery disabled")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Requests not available, HTTP discovery limited")


class DiscoveryMethod(Enum):
    """Service discovery methods."""

    KUBERNETES = "kubernetes"
    CONSUL = "consul"
    PROMETHEUS = "prometheus"
    DOCKER = "docker"
    GCP_COMPUTE = "gcp_compute"
    STATIC_CONFIG = "static_config"


class ServiceType(Enum):
    """Types of services that can be discovered."""

    WEB_APPLICATION = "web_application"
    API_SERVICE = "api_service"
    WORKER_SERVICE = "worker_service"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    LOAD_BALANCER = "load_balancer"
    UNKNOWN = "unknown"


@dataclass
class DiscoveredService:
    """Represents a discovered service."""

    name: str
    type: ServiceType
    environment: str
    namespace: str = "default"
    host: str = ""
    port: int = 0
    protocol: str = "http"
    health_check_path: str = "/health"
    metrics_path: str = "/metrics"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    team: str = "unknown"
    version: str = "unknown"
    language: str = "unknown"
    framework: str = "unknown"
    discovered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    monitoring_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type.value,
            "environment": self.environment,
            "namespace": self.namespace,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "health_check_path": self.health_check_path,
            "metrics_path": self.metrics_path,
            "labels": self.labels,
            "annotations": self.annotations,
            "team": self.team,
            "version": self.version,
            "language": self.language,
            "framework": self.framework,
            "discovered_at": self.discovered_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "monitoring_enabled": self.monitoring_enabled,
        }


class ServiceDiscovery:
    """Main service discovery orchestrator."""

    def __init__(self, config_file: str = "discovery-config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
        self.discovered_services: Dict[str, DiscoveredService] = {}
        self.discovery_methods = self._initialize_discovery_methods()

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.get("log_level", "INFO")),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        """Load discovery configuration."""
        default_config = {
            "discovery_interval": 60,
            "service_ttl": 300,
            "log_level": "INFO",
            "enabled_methods": ["kubernetes", "prometheus"],
            "kubernetes": {
                "in_cluster": True,
                "namespace": "default",
                "label_selectors": ["app", "service"],
                "annotation_mappings": {
                    "monitoring.universal-platform/team": "team",
                    "monitoring.universal-platform/language": "language",
                    "monitoring.universal-platform/framework": "framework",
                },
            },
            "prometheus": {"url": "http://prometheus:9090", "query_timeout": 30},
            "consul": {"host": "consul", "port": 8500, "datacenter": "dc1"},
            "gcp": {
                "project_id": "",
                "zones": ["us-central1-a", "us-central1-b"],
                "instance_filters": ["labels.monitoring=enabled"],
            },
            "output": {
                "prometheus_file": "/etc/prometheus/targets/services.json",
                "grafana_provisioning": "/etc/grafana/provisioning/datasources/",
                "service_registry": "/var/lib/monitoring/services.json",
            },
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    user_config = yaml.safe_load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Failed to load config: {e}, using defaults")

        return default_config

    def _initialize_discovery_methods(self) -> Dict[str, bool]:
        """Initialize available discovery methods."""
        methods = {}

        for method in self.config.get("enabled_methods", []):
            if method == "kubernetes" and KUBERNETES_AVAILABLE:
                try:
                    if self.config["kubernetes"].get("in_cluster", True):
                        config.load_incluster_config()
                    else:
                        config.load_kube_config()
                    self.k8s_client = client.CoreV1Api()
                    self.k8s_apps_client = client.AppsV1Api()
                    methods[method] = True
                    self.logger.info("Kubernetes discovery enabled")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Kubernetes client: {e}")
                    methods[method] = False
            elif method == "consul" and CONSUL_AVAILABLE:
                try:
                    consul_config = self.config.get("consul", {})
                    self.consul_client = consul.Consul(
                        host=consul_config.get("host", "consul"),
                        port=consul_config.get("port", 8500),
                    )
                    methods[method] = True
                    self.logger.info("Consul discovery enabled")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Consul client: {e}")
                    methods[method] = False
            elif method == "prometheus" and REQUESTS_AVAILABLE:
                methods[method] = True
                self.logger.info("Prometheus discovery enabled")
            else:
                methods[method] = False
                self.logger.warning(f"Discovery method '{method}' not available")

        return methods

    def discover_services(self) -> List[DiscoveredService]:
        """Discover services using all enabled methods."""
        all_services = []

        for method, enabled in self.discovery_methods.items():
            if not enabled:
                continue

            try:
                if method == "kubernetes":
                    services = self._discover_kubernetes_services()
                elif method == "consul":
                    services = self._discover_consul_services()
                elif method == "prometheus":
                    services = self._discover_prometheus_services()
                else:
                    continue

                all_services.extend(services)
                self.logger.info(f"Discovered {len(services)} services via {method}")

            except Exception as e:
                self.logger.error(f"Discovery failed for {method}: {e}")

        # Deduplicate and merge services
        merged_services = self._merge_services(all_services)

        # Update service registry
        self._update_service_registry(merged_services)

        return merged_services

    def _discover_kubernetes_services(self) -> List[DiscoveredService]:
        """Discover services from Kubernetes."""
        services = []
        k8s_config = self.config.get("kubernetes", {})
        namespace = k8s_config.get("namespace", "default")

        try:
            # Discover from Services
            k8s_services = self.k8s_client.list_namespaced_service(namespace=namespace)

            for svc in k8s_services.items:
                service = self._parse_kubernetes_service(svc)
                if service:
                    services.append(service)

            # Discover from Deployments
            deployments = self.k8s_apps_client.list_namespaced_deployment(
                namespace=namespace
            )

            for deploy in deployments.items:
                service = self._parse_kubernetes_deployment(deploy)
                if service:
                    services.append(service)

        except Exception as e:
            self.logger.error(f"Kubernetes discovery error: {e}")

        return services

    def _parse_kubernetes_service(self, k8s_service) -> Optional[DiscoveredService]:
        """Parse Kubernetes Service into DiscoveredService."""
        metadata = k8s_service.metadata
        spec = k8s_service.spec

        # Skip system services
        if metadata.namespace in ["kube-system", "kube-public"]:
            return None

        # Extract service information
        name = metadata.name
        namespace = metadata.namespace
        labels = metadata.labels or {}
        annotations = metadata.annotations or {}

        # Determine service type
        service_type = self._determine_service_type(labels, annotations)

        # Get port information
        port = 80
        if spec.ports:
            port = spec.ports[0].port

        # Map annotations to service attributes
        annotation_mappings = self.config["kubernetes"].get("annotation_mappings", {})
        team = self._get_mapped_value(
            annotations, annotation_mappings, "team", "unknown"
        )
        language = self._get_mapped_value(
            annotations, annotation_mappings, "language", "unknown"
        )
        framework = self._get_mapped_value(
            annotations, annotation_mappings, "framework", "unknown"
        )

        return DiscoveredService(
            name=name,
            type=service_type,
            environment=labels.get("environment", namespace),
            namespace=namespace,
            host=f"{name}.{namespace}.svc.cluster.local",
            port=port,
            protocol="http",
            labels=labels,
            annotations=annotations,
            team=team,
            version=labels.get("version", "unknown"),
            language=language,
            framework=framework,
        )

    def _parse_kubernetes_deployment(self, deployment) -> Optional[DiscoveredService]:
        """Parse Kubernetes Deployment into DiscoveredService."""
        metadata = deployment.metadata
        spec = deployment.spec

        if metadata.namespace in ["kube-system", "kube-public"]:
            return None

        name = metadata.name
        namespace = metadata.namespace
        labels = metadata.labels or {}
        annotations = metadata.annotations or {}

        service_type = self._determine_service_type(labels, annotations)

        # Check if this deployment has an associated service
        try:
            services = self.k8s_client.list_namespaced_service(namespace=namespace)
            for svc in services.items:
                if svc.spec.selector and all(
                    labels.get(k) == v for k, v in svc.spec.selector.items()
                ):
                    # Service exists, don't duplicate
                    return None
        except:
            pass

        annotation_mappings = self.config["kubernetes"].get("annotation_mappings", {})
        team = self._get_mapped_value(
            annotations, annotation_mappings, "team", "unknown"
        )
        language = self._get_mapped_value(
            annotations, annotation_mappings, "language", "unknown"
        )
        framework = self._get_mapped_value(
            annotations, annotation_mappings, "framework", "unknown"
        )

        return DiscoveredService(
            name=name,
            type=service_type,
            environment=labels.get("environment", namespace),
            namespace=namespace,
            host=f"{name}.{namespace}.svc.cluster.local",
            port=8080,  # Default assumption
            protocol="http",
            labels=labels,
            annotations=annotations,
            team=team,
            version=labels.get("version", "unknown"),
            language=language,
            framework=framework,
        )

    def _discover_consul_services(self) -> List[DiscoveredService]:
        """Discover services from Consul."""
        services = []

        try:
            consul_services = self.consul_client.catalog.services()[1]

            for service_name, tags in consul_services.items():
                service_details = self.consul_client.catalog.service(service_name)[1]

                for service in service_details:
                    discovered_service = self._parse_consul_service(service, tags)
                    if discovered_service:
                        services.append(discovered_service)

        except Exception as e:
            self.logger.error(f"Consul discovery error: {e}")

        return services

    def _parse_consul_service(
        self, consul_service: Dict, tags: List[str]
    ) -> Optional[DiscoveredService]:
        """Parse Consul service into DiscoveredService."""
        name = consul_service.get("ServiceName", "unknown")
        host = consul_service.get("ServiceAddress", consul_service.get("Address", ""))
        port = consul_service.get("ServicePort", 80)

        # Parse tags for metadata
        labels = {}
        team = "unknown"
        environment = "unknown"
        language = "unknown"
        framework = "unknown"

        for tag in tags:
            if "=" in tag:
                key, value = tag.split("=", 1)
                labels[key] = value

                if key == "team":
                    team = value
                elif key == "environment":
                    environment = value
                elif key == "language":
                    language = value
                elif key == "framework":
                    framework = value

        service_type = self._determine_service_type(labels, {})

        return DiscoveredService(
            name=name,
            type=service_type,
            environment=environment,
            host=host,
            port=port,
            protocol="http",
            labels=labels,
            team=team,
            language=language,
            framework=framework,
        )

    def _discover_prometheus_services(self) -> List[DiscoveredService]:
        """Discover services from Prometheus targets."""
        services = []
        prom_config = self.config.get("prometheus", {})

        try:
            url = f"{prom_config.get('url', 'http://prometheus:9090')}/api/v1/targets"
            timeout = prom_config.get("query_timeout", 30)

            response = requests.get(url, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "success":
                for target in data.get("data", {}).get("activeTargets", []):
                    service = self._parse_prometheus_target(target)
                    if service:
                        services.append(service)

        except Exception as e:
            self.logger.error(f"Prometheus discovery error: {e}")

        return services

    def _parse_prometheus_target(self, target: Dict) -> Optional[DiscoveredService]:
        """Parse Prometheus target into DiscoveredService."""
        labels = target.get("labels", {})
        discovered_labels = target.get("discoveredLabels", {})

        job = labels.get("job", "unknown")
        instance = labels.get("instance", "")

        if not instance:
            return None

        # Parse host and port from instance
        if ":" in instance:
            host, port_str = instance.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 80
        else:
            host = instance
            port = 80

        # Determine service type from job name and labels
        service_type = self._determine_service_type(labels, {})

        return DiscoveredService(
            name=job,
            type=service_type,
            environment=labels.get("environment", "unknown"),
            namespace=labels.get("namespace", "default"),
            host=host,
            port=port,
            protocol="http",
            labels=labels,
            team=labels.get("team", "unknown"),
            version=labels.get("version", "unknown"),
            language=labels.get("language", "unknown"),
            framework=labels.get("framework", "unknown"),
            monitoring_enabled=True,
        )

    def _determine_service_type(
        self, labels: Dict[str, str], annotations: Dict[str, str]
    ) -> ServiceType:
        """Determine service type from labels and annotations."""
        # Check explicit type label
        if "type" in labels:
            type_str = labels["type"].lower()
            if type_str in ["web", "web-application"]:
                return ServiceType.WEB_APPLICATION
            elif type_str in ["api", "api-service"]:
                return ServiceType.API_SERVICE
            elif type_str in ["worker", "worker-service"]:
                return ServiceType.WORKER_SERVICE
            elif type_str in ["database", "db"]:
                return ServiceType.DATABASE
            elif type_str in ["cache", "redis", "memcached"]:
                return ServiceType.CACHE
            elif type_str in ["queue", "message-queue", "mq"]:
                return ServiceType.MESSAGE_QUEUE
            elif type_str in ["lb", "load-balancer"]:
                return ServiceType.LOAD_BALANCER

        # Infer from common patterns
        app_name = labels.get("app", labels.get("name", "")).lower()

        if any(word in app_name for word in ["api", "backend", "service"]):
            return ServiceType.API_SERVICE
        elif any(word in app_name for word in ["web", "frontend", "ui"]):
            return ServiceType.WEB_APPLICATION
        elif any(word in app_name for word in ["worker", "job", "processor"]):
            return ServiceType.WORKER_SERVICE
        elif any(word in app_name for word in ["db", "database", "postgres", "mysql"]):
            return ServiceType.DATABASE
        elif any(word in app_name for word in ["redis", "cache", "memcached"]):
            return ServiceType.CACHE
        elif any(word in app_name for word in ["queue", "mq", "rabbitmq", "kafka"]):
            return ServiceType.MESSAGE_QUEUE
        elif any(word in app_name for word in ["nginx", "traefik", "envoy", "lb"]):
            return ServiceType.LOAD_BALANCER

        return ServiceType.UNKNOWN

    def _get_mapped_value(
        self,
        source: Dict[str, str],
        mappings: Dict[str, str],
        target_key: str,
        default: str,
    ) -> str:
        """Get mapped value from source using annotation mappings."""
        for annotation_key, mapped_key in mappings.items():
            if mapped_key == target_key and annotation_key in source:
                return source[annotation_key]
        return default

    def _merge_services(
        self, services: List[DiscoveredService]
    ) -> List[DiscoveredService]:
        """Merge and deduplicate discovered services."""
        service_map = {}

        for service in services:
            # Create unique key for service
            key = f"{service.name}-{service.namespace}-{service.environment}"

            if key in service_map:
                # Merge information from multiple sources
                existing = service_map[key]

                # Update with most recent information
                if service.last_seen > existing.last_seen:
                    existing.last_seen = service.last_seen

                # Merge labels and annotations
                existing.labels.update(service.labels)
                existing.annotations.update(service.annotations)

                # Update missing information
                if existing.team == "unknown" and service.team != "unknown":
                    existing.team = service.team
                if existing.language == "unknown" and service.language != "unknown":
                    existing.language = service.language
                if existing.framework == "unknown" and service.framework != "unknown":
                    existing.framework = service.framework
                if existing.version == "unknown" and service.version != "unknown":
                    existing.version = service.version

                # Enable monitoring if any source has it enabled
                if service.monitoring_enabled:
                    existing.monitoring_enabled = True
            else:
                service_map[key] = service

        return list(service_map.values())

    def _update_service_registry(self, services: List[DiscoveredService]):
        """Update the service registry with discovered services."""
        registry_file = self.config["output"].get(
            "service_registry", "/var/lib/monitoring/services.json"
        )

        try:
            # Load existing registry
            existing_registry = {}
            if os.path.exists(registry_file):
                with open(registry_file, "r") as f:
                    existing_registry = json.load(f)

            # Update with new services
            for service in services:
                key = f"{service.name}-{service.namespace}-{service.environment}"
                existing_registry[key] = service.to_dict()

            # Remove stale services
            cutoff_time = datetime.now() - timedelta(
                seconds=self.config.get("service_ttl", 300)
            )

            for key in list(existing_registry.keys()):
                last_seen = datetime.fromisoformat(existing_registry[key]["last_seen"])
                if last_seen < cutoff_time:
                    del existing_registry[key]
                    self.logger.info(f"Removed stale service: {key}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(registry_file), exist_ok=True)

            # Write updated registry
            with open(registry_file, "w") as f:
                json.dump(existing_registry, f, indent=2)

            self.logger.info(
                f"Updated service registry with {len(existing_registry)} services"
            )

        except Exception as e:
            self.logger.error(f"Failed to update service registry: {e}")

    def generate_prometheus_targets(
        self, services: List[DiscoveredService]
    ) -> Dict[str, Any]:
        """Generate Prometheus file_sd targets configuration."""
        targets_by_job = {}

        for service in services:
            if not service.monitoring_enabled:
                continue

            job_name = f"{service.name}-{service.environment}"
            target = f"{service.host}:{service.port}"

            if job_name not in targets_by_job:
                targets_by_job[job_name] = {
                    "targets": [],
                    "labels": {
                        "job": job_name,
                        "service": service.name,
                        "environment": service.environment,
                        "namespace": service.namespace,
                        "team": service.team,
                        "type": service.type.value,
                        "language": service.language,
                        "framework": service.framework,
                        "version": service.version,
                    },
                }

            targets_by_job[job_name]["targets"].append(target)

        return list(targets_by_job.values())

    def run_continuous_discovery(self):
        """Run continuous service discovery."""
        interval = self.config.get("discovery_interval", 60)

        self.logger.info(f"Starting continuous discovery with {interval}s interval")

        while True:
            try:
                services = self.discover_services()
                self.logger.info(
                    f"Discovery cycle completed, found {len(services)} services"
                )

                # Generate and write Prometheus targets
                targets = self.generate_prometheus_targets(services)
                self._write_prometheus_targets(targets)

                time.sleep(interval)

            except KeyboardInterrupt:
                self.logger.info("Discovery stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Discovery cycle failed: {e}")
                time.sleep(min(interval, 30))  # Shorter interval on error

    def _write_prometheus_targets(self, targets: List[Dict[str, Any]]):
        """Write Prometheus file service discovery targets."""
        output_file = self.config["output"].get(
            "prometheus_file", "/etc/prometheus/targets/services.json"
        )

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with open(output_file, "w") as f:
                json.dump(targets, f, indent=2)

            self.logger.info(f"Updated Prometheus targets: {output_file}")

        except Exception as e:
            self.logger.error(f"Failed to write Prometheus targets: {e}")


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Universal Platform Service Discovery")
    parser.add_argument(
        "--config", default="discovery-config.yaml", help="Configuration file path"
    )
    parser.add_argument(
        "--continuous", action="store_true", help="Run continuous discovery"
    )
    parser.add_argument("--output-targets", help="Output Prometheus targets to file")
    parser.add_argument("--output-registry", help="Output service registry to file")

    args = parser.parse_args()

    # Initialize discovery
    discovery = ServiceDiscovery(args.config)

    if args.continuous:
        discovery.run_continuous_discovery()
    else:
        # Single discovery run
        services = discovery.discover_services()

        print(f"Discovered {len(services)} services:")
        for service in services:
            print(
                f"  - {service.name} ({service.type.value}) at {service.host}:{service.port}"
            )

        # Output targets if requested
        if args.output_targets:
            targets = discovery.generate_prometheus_targets(services)
            with open(args.output_targets, "w") as f:
                json.dump(targets, f, indent=2)
            print(f"Prometheus targets written to {args.output_targets}")

        # Output registry if requested
        if args.output_registry:
            registry = {
                f"{s.name}-{s.namespace}-{s.environment}": s.to_dict() for s in services
            }
            with open(args.output_registry, "w") as f:
                json.dump(registry, f, indent=2)
            print(f"Service registry written to {args.output_registry}")
