#!/bin/bash

# GPT Image MCP Server - Development and Deployment Runner
# This script helps you run the server in different modes

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
${CYAN}GPT Image MCP Server Runner${NC}

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    dev                 Run development server with HTTP transport
    stdio               Run with stdio transport for Claude Desktop
    prod                Run production server with Docker Compose
    build               Build Docker images
    test                Run tests
    logs                Show server logs
    stop                Stop all services
    clean               Clean up containers and images
    help                Show this help message

Examples:
    $0 dev              # Start development server on http://localhost:3001
    $0 stdio            # Start stdio server for Claude Desktop
    $0 prod             # Start production deployment
    $0 logs             # View server logs
    $0 test             # Run test suite

Environment Setup:
    Make sure you have .env file with OPENAI_API_KEY configured.
    
Server Access:
    HTTP Transport:     http://localhost:3001
    Redis Commander:    http://localhost:8081 (dev mode with --profile tools)
    Grafana:           http://localhost:3000 (production mode)

EOF
}

check_requirements() {
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if docker-compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if .env file exists
    if [ ! -f .env ]; then
        log_warning ".env file not found. Creating template..."
        cp .env.example .env 2>/dev/null || {
            cat > .env << 'EOF'
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Grafana Configuration
GRAFANA_PASSWORD=admin

# Additional settings (optional)
LOG_LEVEL=INFO
CACHE_ENABLED=true
EOF
        }
        log_warning "Please edit .env file and add your OpenAI API key"
        return 1
    fi

    # Check if OPENAI_API_KEY is set
    if ! grep -q "^OPENAI_API_KEY=sk-" .env 2>/dev/null; then
        log_warning "OPENAI_API_KEY not properly configured in .env file"
        log_info "Please edit .env file and add your OpenAI API key"
        return 1
    fi

    return 0
}

run_dev() {
    log_info "Starting development server with HTTP transport..."
    log_info "Server will be available at: ${CYAN}http://localhost:3001${NC}"
    
    if [ "$1" = "--tools" ]; then
        log_info "Starting with Redis Commander at: ${CYAN}http://localhost:8081${NC}"
        docker-compose -f docker-compose.dev.yml --profile tools up --build
    else
        docker-compose -f docker-compose.dev.yml up --build gpt-image-mcp-dev redis
    fi
}

run_stdio() {
    log_info "Starting server with stdio transport for Claude Desktop..."
    log_warning "This mode is for Claude Desktop integration only"
    
    docker-compose -f docker-compose.dev.yml --profile stdio up --build gpt-image-mcp-stdio redis
}

run_prod() {
    log_info "Starting production server..."
    log_info "Server will be available through Nginx proxy"
    log_info "Grafana monitoring: ${CYAN}http://localhost:3000${NC}"
    
    docker-compose -f docker-compose.prod.yml up --build -d
    
    log_success "Production server started successfully!"
    log_info "View logs with: $0 logs"
}

build_images() {
    log_info "Building Docker images..."
    
    docker-compose -f docker-compose.dev.yml build
    docker-compose -f docker-compose.prod.yml build
    
    log_success "Docker images built successfully!"
}

run_tests() {
    log_info "Running test suite..."
    
    # Check if we have UV installed locally
    if command -v uv &> /dev/null; then
        log_info "Running tests with UV..."
        uv run pytest tests/ -v
    else
        log_info "Running tests in Docker container..."
        docker run --rm -v $(pwd):/app -w /app python:3.11-slim bash -c "
            pip install uv && 
            uv sync && 
            uv run pytest tests/ -v
        "
    fi
}

show_logs() {
    if [ -f docker-compose.prod.yml ] && docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_info "Showing production logs..."
        docker-compose -f docker-compose.prod.yml logs -f gpt-image-mcp
    elif docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
        log_info "Showing development logs..."
        docker-compose -f docker-compose.dev.yml logs -f gpt-image-mcp-dev
    else
        log_warning "No running containers found"
        log_info "Available log files:"
        ls -la logs/ 2>/dev/null || log_info "No log files found"
    fi
}

stop_services() {
    log_info "Stopping all services..."
    
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    docker-compose -f docker-compose.dev.yml --profile stdio down 2>/dev/null || true
    docker-compose -f docker-compose.dev.yml --profile tools down 2>/dev/null || true
    
    log_success "All services stopped"
}

clean_up() {
    log_info "Cleaning up containers and images..."
    
    stop_services
    
    # Remove containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (ask for confirmation)
    read -p "Remove unused volumes? This will delete cached data (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    log_success "Cleanup completed"
}

# Main script logic
case "${1:-help}" in
    "dev")
        check_requirements || exit 1
        run_dev "${2:-}"
        ;;
    "stdio")
        check_requirements || exit 1
        run_stdio
        ;;
    "prod")
        check_requirements || exit 1
        run_prod
        ;;
    "build")
        check_requirements || exit 1
        build_images
        ;;
    "test")
        run_tests
        ;;
    "logs")
        show_logs
        ;;
    "stop")
        stop_services
        ;;
    "clean")
        clean_up
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac