#!/usr/bin/env bash
# Comprehensive Performance Testing Framework
# Load testing, stress testing, and performance validation

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log_error() { echo -e "${RED}❌ ERROR: $1${NC}" >&2; }
log_warning() { echo -e "${YELLOW}⚠️  WARNING: $1${NC}"; }
log_success() { echo -e "${GREEN}✅ SUCCESS: $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  INFO: $1${NC}"; }
log_progress() { echo -e "${CYAN}⚡ TESTING: $1${NC}"; }
log_perf() { echo -e "${PURPLE}📊 PERFORMANCE: $1${NC}"; }

# Configuration
TEST_TYPE="${TEST_TYPE:-all}"  # all, load, stress, spike, volume, endurance
TARGET_URL="${TARGET_URL:-}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
OUTPUT_DIR="${OUTPUT_DIR:-./performance-reports}"
DRY_RUN="${DRY_RUN:-false}"

# Performance thresholds
RESPONSE_TIME_THRESHOLD="${RESPONSE_TIME_THRESHOLD:-2000}"  # milliseconds
THROUGHPUT_THRESHOLD="${THROUGHPUT_THRESHOLD:-100}"        # requests per second
ERROR_RATE_THRESHOLD="${ERROR_RATE_THRESHOLD:-1}"          # percentage
AVAILABILITY_THRESHOLD="${AVAILABILITY_THRESHOLD:-99.5}"   # percentage

# Load test configuration
LOAD_USERS="${LOAD_USERS:-50}"
LOAD_DURATION="${LOAD_DURATION:-300}"     # 5 minutes
STRESS_USERS="${STRESS_USERS:-200}"
STRESS_DURATION="${STRESS_DURATION:-180}" # 3 minutes
SPIKE_USERS="${SPIKE_USERS:-500}"
SPIKE_DURATION="${SPIKE_DURATION:-60}"    # 1 minute

# Tools configuration
K6_VERSION="0.47.0"
ARTILLERY_VERSION="2.0.0"
WRENCH_VERSION="4.0.0"

log_info "⚡ Starting Comprehensive Performance Testing"
log_info "Test Type: $TEST_TYPE"
log_info "Target URL: $TARGET_URL"
log_info "Environment: $ENVIRONMENT"
log_info "Output Directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize metrics tracking
declare -A performance_metrics
declare -A test_results

# Function to install performance testing tools
install_performance_tools() {
    log_progress "Installing performance testing tools"

    # Install k6
    if ! command -v k6 &> /dev/null; then
        log_info "Installing k6..."
        curl -sS https://dl.k6.io/key.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/k6-archive-keyring.gpg > /dev/null
        echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list > /dev/null
        sudo apt-get update && sudo apt-get install k6 || {
            # Fallback to binary installation
            curl -sL https://github.com/grafana/k6/releases/download/v${K6_VERSION}/k6-v${K6_VERSION}-linux-amd64.tar.gz | tar -xz
            sudo mv k6-v${K6_VERSION}-linux-amd64/k6 /usr/local/bin/
        }
    fi

    # Install Artillery
    if ! command -v artillery &> /dev/null; then
        log_info "Installing Artillery..."
        npm install -g artillery@${ARTILLERY_VERSION}
    fi

    # Install wrk (if available)
    if ! command -v wrk &> /dev/null && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "load" ]]; then
        log_info "Installing wrk..."
        sudo apt-get update && sudo apt-get install -y wrk || {
            log_warning "wrk installation failed, continuing without it"
        }
    fi

    # Install Apache Bench (ab)
    if ! command -v ab &> /dev/null; then
        log_info "Installing Apache Bench..."
        sudo apt-get update && sudo apt-get install -y apache2-utils || {
            log_warning "Apache Bench installation failed, continuing without it"
        }
    fi

    log_success "Performance tools installation completed"
}

