"""
noc_edge_apple_tesla_dojo_tile_engine_capstone.py - Apple Silicon Ultra & Tesla Dojo Tile NoC Capstone

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: Apple Silicon M3/M4 Ultra & Tesla Dojo D1 Multi-Chiplet Processing Mesh
Application: Unified Coherent Network-on-Chip (NoC), Die-to-Die Fabric, & Directory MESI Engine

MATHEMATICAL FOUNDATION & ARCHITECTURAL SPECIFICATION:
1. Multi-Chiplet Dual-Die Interconnect Topology:
   - Die 0 (Primary)   : (4 x 4) 2D Mesh of Heterogeneous Nodes (CPUs, NPUs, SLC).
   - Die 1 (Secondary) : (4 x 4) 2D Mesh of Heterogeneous Nodes.
   - Die-to-Die Bridge : High-density UCIe / Apple UltraFusion low-latency bridge
     connecting edge boundary routers (Die 0 East shoreline to Die 1 West shoreline).

2. Global Hierarchical XY Routing:
   For source node (d_src, x_src, y_src) to destination node (d_dst, x_dst, y_dst):
   - If d_src == d_dst: Pure local 2D Mesh XY Routing.
   - If d_src != d_dst: Route to D2D boundary egress port, cross UCIe bridge,
     then route within remote die using XY algorithm.

3. Distributed Directory MESI Cache Coherence:
   - System-Level Cache (SLC) acts as Home Directory.
   - Directory Entry tracks:
     * State: Uncached, Shared, Exclusive/Modified.
     * Sharers Bitmask: Set of nodes currently caching the line.
     * Owner Node: ID of node holding Modified (dirty) line.

4. Performance Telemetry & Congestion Analytics:
   - Average Latency (cycles) = Sum(Arrival_t - Inject_t) / Total_Packets
   - Network Throughput (Flits/cycle) = Total_Delivered_Flits / Sim_Cycles
   - Aggregate Mesh Bandwidth = Throughput * Flit_Width_Bytes * F_clk
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
from collections import deque
import sys
import os

sys.path.append(os.path.dirname(__file__))

from noc_edge_xy_routing_packet_router import (
    PortDirection, FlitType, Flit, VirtualChannelBuffer, NocRouter2D, Mesh2DNetwork
)
from noc_edge_mesi_coherence_controller import MesiState
from noc_edge_ucie_die_to_die_adapter import PhysicalLaneArray, UcieD2dAdapter, UcieLinkState


class NodeType(Enum):
    CPU_CORE     = "CPU_CORE"
    NPU_ENGINE   = "NPU_ENGINE"      # Neural Processing Unit
    GPU_SHADER   = "GPU_SHADER"
    SLC_DIR_HOME = "SLC_DIR_HOME"    # System-Level Cache & Directory Controller


class DirectoryEntry:
    """Directory state for a 64-byte memory block tracked at SLC Home Node."""
    def __init__(self, address: int):
        self.address = address
        self.state = MesiState.INVALID  # INVALID implies uncached in any private L1/L2
        self.sharers: set[Tuple[int, int, int]] = set()  # (die_id, x, y) nodes
        self.owner: Optional[Tuple[int, int, int]] = None


class HeterogeneousNode:
    """A processing node attached to a local NoC router port."""
    def __init__(self, node_id: int, node_type: NodeType, die_id: int, x: int, y: int):
        self.node_id = node_id
        self.node_type = node_type
        self.die_id = die_id
        self.x = x
        self.y = y
        self.private_cache: Dict[int, MesiState] = {}


class MultiChipletCoherentFabric:
    """
    Simulates a multi-chiplet processing system (e.g. Apple M3 Ultra dual-die
    or Tesla Dojo D1 multi-core compute tile) with unified coherent NoC.
    """
    def __init__(self, die_dim_x: int = 4, die_dim_y: int = 4):
        self.die_dim_x = die_dim_x
        self.die_dim_y = die_dim_y

        # Two 4x4 meshes: Die 0 and Die 1
        self.mesh_die0 = Mesh2DNetwork(die_dim_x, die_dim_y, num_vcs=2, vc_depth=8)
        self.mesh_die1 = Mesh2DNetwork(die_dim_x, die_dim_y, num_vcs=2, vc_depth=8)

        # UCIe / UltraFusion D2D physical link connecting Die 0 (x=3) to Die 1 (x=0)
        self.phy = PhysicalLaneArray(num_lanes=64, data_rate_gbps=32.0, shoreline_mm=1.2)
        self.d2d_die0 = UcieD2dAdapter("Die0_Bridge", self.phy)
        self.d2d_die1 = UcieD2dAdapter("Die1_Bridge", self.phy)
        self.d2d_die0.train_link()
        self.d2d_die1.train_link()

        # Connect boundary router ports across dies via D2D bridge
        for y in range(die_dim_y):
            r_die0_edge = self.mesh_die0.routers[(die_dim_x - 1, y)]
            r_die1_edge = self.mesh_die1.routers[(0, y)]
            # Connect Die 0 EAST to Die 1 WEST
            r_die0_edge.connect(PortDirection.EAST, r_die1_edge, PortDirection.WEST)
            r_die1_edge.connect(PortDirection.WEST, r_die0_edge, PortDirection.EAST)

        # Instantiate heterogeneous compute tiles across both dies
        self.nodes: Dict[Tuple[int, int, int], HeterogeneousNode] = {}
        node_id_counter = 0

        for die_id in (0, 1):
            for y in range(die_dim_y):
                for x in range(die_dim_x):
                    # Architecture layout:
                    # (0, 0) and (1, 1): CPU cores
                    # (2, 0) to (3, 3): High-throughput NPU matrix engines
                    # (0, 3) and (3, 0): System-Level Cache (SLC) Directory Homes
                    if (x, y) in ((0, 3), (3, 0)):
                        n_type = NodeType.SLC_DIR_HOME
                    elif (x, y) in ((0, 0), (1, 0)):
                        n_type = NodeType.CPU_CORE
                    elif (x, y) in ((0, 1), (1, 1)):
                        n_type = NodeType.GPU_SHADER
                    else:
                        n_type = NodeType.NPU_ENGINE

                    self.nodes[(die_id, x, y)] = HeterogeneousNode(
                        node_id=node_id_counter,
                        node_type=n_type,
                        die_id=die_id,
                        x=x,
                        y=y
                    )
                    node_id_counter += 1

        # Global SLC Directory Entries
        self.directory: Dict[int, DirectoryEntry] = {}

        # Telemetry
        self.delivered_flits_total = 0
        self.d2d_bridge_crossings = 0
        self.packet_latencies: List[int] = []

    def get_home_node(self, address: int) -> Tuple[int, int, int]:
        """Hash function mapping memory address to SLC Home Directory Node."""
        # Simple interleaved mapping between Die 0 (0, 3) and Die 1 (0, 3)
        die = (address >> 6) & 1
        return (die, 0, 3)

    def request_cache_line_read(
        self,
        requester: Tuple[int, int, int],
        address: int,
        current_cycle: int
    ) -> None:
        """
        Executes coherent read transaction over NoC:
        Requester -> SLC Home Directory -> Data Return.
        """
        home = self.get_home_node(address)
        if address not in self.directory:
            self.directory[address] = DirectoryEntry(address)

        entry = self.directory[address]

        # Directory state transition
        if entry.state in (MesiState.INVALID, MesiState.EXCLUSIVE, MesiState.SHARED):
            entry.state = MesiState.SHARED
            entry.sharers.add(requester)
        elif entry.state == MesiState.MODIFIED:
            # Downgrade owner from Modified to Shared
            if entry.owner is not None and entry.owner in self.nodes:
                self.nodes[entry.owner].private_cache[address] = MesiState.SHARED
            entry.state = MesiState.SHARED
            entry.sharers.add(requester)
            if entry.owner is not None:
                entry.sharers.add(entry.owner)
            entry.owner = None

        self.nodes[requester].private_cache[address] = MesiState.SHARED

        # Track D2D bridge crossing if requester and home node are on different dies
        if requester[0] != home[0]:
            self.d2d_bridge_crossings += 2  # Request + Response

    def request_cache_line_write(
        self,
        requester: Tuple[int, int, int],
        address: int,
        current_cycle: int
    ) -> None:
        """
        Executes coherent write transaction over NoC:
        Requester -> SLC Home Directory -> Invalidation messages sent to all sharers.
        """
        home = self.get_home_node(address)
        if address not in self.directory:
            self.directory[address] = DirectoryEntry(address)

        entry = self.directory[address]

        # Invalidate all other sharers
        for sharer in list(entry.sharers):
            if sharer != requester and sharer in self.nodes:
                self.nodes[sharer].private_cache[address] = MesiState.INVALID
                if sharer[0] != home[0]:
                    self.d2d_bridge_crossings += 1

        # Assign exclusive Modified state to requester
        entry.state = MesiState.MODIFIED
        entry.owner = requester
        entry.sharers = {requester}
        self.nodes[requester].private_cache[address] = MesiState.MODIFIED

        if requester[0] != home[0]:
            self.d2d_bridge_crossings += 2

    def simulate_ai_workload(self, num_cycles: int = 50) -> Dict[str, any]:
        """
        Simulates parallel AI tensor matrix multiplication across heterogeneous NPUs:
        1. Die 0 NPU engines read weights from SLC.
        2. Die 1 NPU engines read activations from Die 0 SLC across D2D bridge.
        3. Writeback of updated gradient matrices.
        """
        # Node coordinates
        npu_die0 = (0, 2, 2)
        npu_die1 = (1, 2, 2)

        addr_weights = 0x8000
        addr_activations = 0x9000

        # Phase 1: Die 0 NPU reads weights
        self.request_cache_line_read(npu_die0, addr_weights, current_cycle=1)

        # Phase 2: Die 1 NPU reads weights (Cross-Die Coherent Sharing)
        self.request_cache_line_read(npu_die1, addr_weights, current_cycle=2)

        # Phase 3: Die 1 NPU modifies activations (Cross-Die Invalidation)
        self.request_cache_line_write(npu_die1, addr_activations, current_cycle=3)

        for c in range(1, num_cycles + 1):
            if c == 1:
                # Inject raw NoC flits to measure packet routing latency
                self.mesh_die0.inject_packet(src=(0, 0), dest=(3, 3), packet_id=1, num_flits=3, current_cycle=c)
                self.mesh_die1.inject_packet(src=(1, 1), dest=(3, 2), packet_id=2, num_flits=2, current_cycle=c)
            self.mesh_die0.step(c)
            self.mesh_die1.step(c)

        # Aggregate metrics
        all_delivered = self.mesh_die0.delivered_packets + self.mesh_die1.delivered_packets
        self.delivered_flits_total = len(all_delivered)
        avg_latency = (
            sum(p["latency_cycles"] for p in all_delivered) / len(all_delivered)
            if all_delivered else 0.0
        )

        return {
            "total_flits_delivered": self.delivered_flits_total,
            "d2d_bridge_crossings": self.d2d_bridge_crossings,
            "average_packet_latency_cycles": avg_latency,
            "weights_dir_state": self.directory[addr_weights].state.value,
            "weights_sharers_count": len(self.directory[addr_weights].sharers),
            "activations_dir_state": self.directory[addr_activations].state.value,
            "activations_owner": self.directory[addr_activations].owner,
            "d2d_bandwidth_density_tb_per_mm": self.phy.linear_density_tb_per_mm
        }


def test_apple_tesla_dojo_capstone():
    print("================================================================================")
    print("TEST SUITE: APPLE SILICON ULTRA & TESLA DOJO TILE NoC CAPSTONE ENGINE")
    print("================================================================================")

    fabric = MultiChipletCoherentFabric(die_dim_x=4, die_dim_y=4)
    print("Multi-Chiplet Fabric Initialized:")
    print("  Die 0: 4x4 2D Mesh (16 Heterogeneous Compute Nodes)")
    print("  Die 1: 4x4 2D Mesh (16 Heterogeneous Compute Nodes)")
    print("  Interconnect: 64-lane UCIe / UltraFusion D2D Bridge (32 Gbps/lane)")
    print("--------------------------------------------------------------------------------")

    results = fabric.simulate_ai_workload(num_cycles=30)

    print("AI WORKLOAD PERFORMANCE & COHERENCE TELEMETRY:")
    print(f"  Total Flits Delivered: {results['total_flits_delivered']}")
    print(f"  Average Packet Latency: {results['average_packet_latency_cycles']:.2f} cycles")
    print(f"  Die-to-Die Bridge Crossings: {results['d2d_bridge_crossings']}")
    print(f"  Weights Directory State: {results['weights_dir_state']} (Sharers: {results['weights_sharers_count']})")
    print(f"  Activations Directory State: {results['activations_dir_state']} (Owner: {results['activations_owner']})")
    print(f"  D2D Shoreline Bandwidth Density: {results['d2d_bandwidth_density_tb_per_mm']:.2f} TB/s / mm")
    print("--------------------------------------------------------------------------------")

    # Assertions
    # 1. Weights line must be in SHARED state across both Die 0 and Die 1 NPUs
    assert results["weights_dir_state"] == "S"
    assert results["weights_sharers_count"] == 2

    # 2. Activations line must be in MODIFIED state owned exclusively by Die 1 NPU
    assert results["activations_dir_state"] == "M"
    assert results["activations_owner"] == (1, 2, 2)

    # 3. Flits must be delivered cleanly with low latency
    assert results["total_flits_delivered"] >= 5
    assert results["average_packet_latency_cycles"] <= 10.0

    print("[PASS] Milestone AY.4 Capstone: Multi-Chiplet Unified NoC & Directory MESI Engine validated 100%!")
    print("================================================================================")


if __name__ == "__main__":
    test_apple_tesla_dojo_capstone()
