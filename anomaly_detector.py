"""
SPECTRUM ENGINE — Anomaly Detector
=====================================
Watches the spectrum continuously.
Learns what is "normal" and alerts when something unusual appears.

This is the security layer — detects:
- Fake cell towers (IMSI Catchers)
- Unknown transmitters
- Jamming attempts
- New devices appearing in a known environment
"""

import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class AnomalyAlert:
    """Raised when something unusual is detected in the spectrum."""
    timestamp: float
    alert_type: str           # "NEW_SIGNAL", "POWER_SPIKE", "UNKNOWN_DEVICE", "JAMMING"
    severity: str             # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    frequency_hz: float
    anomaly_score: float
    raw_features: dict = field(default_factory=dict)

    def __str__(self):
        icons = {"LOW": "ℹ", "MEDIUM": "⚠", "HIGH": "🔴", "CRITICAL": "🚨"}
        icon = icons.get(self.severity, "?")
        freq_mhz = self.frequency_hz / 1e6
        return (f"{icon} [{self.severity}] {self.alert_type} "
                f"at {freq_mhz:.2f} MHz — {self.description} "
                f"(score: {self.anomaly_score:.2f})")


class AnomalyDetector:
    """
    Statistical anomaly detection for the radio spectrum.

    Strategy:
    1. Build a baseline of "normal" signal patterns over time
    2. Compare new observations against the baseline
    3. Alert when deviation exceeds threshold

    Uses rolling statistics — no ML training required.
    Works from day one, improves over time.
    """

    def __init__(
        self,
        baseline_window: int = 100,    # samples to build baseline
        alert_threshold: float = 2.5,  # standard deviations from mean
        history_size: int = 500,       # rolling history length
    ):
        self.baseline_window = baseline_window
        self.alert_threshold = alert_threshold

        # Rolling history of observed features
        self.power_history = deque(maxlen=history_size)
        self.bandwidth_history = deque(maxlen=history_size)
        self.peak_freq_history = deque(maxlen=history_size)

        # Known signal fingerprints (learned over time)
        self.known_signals: dict = {}

        # Alert log
        self.alerts: list[AnomalyAlert] = []

        self._baseline_ready = False

    @property
    def baseline_ready(self) -> bool:
        return len(self.power_history) >= self.baseline_window

    def observe(self, features: dict, classification_result=None) -> Optional[AnomalyAlert]:
        """
        Process one observation. Update baseline. Return alert if anomaly detected.

        Args:
            features: dict from preprocessor.extract_features()
            classification_result: optional ClassificationResult

        Returns:
            AnomalyAlert if anomaly detected, None otherwise
        """
        power = features.get("power_db", 0)
        bandwidth = features.get("bandwidth_est_hz", 0)
        peak_freq = features.get("peak_freq_hz", 0)

        # Update rolling history
        self.power_history.append(power)
        self.bandwidth_history.append(bandwidth)
        self.peak_freq_history.append(peak_freq)

        if not self.baseline_ready:
            return None  # Still building baseline

        # ── Check for anomalies ──────────────────────────

        alert = None

        # 1. Power spike detection
        power_mean = np.mean(self.power_history)
        power_std = np.std(self.power_history) + 1e-6
        power_z = abs(power - power_mean) / power_std

        if power_z > self.alert_threshold * 2:
            alert = AnomalyAlert(
                timestamp=time.time(),
                alert_type="POWER_SPIKE",
                severity="HIGH",
                description=f"Power {power:.1f}dB vs baseline {power_mean:.1f}dB ({power_z:.1f}σ)",
                frequency_hz=features.get("peak_freq_hz", 0),
                anomaly_score=min(1.0, power_z / 10),
                raw_features=features,
            )

        # 2. Unknown signal type
        elif classification_result and classification_result.is_anomaly:
            alert = AnomalyAlert(
                timestamp=time.time(),
                alert_type="UNKNOWN_DEVICE",
                severity="MEDIUM",
                description=(f"Unrecognized signal pattern "
                             f"(best guess: {classification_result.signal_type} "
                             f"at {classification_result.confidence:.0%})"),
                frequency_hz=features.get("peak_freq_hz", 0),
                anomaly_score=classification_result.anomaly_score,
                raw_features=features,
            )

        # 3. Bandwidth anomaly (possible jamming)
        elif len(self.bandwidth_history) > 10:
            bw_mean = np.mean(self.bandwidth_history)
            bw_std = np.std(self.bandwidth_history) + 1e-6
            bw_z = abs(bandwidth - bw_mean) / bw_std

            if bw_z > self.alert_threshold * 1.5:
                alert = AnomalyAlert(
                    timestamp=time.time(),
                    alert_type="JAMMING_SUSPECTED",
                    severity="CRITICAL",
                    description=f"Abnormal bandwidth {bandwidth/1e3:.0f}kHz vs baseline {bw_mean/1e3:.0f}kHz",
                    frequency_hz=features.get("peak_freq_hz", 0),
                    anomaly_score=min(1.0, bw_z / 8),
                    raw_features=features,
                )

        if alert:
            self.alerts.append(alert)

        return alert

    def get_environment_summary(self) -> dict:
        """Return a summary of the current radio environment."""
        if not self.baseline_ready:
            return {"status": "building_baseline", "samples": len(self.power_history)}

        return {
            "status": "monitoring",
            "samples_observed": len(self.power_history),
            "avg_power_db": round(float(np.mean(self.power_history)), 2),
            "power_std_db": round(float(np.std(self.power_history)), 2),
            "total_alerts": len(self.alerts),
            "recent_alerts": [str(a) for a in self.alerts[-5:]],
        }

    def reset_baseline(self):
        """Clear learned baseline — use when moving to a new location."""
        self.power_history.clear()
        self.bandwidth_history.clear()
        self.peak_freq_history.clear()
        self.alerts.clear()
        print("[INFO] Baseline reset — rebuilding...")
