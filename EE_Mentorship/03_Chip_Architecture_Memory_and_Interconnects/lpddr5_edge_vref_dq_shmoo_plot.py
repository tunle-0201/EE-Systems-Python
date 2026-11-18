"""
Chuyen de AW: Giao tiep Bo nho Sieu toc LPDDR5X / HBM & Dong co Huan luyen Tang Vat ly PHY Timing
Bai 142 (Milestone AW.3): Hieu chuan Dien ap Tham chieu Vref-DQ va Bieu do Shmoo Mat 2D

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu ky thuat hieu chuan dien ap tham chieu Vref-DQ tren chuan tin hieu bien do thap
          LVSTL (VDDQ = 0.5V), xay dung dong co quet 2D Shmoo Plot (Voltage vs Time Delay)
          de xac dinh tam mat toi uu (Optimal Sampling Point) va dien tich mat Eye Area.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict, Optional


class SignalEyePhysics2DModel:
    """
    Mo hinh vat ly mat tin hieu 2D (Dien ap Vref theo truc doc, Thoi gian Delay theo truc ngang).
    
    Phan tich toan hoc & bien do LVSTL LPDDR5:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Chuan tin hieu LVSTL (VDDQ = 0.5V = 500 mV):         │
    │                                                        │
    │   Vref (mV)                                            │
    │    400 ┤        ... FAIL (Vref qua cao) ...            │
    │        │      ┌─────────────────────────────┐          │
    │    300 ┤      │                             │          │
    │        │      │    VUNG HOAT DONG PASS      │          │
    │    250 ┤======│====== [V_opt, T_opt] =======│ (Tam mat)│
    │        │      │     (Eye Area cuc dai)      │          │
    │    200 ┤      │                             │          │
    │        │      └─────────────────────────────┘          │
    │    100 ┤        ... FAIL (Vref qua thap) ...           │
    │        └──────┴───────────────┴─────────────┴──> Delay │
    │              T_left         T_center      T_right (ps) │
    │                                                        │
    │   1. Chieu cao mat (Eye Height):                       │
    │      EH = Vref_max_pass - Vref_min_pass (mV)           │
    │                                                        │
    │   2. Chieu rong mat (Eye Width):                       │
    │      EW = Delay_max_pass - Delay_min_pass (ps)         │
    │                                                        │
    │   3. Dien tich mat (Eye Area Index):                   │
    │      EA = EH * EW  (mV * ps)                           │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        vddq_mv: float = 500.0,
        nominal_vref_mv: float = 250.0,
        nominal_center_delay_ps: float = 62.5,  # Giua 125 ps UI
        eye_height_mv: float = 160.0,           # Chieu cao mat mo 160 mV
        eye_width_ps: float = 90.0,             # Chieu rong mat mo 90 ps
        jitter_rms_ps: float = 2.0,
        voltage_noise_rms_mv: float = 4.0
    ):
        self.vddq = float(vddq_mv)
        self.vref_center = float(nominal_vref_mv)
        self.delay_center = float(nominal_center_delay_ps)
        self.eh = float(eye_height_mv)
        self.ew = float(eye_width_ps)
        self.jitter_ps = float(jitter_rms_ps)
        self.v_noise_mv = float(voltage_noise_rms_mv)

    def evaluate_ber_at_point(self, vref_mv: float, delay_ps: float) -> float:
        """
        Tinh xac suat loi bit BER tai toa do (vref_mv, delay_ps) bang mo hinh Q-function elip.
        Khoang cach chuan hoa tu tam mat:
        r_norm^2 = ( (t - t_c) / (EW/2) )^2 + ( (v - v_c) / (EH/2) )^2
        """
        norm_t = (delay_ps - self.delay_center) / max(1.0, self.ew / 2.0)
        norm_v = (vref_mv - self.vref_center) / max(1.0, self.eh / 2.0)
        dist_sq = (norm_t ** 2) + (norm_v ** 2)

        # Neu nam ben trong duong bao elip mat mo: BER rat nho (< 1e-12)
        if dist_sq <= 0.85:
            return 0.0
        elif dist_sq <= 1.05:
            # Vung bien chuyen tiep Setup/Hold
            margin = 1.05 - dist_sq
            return 1e-4 * math.exp(-margin * 10.0)
        else:
            # Ngoai mat mo: BER cao (Fail)
            return 0.5 * (1.0 - math.exp(-(dist_sq - 1.05) * 5.0))


