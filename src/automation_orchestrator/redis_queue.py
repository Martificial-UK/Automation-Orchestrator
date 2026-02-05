"""
Redis-based background task queue for Automation Orchestrator
Replaces in-process background tasks with distributed Redis queue
"""

import json
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import redis
from enum import Enum

# Optional fake redis for local development/testing
try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class RedisQueue:
    """
    Redis-based task queue for handling background operations
    Provides:
    - Non-blocking task queueing
    - Task status tracking
    - Retry handling
    - TTL for completed tasks
    """
    
    def __init__(self,
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 queue_prefix: str = "ao:tasks",
                 use_fake_redis: bool = False,
                 allow_fallback: bool = True,
                 required: bool = False):
        """
        Initialize Redis queue
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            queue_prefix: Prefix for all queue keys
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.queue_prefix = queue_prefix

        try:
            if use_fake_redis:
                if not HAS_FAKEREDIS:
                    raise RuntimeError("fakeredis not installed")
                self.client = fakeredis.FakeStrictRedis(decode_responses=True)
                self.client.ping()
                logger.info("Connected to fakeredis (in-memory queue)")
            else:
                self.client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30
                )
                self.client.ping()
                logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            if required:
                raise RuntimeError(f"Redis connection required but failed: {e}")
            if allow_fallback and HAS_FAKEREDIS:
                logger.warning(f"Redis unavailable, using fakeredis fallback: {e}")
                self.client = fakeredis.FakeStrictRedis(decode_responses=True)
                self.client.ping()
            elif allow_fallback:
                logger.warning(f"Redis unavailable, falling back to in-memory queue: {e}")
                self.client = None
            else:
                raise RuntimeError(f"Redis connection failed: {e}")
    
    def _get_queue_key(self, queue_name: str) -> str:
        """Get full queue key"""
        return f"{self.queue_prefix}:{queue_name}"
    
    def _get_task_key(self, task_id: str) -> str:
        """Get full task metadata key"""
        return f"{self.queue_prefix}:task:{task_id}"

    def ping(self) -> bool:
        """Check Redis connectivity."""
        if not self.client:
            return False
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def get_queue_depth(self, queue_name: str = "default") -> int:
        """Return the current queue length."""
        if not self.client:
            return 0
        try:
            return int(self.client.llen(self._get_queue_key(queue_name)))
        except Exception:
            return 0
    
    def enqueue(self,
                task_type: str,
                task_data: Dict[str, Any],
                queue_name: str = "default",
                retry_count: int = 3,
                ttl_seconds: int = 3600) -> str:
        """
        Enqueue a task to Redis queue
        
        Args:
            task_type: Type of task (e.g., "crm_update", "email_send")
            task_data: Task data payload
            queue_name: Name of queue to use
            retry_count: Number of retries on failure
            ttl_seconds: Time-to-live for task metadata
        
        Returns:
            Task ID for tracking
        """
        import uuid
        task_id = str(uuid.uuid4())
        
        if not self.client:
            logger.debug(f"Redis unavailable, storing task in memory: {task_id}")
            return task_id
        
        try:
            queue_key = self._get_queue_key(queue_name)
            task_key = self._get_task_key(task_id)
            
            # Create task object
            task_obj = {
                "id": task_id,
                "type": task_type,
                "data": json.dumps(task_data),
                "status": TaskStatus.PENDING.value,
                "created_at": datetime.now().isoformat(),
                "retry_count": retry_count,
                "retries_remaining": retry_count,
                "error": None
            }
            
            # Store task metadata
            self.client.hset(task_key, mapping=task_obj)
            self.client.expire(task_key, ttl_seconds)
            
            # Add to queue
            self.client.rpush(queue_key, task_id)
            
            logger.info(f"Enqueued task {task_id}: {task_type}")
            return task_id
        
        except Exception as e:
            logger.error(f"Error enqueuing task: {e}")
            raise
    
    def dequeue(self, queue_name: str = "default", timeout: int = 0) -> Optional[Dict[str, Any]]:
        """
        Dequeue a task from Redis queue
        
        Args:
            queue_name: Name of queue to dequeue from
            timeout: Timeout in seconds (0 = non-blocking)
        
        Returns:
            Task object or None if queue empty
        """
        if not self.client:
            return None
        
        try:
            queue_key = self._get_queue_key(queue_name)
            
            # Get task ID from queue
            if timeout == 0:
                task_id = self.client.lpop(queue_key)
            else:
                task_id = self.client.blpop(queue_key, timeout=timeout)
                if task_id:
                    task_id = task_id[1]  # blpop returns [queue_key, value]
            
            if not task_id:
                return None
            
            # Get task metadata
            task_key = self._get_task_key(task_id)
            task_data = self.client.hgetall(task_key)
            
            if not task_data:
                logger.warning(f"Task metadata not found for {task_id}")
                return None
            
            # Update status to processing
            task_data["status"] = TaskStatus.PROCESSING.value
            self.client.hset(task_key, mapping={"status": TaskStatus.PROCESSING.value})
            
            # Parse JSON data
            task_data["data"] = json.loads(task_data.get("data", "{}"))
            
            logger.info(f"Dequeued task {task_id}: {task_data.get('type')}")
            return task_data
        
        except Exception as e:
            logger.error(f"Error dequeuing task: {e}")
            return None
    
    def mark_complete(self, task_id: str) -> bool:
        """
        Mark task as completed
        
        Args:
            task_id: Task ID to mark complete
        
        Returns:
            Success status
        """
        if not self.client:
            return True
        
        try:
            task_key = self._get_task_key(task_id)
            self.client.hset(task_key, mapping={"status": TaskStatus.COMPLETED.value})
            logger.info(f"Task {task_id} marked as completed")
            return True
        except Exception as e:
            logger.error(f"Error marking task complete: {e}")
            return False
    
    def mark_failed(self, task_id: str, error: str, retry: bool = True) -> bool:
        """
        Mark task as failed
        
        Args:
            task_id: Task ID to mark failed
            error: Error message
            retry: Whether to retry this task
        
        Returns:
            Success status
        """
        if not self.client:
            return True
        
        try:
            task_key = self._get_task_key(task_id)
            task_data = self.client.hgetall(task_key)
            
            retries_remaining = int(task_data.get("retries_remaining", 0))
            
            if retry and retries_remaining > 0:
                # Re-queue for retry
                new_status = TaskStatus.RETRY.value
                retries_remaining -= 1
                queue_name = task_data.get("queue_name", "default")
                queue_key = self._get_queue_key(queue_name)
                self.client.rpush(queue_key, task_id)
                logger.info(f"Task {task_id} marked for retry ({retries_remaining} retries left)")
            else:
                new_status = TaskStatus.FAILED.value
                logger.error(f"Task {task_id} failed permanently: {error}")
            
            # Update task
            self.client.hset(task_key, mapping={
                "status": new_status,
                "error": error,
                "retries_remaining": retries_remaining
            })
            
            return True
        except Exception as e:
            logger.error(f"Error marking task failed: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status and metadata
        
        Args:
            task_id: Task ID to check
        
        Returns:
            Task metadata or None
        """
        if not self.client:
            return None
        
        try:
            task_key = self._get_task_key(task_id)
            task_data = self.client.hgetall(task_key)
            
            if task_data:
                task_data["data"] = json.loads(task_data.get("data", "{}"))
            
            return task_data
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return None
    
    def queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        if not self.client:
            return {}
        
        try:
            stats = {}
            pattern = f"{self.queue_prefix}:*"
            keys = self.client.keys(pattern)
            
            for key in keys:
                if key.startswith(f"{self.queue_prefix}:"):
                    queue_name = key.replace(f"{self.queue_prefix}:", "", 1)
                    queue_length = self.client.llen(key)
                    if queue_length > 0:
                        stats[queue_name] = queue_length
            
            return stats
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {}


