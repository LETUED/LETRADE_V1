#!/bin/bash

# =============================================================================
# Letrade_v1 New Feature Development Automation Script
# =============================================================================

set -e

FEATURE_NAME=$1
if [ -z "$FEATURE_NAME" ]; then
    echo "❌ Error: Feature name is required"
    echo ""
    echo "Usage: ./scripts/new-feature.sh <feature-name>"
    echo ""
    echo "Examples:"
    echo "  ./scripts/new-feature.sh core-engine-skeleton"
    echo "  ./scripts/new-feature.sh ma-crossover-strategy"
    echo "  ./scripts/new-feature.sh telegram-notifications"
    echo "  ./scripts/new-feature.sh risk-management"
    exit 1
fi

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} ✅ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} ⚠️ $1"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')]${NC} ❌ $1"
}

# Validate feature name format
if [[ ! "$FEATURE_NAME" =~ ^[a-z0-9-]+$ ]]; then
    log_error "Feature name must contain only lowercase letters, numbers, and hyphens"
    exit 1
fi

log "🚀 Starting new feature development: $FEATURE_NAME"

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]] || [[ ! -d "src" ]]; then
    log_error "This script must be run from the project root directory"
    exit 1
fi

# Sync with latest dev branch
log "🔄 Syncing with latest dev branch..."
git checkout dev
git pull origin dev

# Check if branch already exists
if git branch --list | grep -q "feature/$FEATURE_NAME"; then
    log_error "Branch feature/$FEATURE_NAME already exists"
    exit 1
fi

# Create new feature branch
log "🌱 Creating new feature branch..."
git checkout -b "feature/$FEATURE_NAME"

