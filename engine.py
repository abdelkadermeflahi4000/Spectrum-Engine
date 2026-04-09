"""
SPECTRUM ENGINE — Main Entry Point
=====================================
Ties all layers together into one running system.

Architecture:
    Listen → Preprocess → Classify → Route → Transmit
       ↑                      ↓
       └──── Anomaly Detector ─┘

Run:
    python engine.py                  # simulation mode
    python engine.py --hardware       # real RTL-SDR hardware
    python engine.py --demo           # run full demo and exit
"""

import time
import sys
import argparse
import json
from core.listener import SignalListener
from core.preprocessor import SignalPreprocessor
from core.classifier import SignalClassifier
from core.anomaly_detector import AnomalyDetector
from mesh.router import MeshRouter, MeshPacket
from transport.bitcoin_relay import BitcoinMeshRelay, BitcoinTransaction


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ⚡  S P E C T R U M   E N G I N E                    ║
║                                                          ║
║   AI-Powered Decentralized Radio Mesh Network           ║
║   No internet. No banks. No censorship.                 ║
║                                                          ║
║   https://github.com/YOUR_USERNAME/spectrum-engine      ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


class SpectrumEngine:
    """
    The complete Spectrum Engine system.

    Runs the full pipeline:
    1. Capture radio signals (real or simulated)
    2. Convert to spectrogram images
    3. AI classifies each signal
    4. Anomaly detector watches for suspicious activity
    5. Mesh router finds best paths
    6. Bitcoin transactions relay without internet
    """

    def __init__(
        self,
        node_id: str = "NODE_001",
        simulate: bool = True,
        center_freq: float = 433e6,  # 433 MHz — LoRa band
        is_gateway: bool = False,
    ):
        self.node_id = node_id
        print_banner()
        print(f"Initializing node: {node_id}")
        print("─" * 60)

        # Layer 1: Signal Listener
        self.listener = SignalListener(
            center_freq=center_freq,
            simulate=simulate,
        )

        # Layer 1b: Preprocessor
        self.preprocessor = SignalPreprocessor(
            fft_size=256,
            output_size=(64, 64),
        )

        # Layer 2: AI Classifier
        self.classifier = SignalClassifier(
            model_path="models/rf_classifier.pth",
        )

        # Security: Anomaly Detector
        self.anomaly_detector = AnomalyDetector(
            baseline_window=20,
            alert_threshold=2.5,
        )

        # Layer 3: Mesh Router
        self.router = MeshRouter(
            node_id=node_id,
            broadcast_freq=center_freq,
        )

        # Layer 4: Bitcoin Relay
        self.btc_relay = BitcoinMeshRelay(
            node_id=node_id,
            is_gateway=is_gateway,
        )

        self.cycle_count = 0
        self.start_time = time.time()
        print("─" * 60)
        print("[OK] All systems initialized\n")

    def run_cycle(self, verbose: bool = True) -> dict:
        """
        Run one complete sensing → analysis → routing cycle.
        Returns a summary of what happened.
        """
        self.cycle_count += 1

        # ── Step 1: Capture signal ──────────────────────
        sample = self.listener.capture(num_samples=65536)

        # ── Step 2: Preprocess ──────────────────────────
        spectrogram = self.preprocessor.to_spectrogram(sample)
        features = self.preprocessor.extract_features(sample)

        # ── Step 3: AI Classification ───────────────────
        result = self.classifier.classify(spectrogram)

        # ── Step 4: Anomaly Detection ───────────────────
        alert = self.anomaly_detector.observe(features, result)

        # ── Step 5: Output ──────────────────────────────
        cycle_result = {
            "cycle": self.cycle_count,
            "signal_type": result.signal_type,
            "confidence": result.confidence,
            "anomaly_score": result.anomaly_score,
            "power_db": features["power_db"],
            "alert": str(alert) if alert else None,
            "source": sample.source,
        }

        if verbose:
            self._print_cycle(cycle_result, alert)

        return cycle_result

    def _print_cycle(self, result: dict, alert):
        conf_bar = "█" * int(result["confidence"] * 20)
        conf_bar = conf_bar.ljust(20, "░")

        status = "⚠ ANOMALY DETECTED" if result["alert"] else "✓ Normal"

        print(f"Cycle #{result['cycle']:04d} | {result['source']}")
        print(f"  Signal:    {result['signal_type']:<15} {conf_bar} {result['confidence']:.1%}")
        print(f"  Power:     {result['power_db']:.1f} dBm")
        print(f"  Status:    {status}")
        if alert:
            print(f"  {alert}")
        print()

    def simulate_bitcoin_transfer(self, destination_node: str = "GATEWAY_001"):
        """Demo: create and route a Bitcoin transaction through the mesh."""
        print("\n" + "═" * 60)
        print("DEMO: Bitcoin Transfer via Mesh (No Internet)")
        print("═" * 60)

        tx = BitcoinTransaction.simulate(amount_sats=100000, fee_sats=1000)
        print(f"Created transaction: {tx.txid[:32]}...")
        print(f"Amount: {tx.fee_sats + 100000:,} sats | Fee: {tx.fee_sats} sats")

        packet = self.btc_relay.create_packet(tx, destination=destination_node)
        forwarded = self.router.forward(packet)

        print(f"Mesh routing: {'SUCCESS' if forwarded else 'FAILED'}")
        print("═" * 60 + "\n")
        return forwarded

    def get_status(self) -> dict:
        uptime = time.time() - self.start_time
        return {
            "node_id": self.node_id,
            "uptime_seconds": round(uptime, 1),
            "cycles_completed": self.cycle_count,
            "network": self.router.network_status(),
            "bitcoin": self.btc_relay.status(),
            "environment": self.anomaly_detector.get_environment_summary(),
        }

    def run(self, cycles: int = 0, interval: float = 1.0):
        """
        Run the engine continuously.

        Args:
            cycles: number of cycles to run (0 = infinite)
            interval: seconds between cycles
        """
        print(f"Engine running {'continuously' if cycles == 0 else f'for {cycles} cycles'}...")
        print("Press Ctrl+C to stop\n")

        try:
            i = 0
            while cycles == 0 or i < cycles:
                self.run_cycle()
                i += 1
                if interval > 0:
                    time.sleep(interval)

        except KeyboardInterrupt:
            print("\n[INFO] Engine stopped by user")
        finally:
            self.listener.close()
            print("\n" + "─" * 60)
            print("FINAL STATUS:")
            print(json.dumps(self.get_status(), indent=2))


# ─────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Spectrum Engine — AI Radio Mesh Network",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--hardware", action="store_true",
                        help="Use real RTL-SDR hardware (default: simulation)")
    parser.add_argument("--demo", action="store_true",
                        help="Run a quick demo and exit")
    parser.add_argument("--cycles", type=int, default=0,
                        help="Number of cycles (0 = infinite)")
    parser.add_argument("--node-id", default="NODE_001",
                        help="This node's identifier")
    parser.add_argument("--gateway", action="store_true",
                        help="Run as gateway node (has internet access)")
    parser.add_argument("--freq", type=float, default=433e6,
                        help="Center frequency in Hz (default: 433 MHz)")
    args = parser.parse_args()

    engine = SpectrumEngine(
        node_id=args.node_id,
        simulate=not args.hardware,
        center_freq=args.freq,
        is_gateway=args.gateway,
    )

    if args.demo:
        print("Running demo (10 cycles)...\n")
        engine.run(cycles=10, interval=0.3)
        engine.simulate_bitcoin_transfer()
        print("\nDemo complete.")
        return

    engine.run(cycles=args.cycles)


if __name__ == "__main__":
    main()
