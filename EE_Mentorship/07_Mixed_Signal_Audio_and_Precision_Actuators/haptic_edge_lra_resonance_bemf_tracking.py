"""
EE MENTORSHIP PROGRAM - MODULE BN (NHOM 53) - BAI 208 (MILESTONE BN.1)
================================================================================
MO HINH CO-DIEN TU BO RUNG TUYEN TINH LRA (LINEAR RESONANT ACTUATOR) &
THUAT TOAN DO TAN SO CONG HUONG TU DONG QUA BACK-EMF (AUTO-RESONANCE TRACKING)
CHO APPLE TAPTIC ENGINE & DIEU KHIEN XUC GIAC HAPTICS
================================================================================

Nguyen ly vat ly Co-Dien tu & Toan hoc cot loi:
1. He phuong trinh vi phan cap 2 ghep doi Dien - Co cua LRA:
   - Mach dien cuon day:   V_drive(t) = I * R_e + L_e * dI/dt + B_l * v(t)
     Trong do E_bemf = B_l * v(t) la suc dien dong cam ung nguoc ty le voi van toc!
   - Co hoc Lo xo - Khoi luong:  M * dv/dt = B_l * I(t) - B_m * v(t) - K_s * x(t)
                                 dx/dt = v(t)

2. Nhay cam cua dinh cong huong Q cao (Sharp Resonance f_0):
   - Tan so cong huong tu nhien: f_0 = (1 / 2*pi) * sqrt(K_s / M) (~170 Hz).
   - He so pham chat Q_tot ~ 11.6: Chi can lech tan 10% (xuong 153 Hz do tay nguoi
     cam chat hoac nhiet do nong len lam mem lo xo), bien do gia toc G-force bi
     sut giam hon 60% neu chip driver cu phat cung o 170 Hz!

3. Giai phap Auto-Resonance Tracking trong chip Apple / TI DRV2605:
   - Ngat cau H sang trang thai tro khang cao Hi-Z trong ngan khoang (~0.8 ms) quanh
     diem qua khong dong dien (khi I = 0 thi mat sut ap I*R_e = 0):
       V_terminal(Hi-Z) = B_l * v(t)  (Do thuan Back-EMF tinh khiet!)
   - Đo khoang thoi gian giua hai lan Back-EMF cat diem 0 (Zero-Crossing) de tinh
     chu ky dao dong tu nhien thuc te T_0 = 2 * delta_t_zc -> Cap nhat NCO f_drive!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Tan so cong huong & Gia toc dinh (G-force):
               1          K_s                    |M * dv/dt|
     f_0 = ──────── * sqrt(───),     a_G_peak = ─────────────  (1 G = 9.81 m/s^2)
             2 * pi         M                      M * 9.81

2. Do lech pha Back-EMF / Zero-Cross Tracking:
     f_meas = 1 / (2 * (t_zc_curr - t_zc_prev)) -> f_nco += K_track * (f_meas - f_nco)
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


G_ACCEL = 9.80665


@dataclass
class LRAActuatorParams:
    """Thong so vat ly Linear Resonant Actuator (dang Apple Taptic Engine)."""
    mass_kg: float = 2.5e-3          # Khoi luong con lac rung: 2.5 gram
    k_spring_n_m: float = 2852.32    # Do cung lo xo tai 25C: f0 = 170.00 Hz
    b_mech_ns_m: float = 0.18        # He so can co hoc (Q_m ~ 14.8)
    b_l_force_n_a: float = 0.14      # Hang so luc Lorentz B*l (N/A)
    r_coil_ohm: float = 8.0          # Dien tro cuon day: 8.0 Ohm
    l_coil_h: float = 0.20e-3        # Dien cam cuon day: 0.20 mH
    v_peak_v: float = 3.0            # Dien ap cau H: 3.0 V -> Peak ~ 2.9 G

    @property
    def natural_freq_hz(self) -> float:
        return math.sqrt(self.k_spring_n_m / self.mass_kg) / (2.0 * math.pi)


class LRAElectromechanicalPlant:
    """Mo phong RK4 he phuong trinh dien-co LRA (ho tro ngat cau H sang Hi-Z do Back-EMF)."""

    def __init__(self, params: LRAActuatorParams):
        self.p = params
        self.x = 0.0
        self.v = 0.0
        self.i = 0.0

    def reset(self) -> None:
        self.x = 0.0
        self.v = 0.0
        self.i = 0.0

    def _derivs(self, x: float, v: float, i: float, v_drive: float, hi_z: bool) -> Tuple[float, float, float]:
        dx = v
        dv = (self.p.b_l_force_n_a * i - self.p.b_mech_ns_m * v - self.p.k_spring_n_m * x) / self.p.mass_kg
        if hi_z:
            # Khi ngat cau H sang Hi-Z qua diode chan xung ngan, dong cuon cam tat nhanh ve 0
            di = -i / 3.0e-5
        else:
            di = (v_drive - self.p.r_coil_ohm * i - self.p.b_l_force_n_a * v) / self.p.l_coil_h
        return dx, dv, di

    def step_rk4(self, dt: float, v_drive: float, hi_z: bool = False) -> Tuple[float, float, float]:
        """Tich phan Runge-Kutta bac 4 (tra ve x, v, v_terminal_sense)."""
        k1 = self._derivs(self.x, self.v, self.i, v_drive, hi_z)
        k2 = self._derivs(
            self.x + 0.5 * dt * k1[0], self.v + 0.5 * dt * k1[1], self.i + 0.5 * dt * k1[2], v_drive, hi_z
        )
        k3 = self._derivs(
            self.x + 0.5 * dt * k2[0], self.v + 0.5 * dt * k2[1], self.i + 0.5 * dt * k2[2], v_drive, hi_z
        )
        k4 = self._derivs(
            self.x + dt * k3[0], self.v + dt * k3[1], self.i + dt * k3[2], v_drive, hi_z
        )

        self.x += (dt / 6.0) * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
        self.v += (dt / 6.0) * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
        self.i += (dt / 6.0) * (k1[2] + 2.0 * k2[2] + 2.0 * k3[2] + k4[2])

        # Gia toc tuc thoi theo don vi G
        accel_ms2 = (self.p.b_l_force_n_a * self.i - self.p.b_mech_ns_m * self.v - self.p.k_spring_n_m * self.x) / self.p.mass_kg
        # Khi Hi-Z, dien ap do duoc tren 2 cuc cuon day chinh la suc dien dong Back-EMF = B*l*v!
        v_sense = (self.p.b_l_force_n_a * self.v) if hi_z else v_drive
        return accel_ms2 / G_ACCEL, self.v, v_sense


class LRADriverController:
    """Bo dieu khien LRA ho tro Open-Loop Fixed Frequency vs Back-EMF Auto-Resonance Tracking."""

    @staticmethod
    def run_open_loop(plant: LRAElectromechanicalPlant, drive_freq_hz: float, duration_s: float = 0.14) -> Dict[str, float]:
        plant.reset()
        dt = 20.0e-6
        steps = int(duration_s / dt)
        peak_g = 0.0
        steady_peaks: List[float] = []

        for k in range(steps):
            t = k * dt
            # Song vuong cau H (+/- V_peak)
            v_drv = plant.p.v_peak_v if math.sin(2.0 * math.pi * drive_freq_hz * t) >= 0.0 else -plant.p.v_peak_v
            a_g, _, _ = plant.step_rk4(dt, v_drv, hi_z=False)
            if t >= 0.08:
                steady_peaks.append(abs(a_g))
            peak_g = max(peak_g, abs(a_g))

        return {"steady_peak_g": max(steady_peaks), "drive_freq_hz": drive_freq_hz}

    @staticmethod
    def run_auto_resonance_bemf(
        plant: LRAElectromechanicalPlant, init_guess_hz: float = 170.0, duration_s: float = 0.14
    ) -> Dict[str, float]:
        """
        Thuat toan Auto-Resonance PLL qua Sai lech Pha Zero-Crossing Back-EMF:
        - Tai tan so cong huong f_drive == f_0, van toc v(t) va Back-EMF dong pha voi dien ap lai.
        - Neu f_drive > f_0: Back-EMF bi tre pha (cat 0 muon -> phase_err > 0) -> giam f_nco.
        - Neu f_drive < f_0: Back-EMF vuot pha (cat 0 som -> phase_err < 0) -> tang f_nco.
        Mo cua so Hi-Z ngan (0.5 ms) tai thoi diem Back-EMF cat 0 de khu sut ap I*R_e.
        """
        plant.reset()
        dt = 20.0e-6
        steps = int(duration_s / dt)
        nco_freq_hz = init_guess_hz
        phase = 0.0
        freq_int = 0.0

        prev_v = 0.0
        hiz_timer = 0
        steady_peaks: List[float] = []

        for k in range(steps):
            t = k * dt
            # Khi van toc gan cat 0 (tai nguong Hi-Z Window ~ 0.4 ms), ngat cau H de doc thuan Back-EMF
            if hiz_timer > 0:
                hiz_timer -= 1
            elif abs(plant.v) < 0.025 and k > 50 and (k % 8 == 0):
                hiz_timer = 15  # 300 us do Back-EMF

            in_hiz = hiz_timer > 0
            sign_drive = 1.0 if (phase % (2.0 * math.pi)) < math.pi else -1.0
            v_drv = sign_drive * plant.p.v_peak_v

            a_g, cur_v, _ = plant.step_rk4(dt, v_drv, hi_z=in_hiz)

            # Phat hien diem qua khong cua Back-EMF (E_bemf = B_l * v) va do do lech pha so voi NCO
            if k > 25 and ((prev_v < 0.0 <= cur_v) or (prev_v > 0.0 >= cur_v)):
                # Vi tri ly tuong: 0 rad cho suon len (cur_v > 0), pi rad cho suon xuong (cur_v < 0)
                target_ph = 0.0 if cur_v >= 0.0 else math.pi
                ph_mod = phase % (2.0 * math.pi)
                ph_err = ph_mod - target_ph
                if ph_err > math.pi:
                    ph_err -= 2.0 * math.pi
                elif ph_err < -math.pi:
                    ph_err += 2.0 * math.pi

                # Bo loc PI khoa tan so NCO vao dung f_0 thuc te (giu dai [110..230 Hz])
                freq_int += -12.0 * ph_err
                nco_freq_hz = max(110.0, min(230.0, init_guess_hz + freq_int - 18.0 * ph_err))

            prev_v = cur_v
            phase += 2.0 * math.pi * nco_freq_hz * dt
            if t >= 0.09:
                steady_peaks.append(abs(a_g))

        return {
            "tracked_freq_hz": nco_freq_hz,
            "steady_peak_g": max(steady_peaks),
        }


def test_lra_resonance_bemf_tracking():
    """Chuong trinh kiem thu dac tuyen cong huong LRA & Auto-Resonance Back-EMF."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BN (NHOM 53) - BAI 208 (MILESTONE BN.1)")
    print("MO HINH CO-DIEN TU LRA & DO TAN SO CONG HUONG TU DONG BACK-EMF")
    print("=" * 80)

    # 1. Quet dac tuyen cong huong cua LRA danh dinh f0 = 170.0 Hz
    nom_params = LRAActuatorParams()
    plant_nom = LRAElectromechanicalPlant(nom_params)
    print(f"\n[1] Kiem thu do nhon dinh cong huong LRA danh dinh f_0 = {nom_params.natural_freq_hz:.2f} Hz:")

    res_at_170 = LRADriverController.run_open_loop(plant_nom, drive_freq_hz=170.0)
    res_at_153 = LRADriverController.run_open_loop(plant_nom, drive_freq_hz=153.0)
    res_at_187 = LRADriverController.run_open_loop(plant_nom, drive_freq_hz=187.0)
    drop_pct = (1.0 - res_at_153["steady_peak_g"] / res_at_170["steady_peak_g"]) * 100.0

    print(f"  * Dung tan 170 Hz : Gia toc dinh = {res_at_170['steady_peak_g']:5.2f} G (Peak Resonance)")
    print(f"  * Lech -10% 153 Hz: Gia toc dinh = {res_at_153['steady_peak_g']:5.2f} G (Sut giam -{drop_pct:.1f}%!)")
    print(f"  * Lech +10% 187 Hz: Gia toc dinh = {res_at_187['steady_peak_g']:5.2f} G")

    assert res_at_170["steady_peak_g"] > 2.2 and drop_pct > 55.0
    print("  -> Ket luan: Lech tan chi 10% lam sut hon 55% luc rung LRA (PASS)!")

    # 2. Mo phong LRA bi troi tan so cong huong thuc te xuong 153.0 Hz (lo xo mem do nhiet/tai cam tay)
    print("\n[2] So sanh Open-Loop cung 170 Hz vs Back-EMF Auto-Resonance khi f_0 troi ve 153.0 Hz:")
    shifted_params = LRAActuatorParams(k_spring_n_m=2852.32 * ((153.0 / 170.0) ** 2))
    plant_shifted = LRAElectromechanicalPlant(shifted_params)
    true_f0_shifted = shifted_params.natural_freq_hz

    ref_max = LRADriverController.run_open_loop(plant_shifted, drive_freq_hz=true_f0_shifted)
    open_stuck_170 = LRADriverController.run_open_loop(plant_shifted, drive_freq_hz=170.0)
    auto_tracked = LRADriverController.run_auto_resonance_bemf(plant_shifted, init_guess_hz=170.0)

    freq_err_hz = abs(auto_tracked["tracked_freq_hz"] - true_f0_shifted)
    recovery_pct = (auto_tracked["steady_peak_g"] / ref_max["steady_peak_g"]) * 100.0

    print(f"  * Tan so thuc te sau troi      : {true_f0_shifted:6.2f} Hz")
    print(f"  * Open-Loop cung 170 Hz        : Gia toc chi dat {open_stuck_170['steady_peak_g']:5.2f} G (Mat luc nang!)")
    print(
        f"  * Auto-Resonance Back-EMF      : Khoa tai {auto_tracked['tracked_freq_hz']:6.2f} Hz "
        f"(Sai {freq_err_hz:.2f} Hz) | Dat {auto_tracked['steady_peak_g']:5.2f} G ({recovery_pct:.1f}% max!)"
    )

    assert open_stuck_170["steady_peak_g"] < ref_max["steady_peak_g"] * 0.50
    assert freq_err_hz < 1.5 and recovery_pct > 90.0
    print("  -> Ket luan: Do Back-EMF khoa chinh xac f_0 moi & phuc hoi > 90% luc rung (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 208: LRA ELECTROMECHANICAL & BEMF TRACKING 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_lra_resonance_bemf_tracking()
