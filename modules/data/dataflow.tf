/**
 * Dataflow and data processing resources
 */

# Dataflow jobs
resource "google_dataflow_flex_template_job" "dataflow_jobs" {
  for_each = local.dataflow_jobs
  
  name                = each.value.full_name
  project             = var.project_id
  region              = lookup(each.value, "region", var.default_region)
  
  container_spec_gcs_path = each.value.template_gcs_path
  
  # Parameters
  parameters = lookup(each.value, "parameters", {})
  
  # Additional experiment flags
  additional_experiments = lookup(each.value, "additional_experiments", [])
  
  # Autoscaling algorithm
  autoscaling_algorithm = lookup(each.value, "autoscaling_algorithm", null)
  
  # Enable streaming engine
  enable_streaming_engine = lookup(each.value, "enable_streaming_engine", false)
  
  # IP configuration
  ip_configuration = lookup(each.value, "ip_configuration", null)
  
  # KMS key
  kms_key_name = lookup(each.value, "kms_key_name", null)
  
  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      job_type = "dataflow"
    }
  )
  
  # Launcher machine type
  launcher_machine_type = lookup(each.value, "launcher_machine_type", null)
  
  # Machine type
  machine_type = lookup(each.value, "machine_type", "n1-standard-1")
  
  # Max workers
  max_workers = lookup(each.value, "max_workers", 10)
  
  # Network configuration
  network    = lookup(each.value, "network", var.network_id)
  subnetwork = lookup(each.value, "subnetwork", var.subnet_id)
  
  # Number of workers
  num_workers = lookup(each.value, "num_workers", 1)
  
  # SDK container image
  sdk_container_image = lookup(each.value, "sdk_container_image", null)
  
  # Service account email
  service_account_email = lookup(each.value, "service_account_email", null)
  
  # Skip wait on job termination
  skip_wait_on_job_termination = lookup(each.value, "skip_wait_on_job_termination", false)
  
  # Staging location
  staging_location = lookup(each.value, "staging_location", null)
  
  # Temp location
  temp_location = lookup(each.value, "temp_location", null)
  
  # Transform name mappings
  transform_name_mappings = lookup(each.value, "transform_name_mappings", {})
  
  # Lifecycle
  lifecycle {
    ignore_changes = [
      # Ignore changes to these fields as they might be updated by the service
      additional_experiments,
      transform_name_mappings,
    ]
  }
}

# BigQuery Data Transfer configs
resource "google_bigquery_data_transfer_config" "transfer_configs" {
  for_each = {
    for transfer in var.bigquery_transfers : transfer.name => transfer
  }
  
  project                = var.project_id
  location              = lookup(each.value, "location", var.default_region)
  display_name          = each.value.display_name
  data_source_id        = each.value.data_source_id
  destination_dataset_id = each.value.destination_dataset_id
  
  # Parameters (varies by data source)
  params = each.value.params
  
  # Schedule
  schedule = lookup(each.value, "schedule", null)
  
  # Data refresh window days
  data_refresh_window_days = lookup(each.value, "data_refresh_window_days", 0)
  
  # Disabled
  disabled = lookup(each.value, "disabled", false)
  
  # Service account name
  service_account_name = lookup(each.value, "service_account_name", null)
  
  # Notification pub/sub topic
  notification_pubsub_topic = lookup(each.value, "notification_pubsub_topic", null)
  
  # Email preferences
  dynamic "email_preferences" {
    for_each = lookup(each.value, "email_preferences", null) != null ? [1] : []
    content {
      enable_failure_email = lookup(each.value.email_preferences, "enable_failure_email", false)
    }
  }
  
  # Schedule options
  dynamic "schedule_options" {
    for_each = lookup(each.value, "schedule_options", null) != null ? [1] : []
    content {
      disable_auto_scheduling = lookup(each.value.schedule_options, "disable_auto_scheduling", false)
      start_time             = lookup(each.value.schedule_options, "start_time", null)
      end_time               = lookup(each.value.schedule_options, "end_time", null)
    }
  }
  
  # Sensitive params (for API keys, secrets, etc.)
  sensitive_params = lookup(each.value, "sensitive_params", {})
}

