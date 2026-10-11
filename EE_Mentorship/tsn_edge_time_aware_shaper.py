"""
================================================================================
          MODULE AC: TIME-SENSITIVE NETWORKING & DETERMINISTIC ETHERNET
          MILESTONE AC.3: IEEE 802.1Qbv TIME-AWARE SHAPER (TAS) & GCL SCHEDULE
================================================================================

TAI SAO BO DINH THOI CONG TAS LA TRAI TIM CUA MANG MAY TINH BAY TIEN DINH?
- Trong he thong tau vu tru SpaceX va xe tu hanh Tesla FSD:
  Co nhung goi tin an toan toi quan trong (Scheduled Traffic - ST: Lenh lai gimbal
  dong co ten lua, phanh khan cap AEB) khong bao gio duoc phep bi cham tre!
- Van de nghiem trong cua switch thong thuong (Non-TSN):
  Mot goi tin chan doan dung luong lon (1518 bytes MTU) vua bat dau phat 1 nanogiay
  truoc khi goi tin phanh khan cap den. Goi tin phanh bi ket trong hang doi suot
  12.144 micro-giay (Store-and-Forward Blocking Jitter)!
- Chuan IEEE 802.1Qbv Time-Aware Shaper (TAS):
  1. Dong / mo cac cong hang doi theo lich trinh thoi gian tuan hoan cuc ky chinh xac
     duoc dong bo boi PTP: Bang kiem soat cong GCL (Gate Control List).
  2. Tao dai dem phong ve (Guard Band): Cam cac goi tin thong thuong bat dau phat
     neu chung khong the hoan tat truoc khi khe thoi gian uu tien bat dau!
  3. Dam bao goi tin Scheduled Traffic co do tre hang doi bang 0 tuyet doi (Queue Delay = 0 us)!

SO DO KHOANG THOI GIAN GCL VA DAI DEM GUARD BAND (ASCII DIAGRAM):

   Chu ky tuan hoan GCL (Cycle Time T_cycle = 1000 us = 1 ms):
   +──────────────────────────────+───────────────────────+──────────────+
   | Slot 1: Scheduled Traffic ST | Slot 2: Best-Effort BE|  Guard Band  |
   | Cong Hang doi 7 (ST): MO     | Cong 7 (ST): DONG     |  Tat ca      |
   | Cong Hang doi 0 (BE): DONG   | Cong 0 (BE): MO       |  DONG (HOLD) |
   | Thoi luong: 200.0 us         | Thoi luong: 787.8 us  |  12.2 us     |
   +──────────────────────────────+───────────────────────+──────────────+
   0 us                           200 us                  987.8 us       1000 us

TOAN HOC XAC DINH DAI DEM GUARD BAND (ASCII MATH BLOCKS):

1. Thoi gian phat goi tin lon nhat cua hang doi thong thuong (Max Frame BE):
                 Max_Frame_Size_BE * 8
   T_guard = ─────────────────────────────
                       Port_Rate

   Vi du voi cong 1 Gbps (1000 Mbps) va goi MTU 1518 Bytes:
               1518 * 8 bits
   T_guard = ────────────────── = 12.144 microseconds (us)
               1000 * 10^6 bps

2. Luat kiem soat truyen goi Best-Effort tai cuoi Slot 2:
   Neu thoi gian con lai truoc khi bat dau Slot 1 nho hon thoi gian truyen goi:
   -> CHAN KHONG CHO TRUYEN (Hold in queue)!
   -> Cho den chu ky Slot BE tiep theo!

3. Ket qua: Khi Slot 1 mo, duong truyen 100% thong thoang!
   Do tre hang doi cua goi Scheduled Traffic: Queue_Delay = 0.00 us!
"""

from typing import Tuple, List, Dict, Any, Optional


class GCLEntry:
    """
    Mot dong trong Bang kiem soat cong GCL (Gate Control List Entry).
    - gate_states_mask: Bitmask 8-bit dai dien trang thai dong/mo cua 8 hang doi (Bit 7: ST, Bit 0: BE).
    - duration_us: Thoi luong khe thoi gian nay (Microseconds).
    """

    def __init__(self, gate_states_mask: int, duration_us: float):
        self.gate_states_mask = int(gate_states_mask)
        self.duration_us = float(duration_us)

    def is_queue_open(self, queue_idx: int) -> bool:
        return bool((self.gate_states_mask >> queue_idx) & 1)


