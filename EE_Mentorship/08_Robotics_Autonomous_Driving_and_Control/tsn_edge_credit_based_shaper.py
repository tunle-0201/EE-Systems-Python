"""
================================================================================
          MODULE AC: TIME-SENSITIVE NETWORKING & DETERMINISTIC ETHERNET
          MILESTONE AC.2: IEEE 802.1Qav CREDIT-BASED SHAPER (CBS) FOR AVB
================================================================================

TAI SAO BO DIEU TIET CBS LA BAT BUOC CHO STREAMING CAMERA VA LIDAR TRONG XE TU HANH?
- Trong he thong tu hanh Tesla FSD va robot di dong:
  Cac cam bien LiDAR va Camera 4K lien tuc ban cac luong du lieu lon (Audio/Video
  Bridging - AVB Traffic) qua switch Ethernet.
- Neu khong co bo dieu tiet: Khi mot khung hinh Camera 1.5 MB den, no se chiem dung
  100% bang thong cong ra (Egress Port) trong hang chuc milliseconds, gay nghet mang
  va bo doi (Starvation) cac goi tin dieu khien lai hoac chan doan khac.
- Chuan IEEE 802.1Qav Credit-Based Shaper (CBS):
  1. Gioi han chat che bang thong toi da ma luong du lieu co the su dung (Reserved Bandwidth).
  2. Lam min dong du lieu bung no (Traffic Smoothing), gian cach deu cac goi tin.
  3. Bao dam do tre toi da co chan (Bounded Worst-Case Latency) cho toan bo mang.

SO DO HOAT DONG CO CHE TIN DUNG (CREDIT MECHANISM) TRONG CBS (ASCII DIAGRAM):

   Credit (Bits)
     ^
  +C |     /| (Tich luy Credit khi co goi cho)
     |    / | Toc do: +idleSlope
   0 +───/──+──────────────────────────────────────+──────────────> Thoi gian t
     |  /   |                                      |
     | /    | (Tieu thu Credit khi dang truyen)    | (Tich luy lai ve 0)
     |/     | Toc do: sendSlope = idleSlope - Port |
  -C |      v                                      v
            [ Phat Goi 1 ]                         [ Phat Goi 2 ]

TOAN HOC VAN HANH BO DIEU TIET CBS (ASCII MATH BLOCKS):

1. Hai toc do doc (Slopes):
   idleSlope = Reserved_Bandwidth (Bang thong du tru, vi du: 250 Mbps)
   sendSlope = idleSlope - Port_Rate (Toc do tieu thu am, vi du: 250 - 1000 = -750 Mbps)

2. Thoi gian phat mot goi tin kich thuoc L bits tren cong toc do R:
          L
   dt = ─────
          R

3. Su thay doi Credit khi phat goi:
   delta_Credit = sendSlope * dt < 0  (Credit tut xuong am)

4. Thoi gian can thiet de Credit hoi phuc tu muc am ve 0 (De duoc phat tiep):
            |Credit_am|
   t_wait = ───────────
             idleSlope

5. Luat dieu tiet:
   - Goi tin CHI duoc phep phat khi: Credit >= 0.
   - Khi hang doi rong: Credit khong duoc tich luy duong qua muc (Reset ve 0).
"""

from typing import Tuple, List, Dict, Any, Optional
import math


class Packet:
    """
    Dai dien mot goi tin Ethernet tren mang TSN.
    - packet_id: Dinh danh goi
    - size_bytes: Kich thuoc goi tin (Bytes)
    - arrival_time_us: Thoi diem goi tin den hang doi (Microseconds)
    """

    def __init__(self, packet_id: int, size_bytes: int, arrival_time_us: float):
        self.packet_id = int(packet_id)
        self.size_bytes = int(size_bytes)
        self.size_bits = self.size_bytes * 8
        self.arrival_time_us = float(arrival_time_us)
        self.tx_start_time_us: Optional[float] = None
        self.tx_end_time_us: Optional[float] = None