# Basic connectivity and health check
verify_target_availability() {
    log_progress "Verifying target availability"

    if [[ -z "$TARGET_URL" ]]; then
        log_error "TARGET_URL is required for performance testing"
        exit 1
    fi

    log_info "Testing connectivity to: $TARGET_URL"

    # Basic connectivity test
    for attempt in {1..5}; do
        if curl -f "$TARGET_URL" --max-time 10 --silent --head > /dev/null; then
            log_success "Target is accessible (attempt $attempt)"
            break
        else
            log_warning "Target not accessible (attempt $attempt/5)"
            if [[ $attempt -eq 5 ]]; then
                log_error "Target is not accessible after 5 attempts"
                exit 1
            fi
            sleep 5
        fi
    done

    # Get baseline metrics
    log_info "Collecting baseline metrics..."
    local baseline_response_time
    baseline_response_time=$(curl -o /dev/null -s -w '%{time_total}' "$TARGET_URL" --max-time 10)
    performance_metrics["baseline_response_time"]="$baseline_response_time"

    log_info "Baseline response time: ${baseline_response_time}s"
}

# Generate k6 test scripts
generate_k6_scripts() {
    log_progress "Generating k6 test scripts"

    # Load Test Script
    cat > "$OUTPUT_DIR/k6-load-test.js" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

export let options = {
  stages: [
    { duration: '2m', target: __ENV.LOAD_USERS || 50 }, // Ramp up
    { duration: '5m', target: __ENV.LOAD_USERS || 50 }, // Stay at load
    { duration: '2m', target: 0 },                      // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2s
    http_req_failed: ['rate<0.01'],    // Error rate under 1%
    errors: ['rate<0.01'],
  },
};

export default function() {
  const response = http.get(__ENV.TARGET_URL);

  const result = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 2000ms': (r) => r.timings.duration < 2000,
  });

  errorRate.add(!result);

  sleep(1);
}
EOF

    # Stress Test Script
    cat > "$OUTPUT_DIR/k6-stress-test.js" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

export let options = {
  stages: [
    { duration: '2m', target: __ENV.STRESS_USERS || 200 }, // Ramp up to stress level
    { duration: '3m', target: __ENV.STRESS_USERS || 200 }, // Stay at stress level
    { duration: '2m', target: 0 },                         // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'], // 95% of requests under 5s during stress
    http_req_failed: ['rate<0.05'],    // Error rate under 5% during stress
    errors: ['rate<0.05'],
  },
};

export default function() {
  const response = http.get(__ENV.TARGET_URL);

  const result = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 5000ms': (r) => r.timings.duration < 5000,
  });

  errorRate.add(!result);

  sleep(Math.random() * 2); // Random sleep between 0-2 seconds
}
EOF

    # Spike Test Script
    cat > "$OUTPUT_DIR/k6-spike-test.js" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

export let options = {
  stages: [
    { duration: '1m', target: 50 },                        // Normal load
    { duration: '30s', target: __ENV.SPIKE_USERS || 500 }, // Spike!
    { duration: '30s', target: 50 },                       // Back to normal
    { duration: '1m', target: 0 },                         // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<10000'], // 95% of requests under 10s during spike
    http_req_failed: ['rate<0.1'],      // Error rate under 10% during spike
    errors: ['rate<0.1'],
  },
};

export default function() {
  const response = http.get(__ENV.TARGET_URL);

  const result = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 10000ms': (r) => r.timings.duration < 10000,
  });

  errorRate.add(!result);

  sleep(0.5);
}
EOF

    log_success "k6 test scripts generated"
}