class ShmooPlot2DScannerEngine:
    """
    Dong co quet ma tran 2D Shmoo Plot (Vref Step vs Delay Tap).
    Tu dong tim diem dat toi uu (Vref_opt, Delay_opt) co do du phong (Margin) cao nhat.
    """
    def __init__(
        self,
        vref_range_mv: Tuple[float, float] = (150.0, 350.0),
        vref_step_mv: float = 10.0,
        delay_range_ps: Tuple[float, float] = (10.0, 115.0),
        delay_step_ps: float = 2.5
    ):
        self.v_min, self.v_max = vref_range_mv
        self.v_step = float(vref_step_mv)
        self.d_min, self.d_max = delay_range_ps
        self.d_step = float(delay_step_ps)

        # Tao danh sach diem quet
        self.vref_grid = []
        cur_v = self.v_min
        while cur_v <= self.v_max + 1e-4:
            self.vref_grid.append(round(cur_v, 2))
            cur_v += self.v_step

        self.delay_grid = []
        cur_d = self.d_min
        while cur_d <= self.d_max + 1e-4:
            self.delay_grid.append(round(cur_d, 2))
            cur_d += self.d_step

    def execute_shmoo_scan(self, eye_model: SignalEyePhysics2DModel) -> Dict[str, any]:
        """
        Quet toan bo ma tran 2D va trich xuat cac thong so mat tin hieu.
        """
        shmoo_matrix: List[List[int]] = [] # 1 la Pass, 0 la Fail
        pass_points: List[Tuple[float, float]] = []

        for v in self.vref_grid:
            row = []
            for d in self.delay_grid:
                ber = eye_model.evaluate_ber_at_point(v, d)
                is_pass = 1 if ber < 1e-6 else 0
                row.append(is_pass)
                if is_pass == 1:
                    pass_points.append((v, d))
            shmoo_matrix.append(row)

        if not pass_points:
            return {
                "valid_eye": False,
                "eye_height_mv": 0.0,
                "eye_width_ps": 0.0,
                "eye_area_mv_ps": 0.0,
                "optimal_vref_mv": 0.0,
                "optimal_delay_ps": 0.0,
                "total_pass_pixels": 0
            }

        # Tinh chieu cao mat EH va chieu rong mat EW tu tap diem Pass
        v_passes = [pt[0] for pt in pass_points]
        d_passes = [pt[1] for pt in pass_points]

        v_min_pass = min(v_passes)
        v_max_pass = max(v_passes)
        d_min_pass = min(d_passes)
        d_max_pass = max(d_passes)

        eh_measured = v_max_pass - v_min_pass
        ew_measured = d_max_pass - d_min_pass

        # Tam toi uu la trung vi cua dai Pass
        v_opt = (v_min_pass + v_max_pass) / 2.0
        d_opt = (d_min_pass + d_max_pass) / 2.0

        eye_area = len(pass_points) * self.v_step * self.d_step

        return {
            "valid_eye": True,
            "eye_height_mv": eh_measured,
            "eye_width_ps": ew_measured,
            "eye_area_mv_ps": eye_area,
            "optimal_vref_mv": v_opt,
            "optimal_delay_ps": d_opt,
            "vref_pass_range": (v_min_pass, v_max_pass),
            "delay_pass_range": (d_min_pass, d_max_pass),
            "total_pass_pixels": len(pass_points),
            "shmoo_matrix": shmoo_matrix
        }


def format_ascii_shmoo(shmoo_results: Dict[str, any], vref_grid: List[float], delay_grid: List[float]) -> str:
    """Ve bieu do Shmoo 2D duoi dang khoi ASCII truc quan."""
    mat = shmoo_results["shmoo_matrix"]
    lines = []
    lines.append("  Vref (mV)  +" + "-" * len(delay_grid) + "+")
    for r_idx in range(len(vref_grid) - 1, -1, -1):
        v = vref_grid[r_idx]
        chars = []
        for c_idx in range(len(delay_grid)):
            chars.append("*" if mat[r_idx][c_idx] == 1 else ".")
        row_str = "".join(chars)
        lines.append(f"   {v:5.1f} mV |{row_str}|")
    lines.append("             +" + "-" * len(delay_grid) + "+")
    lines.append(f"             Delay: {delay_grid[0]:.1f} ps ---------> {delay_grid[-1]:.1f} ps")
    return "\n".join(lines)


