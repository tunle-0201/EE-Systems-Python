"""
================================================================================
          MODULE AC: TIME-SENSITIVE NETWORKING & DETERMINISTIC ETHERNET
          MILESTONE AC.1: IEEE 802.1AS PTP PRECISION CLOCK SYNCHRONIZATION
================================================================================

TAI SAO GIAO THUC DONG BO XUNG NHIP PTP LA BAT BUOC CHO TESLA FSD VA SPACEX?
- Trong he thong tu hanh (Tesla HW4 / Robotaxi) va tau vu tru (SpaceX Starship):
  Cac cam bien LiDAR, Radar 77GHz, Camera 4K va may tinh dieu khien bay IMU/FCS
  ket noi voi nhau qua mang Ethernet Gigabit (1000BASE-T1 / TTEthernet).
- Neu dung giao thuc NTP thong thuong (sai so 1 - 10 milliseconds):
  Xe chay 120 km/h di chuyen duoc 33.3 mm trong moi 1 millisecond.
  Sai so thoi gian giua Camera va Radar se khien he thong nhin thay mot vat can
  o hai vi tri khac nhau trong khong gian (Ghost Obstacles)!
- Chuan IEEE 802.1AS (PTP - Precision Time Protocol / gPTP):
  1. Lay dau thoi gian truc tiep bang phan cung (Hardware Timestamping) tai lop
     vat ly PHY/MAC, loai bo 100% do tre cua he dieu hanh OS.
  2. Dong bo dong ho giua Master (Grandmaster Clock) va cac nut Slave dat do chinh
     xac duoi 1 micro-giay (sub-microsecond precision)!

SO DO TRAO DOI BAN TIN PTP TAI TANG PHAN CUNG (ASCII DIAGRAM):

   Master (Grandmaster Clock)                        Slave (Local Clock)
         |                                                   |
     t_1 +─── [ Sync Message ] ─────────────────────────────>| t_2
         |                                                   |
         |─── [ Follow_Up (gui t_1) ] ──────────────────────>|
         |                                                   |
     t_4 |<── [ Delay_Req Message ] ─────────────────────────+ t_3
         |                                                   |
         |─── [ Delay_Resp (gui t_4) ] ─────────────────────>|
         v                                                   v

TOAN HOC DONG BO XUNG NHIP PTP (ASCII MATH BLOCKS):

1. Do tre truyen dan trung binh (Mean Propagation Delay):
   Thoi gian tin hieu di qua cap dong va bo chuyen mach:
                  (t_4 - t_1) - (t_3 - t_2)
   Mean_Delay = ─────────────────────────────
                              2

2. Do lech dong ho giua Master va Slave (Clock Offset):
                  (t_2 - t_1) - (t_4 - t_3)
   Clock_Offset = ─────────────────────────
                              2

3. Bo dieu khien servo PI dieu chinh do troi xung nhip (Clock Drift Compensation):
   Thach anh thuc te co sai so toc do dao dong (vi du +20 ppm do nhiet do).
   Dieu chinh xung nhip sau moi chu ky:
   drift_adjustment = K_p * Clock_Offset + K_i * sum(Clock_Offset)
"""

from typing import Tuple, List, Dict, Any, Optional
import math


class PIServoController:
    """
    Bo dieu khien ty le - tich phan (PI Controller) giu tan so xung nhip Slave
    khoa chat theo tan so Grandmaster Clock, triet tieu sai so trôi (ppm drift).
    """

    def __init__(self, kp: float = 0.6, ki: float = 0.05):
        self.kp = float(kp)
        self.ki = float(ki)
        self.integral = 0.0

    def compute(self, offset_error: float) -> float:
        """
        Tinh toan luong dieu chinh toc do dong ho dua tren Clock Offset.
        """
        self.integral += offset_error
        # Gioi han tich phan de phong chong Windup
        self.integral = max(-100.0, min(100.0, self.integral))
        return self.kp * offset_error + self.ki * self.integral

    def reset(self) -> None:
        self.integral = 0.0


