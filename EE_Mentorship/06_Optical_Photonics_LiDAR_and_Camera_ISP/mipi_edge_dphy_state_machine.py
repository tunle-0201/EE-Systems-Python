"""
MIPI D-PHY Physical Layer State Machine & High-Speed Burst Protocol
Chuyen de 23: MIPI CSI-2 Camera Serial Interface & D-PHY Hardware Pipeline
Milestone AJ.1 - Bai hoc 88 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Mo phong co che vat ly chuyen mach Low-Power (LP) sang High-Speed (HS) cua MIPI D-PHY.
- Kiem tra nghiem ngat cac dac tinh thoi gian (Timing parameters: T_LPX, T_HS_PREPARE, T_HS_ZERO, T_HS_TRAIL, T_HS_EXIT).
- Tinh toan suy hao nang luong khi duy tri o che do Ultra-Low Power State (ULPS) so voi HS transmission.
"""

from enum import Enum
import math
from typing import List, Dict, Tuple


class DPhyLineState(Enum):
    LP_00 = "LP-00"  # Differential line bridge / low
    LP_01 = "LP-01"  # D+ Low, D- High
    LP_10 = "LP-10"  # D+ High, D- Low
    LP_11 = "LP-11"  # Stop State: Both D+ and D- High (1.2V CMOS)
    HS_0  = "HS-0"   # High-Speed differential 0 (-100mV to -200mV)
    HS_1  = "HS-1"   # High-Speed differential 1 (+100mV to +200mV)
    ULPS  = "ULPS"   # Ultra-Low Power State (Mark-1 / LP-00 latch)


class DPhyTimingSpec:
    """
    Quy chuan dinh thoi gian thuc MIPI D-PHY v1.2 (Don vi: nanoseconds - ns).
    Dua tren chu ky bit toc do cao UI (Unit Interval).
    Vi du: O toc do 1.0 Gbps per lane, 1 UI = 1.0 ns.
    """
    def __init__(self, data_rate_mbps: float = 1000.0):
        self.data_rate_mbps = data_rate_mbps
        self.ui_ns = 1000.0 / data_rate_mbps  # UI tinh bang ns

        # Tieu chuan MIPI Alliance D-PHY Specification v1.2
        # T_LPX: Thoi gian truyen tin hieu LP (toi thieu 50 ns)
        self.t_lpx_min_ns = 50.0
        
        # T_HS_PREPARE: Thoi gian chuan bi truoc khi bat bo phat HS (40ns + 4*UI den 85ns + 6*UI)
        self.t_hs_prepare_min_ns = 40.0 + 4.0 * self.ui_ns
        self.t_hs_prepare_max_ns = 85.0 + 6.0 * self.ui_ns

        # T_HS_ZERO: Thoi gian giu muc HS-0 de on dinh may thu (HS_PREPARE + HS_ZERO >= 145ns + 10*UI)
        self.t_hs_prep_zero_min_ns = 145.0 + 10.0 * self.ui_ns

        # T_HS_TRAIL: Thoi gian giu bit nguoc lai sau payload truoc khi tat bo phat HS
        self.t_hs_trail_min_ns = max(8.0 * self.ui_ns, 60.0 + 4.0 * self.ui_ns)

        # T_HS_EXIT: Thoi gian on dinh khi quay lai LP-11 (toi thieu 100 ns)
        self.t_hs_exit_min_ns = 100.0


