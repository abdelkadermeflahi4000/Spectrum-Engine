import time
from modules.spectrum.spectrum_engine import SpectrumEngine
from modules.duka.duka_core import DukaCore
from modules.viola.viola_core import ViolaCore


class UnifiedCore:
    def __init__(self):
        print("[SYSTEM] Initializing Unified Core...")

        self.spectrum = SpectrumEngine()
        self.duka = DukaCore()
        self.viola = ViolaCore()

        self.running = True

    def collect_input(self):
        signal_data = self.spectrum.listen()
        return signal_data

    def process_intelligence(self, data):
        decision = self.duka.process(data)
        return decision

    def synchronize_response(self, decision):
        optimized = self.viola.resonate(decision)
        return optimized

    def execute_output(self, response):
        self.spectrum.transmit(response)

    def run_cycle(self):
        try:
            data = self.collect_input()

            if data:
                decision = self.process_intelligence(data)
                response = self.synchronize_response(decision)
                self.execute_output(response)

        except Exception as e:
            print(f"[ERROR] {e}")

    def run(self):
        print("[SYSTEM] Autonomous mode active.")

        while self.running:
            self.run_cycle()
            time.sleep(0.1)


if __name__ == "__main__":
    core = UnifiedCore()
    core.run()
