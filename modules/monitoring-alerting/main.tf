/**
 * Monitoring and Alerting Module
 *
 * Comprehensive monitoring for VM and container infrastructure
 * Implements observability for agent-cage and claude-talk migration
 */

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

locals {
  # Standard labels following Genesis patterns
  default_labels = {
    managed_by  = "terraform"
    module      = "monitoring-alerting"
    environment = var.environment
    component   = "observability"
    purpose     = "infrastructure-monitoring"
  }

  merged_labels = merge(local.default_labels, var.labels)

  # Monitoring scopes for different environments
  monitoring_scope = var.environment == "prod" ? "comprehensive" : "standard"

  # Alert notification channels by type
  notification_channels = {
    for channel in var.notification_channels : "${channel.type}-${channel.name}" => channel
  }
}

# Cloud Monitoring Workspace
resource "google_monitoring_workspace" "genesis_workspace" {
  count = var.create_monitoring_workspace ? 1 : 0

  project = var.project_id

  lifecycle {
    prevent_destroy = true
  }
}

# Notification Channels
resource "google_monitoring_notification_channel" "notification_channels" {
  for_each = local.notification_channels

  project      = var.project_id
  display_name = each.value.display_name
  type         = each.value.type
  description  = each.value.description

  labels = each.value.labels

  user_labels = merge(
    local.merged_labels,
    {
      "channel-type" = each.value.type
      "environment"  = var.environment
    }
  )

  enabled = lookup(each.value, "enabled", true)
}

# Uptime Checks for Agent Services
resource "google_monitoring_uptime_check_config" "agent_uptime_checks" {
  for_each = var.agent_uptime_checks

  project      = var.project_id
  display_name = "Agent ${each.key} Uptime Check"
  timeout      = "${each.value.timeout_seconds}s"
  period       = "${each.value.period_seconds}s"

  http_check {
    path           = each.value.path
    port           = each.value.port
    use_ssl        = lookup(each.value, "use_ssl", false)
    validate_ssl   = lookup(each.value, "validate_ssl", false)
    request_method = lookup(each.value, "method", "GET")

    dynamic "accepted_response_status_codes" {
      for_each = lookup(each.value, "accepted_status_codes", [{ status_value = 200 }])
      content {
        status_value = accepted_response_status_codes.value.status_value
      }
    }
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      host       = each.value.host
      project_id = var.project_id
    }
  }

  content_matchers {
    content = lookup(each.value, "content_matcher", "")
    matcher = lookup(each.value, "matcher_type", "CONTAINS_STRING")
  }

  checker_type = "STATIC_IP_CHECKERS"

  selected_regions = var.uptime_check_regions
}

# VM Instance Monitoring Alerts
resource "google_monitoring_alert_policy" "vm_instance_alerts" {
  for_each = var.vm_alert_policies

  project      = var.project_id
  display_name = "VM ${each.key}"
  combiner     = each.value.combiner
  enabled      = lookup(each.value, "enabled", true)

  conditions {
    display_name = each.value.condition_display_name

    condition_threshold {
      filter          = each.value.filter
      duration        = each.value.duration
      comparison      = each.value.comparison
      threshold_value = each.value.threshold_value

      aggregations {
        alignment_period     = each.value.alignment_period
        per_series_aligner   = each.value.per_series_aligner
        cross_series_reducer = lookup(each.value, "cross_series_reducer", null)

        dynamic "group_by_fields" {
          for_each = lookup(each.value, "group_by_fields", [])
          content {
            group_by_fields = group_by_fields.value
          }
        }
      }

      dynamic "trigger" {
        for_each = lookup(each.value, "trigger", null) != null ? [each.value.trigger] : []
        content {
          count   = lookup(trigger.value, "count", null)
          percent = lookup(trigger.value, "percent", null)
        }
      }
    }
  }

  notification_channels = [
    for channel_key in each.value.notification_channels :
    google_monitoring_notification_channel.notification_channels[channel_key].id
  ]

  alert_strategy {
    auto_close = lookup(each.value, "auto_close", "1800s")
  }

  documentation {
    content   = each.value.documentation_content
    mime_type = "text/markdown"
  }

  user_labels = merge(
    local.merged_labels,
    {
      "alert-type"    = each.key
      "resource-type" = "vm-instance"
      "severity"      = lookup(each.value, "severity", "warning")
    }
  )
}

