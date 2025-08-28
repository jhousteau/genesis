package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestStateBackendModule(t *testing.T) {
	t.Parallel()

	terraformOptions := &terraform.Options{
		// Path to the Terraform code that will be tested
		TerraformDir: "../modules/state-backend",

		// Variables to pass to our Terraform code
		Vars: map[string]interface{}{
			"project_id": "test-project-" + generateRandomString(6),
			"location":   "US",
		},

		// Disable colors in Terraform commands so it's easier to parse stdout/stderr
		NoColor: true,
	}

	// Clean up everything at the end of the test
	defer terraform.Destroy(t, terraformOptions)

	// Run `terraform init` and `terraform apply`
	terraform.InitAndApply(t, terraformOptions)

	// Run `terraform output` to get the bucket name
	bucketName := terraform.Output(t, terraformOptions, "bucket_name")

	// Verify the bucket name follows expected format
	assert.Contains(t, bucketName, "test-project-")
	assert.Contains(t, bucketName, "-terraform-state")
}

func TestBootstrapModule(t *testing.T) {
	t.Parallel()

	terraformOptions := &terraform.Options{
		TerraformDir: "../modules/bootstrap",
		Vars: map[string]interface{}{
			"project_id":      "test-bootstrap-" + generateRandomString(6),
			"billing_account": "ABCDEF-123456-ABCDEF", // Mock billing account
		},
		NoColor: true,
	}

	defer terraform.Destroy(t, terraformOptions)

	// Only test plan to avoid creating real resources
	terraform.InitAndPlan(t, terraformOptions)
}

// Helper function to generate random string
func generateRandomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyz0123456789"
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[len(charset)/2] // Simple deterministic approach for testing
	}
	return string(b)
}
