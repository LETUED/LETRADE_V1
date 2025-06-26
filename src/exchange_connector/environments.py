"""
Exchange environment configurations for different deployment stages.

Provides testnet and production configurations for Binance API integration
with proper security, rate limiting, and performance settings.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class Environment(Enum):
    """Supported exchange environments."""

    TESTNET = "testnet"
    PRODUCTION = "production"


@dataclass
class ExchangeEnvironmentConfig:
    """Exchange environment configuration."""

    name: str
    base_url: str
    ws_url: str
    sandbox: bool
    rate_limit_buffer: float
    timeout: int
    max_retries: int
    connection_timeout: int
    heartbeat_interval: int

    # Security settings
    require_ip_restriction: bool = False
    require_2fa: bool = False

    # Performance settings
    max_concurrent_requests: int = 10
    request_delay_ms: int = 100

    # Monitoring settings
    enable_detailed_logging: bool = True
    log_api_calls: bool = False

    def to_ccxt_config(self, api_key: str, api_secret: str) -> Dict[str, Any]:
        """Convert to ccxt configuration format."""
        return {
            "apiKey": api_key,
            "secret": api_secret,
            "sandbox": self.sandbox,
            "urls": {"api": self.base_url},
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True,
                "recvWindow": 10000,
            },
            "timeout": self.timeout,
            "enableRateLimit": True,
            "rateLimit": self.request_delay_ms,
        }


# Exchange environment configurations
EXCHANGE_ENVIRONMENTS: Dict[str, ExchangeEnvironmentConfig] = {
    Environment.TESTNET.value: ExchangeEnvironmentConfig(
        name="binance_testnet",
        base_url="https://testnet.binance.vision",
        ws_url="wss://testnet.binance.vision/ws/",
        sandbox=True,
        rate_limit_buffer=0.8,  # 20% buffer for safety
        timeout=30000,  # 30 seconds
        max_retries=3,
        connection_timeout=15000,  # 15 seconds
        heartbeat_interval=30,  # 30 seconds
        # Security (relaxed for testing)
        require_ip_restriction=False,
        require_2fa=False,
        # Performance (more lenient)
        max_concurrent_requests=15,
        request_delay_ms=500,  # 500ms between requests
        # Monitoring (detailed for debugging)
        enable_detailed_logging=True,
        log_api_calls=True,
    ),
    Environment.PRODUCTION.value: ExchangeEnvironmentConfig(
        name="binance",
        base_url="https://api.binance.com",
        ws_url="wss://stream.binance.com/ws/",
        sandbox=False,
        rate_limit_buffer=0.6,  # 40% buffer for safety
        timeout=15000,  # 15 seconds (shorter for faster failure detection)
        max_retries=5,
        connection_timeout=10000,  # 10 seconds
        heartbeat_interval=20,  # 20 seconds
        # Security (strict for production)
        require_ip_restriction=True,
        require_2fa=True,
        # Performance (conservative)
        max_concurrent_requests=8,
        request_delay_ms=1200,  # 1.2 seconds between requests (safer than 1000ms limit)
        # Monitoring (minimal for performance)
        enable_detailed_logging=False,
        log_api_calls=False,
    ),
}


def get_environment_config(environment: str) -> ExchangeEnvironmentConfig:
    """Get configuration for specified environment.

    Args:
        environment: Environment name ('testnet' or 'production')

    Returns:
        ExchangeEnvironmentConfig for the environment

    Raises:
        ValueError: If environment is not supported
    """
    if environment not in EXCHANGE_ENVIRONMENTS:
        raise ValueError(
            f"Unsupported environment: {environment}. "
            f"Supported: {list(EXCHANGE_ENVIRONMENTS.keys())}"
        )

    return EXCHANGE_ENVIRONMENTS[environment]


def validate_environment_config(
    environment: str, api_key: str, api_secret: str
) -> Dict[str, Any]:
    """Validate environment configuration and credentials.

    Args:
        environment: Environment name
        api_key: Binance API key
        api_secret: Binance API secret

    Returns:
        Validation result with status and recommendations
    """
    config = get_environment_config(environment)
    result = {"valid": True, "warnings": [], "errors": [], "recommendations": []}

    # Basic credential validation
    if not api_key or not api_secret:
        result["errors"].append("API key and secret are required")
        result["valid"] = False
        return result

    # Environment-specific validation
    if environment == Environment.PRODUCTION.value:
        # Production-specific checks
        if len(api_key) < 50:
            result["warnings"].append("API key seems too short for production")

        if len(api_secret) < 50:
            result["warnings"].append("API secret seems too short for production")

        if config.require_ip_restriction:
            result["recommendations"].append(
                "Enable IP restrictions in Binance API settings for production"
            )

        if config.require_2fa:
            result["recommendations"].append(
                "Enable 2FA on Binance account for production use"
            )

        result["recommendations"].extend(
            [
                "Start with small amounts ($10-50) for production testing",
                "Monitor rate limiting closely in production",
                "Set up comprehensive logging and alerting",
            ]
        )

    elif environment == Environment.TESTNET.value:
        # Testnet-specific checks
        result["recommendations"].extend(
            [
                "Test all trading scenarios thoroughly in testnet",
                "Verify error handling with invalid orders",
                "Test WebSocket reconnection logic",
                "Validate rate limiting behavior",
            ]
        )

    return result


def get_recommended_settings(
    environment: str, trading_volume: str = "low"
) -> Dict[str, Any]:
    """Get recommended settings based on environment and trading volume.

    Args:
        environment: Environment name
        trading_volume: Expected trading volume ('low', 'medium', 'high')

    Returns:
        Recommended configuration adjustments
    """
    base_config = get_environment_config(environment)

    volume_adjustments = {
        "low": {
            "max_concurrent_requests": min(base_config.max_concurrent_requests, 5),
            "request_delay_ms": max(base_config.request_delay_ms, 2000),
            "rate_limit_buffer": max(base_config.rate_limit_buffer, 0.7),
        },
        "medium": {
            "max_concurrent_requests": base_config.max_concurrent_requests,
            "request_delay_ms": base_config.request_delay_ms,
            "rate_limit_buffer": base_config.rate_limit_buffer,
        },
        "high": {
            "max_concurrent_requests": min(base_config.max_concurrent_requests + 2, 20),
            "request_delay_ms": max(base_config.request_delay_ms - 200, 800),
            "rate_limit_buffer": min(base_config.rate_limit_buffer - 0.1, 0.5),
        },
    }

    if trading_volume not in volume_adjustments:
        trading_volume = "low"  # Default to conservative settings

    return {
        "base_config": base_config,
        "adjustments": volume_adjustments[trading_volume],
        "recommendations": [
            f"Configuration optimized for {trading_volume} volume trading",
            f"Environment: {environment}",
            f"Rate limit buffer: {volume_adjustments[trading_volume]['rate_limit_buffer']:.1%}",
        ],
    }


# Environment validation utilities
def is_production_environment(environment: str) -> bool:
    """Check if environment is production."""
    return environment == Environment.PRODUCTION.value


def is_testnet_environment(environment: str) -> bool:
    """Check if environment is testnet."""
    return environment == Environment.TESTNET.value


def get_safe_environment_for_testing() -> str:
    """Get safe environment for automated testing."""
    return Environment.TESTNET.value


# Security utilities
def get_security_recommendations(environment: str) -> list[str]:
    """Get security recommendations for environment."""
    if is_production_environment(environment):
        return [
            "Use GCP Secret Manager for API credentials",
            "Enable IP restrictions on Binance API keys",
            "Enable 2FA on Binance account",
            "Regularly rotate API keys",
            "Monitor API usage for suspicious activity",
            "Set withdrawal restrictions on account",
            "Use separate API keys for different services",
            "Implement API key expiration policies",
        ]
    else:
        return [
            "Use separate testnet credentials",
            "Never use production credentials in testnet",
            "Regularly clean testnet API keys",
            "Test security scenarios thoroughly",
        ]
