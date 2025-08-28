.PHONY: test validate integration clean

# Quick validation tests (no resources created)
validate:
	@echo "🔍 Running Terraform validation tests..."
	./validate.sh

# Integration tests with terratest (creates real resources)
integration:
	@echo "🚀 Running Terraform integration tests..."
	@echo "⚠️  WARNING: This will create real GCP resources and may incur costs"
	go test -v -timeout 30m

# Run all tests
test: validate
	@echo "✅ Validation tests completed"
	@echo "💡 Run 'make integration' to test with real resources (costs may apply)"

# Clean test artifacts
clean:
	rm -rf .terraform/
	rm -f terraform.tfstate*
	rm -f .terraform.lock.hcl
	go clean -testcache

# Setup dependencies
setup:
	go mod tidy
