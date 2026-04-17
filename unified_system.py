import asyncio
import uuid
import time
from typing import Dict, Any


# ==========================================
# Shared Message Object
# ==========================================
class Message:
    def __init__(self, msg_type: str, payload: Dict[str, Any], priority: int = 1):
        self.id = str(uuid.uuid4())
        self.type = msg_type
        self.payload = payload
        self.priority = priority
        self.timestamp = time.time()


# ==========================================
# Duplicate Protection
# ==========================================
class DuplicateGuard:
    def __init__(self):
        self.seen = set()

    def check(self, message_id: str) -> bool:
        if message_id in self.seen:
            return False
        self.seen.add(message_id)
        return True


# ==========================================
# Base Engine
# ==========================================
class BaseEngine:
    def __init__(self, name):
        self.name = name
        self.health = True

    async def execute(self, message: Message):
        raise NotImplementedError()

    async def recover(self):
        print(f"[RECOVERY] restarting {self.name}")
        await asyncio.sleep(0.2)
        self.health = True


# ==========================================
# Engines
# ==========================================
class SpectrumEngine(BaseEngine):
    async def execute(self, message):
        await asyncio.sleep(0.1)
        return {"engine": self.name, "signal_processed": True}


class DukaEngine(BaseEngine):
    async def execute(self, message):
        await asyncio.sleep(0.1)
        return {"engine": self.name, "reasoning_complete": True}


class ViolaEngine(BaseEngine):
    async def execute(self, message):
        await asyncio.sleep(0.1)
        return {"engine": self.name, "harmonized": True}


class BetaRootEngine(BaseEngine):
    async def execute(self, message):
        await asyncio.sleep(0.1)
        return {"engine": self.name, "memory_updated": True}


# ==========================================
# Meta AI Router
# ==========================================
class MetaRouter:
    def route(self, message: Message):
        if message.type == "frequency":
            return "spectrum"

        if message.type == "logic":
            return "duka"

        if message.type == "sync":
            return "viola"

        return "betaroot"


# ==========================================
# Unified System
# ==========================================
class UnifiedSystem:
    def __init__(self):
        self.queue = asyncio.PriorityQueue()
        self.guard = DuplicateGuard()
        self.router = MetaRouter()

        self.engines = {
            "spectrum": SpectrumEngine("Spectrum"),
            "duka": DukaEngine("Duka"),
            "viola": ViolaEngine("Viola"),
            "betaroot": BetaRootEngine("BetaRoot"),
        }

        self.running = True

    # --------------------------------------
    # Add Task
    # --------------------------------------
    async def submit(self, message: Message):
        if self.guard.check(message.id):
            await self.queue.put((message.priority, message))
        else:
            print("[SKIP] duplicate message")

    # --------------------------------------
    # Safe Execution
    # --------------------------------------
    async def safe_execute(self, engine_name, message):
        engine = self.engines[engine_name]

        try:
            result = await engine.execute(message)
            print(f"[OK] {engine_name} -> {result}")

        except Exception as e:
            print(f"[ERROR] {engine_name}: {e}")
            await engine.recover()

    # --------------------------------------
    # Worker
    # --------------------------------------
    async def worker(self):
        while self.running:
            _, message = await self.queue.get()

            engine_name = self.router.route(message)

            asyncio.create_task(
                self.safe_execute(engine_name, message)
            )

    # --------------------------------------
    # Monitor
    # --------------------------------------
    async def monitor(self):
        while self.running:
            print(f"[MONITOR] queue={self.queue.qsize()}")
            await asyncio.sleep(3)

    # --------------------------------------
    # Start
    # --------------------------------------
    async def start(self):
        await asyncio.gather(
            self.worker(),
            self.monitor()
        )


# ==========================================
# Example Usage
# ==========================================
async def main():
    system = UnifiedSystem()

    asyncio.create_task(system.start())

    await system.submit(Message("frequency", {"value": 432}))
    await system.submit(Message("logic", {"query": "analyze"}))
    await system.submit(Message("sync", {"mode": "balance"}))
    await system.submit(Message("memory", {"store": "state"}))

    await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