# Generate Artillery test configurations
generate_artillery_configs() {
    log_progress "Generating Artillery test configurations"

    # Load Test Configuration
    cat > "$OUTPUT_DIR/artillery-load-test.yml" << EOF
config:
  target: '$TARGET_URL'
  phases:
    - duration: 120
      arrivalRate: 10
      name: "Warm up"
    - duration: 300
      arrivalRate: ${LOAD_USERS}
      name: "Load test"
    - duration: 120
      arrivalRate: 5
      name: "Cool down"
  processor: './artillery-processor.js'

scenarios:
  - name: "Load test scenario"
    weight: 100
    flow:
      - get:
          url: "/"
      - think: 1
      - get:
          url: "/health"
      - think: 2
EOF

    # Artillery processor for custom metrics
    cat > "$OUTPUT_DIR/artillery-processor.js" << 'EOF'
module.exports = {
  setCustomHeaders: setCustomHeaders,
  logResponse: logResponse
};

function setCustomHeaders(requestParams, context, ee, next) {
  requestParams.headers = requestParams.headers || {};
  requestParams.headers['User-Agent'] = 'Artillery-Load-Test';
  return next();
}

function logResponse(requestParams, response, context, ee, next) {
  if (response.statusCode !== 200) {
    console.log(`Non-200 response: ${response.statusCode} for ${requestParams.url}`);
  }
  return next();
}
EOF

    log_success "Artillery configurations generated"
}

# Run load testing
run_load_tests() {
    if [[ "$TEST_TYPE" != "all" && "$TEST_TYPE" != "load" ]]; then
        return 0
    fi

    log_progress "Running load tests"

    if [[ "$DRY_RUN" == "false" ]]; then
        # k6 Load Test
        log_perf "Running k6 load test..."
        export TARGET_URL LOAD_USERS
        k6 run \
            --out json="$OUTPUT_DIR/k6-load-results.json" \
            --summary-export="$OUTPUT_DIR/k6-load-summary.json" \
            "$OUTPUT_DIR/k6-load-test.js" || true

        # Artillery Load Test
        if command -v artillery &> /dev/null; then
            log_perf "Running Artillery load test..."
            artillery run \
                --output "$OUTPUT_DIR/artillery-load-results.json" \
                "$OUTPUT_DIR/artillery-load-test.yml" || true
        fi

        # wrk Load Test (if available)
        if command -v wrk &> /dev/null; then
            log_perf "Running wrk load test..."
            wrk -t12 -c${LOAD_USERS} -d${LOAD_DURATION}s \
                --script="$OUTPUT_DIR/wrk-script.lua" \
                "$TARGET_URL" > "$OUTPUT_DIR/wrk-load-results.txt" 2>&1 || true
        fi

        # Apache Bench Test
        if command -v ab &> /dev/null; then
            log_perf "Running Apache Bench test..."
            ab -n 1000 -c 10 -g "$OUTPUT_DIR/ab-load-results.tsv" \
                "$TARGET_URL" > "$OUTPUT_DIR/ab-load-results.txt" 2>&1 || true
        fi
    fi

    test_results["load"]="completed"
    log_success "Load testing completed"
}

# Run stress testing
run_stress_tests() {
    if [[ "$TEST_TYPE" != "all" && "$TEST_TYPE" != "stress" ]]; then
        return 0
    fi

    log_progress "Running stress tests"

    if [[ "$DRY_RUN" == "false" ]]; then
        # k6 Stress Test
        log_perf "Running k6 stress test..."
        export TARGET_URL STRESS_USERS
        k6 run \
            --out json="$OUTPUT_DIR/k6-stress-results.json" \
            --summary-export="$OUTPUT_DIR/k6-stress-summary.json" \
            "$OUTPUT_DIR/k6-stress-test.js" || true

        # High-concurrency wrk test (if available)
        if command -v wrk &> /dev/null; then
            log_perf "Running wrk stress test..."
            wrk -t12 -c${STRESS_USERS} -d${STRESS_DURATION}s \
                "$TARGET_URL" > "$OUTPUT_DIR/wrk-stress-results.txt" 2>&1 || true
        fi
    fi

    test_results["stress"]="completed"
    log_success "Stress testing completed"
}