# Pub/Sub topics for data processing
resource "google_pubsub_topic" "data_topics" {
  for_each = {
    for topic in var.pubsub_topics : topic.name => topic
  }
  
  name    = "${var.name_prefix}-${each.value.name}"
  project = var.project_id
  
  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      topic_type = "data-processing"
    }
  )
  
  # KMS key
  kms_key_name = lookup(each.value, "kms_key_name", null)
  
  # Message retention duration
  message_retention_duration = lookup(each.value, "message_retention_duration", "604800s")  # 7 days
  
  # Message storage policy
  dynamic "message_storage_policy" {
    for_each = lookup(each.value, "message_storage_policy", null) != null ? [1] : []
    content {
      allowed_persistence_regions = each.value.message_storage_policy.allowed_persistence_regions
    }
  }
  
  # Schema settings
  dynamic "schema_settings" {
    for_each = lookup(each.value, "schema_settings", null) != null ? [1] : []
    content {
      schema   = each.value.schema_settings.schema
      encoding = lookup(each.value.schema_settings, "encoding", "JSON")
    }
  }
  
  # Ingestion data source settings
  dynamic "ingestion_data_source_settings" {
    for_each = lookup(each.value, "ingestion_data_source_settings", null) != null ? [1] : []
    content {
      dynamic "aws_kinesis" {
        for_each = lookup(each.value.ingestion_data_source_settings, "aws_kinesis", null) != null ? [1] : []
        content {
          stream_name            = each.value.ingestion_data_source_settings.aws_kinesis.stream_name
          consumer_arn          = each.value.ingestion_data_source_settings.aws_kinesis.consumer_arn
          aws_role_arn          = each.value.ingestion_data_source_settings.aws_kinesis.aws_role_arn
          gcp_service_account   = each.value.ingestion_data_source_settings.aws_kinesis.gcp_service_account
        }
      }
    }
  }
}

# Pub/Sub subscriptions
resource "google_pubsub_subscription" "data_subscriptions" {
  for_each = {
    for sub in flatten([
      for topic_name, topic in var.pubsub_topics : [
        for subscription in lookup(topic, "subscriptions", []) : {
          key         = "${topic_name}-${subscription.name}"
          topic_name  = topic_name
          subscription = subscription
        }
      ]
    ]) : sub.key => sub
  }
  
  name    = "${var.name_prefix}-${each.value.subscription.name}"
  project = var.project_id
  topic   = google_pubsub_topic.data_topics[each.value.topic_name].name
  
  # Acknowledgment deadline
  ack_deadline_seconds = lookup(each.value.subscription, "ack_deadline_seconds", 20)
  
  # Message retention duration
  message_retention_duration = lookup(each.value.subscription, "message_retention_duration", "604800s")  # 7 days
  
  # Retain acked messages
  retain_acked_messages = lookup(each.value.subscription, "retain_acked_messages", false)
  
  # Enable message ordering
  enable_message_ordering = lookup(each.value.subscription, "enable_message_ordering", false)
  
  # Filter
  filter = lookup(each.value.subscription, "filter", null)
  
  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value.subscription, "labels", {}),
    {
      subscription_type = "data-processing"
    }
  )
  
  # Expiration policy
  dynamic "expiration_policy" {
    for_each = lookup(each.value.subscription, "expiration_policy", null) != null ? [1] : []
    content {
      ttl = each.value.subscription.expiration_policy.ttl
    }
  }
  
  # Dead letter policy
  dynamic "dead_letter_policy" {
    for_each = lookup(each.value.subscription, "dead_letter_policy", null) != null ? [1] : []
    content {
      dead_letter_topic     = each.value.subscription.dead_letter_policy.dead_letter_topic
      max_delivery_attempts = lookup(each.value.subscription.dead_letter_policy, "max_delivery_attempts", 5)
    }
  }
  
  # Retry policy
  dynamic "retry_policy" {
    for_each = lookup(each.value.subscription, "retry_policy", null) != null ? [1] : []
    content {
      minimum_backoff = lookup(each.value.subscription.retry_policy, "minimum_backoff", "10s")
      maximum_backoff = lookup(each.value.subscription.retry_policy, "maximum_backoff", "600s")
    }
  }
  
  # Push configuration
  dynamic "push_config" {
    for_each = lookup(each.value.subscription, "push_config", null) != null ? [1] : []
    content {
      push_endpoint = each.value.subscription.push_config.push_endpoint
      attributes    = lookup(each.value.subscription.push_config, "attributes", {})
      
      dynamic "oidc_token" {
        for_each = lookup(each.value.subscription.push_config, "oidc_token", null) != null ? [1] : []
        content {
          service_account_email = each.value.subscription.push_config.oidc_token.service_account_email
          audience             = lookup(each.value.subscription.push_config.oidc_token, "audience", null)
        }
      }
      
      dynamic "no_wrapper" {
        for_each = lookup(each.value.subscription.push_config, "no_wrapper", null) != null ? [1] : []
        content {
          write_metadata = each.value.subscription.push_config.no_wrapper.write_metadata
        }
      }
    }
  }
  
  # BigQuery configuration
  dynamic "bigquery_config" {
    for_each = lookup(each.value.subscription, "bigquery_config", null) != null ? [1] : []
    content {
      table               = each.value.subscription.bigquery_config.table
      use_topic_schema    = lookup(each.value.subscription.bigquery_config, "use_topic_schema", false)
      write_metadata      = lookup(each.value.subscription.bigquery_config, "write_metadata", false)
      drop_unknown_fields = lookup(each.value.subscription.bigquery_config, "drop_unknown_fields", false)
      use_table_schema    = lookup(each.value.subscription.bigquery_config, "use_table_schema", false)
    }
  }
  
  # Cloud Storage configuration
  dynamic "cloud_storage_config" {
    for_each = lookup(each.value.subscription, "cloud_storage_config", null) != null ? [1] : []
    content {
      bucket                   = each.value.subscription.cloud_storage_config.bucket
      filename_prefix          = lookup(each.value.subscription.cloud_storage_config, "filename_prefix", null)
      filename_suffix          = lookup(each.value.subscription.cloud_storage_config, "filename_suffix", null)
      max_duration            = lookup(each.value.subscription.cloud_storage_config, "max_duration", "300s")
      max_bytes               = lookup(each.value.subscription.cloud_storage_config, "max_bytes", 1000000)
      
      dynamic "avro_config" {
        for_each = lookup(each.value.subscription.cloud_storage_config, "avro_config", null) != null ? [1] : []
        content {
          write_metadata = lookup(each.value.subscription.cloud_storage_config.avro_config, "write_metadata", false)
        }
      }
    }
  }
}