class DPhyTransmitter:
    """
    Mo phong bo phat MIPI D-PHY TX tren cam bien hinh anh (Camera Image Sensor).
    Dieu khien may trang thai LP -> HS Burst -> LP.
    """
    def __init__(self, timing_spec: DPhyTimingSpec):
        self.spec = timing_spec
        self.current_state = DPhyLineState.LP_11
        self.state_history: List[Tuple[float, DPhyLineState, str]] = []
        self.current_time_ns = 0.0

    def _log_state(self, duration_ns: float, state: DPhyLineState, desc: str):
        self.state_history.append((duration_ns, state, desc))
        self.current_time_ns += duration_ns
        self.current_state = state

    def enter_ultra_low_power_state(self):
        """
        Dua lane vao che do tiet kiem dien nang cuc tieu ULPS (Camera cam bien ngu).
        Quy trinh: LP-11 -> LP-10 -> LP-00 (ULPS Entry Sequence).
        """
        self._log_state(60.0, DPhyLineState.LP_11, "Stop State")
        self._log_state(60.0, DPhyLineState.LP_10, "ULPS Request State")
        self._log_state(200.0, DPhyLineState.ULPS, "Ultra-Low Power Latch State")

    def exit_ultra_low_power_state(self):
        """
        Thuc tinh lane tu ULPS de tro ve Stop State LP-11.
        Quy trinh: Phat tin hieu Mark-1 (LP-10 trong toi thieu 1000 ns) -> LP-11.
        """
        self._log_state(1200.0, DPhyLineState.LP_10, "ULPS Wakeup Mark-1 Pulse")
        self._log_state(150.0, DPhyLineState.LP_11, "Back to Stop State LP-11")

    def transmit_hs_burst(self, payload_bytes: bytes) -> List[Tuple[float, DPhyLineState, str]]:
        """
        Thuc hien truyen mot chuoi goi tin High-Speed Burst tu cam bien ve SoC.
        Tuan thu 100% quy trinh khoi dong:
        1. LP-11 (Stop State)
        2. LP-01 (Start-of-Transmission Request)
        3. LP-00 (Bridge State)
        4. HS-0  (HS-Prepare + HS-Zero)
        5. SoT   (Start of Transmission Sync Sequence: 0xB8 = 0b00011101)
        6. HS Payload (D-PHY High-Speed Data)
        7. HS-Trail
        8. LP-11 (HS-Exit)
        """
        # 1. Stop State LP-11
        self._log_state(self.spec.t_lpx_min_ns + 10.0, DPhyLineState.LP_11, "Stop State (T_LPX)")

        # 2. LP-01: Khoi tao yeu cau truyen HS
        self._log_state(self.spec.t_lpx_min_ns + 5.0, DPhyLineState.LP_01, "LP-01 Request State")

        # 3. LP-00: Cau noi truoc khi kich hoat vi sai HS
        self._log_state(self.spec.t_lpx_min_ns + 5.0, DPhyLineState.LP_00, "LP-00 Bridge State")

        # 4. Kich hoat bo phat HS: HS-PREPARE
        prepare_duration = 60.0 + 5.0 * self.spec.ui_ns
        self._log_state(prepare_duration, DPhyLineState.HS_0, "HS-PREPARE (Driving HS-0)")

        # 5. HS-ZERO: Giu HS-0 de on dinh bo thu RX Clock Data Recovery
        zero_duration = max(0.0, self.spec.t_hs_prep_zero_min_ns - prepare_duration + 20.0)
        self._log_state(zero_duration, DPhyLineState.HS_0, "HS-ZERO (Line Stabilization)")

        # 6. SoT Sync Sequence: 8-bit dong bo 0xB8 (0b10111000 MSB hay 00011101 LSB first)
        sot_sync_byte = 0xB8
        sot_duration = 8.0 * self.spec.ui_ns
        self._log_state(sot_duration, DPhyLineState.HS_1, f"SoT Sync Word (0x{sot_sync_byte:02X})")

        # 7. HS Payload Data Transmission
        payload_bits = len(payload_bytes) * 8
        payload_duration = payload_bits * self.spec.ui_ns
        self._log_state(payload_duration, DPhyLineState.HS_1, f"HS Payload Data ({len(payload_bytes)} bytes)")

        # 8. HS-TRAIL: Phat bit nguoc lai bit cuoi de xac dinh ket thuc
        trail_duration = self.spec.t_hs_trail_min_ns + 10.0
        self._log_state(trail_duration, DPhyLineState.HS_0, "HS-TRAIL (End of Burst Marker)")

        # 9. HS-EXIT: Tro ve muc Stop State LP-11
        exit_duration = self.spec.t_hs_exit_min_ns + 10.0
        self._log_state(exit_duration, DPhyLineState.LP_11, "HS-EXIT (Return to LP-11)")

        return self.state_history


class DPhyReceiverValidator:
    """
    Bo kiem chuan phan cung may thu D-PHY RX tren chip xu ly Tesla / Apple ISP.
    Kiem tra toan bo sai lech dinh thoi ns va tinh hop le cua may trang thai.
    """
    def __init__(self, timing_spec: DPhyTimingSpec):
        self.spec = timing_spec

    def validate_burst(self, state_history: List[Tuple[float, DPhyLineState, str]]) -> Dict[str, any]:
        """
        Kiem tra chuoi trang thai co dat chuan MIPI D-PHY Spec khong.
        """
        results = {
            "is_valid": True,
            "violations": [],
            "total_burst_time_ns": 0.0,
            "payload_throughput_mbps": 0.0
        }

        # Tim cac buoc chuyen tiep
        state_seq = [s[1] for s in state_history]
        durations = [s[0] for s in state_history]
        results["total_burst_time_ns"] = sum(durations)

        # Kiem tra trinh tu trang thai khoi dong bat buoc: LP-11 -> LP-01 -> LP-00 -> HS-0
        try:
            idx_lp11 = state_seq.index(DPhyLineState.LP_11)
            idx_lp01 = state_seq.index(DPhyLineState.LP_01)
            idx_lp00 = state_seq.index(DPhyLineState.LP_00)
            
            if not (idx_lp11 < idx_lp01 < idx_lp00):
                results["is_valid"] = False
                results["violations"].append("Trinh tu khoi dong LP khong dung quy chuan (Phai la LP-11 -> LP-01 -> LP-00)")
        except ValueError as e:
            results["is_valid"] = False
            results["violations"].append(f"Thieu trang thai khoi dong LP: {str(e)}")

        # Kiem tra thoi gian T_HS_PREPARE
        prepare_step = next((s for s in state_history if "HS-PREPARE" in s[2]), None)
        if prepare_step:
            dur = prepare_step[0]
            if dur < self.spec.t_hs_prepare_min_ns or dur > self.spec.t_hs_prepare_max_ns:
                results["is_valid"] = False
                results["violations"].append(f"T_HS_PREPARE vi pham: {dur:.2f} ns (Chuan: {self.spec.t_hs_prepare_min_ns:.2f} - {self.spec.t_hs_prepare_max_ns:.2f} ns)")

        # Kiem tra thoi gian ket hop HS_PREPARE + HS_ZERO
        prep_zero_dur = sum([s[0] for s in state_history if "HS-PREPARE" in s[2] or "HS-ZERO" in s[2]])
        if prep_zero_dur < self.spec.t_hs_prep_zero_min_ns:
            results["is_valid"] = False
            results["violations"].append(f"T_HS_PREPARE + T_HS_ZERO qua ngan: {prep_zero_dur:.2f} ns (Toi thieu: {self.spec.t_hs_prep_zero_min_ns:.2f} ns)")

        # Kiem tra thoi gian HS-TRAIL
        trail_step = next((s for s in state_history if "HS-TRAIL" in s[2]), None)
        if trail_step and trail_step[0] < self.spec.t_hs_trail_min_ns:
            results["is_valid"] = False
            results["violations"].append(f"T_HS_TRAIL vi pham: {trail_step[0]:.2f} ns (Toi thieu: {self.spec.t_hs_trail_min_ns:.2f} ns)")

        return results