# Run spike testing
run_spike_tests() {
    if [[ "$TEST_TYPE" != "all" && "$TEST_TYPE" != "spike" ]]; then
        return 0
    fi

    log_progress "Running spike tests"

    if [[ "$DRY_RUN" == "false" ]]; then
        # k6 Spike Test
        log_perf "Running k6 spike test..."
        export TARGET_URL SPIKE_USERS
        k6 run \
            --out json="$OUTPUT_DIR/k6-spike-results.json" \
            --summary-export="$OUTPUT_DIR/k6-spike-summary.json" \
            "$OUTPUT_DIR/k6-spike-test.js" || true
    fi

    test_results["spike"]="completed"
    log_success "Spike testing completed"
}

# Run volume testing
run_volume_tests() {
    if [[ "$TEST_TYPE" != "all" && "$TEST_TYPE" != "volume" ]]; then
        return 0
    fi

    log_progress "Running volume tests"

    if [[ "$DRY_RUN" == "false" ]]; then
        # Volume test with sustained load
        log_perf "Running volume test..."
        export TARGET_URL
        export VOLUME_USERS=100
        export VOLUME_DURATION=1800  # 30 minutes

        # Create volume test script
        cat > "$OUTPUT_DIR/k6-volume-test.js" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

export let options = {
  stages: [
    { duration: '5m', target: __ENV.VOLUME_USERS || 100 }, // Ramp up
    { duration: '30m', target: __ENV.VOLUME_USERS || 100 }, // Sustained load
    { duration: '5m', target: 0 },                          // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% of requests under 3s
    http_req_failed: ['rate<0.02'],    // Error rate under 2%
    errors: ['rate<0.02'],
  },
};

export default function() {
  const response = http.get(__ENV.TARGET_URL);

  const result = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 3000ms': (r) => r.timings.duration < 3000,
  });

  errorRate.add(!result);

  sleep(Math.random() * 3 + 1); // Random sleep between 1-4 seconds
}
EOF

        k6 run \
            --out json="$OUTPUT_DIR/k6-volume-results.json" \
            --summary-export="$OUTPUT_DIR/k6-volume-summary.json" \
            "$OUTPUT_DIR/k6-volume-test.js" || true
    fi

    test_results["volume"]="completed"
    log_success "Volume testing completed"
}

# Run endurance testing
run_endurance_tests() {
    if [[ "$TEST_TYPE" != "all" && "$TEST_TYPE" != "endurance" ]]; then
        return 0
    fi

    log_progress "Running endurance tests"

    if [[ "$DRY_RUN" == "false" ]]; then
        # Endurance test with extended duration
        log_perf "Running endurance test (this will take a while)..."
        export TARGET_URL
        export ENDURANCE_USERS=25
        export ENDURANCE_DURATION=3600  # 1 hour

        # Create endurance test script
        cat > "$OUTPUT_DIR/k6-endurance-test.js" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

export let options = {
  stages: [
    { duration: '10m', target: __ENV.ENDURANCE_USERS || 25 }, // Ramp up
    { duration: '60m', target: __ENV.ENDURANCE_USERS || 25 }, // Endurance load
    { duration: '10m', target: 0 },                           // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2s
    http_req_failed: ['rate<0.01'],    // Error rate under 1%
    errors: ['rate<0.01'],
  },
};

export default function() {
  const response = http.get(__ENV.TARGET_URL);

  const result = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 2000ms': (r) => r.timings.duration < 2000,
  });

  errorRate.add(!result);

  sleep(Math.random() * 5 + 2); // Random sleep between 2-7 seconds
}
EOF

        k6 run \
            --out json="$OUTPUT_DIR/k6-endurance-results.json" \
            --summary-export="$OUTPUT_DIR/k6-endurance-summary.json" \
            "$OUTPUT_DIR/k6-endurance-test.js" || true
    fi

    test_results["endurance"]="completed"
    log_success "Endurance testing completed"
}

