#!/bin/bash

# Stress Test Runner Script for Automation Orchestrator
# Usage: bash run_stress_test.sh [options]
# Options:
#   --host URL           API host (default: http://localhost:8000)
#   --users N            Number of concurrent users (default: 50)
#   --spawn-rate N       Users per second (default: 10)
#   --duration TIME      Test duration (default: 10m)
#   --headless           Run in headless mode
#   --web-ui             Enable web UI (http://localhost:8089)

set -e

# Default values
HOST="http://localhost:8000"
USERS=50
SPAWN_RATE=10
DURATION="10m"
HEADLESS=false
WEB_UI=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host) HOST="$2"; shift 2 ;;
        --users) USERS="$2"; shift 2 ;;
        --spawn-rate) SPAWN_RATE="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        --headless) HEADLESS=true; shift ;;
        --web-ui) WEB_UI=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function banner() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

function check_prerequisites() {
    banner "🔍 Checking Prerequisites"
    
    # Check if locust is installed
    if ! command -v locust &> /dev/null; then
        echo -e "${RED}❌ Locust not installed${NC}"
        echo ""
        echo -e "${YELLOW}Install with: pip install locust${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Locust installed: $(locust --version)${NC}"
    fi
    
    # Check if API is running
    echo "Checking API connectivity..."
    if curl -s "$HOST/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is running and responding${NC}"
    else
        echo -e "${RED}❌ Cannot reach API at $HOST${NC}"
        echo ""
        echo -e "${YELLOW}Make sure the API is running with: docker-compose up -d${NC}"
        exit 1
    fi
}

function system_metrics() {
    echo ""
    echo -e "${CYAN}📊 System Information Before Test:${NC}"
    echo "  Host: $HOST"
    echo "  Simulated Users: $USERS"
    echo "  Spawn Rate: $SPAWN_RATE users/sec"
    echo "  Duration: $DURATION"
    echo ""
}

function run_stress_test() {
    banner "🚀 Starting Stress Test"
    
    CMD="locust -f locustfile.py --host=$HOST --users=$USERS --spawn-rate=$SPAWN_RATE --run-time=$DURATION"
    
    if [ "$HEADLESS" = true ]; then
        CMD="$CMD --headless"
        echo -e "${YELLOW}Running in HEADLESS mode...${NC}"
    elif [ "$WEB_UI" = true ]; then
        echo -e "${YELLOW}Launching Web UI at http://localhost:8089${NC}"
        echo -e "${YELLOW}You can monitor the test in real-time in your browser${NC}"
        echo ""
    else
        CMD="$CMD --headless"
        echo -e "${YELLOW}Running in HEADLESS mode (default)${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}Command: $CMD${NC}"
    echo ""
    
    eval $CMD
}

function api_metrics() {
    banner "📈 API Metrics During Test"
    
    echo "Checking Prometheus metrics endpoint..."
    
    if curl -s "$HOST/metrics" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Metrics available at $HOST/metrics${NC}"
        echo ""
        echo -e "${CYAN}View metrics with: curl $HOST/metrics | grep http_requests${NC}"
    else
        echo -e "${YELLOW}⚠ Metrics endpoint not available${NC}"
    fi
}

function dashboard_info() {
    banner "📊 Monitoring Dashboard"
    
    echo -e "${CYAN}🔗 Access these dashboards during/after test:${NC}"
    echo ""
    echo "  1. Grafana (Metrics Visualization)"
    echo "     URL: http://localhost:3000"
    echo "     Login: admin / admin"
    echo ""
    echo "  2. API Health"
    echo "     Basic: http://localhost:8000/health"
    echo "     Detailed: http://localhost:8000/health/detailed"
    echo ""
    echo "  3. Prometheus (Raw Metrics)"
    echo "     URL: http://localhost:9090"
    echo ""
    echo "  4. Docker System Metrics"
    echo "     Use: docker stats"
    echo ""
}

function post_test_instructions() {
    banner "✅ Test Complete"
    
    echo -e "${CYAN}Review results:${NC}"
    echo ""
    echo "1. Check Grafana dashboard for visualizations"
    echo "2. Review response times and error rates"
    echo "3. Check if auto-scaling triggered (Kubernetes only)"
    echo "4. Monitor database and Redis performance"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo "  - Review memory usage patterns"
    echo "  - Check database connection pool utilization"
    echo "  - Verify error logs in Grafana Loki"
    echo "  - Document baseline metrics for comparison"
    echo ""
}

# ==================== MAIN EXECUTION ====================

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Automation Orchestrator - Local Stress Test Runner    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"

check_prerequisites
system_metrics
api_metrics
dashboard_info

# Confirm before starting
echo ""
echo -e "${YELLOW}Ready to start stress test?${NC}"
echo "Press Enter to continue or Ctrl+C to cancel..."
read

run_stress_test
post_test_instructions
