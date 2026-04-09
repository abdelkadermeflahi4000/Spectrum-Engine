"""
SPECTRUM ENGINE — Transport: Bitcoin Offline Relay
====================================================
Relays Bitcoin transactions through the mesh network.
No internet required. No bank required.

How it works:
1. User creates a signed Bitcoin transaction (offline)
2. Transaction bytes → encoded as mesh packet
3. Packet hops through nodes until it reaches one with internet
4. That node broadcasts to Bitcoin network (Mempool)

This enables Bitcoin in:
- War zones
- Areas with censored internet
- Remote locations (deserts, forests, mountains)
- Disaster recovery scenarios
"""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Optional
from mesh.router import MeshPacket


@dataclass
class BitcoinTransaction:
    """
    A raw Bitcoin transaction ready to broadcast.

    In production: create with bitcoin libraries (python-bitcoinlib, etc.)
    Here we simulate the structure for testing.
    """
    txid: str               # transaction hash
    raw_hex: str            # raw serialized transaction (hex)
    size_bytes: int         # transaction size
    fee_sats: int           # miner fee in satoshis
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

    @classmethod
    def simulate(cls, amount_sats: int = 10000, fee_sats: int = 500):
        """Create a simulated Bitcoin transaction for testing."""
        # In reality: use python-bitcoinlib to construct a real signed tx
        fake_raw = hashlib.sha256(f"tx:{amount_sats}:{time.time()}".encode()).hexdigest() * 4
        txid = hashlib.sha256(fake_raw.encode()).hexdigest()
        return cls(
            txid=txid,
            raw_hex=fake_raw,
            size_bytes=len(fake_raw) // 2,
            fee_sats=fee_sats,
        )

    def to_bytes(self) -> bytes:
        return json.dumps({
            "txid": self.txid,
            "raw": self.raw_hex,
            "fee": self.fee_sats,
        }).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> "BitcoinTransaction":
        d = json.loads(data.decode())
        return cls(
            txid=d["txid"],
            raw_hex=d["raw"],
            size_bytes=len(d["raw"]) // 2,
            fee_sats=d["fee"],
        )


class BitcoinMeshRelay:
    """
    Sends Bitcoin transactions through the mesh network.

    Usage:
        relay = BitcoinMeshRelay(node_id="NODE_001")
        tx = BitcoinTransaction.simulate(amount_sats=50000)
        packet = relay.create_packet(tx, destination="GATEWAY_NODE")
        router.forward(packet)
    """

    def __init__(self, node_id: str, is_gateway: bool = False):
        self.node_id = node_id
        self.is_gateway = is_gateway  # True = this node has internet, will broadcast
        self.pending_txs: dict = {}   # txid → BitcoinTransaction
        self.broadcast_count: int = 0

        mode = "GATEWAY (will broadcast to Bitcoin network)" if is_gateway else "RELAY"
        print(f"[OK] Bitcoin relay ready | Node: {node_id} | Mode: {mode}")

    def create_packet(
        self,
        tx: BitcoinTransaction,
        destination: str = "ANY_GATEWAY",
    ) -> MeshPacket:
        """Wrap a Bitcoin transaction in a mesh packet."""
        self.pending_txs[tx.txid] = tx
        packet = MeshPacket.create(
            source=self.node_id,
            dest=destination,
            data=tx.to_bytes(),
            ptype="BITCOIN_TX",
        )
        print(f"[BTC] Created mesh packet for tx {tx.txid[:16]}... "
              f"({tx.size_bytes} bytes, {tx.fee_sats} sats fee)")
        return packet

    def receive_packet(self, packet: MeshPacket) -> Optional[str]:
        """
        Called when a BITCOIN_TX packet arrives at this node.
        If this node is a gateway, broadcasts to Bitcoin network.

        Returns: txid if broadcast, None otherwise
        """
        if packet.packet_type != "BITCOIN_TX":
            return None

        tx = BitcoinTransaction.from_bytes(packet.payload)

        if self.is_gateway:
            return self._broadcast_to_network(tx)
        else:
            print(f"[BTC] Relayed tx {tx.txid[:16]}... (not a gateway, passing along)")
            return None

    def _broadcast_to_network(self, tx: BitcoinTransaction) -> str:
        """
        Broadcast transaction to Bitcoin network via internet.
        In production: POST to mempool.space API or your own Bitcoin node.
        """
        print(f"[BTC] Broadcasting tx {tx.txid[:16]}... to Bitcoin network")

        # Production code:
        # import requests
        # r = requests.post(
        #     "https://mempool.space/api/tx",
        #     data=tx.raw_hex,
        #     headers={"Content-Type": "text/plain"}
        # )
        # return r.text  # returns txid

        # Simulation:
        time.sleep(0.1)
        self.broadcast_count += 1
        print(f"[BTC] ✓ Transaction confirmed in mempool: {tx.txid[:16]}...")
        return tx.txid

    def status(self) -> dict:
        return {
            "node_id": self.node_id,
            "is_gateway": self.is_gateway,
            "pending_transactions": len(self.pending_txs),
            "total_broadcast": self.broadcast_count,
        }