# Convert feature name to Python module name
MODULE_NAME=${FEATURE_NAME//-/_}

# Create directory structure
log "📁 Creating directory structure..."
mkdir -p "src/${MODULE_NAME}"
mkdir -p "tests/unit"
mkdir -p "tests/integration"

# Create basic source files
log "📄 Creating basic source files..."

# __init__.py
cat > "src/${MODULE_NAME}/__init__.py" << EOF
"""${FEATURE_NAME} module for Letrade_v1 trading system."""

__version__ = "0.1.0"
__author__ = "Letrade Team"
EOF

# main.py with basic structure
cat > "src/${MODULE_NAME}/main.py" << EOF
"""${FEATURE_NAME} main module.

This module implements the core functionality for ${FEATURE_NAME}.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ${MODULE_NAME^}:
    """Main class for ${FEATURE_NAME} functionality."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ${MODULE_NAME^}.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.status = "initialized"
        logger.info(f"${MODULE_NAME^} initialized with config: {self.config}")
    
    def start(self) -> bool:
        """Start the ${MODULE_NAME^} service.
        
        Returns:
            True if started successfully, False otherwise
        """
        logger.info(f"Starting ${MODULE_NAME^}...")
        # TODO: Implement startup logic
        self.status = "running"
        return True
    
    def stop(self) -> bool:
        """Stop the ${MODULE_NAME^} service.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        logger.info(f"Stopping ${MODULE_NAME^}...")
        # TODO: Implement shutdown logic
        self.status = "stopped"
        return True
    
    def get_status(self) -> str:
        """Get current status.
        
        Returns:
            Current status string
        """
        return self.status


def main():
    """Main entry point for ${MODULE_NAME^}."""
    logging.basicConfig(level=logging.INFO)
    
    service = ${MODULE_NAME^}()
    
    try:
        service.start()
        logger.info(f"${MODULE_NAME^} is running...")
        # TODO: Add main application logic
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Error in ${MODULE_NAME^}: {e}")
    finally:
        service.stop()
        logger.info(f"${MODULE_NAME^} shutdown complete")


if __name__ == "__main__":
    main()
EOF

# Create comprehensive unit test file
log "🧪 Creating test files..."
cat > "tests/unit/test_${MODULE_NAME}.py" << EOF
"""Unit tests for ${MODULE_NAME} module."""

import pytest
from unittest.mock import Mock, patch

from src.${MODULE_NAME}.main import ${MODULE_NAME^}


class Test${MODULE_NAME^}:
    """Test cases for ${MODULE_NAME^} class."""
    
    def test_initialization(self):
        """Test ${MODULE_NAME^} initialization."""
        service = ${MODULE_NAME^}()
        assert service is not None
        assert service.status == "initialized"
        assert service.config == {}
    
    def test_initialization_with_config(self):
        """Test ${MODULE_NAME^} initialization with config."""
        config = {"test": "value"}
        service = ${MODULE_NAME^}(config=config)
        assert service.config == config
    
    def test_start_service(self):
        """Test starting the service."""
        service = ${MODULE_NAME^}()
        result = service.start()
        assert result is True
        assert service.status == "running"
    
    def test_stop_service(self):
        """Test stopping the service."""
        service = ${MODULE_NAME^}()
        service.start()
        result = service.stop()
        assert result is True
        assert service.status == "stopped"
    
    def test_get_status(self):
        """Test status retrieval."""
        service = ${MODULE_NAME^}()
        assert service.get_status() == "initialized"
        
        service.start()
        assert service.get_status() == "running"
        
        service.stop()
        assert service.get_status() == "stopped"
    
    @patch('src.${MODULE_NAME}.main.logger')
    def test_logging(self, mock_logger):
        """Test that proper logging occurs."""
        service = ${MODULE_NAME^}()
        service.start()
        
        # Verify logging calls
        mock_logger.info.assert_called()
        assert any("initialized" in str(call) for call in mock_logger.info.call_args_list)


class Test${MODULE_NAME^}Integration:
    """Integration test cases for ${MODULE_NAME^}."""
    
    def test_service_lifecycle(self):
        """Test complete service lifecycle."""
        service = ${MODULE_NAME^}()
        
        # Test initialization
        assert service.status == "initialized"
        
        # Test start
        assert service.start() is True
        assert service.status == "running"
        
        # Test stop
        assert service.stop() is True
        assert service.status == "stopped"


# Trading system specific tests (if applicable)
class Test${MODULE_NAME^}TradingSafety:
    """Trading system safety tests."""
    
    def test_no_hardcoded_secrets(self):
        """Ensure no hardcoded API keys or secrets."""
        # This test will be enhanced by CI security checks
        # but we include it here for early detection
        import inspect
        import src.${MODULE_NAME}.main as module
        
        source = inspect.getsource(module)
        
        # Check for common secret patterns
        forbidden_patterns = [
            'api_key=',
            'secret=',
            'password=',
            'binance_key',
            'coinbase_key'
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in source.lower(), f"Hardcoded secret pattern detected: {pattern}"
    
    def test_error_handling_robustness(self):
        """Test that errors don't crash the system."""
        service = ${MODULE_NAME^}()
        
        # Test graceful handling of invalid config
        with patch.object(service, 'start', side_effect=Exception("Test error")):
            # Should not raise exception
            try:
                service.start()
            except Exception:
                # If exception occurs, it should be caught and logged
                pass
        
        # Service should still be in a valid state
        assert hasattr(service, 'status')


# Performance tests (if applicable)
@pytest.mark.performance
class Test${MODULE_NAME^}Performance:
    """Performance tests for ${MODULE_NAME^}."""
    
    def test_initialization_performance(self, benchmark):
        """Test initialization performance."""
        def create_service():
            return ${MODULE_NAME^}()
        
        result = benchmark(create_service)
        assert result is not None
    
    def test_start_stop_performance(self, benchmark):
        """Test start/stop performance."""
        service = ${MODULE_NAME^}()
        
        def start_stop_cycle():
            service.start()
            service.stop()
            return service.status
        
        result = benchmark(start_stop_cycle)
        assert result == "stopped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
EOF

# Create integration test file
cat > "tests/integration/test_${MODULE_NAME}_integration.py" << EOF
"""Integration tests for ${MODULE_NAME} module."""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.${MODULE_NAME}.main import ${MODULE_NAME^}


@pytest.mark.integration
class Test${MODULE_NAME^}Integration:
    """Integration tests for ${MODULE_NAME^}."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = ${MODULE_NAME^}()
    
    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self.service, 'stop'):
            self.service.stop()
    
    def test_service_integration_with_config(self):
        """Test service integration with configuration."""
        config = {
            "log_level": "INFO",
            "timeout": 30,
            "max_retries": 3
        }
        
        service = ${MODULE_NAME^}(config=config)
        assert service.start() is True
        assert service.get_status() == "running"
        assert service.stop() is True
    
    @pytest.mark.slow
    def test_service_under_load(self):
        """Test service behavior under simulated load."""
        service = ${MODULE_NAME^}()
        service.start()
        
        # Simulate multiple operations
        for i in range(100):
            status = service.get_status()
            assert status == "running"
        
        service.stop()
    
    def test_service_restart_capability(self):
        """Test service restart functionality."""
        service = ${MODULE_NAME^}()
        
        # Start -> Stop -> Start again
        assert service.start() is True
        assert service.stop() is True
        assert service.start() is True  # Should be able to restart
        assert service.get_status() == "running"
        
        service.stop()


# Database integration tests (if applicable)
@pytest.mark.database
class Test${MODULE_NAME^}DatabaseIntegration:
    """Database integration tests."""
    
    @pytest.mark.skipif(
        condition=True,  # Skip until database connection is implemented
        reason="Database integration not yet implemented"
    )
    def test_database_connection(self):
        """Test database connectivity."""
        # TODO: Implement when database integration is added
        pass


# Message bus integration tests (if applicable)
@pytest.mark.messagebus
class Test${MODULE_NAME^}MessageBusIntegration:
    """Message bus integration tests."""
    
    @pytest.mark.skipif(
        condition=True,  # Skip until message bus is implemented
        reason="Message bus integration not yet implemented"
    )
    def test_message_publishing(self):
        """Test message publishing capability."""
        # TODO: Implement when RabbitMQ integration is added
        pass
    
    @pytest.mark.skipif(
        condition=True,  # Skip until message bus is implemented
        reason="Message bus integration not yet implemented"
    )
    def test_message_consumption(self):
        """Test message consumption capability."""
        # TODO: Implement when RabbitMQ integration is added
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
EOF

# Create initial documentation
log "📖 Creating documentation..."
mkdir -p "docs/${MODULE_NAME}"
cat > "docs/${MODULE_NAME}/README.md" << EOF
# ${FEATURE_NAME^} Module

## Overview

The ${FEATURE_NAME} module implements [brief description of functionality].

## Architecture

[Describe the module's architecture and how it fits into the overall system]

## Usage

\`\`\`python
from src.${MODULE_NAME}.main import ${MODULE_NAME^}

# Initialize the service
service = ${MODULE_NAME^}(config={
    "option1": "value1",
    "option2": "value2"
})

# Start the service
service.start()

# Check status
print(service.get_status())

# Stop the service
service.stop()
\`\`\`

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| option1   | str  | None    | Description of option1 |
| option2   | int  | 0       | Description of option2 |

## API Reference

### ${MODULE_NAME^}

Main class for ${FEATURE_NAME} functionality.

#### Methods

- \`__init__(config: Optional[Dict[str, Any]] = None)\`: Initialize the service
- \`start() -> bool\`: Start the service
- \`stop() -> bool\`: Stop the service  
- \`get_status() -> str\`: Get current status

## Testing

Run tests for this module:

\`\`\`bash
# Unit tests
pytest tests/unit/test_${MODULE_NAME}.py -v

# Integration tests
pytest tests/integration/test_${MODULE_NAME}_integration.py -v

# All tests for this module
pytest tests/ -k "${MODULE_NAME}" -v
\`\`\`

## Development

### Adding New Features

1. Write failing tests first
2. Implement minimum code to pass tests
3. Refactor and improve
4. Update documentation

### Performance Considerations

[Add any performance notes specific to this module]

### Security Considerations

[Add any security notes specific to this module]

## TODO

- [ ] Implement core functionality
- [ ] Add error handling
- [ ] Add logging
- [ ] Add configuration validation
- [ ] Add performance monitoring
- [ ] Add integration with other modules

## Contributing

See the main project [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
EOF

# Initial commit for the feature
log "💾 Creating initial commit..."
git add .
git commit -m "feat: initialize ${FEATURE_NAME} module structure

🚀 Feature Setup:
- Add basic module structure for ${MODULE_NAME}
- Implement initial ${MODULE_NAME^} class with lifecycle management
- Add comprehensive unit and integration test templates
- Include trading system safety test patterns
- Add module documentation template

📝 Files Created:
- src/${MODULE_NAME}/main.py: Core implementation
- tests/unit/test_${MODULE_NAME}.py: Unit tests
- tests/integration/test_${MODULE_NAME}_integration.py: Integration tests
- docs/${MODULE_NAME}/README.md: Module documentation

🧪 Test Coverage:
- Basic functionality tests
- Error handling tests
- Performance test templates
- Trading system safety checks

🔜 Next Steps:
1. Write failing tests for specific requirements
2. Implement actual functionality
3. Run: ./scripts/test-and-commit.sh"

log_success "Feature branch ready: feature/$FEATURE_NAME"
log_success "Module created: ${MODULE_NAME}"

echo ""
echo "📝 Next steps:"
echo "  1. Write failing tests in tests/unit/test_${MODULE_NAME}.py"
echo "  2. Implement minimum code to pass tests in src/${MODULE_NAME}/main.py"
echo "  3. Run: ./scripts/test-and-commit.sh"
echo "  4. Iterate: test -> implement -> commit"
echo "  5. When complete: git push -u origin feature/$FEATURE_NAME"
echo ""
echo "🔗 Useful commands:"
echo "  # Run tests for this module only"
echo "  pytest tests/ -k \"${MODULE_NAME}\" -v"
echo ""
echo "  # Run with coverage"
echo "  pytest tests/unit/test_${MODULE_NAME}.py --cov=src.${MODULE_NAME} --cov-report=term-missing"
echo ""
echo "  # Run all quality checks"
echo "  ./scripts/test-and-commit.sh"
echo ""
log_success "🎉 Ready to start developing ${FEATURE_NAME}!"