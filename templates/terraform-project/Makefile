.PHONY: help init plan apply destroy validate fmt check clean

# Default target
help:
	@echo "Available targets:"
	@echo "  init      - Initialize Terraform"
	@echo "  plan      - Show Terraform execution plan"
	@echo "  apply     - Apply Terraform changes"
	@echo "  destroy   - Destroy Terraform-managed resources"
	@echo "  validate  - Validate Terraform configuration"
	@echo "  fmt       - Format Terraform files"
	@echo "  check     - Run validation and formatting checks"
	@echo "  clean     - Remove Terraform cache and lock files"

# Initialize Terraform
init:
	terraform init

# Show execution plan
plan:
	terraform plan

# Apply changes
apply:
	terraform apply

# Destroy resources (with confirmation)
destroy:
	terraform destroy

# Validate configuration
validate:
	terraform validate

# Format Terraform files
fmt:
	terraform fmt -recursive

# Run all checks
check: validate fmt
	@echo "✅ All checks passed"

# Clean up cache files
clean:
	rm -rf .terraform/
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate.backup

# Quick setup (for new projects)
setup: init plan
	@echo "✅ Project initialized. Review the plan above, then run 'make apply'"