class TimeAwareShaper:
    """
    Bo dinh thoi cong Time-Aware Shaper (TAS) theo chuan IEEE 802.1Qbv.
    - port_rate_mbps: Toc do cong vat ly (Mbps)
    - gcl: Danh sach cac dong GCL lap lai tuan hoan
    """

    def __init__(self, port_rate_mbps: float, gcl: List[GCLEntry]):
        self.port_rate_bps = float(port_rate_mbps) * 1e6
        self.gcl = gcl
        self.cycle_time_us = sum(entry.duration_us for entry in self.gcl)

        # 8 hang doi uu tien (Queue 7: ST, Queue 0: BE)
        self.queues: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(8)}
        self.transmitted_log: List[Dict[str, Any]] = []

    def get_current_gcl_state(self, current_time_us: float) -> Tuple[GCLEntry, float]:
        """
        Xac dinh trang thai GCL tai thoi diem current_time_us:
        Tra ve (active_gcl_entry, time_remaining_in_slot_us).
        """
        time_in_cycle = current_time_us % self.cycle_time_us
        accumulated_time = 0.0

        for entry in self.gcl:
            if accumulated_time <= time_in_cycle < (accumulated_time + entry.duration_us):
                time_remaining = (accumulated_time + entry.duration_us) - time_in_cycle
                return entry, time_remaining
            accumulated_time += entry.duration_us

        # Mac dinh entry cuoi cung
        return self.gcl[-1], 0.0

    def enqueue_packet(self, queue_idx: int, packet_id: str, size_bytes: int, arrival_time_us: float) -> None:
        self.queues[queue_idx].append({
            "packet_id": packet_id,
            "size_bytes": size_bytes,
            "size_bits": size_bytes * 8,
            "arrival_time_us": arrival_time_us
        })

    def can_transmit_without_preemption(self, size_bytes: int, time_remaining_in_slot_us: float) -> bool:
        """
        Kiem tra Guard Band: Goi tin co kip truyen xong truoc khi khe thoi gian ket thuc khong.
        """
        tx_duration_us = (size_bytes * 8 / self.port_rate_bps) * 1e6
        return tx_duration_us <= time_remaining_in_slot_us

    def simulate_step(self, current_time_us: float) -> Tuple[float, Optional[Dict[str, Any]]]:
        """
        Thuc thi mot buoc chuyen mach tai thoi diem current_time_us:
        - Xet hang doi uu tien cao nhat co cong dang MO
        - Kiem tra Guard Band
        - Phat goi tin neu thoa man
        Tra ve (next_time_us, transmitted_packet_info).
        """
        entry, time_remaining = self.get_current_gcl_state(current_time_us)

        # Tim thoi diem den gan nhat cua cac goi tin neu chua co goi nao san sang
        earliest_future_arrival = None

        # Quet tu hang doi 7 (Uu tien cao nhat) xuong hang doi 0
        for q_idx in range(7, -1, -1):
            if entry.is_queue_open(q_idx) and len(self.queues[q_idx]) > 0:
                pkt = self.queues[q_idx][0]
                # Kiem tra xem co phai thoi diem goi tin da den khong
                if pkt["arrival_time_us"] > current_time_us:
                    if earliest_future_arrival is None or pkt["arrival_time_us"] < earliest_future_arrival:
                        earliest_future_arrival = pkt["arrival_time_us"]
                    continue

                # Kiem tra Guard Band: Co du thoi gian truyen truoc khi dong cong khong?
                if self.can_transmit_without_preemption(pkt["size_bytes"], time_remaining):
                    # Phat goi tin thanh cong!
                    self.queues[q_idx].pop(0)
                    tx_duration_us = (pkt["size_bits"] / self.port_rate_bps) * 1e6
                    queue_delay_us = current_time_us - pkt["arrival_time_us"]

                    log_entry = {
                        "packet_id": pkt["packet_id"],
                        "queue_idx": q_idx,
                        "size_bytes": pkt["size_bytes"],
                        "tx_start_us": current_time_us,
                        "tx_end_us": current_time_us + tx_duration_us,
                        "queue_delay_us": queue_delay_us
                    }
                    self.transmitted_log.append(log_entry)
                    return current_time_us + tx_duration_us, log_entry
                else:
                    # Bi Guard Band chan lai vi khong kip truyen xong!
                    # Phai cho den khi khe thoi gian nay ket thuc
                    return current_time_us + time_remaining + 0.001, None

        # Neu co goi tin den trong tuong lai, tien thoi gian toi thoi diem goi den
        if earliest_future_arrival is not None:
            next_t = min(current_time_us + time_remaining, earliest_future_arrival)
            return next_t, None

        # Neu khong co goi nao phat duoc, tien thoi gian den het slot nay
        return current_time_us + max(1.0, time_remaining), None