# Data Catalog resources
resource "google_data_catalog_entry_group" "entry_groups" {
  for_each = {
    for group in var.data_catalog_entry_groups : group.name => group
  }
  
  entry_group_id = "${var.name_prefix}-${each.value.name}"
  project        = var.project_id
  region         = lookup(each.value, "region", var.default_region)
  
  display_name = lookup(each.value, "display_name", each.value.name)
  description  = lookup(each.value, "description", "Entry group ${each.value.name}")
}

# Cloud Scheduler jobs for data processing
resource "google_cloud_scheduler_job" "data_jobs" {
  for_each = {
    for job in var.scheduler_jobs : job.name => job
  }
  
  name     = "${var.name_prefix}-${each.value.name}"
  project  = var.project_id
  region   = lookup(each.value, "region", var.default_region)
  
  description = lookup(each.value, "description", "Scheduled data processing job")
  schedule    = each.value.schedule
  time_zone   = lookup(each.value, "time_zone", "UTC")
  
  # Retry configuration
  dynamic "retry_config" {
    for_each = lookup(each.value, "retry_config", null) != null ? [1] : []
    content {
      retry_count          = lookup(each.value.retry_config, "retry_count", 3)
      max_retry_duration   = lookup(each.value.retry_config, "max_retry_duration", "3600s")
      min_backoff_duration = lookup(each.value.retry_config, "min_backoff_duration", "5s")
      max_backoff_duration = lookup(each.value.retry_config, "max_backoff_duration", "3600s")
      max_doublings        = lookup(each.value.retry_config, "max_doublings", 16)
    }
  }
  
  # HTTP target
  dynamic "http_target" {
    for_each = lookup(each.value, "http_target", null) != null ? [1] : []
    content {
      uri         = each.value.http_target.uri
      http_method = lookup(each.value.http_target, "http_method", "GET")
      body        = lookup(each.value.http_target, "body", null)
      headers     = lookup(each.value.http_target, "headers", {})
      
      dynamic "oauth_token" {
        for_each = lookup(each.value.http_target, "oauth_token", null) != null ? [1] : []
        content {
          service_account_email = each.value.http_target.oauth_token.service_account_email
          scope                = lookup(each.value.http_target.oauth_token, "scope", null)
        }
      }
      
      dynamic "oidc_token" {
        for_each = lookup(each.value.http_target, "oidc_token", null) != null ? [1] : []
        content {
          service_account_email = each.value.http_target.oidc_token.service_account_email
          audience             = lookup(each.value.http_target.oidc_token, "audience", null)
        }
      }
    }
  }
  
  # Pub/Sub target
  dynamic "pubsub_target" {
    for_each = lookup(each.value, "pubsub_target", null) != null ? [1] : []
    content {
      topic_name = each.value.pubsub_target.topic_name
      data       = lookup(each.value.pubsub_target, "data", null)
      attributes = lookup(each.value.pubsub_target, "attributes", {})
    }
  }
  
  # App Engine target
  dynamic "app_engine_http_target" {
    for_each = lookup(each.value, "app_engine_target", null) != null ? [1] : []
    content {
      http_method  = lookup(each.value.app_engine_target, "http_method", "GET")
      relative_uri = lookup(each.value.app_engine_target, "relative_uri", "/")
      body         = lookup(each.value.app_engine_target, "body", null)
      headers      = lookup(each.value.app_engine_target, "headers", {})
      
      dynamic "app_engine_routing" {
        for_each = lookup(each.value.app_engine_target, "routing", null) != null ? [1] : []
        content {
          service  = lookup(each.value.app_engine_target.routing, "service", null)
          version  = lookup(each.value.app_engine_target.routing, "version", null)
          instance = lookup(each.value.app_engine_target.routing, "instance", null)
        }
      }
    }
  }
}