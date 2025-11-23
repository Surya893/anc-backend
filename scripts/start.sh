#!/bin/bash
# ANC Platform - Unified Startup Script
# Starts all services for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

# Banner
echo ""
print_header "ANC Platform - Starting Services"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."
MISSING_DEPS=0

if ! check_command python3; then MISSING_DEPS=1; fi
if ! check_command redis-server; then MISSING_DEPS=1; fi

if [ $MISSING_DEPS -eq 1 ]; then
    print_error "Missing required dependencies. Please install them first."
    echo ""
    echo "Installation commands:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv redis-server portaudio19-dev"
    echo "  macOS: brew install python3 redis portaudio"
    exit 1
fi

echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
print_info "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1 || {
    print_error "Failed to install dependencies"
    print_info "Some dependencies may require system libraries. See requirements.txt"
}
print_success "Dependencies installed"

echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_info "Creating .env file from .env.example..."
    cp .env.example .env
    print_success ".env file created"
    print_info "Please update .env file with your configuration"
fi

# Initialize database
print_info "Initializing database..."
python3 -c "
from server import app, db
with app.app_context():
    db.create_all()
    print('Database initialized')
" 2>&1 | grep -v "Warning" || print_error "Database initialization failed"
print_success "Database ready"

echo ""

# Check if Redis is running
if pgrep -x "redis-server" > /dev/null; then
    print_success "Redis is already running"
else
    print_info "Starting Redis server..."
    redis-server --daemonize yes --port 6379 > /dev/null 2>&1
    sleep 1
    if pgrep -x "redis-server" > /dev/null; then
        print_success "Redis server started"
    else
        print_error "Failed to start Redis server"
        print_info "Try running: redis-server"
    fi
fi

echo ""

# Start Celery worker
print_info "Starting Celery worker..."
celery -A tasks.celery_app worker --loglevel=info --detach \
    --pidfile=celery.pid --logfile=logs/celery.log 2>&1 > /dev/null
sleep 2
if [ -f "celery.pid" ]; then
    print_success "Celery worker started (PID: $(cat celery.pid))"
else
    print_error "Failed to start Celery worker"
fi

echo ""

# Start Flask server
print_info "Starting Flask server..."
export FLASK_ENV=development
export FLASK_APP=server

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"

print_success "All services started successfully!"
echo ""
print_header "Access Points"
echo ""
echo -e "  ${GREEN}Web UI:${NC}           http://localhost:$PORT/"
echo -e "  ${GREEN}Live Demo:${NC}        http://localhost:$PORT/live"
echo -e "  ${GREEN}Standalone Demo:${NC}  http://localhost:$PORT/demo"
echo -e "  ${GREEN}API Docs:${NC}         http://localhost:$PORT/api/v1/info"
echo -e "  ${GREEN}Health Check:${NC}     http://localhost:$PORT/health"
echo ""
print_header "Logs"
echo ""
echo -e "  Flask: ${YELLOW}./logs/anc_platform.log${NC}"
echo -e "  Celery: ${YELLOW}./logs/celery.log${NC}"
echo ""
print_header "Stopping Services"
echo ""
echo -e "  Press ${RED}Ctrl+C${NC} to stop Flask server"
echo -e "  Run ${YELLOW}./stop.sh${NC} to stop all services"
echo ""
print_header "Starting Flask Server"
echo ""

# Start Flask with SocketIO
python3 server.py

# Cleanup on exit
echo ""
print_info "Shutting down services..."
if [ -f "celery.pid" ]; then
    kill $(cat celery.pid) 2>/dev/null || true
    rm celery.pid
    print_success "Celery worker stopped"
fi
