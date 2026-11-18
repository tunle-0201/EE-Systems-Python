"""
================================================================================
          MODULE AC: TIME-SENSITIVE NETWORKING & DETERMINISTIC ETHERNET
       MILESTONE AC.4: TSN DETERMINISTIC AUTOMOTIVE & SPACE SWITCH CAPSTONE
================================================================================

KIEN TRUC TOAN CHUOI DONG CO CHUYEN MACH TSN THOI GIAN THUC TIEN DINH (TSN SWITCH CAPSTONE):
Capstone nay tich hop tron ven ca 3 chuan TSN nen tang vao mot he thong chuyen mach:
1. Milestone AC.1: PTP Clock Sync (IEEE 802.1AS) -> Dong bo xung nhip gio Grandmaster.
2. Milestone AC.2: Credit-Based Shaper (IEEE 802.1Qav) -> Dieu tiet bang thong LiDAR/Camera.
3. Milestone AC.3: Time-Aware Shaper (IEEE 802.1Qbv) -> Bang GCL phan chia khe thoi gian.

SO DO DONG CHUYEN MACH DA LUONG DU LIEU TSN SWITCH (ASCII ARCHITECTURE):

   [ Luong 1: Lenh Lai Ten Lua / Phanh AEB ] ──> [ Queue 7: Scheduled Traffic (ST) ] ─+
   (Scheduled Time-Triggered Frames)                                                  |
                                                                                      |
   [ Luong 2: Stream Du Lieu 3D LiDAR/Camera ] ─> [ Queue 5: Audio/Video AVB (CBS) ]  ─+──> [ TAS Gates ] ──> [ Egress Port 1Gbps ]
   (Credit-Based Bandwidth Regulation)                                                |        ^
                                                                                      |        |
   [ Luong 3: Log Du Lieu Chan Doan Telemetry] ─> [ Queue 0: Best-Effort (BE) ]      ─+   [ GCL Schedule ]
   (Non-Critical Bulk Data)                                                                (PTP Synchronized)

SO SANH DOI SANH HIEN NHA VA TSN (ASCII PERFORMANCE COMPARISON):

   Switch thong thuong (Non-TSN):          Switch TSN Thoi gian thuc (TSN Switch):
   - Goi ST bi goi BE 1500B chan truoc     - Guard Band giu goi BE lai truoc Slot ST
   - Do tre hang doi: 12 - 120 us (Jitter) - Do tre hang doi: 0.00 us (Zero Jitter!)
   - Camera bung no gay nghet cong         - CBS dieu tiet Camera khong vuot 250 Mbps
"""

from typing import Tuple, List, Dict, Any, Optional
import math
import os
import sys

# Dam bao import duoc ca khi chay tu goc workspace hoac trong thu muc EE_Mentorship
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tsn_edge_ptp_clock_sync import GrandmasterClock, SlaveClock, simulate_ptp_sync_exchange
from tsn_edge_credit_based_shaper import CreditBasedShaper, Packet
from tsn_edge_time_aware_shaper import TimeAwareShaper, GCLEntry