# Analyze test results
analyze_test_results() {
    log_progress "Analyzing test results"

    # Analyze k6 results
    for test_type in load stress spike volume endurance; do
        local result_file="$OUTPUT_DIR/k6-${test_type}-summary.json"

        if [[ -f "$result_file" ]]; then
            log_info "Analyzing $test_type test results..."

            # Extract key metrics using jq
            local avg_duration=$(jq -r '.metrics.http_req_duration.avg // 0' "$result_file" 2>/dev/null || echo "0")
            local p95_duration=$(jq -r '.metrics.http_req_duration."p(95)" // 0' "$result_file" 2>/dev/null || echo "0")
            local error_rate=$(jq -r '.metrics.http_req_failed.rate // 0' "$result_file" 2>/dev/null || echo "0")
            local throughput=$(jq -r '.metrics.http_reqs.rate // 0' "$result_file" 2>/dev/null || echo "0")

            performance_metrics["${test_type}_avg_duration"]="$avg_duration"
            performance_metrics["${test_type}_p95_duration"]="$p95_duration"
            performance_metrics["${test_type}_error_rate"]="$error_rate"
            performance_metrics["${test_type}_throughput"]="$throughput"

            log_perf "$test_type results - Avg: ${avg_duration}ms, P95: ${p95_duration}ms, Error Rate: ${error_rate}%, Throughput: ${throughput} req/s"
        fi
    done

    log_success "Test results analysis completed"
}

