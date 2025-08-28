#!/bin/bash
set -e

echo "🔍 Testing Terraform modules..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$(cd "$TEST_DIR/.." && pwd)"

# Test function
test_module() {
    local module_path="$1"
    local module_name=$(basename "$module_path")
    
    echo "Testing module: $module_name"
    
    cd "$module_path"
    
    # Initialize
    terraform init -backend=false > /dev/null 2>&1 || {
        echo -e "${RED}❌ $module_name: terraform init failed${NC}"
        return 1
    }
    
    # Validate
    terraform validate > /dev/null 2>&1 || {
        echo -e "${RED}❌ $module_name: terraform validate failed${NC}"
        return 1
    }
    
    # Format check
    terraform fmt -check > /dev/null 2>&1 || {
        echo -e "${RED}❌ $module_name: terraform fmt check failed${NC}"
        return 1
    }
    
    echo -e "${GREEN}✅ $module_name: passed${NC}"
    return 0
}

# Test all modules
failed=0
for module in "$TERRAFORM_DIR/modules"/*; do
    if [ -d "$module" ]; then
        test_module "$module" || failed=1
    fi
done

# Test examples
echo ""
echo "Testing examples..."
for example in "$TERRAFORM_DIR/examples"/*; do
    if [ -d "$example" ]; then
        test_module "$example" || failed=1
    fi
done

# Test template
echo ""
echo "Testing terraform-project template..."
template_dir="$TERRAFORM_DIR/../templates/terraform-project"
if [ -d "$template_dir" ]; then
    test_module "$template_dir" || failed=1
fi

echo ""
if [ $failed -eq 0 ]; then
    echo -e "${GREEN}🎉 All Terraform modules passed validation!${NC}"
else
    echo -e "${RED}💥 Some tests failed${NC}"
    exit 1
fi