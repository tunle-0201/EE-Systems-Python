"""
EE Mentorship - Module BE (Nhom 44) - Bai 173 (Milestone BE.2)
Chuyen de: Co che Dong ho Phan tan Distributed Clocks (DC) va Bu tre Lan truyen
           cho Mang Robot Hinh nguoi 32-Khop noi (Boston Dynamics / Tesla Optimus).

Muc tieu ky thuat:
1. Giai ma toan hoc va co che Dong ho Phan tan EtherCAT Distributed Clocks (DC) IEC 61158.
2. Thuat toan do Do tre Lan truyen vat ly (Propagation Delay Measurement: Cable + PHY).
3. Thiet ke Bo dieu khien servo PI dong pha (Phase Drift Compensation) bu trôi thach anh (+/- 30 ppm).
4. Khoi phat xung ngat dong bo SYNC0 / SYNC1 tai chu ky 1.0 ms dieu khien FOC dong co.
5. Kiem dinh thuc chien tren cum 32 khop robot: Triet tieu do lech pha tu > 25,000 ns ve < 50 ns (chuan < 100 ns).
"""

import time
import math
import random
from typing import List, Tuple, Dict, Optional


class EtherCATDCSlave:
    """
    Mo phong phan cung Dong ho Phan tan (DC Core) tren EtherCAT Slave Controller (ESC):
    Moi no-le co:
      - Bo dao dong thach anh cuc bo (Quartz Crystal Oscillator) co sai so tan so ppm.
      - Thanh ghi 64-bit System Time (0x0910): Thoi gian he thong da bu delay.
      - Thanh ghi 32-bit Propagation Delay (0x0918): Do tre lan truyen tu Reference Clock.
      - Bo dieu khien servo PI dieu chinh toc do dem (Speed Counter 0x0938).
    """
    def __init__(
        self,
        slave_id: int,
        cable_delay_ns: float,
        phy_delay_ns: float = 20.0,
        oscillator_ppm: float = 0.0
    ):
        self.slave_id = slave_id
        self.cable_delay_ns = cable_delay_ns
        self.phy_delay_ns = phy_delay_ns
        self.oscillator_ppm = oscillator_ppm

        # Thoi gian cuc bo (Local Time Counter)
        self.local_time_ns = 0.0
        # Thanh ghi do tre lan truyen tinh tu Reference Clock (Slave 0)
        self.propagation_delay_ns = 0.0
        # Thanh ghi System Time Offset (0x0910)
        self.system_time_offset_ns = 0.0

        # Bo dieu khien Servo PI bu troi pha
        self.kp = 0.30
        self.ki = 0.03
        self.integral_error = 0.0
        self.speed_adj_ns = 0.0
        self.sync_locked = False

        # Tin hieu ngat phan cung SYNC0
        self.sync0_triggered = False

    def get_system_time(self) -> float:
        """Thoi gian he thong chuan hoa doc duoc tu thanh ghi ESC 0x0910."""
        return self.local_time_ns + self.system_time_offset_ns - self.propagation_delay_ns

    def step_clock(self, nominal_dt_ns: float):
        """
        Tien hanh 1 buoc nhay thoi gian xung nhip (vi du: 1.0 ms = 1,000,000 ns):
        Dong ho vat ly chay theo toc do thach anh (ppm) cong tru luong tinh chinh toc do speed_adj.
        """
        freq_factor = 1.0 + (self.oscillator_ppm * 1e-6)
        actual_step = nominal_dt_ns * freq_factor - self.speed_adj_ns
        self.local_time_ns += actual_step

    def synchronize_dc_phase(self, ref_system_time: float):
        """
        Thuc thi bo dieu khien servo PI dong pha (Phase Drift Compensation):
        So sanh System Time sau buoc nhay voi Reference Clock va cap nhat thanh ghi Speed Counter 0x0938.
        """
        phase_error = self.get_system_time() - ref_system_time
        self.integral_error += phase_error
        self.integral_error = max(-5000.0, min(5000.0, self.integral_error))

        # Tinh toan luong tinh chinh toc do cho chu ky tiep theo
        self.speed_adj_ns = self.kp * phase_error + self.ki * self.integral_error
        self.sync_locked = abs(phase_error) < 50.0