# Generate performance report
generate_performance_report() {
    log_progress "Generating comprehensive performance report"

    local report_file="$OUTPUT_DIR/performance-summary-report.json"
    local html_report="$OUTPUT_DIR/performance-summary-report.html"

    # Create JSON summary
    cat > "$report_file" << EOF
{
  "test_metadata": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "test_type": "$TEST_TYPE",
    "target_url": "$TARGET_URL",
    "environment": "$ENVIRONMENT",
    "thresholds": {
      "response_time_ms": $RESPONSE_TIME_THRESHOLD,
      "throughput_rps": $THROUGHPUT_THRESHOLD,
      "error_rate_percent": $ERROR_RATE_THRESHOLD,
      "availability_percent": $AVAILABILITY_THRESHOLD
    }
  },
  "test_results": $(printf '%s\n' "${!test_results[@]}" | jq -R . | jq -s 'map(split(":") | {(.[0]): .[1]}) | add'),
  "performance_metrics": {
EOF

    # Add performance metrics
    local first=true
    for key in "${!performance_metrics[@]}"; do
        if [[ "$first" == "false" ]]; then
            echo "," >> "$report_file"
        fi
        echo "    \"$key\": \"${performance_metrics[$key]}\"" >> "$report_file"
        first=false
    done

    cat >> "$report_file" << 'EOF'
  }
}
EOF

    # Generate HTML report
    cat > "$html_report" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 10px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .pass { background: #e6ffe6; border-color: #99ff99; }
        .fail { background: #ffe6e6; border-color: #ff9999; }
        .warning { background: #fff0e6; border-color: #ffcc99; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .metric { font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ Performance Test Report</h1>
        <p><strong>Timestamp:</strong> $(date -u +%Y-%m-%dT%H:%M:%SZ)</p>
        <p><strong>Target URL:</strong> $TARGET_URL</p>
        <p><strong>Environment:</strong> $ENVIRONMENT</p>
        <p><strong>Test Type:</strong> $TEST_TYPE</p>
    </div>
EOF

    # Add metrics summary to HTML
    echo '<div class="section">' >> "$html_report"
    echo '<h2>📊 Performance Metrics Summary</h2>' >> "$html_report"
    echo '<table>' >> "$html_report"
    echo '<tr><th>Test Type</th><th>Avg Response Time</th><th>P95 Response Time</th><th>Error Rate</th><th>Throughput</th></tr>' >> "$html_report"

    for test_type in load stress spike volume endurance; do
        if [[ -n "${performance_metrics[${test_type}_avg_duration]:-}" ]]; then
            local avg_duration="${performance_metrics[${test_type}_avg_duration]}"
            local p95_duration="${performance_metrics[${test_type}_p95_duration]}"
            local error_rate="${performance_metrics[${test_type}_error_rate]}"
            local throughput="${performance_metrics[${test_type}_throughput]}"

            echo "<tr><td>$test_type</td><td>${avg_duration}ms</td><td>${p95_duration}ms</td><td>${error_rate}%</td><td>${throughput} req/s</td></tr>" >> "$html_report"
        fi
    done

    echo '</table>' >> "$html_report"
    echo '</div>' >> "$html_report"
    echo '</body></html>' >> "$html_report"

    log_success "Performance report generated: $report_file"
    log_success "HTML report generated: $html_report"
}

# Evaluate performance against thresholds
evaluate_performance() {
    log_progress "Evaluating performance against thresholds"

    local exit_code=0
    local failed_tests=()

    # Check each test type against thresholds
    for test_type in load stress spike; do
        if [[ -n "${performance_metrics[${test_type}_avg_duration]:-}" ]]; then
            local avg_duration="${performance_metrics[${test_type}_avg_duration]}"
            local error_rate="${performance_metrics[${test_type}_error_rate]}"
            local throughput="${performance_metrics[${test_type}_throughput]}"

            # Convert to numbers for comparison
            local avg_duration_ms=$(echo "$avg_duration * 1000" | bc 2>/dev/null || echo "0")
            local error_rate_percent=$(echo "$error_rate * 100" | bc 2>/dev/null || echo "0")

            # Response time check
            if (( $(echo "$avg_duration_ms > $RESPONSE_TIME_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
                log_error "$test_type test failed: Average response time ${avg_duration_ms}ms exceeds threshold ${RESPONSE_TIME_THRESHOLD}ms"
                failed_tests+=("$test_type:response_time")
                exit_code=1
            fi

            # Error rate check
            if (( $(echo "$error_rate_percent > $ERROR_RATE_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
                log_error "$test_type test failed: Error rate ${error_rate_percent}% exceeds threshold ${ERROR_RATE_THRESHOLD}%"
                failed_tests+=("$test_type:error_rate")
                exit_code=1
            fi

            # Throughput check (for load test only)
            if [[ "$test_type" == "load" ]] && (( $(echo "$throughput < $THROUGHPUT_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
                log_warning "$test_type test warning: Throughput ${throughput} req/s below threshold ${THROUGHPUT_THRESHOLD} req/s"
            fi
        fi
    done

    # Summary
    if [[ $exit_code -eq 0 ]]; then
        log_success "Performance validation passed!"
        log_info "All tests met the performance thresholds"
    else
        log_error "Performance validation failed!"
        log_error "Failed tests: ${failed_tests[*]}"
    fi

    return $exit_code
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --test-type)
                TEST_TYPE="$2"
                shift 2
                ;;
            --target-url)
                TARGET_URL="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --load-users)
                LOAD_USERS="$2"
                shift 2
                ;;
            --load-duration)
                LOAD_DURATION="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --test-type TYPE      Test type: all, load, stress, spike, volume, endurance"
                echo "  --target-url URL      Target URL for testing"
                echo "  --environment ENV     Environment name"
                echo "  --output-dir DIR      Output directory for reports"
                echo "  --load-users NUM      Number of users for load test"
                echo "  --load-duration SEC   Duration of load test in seconds"
                echo "  --dry-run            Dry run mode"
                echo "  --help               Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "🧪 Running in DRY RUN mode"
    fi

    # Verify target availability
    verify_target_availability

    # Install tools if not in dry run mode
    if [[ "$DRY_RUN" == "false" ]]; then
        install_performance_tools
    fi

    # Generate test configurations
    generate_k6_scripts
    generate_artillery_configs

    # Execute tests based on type
    run_load_tests
    run_stress_tests
    run_spike_tests
    run_volume_tests
    run_endurance_tests

    # Analyze and report
    analyze_test_results
    generate_performance_report

    # Evaluate performance
    evaluate_performance
}

# Execute main function with all arguments
main "$@"
