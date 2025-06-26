"""
중앙 집중식 설정 관리 모듈

환경 변수와 설정 파일을 통합 관리하여
모든 서비스가 일관된 설정을 사용하도록 보장
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class Config:
    """중앙 집중식 설정 클래스"""

    # 환경 설정
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    TESTING = os.getenv("TESTING", "false").lower() == "true"

    # 데이터베이스 설정
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://letrade_user:letrade_password@localhost:5432/letrade_db",
    )

    # RabbitMQ 설정
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER = os.getenv("RABBITMQ_USER", "letrade_user")
    RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "letrade_password")
    RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

    # Redis 설정
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

    # API 설정
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8080"))
    API_LOG_LEVEL = os.getenv("API_LOG_LEVEL", "info")

    # 보안 설정
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-not-for-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = 24

    # 텔레그램 설정
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_WHITELIST = (
        os.getenv("TELEGRAM_WHITELIST", "").split(",")
        if os.getenv("TELEGRAM_WHITELIST")
        else []
    )

    # 거래소 설정
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    # 성능 설정
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
    POOL_SIZE = int(os.getenv("POOL_SIZE", "20"))
    CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))

    # 로깅 설정
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
    LOG_FILE = os.getenv("LOG_FILE", "logs/letrade.log")

    # 모니터링
    PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

    # 리스크 관리 기본값
    DEFAULT_MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.1"))  # 10%
    DEFAULT_STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "2.0"))  # 2%
    DEFAULT_DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", "5.0"))  # 5%

    # Mock 모드
    MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

    @classmethod
    def get_message_bus_config(cls) -> Dict[str, Any]:
        """메시지 버스 설정 반환"""
        return {
            "host": cls.RABBITMQ_HOST,
            "port": cls.RABBITMQ_PORT,
            "username": cls.RABBITMQ_USER,
            "password": cls.RABBITMQ_PASSWORD,
            "virtual_host": cls.RABBITMQ_VHOST,
            "connection_attempts": 3,
            "retry_delay": 5,
        }

    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """Redis 설정 반환"""
        return {
            "host": cls.REDIS_HOST,
            "port": cls.REDIS_PORT,
            "db": cls.REDIS_DB,
            "password": cls.REDIS_PASSWORD,
            "decode_responses": True,
        }

    @classmethod
    def get_exchange_config(cls, exchange: str = "binance") -> Dict[str, Any]:
        """거래소 설정 반환"""
        if exchange == "binance":
            return {
                "apiKey": cls.BINANCE_API_KEY,
                "secret": cls.BINANCE_API_SECRET,
                "enableRateLimit": True,
                "rateLimit": 1200,
                "options": {
                    "defaultType": "spot",
                    "adjustForTimeDifference": True,
                    "recvWindow": 10000,
                    "test": cls.BINANCE_TESTNET,
                },
            }
        return {}

    @classmethod
    def get_capital_manager_config(cls) -> Dict[str, Any]:
        """Capital Manager 설정 반환"""
        return {
            "max_position_size_pct": cls.DEFAULT_MAX_POSITION_SIZE * 100,
            "max_portfolio_risk_pct": 20.0,
            "stop_loss_pct": cls.DEFAULT_STOP_LOSS_PERCENT,
            "daily_loss_limit_pct": cls.DEFAULT_DAILY_LOSS_LIMIT,
            "max_drawdown_pct": 15.0,
            "risk_free_rate": 0.02,  # 2% 연간
        }

    @classmethod
    def load_strategy_config(cls, strategy_name: str) -> Dict[str, Any]:
        """전략별 설정 파일 로드"""
        config_path = Path(f"config/strategies/{strategy_name}.yaml")

        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)

        # 기본 설정 반환
        return {
            "enabled": True,
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "capital_allocation": 100.0,
            "max_positions": 1,
            "parameters": {},
        }

    @classmethod
    def is_production(cls) -> bool:
        """프로덕션 환경 여부"""
        return cls.ENVIRONMENT == "production"

    @classmethod
    def is_development(cls) -> bool:
        """개발 환경 여부"""
        return cls.ENVIRONMENT == "development"

    @classmethod
    def validate_config(cls) -> bool:
        """필수 설정 검증"""
        errors = []

        # 프로덕션 환경에서 필수 설정 확인
        if cls.is_production():
            if cls.JWT_SECRET_KEY == "dev-secret-key-not-for-production":
                errors.append("JWT_SECRET_KEY must be changed in production")

            if not cls.TELEGRAM_BOT_TOKEN:
                errors.append("TELEGRAM_BOT_TOKEN is required in production")

            if cls.MOCK_MODE:
                errors.append("MOCK_MODE should be false in production")

        if errors:
            for error in errors:
                print(f"CONFIG ERROR: {error}")
            return False

        return True


# 설정 검증 (모듈 로드 시)
Config.validate_config()