class GrandmasterClock:
    """
    Dong ho goc Master phat chuan thoi gian tuyet doi (GPS hoac Nguyen tu).
    Don vi thoi gian: Microseconds (us).
    """

    def __init__(self, initial_time_us: float = 1000000.0):
        self.current_time_us = float(initial_time_us)

    def advance(self, dt_us: float) -> float:
        self.current_time_us += dt_us
        return self.current_time_us


class SlaveClock:
    """
    Dong ho cuc bo tai nut Slave (Cam bien LiDAR hoac May tinh bay).
    - current_time_us: Thoi gian hien tai cua dong ho Slave.
    - drift_ppm: Do troi thach anh (Parts Per Million). Vi du: +20 ppm = chay nhanh hon 20 us moi giay.
    """

    def __init__(self, initial_time_us: float = 1000015.0, drift_ppm: float = 20.0):
        self.current_time_us = float(initial_time_us)
        self.drift_ppm = float(drift_ppm)
        self.servo = PIServoController(kp=0.6, ki=0.08)
        self.frequency_adjustment_ppm = 0.0

    def advance(self, dt_us: float) -> float:
        """
        Tien thoi gian voi toc do chiu anh huong cua drift thach anh va bo dieu chinh.
        """
        effective_drift = self.drift_ppm - self.frequency_adjustment_ppm
        actual_elapsed = dt_us * (1.0 + effective_drift * 1e-6)
        self.current_time_us += actual_elapsed
        return self.current_time_us

    def apply_offset_correction(self, offset_us: float) -> None:
        """
        Dieu chinh buoc nhay thoi gian truc tiep (Step Correction).
        """
        self.current_time_us -= offset_us

    def update_frequency_servo(self, offset_us: float, interval_us: float = 125000.0) -> None:
        """
        Dieu chinh tan so dao dong thach anh bang bo loc servo PTP (IEEE 802.1AS Slew Adjustment):
        Do toc do troi thuc te: measured_drift_ppm = (offset_us / interval_seconds)
        Cap nhat bo dieu chinh voi he so loc hoi tu on dinh.
        """
        interval_seconds = interval_us * 1e-6
        if interval_seconds > 0.0:
            measured_drift_ppm = offset_us / interval_seconds
            # Bo loc servo can bang toc do troi thach anh
            alpha = 0.75
            self.frequency_adjustment_ppm += alpha * measured_drift_ppm


def simulate_ptp_sync_exchange(
    master: GrandmasterClock,
    slave: SlaveClock,
    cable_delay_us: float = 2.5
) -> Tuple[float, float]:
    """
    Mo phong mot chu ky trao doi 4 dau thoi gian (4 Hardware Timestamps) chuan PTP:
    - Master phat Sync tai t1 -> Slave nhan duoc tai t2 = t1 + delay + offset
    - Slave phat Delay_Req tai t3 -> Master nhan duoc tai t4 = t3 + delay - offset
    Tra ve: (calculated_delay_us, calculated_offset_us)
    """
    # 1. Master phat Sync message tai t1
    t1 = master.current_time_us

    # Tin hieu di qua cap mang mat cable_delay_us
    master.advance(cable_delay_us)
    slave.advance(cable_delay_us)
    t2 = slave.current_time_us

    # 2. Slave nghi 10 us roi phat Delay_Req tai t3
    slave_wait = 10.0
    master.advance(slave_wait)
    slave.advance(slave_wait)
    t3 = slave.current_time_us

    # Tin hieu Delay_Req di nguoc lai ve Master
    master.advance(cable_delay_us)
    slave.advance(cable_delay_us)
    t4 = master.current_time_us

    # 3. Tinh toan cong thuc PTP IEEE 802.1AS
    calculated_delay = ((t4 - t1) - (t3 - t2)) / 2.0
    calculated_offset = ((t2 - t1) - (t4 - t3)) / 2.0

    return calculated_delay, calculated_offset


