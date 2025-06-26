"""
고성능 캐시 매니저
Redis 기반 분산 캐싱 및 로컬 메모리 캐싱 지원
"""

import asyncio
import json
import logging
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class LocalCache:
    """로컬 메모리 캐시 (LRU)"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                return None

            # LRU: 최근 사용 항목을 끝으로 이동
            self._cache.move_to_end(key)
            return entry["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """캐시에 값 저장"""
        async with self._lock:
            ttl = ttl or self.default_ttl

            # 캐시 크기 제한
            if len(self._cache) >= self.max_size and key not in self._cache:
                # LRU: 가장 오래된 항목 제거
                self._cache.popitem(last=False)

            self._cache[key] = {"value": value, "expires_at": time.time() + ttl}
            self._cache.move_to_end(key)

    async def delete(self, key: str) -> bool:
        """캐시에서 항목 삭제"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """캐시 전체 삭제"""
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        """캐시 크기 반환"""
        async with self._lock:
            return len(self._cache)


class CacheManager:
    """분산 캐시 매니저 (Redis + Local Cache)"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        local_cache_size: int = 1000,
        default_ttl: int = 60,
    ):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache = LocalCache(
            max_size=local_cache_size, default_ttl=default_ttl
        )
        self.default_ttl = default_ttl
        self._connected = False

        # 통계
        self.stats = {
            "hits": 0,
            "misses": 0,
            "local_hits": 0,
            "redis_hits": 0,
            "sets": 0,
            "deletes": 0,
        }

    async def connect(self) -> bool:
        """Redis 연결"""
        if self.redis_url:
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
                await self.redis_client.ping()
                self._connected = True
                logger.info("Connected to Redis cache")
                return True
            except Exception as e:
                logger.warning(
                    f"Failed to connect to Redis: {e}. Using local cache only."
                )
                self._connected = False
                return False
        return True

    async def disconnect(self) -> None:
        """Redis 연결 해제"""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
            logger.info("Disconnected from Redis cache")

    async def get(self, key: str, default: Any = None) -> Any:
        """캐시에서 값 조회 (Local → Redis)"""
        # 1. 로컬 캐시 확인
        value = await self.local_cache.get(key)
        if value is not None:
            self.stats["hits"] += 1
            self.stats["local_hits"] += 1
            return value

        # 2. Redis 캐시 확인
        if self._connected and self.redis_client:
            try:
                redis_value = await self.redis_client.get(key)
                if redis_value:
                    # JSON 디코딩
                    try:
                        value = json.loads(redis_value)
                    except json.JSONDecodeError:
                        value = redis_value

                    # 로컬 캐시에도 저장
                    await self.local_cache.set(key, value)

                    self.stats["hits"] += 1
                    self.stats["redis_hits"] += 1
                    return value
            except Exception as e:
                logger.error(f"Redis get error: {e}")

        self.stats["misses"] += 1
        return default

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, local_only: bool = False
    ) -> bool:
        """캐시에 값 저장"""
        ttl = ttl or self.default_ttl
        self.stats["sets"] += 1

        # 로컬 캐시 저장
        await self.local_cache.set(key, value, ttl)

        # Redis 저장
        if not local_only and self._connected and self.redis_client:
            try:
                # JSON 인코딩
                if isinstance(value, (dict, list)):
                    redis_value = json.dumps(value)
                else:
                    redis_value = str(value)

                await self.redis_client.setex(key, ttl, redis_value)
                return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                return False

        return True

    async def delete(self, key: str) -> bool:
        """캐시에서 항목 삭제"""
        self.stats["deletes"] += 1

        # 로컬 캐시 삭제
        local_deleted = await self.local_cache.delete(key)

        # Redis 삭제
        redis_deleted = False
        if self._connected and self.redis_client:
            try:
                redis_deleted = await self.redis_client.delete(key) > 0
            except Exception as e:
                logger.error(f"Redis delete error: {e}")

        return local_deleted or redis_deleted

    async def clear(self, pattern: Optional[str] = None) -> int:
        """캐시 삭제"""
        count = 0

        # 로컬 캐시 전체 삭제
        if not pattern:
            await self.local_cache.clear()
            count += await self.local_cache.size()

        # Redis 삭제
        if self._connected and self.redis_client:
            try:
                if pattern:
                    # 패턴 매칭 삭제
                    keys = []
                    async for key in self.redis_client.scan_iter(match=pattern):
                        keys.append(key)

                    if keys:
                        count += await self.redis_client.delete(*keys)
                else:
                    # 전체 삭제 (주의!)
                    await self.redis_client.flushdb()
            except Exception as e:
                logger.error(f"Redis clear error: {e}")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.2f}%",
            "local_cache_size": asyncio.run_coroutine_threadsafe(
                self.local_cache.size(), asyncio.get_event_loop()
            ).result(),
        }

    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)


def cached(ttl: int = 60, key_prefix: Optional[str] = None, local_only: bool = False):
    """캐시 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 캐시 매니저 확인
            cache_manager = getattr(self, "cache_manager", None)
            if not cache_manager:
                return await func(self, *args, **kwargs)

            # 캐시 키 생성
            prefix = key_prefix or f"{self.__class__.__name__}:{func.__name__}"
            cache_key = cache_manager.cache_key(prefix, *args, **kwargs)

            # 캐시 조회
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 함수 실행
            result = await func(self, *args, **kwargs)

            # 캐시 저장
            if result is not None:
                await cache_manager.set(
                    cache_key, result, ttl=ttl, local_only=local_only
                )

            return result

        return wrapper

    return decorator


# 싱글톤 인스턴스
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """캐시 매니저 싱글톤 반환"""
    global _cache_manager

    if _cache_manager is None:
        redis_url = "redis://localhost:6379/0"  # 환경 변수에서 읽도록 수정 필요
        _cache_manager = CacheManager(redis_url=redis_url)
        await _cache_manager.connect()

    return _cache_manager