class CreditBasedShaper:
    """
    Bo dieu tiet bang thong Credit-Based Shaper theo chuan IEEE 802.1Qav.
    - port_rate_mbps: Toc do cong vat ly (Mbps, vi du: 1000 Mbps = 1 Gbps)
    - reserved_bw_mbps: Bang thong du tru cho hang doi nay (idleSlope, vi du: 250 Mbps)
    """

    def __init__(self, port_rate_mbps: float = 1000.0, reserved_bw_mbps: float = 250.0):
        self.port_rate_bps = float(port_rate_mbps) * 1e6
        self.idle_slope = float(reserved_bw_mbps) * 1e6
        self.send_slope = self.idle_slope - self.port_rate_bps

        # Trang thai bo dieu tiet
        self.credit = 0.0  # Don vi: bits
        self.current_time_us = 0.0
        self.queue: List[Packet] = []
        self.transmitted_packets: List[Packet] = []

    def enqueue(self, packet: Packet) -> None:
        self.queue.append(packet)

    def advance_time(self, new_time_us: float) -> None:
        """
        Cap nhat credit dua tren khoang thoi gian troi qua tu current_time_us den new_time_us.
        Neu hang doi co goi cho ma khong truyen, credit tang voi toc do idle_slope.
        Neu hang doi rong, credit tang ve 0 roi dung lai (khong duoc > 0 khi rong).
        """
        if new_time_us <= self.current_time_us:
            return

        dt_seconds = (new_time_us - self.current_time_us) * 1e-6

        if len(self.queue) > 0:
            # Hang doi co goi cho: Credit tich luy
            self.credit += self.idle_slope * dt_seconds
        else:
            # Hang doi rong: Credit tang ve 0 neu dang am
            if self.credit < 0.0:
                self.credit += self.idle_slope * dt_seconds
                if self.credit > 0.0:
                    self.credit = 0.0
            else:
                self.credit = 0.0

        self.current_time_us = new_time_us

    def step(self) -> Optional[Packet]:
        """
        Kiem tra va thuc thi truyen goi tin neu du dieu kien (Credit >= 0).
        Tra ve goi tin vua duoc phat hoac None neu phai cho hoi phuc credit.
        """
        if not self.queue:
            return None

        # Kiem tra dieu kien phat: Credit phai >= 0
        if self.credit < 0.0:
            # Tinh thoi gian can thiet de credit hoi phuc ve 0
            time_to_zero_s = abs(self.credit) / self.idle_slope
            time_to_zero_us = time_to_zero_s * 1e6
            self.advance_time(self.current_time_us + time_to_zero_us)
            self.credit = 0.0

        # Phat goi tin dau hang doi
        pkt = self.queue.pop(0)
        pkt.tx_start_time_us = self.current_time_us

        # Thoi gian truyen goi tin tren duong truyen vat ly
        tx_duration_s = pkt.size_bits / self.port_rate_bps
        tx_duration_us = tx_duration_s * 1e6

        # Trong khi truyen, credit tieu thu voi toc do send_slope (am)
        self.credit += self.send_slope * tx_duration_s
        self.current_time_us += tx_duration_us
        pkt.tx_end_time_us = self.current_time_us

        self.transmitted_packets.append(pkt)
        return pkt

    def process_all(self) -> List[Packet]:
        """
        Dieu tiet va phat toan bo cac goi tin trong hang doi.
        """
        while self.queue:
            self.step()
        return self.transmitted_packets


