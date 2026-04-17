import asyncio

from modules.spectrum.spectrum_engine import SpectrumEngine
from modules.duka.duka_core import DukaCore
from modules.viola.viola_core import ViolaCore


class UnifiedAsyncCore:
    def __init__(self):
        self.spectrum = SpectrumEngine()
        self.duka = DukaCore()
        self.viola = ViolaCore()

        self.input_queue = asyncio.Queue()
        self.decision_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()

        self.running = True

    # ==========================
    # Spectrum
    # ==========================
    async def spectrum_listener(self):
        while self.running:
            data = await self.spectrum.listen()

            if data:
                await self.input_queue.put(data)

            await asyncio.sleep(0.01)

    # ==========================
    # Duka
    # ==========================
    async def duka_processor(self):
        while self.running:
            data = await self.input_queue.get()
            decision = await self.duka.process(data)
            await self.decision_queue.put(decision)

    # ==========================
    # Viola
    # ==========================
    async def viola_optimizer(self):
        while self.running:
            decision = await self.decision_queue.get()
            response = await self.viola.resonate(decision)
            await self.output_queue.put(response)

    # ==========================
    # Output
    # ==========================
    async def output_executor(self):
        while self.running:
            response = await self.output_queue.get()
            await self.spectrum.transmit(response)

    # ==========================
    # Monitor
    # ==========================
    async def monitor(self):
        while self.running:
            print(f"[Monitor] Input={self.input_queue.qsize()} "
                  f"Decision={self.decision_queue.qsize()} "
                  f"Output={self.output_queue.qsize()}")

            await asyncio.sleep(5)

    # ==========================
    # Start
    # ==========================
    async def start(self):
        tasks = [
            asyncio.create_task(self.spectrum_listener()),
            asyncio.create_task(self.duka_processor()),
            asyncio.create_task(self.viola_optimizer()),
            asyncio.create_task(self.output_executor()),
            asyncio.create_task(self.monitor())
        ]

        print("[SYSTEM] Async autonomous core started.")

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    core = UnifiedAsyncCore()
    asyncio.run(core.start())