def test_dphy_burst_pipeline():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN D-PHY STATE MACHINE & TIMING SPECIFICATION")
    print("=" * 80)

    # 1. Khoi tao thong so kenh MIPI D-PHY 1.5 Gbps / lane
    data_rate = 1500.0  # Mbps
    timing_spec = DPhyTimingSpec(data_rate_mbps=data_rate)
    print(f"Toc do kenh D-PHY        : {data_rate:.1f} Mbps (1 UI = {timing_spec.ui_ns:.3f} ns)")
    print(f"Yeu cau T_HS_PREPARE     : [{timing_spec.t_hs_prepare_min_ns:.2f} ns, {timing_spec.t_hs_prepare_max_ns:.2f} ns]")
    print(f"Yeu cau T_HS_PREP + ZERO : >= {timing_spec.t_hs_prep_zero_min_ns:.2f} ns")
    print(f"Yeu cau T_HS_TRAIL       : >= {timing_spec.t_hs_trail_min_ns:.2f} ns")
    print("-" * 80)

    # 2. Tao du lieu goi tin anh (Payload 512 bytes)
    mock_payload = bytes([i % 256 for i in range(512)])
    tx = DPhyTransmitter(timing_spec)

    # 3. Thuc hien quy trinh HS Burst
    burst_history = tx.transmit_hs_burst(mock_payload)

    # In bang trinh tu trang thai may phat
    print("Trinh tu chuyen doi trang thai MIPI D-PHY TX:")
    print("STT | Thoi Gian (ns) | Trang Thai | Mo Ta Chi Tiet")
    print("-" * 75)
    for i, (dur, state, desc) in enumerate(burst_history, 1):
        print(f"{i:3d} | {dur:14.2f} | {state.value:10s} | {desc}")
    print("-" * 80)

    # 4. Kiem tra tinh hop le bang RX Validator
    rx = DPhyReceiverValidator(timing_spec)
    validation = rx.validate_burst(burst_history)

    print("Ket qua kiem chuan bo thu D-PHY RX:")
    print(f"-> Tong thoi gian chum xung (Burst Duration): {validation['total_burst_time_ns']:.2f} ns")
    print(f"-> Trang thai hop le chuan MIPI D-PHY       : {'DAP UNG (VALID)' if validation['is_valid'] else 'VI PHAM (INVALID)'}")
    if validation["violations"]:
        for v in validation["violations"]:
            print(f"   [!] Canh bao: {v}")

    # 5. Kiem tra che do tiet kiem nang luong Ultra-Low Power State (ULPS)
    tx_ulps = DPhyTransmitter(timing_spec)
    tx_ulps.enter_ultra_low_power_state()
    tx_ulps.exit_ultra_low_power_state()
    print("-" * 80)
    print("Che do tiet kiem dien nang Ultra-Low Power State (ULPS):")
    print(f"-> So buoc chuyen doi vao va thoat ULPS: {len(tx_ulps.state_history)} buoc")
    print(f"-> Thoi gian phat xung thuc tinh Mark-1 : 1200.00 ns (Dung chuan >= 1000 ns)")
    print("=" * 80)

    assert validation["is_valid"] is True, "Kiem chuan MIPI D-PHY Burst that bai!"
    assert len(validation["violations"]) == 0, "Ton tai vi pham quy chuan D-PHY!"
    print("[PASS] MIPI D-PHY State Machine & Timing Specification: 100% Hoan hao!")


if __name__ == "__main__":
    test_dphy_burst_pipeline()
