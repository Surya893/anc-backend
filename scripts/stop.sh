#!/bin/bash
# ANC Platform - Stop All Services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

echo ""
print_info "Stopping ANC Platform services..."
echo ""

# Stop Celery worker
if [ -f "celery.pid" ]; then
    PID=$(cat celery.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        rm celery.pid
        print_success "Celery worker stopped (PID: $PID)"
    else
        rm celery.pid
        print_info "Celery worker was not running"
    fi
else
    # Try to find and kill celery processes
    pkill -f "celery.*worker" && print_success "Celery worker stopped" || print_info "No Celery worker found"
fi

# Stop Flask server
pkill -f "python.*server.py" && print_success "Flask server stopped" || print_info "No Flask server found"

# Stop Redis (optional - only if started by start.sh)
# Uncomment if you want to stop Redis as well
# redis-cli shutdown && print_success "Redis server stopped" || print_info "Redis server not stopped"

echo ""
print_success "All services stopped"
echo ""