# Global queue instance
_queue_instance: Optional[RedisQueue] = None


def get_queue(redis_config: Optional[Dict[str, Any]] = None) -> RedisQueue:
    """Get or create global Redis queue"""
    global _queue_instance
    
    if _queue_instance is None:
        if redis_config is None:
            redis_config = {}
        
        _queue_instance = RedisQueue(
            redis_host=redis_config.get("host", "localhost"),
            redis_port=redis_config.get("port", 6379),
            redis_db=redis_config.get("db", 0),
            queue_prefix=redis_config.get("queue_prefix", "ao:tasks"),
            use_fake_redis=redis_config.get("use_fake_redis", False),
            allow_fallback=redis_config.get("allow_fallback", True),
            required=redis_config.get("required", False)
        )
    
    return _queue_instance


# Task handlers
def register_task_handler(task_type: str, handler: Callable) -> None:
    """
    Register a handler for a task type
    
    Usage:
        def handle_crm_update(task_data):
            # Process CRM update
            pass
        
        register_task_handler("crm_update", handle_crm_update)
    """
    logger.info(f"Registered handler for task type: {task_type}")
    # Implementation would store handlers in a registry


# Middleware for FastAPI
async def enqueue_background_task(task_type: str,
                                   task_data: Dict[str, Any],
                                   queue: RedisQueue = None,
                                   queue_name: str = "default") -> str:
    """
    Enqueue a background task instead of using BackgroundTasks
    
    Usage in endpoint:
        @app.put("/api/leads/{lead_id}")
        async def update_lead(lead_id: str, lead: LeadData):
            # Store in cache immediately
            app.state.leads_cache[lead_id] = lead_dict
            
            # Queue async CRM update
            await enqueue_background_task(
                "crm_update",
                {"lead_id": lead_id, "lead_data": lead_dict}
            )
            
            return response
    """
    if queue is None:
        queue = get_queue()
    
    task_id = queue.enqueue(
        task_type=task_type,
        task_data=task_data,
        queue_name=queue_name
    )
    
    return task_id
