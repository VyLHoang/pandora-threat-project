#!/bin/bash
##############################################################################
# Pandora Deployment Test Script
# Test all services after deployment
##############################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "========================================================================"
echo "  PANDORA DEPLOYMENT VERIFICATION"
echo "========================================================================"
echo ""

PASSED=0
FAILED=0

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Testing $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null)
    
    if [ "$response" -eq "$expected" ] || [ "$response" -eq "200" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $response)"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC} (HTTP $response, expected $expected)"
        ((FAILED++))
    fi
}

# Function to test service
test_service() {
    local service=$1
    local name=$2
    
    echo -n "Testing $name... "
    
    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}RUNNING${NC}"
        ((PASSED++))
    else
        echo -e "${RED}STOPPED${NC}"
        ((FAILED++))
    fi
}

# Function to test docker container
test_docker() {
    local container=$1
    local name=$2
    
    echo -n "Testing $name... "
    
    if docker ps | grep -q "$container"; then
        echo -e "${GREEN}RUNNING${NC}"
        ((PASSED++))
    else
        echo -e "${RED}NOT FOUND${NC}"
        ((FAILED++))
    fi
}

echo -e "${CYAN}=== Systemd Services ===${NC}"
test_service "pandora-backend-admin.service" "Backend Admin"
test_service "pandora-backend-user.service" "Backend User"
test_service "pandora-central-monitor.service" "Central Monitor"
test_service "pandora-ids.service" "IDS Engine"
test_service "pandora-http-80.service" "HTTP Server"
test_service "pandora-https-443.service" "HTTPS Server"

echo ""
echo -e "${CYAN}=== Docker Containers ===${NC}"
test_docker "postgres" "PostgreSQL (Shared)"
test_docker "postgres-admin" "PostgreSQL (Admin)"
test_docker "postgres-user" "PostgreSQL (User)"
test_docker "redis" "Redis (Shared)"
test_docker "redis-admin" "Redis (Admin)"
test_docker "redis-user" "Redis (User)"
test_docker "elasticsearch" "Elasticsearch"
test_docker "kibana" "Kibana"

echo ""
echo -e "${CYAN}=== HTTP Endpoints ===${NC}"
test_endpoint "HTTP (Port 80)" "http://localhost" "301"
test_endpoint "HTTPS (Port 443)" "https://localhost" "200"
test_endpoint "Backend Admin Health" "http://localhost:9000/api/v1/health" "200"
test_endpoint "Backend User Health" "http://localhost:8000/api/v1/health" "200"
test_endpoint "Central Monitor" "http://localhost:22002" "200"
test_endpoint "Elasticsearch" "http://localhost:9200" "200"
test_endpoint "Kibana" "http://localhost:5601" "200"

echo ""
echo -e "${CYAN}=== Port Listening ===${NC}"

check_port() {
    local port=$1
    local name=$2
    
    echo -n "Port $port ($name)... "
    
    if sudo netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "${GREEN}LISTENING${NC}"
        ((PASSED++))
    else
        echo -e "${RED}NOT LISTENING${NC}"
        ((FAILED++))
    fi
}

check_port "80" "HTTP"
check_port "443" "HTTPS"
check_port "8000" "Backend User"
check_port "9000" "Backend Admin"
check_port "22002" "Central Monitor"
check_port "5432" "PostgreSQL"
check_port "6379" "Redis"
check_port "9200" "Elasticsearch"
check_port "5601" "Kibana"

echo ""
echo "========================================================================"
echo -e "  ${GREEN}PASSED: $PASSED${NC} | ${RED}FAILED: $FAILED${NC}"
echo "========================================================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED! Deployment successful!${NC}"
    echo ""
    echo "Access your system:"
    echo "  • Website: https://172.235.245.60"
    echo "  • Central Monitor: http://172.235.245.60:22002"
    echo "  • Admin API: http://172.235.245.60:9000/docs"
    echo "  • User API: http://172.235.245.60:8000/docs"
    echo "  • Kibana: http://172.235.245.60:5601"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED!${NC}"
    echo ""
    echo "Debug commands:"
    echo "  • Check services: sudo systemctl status pandora-*"
    echo "  • Check logs: sudo journalctl -u pandora-backend-admin -n 50"
    echo "  • Check docker: docker ps -a"
    echo ""
    exit 1
fi

