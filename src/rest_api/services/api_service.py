"""API service layer for business logic and message bus integration."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from common.message_bus import MessageBus

from ..auth.jwt_auth import JWTAuthHandler

logger = logging.getLogger(__name__)


class APIService:
    """API service layer for handling business logic and Core Engine communication.

    Acts as intermediary between FastAPI endpoints and Core Engine via message bus.
    Manages request/response lifecycle and provides caching for common operations.
    """

    def __init__(self, message_bus: MessageBus, jwt_handler: JWTAuthHandler):
        """Initialize API service.

        Args:
            message_bus: Message bus instance for Core Engine communication
            jwt_handler: JWT authentication handler
        """
        self.message_bus = message_bus
        self.jwt_handler = jwt_handler
        self.is_running = False

        # Request tracking
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.request_timeout = 30  # seconds

        # Response cache (simple in-memory cache for MVP)
        self.response_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes

        logger.info("API service initialized")

    async def start(self) -> bool:
        """Start API service and set up message bus subscriptions.

        Returns:
            bool: True if started successfully
        """
        try:
            if self.is_running:
                logger.info("API service already running")
                return True

            # Subscribe to response channels from Core Engine
            await self._setup_response_handlers()

            self.is_running = True
            logger.info("API service started successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to start API service: {e}")
            return False

    async def stop(self) -> bool:
        """Stop API service.

        Returns:
            bool: True if stopped successfully
        """
        try:
            self.is_running = False

            # Clear pending requests
            self.pending_requests.clear()
            self.response_cache.clear()

            logger.info("API service stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping API service: {e}")
            return False

    async def _setup_response_handlers(self) -> None:
        """Set up message bus response handlers."""
        response_channels = [
            "response.system.status",
            "response.strategies.list",
            "response.strategies.get",
            "response.strategies.create",
            "response.strategies.update",
            "response.strategies.delete",
            "response.strategies.control",
            "response.portfolios.list",
            "response.portfolios.get",
            "response.portfolios.update",
            "response.monitoring.status",
            "response.monitoring.metrics",
        ]

        for channel in response_channels:
            await self.message_bus.subscribe(channel, self._handle_response)

        logger.info(f"Set up {len(response_channels)} response handlers")

    async def _handle_response(self, message: Dict[str, Any]) -> None:
        """Handle responses from Core Engine.

        Args:
            message: Response message from Core Engine
        """
        try:
            request_id = message.get("request_id")
            if not request_id:
                logger.warning("Received response without request_id")
                return

            if request_id in self.pending_requests:
                # Store response for the pending request
                self.pending_requests[request_id]["response"] = message
                self.pending_requests[request_id]["completed"] = True

                logger.debug(f"Received response for request {request_id}")
            else:
                logger.warning(f"Received response for unknown request: {request_id}")

        except Exception as e:
            logger.error(f"Error handling response: {e}")

    async def send_request(
        self, routing_key: str, request_data: Dict[str, Any], timeout: int = None
    ) -> Dict[str, Any]:
        """Send request to Core Engine and wait for response.

        Args:
            routing_key: Message routing key
            request_data: Request data
            timeout: Request timeout in seconds

        Returns:
            dict: Response data from Core Engine

        Raises:
            TimeoutError: If request times out
            Exception: If request fails
        """
        if not self.is_running:
            raise Exception("API service not running")

        request_id = str(uuid.uuid4())
        timeout = timeout or self.request_timeout

        # Prepare request
        message = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **request_data,
        }

        # Track request
        self.pending_requests[request_id] = {
            "routing_key": routing_key,
            "request": message,
            "completed": False,
            "response": None,
            "created_at": datetime.now(timezone.utc),
        }

        try:
            # Send request
            await self.message_bus.publish(routing_key, message)
            logger.debug(f"Sent request {request_id} via {routing_key}")

            # Wait for response
            start_time = datetime.now(timezone.utc)
            while not self.pending_requests[request_id]["completed"]:
                await asyncio.sleep(0.1)

                # Check timeout
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(
                        f"Request {request_id} timed out after {timeout} seconds"
                    )

            # Get response
            response = self.pending_requests[request_id]["response"]

            # Clean up
            del self.pending_requests[request_id]

            return response

        except Exception as e:
            # Clean up on error
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise e

    # Strategy management methods
    async def list_strategies(
        self, user_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """List all strategies.

        Args:
            user_id: User ID making the request
            filters: Optional filters

        Returns:
            dict: Strategies list response
        """
        request_data = {
            "type": "list_strategies",
            "user_id": user_id,
            "filters": filters or {},
        }

        return await self.send_request("request.strategies.list", request_data)

    async def get_strategy(self, user_id: str, strategy_id: int) -> Dict[str, Any]:
        """Get strategy by ID.

        Args:
            user_id: User ID making the request
            strategy_id: Strategy ID

        Returns:
            dict: Strategy data
        """
        request_data = {
            "type": "get_strategy",
            "user_id": user_id,
            "strategy_id": strategy_id,
        }

        return await self.send_request("request.strategies.get", request_data)

    async def create_strategy(
        self, user_id: str, strategy_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new strategy.

        Args:
            user_id: User ID making the request
            strategy_data: Strategy configuration

        Returns:
            dict: Created strategy data
        """
        request_data = {
            "type": "create_strategy",
            "user_id": user_id,
            "strategy_data": strategy_data,
        }

        return await self.send_request("request.strategies.create", request_data)

    async def update_strategy(
        self, user_id: str, strategy_id: int, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update strategy.

        Args:
            user_id: User ID making the request
            strategy_id: Strategy ID
            update_data: Update data

        Returns:
            dict: Updated strategy data
        """
        request_data = {
            "type": "update_strategy",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "update_data": update_data,
        }

        return await self.send_request("request.strategies.update", request_data)

    async def delete_strategy(self, user_id: str, strategy_id: int) -> Dict[str, Any]:
        """Delete strategy.

        Args:
            user_id: User ID making the request
            strategy_id: Strategy ID

        Returns:
            dict: Deletion confirmation
        """
        request_data = {
            "type": "delete_strategy",
            "user_id": user_id,
            "strategy_id": strategy_id,
        }

        return await self.send_request("request.strategies.delete", request_data)

    async def control_strategy(
        self,
        user_id: str,
        strategy_id: int,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Control strategy (start/stop/pause/resume).

        Args:
            user_id: User ID making the request
            strategy_id: Strategy ID
            action: Control action
            parameters: Optional action parameters

        Returns:
            dict: Control result
        """
        request_data = {
            "type": "control_strategy",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "action": action,
            "parameters": parameters or {},
        }

        return await self.send_request("request.strategies.control", request_data)

    # Portfolio management methods
    async def list_portfolios(
        self, user_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """List all portfolios.

        Args:
            user_id: User ID making the request
            filters: Optional filters

        Returns:
            dict: Portfolios list response
        """
        request_data = {
            "type": "list_portfolios",
            "user_id": user_id,
            "filters": filters or {},
        }

        return await self.send_request("request.portfolios.list", request_data)

    async def get_portfolio(self, user_id: str, portfolio_id: int) -> Dict[str, Any]:
        """Get portfolio by ID.

        Args:
            user_id: User ID making the request
            portfolio_id: Portfolio ID

        Returns:
            dict: Portfolio data
        """
        request_data = {
            "type": "get_portfolio",
            "user_id": user_id,
            "portfolio_id": portfolio_id,
        }

        return await self.send_request("request.portfolios.get", request_data)

    async def update_portfolio(
        self, user_id: str, portfolio_id: int, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update portfolio.

        Args:
            user_id: User ID making the request
            portfolio_id: Portfolio ID
            update_data: Update data

        Returns:
            dict: Updated portfolio data
        """
        request_data = {
            "type": "update_portfolio",
            "user_id": user_id,
            "portfolio_id": portfolio_id,
            "update_data": update_data,
        }

        return await self.send_request("request.portfolios.update", request_data)

    # System monitoring methods
    async def get_system_status(self, user_id: str) -> Dict[str, Any]:
        """Get system status.

        Args:
            user_id: User ID making the request

        Returns:
            dict: System status data
        """
        request_data = {"type": "get_system_status", "user_id": user_id}

        return await self.send_request("request.monitoring.status", request_data)

    async def get_system_metrics(
        self, user_id: str, period: str = "hour"
    ) -> Dict[str, Any]:
        """Get system metrics.

        Args:
            user_id: User ID making the request
            period: Metrics period

        Returns:
            dict: System metrics data
        """
        request_data = {
            "type": "get_system_metrics",
            "user_id": user_id,
            "period": period,
        }

        return await self.send_request("request.monitoring.metrics", request_data)

    def get_service_status(self) -> Dict[str, Any]:
        """Get API service status.

        Returns:
            dict: Service status information
        """
        return {
            "is_running": self.is_running,
            "message_bus_connected": (
                self.message_bus.is_connected if self.message_bus else False
            ),
            "pending_requests": len(self.pending_requests),
            "cache_size": len(self.response_cache),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
