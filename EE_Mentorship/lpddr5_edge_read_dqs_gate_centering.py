"""
Chuyen de AW: Giao tiep Bo nho Sieu toc LPDDR5X / HBM & Dong co Huan luyen Tang Vat ly PHY Timing
Bai 141 (Milestone AW.2): Dinh vi Cong doc DQS Gating va Can tam Mat du lieu doc Read DQ Centering

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu ky thuat mo cong doc DQS (Read Gating) chong nhieu Preamble, hien thuc thuat toan
          dich pha 90 do va can tam mat du lieu doc (Read DQ Eye Centering) toi uu hoa do mo
          thoi gian Timing Margin cho chip Apple Silicon & Tesla FSD HW4.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict, Optional


class ReadDQSBurstSignalModel:
    """
    Mo hinh xung nhip DQS doc phat tu DRAM (Burst Strobe kem Preamble va Postamble).
    
    Phan tich dang song JEDEC LPDDR5:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Trang thai tro khang cao Tri-State (Hi-Z):           │
    │   Khong co doc => DQS tro lo lung (Floating)           │
    │                                                        │
    │   Preamble: DRAM keo DQS ve muc thap / toggle truoc doc│
    │   t_preamble: Khoang thoi gian tien de                 │
    │                                                        │
    │   Burst Data: Chuoi xung chuyen muc 0/1/0/1 lien tuc   │
    │   Moi chu ky xung truyen 2 bit du lieu (DDR)           │
    │                                                        │
    │   Phan tich mien thoi gian (ps):                       │
    │   ├─── Hi-Z ───┼── Preamble ──┼── DQS Toggles ──┼── Hi-Z │
    │   0            t_start        t_burst_start     t_end  │
    │                                                        │
    │   Nhiem vu Cong doc (DQS Gate):                        │
    │   Phai mo cong chinh xac trong cua so Preamble!       │
    │   Mo som => Bat nhieu Hi-Z lam sai lech bo dem         │
    │   Mo muon => Cat mat xung DQS dau tien                 │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        ui_ps: float = 125.0,            # 1 UI = 125 ps (8000 MT/s)
        burst_length: int = 16,          # BL16
        preamble_ui: float = 4.0,        # 4 UI preamble
        t_flight_roundtrip_ps: float = 850.0 # Thoi gian di ve tong cong
    ):
        self.ui = float(ui_ps)
        self.bl = int(burst_length)
        self.t_preamble_start = float(t_flight_roundtrip_ps)
        self.t_preamble_duration = self.ui * preamble_ui
        self.t_burst_start = self.t_preamble_start + self.t_preamble_duration
        self.t_burst_duration = (self.bl / 2.0) * (2.0 * self.ui) # bl * ui
        self.t_burst_end = self.t_burst_start + self.t_burst_duration

    def get_signal_state_at(self, t_ps: float) -> str:
        """Kiem tra trang thai DQS tai thoi diem t_ps."""
        if t_ps < self.t_preamble_start:
            return "HI_Z"
        elif self.t_preamble_start <= t_ps < self.t_burst_start:
            return "PREAMBLE"
        elif self.t_burst_start <= t_ps <= self.t_burst_end:
            return "BURST_DATA"
        else:
            return "HI_Z"


class ReadDQSGatingCalibrator:
    """
    Bo huan luyen Cong doc DQS (DQS Gate Training Engine).
    Quet delay line de tim cua so mo cong hoan hao nam tron trong vung Preamble.
    """
    def __init__(self, step_resolution_ps: float = 2.5, max_steps: int = 500):
        self.step_ps = float(step_resolution_ps)
        self.max_steps = int(max_steps)

    def calibrate_gate_window(self, dqs_model: ReadDQSBurstSignalModel) -> Dict[str, any]:
        """
        Quet vi tri mo cong de tim vi tri bat dau va ket thuc cua vung Preamble hop le.
        """
        left_bound_tap = -1
        right_bound_tap = -1

        for tap in range(self.max_steps):
            t_gate_open = tap * self.step_ps
            state = dqs_model.get_signal_state_at(t_gate_open)

            if state == "PREAMBLE":
                if left_bound_tap == -1:
                    left_bound_tap = tap
                right_bound_tap = tap

        if left_bound_tap != -1 and right_bound_tap != -1:
            opt_tap = (left_bound_tap + right_bound_tap) // 2
            opt_time_ps = opt_tap * self.step_ps
            window_size_ps = (right_bound_tap - left_bound_tap) * self.step_ps
            return {
                "locked": True,
                "optimal_gate_tap": opt_tap,
                "optimal_gate_time_ps": opt_time_ps,
                "window_size_ps": window_size_ps,
                "preamble_start_ps": dqs_model.t_preamble_start,
                "preamble_end_ps": dqs_model.t_burst_start
            }
        else:
            return {
                "locked": False,
                "optimal_gate_tap": -1,
                "optimal_gate_time_ps": 0.0,
                "window_size_ps": 0.0
            }


