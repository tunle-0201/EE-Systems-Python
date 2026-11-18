"""
Chuyen de AW: Giao tiep Bo nho Sieu toc LPDDR5X / HBM & Dong co Huan luyen Tang Vat ly PHY Timing
Bai 140 (Milestone AW.1): Leeh pha kien truc Fly-by va Thuat toan Huan luyen Write Leveling

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu kien truc duong truyen Fly-by tren bo nho toc do cao, phan tich su lech pha
          thoi gian giua Clock (CK) va Data Strobe (DQS), hien thuc thuat toan Write Leveling
          tinh chinh hang tre delay line do phan giai pico-giay theo chuan JEDEC LPDDR5X.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict, Optional


class FlyByBusTopologyModel:
    """
    Mo hinh vat ly duong truyen kien truc Fly-by giua Memory Controller va cac chip DRAM.
    
    Phan tich toan hoc & vat ly duong truyen:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Kien truc Fly-by (Noi tiep chuoi Daisy-Chain):       │
    │                                                        │
    │   Controller ────[CK]────*───────*───────*───────*──|| │
    │                          │       │       │       │     │
    │                       DRAM_0  DRAM_1  DRAM_2  DRAM_3   │
    │                          │       │       │       │     │
    │   Controller ───[DQS0]───┘       │       │       │     │
    │   Controller ───[DQS1]───────────┘       │       │     │
    │   Controller ───[DQS2]───────────────────┘       │     │
    │   Controller ───[DQS3]───────────────────────────┘     │
    │                                                        │
    │   1. Thoi gian truyen tin hieu Clock den chip k:       │
    │      t_CK[k] = t_flight_CK_0 + k * Delta_t_flight      │
    │                                                        │
    │   2. Thoi gian truyen DQS den chip k:                  │
    │      t_DQS[k] = t_trace_DQS[k]                         │
    │                                                        │
    │   3. Do lech pha thoi gian (Skew):                     │
    │      t_skew[k] = t_CK[k] - t_DQS[k]                    │
    │                                                        │
    │   Neu khong co Write Leveling, DQS se den lech hang    │
    │   tram pico-giay so voi CK, lam hong chu ky ghi!       │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        num_dram_chips: int = 4,
        ck_propagation_ps_per_hop: float = 85.0,  # 85 ps truyen giua 2 chip DRAM ke nhau
        dqs_trace_propagation_ps: List[float] = None
    ):
        self.num_chips = num_dram_chips
        self.ck_hop_ps = float(ck_propagation_ps_per_hop)

        if dqs_trace_propagation_ps is None:
            # Cac duong DQS thuong ngan hon tong duong CK daisy-chain (do do DQS den truoc CK)
            self.dqs_prop_ps = [60.0 + i * 15.0 for i in range(num_dram_chips)]
        else:
            if len(dqs_trace_propagation_ps) != num_dram_chips:
                raise ValueError("So luong duong truyen DQS phai bang so chip DRAM")
            self.dqs_prop_ps = [float(x) for x in dqs_trace_propagation_ps]

    def get_chip_skew_ps(self, chip_index: int) -> float:
        """Tinh do lech thoi gian giua CK va DQS tai chip chi dinh."""
        if chip_index < 0 or chip_index >= self.num_chips:
            raise IndexError("Chi so chip khong hop le")
        # Thoi gian CK den chip k
        t_ck = 100.0 + chip_index * self.ck_hop_ps
        t_dqs = self.dqs_prop_ps[chip_index]
        return t_ck - t_dqs


class DRAMWriteLevelingFeedbackModel:
    """
    Mo hinh hanh vi phan hoi cua chip DRAM trong che do Write Leveling (theo chuan JEDEC).
    DRAM lay mau tin hieu CK bang suon len cua DQS:
    - Neu DQS den som hon CK: DQ output = 0
    - Neu DQS den muon hon CK: DQ output = 1
    """
    def __init__(self, true_clock_arrival_ps: float):
        self.t_ck = float(true_clock_arrival_ps)

    def sample_dq(self, dqs_arrival_ps: float) -> int:
        """DRAM lay mau CK tai thoi diem dqs_arrival_ps."""
        return 1 if dqs_arrival_ps >= self.t_ck else 0


