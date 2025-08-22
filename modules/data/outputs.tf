/**
 * Data Module - Outputs
 * 
 * Export data infrastructure information for use by other modules
 */

# Cloud SQL Outputs
output "sql_instances" {
  description = "Map of Cloud SQL instance details"
  value = {
    for instance_name, instance in google_sql_database_instance.instances :
    instance_name => {
      name                = instance.name
      connection_name     = instance.connection_name
      first_ip_address    = instance.first_ip_address
      ip_address          = instance.ip_address
      private_ip_address  = instance.private_ip_address
      public_ip_address   = instance.public_ip_address
      server_ca_cert      = instance.server_ca_cert
      service_account_email_address = instance.service_account_email_address
      self_link           = instance.self_link
      database_version    = instance.database_version
      settings            = {
        tier                = instance.settings[0].tier
        availability_type   = instance.settings[0].availability_type
        disk_size          = instance.settings[0].disk_size
        disk_type          = instance.settings[0].disk_type
        version            = instance.settings[0].version
        user_labels        = instance.settings[0].user_labels
      }
    }
  }
}

output "sql_databases" {
  description = "Map of Cloud SQL databases created"
  value = {
    for db_key, db in google_sql_database.databases :
    db_key => {
      name     = db.name
      instance = db.instance
      charset  = db.charset
      collation = db.collation
      self_link = db.self_link
    }
  }
}

output "sql_users" {
  description = "Map of Cloud SQL users created"
  value = {
    for user_key, user in google_sql_user.users :
    user_key => {
      name     = user.name
      instance = user.instance
      host     = user.host
      type     = user.type
    }
  }
  sensitive = true
}

# BigQuery Outputs
output "bigquery_datasets" {
  description = "Map of BigQuery dataset details"
  value = {
    for dataset_name, dataset in google_bigquery_dataset.datasets :
    dataset_name => {
      dataset_id       = dataset.dataset_id
      friendly_name    = dataset.friendly_name
      description      = dataset.description
      location         = dataset.location
      labels          = dataset.labels
      self_link       = dataset.self_link
      creation_time   = dataset.creation_time
      last_modified_time = dataset.last_modified_time
      etag            = dataset.etag
    }
  }
}

output "bigquery_tables" {
  description = "Map of BigQuery tables created"
  value = {
    for table_key, table in google_bigquery_table.tables :
    table_key => {
      table_id         = table.table_id
      dataset_id       = table.dataset_id
      description      = table.description
      schema          = table.schema
      clustering      = table.clustering
      labels          = table.labels
      self_link       = table.self_link
      creation_time   = table.creation_time
      last_modified_time = table.last_modified_time
      location        = table.location
      num_bytes       = table.num_bytes
      num_long_term_bytes = table.num_long_term_bytes
      num_rows        = table.num_rows
      type            = table.type
    }
  }
}

output "bigquery_transfer_configs" {
  description = "Map of BigQuery Data Transfer configurations"
  value = {
    for transfer_name, transfer in google_bigquery_data_transfer_config.transfer_configs :
    transfer_name => {
      name                   = transfer.name
      display_name           = transfer.display_name
      data_source_id        = transfer.data_source_id
      destination_dataset_id = transfer.destination_dataset_id
      location              = transfer.location
      schedule              = transfer.schedule
      data_refresh_window_days = transfer.data_refresh_window_days
      disabled              = transfer.disabled
    }
  }
}

# Firestore Outputs
output "firestore_databases" {
  description = "Map of Firestore database details"
  value = {
    for db_name, db in google_firestore_database.databases :
    db_name => {
      name                        = db.name
      location_id                 = db.location_id
      type                        = db.type
      concurrency_mode           = db.concurrency_mode
      app_engine_integration_mode = db.app_engine_integration_mode
      point_in_time_recovery_enablement = db.point_in_time_recovery_enablement
      delete_protection_state    = db.delete_protection_state
      uid                        = db.uid
      create_time               = db.create_time
      update_time               = db.update_time
      earliest_version_time     = db.earliest_version_time
      version_retention_period  = db.version_retention_period
      etag                      = db.etag
    }
  }
}

