"""
spacewire_edge_wormhole_packet_router.py - SpaceWire Wormhole Routing Switch (ECSS-E-ST-50-52C)

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: SpaceX Starship Multi-Node Avionics / NASA James Webb Router Network
Standard: ECSS-E-ST-50-52C Clause 10 - SpaceWire Network Routing & Packet Formatting

MATHEMATICAL FOUNDATION & WORMHOLE SWITCHING ARCHITECTURE:
1. Low-Latency Wormhole Routing:
   Instead of buffering complete megabyte-sized spacecraft telemetry frames (Store-and-Forward),
   Wormhole switches begin forwarding the packet to the output port as soon as the first
   header byte is parsed. The packet snakes through the network like a worm:
   - Head byte sets up the crossbar switch connection.
   - Body bytes stream through with minimal sub-microsecond latency.
   - End of Packet (EOP) or Error End of Packet (EEP) marker tears down the connection.

2. SpaceWire Addressing Modes:
   - Path Addressing (1 to 31):
     Specifies the physical output port directly.
     The router consumes and STRIPS the first byte so subsequent switches read their own port!
   - Logical Addressing (32 to 255):
     Index into a programmable routing table: Routing_Table[Logical_Addr] -> Output_Port.
     Logical address byte is PRESERVED and forwarded to the destination endpoint.

3. Error End of Packet (EEP) Truncation:
   If an anomaly or disconnect occurs, EEP is transmitted to truncate the corrupt packet,
   purge downstream receiver FIFOs, and immediately release crossbar port locks.
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
from collections import deque


class PacketEndMarker(Enum):
    EOP = "EOP"  # Normal End of Packet
    EEP = "EEP"  # Error End of Packet (abnormal termination)


class SpwPacket:
    """Represents a SpaceWire telemetry packet."""
    def __init__(self, header_bytes: List[int], cargo_bytes: List[int], marker: PacketEndMarker = PacketEndMarker.EOP):
        self.header_bytes = list(header_bytes)
        self.cargo_bytes = list(cargo_bytes)
        self.marker = marker

    @property
    def full_byte_stream(self) -> List[int]:
        return self.header_bytes + self.cargo_bytes


class SpwWormholeRouter:
    """
    SpaceWire Non-Blocking Wormhole Crossbar Routing Switch.
    Supports Path Addressing, Logical Addressing, and EEP Abort Recovery.
    """
    def __init__(self, router_id: str, num_ports: int = 8):
        self.router_id = router_id
        self.num_ports = num_ports

        # Routing table for Logical Addresses (32 to 255): Logical_ID -> Output_Port
        self.routing_table: Dict[int, int] = {}

        # Crossbar connections: output_port -> active input_port
        self.crossbar_locks: Dict[int, Optional[int]] = {p: None for p in range(1, num_ports + 1)}

        # Port Input and Output FIFOs
        self.port_in_buffers: Dict[int, deque[int]] = {p: deque() for p in range(1, num_ports + 1)}
        self.port_out_buffers: Dict[int, List[Dict[str, any]]] = {p: [] for p in range(1, num_ports + 1)}

        # Performance counters
        self.packets_routed = 0
        self.packets_aborted_eep = 0

    def set_logical_route(self, logical_addr: int, output_port: int) -> None:
        """Configures routing table entry for a logical address."""
        assert 32 <= logical_addr <= 255, "Logical address must be in range [32, 255]"
        assert 1 <= output_port <= self.num_ports, f"Port must be in range [1, {self.num_ports}]"
        self.routing_table[logical_addr] = output_port

    def route_packet(self, in_port: int, packet: SpwPacket) -> Tuple[int, SpwPacket]:
        """
        Processes and wormhole-routes packet from input port to selected output port.
        Returns (out_port, modified_packet).
        """
        assert 1 <= in_port <= self.num_ports, "Invalid input port"
        stream = packet.full_byte_stream
        assert len(stream) > 0, "Packet stream cannot be empty"

        first_byte = stream[0]
        out_port: Optional[int] = None
        forwarded_cargo: List[int] = []

        if 1 <= first_byte <= 31:
            # Path Addressing: first byte specifies output port directly, and must be STRIPPED!
            out_port = first_byte
            assert out_port <= self.num_ports, f"Requested port {out_port} exceeds router port count"
            # Strip first byte
            forwarded_stream = stream[1:]
            routed_pkt = SpwPacket(header_bytes=[], cargo_bytes=forwarded_stream, marker=packet.marker)

        elif 32 <= first_byte <= 255:
            # Logical Addressing: look up in routing table, PRESERVE header byte!
            assert first_byte in self.routing_table, f"Unmapped logical address: 0x{first_byte:02X}"
            out_port = self.routing_table[first_byte]
            routed_pkt = SpwPacket(header_bytes=[first_byte], cargo_bytes=stream[1:], marker=packet.marker)
        else:
            raise ValueError(f"Invalid SpaceWire address byte: {first_byte}")

        # Check / Acquire Crossbar Lock
        assert self.crossbar_locks[out_port] is None or self.crossbar_locks[out_port] == in_port, \
            f"Port {out_port} is busy / locked by another input port"

        self.crossbar_locks[out_port] = in_port

        # Stream packet to output port
        self.port_out_buffers[out_port].append({
            "packet": routed_pkt,
            "marker": packet.marker.value,
            "bytes_count": len(routed_pkt.full_byte_stream)
        })

        if packet.marker == PacketEndMarker.EOP:
            self.packets_routed += 1
        elif packet.marker == PacketEndMarker.EEP:
            self.packets_aborted_eep += 1

        # Release Crossbar Lock upon receiving EOP / EEP
        self.crossbar_locks[out_port] = None

        return out_port, routed_pkt


def test_spacewire_wormhole_routing():
    print("================================================================================")
    print("TEST SUITE: SPACEWIRE WORMHOLE ROUTING SWITCH & ADDRESSING MODES")
    print("================================================================================")

    # 8-Port SpaceWire Router (e.g. Starship flight avionics crossbar)
    router = SpwWormholeRouter(router_id="Starship_Avionics_Router_1", num_ports=8)

    # 1. Path Addressing Verification (Source Routing):
    # Packet targets Output Port 3 directly. First byte = 0x03.
    # Cargo = [0xAA, 0xBB, 0xCC, 0xDD]
    payload_raw = [0xAA, 0xBB, 0xCC, 0xDD]
    path_pkt = SpwPacket(header_bytes=[3], cargo_bytes=payload_raw, marker=PacketEndMarker.EOP)

    out_port, routed_pkt = router.route_packet(in_port=1, packet=path_pkt)
    print(f"Path Addressing Test: Input Port=1 -> Routed to Output Port={out_port}")
    print(f"  Sent Header : {path_pkt.header_bytes}")
    print(f"  Sent Cargo  : {[hex(x) for x in path_pkt.cargo_bytes]}")
    print(f"  Routed Body : {[hex(x) for x in routed_pkt.cargo_bytes]}")

    assert out_port == 3
    # First byte '3' must have been stripped!
    assert routed_pkt.full_byte_stream == payload_raw
    print("[PASS] Milestone 1: Path Addressing selected Port 3 and stripped routing header byte.")

    # 2. Logical Addressing Verification:
    # Map Logical Address 0xFE (254: Starship Flight Guidance Computer) to Port 7
    router.set_logical_route(logical_addr=0xFE, output_port=7)
    logical_pkt = SpwPacket(header_bytes=[0xFE], cargo_bytes=[0x11, 0x22, 0x33], marker=PacketEndMarker.EOP)

    out_port_log, routed_log_pkt = router.route_packet(in_port=2, packet=logical_pkt)
    print(f"\nLogical Addressing Test: Input Port=2 -> Routed to Output Port={out_port_log}")
    print(f"  Routed Stream: {[hex(x) for x in routed_log_pkt.full_byte_stream]}")

    assert out_port_log == 7
    # Logical Address 0xFE must be PRESERVED in forwarded packet
    assert routed_log_pkt.full_byte_stream[0] == 0xFE
    assert routed_log_pkt.full_byte_stream[1:] == [0x11, 0x22, 0x33]
    print("[PASS] Milestone 2: Logical Addressing routed via table lookup and preserved destination address.")

    # 3. Error End of Packet (EEP) Truncation & Lock Release:
    # Packet sent with EEP marker due to mid-flight transmission fault
    corrupt_pkt = SpwPacket(header_bytes=[4], cargo_bytes=[0xDE, 0xAD], marker=PacketEndMarker.EEP)
    out_port_eep, routed_eep_pkt = router.route_packet(in_port=1, packet=corrupt_pkt)

    print(f"\nEEP Abort Test: Output Port={out_port_eep}, Marker={routed_eep_pkt.marker.value}")
    assert out_port_eep == 4
    assert routed_eep_pkt.marker == PacketEndMarker.EEP
    assert router.crossbar_locks[4] is None, "Crossbar port lock must be released immediately upon EEP"
    assert router.packets_aborted_eep == 1
    print("[PASS] Milestone 3: EEP marker propagated and crossbar locks released without deadlock.")

    print("--------------------------------------------------------------------------------")
    print("ROUTER PERFORMANCE TELEMETRY:")
    print(f"  Total Packets Routed Cleanly : {router.packets_routed}")
    print(f"  Total Packets Aborted via EEP: {router.packets_aborted_eep}")
    print("================================================================================")
    print("ALL MILESTONE BB.3 WORMHOLE ROUTING TESTS PASSED SUCCESSFULLY!")
    print("================================================================================")


if __name__ == "__main__":
    test_spacewire_wormhole_routing()
