"""Message handler for Exchange Connector integration with RabbitMQ.

Handles message-driven communication with Capital Manager and Core Engine.
Implements standardized message routing for trading commands.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from decimal import Decimal

from common.message_bus import MessageBus
from exchange_connector.main import ExchangeConnector
from exchange_connector.interfaces import OrderRequest, OrderSide, OrderType

logger = logging.getLogger(__name__)


class ExchangeMessageHandler:
    """Handles RabbitMQ messages for exchange operations.
    
    Processes trading commands from Capital Manager and publishes
    execution results back to the message bus.
    """
    
    def __init__(self, exchange_connector: ExchangeConnector, message_bus: MessageBus):
        """Initialize message handler.
        
        Args:
            exchange_connector: Exchange connector instance
            message_bus: Message bus for communication
        """
        self.exchange = exchange_connector
        self.message_bus = message_bus
        self.is_running = False
        
        # Message routing configuration
        self.routing_keys = {
            'trade_commands': 'commands.execute_trade',
            'market_data_request': 'request.market_data',
            'account_info_request': 'request.account_info',
            'order_status_request': 'request.order_status'
        }
        
        # Response routing keys
        self.response_keys = {
            'trade_executed': 'events.trade_executed',
            'market_data_response': 'response.market_data',
            'account_info_response': 'response.account_info',
            'order_status_response': 'response.order_status',
            'error_event': 'events.error'
        }
        
        logger.info("Exchange message handler initialized")
    
    async def start(self) -> bool:
        """Start message handling."""
        try:
            if self.is_running:
                logger.info("Message handler already running")
                return True
            
            # Connect to exchange
            if not await self.exchange.connect():
                logger.error("Failed to connect to exchange")
                return False
            
            # Set up message subscriptions
            await self._setup_subscriptions()
            
            self.is_running = True
            logger.info("Exchange message handler started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start message handler: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop message handling."""
        try:
            self.is_running = False
            
            # Disconnect from exchange
            await self.exchange.disconnect()
            
            logger.info("Exchange message handler stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping message handler: {e}")
            return False
    
    async def _setup_subscriptions(self) -> None:
        """Set up RabbitMQ message subscriptions."""
        # Subscribe to trade execution commands
        await self.message_bus.subscribe(
            routing_key=self.routing_keys['trade_commands'],
            callback=self._handle_trade_command
        )
        
        # Subscribe to market data requests
        await self.message_bus.subscribe(
            routing_key=self.routing_keys['market_data_request'],
            callback=self._handle_market_data_request
        )
        
        # Subscribe to account info requests
        await self.message_bus.subscribe(
            routing_key=self.routing_keys['account_info_request'],
            callback=self._handle_account_info_request
        )
        
        # Subscribe to order status requests
        await self.message_bus.subscribe(
            routing_key=self.routing_keys['order_status_request'],
            callback=self._handle_order_status_request
        )
        
        logger.info("Message subscriptions set up successfully")
    
    async def _handle_trade_command(self, message: Dict[str, Any]) -> None:
        """Handle trade execution command from Capital Manager.
        
        Expected message format:
        {
            "strategy_id": 123,
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 0.01,
            "price": 50000.0,  # Optional for limit orders
            "stop_loss": 49000.0,  # Optional
            "take_profit": 55000.0,  # Optional
            "client_order_id": "strategy_123_001"
        }
        """
        try:
            logger.info(f"Processing trade command: {message}")
            
            # Validate required fields
            required_fields = ['strategy_id', 'symbol', 'side', 'type', 'amount']
            for field in required_fields:
                if field not in message:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create order request
            order_request = OrderRequest(
                symbol=message['symbol'],
                side=OrderSide(message['side']),
                type=OrderType(message['type']),
                amount=Decimal(str(message['amount'])),
                price=Decimal(str(message['price'])) if message.get('price') else None,
                stop_loss=Decimal(str(message['stop_loss'])) if message.get('stop_loss') else None,
                take_profit=Decimal(str(message['take_profit'])) if message.get('take_profit') else None,
                client_order_id=message.get('client_order_id'),
                metadata={
                    'strategy_id': message['strategy_id'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Execute trade
            order_response = await self.exchange.place_order(order_request)
            
            # Publish execution result
            execution_event = {
                'strategy_id': message['strategy_id'],
                'order_id': order_response.order_id,
                'symbol': order_response.symbol,
                'side': order_response.side.value,
                'type': order_response.type.value,
                'amount': float(order_response.amount),
                'filled': float(order_response.filled),
                'status': order_response.status.value,
                'average_price': float(order_response.average_price) if order_response.average_price else None,
                'cost': float(order_response.cost) if order_response.cost else None,
                'fee': float(order_response.fee) if order_response.fee else None,
                'timestamp': order_response.timestamp.isoformat(),
                'exchange': self.exchange.config.exchange_name
            }
            
            await self.message_bus.publish(
                routing_key=self.response_keys['trade_executed'],
                message=execution_event
            )
            
            logger.info(f"Trade executed successfully: {order_response.order_id}")
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            
            # Publish error event
            error_event = {
                'strategy_id': message.get('strategy_id', 'unknown'),
                'error_type': 'trade_execution_failed',
                'error_message': str(e),
                'original_message': message,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.message_bus.publish(
                routing_key=self.response_keys['error_event'],
                message=error_event
            )
    
    async def _handle_market_data_request(self, message: Dict[str, Any]) -> None:
        """Handle market data request.
        
        Expected message format:
        {
            "symbol": "BTC/USDT",
            "timeframe": "1m",
            "limit": 100,
            "request_id": "req_001"
        }
        """
        try:
            logger.debug(f"Processing market data request: {message}")
            
            symbol = message['symbol']
            timeframe = message.get('timeframe', '1m')
            limit = message.get('limit', 100)
            request_id = message.get('request_id', 'unknown')
            
            # Fetch market data
            market_data = await self.exchange.get_market_data(symbol, timeframe, limit)
            
            # Convert to response format
            response_data = {
                'request_id': request_id,
                'symbol': symbol,
                'timeframe': timeframe,
                'data': [md.to_dict() for md in market_data],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.message_bus.publish(
                routing_key=self.response_keys['market_data_response'],
                message=response_data
            )
            
            logger.debug(f"Market data response sent for {symbol}")
            
        except Exception as e:
            logger.error(f"Market data request failed: {e}")
            await self._publish_error_response(message, str(e))
    
    async def _handle_account_info_request(self, message: Dict[str, Any]) -> None:
        """Handle account information request."""
        try:
            logger.debug("Processing account info request")
            
            # Get account balance
            balances = await self.exchange.get_account_balance()
            
            # Get open orders
            open_orders = await self.exchange.get_open_orders()
            
            # Convert to response format
            response_data = {
                'request_id': message.get('request_id', 'unknown'),
                'balances': {
                    currency: {
                        'free': float(balance.free),
                        'used': float(balance.used),
                        'total': float(balance.total)
                    }
                    for currency, balance in balances.items()
                },
                'open_orders': [
                    {
                        'order_id': order.order_id,
                        'symbol': order.symbol,
                        'side': order.side.value,
                        'type': order.type.value,
                        'amount': float(order.amount),
                        'filled': float(order.filled),
                        'remaining': float(order.remaining),
                        'status': order.status.value
                    }
                    for order in open_orders
                ],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.message_bus.publish(
                routing_key=self.response_keys['account_info_response'],
                message=response_data
            )
            
            logger.debug("Account info response sent")
            
        except Exception as e:
            logger.error(f"Account info request failed: {e}")
            await self._publish_error_response(message, str(e))
    
    async def _handle_order_status_request(self, message: Dict[str, Any]) -> None:
        """Handle order status request.
        
        Expected message format:
        {
            "order_id": "123456",
            "symbol": "BTC/USDT",
            "request_id": "req_002"
        }
        """
        try:
            logger.debug(f"Processing order status request: {message}")
            
            order_id = message['order_id']
            symbol = message['symbol']
            request_id = message.get('request_id', 'unknown')
            
            # Get order status
            order_response = await self.exchange.get_order_status(order_id, symbol)
            
            # Convert to response format
            response_data = {
                'request_id': request_id,
                'order_id': order_response.order_id,
                'symbol': order_response.symbol,
                'side': order_response.side.value,
                'type': order_response.type.value,
                'amount': float(order_response.amount),
                'filled': float(order_response.filled),
                'remaining': float(order_response.remaining),
                'status': order_response.status.value,
                'average_price': float(order_response.average_price) if order_response.average_price else None,
                'cost': float(order_response.cost) if order_response.cost else None,
                'timestamp': order_response.timestamp.isoformat()
            }
            
            await self.message_bus.publish(
                routing_key=self.response_keys['order_status_response'],
                message=response_data
            )
            
            logger.debug(f"Order status response sent for {order_id}")
            
        except Exception as e:
            logger.error(f"Order status request failed: {e}")
            await self._publish_error_response(message, str(e))
    
    async def _publish_error_response(self, original_message: Dict[str, Any], error_message: str) -> None:
        """Publish error response for failed requests."""
        error_event = {
            'request_id': original_message.get('request_id', 'unknown'),
            'error_type': 'request_failed',
            'error_message': error_message,
            'original_message': original_message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        await self.message_bus.publish(
            routing_key=self.response_keys['error_event'],
            message=error_event
        )
    
    async def start_market_data_stream(self, symbols: List[str]) -> bool:
        """Start real-time market data streaming.
        
        Args:
            symbols: List of symbols to stream
            
        Returns:
            bool: True if streaming started successfully
        """
        try:
            def market_data_callback(market_data):
                """Callback for market data events."""
                asyncio.create_task(self._publish_market_data_event(market_data))
            
            success = await self.exchange.subscribe_market_data(symbols, market_data_callback)
            
            if success:
                logger.info(f"Market data streaming started for {len(symbols)} symbols")
            else:
                logger.warning("Failed to start market data streaming")
            
            return success
            
        except Exception as e:
            logger.error(f"Error starting market data stream: {e}")
            return False
    
    async def _publish_market_data_event(self, market_data) -> None:
        """Publish market data event to message bus."""
        try:
            market_data_event = {
                'symbol': market_data.symbol,
                'timestamp': market_data.timestamp.isoformat(),
                'open': float(market_data.open),
                'high': float(market_data.high),
                'low': float(market_data.low),
                'close': float(market_data.close),
                'volume': float(market_data.volume),
                'exchange': self.exchange.config.exchange_name
            }
            
            # Publish to symbol-specific routing key
            routing_key = f"market_data.{self.exchange.config.exchange_name}.{market_data.symbol.replace('/', '').lower()}"
            
            await self.message_bus.publish(
                routing_key=routing_key,
                message=market_data_event
            )
            
        except Exception as e:
            logger.error(f"Error publishing market data event: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on message handler and exchange."""
        exchange_health = await self.exchange.health_check()
        
        return {
            'message_handler_running': self.is_running,
            'exchange_status': exchange_health,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }