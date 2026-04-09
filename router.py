"""
SPECTRUM ENGINE — Layer 3: Mesh Router
========================================
AI-guided mesh network routing.

Each node knows:
- Which neighbors exist
- Signal quality to each neighbor
- Current anomaly status of each link

The router picks the best path considering all factors.
No central server. No internet. Pure peer-to-peer.
"""

import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MeshNode:
    """Represents one node in the mesh network."""
    node_id: str
    frequency_hz: float
    last_seen: float = field(default_factory=time.time)
    signal_quality: float = 1.0   # 0.0 = no signal, 1.0 = perfect
    anomaly_score: float = 0.0    # from AI classifier
    is_trusted: bool = True
    hops_away: int = 0

    @property
    def is_active(self) -> bool:
        return (time.time() - self.last_seen) < 60  # seen in last 60s

    @property
    def route_score(self) -> float:
        """
        Combined score for routing decisions.
        Higher = better path to use.
        """
        if not self.is_active:
            return 0.0
        if not self.is_trusted:
            return 0.0
        # Penalize hops and anomalies, reward signal quality
        return self.signal_quality * (1 - self.anomaly_score) * (1 / (self.hops_away + 1))


@dataclass
class MeshPacket:
    """A data packet traveling through the mesh."""
    packet_id: str
    source_id: str
    destination_id: str
    payload: bytes
    packet_type: str           # "MESSAGE", "BITCOIN_TX", "IOT_DATA", "BEACON"
    created_at: float = field(default_factory=time.time)
    ttl: int = 10              # max hops before dropping
    hops: list = field(default_factory=list)
    encrypted: bool = True

    @classmethod
    def create(cls, source: str, dest: str, data: bytes, ptype: str = "MESSAGE"):
        pid = hashlib.sha256(f"{source}{dest}{time.time()}".encode()).hexdigest()[:16]
        return cls(packet_id=pid, source_id=source, destination_id=dest,
                   payload=data, packet_type=ptype)

    def add_hop(self, node_id: str):
        self.hops.append(node_id)
        self.ttl -= 1

    @property
    def is_expired(self) -> bool:
        return self.ttl <= 0 or (time.time() - self.created_at) > 300

    def to_dict(self) -> dict:
        return {
            "id": self.packet_id,
            "src": self.source_id,
            "dst": self.destination_id,
            "type": self.packet_type,
            "ttl": self.ttl,
            "hops": self.hops,
            "size_bytes": len(self.payload),
        }


class MeshRouter:
    """
    Intelligent mesh network router.

    Manages node discovery, routing table, and packet forwarding.
    Uses AI anomaly scores to avoid compromised nodes.
    """

    def __init__(self, node_id: str, broadcast_freq: float = 433e6):
        self.node_id = node_id
        self.broadcast_freq = broadcast_freq
        self.routing_table: dict[str, MeshNode] = {}
        self.packet_cache: set = set()         # seen packet IDs (dedup)
        self.forwarded_count: int = 0
        self.dropped_count: int = 0

        print(f"[OK] Mesh node started: {node_id}")

    def discover_node(
        self,
        node_id: str,
        frequency: float,
        signal_quality: float = 1.0,
        anomaly_score: float = 0.0,
        hops: int = 1,
    ) -> MeshNode:
        """Register or update a neighbor node."""
        node = MeshNode(
            node_id=node_id,
            frequency_hz=frequency,
            last_seen=time.time(),
            signal_quality=signal_quality,
            anomaly_score=anomaly_score,
            hops_away=hops,
            is_trusted=anomaly_score < 0.7,  # distrust anomalous nodes
        )
        self.routing_table[node_id] = node
        return node

    def update_anomaly_score(self, node_id: str, score: float):
        """AI classifier detected something — update node trust."""
        if node_id in self.routing_table:
            self.routing_table[node_id].anomaly_score = score
            self.routing_table[node_id].is_trusted = score < 0.7
            if score > 0.7:
                print(f"[WARN] Node {node_id} flagged as untrusted (anomaly: {score:.2f})")

    def find_best_path(self, destination_id: str) -> Optional[list[str]]:
        """
        Find the best route to a destination node.
        Considers: signal quality, anomaly scores, hop count.

        Returns ordered list of node IDs forming the path, or None if unreachable.
        """
        if destination_id not in self.routing_table:
            return None

        dest_node = self.routing_table[destination_id]

        if not dest_node.is_active:
            print(f"[WARN] Destination {destination_id} is offline")
            return None

        if not dest_node.is_trusted:
            print(f"[WARN] Destination {destination_id} is not trusted — route blocked")
            return None

        # For now: direct path (multi-hop routing in Phase 2)
        # Future: Dijkstra's algorithm weighted by route_score
        return [self.node_id, destination_id]

    def should_forward(self, packet: MeshPacket) -> bool:
        """Decide if this node should forward a packet."""
        if packet.packet_id in self.packet_cache:
            return False  # Already seen
        if packet.is_expired:
            self.dropped_count += 1
            return False
        if packet.source_id == self.node_id:
            return False  # Own packet
        return True

    def forward(self, packet: MeshPacket) -> bool:
        """Forward a packet through the mesh."""
        if not self.should_forward(packet):
            return False

        self.packet_cache.add(packet.packet_id)
        packet.add_hop(self.node_id)
        self.forwarded_count += 1

        path = self.find_best_path(packet.destination_id)
        if path:
            print(f"[MESH] Forwarding {packet.packet_type} → {packet.destination_id} "
                  f"via {' → '.join(path)}")
            return True
        else:
            print(f"[MESH] No route to {packet.destination_id} — broadcasting")
            return True  # Flood to all neighbors

    def get_active_nodes(self) -> list[MeshNode]:
        """Return all currently active neighbor nodes."""
        return [n for n in self.routing_table.values() if n.is_active]

    def get_trusted_nodes(self) -> list[MeshNode]:
        """Return active AND trusted nodes."""
        return [n for n in self.get_active_nodes() if n.is_trusted]

    def network_status(self) -> dict:
        active = self.get_active_nodes()
        trusted = self.get_trusted_nodes()
        return {
            "node_id": self.node_id,
            "total_known_nodes": len(self.routing_table),
            "active_nodes": len(active),
            "trusted_nodes": len(trusted),
            "packets_forwarded": self.forwarded_count,
            "packets_dropped": self.dropped_count,
            "avg_signal_quality": round(
                sum(n.signal_quality for n in active) / max(len(active), 1), 3
            ),
        }