# Container and GKE Monitoring Alerts
resource "google_monitoring_alert_policy" "container_alerts" {
  for_each = var.container_alert_policies

  project      = var.project_id
  display_name = "Container ${each.key}"
  combiner     = each.value.combiner
  enabled      = lookup(each.value, "enabled", true)

  conditions {
    display_name = each.value.condition_display_name

    condition_threshold {
      filter          = each.value.filter
      duration        = each.value.duration
      comparison      = each.value.comparison
      threshold_value = each.value.threshold_value

      aggregations {
        alignment_period     = each.value.alignment_period
        per_series_aligner   = each.value.per_series_aligner
        cross_series_reducer = lookup(each.value, "cross_series_reducer", null)

        dynamic "group_by_fields" {
          for_each = lookup(each.value, "group_by_fields", [])
          content {
            group_by_fields = group_by_fields.value
          }
        }
      }
    }
  }

  notification_channels = [
    for channel_key in each.value.notification_channels :
    google_monitoring_notification_channel.notification_channels[channel_key].id
  ]

  alert_strategy {
    auto_close = lookup(each.value, "auto_close", "1800s")
  }

  documentation {
    content   = each.value.documentation_content
    mime_type = "text/markdown"
  }

  user_labels = merge(
    local.merged_labels,
    {
      "alert-type"    = each.key
      "resource-type" = "container"
      "severity"      = lookup(each.value, "severity", "warning")
    }
  )
}

# Agent-specific Custom Metrics
resource "google_monitoring_metric_descriptor" "agent_custom_metrics" {
  for_each = var.agent_custom_metrics

  project      = var.project_id
  type         = "custom.googleapis.com/genesis/agent/${each.key}"
  metric_kind  = each.value.metric_kind
  value_type   = each.value.value_type
  display_name = "Genesis Agent ${title(replace(each.key, "_", " "))}"
  description  = each.value.description

  labels {
    key         = "agent_type"
    value_type  = "STRING"
    description = "Type of Genesis agent"
  }

  labels {
    key         = "environment"
    value_type  = "STRING"
    description = "Environment (dev, staging, prod)"
  }

  labels {
    key         = "instance_id"
    value_type  = "STRING"
    description = "Agent instance identifier"
  }

  dynamic "labels" {
    for_each = lookup(each.value, "additional_labels", [])
    content {
      key         = labels.value.key
      value_type  = labels.value.value_type
      description = labels.value.description
    }
  }

  unit         = lookup(each.value, "unit", "1")
  launch_stage = "BETA"
}

# Dashboard for VM Management
resource "google_monitoring_dashboard" "vm_management_dashboard" {
  count = var.create_dashboards ? 1 : 0

  project = var.project_id
  dashboard_json = templatefile("${path.module}/dashboards/vm-management-dashboard.json", {
    project_id  = var.project_id
    environment = var.environment
    name_prefix = var.name_prefix
  })
}

# Dashboard for Container Orchestration
resource "google_monitoring_dashboard" "container_orchestration_dashboard" {
  count = var.create_dashboards ? 1 : 0

  project = var.project_id
  dashboard_json = templatefile("${path.module}/dashboards/container-orchestration-dashboard.json", {
    project_id  = var.project_id
    environment = var.environment
    name_prefix = var.name_prefix
  })
}

# SLO for Agent Availability
resource "google_monitoring_slo" "agent_availability_slo" {
  for_each = var.agent_slos

  project      = var.project_id
  service      = google_monitoring_service.genesis_services[each.value.service].service_id
  slo_id       = "${each.key}-availability"
  display_name = "Agent ${each.key} Availability SLO"

  goal                = each.value.availability_target
  rolling_period_days = each.value.rolling_period_days

  request_based_sli {
    good_total_ratio {
      total_service_filter = each.value.total_service_filter
      good_service_filter  = each.value.good_service_filter
    }
  }

  user_labels = merge(
    local.merged_labels,
    {
      "slo-type"   = "availability"
      "agent-type" = each.key
    }
  )
}