class ReadDQCenteringEngine:
    """
    Dong co can tam mat du lieu doc (Read DQ Eye Centering).
    
    Phan tich can chinh pha:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   DRAM phat DQ va DQS dong pha (Edge-Aligned):         │
    │                                                        │
    │   DQ :    ──[ Bit 0 ]───[ Bit 1 ]───[ Bit 2 ]───       │
    │   DQS:    ──|___________|───────────|___________|──    │
    │             ^                                          │
    │             Suon DQS trung voi suon doi bit!           │
    │                                                        │
    │   PHY phai dich pha DQS 90 do (1/2 UI):                │
    │                                                        │
    │   DQS_del:──────|___________|───────────|_______       │
    │                     ^                                  │
    │                     Lay mau ngay giua tam mat DQ!      │
    │                                                        │
    │   Thuat toan Eye Sweeper:                              │
    │   Quet Delay Line tu -1/2 UI den +1/2 UI               │
    │   Xac dinh bien trai (Setup fail) va bien phai (Hold fail)│
    │                                                        │
    │                 Tap_left + Tap_right                   │
    │   Tap_optimal = ────────────────────                   │
    │                          2                             │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(self, ui_ps: float = 125.0, step_resolution_ps: float = 1.25):
        self.ui = float(ui_ps)
        self.step_ps = float(step_resolution_ps)
        self.num_taps = int(math.ceil((1.5 * self.ui) / self.step_ps))

    def sweep_data_eye(
        self,
        dq_skew_offset_ps: float,
        eye_width_ps: float = 95.0,  # Mat mo 95 ps tren tong 125 ps UI
        expected_pattern: int = 0xAA55
    ) -> Dict[str, any]:
        """
        Mo phong quet toan bo mat doc de tim bien Pass/Fail cua Setup va Hold.
        dq_skew_offset_ps: Do lech pha thuc te giua DQS va DQ.
        """
        # Tam mat thuc te nam tai dq_skew_offset_ps + UI/2
        center_eye_actual = dq_skew_offset_ps + (self.ui / 2.0)
        half_eye = eye_width_ps / 2.0
        pass_left_ps = center_eye_actual - half_eye
        pass_right_ps = center_eye_actual + half_eye

        pass_taps = []
        for tap in range(self.num_taps):
            t_sample = tap * self.step_ps
            # Kiem tra thoi diem lay mau co nam trong mat mo khong
            if pass_left_ps <= t_sample <= pass_right_ps:
                pass_taps.append(tap)

        if not pass_taps:
            return {
                "locked": False,
                "eye_width_measured_ps": 0.0,
                "optimal_tap": -1,
                "setup_margin_ps": 0.0,
                "hold_margin_ps": 0.0
            }

        left_tap = pass_taps[0]
        right_tap = pass_taps[-1]
        opt_tap = (left_tap + right_tap) // 2
        measured_width_ps = (right_tap - left_tap) * self.step_ps
        opt_time_ps = opt_tap * self.step_ps

        setup_margin_ps = opt_time_ps - (left_tap * self.step_ps)
        hold_margin_ps = (right_tap * self.step_ps) - opt_time_ps

        return {
            "locked": True,
            "optimal_tap": opt_tap,
            "optimal_delay_ps": opt_time_ps,
            "eye_width_measured_ps": measured_width_ps,
            "setup_margin_ps": setup_margin_ps,
            "hold_margin_ps": hold_margin_ps,
            "total_pass_taps": len(pass_taps)
        }


def test_read_dqs_gating_and_centering():
    print("================================================================================")
    print("TEST SUITE: DINH VI CONG DOC DQS GATING VA CAN TAM MAT DU LIEU DOC READ DQ")
    print("================================================================================")

    # 1. Kiem tra mo hinh xung DQS doc (LPDDR5 8000 MT/s, UI = 125 ps, Preamble = 4 UI = 500 ps)
    dqs_burst = ReadDQSBurstSignalModel(
        ui_ps=125.0,
        burst_length=16,
        preamble_ui=4.0,
        t_flight_roundtrip_ps=850.0
    )
    print(f"[1] Tin hieu Read DQS LPDDR5 (Round-trip delay = {dqs_burst.t_preamble_start:.1f} ps):")
    print(f"    - Preamble bat dau tai: {dqs_burst.t_preamble_start:.1f} ps")
    print(f"    - Preamble ket thuc tai:{dqs_burst.t_burst_start:.1f} ps (Do dai = {dqs_burst.t_preamble_duration:.1f} ps)")
    print(f"    - Burst Data ket thuc:  {dqs_burst.t_burst_end:.1f} ps")

    assert dqs_burst.get_signal_state_at(800.0) == "HI_Z"
    assert dqs_burst.get_signal_state_at(1000.0) == "PREAMBLE"
    assert dqs_burst.get_signal_state_at(1500.0) == "BURST_DATA"
    print("    -> Trang thai tin hieu DQS (Hi-Z -> Preamble -> Burst) duoc xac dinh chinh xac!")

    # 2. Huan luyen Cong doc DQS Gating (DQS Gate Training)
    gate_cal = ReadDQSGatingCalibrator(step_resolution_ps=2.5, max_steps=600)
    gate_res = gate_cal.calibrate_gate_window(dqs_burst)
    print(f"\n[2] Huan luyen Cong doc DQS Gating (Buoc DLL = 2.5 ps):")
    print(f"    - Locked: {gate_res['locked']}")
    print(f"    - Optimal Gate Open Tap:  {gate_res['optimal_gate_tap']} ({gate_res['optimal_gate_time_ps']:.1f} ps)")
    print(f"    - Kich thuoc cua so Gate: {gate_res['window_size_ps']:.1f} ps (Ky vong ~ 500 ps)")

    assert gate_res["locked"] is True, "Gate training phai lock thanh cong"
    # Optimal gate time phai nam chinh xac giua Preamble (850 + 250 = 1100 ps)
    assert abs(gate_res["optimal_gate_time_ps"] - 1100.0) < 5.0, "Gate time phai nam o trung tam Preamble"
    print("    -> Cong doc DQS mo hoan hao tai tam cua so Preamble, triet tieu hoan toan nhieu Hi-Z!")

    # 3. Huan luyen can tam mat du lieu doc (Read DQ Centering)
    # 1 UI = 125 ps, mat mo 92 ps (bi hep do ISI va jitter 33 ps)
    # Do lech skew duong truyen = 15 ps
    dq_centering = ReadDQCenteringEngine(ui_ps=125.0, step_resolution_ps=1.25)
    eye_res = dq_centering.sweep_data_eye(dq_skew_offset_ps=15.0, eye_width_ps=92.0)

    print(f"\n[3] Can tam mat du lieu doc Read DQ Centering:")
    print(f"    - Locked: {eye_res['locked']}")
    print(f"    - Optimal Sampling Tap:   {eye_res['optimal_tap']} (t = {eye_res['optimal_delay_ps']:.2f} ps)")
    print(f"    - Do rong mat do duoc:    {eye_res['eye_width_measured_ps']:.2f} ps")
    print(f"    - Setup Margin:           {eye_res['setup_margin_ps']:.2f} ps")
    print(f"    - Hold Margin:            {eye_res['hold_margin_ps']:.2f} ps")

    assert eye_res["locked"] is True, "DQ centering phai lock thanh cong"
    # Setup va Hold margin phai can xung tuyet doi (chenh lech < 2 ps)
    margin_diff = abs(eye_res["setup_margin_ps"] - eye_res["hold_margin_ps"])
    assert margin_diff <= 2.5, f"Tam mat chua can xung: diff = {margin_diff}"
    assert eye_res["eye_width_measured_ps"] >= 88.0, "Do mo mat doc phai du lon de dam bao BER < 1e-12"
    print("    -> Can tam mat doc thanh cong voi Setup/Hold margin hoan toan can xung!")

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AW.2 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_read_dqs_gating_and_centering()
