"""Authentication and authorization system for Telegram Bot.

Implements SEC-AUTH-001 (텔레그램 사용자 화이트리스트 기반 인증) from MVP specification.
Provides secure, whitelist-based access control with rate limiting and session management.
"""

import logging
from typing import Dict, List, Set, Optional
from datetime import datetime, timezone, timedelta
import hashlib
import hmac

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication and authorization for Telegram users.
    
    Implements whitelist-based security with support for both user IDs and usernames.
    Provides session management and security logging.
    """
    
    def __init__(self, config: Dict):
        """Initialize authentication manager.
        
        Args:
            config: Authentication configuration
        """
        self.config = config
        
        # Whitelist configuration
        self.allowed_user_ids: Set[int] = set(config.get('allowed_users', []))
        self.allowed_usernames: Set[str] = set(config.get('allowed_usernames', []))
        
        # Session management
        self.authenticated_users: Dict[int, Dict] = {}
        self.session_duration = config.get('session_duration', 3600)  # 1 hour default
        
        # Security settings
        self.max_failed_attempts = config.get('max_failed_attempts', 5)
        self.lockout_duration = config.get('lockout_duration', 1800)  # 30 minutes
        self.require_username = config.get('require_username', True)
        
        # Failed attempt tracking
        self.failed_attempts: Dict[int, Dict] = {}
        
        # Security token for additional verification (optional)
        self.security_token = config.get('security_token')
        
        logger.info(f"AuthManager initialized with {len(self.allowed_user_ids)} allowed user IDs "
                   f"and {len(self.allowed_usernames)} allowed usernames")
    
    async def is_authenticated(self, user_id: int, username: Optional[str] = None) -> bool:
        """Check if user is authenticated and authorized.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username (optional)
            
        Returns:
            bool: True if user is authenticated and authorized
        """
        # Check if user is locked out
        if self._is_locked_out(user_id):
            logger.warning(f"User {user_id} is locked out due to failed attempts")
            return False
        
        # Check whitelist authorization
        if not self._is_authorized(user_id, username):
            await self._record_failed_attempt(user_id, "Not in whitelist")
            return False
        
        # Check existing session
        if self._has_valid_session(user_id):
            await self._refresh_session(user_id)
            return True
        
        # Create new session for authorized user
        await self._create_session(user_id, username)
        logger.info(f"New session created for user {user_id} (@{username})")
        return True
    
    def _is_authorized(self, user_id: int, username: Optional[str] = None) -> bool:
        """Check if user is in whitelist.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            
        Returns:
            bool: True if user is authorized
        """
        # Check user ID whitelist
        if user_id in self.allowed_user_ids:
            return True
        
        # Check username whitelist (if username provided and required)
        if username and username in self.allowed_usernames:
            return True
        
        # If require_username is True and no username provided, deny access
        if self.require_username and not username:
            logger.warning(f"User {user_id} denied access: username required but not provided")
            return False
        
        return False
    
    def _has_valid_session(self, user_id: int) -> bool:
        """Check if user has a valid active session.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if session is valid
        """
        if user_id not in self.authenticated_users:
            return False
        
        session = self.authenticated_users[user_id]
        expires_at = session.get('expires_at')
        
        if not expires_at:
            return False
        
        return datetime.now(timezone.utc) < expires_at
    
    async def _create_session(self, user_id: int, username: Optional[str] = None) -> None:
        """Create new authentication session.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
        """
        session = {
            'user_id': user_id,
            'username': username,
            'created_at': datetime.now(timezone.utc),
            'expires_at': datetime.now(timezone.utc) + timedelta(seconds=self.session_duration),
            'last_activity': datetime.now(timezone.utc),
            'command_count': 0
        }
        
        self.authenticated_users[user_id] = session
        
        # Clear any failed attempts
        if user_id in self.failed_attempts:
            del self.failed_attempts[user_id]
    
    async def _refresh_session(self, user_id: int) -> None:
        """Refresh existing session.
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.authenticated_users:
            session = self.authenticated_users[user_id]
            session['last_activity'] = datetime.now(timezone.utc)
            session['command_count'] = session.get('command_count', 0) + 1
    
    def _is_locked_out(self, user_id: int) -> bool:
        """Check if user is currently locked out.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user is locked out
        """
        if user_id not in self.failed_attempts:
            return False
        
        failed_data = self.failed_attempts[user_id]
        attempts = failed_data.get('count', 0)
        last_attempt = failed_data.get('last_attempt')
        
        if attempts < self.max_failed_attempts:
            return False
        
        if not last_attempt:
            return False
        
        # Check if lockout period has expired
        lockout_expires = last_attempt + timedelta(seconds=self.lockout_duration)
        if datetime.now(timezone.utc) > lockout_expires:
            # Reset failed attempts after lockout period
            del self.failed_attempts[user_id]
            return False
        
        return True
    
    async def _record_failed_attempt(self, user_id: int, reason: str) -> None:
        """Record failed authentication attempt.
        
        Args:
            user_id: Telegram user ID
            reason: Reason for failure
        """
        if user_id not in self.failed_attempts:
            self.failed_attempts[user_id] = {
                'count': 0,
                'attempts': []
            }
        
        failed_data = self.failed_attempts[user_id]
        failed_data['count'] += 1
        failed_data['last_attempt'] = datetime.now(timezone.utc)
        failed_data['attempts'].append({
            'timestamp': datetime.now(timezone.utc),
            'reason': reason
        })
        
        logger.warning(f"Failed authentication attempt {failed_data['count']} for user {user_id}: {reason}")
        
        # Log security alert if approaching lockout
        if failed_data['count'] >= self.max_failed_attempts - 1:
            logger.error(f"SECURITY ALERT: User {user_id} approaching lockout threshold")
    
    async def logout_user(self, user_id: int) -> bool:
        """Logout user and invalidate session.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if logout successful
        """
        if user_id in self.authenticated_users:
            del self.authenticated_users[user_id]
            logger.info(f"User {user_id} logged out")
            return True
        
        return False
    
    def get_session_info(self, user_id: int) -> Optional[Dict]:
        """Get session information for user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            dict: Session information or None if no session
        """
        if user_id not in self.authenticated_users:
            return None
        
        session = self.authenticated_users[user_id].copy()
        
        # Convert datetime objects to strings for serialization
        if 'created_at' in session:
            session['created_at'] = session['created_at'].isoformat()
        if 'expires_at' in session:
            session['expires_at'] = session['expires_at'].isoformat()
        if 'last_activity' in session:
            session['last_activity'] = session['last_activity'].isoformat()
        
        return session
    
    def verify_security_token(self, provided_token: str) -> bool:
        """Verify security token for additional authentication.
        
        Args:
            provided_token: Token provided by user
            
        Returns:
            bool: True if token is valid
        """
        if not self.security_token:
            return True  # No token required
        
        if not provided_token:
            return False
        
        # Use HMAC for secure token comparison
        expected_token = hmac.new(
            self.security_token.encode(),
            b"letrade_auth",
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(provided_token, expected_token)
    
    def add_authorized_user(self, user_id: Optional[int] = None, username: Optional[str] = None) -> bool:
        """Add user to authorization whitelist.
        
        Args:
            user_id: Telegram user ID to add
            username: Telegram username to add
            
        Returns:
            bool: True if user added successfully
        """
        added = False
        
        if user_id and user_id not in self.allowed_user_ids:
            self.allowed_user_ids.add(user_id)
            logger.info(f"Added user ID {user_id} to whitelist")
            added = True
        
        if username and username not in self.allowed_usernames:
            self.allowed_usernames.add(username)
            logger.info(f"Added username @{username} to whitelist")
            added = True
        
        return added
    
    def remove_authorized_user(self, user_id: Optional[int] = None, username: Optional[str] = None) -> bool:
        """Remove user from authorization whitelist.
        
        Args:
            user_id: Telegram user ID to remove
            username: Telegram username to remove
            
        Returns:
            bool: True if user removed successfully
        """
        removed = False
        
        if user_id and user_id in self.allowed_user_ids:
            self.allowed_user_ids.remove(user_id)
            # Also logout if currently authenticated
            if user_id in self.authenticated_users:
                del self.authenticated_users[user_id]
            logger.info(f"Removed user ID {user_id} from whitelist")
            removed = True
        
        if username and username in self.allowed_usernames:
            self.allowed_usernames.remove(username)
            logger.info(f"Removed username @{username} from whitelist")
            removed = True
        
        return removed
    
    def get_auth_stats(self) -> Dict:
        """Get authentication statistics.
        
        Returns:
            dict: Authentication statistics
        """
        active_sessions = len([
            s for s in self.authenticated_users.values()
            if self._has_valid_session(s['user_id'])
        ])
        
        locked_users = len([
            user_id for user_id in self.failed_attempts.keys()
            if self._is_locked_out(user_id)
        ])
        
        return {
            'authorized_user_ids': len(self.allowed_user_ids),
            'authorized_usernames': len(self.allowed_usernames),
            'active_sessions': active_sessions,
            'total_sessions': len(self.authenticated_users),
            'locked_users': locked_users,
            'failed_attempts_tracked': len(self.failed_attempts),
            'session_duration': self.session_duration,
            'max_failed_attempts': self.max_failed_attempts,
            'lockout_duration': self.lockout_duration
        }