# SLO for Agent Latency
resource "google_monitoring_slo" "agent_latency_slo" {
  for_each = {
    for k, v in var.agent_slos : k => v
    if lookup(v, "latency_threshold", null) != null
  }

  project      = var.project_id
  service      = google_monitoring_service.genesis_services[each.value.service].service_id
  slo_id       = "${each.key}-latency"
  display_name = "Agent ${each.key} Latency SLO"

  goal                = each.value.latency_target
  rolling_period_days = each.value.rolling_period_days

  request_based_sli {
    distribution_cut {
      distribution_filter = each.value.latency_distribution_filter
      range {
        min = 0
        max = each.value.latency_threshold
      }
    }
  }

  user_labels = merge(
    local.merged_labels,
    {
      "slo-type"   = "latency"
      "agent-type" = each.key
    }
  )
}

# Monitoring Services
resource "google_monitoring_service" "genesis_services" {
  for_each = var.monitoring_services

  project      = var.project_id
  service_id   = each.key
  display_name = each.value.display_name

  user_labels = merge(
    local.merged_labels,
    {
      "service-type" = each.value.service_type
      "environment"  = var.environment
    }
  )
}

# Log-based Metrics for Custom Monitoring
resource "google_logging_metric" "agent_log_metrics" {
  for_each = var.agent_log_metrics

  project = var.project_id
  name    = "${var.name_prefix}-${each.key}"
  filter  = each.value.filter

  label_extractors = lookup(each.value, "label_extractors", {})

  metric_descriptor {
    metric_kind = each.value.metric_kind
    value_type  = each.value.value_type
    unit        = lookup(each.value, "unit", "1")

    dynamic "labels" {
      for_each = lookup(each.value, "labels", [])
      content {
        key         = labels.value.key
        value_type  = labels.value.value_type
        description = lookup(labels.value, "description", "")
      }
    }
  }

  dynamic "value_extractor" {
    for_each = lookup(each.value, "value_extractor", null) != null ? [each.value.value_extractor] : []
    content {
      value_extractor = value_extractor.value
    }
  }

  dynamic "bucket_options" {
    for_each = lookup(each.value, "bucket_options", null) != null ? [each.value.bucket_options] : []
    content {
      linear_buckets {
        num_finite_buckets = bucket_options.value.num_finite_buckets
        width              = bucket_options.value.width
        offset             = bucket_options.value.offset
      }
    }
  }
}

# Kubernetes Monitoring via Prometheus
resource "kubernetes_config_map" "prometheus_config" {
  count = var.enable_prometheus_monitoring ? 1 : 0

  metadata {
    name      = "prometheus-config"
    namespace = var.monitoring_namespace

    labels = merge(
      local.merged_labels,
      {
        "component" = "prometheus"
      }
    )
  }

  data = {
    "prometheus.yml" = templatefile("${path.module}/configs/prometheus.yml", {
      project_id  = var.project_id
      environment = var.environment
      agent_types = var.agent_types
    })
  }
}

# Grafana ConfigMap for Dashboards
resource "kubernetes_config_map" "grafana_dashboards" {
  count = var.enable_grafana_dashboards ? 1 : 0

  metadata {
    name      = "grafana-dashboards"
    namespace = var.monitoring_namespace

    labels = merge(
      local.merged_labels,
      {
        "component"         = "grafana"
        "grafana_dashboard" = "1"
      }
    )
  }

  data = {
    "genesis-overview.json" = file("${path.module}/dashboards/genesis-overview.json")
    "vm-management.json"    = file("${path.module}/dashboards/vm-management.json")
    "containers.json"       = file("${path.module}/dashboards/containers.json")
    "agents.json"           = file("${path.module}/dashboards/agents.json")
  }
}

# ServiceMonitor for Prometheus Operator
resource "kubernetes_manifest" "agent_service_monitors" {
  for_each = var.enable_prometheus_monitoring ? toset(var.agent_types) : toset([])

  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"

    metadata = {
      name      = "${each.value}-monitor"
      namespace = var.monitoring_namespace
      labels = merge(
        local.merged_labels,
        {
          "component"  = "service-monitor"
          "agent-type" = each.value
        }
      )
    }

    spec = {
      selector = {
        matchLabels = {
          "app" = each.value
        }
      }

      endpoints = [
        {
          port     = "metrics"
          path     = "/metrics"
          interval = var.prometheus_scrape_interval
        }
      ]
    }
  }
}

# PrometheusRule for Agent Alerts
resource "kubernetes_manifest" "agent_prometheus_rules" {
  count = var.enable_prometheus_monitoring ? 1 : 0

  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "PrometheusRule"

    metadata = {
      name      = "genesis-agent-rules"
      namespace = var.monitoring_namespace
      labels = merge(
        local.merged_labels,
        {
          "component" = "prometheus-rules"
        }
      )
    }

    spec = {
      groups = [
        {
          name = "genesis.agents"
          rules = [
            {
              alert = "AgentDown"
              expr  = "up{job=~\".*-agent\"} == 0"
              for   = "5m"
              labels = {
                severity = "critical"
              }
              annotations = {
                summary     = "Agent {{ $labels.instance }} is down"
                description = "Genesis agent {{ $labels.job }} on {{ $labels.instance }} has been down for more than 5 minutes."
              }
            },
            {
              alert = "AgentHighCPU"
              expr  = "rate(process_cpu_seconds_total{job=~\".*-agent\"}[5m]) * 100 > 80"
              for   = "10m"
              labels = {
                severity = "warning"
              }
              annotations = {
                summary     = "High CPU usage on {{ $labels.instance }}"
                description = "Genesis agent {{ $labels.job }} on {{ $labels.instance }} has high CPU usage ({{ $value }}%) for more than 10 minutes."
              }
            },
            {
              alert = "AgentHighMemory"
              expr  = "process_resident_memory_bytes{job=~\".*-agent\"} / 1024 / 1024 > 1024"
              for   = "15m"
              labels = {
                severity = "warning"
              }
              annotations = {
                summary     = "High memory usage on {{ $labels.instance }}"
                description = "Genesis agent {{ $labels.job }} on {{ $labels.instance }} is using more than 1GB of memory for more than 15 minutes."
              }
            }
          ]
        },
        {
          name = "genesis.infrastructure"
          rules = [
            {
              alert = "VMInstanceDown"
              expr  = "up{job=\"vm-instances\"} == 0"
              for   = "5m"
              labels = {
                severity = "critical"
              }
              annotations = {
                summary     = "VM Instance {{ $labels.instance }} is down"
                description = "VM instance {{ $labels.instance }} has been down for more than 5 minutes."
              }
            },
            {
              alert = "ContainerRestartingFrequently"
              expr  = "rate(kube_pod_container_status_restarts_total[15m]) * 60 * 15 > 0"
              for   = "5m"
              labels = {
                severity = "warning"
              }
              annotations = {
                summary     = "Container restarting frequently"
                description = "Container {{ $labels.container }} in pod {{ $labels.pod }} is restarting frequently."
              }
            }
          ]
        }
      ]
    }
  }
}

# Alertmanager Configuration
resource "kubernetes_secret" "alertmanager_config" {
  count = var.enable_prometheus_monitoring ? 1 : 0

  metadata {
    name      = "alertmanager-config"
    namespace = var.monitoring_namespace

    labels = merge(
      local.merged_labels,
      {
        "component" = "alertmanager"
      }
    )
  }

  data = {
    "alertmanager.yml" = base64encode(templatefile("${path.module}/configs/alertmanager.yml", {
      slack_api_url   = var.slack_webhook_url
      email_smarthost = var.email_smarthost
      email_from      = var.email_from
      email_to        = var.email_to
    }))
  }
}

# Network Policy for Monitoring
resource "kubernetes_network_policy" "monitoring_network_policy" {
  count = var.enable_monitoring_network_policy ? 1 : 0

  metadata {
    name      = "monitoring-network-policy"
    namespace = var.monitoring_namespace

    labels = local.merged_labels
  }

  spec {
    pod_selector {
      match_labels = {
        "component" = "monitoring"
      }
    }

    policy_types = ["Ingress", "Egress"]

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "name" = var.monitoring_namespace
          }
        }
      }

      ports {
        port     = 9090 # Prometheus
        protocol = "TCP"
      }

      ports {
        port     = 3000 # Grafana
        protocol = "TCP"
      }
    }

    egress {
      # Allow egress to all for metrics collection
      to {}

      ports {
        port     = 8080 # Agent metrics
        protocol = "TCP"
      }

      ports {
        port     = 9090 # Prometheus metrics
        protocol = "TCP"
      }
    }
  }
}