class EtherCATDCMasterSyncCoordinator:
    """
    Bo dieu phoi Dong ho Phan tan tren EtherCAT Master:
    - Phat hien cau truc mang chuoi (Daisy-Chain Topology).
    - Tinh toan do tre lan truyen tren tung doan cap (Propagation Delay Calculation).
    - Can chinh thoi gian he thong System Time theo Slave 0 (Reference Clock).
    """
    def __init__(self, slaves: List[EtherCATDCSlave]):
        self.slaves = slaves
        self.ref_clock_slave = slaves[0] if slaves else None
        self.system_time_ns = 0.0

    def calculate_propagation_delays(self):
        """
        Thuat toan do tre lan truyen cap (IEC 61158-6-12 Section 5.4):
        Master phat khung tin doc timestamp tren cac cong Port cua ESC:
        Do tre cua Slave i = Do tre cua Slave i-1 + Cable Delay + PHY Forwarding Delay.
        """
        accumulated_delay = 0.0
        for i, slave in enumerate(self.slaves):
            if i == 0:
                # Slave 0 la Reference Clock (do tre moc = 0.0 ns)
                slave.propagation_delay_ns = 0.0
            else:
                # Do tre cong don qua chieu dai cap va mach PHY cua node truoc
                delay_segment = slave.cable_delay_ns + slave.phy_delay_ns
                accumulated_delay += delay_segment
                slave.propagation_delay_ns = accumulated_delay

    def synchronize_network(self, simulation_steps: int = 1000, cycle_dt_ns: float = 1_000_000.0) -> Dict[str, float]:
        """
        Chay mo phong chuoi dong bo DC tren toan mang:
        - Chu ky 1.0 ms (1 kHz control loop cho Robot hình nguoi).
        - Ghi nhan do lech pha (Phase Jitter) cua toan bo cac khop noi.
        """
        # Buoc 1: Do tre lan truyen va khoi tao offset
        self.calculate_propagation_delays()

        for slave in self.slaves:
            slave.local_time_ns = 0.0
            slave.system_time_offset_ns = slave.propagation_delay_ns
            slave.integral_error = 0.0
            slave.speed_adj_ns = 0.0

        settled_jitters = []

        for step in range(simulation_steps):
            # 1. Reference Clock (Slave 0) tien ve truoc 1 chu ky
            self.ref_clock_slave.step_clock(cycle_dt_ns)
            current_ref_time = self.ref_clock_slave.get_system_time()
            self.system_time_ns = current_ref_time

            # 2. Cac Slave con lai tien nhip va kich hoat PI servo dong pha
            step_jitters = []
            for slave in self.slaves[1:]:
                # Tien nhip vat ly
                slave.step_clock(cycle_dt_ns)
                # Cong them nhieu do luong PHY +/- 2 ns vao phan hoi Master
                meas_noise = random.gauss(0.0, 2.0)
                slave.synchronize_dc_phase(current_ref_time + meas_noise)

                jitter = abs(slave.get_system_time() - current_ref_time)
                step_jitters.append(jitter)

            max_j = max(step_jitters) if step_jitters else 0.0

            # Ghi nhan sau khi he thong da on dinh (sau 200 chu ky khoi dong)
            if step >= 200:
                settled_jitters.append(max_j)

        peak_locked_jitter = max(settled_jitters) if settled_jitters else 0.0
        avg_locked_jitter = sum(settled_jitters) / len(settled_jitters) if settled_jitters else 0.0

        return {
            "peak_locked_jitter_ns": peak_locked_jitter,
            "avg_locked_jitter_ns": avg_locked_jitter,
            "total_propagation_delay_ns": self.slaves[-1].propagation_delay_ns
        }


