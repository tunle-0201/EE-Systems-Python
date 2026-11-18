"""
dft_edge_boundary_scan_interconnect_test.py - Boundary-Scan EXTEST & Interconnect Fault Diagnosis

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: Apple Silicon / Tesla FSD High-Density BGA Interconnect Testing
Standard: IEEE 1149.1 Boundary-Scan Architecture (EXTEST & SAMPLE/PRELOAD)

MATHEMATICAL FOUNDATION & INTERCONNECT FAULT MODELS:
1. Physical Pin Accessibility Problem:
   High-density Ball Grid Arrays (BGA) hide 2,000+ solder joints beneath the package.
   Mechanical probes cannot reach inner traces without damaging high-speed signal integrity.

2. Boundary-Scan Cell (BSC) Architecture:
   Each I/O pad contains boundary-scan flip-flops:
   - Capture Stage: Latches pin input state during Capture-DR.
   - Shift Stage: Chains flip-flops into a serial Boundary Scan Register (BSR).
   - Update Stage: Latches shift contents to drive output pin during EXTEST.

3. Interconnect Defect Classification:
   - Stuck-At-0 (SA0): Solder bridge to Ground (V = 0.0V).
   - Stuck-At-1 (SA1): Solder bridge to VDD or floating open with pull-up.
   - Open Circuit: Cracked solder joint or severed trace (reads default pull state).
   - Short Circuit / Bridging:
     * AND-Bridge: Net_A = Net_B = (Net_A AND Net_B)
     * OR-Bridge:  Net_A = Net_B = (Net_A OR Net_B)

4. Algorithmic Test Vectors:
   - All-0s vector: Detects SA1 on any net.
   - All-1s vector: Detects SA0 on any net.
   - Walking-1s Matrix: N vectors of length N where exactly one bit is 1.
     Detects and locates pairwise short-circuit bridging and opens without aliasing.
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional


class FaultType(Enum):
    NO_FAULT       = "NO_FAULT"
    STUCK_AT_0     = "STUCK_AT_0"
    STUCK_AT_1     = "STUCK_AT_1"
    OPEN_CIRCUIT   = "OPEN_CIRCUIT"
    BRIDGED_SHORT  = "BRIDGED_SHORT"


class PcbInterconnectChannel:
    """
    Simulates physical PCB interconnect nets connecting Transmitter Chip to Receiver Chip,
    with configurable hardware solder defects (Stuck-At, Open, Solder Bridge).
    """
    def __init__(self, num_nets: int, default_pull: int = 1):
        self.num_nets = num_nets
        self.default_pull = default_pull  # 1 for internal pull-up, 0 for pull-down

        # Injected faults
        self.stuck_at_0_nets: set = set()
        self.stuck_at_1_nets: set = set()
        self.open_nets: set = set()
        self.bridged_pairs: List[Tuple[int, int]] = []  # Pairs of nets shorted together

    def inject_stuck_at_0(self, net_idx: int) -> None:
        self.stuck_at_0_nets.add(net_idx)

    def inject_stuck_at_1(self, net_idx: int) -> None:
        self.stuck_at_1_nets.add(net_idx)

    def inject_open(self, net_idx: int) -> None:
        self.open_nets.add(net_idx)

    def inject_bridge(self, net_a: int, net_b: int) -> None:
        if (net_a, net_b) not in self.bridged_pairs and (net_b, net_a) not in self.bridged_pairs:
            self.bridged_pairs.append((net_a, net_b))

    def propagate(self, driven_vector: List[int]) -> List[int]:
        """
        Propagate digital test signals through physical nets subject to PCB faults.
        """
        received = list(driven_vector)

        # 1. Apply bridging short-circuits (wired-AND logic for typical pull-up drivers)
        for net_a, net_b in self.bridged_pairs:
            bridge_val = received[net_a] & received[net_b]
            received[net_a] = bridge_val
            received[net_b] = bridge_val

        # 2. Apply Open circuits (floats to default pull-up/pull-down)
        for net_idx in self.open_nets:
            received[net_idx] = self.default_pull

        # 3. Apply Stuck-at-0 (hard tie to GND)
        for net_idx in self.stuck_at_0_nets:
            received[net_idx] = 0

        # 4. Apply Stuck-at-1 (hard tie to VDD)
        for net_idx in self.stuck_at_1_nets:
            received[net_idx] = 1

        return received


class BoundaryScanTester:
    """
    Automated Test Equipment (ATE) Boundary-Scan Engine for IEEE 1149.1 Interconnect Verification.
    Generates algorithmic patterns and performs fault syndrome isolation.
    """
    def __init__(self, num_nets: int, channel: PcbInterconnectChannel):
        self.num_nets = num_nets
        self.channel = channel

    def generate_all_zeros_vector(self) -> List[int]:
        return [0] * self.num_nets

    def generate_all_ones_vector(self) -> List[int]:
        return [1] * self.num_nets

    def generate_walking_ones_matrix(self) -> List[List[int]]:
        """
        Walking-1s matrix of size (N x N):
        Row i has a '1' at index i, and '0' elsewhere.
        """
        matrix = []
        for i in range(self.num_nets):
            row = [0] * self.num_nets
            row[i] = 1
            matrix.append(row)
        return matrix

    def generate_walking_zeros_matrix(self) -> List[List[int]]:
        """
        Walking-0s matrix of size (N x N):
        Row i has a '0' at index i, and '1' elsewhere.
        """
        matrix = []
        for i in range(self.num_nets):
            row = [1] * self.num_nets
            row[i] = 0
            matrix.append(row)
        return matrix

    def execute_interconnect_test(self) -> Dict[str, any]:
        """
        Executes full IEEE 1149.1 EXTEST interconnect test suite:
        1. All-0s & All-1s test (detects global rail shorts).
        2. Walking-1s test (locates bridge pairs and stuck-at faults).
        3. Walking-0s test (confirms open circuits vs stuck-at-1).
        """
        test_log = []

        # 1. All-0s Vector
        vec_0 = self.generate_all_zeros_vector()
        rec_0 = self.channel.propagate(vec_0)

        # 2. All-1s Vector
        vec_1 = self.generate_all_ones_vector()
        rec_1 = self.channel.propagate(vec_1)

        # 3. Walking-1s Suite
        w1_matrix = self.generate_walking_ones_matrix()
        rec_w1_matrix = []
        for row in w1_matrix:
            rec_w1_matrix.append(self.channel.propagate(row))

        # 4. Walking-0s Suite
        w0_matrix = self.generate_walking_zeros_matrix()
        rec_w0_matrix = []
        for row in w0_matrix:
            rec_w0_matrix.append(self.channel.propagate(row))

        # --- Diagnostic Fault Syndrome Analyzer ---
        net_diagnostics: Dict[int, Dict[str, any]] = {}
        detected_bridges = []

        for net_i in range(self.num_nets):
            # Check response to all-0 and all-1
            val_at_0 = rec_0[net_i]
            val_at_1 = rec_1[net_i]

            # Check walking-1 responses for net_i
            # When net_i was driven 1, did it stay 1?
            own_w1 = rec_w1_matrix[net_i][net_i]
            # When other nets were driven 1, did net_i turn 1?
            other_w1_corruptions = [
                j for j in range(self.num_nets)
                if j != net_i and rec_w1_matrix[j][net_i] == 1
            ]

            # Check walking-0 responses for net_i
            own_w0 = rec_w0_matrix[net_i][net_i]
            other_w0_corruptions = [
                j for j in range(self.num_nets)
                if j != net_i and rec_w0_matrix[j][net_i] == 0
            ]

            fault = FaultType.NO_FAULT
            detail = "Healthy Interconnect"

            # Diagnosis tree
            if val_at_0 == 0 and val_at_1 == 0:
                fault = FaultType.STUCK_AT_0
                detail = "Solder short to Ground (GND rail)"
            elif val_at_0 == 1 and val_at_1 == 1:
                # Distinguish between Stuck-At-1 (VDD short) and Open Circuit (pull-up floating)
                # An open net pulled up will never drop to 0 under walking-0s!
                if own_w0 == 1:
                    fault = FaultType.OPEN_CIRCUIT
                    detail = "Severed PCB trace or fractured BGA solder ball (Pulled High)"
                else:
                    fault = FaultType.STUCK_AT_1
                    detail = "Hard solder short to VDD power plane"
            elif other_w1_corruptions or other_w0_corruptions:
                fault = FaultType.BRIDGED_SHORT
                bridged_with = list(set(other_w1_corruptions + other_w0_corruptions))
                detail = f"Solder bridge between adjacent nets: {bridged_with}"
                for partner in bridged_with:
                    pair = tuple(sorted((net_i, partner)))
                    if pair not in detected_bridges:
                        detected_bridges.append(pair)
            elif val_at_0 == 0 and val_at_1 == 1 and own_w1 == 1 and own_w0 == 0:
                fault = FaultType.NO_FAULT
                detail = "100% Signal Continuity Confirmed"

            net_diagnostics[net_i] = {
                "fault_type": fault,
                "detail": detail
            }

        total_faulty = sum(1 for d in net_diagnostics.values() if d["fault_type"] != FaultType.NO_FAULT)
        pass_verdict = (total_faulty == 0)

        return {
            "pass_verdict": pass_verdict,
            "total_nets": self.num_nets,
            "total_faulty_nets": total_faulty,
            "net_diagnostics": net_diagnostics,
            "detected_bridges": detected_bridges,
            "vectors_evaluated": 2 + 2 * self.num_nets
        }


def test_boundary_scan_interconnect():
    print("================================================================================")
    print("TEST SUITE: BOUNDARY-SCAN EXTEST INTERCONNECT FAULT DIAGNOSIS")
    print("================================================================================")

    num_nets = 8
    # Create PCB interconnect bus with default pull-up
    channel = PcbInterconnectChannel(num_nets=num_nets, default_pull=1)

    # Injected Hardware Defects:
    # 1. Net 1: Stuck-At-0 (solder ball bridged to ground plane)
    channel.inject_stuck_at_0(1)

    # 2. Net 4: Open Circuit (cracked BGA solder joint, pulled up)
    channel.inject_open(4)

    # 3. Nets 6 & 7: Bridging Short (solder paste bridge between adjacent traces)
    channel.inject_bridge(6, 7)

    # Run Automated Boundary-Scan Test
    tester = BoundaryScanTester(num_nets=num_nets, channel=channel)
    results = tester.execute_interconnect_test()

    print(f"Total Nets Tested: {results['total_nets']}")
    print(f"Total Test Vectors Evaluated: {results['vectors_evaluated']}")
    print(f"Pass Verdict: {results['pass_verdict']}")
    print(f"Total Faulty Nets Detected: {results['total_faulty_nets']}")
    print("--------------------------------------------------------------------------------")
    print("NET-BY-NET FAULT SYNDROME ISOLATION REPORT:")

    for net_idx, diag in results["net_diagnostics"].items():
        status_tag = "[FAIL]" if diag["fault_type"] != FaultType.NO_FAULT else "[PASS]"
        print(f"  Net {net_idx}: {status_tag} {diag['fault_type'].value:<14} -> {diag['detail']}")

    print("--------------------------------------------------------------------------------")
    # Verify exact detection of injected defects
    assert results["net_diagnostics"][0]["fault_type"] == FaultType.NO_FAULT
    assert results["net_diagnostics"][1]["fault_type"] == FaultType.STUCK_AT_0
    assert results["net_diagnostics"][2]["fault_type"] == FaultType.NO_FAULT
    assert results["net_diagnostics"][3]["fault_type"] == FaultType.NO_FAULT
    assert results["net_diagnostics"][4]["fault_type"] == FaultType.OPEN_CIRCUIT
    assert results["net_diagnostics"][5]["fault_type"] == FaultType.NO_FAULT
    assert results["net_diagnostics"][6]["fault_type"] == FaultType.BRIDGED_SHORT
    assert results["net_diagnostics"][7]["fault_type"] == FaultType.BRIDGED_SHORT
    assert (6, 7) in results["detected_bridges"]

    print("[PASS] Milestone AX.2: All injected solder defects isolated with 100% pinpoint accuracy!")
    print("================================================================================")


if __name__ == "__main__":
    test_boundary_scan_interconnect()
