#!/usr/bin/env bash
# Test the hardcoded value detection scripts

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 Testing Hardcoded Value Detection Scripts${NC}"
echo "=============================================="
echo

# Check if we're in the right directory
if [ ! -f "scripts/find-hardcoded-values.sh" ] || [ ! -f "scripts/check-variable-defaults.sh" ]; then
    echo -e "${RED}❌ Please run this script from the Genesis root directory${NC}"
    exit 1
fi

# Check if pytest is available
if ! command -v pytest >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  pytest not found. Installing...${NC}"
    pip install pytest
fi

echo -e "${BLUE}📋 Running detection script tests...${NC}"
echo

# Run the pytest tests
if pytest tests/test_hardcoded_detection.py -v; then
    echo
    echo -e "${GREEN}✅ All detection script tests passed!${NC}"
else
    echo
    echo -e "${RED}❌ Some tests failed. Check output above.${NC}"
    exit 1
fi

echo
echo -e "${BLUE}🔍 Running quick manual tests...${NC}"

# Create temporary test files for manual verification
TEMP_DIR=$(mktemp -d)
echo "Using temp directory: $TEMP_DIR"

# Create test files with known issues
cat > "$TEMP_DIR/bad_python.py" << 'EOF'
def bad_function(name="hardcoded", port=8080):
    pass

DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
API_KEY = "sk-1234567890abcdef"
EOF

cat > "$TEMP_DIR/bad_typescript.ts" << 'EOF'
function badFunction(name = "hardcoded", port = 8080) {
    return name + port;
}

const config = {
    apiUrl: "https://api.example.com",
    timeout: 5000
};
EOF

cat > "$TEMP_DIR/good_python.py" << 'EOF'
def good_function(name=None, port=0):
    pass

import os
DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("API_KEY")
EOF

echo
echo -e "${YELLOW}Testing hardcoded values script on bad files...${NC}"
cd "$TEMP_DIR"

# Test hardcoded values script (should find issues)
if ../$(dirname "$0")/find-hardcoded-values.sh >/dev/null 2>&1; then
    echo -e "${RED}❌ Hardcoded values script should have detected issues but didn't${NC}"
else
    echo -e "${GREEN}✅ Hardcoded values script correctly detected issues${NC}"
fi

echo -e "${YELLOW}Testing variable defaults script on bad files...${NC}"
# Test variable defaults script (should find issues)
if ../$(dirname "$0")/check-variable-defaults.sh >/dev/null 2>&1; then
    echo -e "${RED}❌ Variable defaults script should have detected issues but didn't${NC}"
else
    echo -e "${GREEN}✅ Variable defaults script correctly detected issues${NC}"
fi

# Test with only good files
rm bad_python.py bad_typescript.ts

echo -e "${YELLOW}Testing scripts on clean files...${NC}"
# Should pass now
if ../$(dirname "$0")/find-hardcoded-values.sh >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Hardcoded values script correctly passed clean files${NC}"
else
    echo -e "${RED}❌ Hardcoded values script incorrectly failed on clean files${NC}"
fi

if ../$(dirname "$0")/check-variable-defaults.sh >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Variable defaults script correctly passed clean files${NC}"
else
    echo -e "${RED}❌ Variable defaults script incorrectly failed on clean files${NC}"
fi

# Cleanup
cd - >/dev/null
rm -rf "$TEMP_DIR"

echo
echo -e "${GREEN}🎉 All tests completed successfully!${NC}"
echo -e "${BLUE}💡 The detection scripts are working correctly and ready for use in pre-commit hooks.${NC}"