output "firestore_indexes" {
  description = "Map of Firestore indexes created"
  value = {
    for index_key, index in google_firestore_index.indexes :
    index_key => {
      name       = index.name
      database   = index.database
      collection = index.collection
      query_scope = index.query_scope
      api_scope  = index.api_scope
      fields     = index.fields
    }
  }
}

output "firestore_backup_schedules" {
  description = "Map of Firestore backup schedules"
  value = {
    for schedule_key, schedule in google_firestore_backup_schedule.backup_schedules :
    schedule_key => {
      name      = schedule.name
      database  = schedule.database
      retention = schedule.retention
    }
  }
}

# Cloud Storage Outputs
output "storage_buckets" {
  description = "Map of Cloud Storage bucket details"
  value = {
    for bucket_name, bucket in google_storage_bucket.buckets :
    bucket_name => {
      name                        = bucket.name
      url                         = bucket.url
      self_link                   = bucket.self_link
      location                    = bucket.location
      storage_class               = bucket.storage_class
      versioning                  = bucket.versioning
      uniform_bucket_level_access = bucket.uniform_bucket_level_access
      public_access_prevention    = bucket.public_access_prevention
      labels                      = bucket.labels
      lifecycle_rule              = bucket.lifecycle_rule
      retention_policy            = bucket.retention_policy
      encryption                  = bucket.encryption
      cors                        = bucket.cors
      website                     = bucket.website
      logging                     = bucket.logging
    }
  }
}

output "storage_bucket_iam" {
  description = "Map of Cloud Storage bucket IAM bindings"
  value = {
    for binding_key, binding in google_storage_bucket_iam_binding.bucket_bindings :
    binding_key => {
      bucket  = binding.bucket
      role    = binding.role
      members = binding.members
    }
  }
}

output "storage_notifications" {
  description = "Map of Cloud Storage bucket notifications"
  value = {
    for notification_key, notification in google_storage_notification.bucket_notifications :
    notification_key => {
      id             = notification.id
      bucket         = notification.bucket
      topic          = notification.topic
      payload_format = notification.payload_format
      event_types    = notification.event_types
      object_name_prefix = notification.object_name_prefix
      custom_attributes = notification.custom_attributes
      self_link      = notification.self_link
    }
  }
}

# Memorystore Outputs
output "redis_instances" {
  description = "Map of Redis instance details"
  value = {
    for instance_name, instance in google_redis_instance.redis_instances :
    instance_name => {
      name                    = instance.name
      display_name            = instance.display_name
      region                  = instance.region
      location_id             = instance.location_id
      alternative_location_id = instance.alternative_location_id
      tier                    = instance.tier
      memory_size_gb          = instance.memory_size_gb
      redis_version           = instance.redis_version
      host                    = instance.host
      port                    = instance.port
      current_location_id     = instance.current_location_id
      create_time            = instance.create_time
      state                  = instance.state
      status_message         = instance.status_message
      redis_configs          = instance.redis_configs
      auth_string            = instance.auth_string
      server_ca_certs        = instance.server_ca_certs
      transit_encryption_mode = instance.transit_encryption_mode
      labels                 = instance.labels
    }
  }
  sensitive = true
}

output "memcached_instances" {
  description = "Map of Memcached instance details"
  value = {
    for instance_name, instance in google_memcache_instance.memcached_instances :
    instance_name => {
      name                = instance.name
      display_name        = instance.display_name
      region              = instance.region
      zones               = instance.zones
      authorized_network  = instance.authorized_network
      node_count          = instance.node_count
      node_config         = instance.node_config
      memcache_version    = instance.memcache_version
      memcache_full_version = instance.memcache_full_version
      instance_messages   = instance.instance_messages
      discovery_endpoint  = instance.discovery_endpoint
      memcache_nodes      = instance.memcache_nodes
      create_time        = instance.create_time
      state              = instance.state
      labels             = instance.labels
    }
  }
}

