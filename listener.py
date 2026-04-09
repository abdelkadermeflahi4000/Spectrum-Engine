"""
SPECTRUM ENGINE — Layer 1: Listener
====================================
Captures raw IQ samples from SDR hardware.
Falls back to realistic simulation if no hardware detected.
"""

import numpy as np
import time
from dataclasses import dataclass


@dataclass
class SignalSample:
    """A captured block of radio signal data."""
    timestamp: float
    center_freq: float      # Hz  e.g. 100e6 = 100 MHz
    sample_rate: float      # samples/sec
    samples: np.ndarray     # complex IQ samples
    source: str             # "hardware" or "sim:TYPE"

    @property
    def duration(self):
        return len(self.samples) / self.sample_rate

    @property
    def power_db(self):
        p = np.mean(np.abs(self.samples) ** 2)
        return round(10 * np.log10(p + 1e-10), 2)


class SignalListener:
    """
    Listens to the electromagnetic spectrum.

    With hardware:  plug in RTL-SDR USB dongle (~$25) and set simulate=False
    Without hardware: set simulate=True for realistic generated signals
    """

    SIGNAL_TYPES = [
        "FM_RADIO", "AM_RADIO", "WIFI_24GHZ",
        "BLUETOOTH", "LORA_MESH", "UNKNOWN", "NOISE"
    ]

    def __init__(
        self,
        center_freq: float = 100e6,    # 100 MHz default (FM band)
        sample_rate: float = 2.048e6,  # 2 MHz bandwidth
        gain: float = 40.0,
        simulate: bool = True,          # True = no hardware needed
    ):
        self.center_freq = center_freq
        self.sample_rate = sample_rate
        self.gain = gain
        self.simulate = simulate
        self._sdr = None

        if not simulate:
            self._init_hardware()

    def _init_hardware(self):
        """Attempt connection to RTL-SDR USB device."""
        try:
            from rtlsdr import RtlSdr
            self._sdr = RtlSdr()
            self._sdr.sample_rate = self.sample_rate
            self._sdr.center_freq = self.center_freq
            self._sdr.gain = self.gain
            print("[OK] RTL-SDR hardware connected")
        except Exception as e:
            print(f"[INFO] No hardware found ({e}) — using simulation")
            self.simulate = True

    def capture(self, num_samples: int = 131072) -> SignalSample:
        """Capture one block of IQ samples."""
        if self.simulate:
            return self._simulate_signal(num_samples)
        raw = self._sdr.read_samples(num_samples)
        return SignalSample(
            timestamp=time.time(),
            center_freq=self.center_freq,
            sample_rate=self.sample_rate,
            samples=np.array(raw),
            source="hardware"
        )

    def _simulate_signal(self, num_samples: int) -> SignalSample:
        """Generate realistic IQ data for development & testing."""
        t = np.linspace(0, num_samples / self.sample_rate, num_samples)
        stype = np.random.choice(self.SIGNAL_TYPES, p=[0.2,0.1,0.15,0.15,0.2,0.1,0.1])
        noise = (np.random.normal(0, 0.08, num_samples) +
                 1j * np.random.normal(0, 0.08, num_samples))

        if stype == "FM_RADIO":
            # Strong AM-modulated carrier — wide bandwidth
            carrier = 1.5 * np.exp(2j * np.pi * 0.3e6 * t)
            mod = np.sin(2 * np.pi * 1200 * t)
            sig = carrier * (1 + 0.35 * mod)

        elif stype == "BLUETOOTH":
            # Frequency-hopping bursts
            sig = np.zeros(num_samples, dtype=complex)
            hop = num_samples // 20
            for i in range(20):
                f = np.random.uniform(-0.5e6, 0.5e6)
                s = i * hop
                sig[s:s + hop // 2] = 0.8 * np.exp(2j * np.pi * f * t[s:s + hop // 2])

        elif stype == "LORA_MESH":
            # Chirp spread spectrum — rising frequency sweep
            chirp_rate = self.sample_rate / num_samples
            phase = 2 * np.pi * chirp_rate * t ** 2 / 2
            sig = 0.9 * np.exp(1j * phase)

        elif stype == "WIFI_24GHZ":
            # OFDM multi-carrier with duty cycling
            subs = [np.exp(2j * np.pi * f * t) for f in np.linspace(-0.5e6, 0.5e6, 52)]
            sig = 0.6 * sum(subs) / 52
            sig = sig * (np.random.rand(num_samples) > 0.35)

        elif stype == "AM_RADIO":
            carrier = np.exp(2j * np.pi * 0.1e6 * t)
            audio = 0.5 * np.sin(2 * np.pi * 800 * t)
            sig = (1 + audio) * carrier

        else:
            sig = np.zeros(num_samples, dtype=complex)

        return SignalSample(
            timestamp=time.time(),
            center_freq=self.center_freq,
            sample_rate=self.sample_rate,
            samples=sig + noise,
            source=f"sim:{stype}"
        )

    def close(self):
        if self._sdr:
            self._sdr.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
