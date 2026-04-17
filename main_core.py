import threading
import queue
import time

from modules.spectrum.spectrum_engine import SpectrumEngine
from modules.duka.duka_core import DukaCore
from modules.viola.viola_core import ViolaCore


class UnifiedCore:
    def __init__(self):
        self.spectrum = SpectrumEngine()
        self.duka = DukaCore()
        self.viola = ViolaCore()

        self.input_queue = queue.Queue()
        self.decision_queue = queue.Queue()
        self.output_queue = queue.Queue()

        self.running = True

    # ==========================
    # Spectrum Thread
    # ==========================
    def spectrum_listener(self):
        while self.running:
            data = self.spectrum.listen()

            if data:
                self.input_queue.put(data)

            time.sleep(0.05)

    # ==========================
    # Duka Thread
    # ==========================
    def duka_processor(self):
        while self.running:
            if not self.input_queue.empty():
                data = self.input_queue.get()
                decision = self.duka.process(data)
                self.decision_queue.put(decision)

            time.sleep(0.05)

    # ==========================
    # Viola Thread
    # ==========================
    def viola_optimizer(self):
        while self.running:
            if not self.decision_queue.empty():
                decision = self.decision_queue.get()
                response = self.viola.resonate(decision)
                self.output_queue.put(response)

            time.sleep(0.05)

    # ==========================
    # Execution Thread
    # ==========================
    def output_executor(self):
        while self.running:
            if not self.output_queue.empty():
                response = self.output_queue.get()
                self.spectrum.transmit(response)

            time.sleep(0.05)

    # ==========================
    # Start all threads
    # ==========================
    def start(self):
        threads = [
            threading.Thread(target=self.spectrum_listener),
            threading.Thread(target=self.duka_processor),
            threading.Thread(target=self.viola_optimizer),
            threading.Thread(target=self.output_executor)
        ]

        for t in threads:
            t.daemon = True
            t.start()

        print("[SYSTEM] Parallel autonomous core started.")

        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            self.running = False
            print("[SYSTEM] Shutdown complete.")


if __name__ == "__main__":
    core = UnifiedCore()
    core.start()