class MemoryPHYWriteLevelingEngine:
    """
    Dong co huan luyen Write Leveling tren Memory PHY.
    Dieu chinh Delay Line (DLL Coarse / Fine Steps) de can chinh DQS trung suon CK.
    
    Phan tich thuat toan tim kiem suon 0 -> 1:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Step 1: Bat che do Write Leveling qua Mode Register  │
    │   Step 2: Phat xung DQS lien tuc                       │
    │   Step 3: Tang dan delay line tu 0 ps:                 │
    │           t_dqs_total = t_dqs_trace + delay_tap        │
    │   Step 4: Ghi nhan phan hoi DQ tu DRAM [0, 0, ..., 1]  │
    │   Step 5: Khi phat hien chuyen trang thai 0 -> 1       │
    │           Khoa gia tri Delay Line:                     │
    │           Tap_opt = Tap_transition                    │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        step_resolution_ps: float = 1.25,  # Do phan giai 1 tap DLL = 1.25 picoseconds
        max_taps: int = 512
    ):
        self.step_ps = float(step_resolution_ps)
        self.max_taps = int(max_taps)

    def calibrate_channel(
        self,
        dqs_trace_delay_ps: float,
        dram_feedback: DRAMWriteLevelingFeedbackModel
    ) -> Dict[str, any]:
        """
        Thuc hien quet delay line tu 0 den max_taps de tim suon chuyen 0 -> 1.
        Tra ve (optimal_tap, optimal_delay_ps, locked, samples_history).
        """
        history: List[int] = []
        locked_tap = -1

        prev_sample = dram_feedback.sample_dq(dqs_trace_delay_ps)
        history.append(prev_sample)

        for tap in range(1, self.max_taps):
            added_delay_ps = tap * self.step_ps
            total_dqs_ps = dqs_trace_delay_ps + added_delay_ps
            sample = dram_feedback.sample_dq(total_dqs_ps)
            history.append(sample)

            # Phat hien suon len tu 0 sang 1
            if prev_sample == 0 and sample == 1:
                locked_tap = tap
                break
            prev_sample = sample

        locked = (locked_tap != -1)
        opt_delay_ps = locked_tap * self.step_ps if locked else 0.0
        final_alignment_error_ps = abs((dqs_trace_delay_ps + opt_delay_ps) - dram_feedback.t_ck) if locked else 999.0

        return {
            "locked": locked,
            "optimal_tap": locked_tap,
            "added_delay_ps": opt_delay_ps,
            "alignment_error_ps": final_alignment_error_ps,
            "total_taps_tested": len(history)
        }


def test_write_leveling_flyby():
    print("================================================================================")
    print("TEST SUITE: HUAN LUYEN WRITE LEVELING CAN CHINH CK-DQS KIEN TRUC FLY-BY")
    print("================================================================================")

    # 1. Khoi tao bus Fly-by 4 chip LPDDR5X
    bus = FlyByBusTopologyModel(num_dram_chips=4, ck_propagation_ps_per_hop=85.0)
    print(f"[1] Kien truc Fly-by 4 chip DRAM (Khoang cach giua cac chip: 85 ps):")
    
    skews = []
    for chip_id in range(4):
        skew = bus.get_chip_skew_ps(chip_id)
        skews.append(skew)
        t_ck = 100.0 + chip_id * 85.0
        t_dqs = bus.dqs_prop_ps[chip_id]
        print(f"    - DRAM[{chip_id}]: t_CK = {t_ck:5.1f} ps | t_DQS = {t_dqs:5.1f} ps | Skew = {skew:5.1f} ps")

    # Kiem tra tinh lech pha tang dan do fly-by daisy-chain
    assert skews[-1] > skews[0], "Skew tai chip cuoi cung phai lon hon do duong CK dai nhat"
    print("    -> Phat hien lech pha t_CK - t_DQS do topology Fly-by chinh xac!")

    # 2. Huan luyen Write Leveling cho tung chip bang Memory PHY DLL Engine
    phy_engine = MemoryPHYWriteLevelingEngine(step_resolution_ps=1.25, max_taps=512)
    print(f"\n[2] Huan luyen Write Leveling voi bo chia DLL (Do phan giai 1.25 ps / Tap):")

    all_locked = True
    for chip_id in range(4):
        t_ck_target = 100.0 + chip_id * 85.0
        dram_sim = DRAMWriteLevelingFeedbackModel(true_clock_arrival_ps=t_ck_target)
        t_dqs_trace = bus.dqs_prop_ps[chip_id]

        res = phy_engine.calibrate_channel(dqs_trace_delay_ps=t_dqs_trace, dram_feedback=dram_sim)
        
        print(f"    - Chip {chip_id}: Locked={res['locked']} | Opt Tap={res['optimal_tap']:3d} | Delay={res['added_delay_ps']:5.1f} ps | Error={res['alignment_error_ps']:.3f} ps")
        
        if not res["locked"] or res["alignment_error_ps"] > 1.25:
            all_locked = False

    assert all_locked is True, "Tat ca cac chip phai lock duoc voi sai so duoi 1 Tap DLL (1.25 ps)"
    print("    -> Can chinh dong pha CK-DQS thanh cong cho toan bo cac chip tren bus Fly-by!")

    # 3. Kiem tra truong hop bien: Khi duong truyen DQS bi qua tre (khong the lock trong dải tap)
    dram_far = DRAMWriteLevelingFeedbackModel(true_clock_arrival_ps=1000.0) # CK = 1000 ps
    res_fail = phy_engine.calibrate_channel(dqs_trace_delay_ps=100.0, dram_feedback=dram_far) # 100 + 512*1.25 = 740 < 1000
    print(f"\n[3] Kiem tra truong hop lech pha vuot nguong dai quet DLL:")
    print(f"    - Locked: {res_fail['locked']} (Ky vong: False khi vuot qua max taps)")
    assert res_fail["locked"] is False, "Phai phat hien failure khi vuot qua dai dieu chinh DLL"

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AW.1 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_write_leveling_flyby()