def test_distributed_clocks_sync():
    """
    Kiem thu toan dien co che Dong ho Phan tan EtherCAT Distributed Clocks tren Robot 32-Khop.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BE (NHOM 44) - BAI 173 (MILESTONE BE.2)")
    print("DONG HO PHAN TAN DISTRIBUTED CLOCKS (DC) CHO ROBOT HINH NGUOI 32-KHOP")
    print("================================================================================")

    # Khoi tao 32 khop chap hanh robot (Tay, Chan, Cot song, Co)
    # Moi khop noi bang doan cap Ethernet tu 0.3m den 1.5m (khoang 1.5 ns den 7.5 ns delay)
    # Thach anh moi khop co sai lech chech lech tu -25 ppm den +25 ppm
    random.seed(42)
    NUM_JOINTS = 32
    robot_slaves = []

    for i in range(NUM_JOINTS):
        cable_len_m = 0.3 + (i % 5) * 0.25  # Chieu dai cap tu 0.3m den 1.3m
        cable_delay = cable_len_m * 5.0      # Cap CAT5e co van toc truyen ~ 5 ns/meter
        # Tao sai so tan so thach anh ngau nhien
        ppm = random.uniform(-25.0, 25.0) if i > 0 else 0.0  # Slave 0 la Reference Clock
        slave = EtherCATDCSlave(slave_id=i, cable_delay_ns=cable_delay, phy_delay_ns=18.0, oscillator_ppm=ppm)
        robot_slaves.append(slave)

    coordinator = EtherCATDCMasterSyncCoordinator(robot_slaves)

    # 1. Kiem tra thuat toan do tre lan truyen (Propagation Delay Measurement)
    print(f"[1] Thuat toan do Do tre Lan truyen vat ly (Line Topology {NUM_JOINTS} Slaves):")
    coordinator.calculate_propagation_delays()

    for idx in [0, 1, 8, 16, 31]:
        s = robot_slaves[idx]
        print(f"    * Khop #{idx:02d} | Cap: {s.cable_delay_ns:>4.1f} ns | PHY: {s.phy_delay_ns:>4.1f} ns | Do tre tich luy: {s.propagation_delay_ns:>6.1f} ns")

    total_delay = robot_slaves[-1].propagation_delay_ns
    print(f"    * Tong do tre lan truyen toan robot (Tu Khop 0 den Khop 31): {total_delay:.1f} ns")

    # 2. Mo phong truong hop KHONG CO DC (Unsynchronized Clock Drift)
    print("\n[2] Danh gia khi KHONG CO Dong ho Phan tan (Free-running Oscillators):")
    uncontrolled_drift_slave = EtherCATDCSlave(1, cable_delay_ns=5.0, oscillator_ppm=25.0)
    ref_dummy = EtherCATDCSlave(0, cable_delay_ns=0.0, oscillator_ppm=0.0)

    for _ in range(1000):  # Chay 1 giay (1000 chu ky 1ms)
        ref_dummy.step_clock(1_000_000.0)
        uncontrolled_drift_slave.step_clock(1_000_000.0)

    uncontrolled_drift_ns = abs(uncontrolled_drift_slave.local_time_ns - ref_dummy.local_time_ns)
    print(f"    * Do lech pha sau chi 1.0 giay hoat dong: {uncontrolled_drift_ns:.0f} ns ({uncontrolled_drift_ns/1000.0:.2f} us)")
    print("    * HAU QUA: Mat dong bo tram trong gay giat rung khop noi va pha huy co hoc robot!")

    # 3. Kiem thu kich hoat Dong ho Phan tan Distributed Clocks (Closed-Loop PI Servo)
    print(f"\n[3] Kich hoat Dong ho Phan tan EtherCAT DC (Vong lap dong bo chu ky 1.0 kHz):")
    sync_results = coordinator.synchronize_network(simulation_steps=1000, cycle_dt_ns=1_000_000.0)

    print(f"    * Do troi pha cuc dai sau on dinh (Peak Jitter): {sync_results['peak_locked_jitter_ns']:.2f} ns")
    print(f"    * Do troi pha trung binh (Average Jitter)     : {sync_results['avg_locked_jitter_ns']:.2f} ns")

    # Tieu chuan cong nghiep EtherCAT IEC 61158 yeu cau do troi < 100 ns
    assert sync_results["peak_locked_jitter_ns"] < 100.0, "Loi: Do troi vuot qua nguong an toan 100 ns!"
    print("    * KET QUA KIEM DINH: PASS TUYET DOI (< 100 ns tieu chuan quoc te)")
    print("    * Toan bo 32 khop robot lay mau encoder va dong bo xung PWM tai cung mot nano-giay!")
    print("================================================================================")


if __name__ == "__main__":
    test_distributed_clocks_sync()