if __name__ == "__main__":
    print("=========================================================")
    print("   TSN ETHERNET: IEEE 802.1AS PTP CLOCK SYNCHRONIZATION")
    print("=========================================================\n")

    # 1. Khoi tao he thong: Master chuan, Slave bi lech +15.0 us va troi +25 ppm
    master_clock = GrandmasterClock(initial_time_us=1000000.0)
    slave_clock = SlaveClock(initial_time_us=1000015.0, drift_ppm=25.0)
    physical_cable_delay = 3.2  # Do tre cap quang/dong la 3.2 us

    initial_offset = slave_clock.current_time_us - master_clock.current_time_us
    print("1. TRANG THAI DONG HO TRUOC KHI DONG BO PTP:")
    print(f"   -> Thoi gian Grandmaster   : {master_clock.current_time_us:.3f} us")
    print(f"   -> Thoi gian Slave cuc bo  : {slave_clock.current_time_us:.3f} us")
    print(f"   -> Do lech ban dau         : {initial_offset:.3f} us")
    print(f"   -> Do troi thach anh Slave : {slave_clock.drift_ppm:.1f} ppm\n")

    assert abs(initial_offset - 15.0) < 1e-3, "Do lech ban dau phai dung bang 15.0 us!"

    # 2. Chu ky PTP dau tien: Phat hien tre truyen dan va offset
    delay_calc, offset_calc = simulate_ptp_sync_exchange(master_clock, slave_clock, physical_cable_delay)
    print("2. CHU KY DONG BO PTP #1 (TINH TOAN 4 DAU THOI GIAN t1, t2, t3, t4):")
    print(f"   -> Tre truyen dan tinh duoc: {delay_calc:.3f} us (Thuc te: {physical_cable_delay:.3f} us)")
    print(f"   -> Do lech Offset tinh duoc: {offset_calc:.3f} us")

    assert abs(delay_calc - physical_cable_delay) < 1e-2, "PTP phai do chinh xac do tre cap!"
    assert abs(offset_calc - 15.0) < 0.1, "Offset tinh duoc phai xap xi 15 us!"

    # Ap dung buoc nhay can chinh (Step Correction)
    slave_clock.apply_offset_correction(offset_calc)
    residual_offset = slave_clock.current_time_us - master_clock.current_time_us
    print(f"   -> Do lech sau can chinh   : {residual_offset:.4f} us (Da khoa vao Master)\n")
    assert abs(residual_offset) < 0.05

    # 3. Chay 10 chu ky PTP tiep theo de Servo PI khoa tan so chong troi PPM
    print("3. KHOA TAN SO SERVO PI CHONG TROI THACH ANH (10 CHU KY LIEN TIEP):")
    for cycle in range(2, 11):
        # Giua cac chu ky PTP cach nhau 125 milliseconds (8 Hz theo chuan IEEE 802.1AS)
        interval_us = 125000.0
        master_clock.advance(interval_us)
        slave_clock.advance(interval_us)

        # Trao doi PTP
        d_est, off_est = simulate_ptp_sync_exchange(master_clock, slave_clock, physical_cable_delay)
        slave_clock.update_frequency_servo(off_est)
        slave_clock.apply_offset_correction(off_est)

    final_offset = slave_clock.current_time_us - master_clock.current_time_us
    print(f"   -> Do lech con lai sau 10 chu ky: {final_offset:.5f} us")
    print(f"   -> Do troi bu duoc boi Servo   : {slave_clock.frequency_adjustment_ppm:.2f} ppm (Muc tieu: ~25 ppm)")

    assert abs(final_offset) < 0.05, "Do lech dong ho cuoi cung phai duoi 0.05 us (Sub-microsecond)!"
    assert abs(slave_clock.frequency_adjustment_ppm - 25.0) < 5.0, "Servo phai hoc duoc do troi 25 ppm!"

    print("\n[THANH CONG] DA HOAN THANH DONG BO DONG HO PTP IEEE 802.1AS CHUAN SUB-MICROSECOND CHO XE VA TAU VU TRU!")
