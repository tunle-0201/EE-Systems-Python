"""
dft_edge_apple_tesla_ate_silicon_test_capstone.py - Apple Silicon & Tesla FSD ATE Test Engine Capstone

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: Apple Silicon M-Series SoC / Tesla FSD HW4 Neural Processing Unit
Application: Automated Test Equipment (ATE) Production Flow, DFT Scan, MBIST, & Silicon Binning

MATHEMATICAL FOUNDATION & PRODUCTION TEST METHODOLOGY:
1. Production Test Flow (Advantest V93000 / Teradyne UltraFLEX):
   Stage 1: DC Parametric & Contact Test (Open/Short, IDDQ Quiescent Current Leakage).
   Stage 2: JTAG IEEE 1149.1 Infrastructure & 32-bit IDCODE Verification.
   Stage 3: Memory Built-In Self-Test (MBIST) on On-Chip SRAM (March C- 10N Complexity).
   Stage 4: Logic Scan ATPG (Automatic Test Pattern Generation) Stuck-At Fault Coverage:
            Fault_Coverage = (Detected_Faults / Total_Faults) * 100%
   Stage 5: Boundary-Scan EXTEST Interconnect Integrity (High-Density BGA SerDes/LPDDR5X).
   Stage 6: At-Speed PVT Shmoo & Silicon Speed Binning:
            - Bin 1: Ultra Performance (> 3.5 GHz, Vdd = 0.85V, Pass All Stages)
            - Bin 2: Standard Spec      (3.0 GHz - 3.5 GHz, Pass All Stages)
            - Bin 3: Low-Power Spec     (2.5 GHz - 3.0 GHz, Pass All Stages)
            - Bin Reject: Hardware defect detected at any stage.

2. Statistical Yield Calculation:
                Number_of_Passing_Dies
      Yield = ────────────────────────── * 100%
                  Total_Tested_Dies
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
import math
import sys
import os

sys.path.append(os.path.dirname(__file__))

from dft_edge_jtag_tap_controller_fsm import JtagTapController, TapState
from dft_edge_boundary_scan_interconnect_test import PcbInterconnectChannel, BoundaryScanTester, FaultType
from dft_edge_silicon_pvt_shmoo_characterization import SiliconPathModel, ShmooPlotEngine, ProcessCorner


class SiliconBin(Enum):
    BIN_1_ULTRA_PERF = "BIN_1_ULTRA_PERF"  # Fmax >= 3.5 GHz
    BIN_2_STANDARD   = "BIN_2_STANDARD"    # 2.5 GHz <= Fmax < 3.5 GHz
    BIN_3_EFFICIENCY = "BIN_3_EFFICIENCY"  # 1.5 GHz <= Fmax < 2.5 GHz
    BIN_REJECT       = "BIN_REJECT"        # Hardware fault or Fmax < 1.5 GHz


class DieDefectType(Enum):
    NONE               = "NONE"
    IDDQ_LEAKAGE_FAULT = "IDDQ_LEAKAGE_FAULT"
    JTAG_TAP_DEFECT    = "JTAG_TAP_DEFECT"
    SRAM_CELL_FAILURE  = "SRAM_CELL_FAILURE"
    SCAN_CHAIN_BROKEN  = "SCAN_CHAIN_BROKEN"
    BGA_SOLDER_BRIDGE  = "BGA_SOLDER_BRIDGE"
    PVT_SLOW_DEFECT    = "PVT_SLOW_DEFECT"


class SiliconDieUnderTesting:
    """
    Simulates a manufactured semiconductor die from a 3nm wafer lot.
    """
    def __init__(
        self,
        die_id: str,
        target_soc: str,
        corner: ProcessCorner,
        defect: DieDefectType = DieDefectType.NONE
    ):
        self.die_id = die_id
        self.target_soc = target_soc
        self.corner = corner
        self.defect = defect

        # DC Parametric specs
        self.iddq_leakage_ma = 12.5 if corner == ProcessCorner.TYPICAL_TYPICAL else (
            28.0 if corner == ProcessCorner.FAST_FAST else 6.2
        )
        if self.defect == DieDefectType.IDDQ_LEAKAGE_FAULT:
            self.iddq_leakage_ma = 145.0  # Massive gate oxide rupture / short


class AteProductionTestEngine:
    """
    High-Throughput Automated Test Equipment (ATE) Production Engine.
    Executes comprehensive 6-Stage DFT validation on advanced Silicon SoCs.
    """
    IDDQ_THRESHOLD_MA = 50.0  # Maximum permissible quiescent leakage

    def __init__(self, target_soc: str = "Apple_M3_Max_SoC"):
        self.target_soc = target_soc
        self.path_model = SiliconPathModel()
        self.shmoo_engine = ShmooPlotEngine(path_model=self.path_model)

    def stage_1_dc_parametric(self, die: SiliconDieUnderTesting) -> Tuple[bool, str]:
        """
        Stage 1: DC Parametric Continuity & IDDQ Quiescent Leakage Measurement.
        """
        if die.iddq_leakage_ma > self.IDDQ_THRESHOLD_MA:
            return False, f"IDDQ Exceeded Limit: {die.iddq_leakage_ma:.1f} mA > {self.IDDQ_THRESHOLD_MA} mA"
        return True, f"IDDQ Leakage Passed: {die.iddq_leakage_ma:.1f} mA"

    def stage_2_jtag_idcode(self, die: SiliconDieUnderTesting) -> Tuple[bool, str]:
        """
        Stage 2: IEEE 1149.1 JTAG TAP Controller & 32-bit IDCODE Verification.
        """
        if die.defect == DieDefectType.JTAG_TAP_DEFECT:
            return False, "JTAG TAP Controller FSM stuck in undefined state"

        # Initialize TAP controller
        tap = JtagTapController(
            chip_name=die.target_soc,
            part_number=0xA170,
            manufacturer_id=0x017,
            version=1
        )
        tap.reset_tap()
        read_idcode = tap.read_idcode()
        decoded = tap.decode_idcode(read_idcode)

        if decoded["part_number"] != 0xA170 or decoded["tie_bit"] != 1:
            return False, f"IDCODE mismatch: 0x{read_idcode:08X}"
        return True, f"JTAG IDCODE Validated: 0x{read_idcode:08X}"

    def stage_3_memory_bist(self, die: SiliconDieUnderTesting) -> Tuple[bool, str]:
        """
        Stage 3: On-Chip SRAM March C- 10N Built-In Self-Test (L2 Cache / NPU Buffers).
        """
        if die.defect == DieDefectType.SRAM_CELL_FAILURE:
            return False, "March C- Failure: Stuck-at cell defect at word offset 0x3E80"
        return True, "MBIST March C- Passed: 100% SRAM cells functional (64 MB Cache)"

    def stage_4_logic_scan_atpg(self, die: SiliconDieUnderTesting) -> Tuple[bool, str]:
        """
        Stage 4: Full-Scan ATPG Stuck-At Fault Coverage Verification.
        """
        if die.defect == DieDefectType.SCAN_CHAIN_BROKEN:
            return False, "Scan Chain Broken at Flip-Flop 142,890 (TDO tie low)"
        
        # Nominal test coverage on healthy silicon
        coverage = 99.82
        return True, f"Scan ATPG Coverage: {coverage:.2f}% (Passed 1,500,000 vectors)"

    def stage_5_boundary_scan_interconnect(self, die: SiliconDieUnderTesting) -> Tuple[bool, str]:
        """
        Stage 5: Boundary-Scan EXTEST Interconnect Solder Joint Testing.
        """
        channel = PcbInterconnectChannel(num_nets=8, default_pull=1)
        if die.defect == DieDefectType.BGA_SOLDER_BRIDGE:
            channel.inject_bridge(2, 3)

        tester = BoundaryScanTester(num_nets=8, channel=channel)
        results = tester.execute_interconnect_test()

        if not results["pass_verdict"]:
            return False, f"BGA Interconnect Failure: {results['total_faulty_nets']} faulty nets"
        return True, "Boundary-Scan EXTEST Passed: All 8 SerDes nets clean"

    def stage_6_at_speed_pvt_binning(self, die: SiliconDieUnderTesting) -> Tuple[SiliconBin, float, str]:
        """
        Stage 6: At-Speed Frequency Testing & Silicon Speed Binning.
        """
        if die.defect == DieDefectType.PVT_SLOW_DEFECT:
            return SiliconBin.BIN_REJECT, 1.5, "At-speed timing violation: Fmax < 2.0 GHz"

        # Evaluate at nominal operating voltage 0.85V at 25 deg C
        voltages = [0.85]
        frequencies = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
        shmoo_data = self.shmoo_engine.generate_shmoo_matrix(
            voltages=voltages,
            frequencies_ghz=frequencies,
            corner=die.corner,
            temp_celsius=25.0
        )

        f_max = shmoo_data["fmax_map"][0.85]

        if f_max >= 3.5:
            return SiliconBin.BIN_1_ULTRA_PERF, f_max, f"Bin 1 Ultra-Performance ({f_max:.1f} GHz)"
        elif f_max >= 2.5:
            return SiliconBin.BIN_2_STANDARD, f_max, f"Bin 2 Standard Spec ({f_max:.1f} GHz)"
        elif f_max >= 1.5:
            return SiliconBin.BIN_3_EFFICIENCY, f_max, f"Bin 3 Efficiency Spec ({f_max:.1f} GHz)"
        else:
            return SiliconBin.BIN_REJECT, f_max, f"Fmax below minimum spec: {f_max:.1f} GHz"

    def test_single_die(self, die: SiliconDieUnderTesting) -> Dict[str, any]:
        """
        Orchestrates full ATE test program on a single die.
        """
        stage_results = {}

        # Stage 1
        s1_pass, s1_msg = self.stage_1_dc_parametric(die)
        stage_results["Stage_1_DC_Parametric"] = (s1_pass, s1_msg)
        if not s1_pass:
            return {"die_id": die.die_id, "bin": SiliconBin.BIN_REJECT, "f_max": 0.0, "fail_stage": "Stage 1", "stages": stage_results}

        # Stage 2
        s2_pass, s2_msg = self.stage_2_jtag_idcode(die)
        stage_results["Stage_2_JTAG_IDCODE"] = (s2_pass, s2_msg)
        if not s2_pass:
            return {"die_id": die.die_id, "bin": SiliconBin.BIN_REJECT, "f_max": 0.0, "fail_stage": "Stage 2", "stages": stage_results}

        # Stage 3
        s3_pass, s3_msg = self.stage_3_memory_bist(die)
        stage_results["Stage_3_MBIST_March_C"] = (s3_pass, s3_msg)
        if not s3_pass:
            return {"die_id": die.die_id, "bin": SiliconBin.BIN_REJECT, "f_max": 0.0, "fail_stage": "Stage 3", "stages": stage_results}

        # Stage 4
        s4_pass, s4_msg = self.stage_4_logic_scan_atpg(die)
        stage_results["Stage_4_Logic_Scan_ATPG"] = (s4_pass, s4_msg)
        if not s4_pass:
            return {"die_id": die.die_id, "bin": SiliconBin.BIN_REJECT, "f_max": 0.0, "fail_stage": "Stage 4", "stages": stage_results}

        # Stage 5
        s5_pass, s5_msg = self.stage_5_boundary_scan_interconnect(die)
        stage_results["Stage_5_Boundary_Scan"] = (s5_pass, s5_msg)
        if not s5_pass:
            return {"die_id": die.die_id, "bin": SiliconBin.BIN_REJECT, "f_max": 0.0, "fail_stage": "Stage 5", "stages": stage_results}

        # Stage 6
        bin_verdict, f_max, s6_msg = self.stage_6_at_speed_pvt_binning(die)
        stage_results["Stage_6_PVT_Binning"] = (bin_verdict != SiliconBin.BIN_REJECT, s6_msg)

        fail_stage = "None" if bin_verdict != SiliconBin.BIN_REJECT else "Stage 6"
        return {
            "die_id": die.die_id,
            "bin": bin_verdict,
            "f_max": f_max,
            "fail_stage": fail_stage,
            "stages": stage_results
        }

    def run_wafer_lot_test(self, dies: List[SiliconDieUnderTesting]) -> Dict[str, any]:
        """
        Executes production testing across an entire wafer lot.
        Calculates yield, bin distribution, and failure Pareto.
        """
        lot_results = []
        bin_counts = {
            SiliconBin.BIN_1_ULTRA_PERF: 0,
            SiliconBin.BIN_2_STANDARD: 0,
            SiliconBin.BIN_3_EFFICIENCY: 0,
            SiliconBin.BIN_REJECT: 0
        }
        pareto_failures = {}

        for die in dies:
            res = self.test_single_die(die)
            lot_results.append(res)
            bin_verdict = res["bin"]
            bin_counts[bin_verdict] += 1

            if bin_verdict == SiliconBin.BIN_REJECT:
                stage = res["fail_stage"]
                pareto_failures[stage] = pareto_failures.get(stage, 0) + 1

        total_dies = len(dies)
        passing_dies = total_dies - bin_counts[SiliconBin.BIN_REJECT]
        lot_yield = (passing_dies / total_dies) * 100.0 if total_dies > 0 else 0.0

        return {
            "total_dies": total_dies,
            "passing_dies": passing_dies,
            "lot_yield_pct": lot_yield,
            "bin_counts": bin_counts,
            "pareto_failures": pareto_failures,
            "lot_results": lot_results
        }


def test_ate_silicon_capstone():
    print("================================================================================")
    print("TEST SUITE: APPLE SILICON & TESLA FSD ATE TEST ENGINE CAPSTONE")
    print("================================================================================")

    engine = AteProductionTestEngine(target_soc="Apple_M3_Max_SoC")

    # Construct representative wafer lot with process variations and physical defects
    wafer_lot = [
        # Healthy Fast-Fast dies -> Should achieve Bin 1 Ultra-Performance
        SiliconDieUnderTesting("DIE_001_FF", "Apple_M3_Max", ProcessCorner.FAST_FAST),
        SiliconDieUnderTesting("DIE_002_FF", "Apple_M3_Max", ProcessCorner.FAST_FAST),

        # Healthy Typical-Typical dies -> Should achieve Bin 2 Standard
        SiliconDieUnderTesting("DIE_003_TT", "Apple_M3_Max", ProcessCorner.TYPICAL_TYPICAL),
        SiliconDieUnderTesting("DIE_004_TT", "Apple_M3_Max", ProcessCorner.TYPICAL_TYPICAL),

        # Healthy Slow-Slow dies -> Should achieve Bin 3 Efficiency
        SiliconDieUnderTesting("DIE_005_SS", "Apple_M3_Max", ProcessCorner.SLOW_SLOW),

        # Defective Dies:
        SiliconDieUnderTesting("DIE_006_IDDQ", "Apple_M3_Max", ProcessCorner.TYPICAL_TYPICAL, DieDefectType.IDDQ_LEAKAGE_FAULT),
        SiliconDieUnderTesting("DIE_007_JTAG", "Apple_M3_Max", ProcessCorner.TYPICAL_TYPICAL, DieDefectType.JTAG_TAP_DEFECT),
        SiliconDieUnderTesting("DIE_008_SRAM", "Apple_M3_Max", ProcessCorner.TYPICAL_TYPICAL, DieDefectType.SRAM_CELL_FAILURE),
        SiliconDieUnderTesting("DIE_009_SCAN", "Apple_M3_Max", ProcessCorner.TYPICAL_TYPICAL, DieDefectType.SCAN_CHAIN_BROKEN),
        SiliconDieUnderTesting("DIE_010_BGA",  "Apple_M3_Max", ProcessCorner.TYPICAL_TYPICAL, DieDefectType.BGA_SOLDER_BRIDGE),
    ]

    summary = engine.run_wafer_lot_test(wafer_lot)

    print(f"Total Dies Tested: {summary['total_dies']}")
    print(f"Passing Dies: {summary['passing_dies']} / {summary['total_dies']}")
    print(f"Wafer Lot Yield: {summary['lot_yield_pct']:.1f} %")
    print("--------------------------------------------------------------------------------")
    print("SILICON BINNING DISTRIBUTION:")
    for b, count in summary["bin_counts"].items():
        print(f"  {b.value:<20}: {count:2d} dies")

    print("--------------------------------------------------------------------------------")
    print("DEFECT PARETO BREAKDOWN:")
    for stage, count in summary["pareto_failures"].items():
        print(f"  {stage:<12}: {count:2d} dies rejected")

    print("--------------------------------------------------------------------------------")
    # Verify exact binning results
    results = {r["die_id"]: r for r in summary["lot_results"]}

    assert results["DIE_001_FF"]["bin"] == SiliconBin.BIN_1_ULTRA_PERF
    assert results["DIE_002_FF"]["bin"] == SiliconBin.BIN_1_ULTRA_PERF
    assert results["DIE_003_TT"]["bin"] == SiliconBin.BIN_2_STANDARD
    assert results["DIE_004_TT"]["bin"] == SiliconBin.BIN_2_STANDARD
    assert results["DIE_005_SS"]["bin"] == SiliconBin.BIN_3_EFFICIENCY

    assert results["DIE_006_IDDQ"]["fail_stage"] == "Stage 1"
    assert results["DIE_007_JTAG"]["fail_stage"] == "Stage 2"
    assert results["DIE_008_SRAM"]["fail_stage"] == "Stage 3"
    assert results["DIE_009_SCAN"]["fail_stage"] == "Stage 4"
    assert results["DIE_010_BGA"]["fail_stage"] == "Stage 5"

    assert summary["passing_dies"] == 5
    assert summary["bin_counts"][SiliconBin.BIN_REJECT] == 5
    assert summary["lot_yield_pct"] == 50.0

    print("[PASS] Milestone AX.4 Capstone: ATE 6-Stage DFT Test Program & Binning verified with 100% test integrity!")
    print("================================================================================")


if __name__ == "__main__":
    test_ate_silicon_capstone()
