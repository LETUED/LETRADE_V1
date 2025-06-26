"""
Strategy Worker 프로세스 관리자 패키지

이 패키지는 거래 전략의 실행을 담당하는 프로세스를 관리합니다.
각 전략은 독립적인 프로세스에서 실행되어 격리성과 안정성을 보장합니다.
"""

from .main import StrategyWorker, WorkerStatus

__all__ = ["StrategyWorker", "WorkerStatus"]
