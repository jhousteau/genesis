/**
 * Security Module Variables
 *
 * Comprehensive security infrastructure configuration for GCP
 */

# Basic Configuration
variable "project_id" {
  description = "The GCP project ID where security resources will be created"
  type        = string
}

variable "organization_id" {
  description = "The GCP organization ID for organization-level security controls"
  type        = string
  default     = null
}

variable "name_prefix" {
  description = "Prefix for all security resource names"
  type        = string
  default     = "security"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "default_region" {
  description = "Default region for security resources"
  type        = string
  default     = "us-central1"
}

variable "labels" {
  description = "Additional labels to apply to all security resources"
  type        = map(string)
  default     = {}
}

# KMS Configuration
variable "kms_key_rings" {
  description = "KMS key rings configuration"
  type = list(object({
    name     = string
    location = optional(string)
    keys = optional(list(object({
      name            = string
      purpose         = optional(string, "ENCRYPT_DECRYPT")
      rotation_period = optional(string, "7776000s") # 90 days
      version_template = optional(object({
        algorithm        = string
        protection_level = optional(string, "SOFTWARE")
      }))
      labels = optional(map(string), {})
      iam_bindings = optional(list(object({
        role    = string
        members = list(string)
        condition = optional(object({
          title       = string
          description = optional(string)
          expression  = string
        }))
      })), [])
    })), [])
  }))
  default = []

  validation {
    condition = alltrue([
      for ring in var.kms_key_rings : alltrue([
        for key in ring.keys : contains([
          "ENCRYPT_DECRYPT",
          "ASYMMETRIC_SIGN",
          "ASYMMETRIC_DECRYPT",
          "MAC"
        ], key.purpose)
      ])
    ])
    error_message = "Key purpose must be one of: ENCRYPT_DECRYPT, ASYMMETRIC_SIGN, ASYMMETRIC_DECRYPT, MAC"
  }
}

# Secret Manager Configuration
variable "secrets" {
  description = "Secret Manager secrets configuration"
  type = list(object({
    name               = string
    secret_data        = optional(string)
    replication_policy = optional(string, "auto") # auto or user_managed
    replica_locations = optional(list(object({
      location       = string
      encryption_key = optional(string)
    })), [])
    encryption_key = optional(string)
    expire_time    = optional(string)
    ttl            = optional(string)
    rotation = optional(object({
      next_rotation_time = optional(string)
      rotation_period    = optional(string)
    }))
    topics      = optional(list(string), [])
    annotations = optional(map(string), {})
    labels      = optional(map(string), {})
    secret_type = optional(string, "application")
    enabled     = optional(bool, true)
    iam_bindings = optional(list(object({
      role    = string
      members = list(string)
      condition = optional(object({
        title       = string
        description = optional(string)
        expression  = string
      }))
    })), [])
  }))
  default = []

  validation {
    condition = alltrue([
      for secret in var.secrets : contains(["auto", "user_managed"], secret.replication_policy)
    ])
    error_message = "Replication policy must be 'auto' or 'user_managed'"
  }
}

# Custom IAM Roles Configuration
variable "custom_iam_roles" {
  description = "Custom IAM roles configuration"
  type = list(object({
    role_id     = string
    title       = string
    description = string
    permissions = list(string)
    stage       = optional(string, "GA")
    scope       = optional(string, "project") # project or organization
  }))
  default = []

  validation {
    condition = alltrue([
      for role in var.custom_iam_roles : contains(["ALPHA", "BETA", "GA", "DEPRECATED"], role.stage)
    ])
    error_message = "Role stage must be one of: ALPHA, BETA, GA, DEPRECATED"
  }

  validation {
    condition = alltrue([
      for role in var.custom_iam_roles : contains(["project", "organization"], role.scope)
    ])
    error_message = "Role scope must be 'project' or 'organization'"
  }
}

# Conditional IAM Bindings
variable "conditional_iam_bindings" {
  description = "Conditional IAM bindings configuration"
  type = list(object({
    role    = string
    members = list(string)
    condition = optional(object({
      title       = string
      description = optional(string)
      expression  = string
    }))
  }))
  default = []
}

# Security Command Center Configuration
variable "security_center_sources" {
  description = "Security Command Center custom sources"
  type = list(object({
    display_name = string
    description  = optional(string)
  }))
  default = []
}

variable "security_center_notifications" {
  description = "Security Command Center notification configurations"
  type = list(object({
    config_id    = string
    description  = optional(string)
    pubsub_topic = string
    filter       = string
  }))
  default = []
}

# Binary Authorization Configuration
variable "binary_authorization" {
  description = "Binary Authorization configuration"
  type = object({
    enabled = bool
    default_admission_rule = object({
      evaluation_mode  = string
      enforcement_mode = string
    })
    admission_whitelist_patterns = optional(list(string), [])
    istio_service_identity_admission_rules = optional(list(object({
      evaluation_mode         = string
      enforcement_mode        = string
      require_attestations_by = list(string)
    })), [])
    kubernetes_namespace_admission_rules = optional(list(object({
      namespace               = string
      evaluation_mode         = string
      enforcement_mode        = string
      require_attestations_by = list(string)
    })), [])
    kubernetes_service_account_admission_rules = optional(list(object({
      service_account         = string
      namespace               = string
      evaluation_mode         = string
      enforcement_mode        = string
      require_attestations_by = list(string)
    })), [])
    global_policy_evaluation_mode = optional(string, "ENABLE")
    attestors = list(object({
      name           = string
      note_reference = string
      description    = optional(string)
      public_keys = optional(list(object({
        id                           = string
        ascii_armored_pgp_public_key = optional(string)
        pkix_public_key = optional(object({
          public_key_pem      = string
          signature_algorithm = optional(string)
        }))
      })), [])
    }))
  })
  default = {
    enabled = false
    default_admission_rule = {
      evaluation_mode  = "REQUIRE_ATTESTATION"
      enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"
    }
    attestors = []
  }

  validation {
    condition = contains([
      "ALWAYS_ALLOW",
      "ALWAYS_DENY",
      "REQUIRE_ATTESTATION"
    ], var.binary_authorization.default_admission_rule.evaluation_mode)
    error_message = "Evaluation mode must be ALWAYS_ALLOW, ALWAYS_DENY, or REQUIRE_ATTESTATION"
  }

  validation {
    condition = contains([
      "ENFORCED_BLOCK_AND_AUDIT_LOG",
      "DRYRUN_AUDIT_LOG_ONLY"
    ], var.binary_authorization.default_admission_rule.enforcement_mode)
    error_message = "Enforcement mode must be ENFORCED_BLOCK_AND_AUDIT_LOG or DRYRUN_AUDIT_LOG_ONLY"
  }
}

# Security Policies (Cloud Armor) Configuration
variable "security_policies" {
  description = "Cloud Armor security policies configuration"
  type = list(object({
    name        = string
    description = optional(string)
    type        = optional(string, "CLOUD_ARMOR")
    adaptive_protection_config = optional(object({
      layer_7_ddos_defense_config = object({
        enable          = optional(bool, true)
        rule_visibility = optional(string, "STANDARD")
      })
      auto_deploy_config = object({
        load_threshold              = optional(number, 0.1)
        confidence_threshold        = optional(number, 0.5)
        impacted_baseline_threshold = optional(number, 0.01)
        expiration_sec              = optional(number, 600)
      })
    }))
    advanced_options_config = optional(object({
      json_parsing                     = optional(string, "DISABLED")
      json_custom_config_content_types = optional(list(string), [])
      log_level                        = optional(string, "NORMAL")
      user_ip_request_headers          = optional(list(string), [])
    }))
    recaptcha_options_config = optional(object({
      redirect_site_key = string
    }))
    rules = optional(list(object({
      action      = string
      priority    = number
      description = optional(string)
      preview     = optional(bool, false)
      match = optional(object({
        versioned_expr = optional(string)
        config = optional(object({
          src_ip_ranges = list(string)
        }))
        expr = optional(object({
          expression = string
        }))
      }))
      rate_limit_options = optional(object({
        conform_action      = string
        exceed_action       = string
        enforce_on_key      = optional(string)
        enforce_on_key_name = optional(string)
        rate_limit_threshold = optional(object({
          count        = number
          interval_sec = number
        }))
        ban_threshold = optional(object({
          count        = number
          interval_sec = number
        }))
        ban_duration_sec = optional(number)
      }))
      header_action = optional(object({
        request_headers_to_adds = list(object({
          header_name  = string
          header_value = string
        }))
      }))
      redirect_options = optional(object({
        type   = string
        target = optional(string)
      }))
    })), [])
  }))
  default = []

  validation {
    condition = alltrue([
      for policy in var.security_policies : contains(["CLOUD_ARMOR", "CLOUD_ARMOR_EDGE"], policy.type)
    ])
    error_message = "Security policy type must be CLOUD_ARMOR or CLOUD_ARMOR_EDGE"
  }
}

# Web Security Scanner Configuration
variable "web_security_scanner" {
  description = "Web Security Scanner configuration"
  type = object({
    enabled = bool
    scan_configs = list(object({
      display_name  = string
      starting_urls = list(string)
      authentication = optional(object({
        google_account = optional(object({
          username = string
          password = string
        }))
        custom_account = optional(object({
          username  = string
          password  = string
          login_url = string
        }))
      }))
      schedule = optional(object({
        schedule_time          = string
        interval_duration_days = optional(number, 7)
      }))
      blacklist_patterns                = optional(list(string), [])
      max_qps                           = optional(number, 15)
      user_agent                        = optional(string, "CHROME_LINUX")
      export_to_security_command_center = optional(string, "ENABLED")
    }))
  })
  default = {
    enabled      = false
    scan_configs = []
  }

  validation {
    condition = alltrue([
      for config in var.web_security_scanner.scan_configs : contains([
        "CHROME_LINUX",
        "CHROME_ANDROID",
        "SAFARI_IPHONE"
      ], config.user_agent)
    ])
    error_message = "User agent must be CHROME_LINUX, CHROME_ANDROID, or SAFARI_IPHONE"
  }
}

# VPC Security Controls Configuration
variable "vpc_security_controls" {
  description = "VPC Security Controls configuration"
  type = object({
    enabled = bool
    access_levels = list(object({
      name        = string
      title       = string
      description = optional(string)
      basic = optional(object({
        combining_function = optional(string, "AND")
        conditions = list(object({
          ip_subnetworks         = optional(list(string), [])
          required_access_levels = optional(list(string), [])
          members                = optional(list(string), [])
          negate                 = optional(bool, false)
          regions                = optional(list(string), [])
          device_policy = optional(object({
            require_screen_lock              = optional(bool, false)
            require_admin_approval           = optional(bool, false)
            require_corp_owned               = optional(bool, false)
            allowed_device_management_levels = optional(list(string), [])
            allowed_encryption_statuses      = optional(list(string), [])
            os_constraints = optional(list(object({
              os_type                    = string
              minimum_version            = optional(string)
              require_verified_chrome_os = optional(bool, false)
            })), [])
          }))
        }))
      }))
      custom = optional(object({
        expr = object({
          expression  = string
          title       = optional(string)
          description = optional(string)
          location    = optional(string, "")
        })
      }))
    }))
    service_perimeters = list(object({
      name           = string
      title          = string
      description    = optional(string)
      perimeter_type = optional(string, "PERIMETER_TYPE_REGULAR")
      status = optional(object({
        resources           = list(string)
        restricted_services = list(string)
        access_levels       = list(string)
        vpc_accessible_services = optional(object({
          enable_restriction = bool
          allowed_services   = list(string)
        }))
        ingress_policies = optional(list(object({
          ingress_from = optional(object({
            sources = object({
              access_level = optional(string)
              resource     = optional(string)
            })
            identity_type = optional(string)
            identities    = optional(list(string), [])
          }))
          ingress_to = optional(object({
            resources = list(string)
            operations = optional(list(object({
              service_name = string
              method_selectors = optional(list(object({
                method     = optional(string)
                permission = optional(string)
              })), [])
            })), [])
          }))
        })), [])
        egress_policies = optional(list(object({
          egress_from = optional(object({
            identity_type = optional(string)
            identities    = optional(list(string), [])
          }))
          egress_to = optional(object({
            resources          = optional(list(string), [])
            external_resources = optional(list(string), [])
            operations = optional(list(object({
              service_name = string
              method_selectors = optional(list(object({
                method     = optional(string)
                permission = optional(string)
              })), [])
            })), [])
          }))
        })), [])
      }))
      spec = optional(object({
        resources           = list(string)
        restricted_services = list(string)
        access_levels       = list(string)
        vpc_accessible_services = optional(object({
          enable_restriction = bool
          allowed_services   = list(string)
        }))
      }))
    }))
  })
  default = {
    enabled            = false
    access_levels      = []
    service_perimeters = []
  }

  validation {
    condition = alltrue([
      for perimeter in var.vpc_security_controls.service_perimeters : contains([
        "PERIMETER_TYPE_REGULAR",
        "PERIMETER_TYPE_BRIDGE"
      ], perimeter.perimeter_type)
    ])
    error_message = "Perimeter type must be PERIMETER_TYPE_REGULAR or PERIMETER_TYPE_BRIDGE"
  }
}

variable "access_context_manager_policy" {
  description = "Access Context Manager policy ID for VPC Security Controls"
  type        = string
  default     = null
}

# Data Loss Prevention (DLP) Configuration
variable "dlp_config" {
  description = "Data Loss Prevention configuration"
  type = object({
    enabled = bool
    inspect_templates = list(object({
      display_name = string
      description  = optional(string)
      inspect_config = object({
        info_types = optional(list(object({
          name = string
        })), [])
        min_likelihood     = optional(string, "POSSIBLE")
        include_quote      = optional(bool, false)
        exclude_info_types = optional(bool, false)
        limits = optional(object({
          max_findings_per_item    = optional(number, 100)
          max_findings_per_request = optional(number, 1000)
          max_findings_per_info_type = optional(list(object({
            info_type = object({
              name = string
            })
            max_findings = number
          })), [])
        }))
        custom_info_types = optional(list(object({
          info_type = object({
            name = string
          })
          likelihood = optional(string, "POSSIBLE")
          dictionary = optional(object({
            word_list = object({
              words = list(string)
            })
          }))
          regex = optional(object({
            pattern = string
          }))
        })), [])
        rule_sets = optional(list(object({
          info_types = object({
            name = string
          })
          rules = optional(list(object({
            hotword_rule = optional(object({
              hotword_regex = object({
                pattern = string
              })
              proximity = object({
                window_before = optional(number, 50)
                window_after  = optional(number, 50)
              })
              likelihood_adjustment = object({
                fixed_likelihood = optional(string, "VERY_LIKELY")
              })
            }))
            exclusion_rule = optional(object({
              matching_type = string
              dictionary = optional(object({
                word_list = object({
                  words = list(string)
                })
              }))
              regex = optional(object({
                pattern = string
              }))
            }))
          })), [])
        })), [])
      })
    }))
    job_triggers = list(object({
      display_name = string
      description  = optional(string)
      status       = optional(string, "HEALTHY")
      triggers = list(object({
        schedule = optional(object({
          recurrence_period_duration = string
        }))
        manual = optional(bool, false)
      }))
      inspect_job = object({
        inspect_template_name = optional(string)
        storage_config = object({
          cloud_storage_options = optional(object({
            file_set = object({
              url = string
            })
            bytes_limit_per_file         = optional(number, 0)
            bytes_limit_per_file_percent = optional(number, 0)
            file_types                   = optional(list(string), [])
            sample_method                = optional(string, "TOP")
            files_limit_percent          = optional(number, 0)
          }))
          big_query_options = optional(object({
            table_reference = object({
              project_id = optional(string)
              dataset_id = string
              table_id   = string
            })
            rows_limit         = optional(number, 0)
            rows_limit_percent = optional(number, 0)
            sample_method      = optional(string, "TOP")
            identifying_fields = optional(list(object({
              name = string
            })), [])
            excluded_fields = optional(list(object({
              name = string
            })), [])
            included_fields = optional(list(object({
              name = string
            })), [])
          }))
          datastore_options = optional(object({
            partition_id = object({
              project_id   = optional(string)
              namespace_id = optional(string)
            })
            kind = object({
              name = string
            })
          }))
          timespan_config = optional(object({
            start_time = optional(string)
            end_time   = optional(string)
            timestamp_field = optional(object({
              name = string
            }))
            enable_auto_population_of_timespan_config = optional(bool, false)
          }))
        })
        actions = optional(list(object({
          save_findings = optional(object({
            output_config = object({
              table = object({
                project_id = optional(string)
                dataset_id = string
                table_id   = optional(string)
              })
              output_schema = optional(string, "BASIC_COLUMNS")
            })
          }))
          pub_sub = optional(object({
            topic = string
          }))
          publish_summary_to_cscc                = optional(bool, false)
          publish_findings_to_cloud_data_catalog = optional(bool, false)
        })), [])
      })
    }))
  })
  default = {
    enabled           = false
    inspect_templates = []
    job_triggers      = []
  }

  validation {
    condition = alltrue(flatten([
      for template in var.dlp_config.inspect_templates : [
        for info_type in template.inspect_config.info_types : contains([
          "POSSIBLE", "LIKELY", "VERY_LIKELY", "VERY_UNLIKELY", "UNLIKELY"
        ], template.inspect_config.min_likelihood)
      ]
    ]))
    error_message = "DLP likelihood must be one of: POSSIBLE, LIKELY, VERY_LIKELY, VERY_UNLIKELY, UNLIKELY"
  }

  validation {
    condition = alltrue([
      for trigger in var.dlp_config.job_triggers : contains([
        "HEALTHY", "PAUSED", "CANCELLED"
      ], trigger.status)
    ])
    error_message = "DLP job trigger status must be HEALTHY, PAUSED, or CANCELLED"
  }
}

# Advanced Security Configuration
variable "enable_security_monitoring" {
  description = "Enable comprehensive security monitoring and alerting"
  type        = bool
  default     = true
}

variable "enable_compliance_automation" {
  description = "Enable automated compliance scanning and reporting"
  type        = bool
  default     = true
}

variable "security_notifications" {
  description = "Security notification configuration"
  type = object({
    enabled           = bool
    email_recipients  = optional(list(string), [])
    slack_webhook_url = optional(string)
    pagerduty_key     = optional(string)
    severity_levels   = optional(list(string), ["HIGH", "CRITICAL"])
  })
  default = {
    enabled = false
  }

  validation {
    condition = alltrue([
      for level in var.security_notifications.severity_levels : contains([
        "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"
      ], level)
    ])
    error_message = "Severity levels must be one of: INFO, LOW, MEDIUM, HIGH, CRITICAL"
  }
}

variable "security_baseline" {
  description = "Security baseline configuration"
  type = object({
    enabled                        = bool
    cis_benchmarks                 = optional(bool, true)
    nist_framework                 = optional(bool, true)
    iso_27001                      = optional(bool, false)
    encryption_at_rest_required    = optional(bool, true)
    encryption_in_transit_required = optional(bool, true)
    mfa_required                   = optional(bool, true)
    password_policy = optional(object({
      min_length        = optional(number, 12)
      require_uppercase = optional(bool, true)
      require_lowercase = optional(bool, true)
      require_numbers   = optional(bool, true)
      require_symbols   = optional(bool, true)
      max_age_days      = optional(number, 90)
    }), {})
    session_management = optional(object({
      max_session_duration_hours = optional(number, 8)
      idle_timeout_minutes       = optional(number, 60)
      concurrent_sessions_limit  = optional(number, 3)
    }), {})
  })
  default = {
    enabled = true
  }
}

variable "threat_detection" {
  description = "Advanced threat detection configuration"
  type = object({
    enabled              = bool
    anomaly_detection    = optional(bool, true)
    behavioral_analysis  = optional(bool, true)
    machine_learning     = optional(bool, false)
    threat_intelligence  = optional(bool, true)
    real_time_monitoring = optional(bool, true)
    custom_rules = optional(list(object({
      name        = string
      description = string
      severity    = string
      conditions  = list(string)
      actions     = list(string)
    })), [])
  })
  default = {
    enabled = false
  }

  validation {
    condition = alltrue([
      for rule in var.threat_detection.custom_rules : contains([
        "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"
      ], rule.severity)
    ])
    error_message = "Threat detection rule severity must be one of: INFO, LOW, MEDIUM, HIGH, CRITICAL"
  }
}

variable "incident_response" {
  description = "Incident response automation configuration"
  type = object({
    enabled             = bool
    auto_containment    = optional(bool, false)
    auto_investigation  = optional(bool, true)
    playbooks_enabled   = optional(bool, true)
    forensics_enabled   = optional(bool, false)
    recovery_automation = optional(bool, false)
    escalation_policy = optional(object({
      level_1_timeout_minutes = optional(number, 15)
      level_2_timeout_minutes = optional(number, 60)
      level_3_timeout_minutes = optional(number, 240)
      contacts = optional(list(object({
        level = number
        type  = string # email, sms, webhook
        value = string
      })), [])
    }), {})
  })
  default = {
    enabled = false
  }

  validation {
    condition = alltrue([
      for contact in var.incident_response.escalation_policy.contacts : contains([
        "email", "sms", "webhook", "slack", "pagerduty"
      ], contact.type)
    ])
    error_message = "Incident response contact type must be one of: email, sms, webhook, slack, pagerduty"
  }
}
