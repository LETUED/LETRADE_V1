"""Core Engine main module for Letrade_v1 trading system.

The Core Engine is the central orchestrator that manages all trading components,
coordinates strategy execution, and ensures system-wide consistency.
"""

import asyncio
import logging
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Add path for imports
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.message_bus import (  # noqa: E402
    MessageBus,
    create_message_bus,
)
from strategy_worker.main import StrategyWorkerManager  # noqa: E402
from strategies.ma_crossover import MAcrossoverStrategy  # noqa: E402
from strategies.base_strategy import StrategyConfig  # noqa: E402

logger = logging.getLogger(__name__)


@dataclass
class SystemStatus:
    """System status tracking."""

    is_running: bool = False
    start_time: Optional[datetime] = None
    active_strategies: Set[str] = field(default_factory=set)
    total_trades: int = 0
    last_reconciliation: Optional[datetime] = None
    health_checks: Dict[str, bool] = field(default_factory=dict)


class CoreEngine:
    """Central orchestrator for the Letrade_v1 trading system.

    The Core Engine manages:
    - Strategy lifecycle management
    - System health monitoring
    - Message bus coordination
    - State reconciliation
    - Risk management oversight
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Core Engine.

        Args:
            config: System configuration dictionary
        """
        self.config = config or {}
        self.status = SystemStatus()
        self._shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        self._signal_received = False

        # Component references (will be injected)
        self.strategy_worker_manager: Optional[StrategyWorkerManager] = None
        self.capital_manager = None
        self.exchange_connector = None
        self.message_bus: Optional[MessageBus] = None

        logger.info(
            "Core Engine initialized",
            extra={
                "component": "core_engine",
                "config_keys": list(self.config.keys()) if self.config else [],
            },
        )

    async def start(self) -> bool:
        """Start the Core Engine and all subsystems.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info("Starting Core Engine...", extra={"component": "core_engine"})

            # 1. Pre-startup validation
            if not await self._validate_startup_conditions():
                logger.error(
                    "Startup validation failed", extra={"component": "core_engine"}
                )
                return False

            # 2. Initialize subsystems
            await self._initialize_subsystems()

            # 3. Setup signal handlers
            self._setup_signal_handlers()

            # 4. Start background tasks
            await self._start_background_tasks()

            # 5. Perform state reconciliation
            await self._perform_startup_reconciliation()

            # 6. Mark system as running
            self.status.is_running = True
            self.status.start_time = datetime.now(timezone.utc)

            logger.info(
                "Core Engine started successfully",
                extra={
                    "component": "core_engine",
                    "start_time": self.status.start_time.isoformat(),
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to start Core Engine",
                extra={"component": "core_engine", "error": str(e)},
            )
            await self._emergency_shutdown()
            return False

    async def stop(self) -> bool:
        """Stop the Core Engine and all subsystems gracefully.

        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            logger.info("Stopping Core Engine...", extra={"component": "core_engine"})

            # 1. Mark shutdown in progress
            self.status.is_running = False
            self._shutdown_event.set()

            # 2. Stop accepting new trades
            await self._stop_new_operations()

            # 3. Wait for active operations to complete
            await self._wait_for_active_operations()

            # 4. Stop background tasks
            await self._stop_background_tasks()

            # 5. Shutdown subsystems
            await self._shutdown_subsystems()

            # 6. Final state persistence
            await self._persist_final_state()

            logger.info(
                "Core Engine stopped successfully",
                extra={
                    "component": "core_engine",
                    "uptime_seconds": (
                        (
                            datetime.now(timezone.utc) - self.status.start_time
                        ).total_seconds()
                        if self.status.start_time
                        else 0
                    ),
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Error during Core Engine shutdown",
                extra={"component": "core_engine", "error": str(e)},
            )
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status.

        Returns:
            System status dictionary
        """
        uptime = None
        if self.status.start_time and self.status.is_running:
            uptime = (
                datetime.now(timezone.utc) - self.status.start_time
            ).total_seconds()

        return {
            "is_running": self.status.is_running,
            "start_time": (
                self.status.start_time.isoformat() if self.status.start_time else None
            ),
            "uptime_seconds": uptime,
            "active_strategies": list(self.status.active_strategies),
            "total_trades": self.status.total_trades,
            "last_reconciliation": (
                self.status.last_reconciliation.isoformat()
                if self.status.last_reconciliation
                else None
            ),
            "health_checks": self.status.health_checks,
            "component_status": self._get_component_status(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health check results
        """
        health_results = {
            "core_engine": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {},
        }

        try:
            # Check each component
            if self.strategy_worker_manager:
                health_results["components"]["strategy_worker_manager"] = (
                    await self._check_component_health("strategy_worker_manager")
                )

            if self.capital_manager:
                health_results["components"]["capital_manager"] = (
                    await self._check_component_health("capital_manager")
                )

            if self.exchange_connector:
                health_results["components"]["exchange_connector"] = (
                    await self._check_component_health("exchange_connector")
                )

            if self.message_bus:
                health_results["components"]["message_bus"] = (
                    await self._check_component_health("message_bus")
                )

            # Overall health
            all_healthy = all(health_results["components"].values())
            health_results["overall_health"] = all_healthy

            # Update status
            self.status.health_checks = health_results["components"]

        except Exception as e:
            logger.error(
                "Health check failed",
                extra={"component": "core_engine", "error": str(e)},
            )
            health_results["core_engine"] = False
            health_results["error"] = str(e)

        return health_results
    
    # Strategy Management API
    async def start_strategy(self, strategy_config: StrategyConfig) -> bool:
        """전략 시작
        
        Args:
            strategy_config: 시작할 전략 설정
            
        Returns:
            bool: 시작 성공 여부
        """
        if not self.strategy_worker_manager:
            logger.error("Strategy Worker Manager not initialized")
            return False
        
        try:
            # Strategy Worker 추가 및 시작
            success = await self.strategy_worker_manager.add_worker(
                strategy_id=strategy_config.strategy_id,
                strategy_class=MAcrossoverStrategy,  # 현재는 MA 전략만 지원
                strategy_config=strategy_config
            )
            
            if success:
                # 전략 시작
                success = await self.strategy_worker_manager.start_worker(
                    strategy_config.strategy_id
                )
                
                if success:
                    self.status.active_strategies.add(strategy_config.strategy_id)
                    
                    logger.info(
                        f"Strategy {strategy_config.strategy_id} started successfully",
                        extra={
                            "component": "core_engine",
                            "strategy_id": strategy_config.strategy_id,
                            "active_count": len(self.status.active_strategies)
                        }
                    )
                    
                    return True
            
            logger.error(f"Failed to start strategy {strategy_config.strategy_id}")
            return False
            
        except Exception as e:
            logger.error(
                f"Error starting strategy {strategy_config.strategy_id}: {e}",
                extra={
                    "component": "core_engine",
                    "strategy_id": strategy_config.strategy_id,
                    "error": str(e)
                }
            )
            return False
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """전략 중지
        
        Args:
            strategy_id: 중지할 전략 ID
            
        Returns:
            bool: 중지 성공 여부
        """
        if not self.strategy_worker_manager:
            logger.error("Strategy Worker Manager not initialized")
            return False
        
        try:
            success = await self.strategy_worker_manager.stop_worker(strategy_id)
            
            if success:
                self.status.active_strategies.discard(strategy_id)
                
                logger.info(
                    f"Strategy {strategy_id} stopped successfully",
                    extra={
                        "component": "core_engine",
                        "strategy_id": strategy_id,
                        "active_count": len(self.status.active_strategies)
                    }
                )
                
            return success
            
        except Exception as e:
            logger.error(
                f"Error stopping strategy {strategy_id}: {e}",
                extra={
                    "component": "core_engine",
                    "strategy_id": strategy_id,
                    "error": str(e)
                }
            )
            return False
    
    async def restart_strategy(self, strategy_id: str) -> bool:
        """전략 재시작
        
        Args:
            strategy_id: 재시작할 전략 ID
            
        Returns:
            bool: 재시작 성공 여부
        """
        if not self.strategy_worker_manager:
            logger.error("Strategy Worker Manager not initialized")
            return False
        
        try:
            success = await self.strategy_worker_manager.restart_worker(strategy_id)
            
            if success:
                logger.info(
                    f"Strategy {strategy_id} restarted successfully",
                    extra={
                        "component": "core_engine",
                        "strategy_id": strategy_id
                    }
                )
                
            return success
            
        except Exception as e:
            logger.error(
                f"Error restarting strategy {strategy_id}: {e}",
                extra={
                    "component": "core_engine",
                    "strategy_id": strategy_id,
                    "error": str(e)
                }
            )
            return False
    
    async def get_strategy_status(self, strategy_id: str = None) -> Dict[str, Any]:
        """전략 상태 조회
        
        Args:
            strategy_id: 조회할 전략 ID (None이면 전체 조회)
            
        Returns:
            Dict[str, Any]: 전략 상태 정보
        """
        if not self.strategy_worker_manager:
            return {"error": "Strategy Worker Manager not initialized"}
        
        try:
            if strategy_id:
                # 특정 전략 상태
                if strategy_id in self.strategy_worker_manager.workers:
                    worker = self.strategy_worker_manager.workers[strategy_id]
                    return await worker.health_check()
                else:
                    return {"error": f"Strategy {strategy_id} not found"}
            else:
                # 전체 전략 상태
                return await self.strategy_worker_manager.get_all_health_status()
                
        except Exception as e:
            logger.error(
                f"Error getting strategy status: {e}",
                extra={
                    "component": "core_engine",
                    "strategy_id": strategy_id,
                    "error": str(e)
                }
            )
            return {"error": str(e)}

    # Private methods
    async def _validate_startup_conditions(self) -> bool:
        """Validate conditions required for startup."""
        logger.info("Validating startup conditions", extra={"component": "core_engine"})

        # TODO: Implement actual validation
        # - Database connectivity
        # - Message bus connectivity
        # - Required configuration presence
        # - External API connectivity

        return True

    async def _initialize_subsystems(self):
        """Initialize all subsystem components."""
        logger.info("Initializing subsystems", extra={"component": "core_engine"})

        try:
            # Initialize message bus first (other components depend on it)
            message_bus_config = self.config.get(
                "message_bus",
                {
                    "host": "localhost",
                    "port": 5672,
                    "username": "guest",
                    "password": "guest",
                    "virtual_host": "/",
                },
            )

            self.message_bus = await create_message_bus(message_bus_config)
            logger.info(
                "Message bus initialized successfully",
                extra={"component": "core_engine"},
            )

            # Setup message handlers
            await self._setup_message_handlers()

            # Initialize Strategy Worker Manager
            self.strategy_worker_manager = StrategyWorkerManager(
                message_bus=self.message_bus
            )
            logger.info(
                "Strategy Worker Manager initialized successfully",
                extra={"component": "core_engine"},
            )
            
            # TODO: Initialize other components
            # self.capital_manager = CapitalManager(
            #     self.config.get("capital_manager", {}),
            #     message_bus=self.message_bus
            # )
            # self.exchange_connector = ExchangeConnector(
            #     self.config.get("exchange_connector", {}),
            #     message_bus=self.message_bus
            # )

            logger.info("Subsystems initialized", extra={"component": "core_engine"})

        except Exception as e:
            logger.error(
                "Failed to initialize subsystems",
                extra={"component": "core_engine", "error": str(e)},
            )
            raise

    async def _setup_message_handlers(self):
        """Setup message bus event handlers."""
        if not self.message_bus:
            logger.warning(
                "Message bus not available for handler setup",
                extra={"component": "core_engine"},
            )
            return

        try:
            # Subscribe to system events
            await self.message_bus.subscribe("system_events", self._handle_system_event)

            logger.info(
                "Message handlers setup completed", extra={"component": "core_engine"}
            )

        except Exception as e:
            logger.error(
                "Failed to setup message handlers",
                extra={"component": "core_engine", "error": str(e)},
            )
            raise

    async def _handle_system_event(self, message: Dict[str, Any]):
        """Handle system events from message bus.

        Args:
            message: System event message
        """
        try:
            routing_key = message.get("routing_key", "")
            payload = message.get("payload", {})

            logger.debug(
                "Processing system event",
                extra={
                    "component": "core_engine",
                    "routing_key": routing_key,
                    "payload_keys": list(payload.keys()),
                },
            )

            if "system.error" in routing_key:
                await self._handle_system_error(payload)
            elif "events.trade_executed" in routing_key:
                await self._handle_trade_executed(payload)
            elif "events.strategy_started" in routing_key:
                await self._handle_strategy_started(payload)
            elif "events.strategy_stopped" in routing_key:
                await self._handle_strategy_stopped(payload)

        except Exception as e:
            logger.error(
                "Error handling system event",
                extra={"component": "core_engine", "error": str(e)},
            )

    async def _handle_system_error(self, payload: Dict[str, Any]):
        """Handle system error events."""
        logger.error(
            "System error event received",
            extra={"component": "core_engine", "error_payload": payload},
        )

    async def _handle_trade_executed(self, payload: Dict[str, Any]):
        """Handle trade execution events."""
        self.status.total_trades += 1
        logger.info(
            "Trade executed",
            extra={
                "component": "core_engine",
                "total_trades": self.status.total_trades,
                "trade_info": payload,
            },
        )

    async def _handle_strategy_started(self, payload: Dict[str, Any]):
        """Handle strategy started events."""
        strategy_id = payload.get("strategy_id")
        if strategy_id:
            self.status.active_strategies.add(strategy_id)
            logger.info(
                "Strategy started",
                extra={
                    "component": "core_engine",
                    "strategy_id": strategy_id,
                    "active_count": len(self.status.active_strategies),
                },
            )

    async def _handle_strategy_stopped(self, payload: Dict[str, Any]):
        """Handle strategy stopped events."""
        strategy_id = payload.get("strategy_id")
        if strategy_id:
            self.status.active_strategies.discard(strategy_id)
            logger.info(
                "Strategy stopped",
                extra={
                    "component": "core_engine",
                    "strategy_id": strategy_id,
                    "active_count": len(self.status.active_strategies),
                },
            )

    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}", extra={"component": "core_engine"})
            self._signal_received = True
            asyncio.create_task(self._graceful_shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Signal handlers configured", extra={"component": "core_engine"})

    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks."""
        logger.info("Starting background tasks", extra={"component": "core_engine"})

        # Health monitoring task
        self._tasks.append(asyncio.create_task(self._health_monitor_loop()))

        # State reconciliation task
        self._tasks.append(asyncio.create_task(self._reconciliation_loop()))

        # System metrics task
        self._tasks.append(asyncio.create_task(self._metrics_collection_loop()))

        logger.info(
            f"Started {len(self._tasks)} background tasks",
            extra={"component": "core_engine"},
        )

    async def _perform_startup_reconciliation(self):
        """Perform startup state reconciliation."""
        logger.info(
            "Performing startup reconciliation", extra={"component": "core_engine"}
        )

        try:
            # TODO: Implement actual reconciliation
            # - Compare system state with exchange state
            # - Resolve any discrepancies
            # - Update position tracking

            self.status.last_reconciliation = datetime.now(timezone.utc)
            logger.info(
                "Startup reconciliation completed", extra={"component": "core_engine"}
            )

        except Exception as e:
            logger.error(
                "Startup reconciliation failed",
                extra={"component": "core_engine", "error": str(e)},
            )
            raise

    async def _stop_new_operations(self):
        """Stop accepting new trading operations."""
        logger.info("Stopping new operations", extra={"component": "core_engine"})
        # TODO: Implement operation stopping logic

    async def _wait_for_active_operations(self):
        """Wait for active operations to complete."""
        logger.info(
            "Waiting for active operations to complete",
            extra={"component": "core_engine"},
        )
        # TODO: Implement active operation waiting logic

    async def _stop_background_tasks(self):
        """Stop all background tasks."""
        logger.info("Stopping background tasks", extra={"component": "core_engine"})

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("Background tasks stopped", extra={"component": "core_engine"})

    async def _shutdown_subsystems(self):
        """Shutdown all subsystem components."""
        logger.info("Shutting down subsystems", extra={"component": "core_engine"})

        try:
            # Shutdown components in reverse order
            # Stop all Strategy Workers first
            if self.strategy_worker_manager:
                logger.info("Stopping Strategy Worker Manager...")
                await self.strategy_worker_manager.stop_all()
                
            # TODO: Shutdown other components
            # if self.capital_manager:
            #     await self.capital_manager.stop()
            # if self.exchange_connector:
            #     await self.exchange_connector.stop()

            # Shutdown message bus last
            if self.message_bus:
                await self.message_bus.disconnect()
                logger.info(
                    "Message bus disconnected", extra={"component": "core_engine"}
                )

            logger.info(
                "Subsystems shutdown complete", extra={"component": "core_engine"}
            )

        except Exception as e:
            logger.error(
                "Error during subsystems shutdown",
                extra={"component": "core_engine", "error": str(e)},
            )

    async def _persist_final_state(self):
        """Persist final system state."""
        logger.info("Persisting final state", extra={"component": "core_engine"})
        # TODO: Implement state persistence

    async def _emergency_shutdown(self):
        """Perform emergency shutdown procedures."""
        logger.error(
            "Performing emergency shutdown", extra={"component": "core_engine"}
        )

        self.status.is_running = False
        self._shutdown_event.set()

        # Cancel all tasks immediately
        for task in self._tasks:
            task.cancel()

    async def _graceful_shutdown(self):
        """Handle graceful shutdown from signal."""
        logger.info("Initiating graceful shutdown", extra={"component": "core_engine"})
        await self.stop()

    def _get_component_status(self) -> Dict[str, Any]:
        """Get status of all components."""
        return {
            "strategy_worker_manager": self.strategy_worker_manager is not None,
            "capital_manager": self.capital_manager is not None,
            "exchange_connector": self.exchange_connector is not None,
            "message_bus": self.message_bus is not None,
        }

    async def _check_component_health(self, component_name: str) -> bool:
        """Check health of a specific component."""
        try:
            component = getattr(self, component_name, None)
            if component and hasattr(component, "health_check"):
                health_result = await component.health_check()
                # Handle different return types
                if isinstance(health_result, dict):
                    return health_result.get("healthy", False)
                return bool(health_result)
            return component is not None
        except Exception as e:
            logger.error(
                f"Health check failed for {component_name}",
                extra={
                    "component": "core_engine",
                    "target_component": component_name,
                    "error": str(e),
                },
            )
            return False

    # Background task loops
    async def _health_monitor_loop(self):
        """Background health monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                await self.health_check()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Health monitor loop error",
                    extra={"component": "core_engine", "error": str(e)},
                )
                await asyncio.sleep(60)  # Wait longer on error

    async def _reconciliation_loop(self):
        """Background state reconciliation loop."""
        while not self._shutdown_event.is_set():
            try:
                # TODO: Implement periodic reconciliation
                await asyncio.sleep(300)  # Every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Reconciliation loop error",
                    extra={"component": "core_engine", "error": str(e)},
                )
                await asyncio.sleep(600)  # Wait longer on error

    async def _metrics_collection_loop(self):
        """Background metrics collection loop."""
        while not self._shutdown_event.is_set():
            try:
                # TODO: Collect and emit system metrics
                await asyncio.sleep(60)  # Every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Metrics collection loop error",
                    extra={"component": "core_engine", "error": str(e)},
                )
                await asyncio.sleep(120)  # Wait longer on error


async def main():
    """Main entry point for Core Engine."""
    # Setup structured logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/core_engine.log", mode="a"),
        ],
    )

    # TODO: Load configuration from environment/files
    config = {
        "log_level": "INFO",
        "health_check_interval": 30,
        "reconciliation_interval": 300,
    }

    # Create and start Core Engine
    engine = CoreEngine(config)

    try:
        if await engine.start():
            logger.info("Core Engine running, waiting for shutdown signal...")

            # Keep running until shutdown
            while engine.status.is_running:
                await asyncio.sleep(1)

        else:
            logger.error("Failed to start Core Engine")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Unexpected error in Core Engine: {e}")
        sys.exit(1)
    finally:
        await engine.stop()
        logger.info("Core Engine shutdown complete")


if __name__ == "__main__":
    # Ensure logs directory exists
    import os

    os.makedirs("logs", exist_ok=True)

    # Run the async main function
    asyncio.run(main())
