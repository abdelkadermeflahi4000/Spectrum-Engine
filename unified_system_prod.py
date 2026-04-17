import asyncio
import signal
import uuid
import time
import structlog
from typing import Dict, Any, Set
from cachetools import TTLCache
from enum import Enum

# ==========================================
# Structured Logging Setup
# ==========================================
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("unified_core")

# ==========================================
# Shared Message
# ==========================================
class Message:
    def __init__(self, msg_type: str, payload: Dict[str, Any], priority: int = 1, ttl: float = 30.0):
        self.id = str(uuid.uuid4())
        self.type = msg_type
        self.payload = payload
        self.priority = priority
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


# ==========================================
# TTL Duplicate Guard
# ==========================================
class DuplicateGuard:
    def __init__(self, max_size: int = 10000, ttl: int = 300):
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)

    def check(self, message_id: str) -> bool:
        if message_id in self.cache:
            return False
        self.cache[message_id] = True
        return True


# ==========================================
# Async Circuit Breaker
# ==========================================
class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class AsyncCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 10.0):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = 0.0

    async def execute(self, coro_func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_state", state="half_open")
            else:
                raise RuntimeError("Circuit breaker is OPEN")

        try:
            result = await coro_func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("circuit_breaker_state", state="closed")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning("circuit_breaker_state", state="open")
            raise e


# ==========================================
# Base Engine
# ==========================================
class BaseEngine:
    def __init__(self, name: str):
        self.name = name
        self.breaker = AsyncCircuitBreaker(failure_threshold=3, recovery_timeout=15.0)

    async def execute(self, message: Message):
        raise NotImplementedError()


# ==========================================
# Engines
# ==========================================
class SpectrumEngine(BaseEngine):
    async def execute(self, message: Message):
        await asyncio.sleep(0.1)
        return {"engine": self.name, "signal_processed": True}

class DukaEngine(BaseEngine):
    async def execute(self, message: Message):
        await asyncio.sleep(0.1)
        return {"engine": self.name, "reasoning_complete": True}

class ViolaEngine(BaseEngine):
    async def execute(self, message: Message):
        await asyncio.sleep(0.1)
        return {"engine": self.name, "harmonized": True}

class BetaRootEngine(BaseEngine):
    async def execute(self, message: Message):
        await asyncio.sleep(0.1)
        return {"engine": self.name, "memory_updated": True}


# ==========================================
# Meta Router
# ==========================================
class MetaRouter:
    ROUTING_TABLE = {
        "frequency": "spectrum",
        "logic": "duka",
        "sync": "viola",
        "memory": "betaroot",
    }

    def route(self, message: Message) -> str:
        return self.ROUTING_TABLE.get(message.type, "betaroot")


# ==========================================
# Unified System (Production)
# ==========================================
class UnifiedSystem:
    def __init__(self):
        self.queue = asyncio.PriorityQueue()
        self.guard = DuplicateGuard(max_size=50000, ttl=600)
        self.router = MetaRouter()
        self.engines: Dict[str, BaseEngine] = {
            "spectrum": SpectrumEngine("Spectrum"),
            "duka": DukaEngine("Duka"),
            "viola": ViolaEngine("Viola"),
            "betaroot": BetaRootEngine("BetaRoot"),
        }
        self.running = True
        self.active_tasks: Set[asyncio.Task] = set()

    async def submit(self, message: Message):
        if message.is_expired():
            logger.warning("message_expired", msg_id=message.id)
            return
        if self.guard.check(message.id):
            await self.queue.put((message.priority, message))
            logger.debug("message_queued", msg_id=message.id, type=message.type)
        else:
            logger.warning("duplicate_skipped", msg_id=message.id)

    async def safe_execute(self, engine_name: str, message: Message):
        engine = self.engines.get(engine_name)
        if not engine:
            logger.error("unknown_engine", name=engine_name)
            return

        try:
            result = await engine.breaker.execute(engine.execute, message)
            logger.info("execution_success", engine=engine_name, result=result)
        except Exception as e:
            logger.error("execution_failed", engine=engine_name, error=str(e))
            # In production: trigger alerting / fallback route here

    async def worker(self):
        while self.running:
            try:
                _, message = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            engine_name = self.router.route(message)
            task = asyncio.create_task(self.safe_execute(engine_name, message))
            self.active_tasks.add(task)
            task.add_done_callback(self.active_tasks.discard)

    async def monitor(self):
        while self.running:
            logger.info("system_health", queue_size=self.queue.qsize(), active_tasks=len(self.active_tasks))
            await asyncio.sleep(5)

    async def graceful_shutdown(self):
        logger.info("shutdown_initiated")
        self.running = False
        # Wait for pending tasks
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        logger.info("shutdown_completed")

    async def start(self):
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.graceful_shutdown()))

        await asyncio.gather(self.worker(), self.monitor())