if __name__ == "__main__":
    print("=========================================================")
    print("   TSN ETHERNET: IEEE 802.1Qbv TIME-AWARE SHAPER (TAS)")
    print("=========================================================\n")

    # 1. Thiet lap Bang kiem soat cong GCL tren cong 1 Gbps (T_cycle = 1000 us = 1 ms):
    # - Slot 1 (ST): 0 us -> 200 us (Queue 7 Open = 0b10000000)
    # - Slot 2 (BE): 200 us -> 987.856 us (Queue 0 Open = 0b00000001, Thoi luong 787.856 us)
    # - Slot 3 (Guard Band): 987.856 us -> 1000.0 us (All Closed = 0b00000000, Thoi luong 12.144 us)
    port_rate_mbps = 1000.0
    guard_band_us = (1518 * 8 / 1e9) * 1e6  # 12.144 us

    gcl_schedule = [
        GCLEntry(gate_states_mask=0b10000000, duration_us=200.0),                     # Slot 1: Scheduled Traffic (Queue 7)
        GCLEntry(gate_states_mask=0b00000001, duration_us=1000.0 - 200.0 - guard_band_us),  # Slot 2: Best-Effort (Queue 0)
        GCLEntry(gate_states_mask=0b00000000, duration_us=guard_band_us)              # Slot 3: Guard Band (All Closed)
    ]

    tas = TimeAwareShaper(port_rate_mbps=port_rate_mbps, gcl=gcl_schedule)

    print("1. CAU HINH BANG KIEM SOAT CONG GCL (GATE CONTROL LIST):")
    print(f"   -> Tong chu ky T_cycle       : {tas.cycle_time_us:.3f} us (1.0 ms)")
    print(f"   -> Slot 1 (Scheduled Traffic): 200.000 us (Queue 7 MO)")
    print(f"   -> Slot 2 (Best-Effort)      : {gcl_schedule[1].duration_us:.3f} us (Queue 0 MO)")
    print(f"   -> Slot 3 (Guard Band)       : {guard_band_us:.3f} us (Tat ca DONG chong chan goi)\n")

    assert abs(tas.cycle_time_us - 1000.0) < 1e-3, "Tong chu ky GCL phai dung 1000 us!"

    # 2. Kich ban kiem tra tinh dung dan:
    # Goi BE #1 (1500B) den tai t = 205.0 us (trong Slot 2) -> Du thoi gian truyen ngay.
    # Goi BE #2 (1500B) den tai t = 980.0 us (cach Guard Band 7.8 us, can 12.0 us de truyen)
    #   -> BI GUARD BAND CHAN LAI!
    # Goi ST khẩn cấp #1 (250B) den tai t = 1000.0 us (dung moc Slot 1 cua chu ky 2)
    #   -> PHAI DUOC PHAT NGAY LAP TUC VOI QUEUE DELAY = 0.0 us!

    tas.enqueue_packet(queue_idx=0, packet_id="BE_Packet_1", size_bytes=1500, arrival_time_us=205.0)
    tas.enqueue_packet(queue_idx=0, packet_id="BE_Packet_2", size_bytes=1500, arrival_time_us=980.0)
    tas.enqueue_packet(queue_idx=7, packet_id="ST_Flight_Critical", size_bytes=250, arrival_time_us=1000.0)

    # Chay mo phong
    sim_time = 0.0
    while len(tas.transmitted_log) < 3 and sim_time < 3000.0:
        sim_time, _ = tas.simulate_step(sim_time)

    print("2. KET QUA DIEU PHOI CONG THEO THOI GIAN THUC TAS:")
    for log in tas.transmitted_log:
        print(f"   -> Goi [{log['packet_id']}] (Hang doi {log['queue_idx']}):")
        print(f"      + Thoi diem phat     : {log['tx_start_us']:.1f} us -> {log['tx_end_us']:.1f} us")
        print(f"      + Do tre hang doi    : {log['queue_delay_us']:.3f} us")

    # Kiem tra ket qua:
    be1, st_pkt, be2 = sorted(tas.transmitted_log, key=lambda x: x["tx_start_us"])

    assert be1["packet_id"] == "BE_Packet_1"
    assert st_pkt["packet_id"] == "ST_Flight_Critical"
    assert be2["packet_id"] == "BE_Packet_2"

    print(f"\n3. DANH GIA TINH TIEN DINH (DETERMINISTIC FLIGHT DELAY):")
    print(f"   -> Do tre hang doi ST_Flight_Critical : {st_pkt['queue_delay_us']:.3f} us (Zero Queue Jitter!)")
    assert abs(st_pkt["queue_delay_us"]) < 1e-3, "Goi tin Scheduled Traffic phai co Queue Delay = 0.0 us tuyet doi!"

    print(f"   -> Goi BE_Packet_2 da bi Guard Band giu lai va phat tai Slot 2 cua chu ky tiep theo: {be2['tx_start_us']:.1f} us")
    assert be2["tx_start_us"] >= 1200.0, "BE_Packet_2 phai bi hoan den Slot 2 cua chu ky ke tiep!"

    print("\n[THANH CONG] DA HOAN THANH BO DINH THOI CONG TIME-AWARE SHAPER (TAS) IEEE 802.1Qbv ZERO-JITTER!")
