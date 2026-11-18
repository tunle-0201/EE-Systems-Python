"""
EE MENTORSHIP PROGRAM - MODULE BI (NHOM 48) - BAI 188 (MILESTONE BI.1)
================================================================================
CAM BIEN VI TRI CHUM TIA QUANG HOC QUADRANT PHOTODIODE (QPD) CHO LIEN KET LASER
================================================================================

Kien truc mach cam bien vi tri chum tia quang hoc (Optical Beam Position Sensing AFE):
1. Mang di-ot 4 goc phan tu (Quadrant Photodiode - QPD):
   - Gom 4 phan tu quang doc lap (Quadrants A, B, C, D) duoc cach ly boi khe hep (Gap w_gap ~ 10 um).
   - Bo tri khong gian:
       ┌───────┬───────┐
       │   B   │   A   │   (Nua tren: B, A)
       ├───────┼───────┤
       │   C   │   D   │   (Nua duoi: C, D)
       └───────┴───────┘
   - Chum tia laser Gaussian hoi tu len be mat QPD voi ban kinh vet sang w_spot (100 um).

2. Giai ma toa do tam chum tia (Beam Centroid Demodulation):
   - Tong cong suat quang thu nhan: P_sum = I_A + I_B + I_C + I_D
   - Sai so vi tri truc ngang (Horizontal Error):
     delta_x = [ (I_A + I_D) - (I_B + I_C) ] / P_sum
   - Sai so vi tri truc doc (Vertical Error):
     delta_y = [ (I_A + I_B) - (I_C + I_D) ] / P_sum

3. Do nhay vi tri va tuyen tinh hoa phi tuyen (Sensitivity & Linearization):
   - Trong vung lech tam nho (|x_0| << w_spot), dap ung co tinh tuyen tinh:
     delta_x = sqrt(8 / pi) * (x_0 / w_spot)
     Do nhay: S_x = d(delta_x) / dx = sqrt(8 / pi) / w_spot  (1/um)
   - Khi lech tam lon, dap ung bi bao hoa theo ham tich phan loi (Error Function erf).
     Thuat toan bu phi tuyen bac 3 giup mo rong dai do tuyen tinh len toi +/- 0.6 * w_spot.

4. Mo hinh nhieu AFE TIA va do phan giai vi tri duoi micromet (Sub-Micron Resolution):
   - Nhieu ban dan Shot Noise: i_shot = sqrt(2 * q * I_photo * B)
   - Nhieu nhiet dien tro TIA Thermal Noise: i_thermal = sqrt(4 * k_B * T * B / R_f)
   - Do phan giai vi tri RMS: sigma_pos = w_spot / ( 2 * sqrt(2) * SNR )

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Toa do lech tam chuan hoa (Normalized Centroid Displacement):
                (I_A + I_D) - (I_B + I_C)
     delta_x = ───────────────────────────
                  I_A + I_B + I_C + I_D

                (I_A + I_B) - (I_C + I_D)
     delta_y = ───────────────────────────
                  I_A + I_B + I_C + I_D

2. Toa do vi tri thuc te sau khi bu phi tuyen (Calibrated Position):
               w_spot
     x_pos  = ──────── * sqrt(pi / 8) * ( delta_x + c3 * delta_x^3 )
                 1

3. Do phan giai vi tri gioi han boi nhieu (Position Noise Equivalent):
                       w_spot
     sigma_pos = ──────────────────
                  2 * sqrt(2) * SNR
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class QPDParameters:
    """Tham so vat ly mang cam bien QPD va thiet ke TIA."""
    wavelength_m: float = 1.55e-6         # Buoc song 1550 nm
    responsivity_a_per_w: float = 0.95    # Do nhay quang InGaAs PIN Photodiode (0.95 A/W)
    spot_radius_um: float = 100.0         # Ban kinh vet sang Gaussian w_spot (100 um)
    gap_width_um: float = 10.0            # Be rong khe giua cac goc phan tu (10 um)
    r_feedback_ohm: float = 100.0e3       # Tro khang hoi tiep TIA R_f = 100 kOhm
    bandwidth_hz: float = 500.0e3         # Bang thong AFE 500 kHz (cho FSM loop)
    temperature_k: float = 300.0          # Nhiet do 300 K


class QuadrantPhotodiodeAFE:
    """
    Subsystem 1: Mo phong vat ly mang QPD Gaussian Beam Integration.
    Tich phan ham mat do cong suat Gaussian tren 4 goc phan tu A, B, C, D.
    """
    def __init__(self, params: Optional[QPDParameters] = None):
        self.p = params if params is not None else QPDParameters()
        self.k_b = 1.380649e-23           # Hang so Boltzmann
        self.q_electron = 1.60217663e-19  # Dien tich electron
        
        # He so do nhay tuyen tinh ly thuyet: S_x = sqrt(8 / pi) / w_spot (1/um)
        self.s_theoretical = math.sqrt(8.0 / math.pi) / self.p.spot_radius_um

    def _integrate_gaussian_quadrant(self, x_center_um: float, y_center_um: float, quad_name: str) -> float:
        """
        Tich phan xap xi nang luong vet sang Gaussian roi vao mot goc phan tu.
        I(x, y) = (2 * P / (pi * w^2)) * exp( -2 * ((x - x0)^2 + (y - y0)^2) / w^2 )
        """
        w = self.p.spot_radius_um
        gap = self.p.gap_width_um / 2.0
        
        # Su dung xap xi ham loi erf de tich phan chinh xac:
        # Integral[x1..x2] exp(-2 * (x - x0)^2 / w^2) dx = (w * sqrt(pi/2) / 2) * [ erf(sqrt(2)*(x2-x0)/w) - erf(sqrt(2)*(x1-x0)/w) ]
        scale = math.sqrt(2.0) / w

        if quad_name == "A":    # x > gap, y > gap
            x1, x2 = gap, 4.0 * w
            y1, y2 = gap, 4.0 * w
        elif quad_name == "B":  # x < -gap, y > gap
            x1, x2 = -4.0 * w, -gap
            y1, y2 = gap, 4.0 * w
        elif quad_name == "C":  # x < -gap, y < -gap
            x1, x2 = -4.0 * w, -gap
            y1, y2 = -4.0 * w, -gap
        elif quad_name == "D":  # x > gap, y < -gap
            x1, x2 = gap, 4.0 * w
            y1, y2 = -4.0 * w, -gap
        else:
            raise ValueError(f"Quad name {quad_name} khong hop le")

        fx = 0.5 * (math.erf((x2 - x_center_um) * scale) - math.erf((x1 - x_center_um) * scale))
        fy = 0.5 * (math.erf((y2 - y_center_um) * scale) - math.erf((y1 - y_center_um) * scale))

        return max(0.0, fx * fy)

    def measure_beam_currents(self, x_true_um: float, y_true_um: float, total_power_watts: float = 1.0e-6, add_noise: bool = True) -> Tuple[float, float, float, float]:
        """
        Mo phong dong quang dien tren 4 phan tu A, B, C, D (don vi: Amperes).
        Kem theo mo hinh nhieu Shot Noise va Thermal Noise cua AFE.
        """
        # Phan bo cong suat quang
        p_a = total_power_watts * self._integrate_gaussian_quadrant(x_true_um, y_true_um, "A")
        p_b = total_power_watts * self._integrate_gaussian_quadrant(x_true_um, y_true_um, "B")
        p_c = total_power_watts * self._integrate_gaussian_quadrant(x_true_um, y_true_um, "C")
        p_d = total_power_watts * self._integrate_gaussian_quadrant(x_true_um, y_true_um, "D")

        i_a = p_a * self.p.responsivity_a_per_w
        i_b = p_b * self.p.responsivity_a_per_w
        i_c = p_c * self.p.responsivity_a_per_w
        i_d = p_d * self.p.responsivity_a_per_w

        if add_noise:
            # Tinh tong dong nhieu RMS tren moi kenh TIA
            # 1. Thermal Noise TIA: i_th = sqrt(4 * k_B * T * B / R_f)
            i_th_rms = math.sqrt(4.0 * self.k_b * self.p.temperature_k * self.p.bandwidth_hz / self.p.r_feedback_ohm)

            def add_channel_noise(i_sig: float) -> float:
                # 2. Shot noise: i_sh = sqrt(2 * q * I * B)
                i_sh_rms = math.sqrt(2.0 * self.q_electron * max(i_sig, 1e-12) * self.p.bandwidth_hz)
                total_noise_sigma = math.sqrt(i_th_rms ** 2 + i_sh_rms ** 2)
                return max(0.0, i_sig + random.gauss(0.0, total_noise_sigma))

            i_a = add_channel_noise(i_a)
            i_b = add_channel_noise(i_b)
            i_c = add_channel_noise(i_c)
            i_d = add_channel_noise(i_d)

        return i_a, i_b, i_c, i_d


class BeamCentroidProcessor:
    """
    Subsystem 2: Bo xu ly dinh tam chùm tia quang hoc (Centroid Extraction DSP).
    Giai dieu che sai so chuan hoa va ap dung da thuc bu phi tuyen.
    """
    def __init__(self, spot_radius_um: float = 100.0, gap_width_um: float = 10.0):
        self.w_spot = spot_radius_um
        self.gap_um = gap_width_um
        # He so tuyen tinh ly thuyet khi co khe hep gap_width
        # Do khe hep lam giam I_sum o giua, do nhay thuc te tang nhe:
        # S_actual = sqrt(8/pi)/w_spot * (1 + 0.5 * (gap / w_spot))
        gap_factor = 1.0 + 0.79 * (self.gap_um / self.w_spot)
        self.s_calibrated = (math.sqrt(8.0 / math.pi) / self.w_spot) * gap_factor
        self.c1 = 1.0 / self.s_calibrated               # He so ty le vi tri
        self.c3 = 0.220                                 # He so bu phi tuyen bac 3

    def compute_normalized_errors(self, i_a: float, i_b: float, i_c: float, i_d: float) -> Tuple[float, float, float]:
        """
        Tinh toan tin hieu sai so chuan hoa delta_x, delta_y va tong dong quang dien.
        Tra ve (delta_x, delta_y, i_sum).
        """
        i_sum = i_a + i_b + i_c + i_d
        if i_sum < 1e-12:
            return 0.0, 0.0, 0.0

        delta_x = ((i_a + i_d) - (i_b + i_c)) / i_sum
        delta_y = ((i_a + i_b) - (i_c + i_d)) / i_sum
        return delta_x, delta_y, i_sum

    def estimate_position_um(self, delta_x: float, delta_y: float) -> Tuple[float, float]:
        """
        Uoc tinh toa do lech tam thuc te x_um, y_um sau khi bu phi tuyen:
        x_est = c1 * (delta_x + c3 * delta_x^3)
        y_est = c1 * (delta_y + c3 * delta_y^3)
        """
        # Kiem soat gioi han bao hoa [-1 .. +1]
        dx = max(-1.0, min(1.0, delta_x))
        dy = max(-1.0, min(1.0, delta_y))

        x_um = self.c1 * (dx + self.c3 * (dx ** 3))
        y_um = self.c1 * (dy + self.c3 * (dy ** 3))
        return x_um, y_um


def test_quadrant_photodiode_beam_sensing():
    """Chuong trinh kiem thu toan dien cam bien quang QPD."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BI (NHOM 48) - BAI 188 (MILESTONE BI.1)")
    print("CAM BIEN VI TRI CHUM TIA QUANG HOC QUADRANT PHOTODIODE (QPD) LIEN VE TINH")
    print("=" * 80)

    params = QPDParameters(spot_radius_um=100.0, gap_width_um=10.0)
    qpd_afe = QuadrantPhotodiodeAFE(params)
    dsp = BeamCentroidProcessor(spot_radius_um=100.0, gap_width_um=10.0)

    print(f"Cau hinh he thong cam bien quang QPD:")
    print(f"  * Buoc song laser               : {params.wavelength_m * 1e9:.1f} nm (Telecom 1550 nm)")
    print(f"  * Ban kinh vet sang w_spot      : {params.spot_radius_um:.1f} um")
    print(f"  * Be rong khe hep giua cac goc : {params.gap_width_um:.1f} um")
    print(f"  * Tro khang TIA                 : {params.r_feedback_ohm / 1e3:.1f} kOhm (Bang thong: 500 kHz)")
    print(f"  * Do nhay ly thuyet tuyen tinh  : {qpd_afe.s_theoretical * 1000.0:.4f} m^-1 / um ({qpd_afe.s_theoretical:.6f} / um)")
    print("-" * 80)

    # 1. Kiem thu trang thai can bang tam (Centered Beam: x = 0, y = 0)
    print("\n[1] Kiem thu chum tia hoi tu chinh tam (x_true = 0.0 um, y_true = 0.0 um):")
    ia, ib, ic, id_curr = qpd_afe.measure_beam_currents(0.0, 0.0, total_power_watts=2.0e-6, add_noise=False)
    dx, dy, isum = dsp.compute_normalized_errors(ia, ib, ic, id_curr)
    x_est, y_est = dsp.estimate_position_um(dx, dy)

    print(f"  * Dong quang 4 goc phan tu : A={ia*1e6:.3f} uA | B={ib*1e6:.3f} uA | C={ic*1e6:.3f} uA | D={id_curr*1e6:.3f} uA")
    print(f"  * Sai so chuan hoa         : delta_x = {dx:.6f} | delta_y = {dy:.6f}")
    print(f"  * Toa do uoc tinh          : x_est = {x_est:.4f} um | y_est = {y_est:.4f} um")

    assert abs(dx) < 1e-4 and abs(dy) < 1e-4, "Loi: Chum tia chinh tam nhung sai so khong bang 0!"
    print("  -> Ket luan: 4 goc phan tu can bang hoan hao khi chum tia chinh tam (PASS)!")

    # 2. Kiem thu do nhay tuyen tinh tai cac buoc lech nho (Linear Sensitivity Calibration)
    print("\n[2] Kiem thu do nhay tuyen tinh tai cac do lech vi mo (x = 5.0 um, y = -8.0 um):")
    ia, ib, ic, id_curr = qpd_afe.measure_beam_currents(5.0, -8.0, total_power_watts=2.0e-6, add_noise=False)
    dx, dy, _ = dsp.compute_normalized_errors(ia, ib, ic, id_curr)
    x_est, y_est = dsp.estimate_position_um(dx, dy)

    measured_sx = dx / 5.0
    err_x = abs(x_est - 5.0)
    err_y = abs(y_est - (-8.0))

    print(f"  * Do lech thuc te              : x = +5.00 um | y = -8.00 um")
    print(f"  * Do lech uoc tinh DSP         : x = +{x_est:.2f} um | y = {y_est:.2f} um")
    print(f"  * Sai so uoc tinh              : err_x = {err_x:.3f} um | err_y = {err_y:.3f} um")
    print(f"  * Do nhay thuc do S_x          : {measured_sx:.6f} / um (Ly thuyet: {qpd_afe.s_theoretical:.6f} / um)")

    assert err_x < 0.25 and err_y < 0.25, "Loi: Sai so uoc tinh vi tri tuyen tinh vuot nguong!"
    print("  -> Ket luan: Do nhay vi tri dat do chinh xac sub-micron (< 0.25 um error) (PASS)!")

    # 3. Kiem thu quet quy dao 2D hinh xoan oc va bu phi tuyen bac 3
    print("\n[3] Kiem thu quet quy dao 2D bien do lon (+/- 40 um) kem bu phi tuyen:")
    test_trajectory = [
        (10.0, 10.0), (-20.0, 15.0), (-35.0, -25.0), (30.0, -30.0), (0.0, 40.0)
    ]
    max_err_um = 0.0
    for xt, yt in test_trajectory:
        ia, ib, ic, id_curr = qpd_afe.measure_beam_currents(xt, yt, total_power_watts=2.0e-6, add_noise=False)
        dx, dy, _ = dsp.compute_normalized_errors(ia, ib, ic, id_curr)
        xe, ye = dsp.estimate_position_um(dx, dy)
        pos_err = math.sqrt((xe - xt)**2 + (ye - yt)**2)
        max_err_um = max(max_err_um, pos_err)
        print(f"  * Thuc te: ({xt:+5.1f}, {yt:+5.1f}) um | Uoc tinh: ({xe:+5.1f}, {ye:+5.1f}) um | Sai so: {pos_err:4.2f} um")

    assert max_err_um < 3.0, f"Loi: Sai so phi tuyen bien do lon vuot nguong 3 um: {max_err_um} um"
    print(f"  -> Ket luan: Thuat toan bu phi tuyen bac 3 giu sai so < {max_err_um:.2f} um tren toan dai quet 80 um (PASS)!")

    # 4. Kiem thu do phan giai vi tri duoi nhieu thuc te (Noise Equivalent Position Resolution)
    print("\n[4] Kiem thu do phan giai vi tri khi co nhieu Shot Noise va TIA Thermal Noise:")
    random.seed(42)
    noise_runs = 500
    estimated_xs = []
    for _ in range(noise_runs):
        ia, ib, ic, id_curr = qpd_afe.measure_beam_currents(12.0, -6.0, total_power_watts=1.5e-6, add_noise=True)
        dx, dy, _ = dsp.compute_normalized_errors(ia, ib, ic, id_curr)
        xe, ye = dsp.estimate_position_um(dx, dy)
        estimated_xs.append(xe)

    mean_x = sum(estimated_xs) / noise_runs
    sigma_x_um = math.sqrt(sum((x - mean_x)**2 for x in estimated_xs) / noise_runs)

    print(f"  * Toa do thuc te               : x = 12.000 um")
    print(f"  * Toa do trung binh sau nhieu  : x = {mean_x:.3f} um")
    print(f"  * Do rung vi tri do nhieu RMS  : sigma_pos = {sigma_x_um:.3f} um ({sigma_x_um * 1000.0:.1f} nanomet)")

    assert sigma_x_um < 0.20, f"Loi: Rung vi tri do nhieu qua lon: {sigma_x_um} um"
    print("  -> Ket luan: Do phan giai vi tri cua QPD dat cap do sub-micron (nanomet resolution) (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 188: CAM BIEN QUANG QPD HOAN TAT KIEM THU 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_quadrant_photodiode_beam_sensing()
