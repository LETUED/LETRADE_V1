# =============================================================================
# Letrade_v1 Production Dockerfile
# Multi-stage build for optimized production image
# =============================================================================

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install build && \
    pip install .

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    ENVIRONMENT=production

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

# Create app directory and set ownership
RUN mkdir -p /app /app/logs /app/data && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser migrations/ ./migrations/
COPY --chown=appuser:appuser scripts/ ./scripts/

# Copy essential files
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser README.md ./

# Create startup script
COPY --chown=appuser:appuser <<'EOF' /app/entrypoint.sh
#!/bin/bash

# =============================================================================
# Letrade_v1 Container Entrypoint Script
# =============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ✅ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ⚠️ $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ❌ $1"
}

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-30}
    
    log "Waiting for $service_name at $host:$port..."
    
    for i in $(seq 1 $timeout); do
        if nc -z "$host" "$port" 2>/dev/null; then
            log_success "$service_name is ready"
            return 0
        fi
        sleep 1
    done
    
    log_error "$service_name is not available after ${timeout}s"
    return 1
}

# Function to check environment variables
check_env_vars() {
    log "Checking required environment variables..."
    
    required_vars=(
        "DATABASE_URL"
        "RABBITMQ_URL"
        "ENVIRONMENT"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "All required environment variables are set"
}

# Function to run health checks
health_check() {
    log "Running health checks..."
    
    # Check Python installation
    if ! python --version; then
        log_error "Python is not available"
        exit 1
    fi
    
    # Check if we can import our main modules
    if ! python -c "import src.core_engine" 2>/dev/null; then
        log_error "Cannot import core_engine module"
        exit 1
    fi
    
    log_success "Health checks passed"
}

# Function to handle graceful shutdown
graceful_shutdown() {
    log "Received shutdown signal, stopping services gracefully..."
    
    if [[ -n "$MAIN_PID" ]]; then
        log "Stopping main process (PID: $MAIN_PID)..."
        kill -TERM "$MAIN_PID" 2>/dev/null || true
        wait "$MAIN_PID" 2>/dev/null || true
    fi
    
    log_success "Graceful shutdown completed"
    exit 0
}

# Set up signal handlers
trap graceful_shutdown SIGTERM SIGINT

# Main execution
main() {
    log "🚀 Starting Letrade_v1 Trading System..."
    log "Environment: $ENVIRONMENT"
    log "Python version: $(python --version)"
    log "Working directory: $(pwd)"
    
    # Check environment variables
    check_env_vars
    
    # Run health checks
    health_check
    
    # Wait for required services
    if [[ "$ENVIRONMENT" != "test" ]]; then
        # Extract database host and port from DATABASE_URL
        if [[ "$DATABASE_URL" =~ postgresql://[^@]+@([^:]+):([0-9]+)/ ]]; then
            DB_HOST="${BASH_REMATCH[1]}"
            DB_PORT="${BASH_REMATCH[2]}"
            wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"
        fi
        
        # Extract RabbitMQ host and port from RABBITMQ_URL
        if [[ "$RABBITMQ_URL" =~ amqp://[^@]+@([^:]+):([0-9]+)/ ]]; then
            RABBITMQ_HOST="${BASH_REMATCH[1]}"
            RABBITMQ_PORT="${BASH_REMATCH[2]}"
            wait_for_service "$RABBITMQ_HOST" "$RABBITMQ_PORT" "RabbitMQ"
        fi
    fi
    
    # Determine which service to run based on LETRADE_SERVICE environment variable
    SERVICE=${LETRADE_SERVICE:-"core-engine"}
    
    case "$SERVICE" in
        "core-engine")
            log "Starting Core Engine..."
            exec python -m src.core_engine.main &
            MAIN_PID=$!
            ;;
        "strategy-worker")
            if [[ -z "$STRATEGY_ID" ]]; then
                log_error "STRATEGY_ID environment variable is required for strategy worker"
                exit 1
            fi
            log "Starting Strategy Worker for strategy $STRATEGY_ID..."
            exec python -m src.strategies.worker --strategy-id "$STRATEGY_ID" &
            MAIN_PID=$!
            ;;
        "capital-manager")
            log "Starting Capital Manager..."
            exec python -m src.capital_manager.main &
            MAIN_PID=$!
            ;;
        "exchange-connector")
            log "Starting Exchange Connector..."
            exec python -m src.exchange_connector.main &
            MAIN_PID=$!
            ;;
        "telegram-bot")
            log "Starting Telegram Bot..."
            exec python -m src.telegram_interface.main &
            MAIN_PID=$!
            ;;
        "cli")
            log "Running CLI command: $*"
            exec python -m src.cli.main "$@"
            ;;
        *)
            log_error "Unknown service: $SERVICE"
            log "Available services: core-engine, strategy-worker, capital-manager, exchange-connector, telegram-bot, cli"
            exit 1
            ;;
    esac
    
    # Wait for the main process
    if [[ -n "$MAIN_PID" ]]; then
        log_success "$SERVICE started successfully (PID: $MAIN_PID)"
        wait "$MAIN_PID"
    fi
}

# Install netcat for service checking
if ! command -v nc >/dev/null 2>&1; then
    apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*
fi

# Run main function
main "$@"
EOF

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Create volume mount points
VOLUME ["/app/logs", "/app/data"]

# Expose ports
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["core-engine"]

# =============================================================================
# Labels for better image management
# =============================================================================
LABEL maintainer="Letrade Team <dev@letrade.com>" \
      version="1.0.0" \
      description="Letrade_v1 Automated Cryptocurrency Trading System" \
      org.opencontainers.image.title="Letrade_v1" \
      org.opencontainers.image.description="Production-grade automated cryptocurrency trading system" \
      org.opencontainers.image.vendor="Letrade" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/your-org/letrade_v1"