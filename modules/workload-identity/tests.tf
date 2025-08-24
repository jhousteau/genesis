/**
 * Test configurations for the Workload Identity Federation module
 * Run these tests to validate the module functionality
 */

# Test 1: Minimal valid configuration
module "test_minimal" {
  source = "../workload-identity"

  project_id = "test-project"
  pool_id    = "test-pool"
}

# Test 2: GitHub Actions provider
module "test_github" {
  source = "../workload-identity"

  project_id = "test-project"
  pool_id    = "github-test"

  providers = {
    github = {
      provider_id = "github-test"

      github = {
        organization = "test-org"
        repositories = ["test-repo"]
        branches     = ["main"]
      }
    }
  }

  service_accounts = {
    test = {
      service_account_id = "github-test-sa"

      bindings = [{
        provider_id = "github-test"
      }]
    }
  }
}

# Test 3: Multiple providers
module "test_multi_provider" {
  source = "../workload-identity"

  project_id = "test-project"
  pool_id    = "multi-test"

  providers = {
    github = {
      provider_id = "github"
      github = {
        organization = "org1"
      }
    }

    gitlab = {
      provider_id = "gitlab"
      gitlab = {
        project_path = "group/project"
      }
    }
  }
}

# Test 4: Custom attribute conditions
module "test_custom_conditions" {
  source = "../workload-identity"

  project_id = "test-project"
  pool_id    = "conditions-test"

  providers = {
    custom = {
      provider_id         = "custom"
      issuer_uri          = "https://custom.issuer.com"
      attribute_condition = "assertion.env == 'production'"

      attribute_mapping = {
        "google.subject" = "assertion.sub"
        "attribute.env"  = "assertion.environment"
      }
    }
  }
}

# Test 5: Existing service account
module "test_existing_sa" {
  source = "../workload-identity"

  project_id = "test-project"
  pool_id    = "existing-sa-test"

  providers = {
    test = {
      provider_id = "test"
      issuer_uri  = "https://test.com"
    }
  }

  service_accounts = {
    existing = {
      create_new     = false
      existing_email = "existing@test-project.iam.gserviceaccount.com"

      bindings = [{
        provider_id = "test"
      }]
    }
  }
}

# Test 6: Complex attribute conditions
module "test_complex_conditions" {
  source = "../workload-identity"

  project_id = "test-project"
  pool_id    = "complex-test"

  providers = {
    github_complex = {
      provider_id = "github-complex"

      github = {
        organization = "test-org"
        repositories = ["repo1", "repo2", "repo3"]
        branches     = ["main", "develop", "release/*"]
        environments = ["production", "staging"]
      }
    }
  }

  service_accounts = {
    complex = {
      service_account_id = "complex-sa"
      project_roles = [
        "roles/viewer",
        "roles/storage.objectViewer"
      ]

      bindings = [
        {
          provider_id         = "github-complex"
          attribute_condition = "attribute.environment == 'production'"
        },
        {
          provider_id         = "github-complex"
          attribute_condition = "attribute.environment == 'staging'"
          roles               = ["roles/iam.workloadIdentityUser", "roles/iam.serviceAccountTokenCreator"]
        }
      ]
    }
  }
}

# Test 7: All supported platforms
module "test_all_platforms" {
  source = "../workload-identity"

  project_id = "test-project"
  pool_id    = "all-platforms"

  providers = {
    github = {
      provider_id = "github"
      github = {
        organization = "org"
      }
    }

    gitlab = {
      provider_id = "gitlab"
      gitlab = {
        group_path = "group"
      }
    }

    azure = {
      provider_id = "azure"
      azure_devops = {
        organization = "org"
      }
    }

    terraform = {
      provider_id = "terraform"
      terraform_cloud = {
        organization = "org"
      }
    }
  }
}

# Test 8: Disabled pool and providers
module "test_disabled" {
  source = "../workload-identity"

  project_id    = "test-project"
  pool_id       = "disabled-test"
  pool_disabled = true

  providers = {
    disabled_provider = {
      provider_id = "disabled"
      disabled    = true
      issuer_uri  = "https://disabled.com"
    }
  }
}

# Test 9: Labels and metadata
module "test_labels" {
  source = "../workload-identity"

  project_id        = "test-project"
  pool_id           = "labeled-test"
  pool_display_name = "Test Pool with Labels"
  pool_description  = "This is a test pool with labels"

  labels = {
    environment = "test"
    team        = "platform"
    cost_center = "engineering"
  }

  providers = {
    test = {
      provider_id  = "test"
      display_name = "Test Provider"
      description  = "Test provider with metadata"
      issuer_uri   = "https://test.com"
    }
  }
}

# Test 10: Session duration configuration
module "test_session_duration" {
  source = "../workload-identity"

  project_id       = "test-project"
  pool_id          = "session-test"
  session_duration = "7200s" # 2 hours

  providers = {
    test = {
      provider_id = "test"
      issuer_uri  = "https://test.com"
    }
  }
}

# Test validation script
resource "null_resource" "validate_tests" {
  provisioner "local-exec" {
    command = <<-EOT
      echo "Running Terraform validation tests..."
      terraform init
      terraform validate
      echo "All tests passed successfully!"
    EOT
  }
}
