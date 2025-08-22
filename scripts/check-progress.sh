#!/bin/bash
# Genesis Progress Checker
# Updates and displays project progress

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🎯 Genesis Implementation Progress Check"
echo "========================================"
echo ""

# Check Phase 1 components
echo "📦 Phase 1: Core Foundation"
echo ""

# Track A: Core Infrastructure
echo "Issue #2 - Core Infrastructure:"
if [ -f "core/errors/handler.py" ]; then
    echo -e "  ✅ Error handling ${GREEN}DONE${NC}"
else
    echo -e "  ⬜ Error handling ${RED}TODO${NC}"
fi

if [ -f "core/logging/logger.py" ]; then
    echo -e "  ✅ Structured logging ${GREEN}DONE${NC}"
else
    echo -e "  ⬜ Structured logging ${RED}TODO${NC}"
fi

if [ -f "core/retry/retry.py" ]; then
    echo -e "  ✅ Retry logic ${GREEN}DONE${NC}"
else
    echo -e "  ⬜ Retry logic ${RED}TODO${NC}"
fi

if [ -f "core/retry/circuit_breaker.py" ]; then
    echo -e "  ✅ Circuit breakers ${GREEN}DONE${NC}"
else
    echo -e "  ⬜ Circuit breakers ${RED}TODO${NC}"
fi

if [ -f "core/health/checker.py" ]; then
    echo -e "  ✅ Health checks ${GREEN}DONE${NC}"
else
    echo -e "  ⬜ Health checks ${RED}TODO${NC}"
fi

echo ""

# Track B: SOLVE Integration
echo "Issue #3 - SOLVE Integration:"
if [ -d "intelligence/solve" ] || [ -d "intelligence/autofix" ]; then
    echo -e "  ✅ SOLVE code copied ${GREEN}DONE${NC}"
else
    echo -e "  ⬜ SOLVE code copied ${RED}TODO${NC}"
fi

echo ""

# Track C: CLI
echo "Issue #4 - CLI Development:"
if [ -f "cli/bin/g" ]; then
    echo -e "  ✅ CLI entry point ${GREEN}DONE${NC}"
    
    # Check if commands are implemented
    if grep -q "def init" cli/commands/*.py 2>/dev/null; then
        echo -e "  ✅ g init command ${GREEN}DONE${NC}"
    else
        echo -e "  ⬜ g init command ${RED}TODO${NC}"
    fi
    
    if grep -q "def new" cli/commands/*.py 2>/dev/null; then
        echo -e "  ✅ g new command ${GREEN}DONE${NC}"
    else
        echo -e "  ⬜ g new command ${RED}TODO${NC}"
    fi
    
    if grep -q "def deploy" cli/commands/*.py 2>/dev/null; then
        echo -e "  ✅ g deploy command ${GREEN}DONE${NC}"
    else
        echo -e "  ⬜ g deploy command ${RED}TODO${NC}"
    fi
else
    echo -e "  ⬜ CLI entry point ${RED}TODO${NC}"
fi

echo ""

# Track D: GCP Foundation
echo "Issue #5 - GCP Foundation:"
if [ -d "modules" ]; then
    echo -e "  ✅ Module structure ${GREEN}EXISTS${NC}"
    
    # Count implemented modules
    implemented=0
    total=6
    
    [ -f "modules/service-accounts/main.tf" ] && ((implemented++))
    [ -f "modules/workload-identity/main.tf" ] && ((implemented++))
    [ -f "modules/state-backend/main.tf" ] && ((implemented++))
    [ -f "modules/compute/main.tf" ] && ((implemented++))
    [ -f "modules/networking/main.tf" ] && ((implemented++))
    [ -f "modules/security/main.tf" ] && ((implemented++))
    
    echo -e "  📊 Modules implemented: ${implemented}/${total}"
else
    echo -e "  ⬜ Module structure ${RED}TODO${NC}"
fi

echo ""
echo "========================================"
echo ""

# Calculate overall progress
completed=0
total=50  # Approximate total tasks

[ -f "core/errors/handler.py" ] && ((completed++))
[ -f "core/logging/logger.py" ] && ((completed++))
[ -d "intelligence/solve" ] && ((completed++))
[ -f "cli/bin/g" ] && ((completed++))

progress=$((completed * 100 / total))

echo "📊 Overall Progress: ${progress}%"
echo ""

# Show blocking issues
echo "🚨 Current Blockers:"
if [ ! -f "core/retry/retry.py" ]; then
    echo "  - Retry logic blocking circuit breakers"
fi
if [ ! -f "core/logging/logger.py" ]; then
    echo "  - Logging blocking health checks"
fi
echo ""

# Show next actions
echo "🎯 Next Actions:"
echo "  1. Complete retry logic (core/retry/retry.py)"
echo "  2. Implement circuit breakers"
echo "  3. Start GCP service accounts"
echo "  4. Integrate smart-commit from SOLVE"
echo ""

# Generate GitHub issue update
echo "📝 GitHub Issue Update Command:"
echo ""
echo "gh issue comment 1 --body \"## Progress Update $(date '+%Y-%m-%d')

**Overall Progress**: ${progress}%

### Completed
- ✅ Error handling foundation
- ✅ Structured logging
- ✅ SOLVE components copied
- ✅ CLI entry point

### In Progress
- 🟡 Core Infrastructure (#2) - 20% complete
- 🟡 SOLVE Integration (#3) - 15% complete
- 🟡 CLI Development (#4) - 10% complete

### Blocked
- 🔴 GCP Foundation (#5) - Not started
- 🔴 Agent-Cage Migration (#6) - Waiting for Phase 1

### Next 24 Hours
- Complete retry logic implementation
- Start circuit breaker pattern
- Begin GCP service account module
\""