def test_vref_dq_shmoo_plot():
    print("================================================================================")
    print("TEST SUITE: HIEU CHUAN VREF-DQ VA MO PHONG BIEU DO SHMOO MAT 2D LPDDR5X")
    print("================================================================================")

    # 1. Khoi tao mo hinh mat tin hieu LPDDR5X (VDDQ = 500 mV, Vref_center = 250 mV, Center_delay = 62.5 ps)
    eye_model = SignalEyePhysics2DModel(
        vddq_mv=500.0,
        nominal_vref_mv=250.0,
        nominal_center_delay_ps=62.5,
        eye_height_mv=150.0,
        eye_width_ps=80.0
    )
    print(f"[1] Khoi tao mat tin hieu LPDDR5X LVSTL 500 mV:")
    print(f"    - Tam mat danh dinh: Vref = {eye_model.vref_center:.1f} mV | Delay = {eye_model.delay_center:.1f} ps")
    print(f"    - Kich thuoc mat mo ly thuyet: EH = {eye_model.eh:.1f} mV | EW = {eye_model.ew:.1f} ps")

    # Kiem tra BER tai tam mat va tai bien fail
    ber_center = eye_model.evaluate_ber_at_point(250.0, 62.5)
    ber_fail = eye_model.evaluate_ber_at_point(400.0, 62.5)
    print(f"    - BER tai tam mat (250 mV, 62.5 ps): {ber_center:.1e} (Pass tuyet doi)")
    print(f"    - BER tai vung ngoai bien (400 mV):   {ber_fail:.2f} (Fail ro ret)")
    assert ber_center == 0.0, "Tam mat phai co BER = 0"
    assert ber_fail > 0.1, "Ngoai mat phai co BER cao"

    # 2. Chay dong co quet 2D Shmoo Plot
    scanner = ShmooPlot2DScannerEngine(
        vref_range_mv=(160.0, 340.0),
        vref_step_mv=10.0,
        delay_range_ps=(15.0, 110.0),
        delay_step_ps=2.5
    )
    res = scanner.execute_shmoo_scan(eye_model)

    print(f"\n[2] Ket qua quet 2D Shmoo Plot ({len(scanner.vref_grid)} x {len(scanner.delay_grid)} diem quet):")
    print(f"    - Valid Eye:              {res['valid_eye']}")
    print(f"    - Chieu cao mat do duoc:  {res['eye_height_mv']:.1f} mV (Dai Vref Pass: {res['vref_pass_range']})")
    print(f"    - Chieu rong mat do duoc: {res['eye_width_ps']:.1f} ps (Dai Delay Pass: {res['delay_pass_range']})")
    print(f"    - Toa do tam toi uu:      Vref_opt = {res['optimal_vref_mv']:.1f} mV | Delay_opt = {res['optimal_delay_ps']:.2f} ps")
    print(f"    - Dien tich mat (Eye Area): {res['eye_area_mv_ps']:,.1f} mV*ps (Pass Pixels: {res['total_pass_pixels']})")

    assert res["valid_eye"] is True, "Quet 2D phai tim duoc mat mo hop le"
    assert abs(res["optimal_vref_mv"] - 250.0) <= 10.0, "Vref toi uu phai nam sat 250 mV"
    assert abs(res["optimal_delay_ps"] - 62.5) <= 2.5, "Delay toi uu phai nam sat 62.5 ps"
    assert res["eye_height_mv"] >= 120.0, "Chieu cao mat do duoc phai >= 120 mV"
    assert res["eye_width_ps"] >= 65.0, "Chieu rong mat do duoc phai >= 65 ps"

    # 3. Hien thi bieu do Shmoo ASCII truc quan
    ascii_shmoo = format_ascii_shmoo(res, scanner.vref_grid, scanner.delay_grid)
    print(f"\n[3] Bieu do Shmoo Mat 2D ASCII (Dau '*' la Pass, '.' la Fail):")
    print(ascii_shmoo)

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AW.3 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_vref_dq_shmoo_plot()
