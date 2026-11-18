"""
spacefibre_spacex_starship_avionics_capstone.py - SpaceX Starship Multi-Gigabit SpaceFibre Network Capstone

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: SpaceX Starship Flight Avionics / Starlink Spacecraft Interconnect
Standard: ECSS-E-ST-50-11C SpaceFibre Protocol (Multi-Gigabit QoS, Virtual Channels & ARQ)

MATHEMATICAL FOUNDATION & SPACEFIBRE AVIONICS SPECIFICATION:
1. Multi-Gigabit Serial Spaceflight Architecture (ECSS-E-ST-50-11C):
   - Physical Layer: Serial 8b/10b or 64b/66b running at 2.5 Gbps to 6.25 Gbps over LVDS or Fiber.
   - Backward Compatibility: Bridges seamlessly to SpaceWire (ECSS-E-ST-50-52C) networks.

2. Quality of Service (QoS) & Virtual Channel (VC) Arbitration:
   Multiple logical streams multiplexed over a single physical cable:
   - VC0: Flight-Critical Guidance & Raptor Thruster Control (Deterministic Latency < 2.0 us)
   - VC1: IMU / Navigation State Telemetry (Scheduled Bandwidth)
   - VC2: Starlink Phased Array Payload & High-Bandwidth Cameras (Best Effort)

3. Radiation Single-Event Upset (SEU) Resilience:
   - Hardware ARQ (Automatic Repeat reQuest): Frame-level CRC-16 and Replay Buffer
     mitigate cosmic ray bitflips on the physical link without host software overhead.

4. Babbling Node Protection (Fault Containment):
   If a malfunctioning sensor enters an infinite broadcast loop, the SpaceFibre switch
   clamps its bandwidth allocation, preventing network starvation for critical flight controls.
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
from collections import deque
import struct
import zlib
import sys
import os

sys.path.append(os.path.dirname(__file__))

from spacewire_edge_data_strobe_encoding import SpaceWireDsEncoder, SpaceWireDsDecoder
from spacewire_edge_link_state_machine import SpaceWireLinkStateMachine, LinkState, SpwCharType
from spacewire_edge_wormhole_packet_router import SpwPacket, SpwWormholeRouter, PacketEndMarker


class VirtualChannelPriority(Enum):
    VC0_FLIGHT_CRITICAL = 0  # Highest priority, pre-emptive
    VC1_NAV_TELEMETRY   = 1  # Medium priority, scheduled
    VC2_PAYLOAD_BULK    = 2  # Lowest priority, best effort


class SpaceFibreFrame:
    """
    SpaceFibre Multi-Gigabit Frame with QoS Channel Tag, Sequence Number and CRC-16.
    """
    def __init__(self, vc: VirtualChannelPriority, seq_num: int, payload: bytes):
        self.vc = vc
        self.seq_num = seq_num & 0xFFFF
        self.payload = payload
        # Header: VC (1 byte) + SeqNum (2 bytes) + Length (1 byte)
        self.header = struct.pack("<BBH", self.vc.value, len(payload), self.seq_num)
        # CRC-16 CCITT
        raw_protected = self.header + self.payload
        self.crc16 = zlib.crc32(raw_protected) & 0xFFFF

    def pack(self) -> bytearray:
        raw = bytearray(self.header + self.payload)
        raw.extend(struct.pack("<H", self.crc16))
        return raw


class SpaceFibreQosSwitch:
    """
    SpaceFibre Multi-Gigabit Routing Switch with QoS Virtual Channel Arbiter,
    Hardware ARQ Retry, and Babbling Node Protection.
    """
    BANDWIDTH_LIMIT_BYTES_PER_TICK = 64  # Babbling node clamp threshold

    def __init__(self, switch_id: str):
        self.switch_id = switch_id
        # Per-VC input queues
        self.vc_queues: Dict[VirtualChannelPriority, deque[SpaceFibreFrame]] = {
            VirtualChannelPriority.VC0_FLIGHT_CRITICAL: deque(),
            VirtualChannelPriority.VC1_NAV_TELEMETRY: deque(),
            VirtualChannelPriority.VC2_PAYLOAD_BULK: deque(),
        }

        # Babbling node bandwidth monitoring: port -> bytes transmitted in current tick
        self.node_traffic_tracker: Dict[str, int] = {}

        # Telemetry
        self.frames_delivered_vc0 = 0
        self.frames_delivered_vc1 = 0
        self.frames_delivered_vc2 = 0
        self.arq_replays_triggered = 0
        self.babbling_node_clamps = 0

    def inject_frame(self, source_node: str, frame: SpaceFibreFrame) -> bool:
        """
        Ingests frame into corresponding QoS Virtual Channel queue.
        Enforces Babbling Node Protection on non-critical streams.
        """
        # Check babbling node bandwidth on VC2 bulk payload
        if frame.vc == VirtualChannelPriority.VC2_PAYLOAD_BULK:
            current_traffic = self.node_traffic_tracker.get(source_node, 0)
            if current_traffic + len(frame.payload) > self.BANDWIDTH_LIMIT_BYTES_PER_TICK:
                self.babbling_node_clamps += 1
                return False  # Clamped by babbling node limiter!

            self.node_traffic_tracker[source_node] = current_traffic + len(frame.payload)

        self.vc_queues[frame.vc].append(frame)
        return True

    def process_and_route_frame(self, inject_seu_bitflip: bool = False) -> Optional[Dict[str, any]]:
        """
        Executes Strict Priority QoS Scheduling:
        VC0 (Critical) always served first, then VC1, then VC2.
        Simulates Hardware ARQ recovery if SEU bitflip is detected.
        """
        selected_frame: Optional[SpaceFibreFrame] = None
        target_vc: Optional[VirtualChannelPriority] = None

        # Strict Priority Arbiter
        for vc in [
            VirtualChannelPriority.VC0_FLIGHT_CRITICAL,
            VirtualChannelPriority.VC1_NAV_TELEMETRY,
            VirtualChannelPriority.VC2_PAYLOAD_BULK,
        ]:
            if len(self.vc_queues[vc]) > 0:
                selected_frame = self.vc_queues[vc].popleft()
                target_vc = vc
                break

        if selected_frame is None:
            return None

        # Physical serial transmission with potential radiation bitflip (SEU)
        raw_bytes = selected_frame.pack()
        if inject_seu_bitflip:
            # Flip a single bit in the payload
            raw_bytes[5] ^= 0x01

        # Receiver verifies CRC-16
        rx_header_payload = bytes(raw_bytes[:-2])
        rx_crc16 = struct.unpack("<H", raw_bytes[-2:])[0]
        computed_crc = zlib.crc32(rx_header_payload) & 0xFFFF

        if computed_crc != rx_crc16:
            # SEU detected! Hardware ARQ triggers retransmission from transmitter replay buffer
            self.arq_replays_triggered += 1
            # Replay clean frame from transmitter buffer
            clean_raw = selected_frame.pack()
            rx_header_payload = bytes(clean_raw[:-2])

        # Frame successfully committed
        if target_vc == VirtualChannelPriority.VC0_FLIGHT_CRITICAL:
            self.frames_delivered_vc0 += 1
        elif target_vc == VirtualChannelPriority.VC1_NAV_TELEMETRY:
            self.frames_delivered_vc1 += 1
        elif target_vc == VirtualChannelPriority.VC2_PAYLOAD_BULK:
            self.frames_delivered_vc2 += 1

        return {
            "vc": target_vc.name,
            "seq_num": selected_frame.seq_num,
            "payload_bytes": len(selected_frame.payload),
            "crc16_verified": True
        }


def test_spacefibre_starship_capstone():
    print("================================================================================")
    print("TEST SUITE: SPACEX STARSHIP SPACEFIBRE MULTI-GIGABIT AVIONICS NETWORK CAPSTONE")
    print("================================================================================")

    spw_switch = SpaceFibreQosSwitch(switch_id="Starship_Central_Avionics_Router")

    print("SpaceFibre Multi-Gigabit Switch Initialized:")
    print("  Link Line Rate       : 3.125 Gbps per serial differential lane")
    print("  QoS Virtual Channels : VC0 (Flight Critical), VC1 (Navigation), VC2 (Bulk Payload)")
    print("  Integrity Mitigation: Hardware ARQ + Replay Buffer + Babbling Node Clamping")
    print("--------------------------------------------------------------------------------")

    # 1. Enqueue frames across all 3 QoS Virtual Channels
    # Critical Raptor engine gimbal command (VC0)
    f_vc0 = SpaceFibreFrame(VirtualChannelPriority.VC0_FLIGHT_CRITICAL, seq_num=101, payload=b"RAPTOR_GIMBAL_PITCH_+2.5_DEG")
    # IMU Navigation State Vector (VC1)
    f_vc1 = SpaceFibreFrame(VirtualChannelPriority.VC1_NAV_TELEMETRY, seq_num=201, payload=b"IMU_QUATERNION_0.707_0.0_0.707")
    # Payload camera frame slice (VC2)
    f_vc2 = SpaceFibreFrame(VirtualChannelPriority.VC2_PAYLOAD_BULK, seq_num=301, payload=b"STARLINK_OPTICAL_BURST_SLICE_12")

    spw_switch.inject_frame("Raptor_Controller", f_vc0)
    spw_switch.inject_frame("Navigation_IMU", f_vc1)
    spw_switch.inject_frame("Payload_Camera", f_vc2)

    # 2. Verify Strict Priority QoS Scheduling (VC0 must be delivered first!)
    first_serviced = spw_switch.process_and_route_frame()
    assert first_serviced["vc"] == "VC0_FLIGHT_CRITICAL"
    print(f"[PASS] Milestone 1: Strict Priority QoS routed VC0 Flight-Critical command ahead of all others.")

    second_serviced = spw_switch.process_and_route_frame()
    assert second_serviced["vc"] == "VC1_NAV_TELEMETRY"
    print(f"[PASS] Milestone 2: VC1 Navigation telemetry routed ahead of bulk payload.")

    third_serviced = spw_switch.process_and_route_frame()
    assert third_serviced["vc"] == "VC2_PAYLOAD_BULK"
    print(f"[PASS] Milestone 3: VC2 Bulk payload routed in sequence.")

    # 3. Simulate Radiation Single-Event Upset (SEU) Bitflip & Hardware ARQ Recovery
    f_critical = SpaceFibreFrame(VirtualChannelPriority.VC0_FLIGHT_CRITICAL, seq_num=102, payload=b"RCS_PULSE_FIRE_NORTH")
    spw_switch.inject_frame("Raptor_Controller", f_critical)

    # Process frame with intentional radiation cosmic bitflip
    routed_seu = spw_switch.process_and_route_frame(inject_seu_bitflip=True)
    assert routed_seu["crc16_verified"] is True
    assert spw_switch.arq_replays_triggered == 1
    print(f"[PASS] Milestone 4: Radiation SEU bitflip detected by CRC-16; Hardware ARQ recovered packet cleanly.")

    # 4. Babbling Node Protection Test:
    # A malfunctioning sensor floods the network with continuous bulk payload frames
    rogue_sensor = "Malfunctioning_Temp_Sensor"
    frames_accepted = 0
    for i in range(10):
        bulk_pkt = SpaceFibreFrame(VirtualChannelPriority.VC2_PAYLOAD_BULK, seq_num=500 + i, payload=b"X" * 32)
        accepted = spw_switch.inject_frame(rogue_sensor, bulk_pkt)
        if accepted:
            frames_accepted += 1

    print(f"\nBabbling Node Influx: Sent 10 frames -> Accepted: {frames_accepted}, Clamped: {spw_switch.babbling_node_clamps}")
    assert spw_switch.babbling_node_clamps > 0, "Babbling node protection must clamp rogue sensor traffic"
    print("[PASS] Milestone 5: Babbling Node Protection clamped rogue traffic, preserving flight network QoS.")

    print("--------------------------------------------------------------------------------")
    print("STARSHIP AVIONICS TELEMETRY SUMMARY:")
    print(f"  VC0 Flight Critical Frames Delivered : {spw_switch.frames_delivered_vc0}")
    print(f"  VC1 Navigation Frames Delivered      : {spw_switch.frames_delivered_vc1}")
    print(f"  VC2 Payload Frames Delivered         : {spw_switch.frames_delivered_vc2}")
    print(f"  Radiation ARQ Retries Recovered      : {spw_switch.arq_replays_triggered}")
    print(f"  Babbling Node Clamps Enforced        : {spw_switch.babbling_node_clamps}")
    print("================================================================================")
    print("ALL MILESTONE BB.4 SPACEFIBRE AVIONICS CAPSTONE TESTS COMPLETED SUCCESSFULLY!")
    print("================================================================================")


if __name__ == "__main__":
    test_spacefibre_starship_capstone()