# Dataflow Outputs
output "dataflow_jobs" {
  description = "Map of Dataflow job details"
  value = {
    for job_name, job in google_dataflow_flex_template_job.dataflow_jobs :
    job_name => {
      name                = job.name
      job_id             = job.job_id
      project            = job.project
      region             = job.region
      state              = job.state
      type               = job.type
      sdk_container_image = job.sdk_container_image
      labels             = job.labels
    }
  }
}

# Pub/Sub Outputs
output "pubsub_topics" {
  description = "Map of Pub/Sub topic details"
  value = {
    for topic_name, topic in google_pubsub_topic.data_topics :
    topic_name => {
      name                       = topic.name
      kms_key_name              = topic.kms_key_name
      labels                    = topic.labels
      message_retention_duration = topic.message_retention_duration
      message_storage_policy    = topic.message_storage_policy
      schema_settings           = topic.schema_settings
    }
  }
}

output "pubsub_subscriptions" {
  description = "Map of Pub/Sub subscription details"
  value = {
    for subscription_key, subscription in google_pubsub_subscription.data_subscriptions :
    subscription_key => {
      name                       = subscription.name
      topic                      = subscription.topic
      ack_deadline_seconds       = subscription.ack_deadline_seconds
      message_retention_duration = subscription.message_retention_duration
      retain_acked_messages      = subscription.retain_acked_messages
      enable_message_ordering    = subscription.enable_message_ordering
      filter                     = subscription.filter
      labels                     = subscription.labels
      push_config               = subscription.push_config
      bigquery_config           = subscription.bigquery_config
      cloud_storage_config      = subscription.cloud_storage_config
      dead_letter_policy        = subscription.dead_letter_policy
      retry_policy              = subscription.retry_policy
      expiration_policy         = subscription.expiration_policy
    }
  }
}

# Data Catalog Outputs
output "data_catalog_entry_groups" {
  description = "Map of Data Catalog entry group details"
  value = {
    for group_name, group in google_data_catalog_entry_group.entry_groups :
    group_name => {
      name         = group.name
      entry_group_id = group.entry_group_id
      display_name = group.display_name
      description  = group.description
      region       = group.region
    }
  }
}

# Cloud Scheduler Outputs
output "scheduler_jobs" {
  description = "Map of Cloud Scheduler job details"
  value = {
    for job_name, job in google_cloud_scheduler_job.data_jobs :
    job_name => {
      name        = job.name
      description = job.description
      schedule    = job.schedule
      time_zone   = job.time_zone
      region      = job.region
      state       = job.state
    }
  }
}

# Network Configuration Outputs
output "private_vpc_connection" {
  description = "Private VPC connection for Cloud SQL"
  value = var.enable_private_ip && var.network_id != null ? {
    network                 = google_service_networking_connection.private_vpc_connection[0].network
    service                 = google_service_networking_connection.private_vpc_connection[0].service
    reserved_peering_ranges = google_service_networking_connection.private_vpc_connection[0].reserved_peering_ranges
  } : null
}

output "private_ip_range" {
  description = "Reserved IP range for private Cloud SQL"
  value = var.enable_private_ip && var.network_id != null ? {
    name          = google_compute_global_address.private_ip_range[0].name
    address       = google_compute_global_address.private_ip_range[0].address
    prefix_length = google_compute_global_address.private_ip_range[0].prefix_length
    address_type  = google_compute_global_address.private_ip_range[0].address_type
    purpose       = google_compute_global_address.private_ip_range[0].purpose
    network       = google_compute_global_address.private_ip_range[0].network
  } : null
}

