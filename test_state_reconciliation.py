#!/usr/bin/env python3
"""
State Reconciliation Engine Integration Test

간단한 통합 테스트로 상태 조정 엔진의 기본 기능을 검증합니다.
"""

import asyncio
import sys
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from common.state_reconciliation import (
    StateReconciliationEngine, 
    ReconciliationStatus,
    DiscrepancyType,
    ReconciliationSeverity
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockExchangeConnector:
    """Mock exchange connector for testing."""
    
    def __init__(self):
        self.is_connected = True
        self.config = MagicMock()
        self.config.exchange_name = "binance_testnet"
    
    async def get_account_balance(self):
        """Mock account balance."""
        return {
            'USDT': MagicMock(total=10000.0, free=9500.0, locked=500.0),
            'BTC': MagicMock(total=0.0, free=0.0, locked=0.0),
            'ETH': MagicMock(total=0.1, free=0.1, locked=0.0)
        }
    
    async def get_open_orders(self):
        """Mock open orders."""
        return []
    
    async def health_check(self):
        """Mock health check."""
        return {
            "healthy": True,
            "connected": True,
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }


class MockCapitalManager:
    """Mock capital manager for testing."""
    
    def __init__(self):
        self.is_running = True
    
    async def health_check(self):
        """Mock health check."""
        return {
            "healthy": True,
            "running": True,
            "available_capital": 10000.0
        }


async def test_reconciliation_engine_basic():
    """Test basic reconciliation engine functionality."""
    logger.info("🧪 Starting State Reconciliation Engine Basic Test")
    
    # Create mock components
    exchange_connector = MockExchangeConnector()
    capital_manager = MockCapitalManager()
    
    # Initialize reconciliation engine
    reconciliation_engine = StateReconciliationEngine(
        exchange_connector=exchange_connector,
        capital_manager=capital_manager
    )
    
    logger.info("✅ Reconciliation engine initialized successfully")
    
    # Test health check
    health_status = await reconciliation_engine.health_check()
    logger.info(f"🔍 Health check result: {health_status}")
    
    assert health_status["reconciliation_engine_ready"] is True
    assert health_status["exchange_connected"] is True
    assert health_status["capital_manager_ready"] is True
    
    logger.info("✅ Health check passed")
    
    # Test full reconciliation
    logger.info("🔄 Starting full reconciliation test...")
    
    reconciliation_report = await reconciliation_engine.perform_full_reconciliation()
    
    logger.info(f"📊 Reconciliation completed:")
    logger.info(f"   - Session ID: {reconciliation_report.session_id}")
    logger.info(f"   - Status: {reconciliation_report.status.value}")
    logger.info(f"   - Total discrepancies: {len(reconciliation_report.discrepancies)}")
    logger.info(f"   - Duration: {(reconciliation_report.end_time - reconciliation_report.start_time).total_seconds():.2f}s")
    
    # Verify reconciliation completed successfully
    assert reconciliation_report.status in [ReconciliationStatus.COMPLETED, ReconciliationStatus.PARTIAL]
    assert reconciliation_report.end_time is not None
    assert len(reconciliation_report.exchanges_checked) > 0
    
    logger.info("✅ Full reconciliation test passed")
    
    # Test report summary
    summary = reconciliation_report.to_summary()
    logger.info(f"📄 Report summary: {summary}")
    
    assert "session_id" in summary
    assert "total_discrepancies" in summary
    assert "duration_seconds" in summary
    
    logger.info("✅ Report summary test passed")
    
    logger.info("🎉 All State Reconciliation Engine tests passed!")
    
    return reconciliation_report


async def test_reconciliation_with_mock_discrepancies():
    """Test reconciliation with simulated discrepancies."""
    logger.info("🧪 Testing reconciliation with mock discrepancies")
    
    # Create enhanced mock exchange connector with discrepancies
    class MockExchangeConnectorWithDiscrepancies(MockExchangeConnector):
        async def get_account_balance(self):
            # Return balance that doesn't match system state
            return {
                'USDT': MagicMock(total=9500.0, free=9000.0, locked=500.0),  # Less than expected
                'BTC': MagicMock(total=0.05, free=0.05, locked=0.0),  # Extra position
            }
    
    exchange_connector = MockExchangeConnectorWithDiscrepancies()
    capital_manager = MockCapitalManager()
    
    reconciliation_engine = StateReconciliationEngine(
        exchange_connector=exchange_connector,
        capital_manager=capital_manager
    )
    
    # Since we don't have actual database data, this will mostly test the framework
    reconciliation_report = await reconciliation_engine.perform_full_reconciliation()
    
    logger.info(f"📊 Reconciliation with mock discrepancies:")
    logger.info(f"   - Total discrepancies: {len(reconciliation_report.discrepancies)}")
    logger.info(f"   - Critical discrepancies: {len(reconciliation_report.get_critical_discrepancies())}")
    
    # Log any discrepancies found
    for i, discrepancy in enumerate(reconciliation_report.discrepancies):
        logger.info(f"   - Discrepancy {i+1}: {discrepancy.description} (Severity: {discrepancy.severity.value})")
    
    logger.info("✅ Mock discrepancy test completed")
    
    return reconciliation_report


async def main():
    """Main test runner."""
    try:
        logger.info("🚀 Starting State Reconciliation Integration Tests")
        logger.info("=" * 60)
        
        # Test 1: Basic functionality
        await test_reconciliation_engine_basic()
        
        logger.info("-" * 60)
        
        # Test 2: Mock discrepancies
        await test_reconciliation_with_mock_discrepancies()
        
        logger.info("=" * 60)
        logger.info("🎉 All integration tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Run the async tests
    asyncio.run(main())