if __name__ == "__main__":
    print("=========================================================")
    print("   TSN ETHERNET: IEEE 802.1Qav CREDIT-BASED SHAPER (CBS)")
    print("=========================================================\n")

    # 1. Khoi tao cong 1 Gbps (1000 Mbps) voi bang thong du tru cho Camera la 250 Mbps (25%)
    port_rate = 1000.0  # Mbps
    reserved_bw = 250.0  # Mbps
    cbs = CreditBasedShaper(port_rate_mbps=port_rate, reserved_bw_mbps=reserved_bw)

    print("1. THONG SO CAU HINH BO DIEU TIET CBS:")
    print(f"   -> Toc do cong vat ly (Port Rate) : {port_rate} Mbps")
    print(f"   -> Bang thong du tru (idleSlope)  : {reserved_bw} Mbps (25%)")
    print(f"   -> Toc do tieu thu (sendSlope)    : {cbs.send_slope / 1e6:.1f} Mbps (-750 Mbps)\n")

    assert cbs.send_slope == (250e6 - 1000e6), "sendSlope phai bang idleSlope - PortRate!"

    # 2. Mo phong dot bung no luong Camera (Traffic Burst):
    # 4 goi tin kich thuoc lon 1500 bytes (MTU) den cung luc tai thoi diem t = 0 us
    packet_size = 1500  # Bytes = 12,000 bits
    for i in range(4):
        cbs.enqueue(Packet(packet_id=i + 1, size_bytes=packet_size, arrival_time_us=0.0))

    # Phat toan bo qua CBS
    tx_results = cbs.process_all()

    print("2. KET QUA DIEU TIET DONG DU LIEU BUNG NO (4 GOI 1500 BYTES):")
    # Goi 1 truyen trong 12,000 bits / 1,000 Mbps = 12.0 us
    # Sau goi 1: credit = 0 + (-750 Mbps) * 12 us = -9000 bits
    # Thoi gian cho hoi phuc: 9000 bits / 250 Mbps = 36.0 us
    # Goi 2 phai cho den t = 12.0 + 36.0 = 48.0 us moi duoc phat!
    for p in tx_results:
        delay = p.tx_start_time_us - p.arrival_time_us
        duration = p.tx_end_time_us - p.tx_start_time_us
        print(f"   -> Goi #{p.packet_id}: Phat tu {p.tx_start_time_us:.1f} us den {p.tx_end_time_us:.1f} us (Tre cho: {delay:.1f} us, Truyen: {duration:.1f} us)")

    p1, p2, p3, p4 = tx_results
    assert p1.tx_start_time_us == 0.0, "Goi dau tien phai duoc phat ngay vi Credit = 0!"
    assert abs((p1.tx_end_time_us - p1.tx_start_time_us) - 12.0) < 1e-3, "Thoi gian phat 1500B tren cong 1Gbps la 12 us!"
    assert abs(p2.tx_start_time_us - 48.0) < 1e-3, "Goi 2 phai cho dung 36 us hoi phuc credit truoc khi phat tai 48 us!"

    # 3. Kiem tra ty le chiem dung bang thong thuc te (Measured Bandwidth Ratio)
    # Moi chu ky truyen 1 goi bao gom: 12.0 us truyen + 36.0 us cho hoi phuc credit = 48.0 us
    # Tong chu ky hoan tat cho 4 goi gom ca thoi gian hoi phuc credit cua goi cuoi ve 0:
    recovery_time_us = (abs(cbs.credit) / cbs.idle_slope) * 1e6
    full_cycle_time_us = p4.tx_end_time_us + recovery_time_us
    total_bits = 4 * packet_size * 8
    effective_bw_mbps = (total_bits / (full_cycle_time_us * 1e-6)) / 1e6
    print(f"\n3. DANH GIA TY LE BANG THONG SAU DIEU TIET:")
    print(f"   -> Tong thoi gian ca hoi phuc : {full_cycle_time_us:.1f} us (Moi chu ky goi: 48.0 us)")
    print(f"   -> Bang thong thuc te dat duoc: {effective_bw_mbps:.2f} Mbps (Muc tieu du tru: 250.00 Mbps)")

    # Ty le bang thong dat dung 250.00 Mbps
    assert abs(effective_bw_mbps - 250.0) < 1e-3, "CBS phai duy tri dung bang thong 250 Mbps du tru!"

    print("\n[THANH CONG] DA HOAN THANH BO DIEU TIET BANG THONG CREDIT-BASED SHAPER CHO CAMERA VA LIDAR!")