class TSNDeterministicSwitchEngine:
    """
    Dong co chuyen mach mang thoi gian thuc tien dinh TSN Switch Engine.
    Tich hop dong bo PTP, dieu tiet CBS va phan chia khe thoi gian TAS.
    """

    def __init__(self, port_rate_mbps: float = 1000.0, cycle_time_us: float = 1000.0):
        self.port_rate_mbps = float(port_rate_mbps)
        self.cycle_time_us = float(cycle_time_us)

        # 1. Dong bo thoi gian PTP
        self.master_clock = GrandmasterClock(initial_time_us=0.0)
        self.switch_clock = SlaveClock(initial_time_us=5.0, drift_ppm=10.0)

        # 2. Bo dieu tiet CBS cho Queue 5 (AVB Traffic, du tru 250 Mbps)
        self.cbs = CreditBasedShaper(port_rate_mbps=port_rate_mbps, reserved_bw_mbps=250.0)

        # 3. Bo dinh thoi TAS voi lich trinh GCL (Queue 7: ST, Queue 5: AVB, Queue 0: BE)
        guard_band_us = (1518 * 8 / (port_rate_mbps * 1e6)) * 1e6  # 12.144 us
        st_slot_us = 150.0
        be_slot_us = cycle_time_us - st_slot_us - guard_band_us

        self.gcl = [
            GCLEntry(gate_states_mask=0b10000000, duration_us=st_slot_us),     # Slot 1: ST Open (Queue 7)
            GCLEntry(gate_states_mask=0b00100001, duration_us=be_slot_us),     # Slot 2: AVB & BE Open (Queue 5 & 0)
            GCLEntry(gate_states_mask=0b00000000, duration_us=guard_band_us)   # Slot 3: Guard Band (All Closed)
        ]
        self.tas = TimeAwareShaper(port_rate_mbps=port_rate_mbps, gcl=self.gcl)

    def synchronize_clock(self) -> float:
        """
        Thuc hien dong bo xung nhip PTP truoc khi van hanh chuyen mach:
        Tra ve do lech dong ho sau can chinh (micro-giay).
        """
        d_est, off_est = simulate_ptp_sync_exchange(self.master_clock, self.switch_clock, cable_delay_us=1.5)
        self.switch_clock.apply_offset_correction(off_est)
        return self.switch_clock.current_time_us - self.master_clock.current_time_us

    def simulate_mission_workload(self) -> Dict[str, Any]:
        """
        Mo phong tai lam viec thuc te:
        1. Luong Scheduled Traffic (Queue 7): 2 goi lenh lai khẩn cấp den dung dau moi chu ky (t = 0 us, t = 1000 us).
        2. Luong Best-Effort (Queue 0): 1 goi chan doan MTU 1500B den tai t = 830 us (gan Guard Band).
        3. Luong AVB (Queue 5): 1 goi camera 800B den tai t = 200 us.
        Tra ve bao cao thong ke do tre va tinh tien dinh (Telemetry Report).
        """
        # Nap cac goi tin vao switch
        self.tas.enqueue_packet(queue_idx=7, packet_id="Flight_Actuator_Cmd_1", size_bytes=128, arrival_time_us=0.0)
        self.tas.enqueue_packet(queue_idx=5, packet_id="LiDAR_PointCloud_Frame", size_bytes=800, arrival_time_us=200.0)
        self.tas.enqueue_packet(queue_idx=0, packet_id="Diagnostic_Log_Bulk", size_bytes=1500, arrival_time_us=980.0)
        self.tas.enqueue_packet(queue_idx=7, packet_id="Flight_Actuator_Cmd_2", size_bytes=128, arrival_time_us=1000.0)

        # Chay mo phong TAS chuyen mach
        sim_time = 0.0
        while len(self.tas.transmitted_log) < 4 and sim_time < 3000.0:
            sim_time, _ = self.tas.simulate_step(sim_time)

        # Thu thap so lieu
        st_packets = [p for p in self.tas.transmitted_log if p["queue_idx"] == 7]
        avb_packets = [p for p in self.tas.transmitted_log if p["queue_idx"] == 5]
        be_packets = [p for p in self.tas.transmitted_log if p["queue_idx"] == 0]

        st_delays = [p["queue_delay_us"] for p in st_packets]
        st_jitter = max(st_delays) - min(st_delays) if st_delays else 0.0

        return {
            "total_packets": len(self.tas.transmitted_log),
            "st_packet_count": len(st_packets),
            "st_max_delay_us": max(st_delays) if st_delays else 0.0,
            "st_jitter_us": st_jitter,
            "be_packet_count": len(be_packets),
            "be_tx_start_us": be_packets[0]["tx_start_us"] if be_packets else 0.0,
            "guard_band_held_packet": be_packets[0]["tx_start_us"] >= 1000.0 if be_packets else False,
            "transmitted_log": self.tas.transmitted_log
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AC CAPSTONE: TSN DETERMINISTIC SWITCH ENGINE")
    print("=========================================================\n")

    # 1. Khoi tao Dong co Chuyen mach TSN 1 Gbps
    tsn_switch = TSNDeterministicSwitchEngine(port_rate_mbps=1000.0, cycle_time_us=1000.0)

    # 2. Dong bo thoi gian PTP IEEE 802.1AS
    residual_clk_offset = tsn_switch.synchronize_clock()
    print("1. KET QUA DONG BO THOI GIAN PTP IEEE 802.1AS:")
    print(f"   -> Do lech dong ho Grandmaster vs Switch : {residual_clk_offset:.5f} us (Sub-microsecond)\n")
    assert abs(residual_clk_offset) < 0.05, "PTP phai khoa dong ho switch duoi 0.05 us!"

    # 3. Chay kich ban chuyen mach da luong thoi gian thuc
    print("2. CHAY KIEM DINH CHUYEN MACH DA LUONG TSN (ST, AVB, BE):")
    report = tsn_switch.simulate_mission_workload()

    print(f"   -> Tong so goi tin chuyen mach thanh cong : {report['total_packets']} / 4 goi")
    print(f"   -> So goi tin uu tien Scheduled Traffic   : {report['st_packet_count']} goi")
    print(f"   -> Do tre hang doi lon nhat cua goi ST    : {report['st_max_delay_us']:.3f} us (Ly tuong: 0.0 us)")
    print(f"   -> Do bien thien thoi gian (ST Jitter)    : {report['st_jitter_us']:.3f} us (Zero Jitter!)")

    assert report["st_max_delay_us"] < 1e-3, "Goi tin Scheduled Traffic khong duoc phep bi tre hang doi!"
    assert report["st_jitter_us"] < 1e-3, "Do bien thien thoi gian cua goi Scheduled Traffic phai bang 0!"

    print("\n3. CHI TIET DIEU PHOI TUNG GOI TIN QUA CONG EGRESS:")
    for p in report["transmitted_log"]:
        print(f"   -> [{p['packet_id']}] (Hang doi {p['queue_idx']}): Phat {p['tx_start_us']:.1f} us -> {p['tx_end_us']:.1f} us (Tre: {p['queue_delay_us']:.1f} us)")

    # Kiem tra Guard Band hoat dong chinh xac
    print(f"\n4. KIEM TRA TAC DUNG CUA DAI DEM GUARD BAND:")
    print(f"   -> Goi Diagnostic_Log_Bulk (MTU 1500B den tai 980 us) co bi Guard Band hoan lai?")
    print(f"   -> Thoi diem phat thuc te: {report['be_tx_start_us']:.1f} us (Slot 2 cua chu ky 2)")
    assert report["guard_band_held_packet"], "Goi Best-Effort phai bi Guard Band giu lai de tranh cham goi ST chu ky 2!"
    print("   -> Ket luan: GUARD BAND HOAT DONG HOAN HAO (Bao ve tuyet doi Slot ST chu ky 2)!")

    print("\n=========================================================")
    print("[THANH CONG] TOT NGHIEP XUAT SAC CAPSTONE MODULE AC: TSN DETERMINISTIC SWITCH ENGINE!")
    print("=========================================================")