# Connection Strings and Endpoints
output "connection_info" {
  description = "Connection information for data services"
  value = {
    sql_instances = {
      for instance_name, instance in google_sql_database_instance.instances :
      instance_name => {
        connection_name    = instance.connection_name
        private_ip_address = instance.private_ip_address
        public_ip_address  = instance.public_ip_address
        # Connection string format for applications
        private_connection_string = var.enable_private_ip ? 
          "postgresql://username:password@${instance.private_ip_address}:5432/database" : null
        public_connection_string = 
          "postgresql://username:password@${instance.public_ip_address}:5432/database"
      }
    }
    
    redis_instances = {
      for instance_name, instance in google_redis_instance.redis_instances :
      instance_name => {
        host = instance.host
        port = instance.port
        # Redis connection string
        connection_string = "redis://${instance.host}:${instance.port}"
        auth_string = instance.auth_string
      }
    }
    
    memcached_instances = {
      for instance_name, instance in google_memcache_instance.memcached_instances :
      instance_name => {
        discovery_endpoint = instance.discovery_endpoint
        # Memcached connection endpoint
        connection_endpoint = instance.discovery_endpoint
      }
    }
    
    firestore_databases = {
      for db_name, db in google_firestore_database.databases :
      db_name => {
        # Firestore connection information
        database_id = db.name
        location_id = db.location_id
        # Connection URL format
        connection_url = "projects/${var.project_id}/databases/${db.name}"
      }
    }
  }
  sensitive = true
}

# Summary Output
output "data_infrastructure_summary" {
  description = "Comprehensive summary of data infrastructure"
  value = {
    sql_instances = {
      total = length(google_sql_database_instance.instances)
      instances = [for instance in google_sql_database_instance.instances : instance.name]
      databases_total = length(google_sql_database.databases)
      users_total = length(google_sql_user.users)
      private_connectivity = var.enable_private_ip
    }
    
    bigquery = {
      datasets_total = length(google_bigquery_dataset.datasets)
      tables_total = length(google_bigquery_table.tables)
      transfer_configs_total = length(google_bigquery_data_transfer_config.transfer_configs)
      datasets = [for dataset in google_bigquery_dataset.datasets : dataset.dataset_id]
    }
    
    firestore = {
      databases_total = length(google_firestore_database.databases)
      indexes_total = length(google_firestore_index.indexes)
      backup_schedules_total = length(google_firestore_backup_schedule.backup_schedules)
      databases = [for db in google_firestore_database.databases : db.name]
    }
    
    storage = {
      buckets_total = length(google_storage_bucket.buckets)
      notifications_total = length(google_storage_notification.bucket_notifications)
      iam_bindings_total = length(google_storage_bucket_iam_binding.bucket_bindings)
      buckets = [for bucket in google_storage_bucket.buckets : bucket.name]
    }
    
    memorystore = {
      redis_instances_total = length(google_redis_instance.redis_instances)
      memcached_instances_total = length(google_memcache_instance.memcached_instances)
      total_instances = length(google_redis_instance.redis_instances) + length(google_memcache_instance.memcached_instances)
      redis_instances = [for instance in google_redis_instance.redis_instances : instance.name]
      memcached_instances = [for instance in google_memcache_instance.memcached_instances : instance.name]
    }
    
    dataflow = {
      jobs_total = length(google_dataflow_flex_template_job.dataflow_jobs)
      jobs = [for job in google_dataflow_flex_template_job.dataflow_jobs : job.name]
    }
    
    pubsub = {
      topics_total = length(google_pubsub_topic.data_topics)
      subscriptions_total = length(google_pubsub_subscription.data_subscriptions)
      topics = [for topic in google_pubsub_topic.data_topics : topic.name]
    }
    
    data_catalog = {
      entry_groups_total = length(google_data_catalog_entry_group.entry_groups)
      entry_groups = [for group in google_data_catalog_entry_group.entry_groups : group.name]
    }
    
    scheduler = {
      jobs_total = length(google_cloud_scheduler_job.data_jobs)
      jobs = [for job in google_cloud_scheduler_job.data_jobs : job.name]
    }
    
    network = {
      private_ip_enabled = var.enable_private_ip
      network_id = var.network_id
      subnet_id = var.subnet_id
    }
    
    labels_applied = local.merged_labels
    created_at = timestamp()
  }
}