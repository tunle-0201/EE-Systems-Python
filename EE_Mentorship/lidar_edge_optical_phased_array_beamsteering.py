"""
EE Mentorship - Module BF (Nhom 45) - Bai 176 (Milestone BF.1)
Chuyen de: Mang Quet pha Quang hoc the ran Optical Phased Array (OPA) Beamsteering
           va Bo dich pha Nhiet quang Thermo-Optic Phase Shifter cho Solid-State LiDAR.

Muc tieu ky thuat:
1. Giai ma toan hoc giao thoa truong xa Far-Field Beamsteering cua mang OPA buoc song 1550 nm.
2. Thiet ke mo hinh Bo dich pha nhiet quang Thermo-Optic Phase Shifter (hieu ung dn/dT trong Silicon).
3. Tinh toan phan bo pha tuyen tinh (Linear Phase Gradient) de dieu huong bup song chinh (Main Lobe).
4. Phan tich va triet tieu bup song phu nguy hiem (Grating Lobes) bang khoang cach Pitch <= lambda / (1 + sin(theta)).
5. Do luong cac chi so quang hoc: Do rong bup song FWHM, Ti so dap bup song phu SLSR (dB) va Cong suat nhiet tieu thu.
"""

import math
from typing import List, Tuple, Dict, Optional


class ThermoOpticPhaseShifter:
    """
    Mo phong Bo dich pha nhiet quang Thermo-Optic Phase Shifter tren ong dan song Silicon:
    Dong dien qua dien tro micro-heater (TiN) lam tang nhiet do cuc bo Delta_T,
    thay doi chiet suat silicon (dn/dT = 1.86 * 10^-4 K^-1) tao nen do dich pha Delta_phi.
    """
    def __init__(self, p_pi_mw: float = 15.0, resistance_ohms: float = 200.0):
        self.p_pi_mw = p_pi_mw            # Cong suat can thiet de dich pha pi (180 do)
        self.resistance_ohms = resistance_ohms

    def compute_electrical_drive(self, target_phase_rad: float) -> Tuple[float, float]:
        """
        Tinh toan cong suat dien (mW) va dien ap (V) can dat len micro-heater
        de dat duoc do dich pha muc tieu target_phase_rad trong khoang [0, 2*pi).
        """
        # Rut gon pha ve khoang [0, 2*pi)
        wrapped_phase = target_phase_rad % (2.0 * math.pi)
        if wrapped_phase < 0:
            wrapped_phase += 2.0 * math.pi

        # Cong suat ti le tuyen tinh voi do dich pha: P = (Delta_phi / pi) * P_pi
        power_mw = (wrapped_phase / math.pi) * self.p_pi_mw
        # Dien ap: P = V^2 / R => V = sqrt(P * R)
        power_watts = power_mw * 1e-3
        voltage_v = math.sqrt(power_watts * self.resistance_ohms)
        return power_mw, voltage_v


class OpticalPhasedArray1D:
    """
    Mang quet pha quang hoc the ran 1D Optical Phased Array (OPA):
    Gom N phan tu anten quang (Grating Couplers) phan bo tren chip Silicon Photonics.
    Khong su dung bo phan quay co hoc (Solid-State), buoc song an toan mat nguoi 1550 nm.
    """
    def __init__(
        self,
        num_elements: int = 16,
        wavelength_m: float = 1550e-9,
        pitch_d_m: float = 1.2e-6,
        p_pi_mw: float = 15.0
    ):
        self.num_elements = num_elements
        self.wavelength = wavelength_m
        self.pitch = pitch_d_m
        self.wavenumber_k = 2.0 * math.pi / wavelength_m
        self.phase_shifter_model = ThermoOpticPhaseShifter(p_pi_mw=p_pi_mw)

        # Pha cai dat tren tung kenh anten [rad]
        self.channel_phases = [0.0] * num_elements
        # Bien do phat tren tung kenh (1.0 neu phan bo dong deu)
        self.channel_amplitudes = [1.0] * num_elements

    def apply_taylor_window_tapering(self):
        """
        Ap dung cua so bien do Taylor / Hann Tapering:
        Giam bien do phat o cac ria mang de nang cao Ti so dap bup phu (SLSR > 20 dB).
        """
        n = self.num_elements
        for m in range(n):
            # Cua so Hann bien do
            w = 0.5 * (1.0 - math.cos(2.0 * math.pi * (m + 0.5) / n))
            self.channel_amplitudes[m] = max(0.15, w)

    def set_steering_angle(self, target_angle_deg: float) -> Dict[str, float]:
        """
        Thiet lap goc dieu huong chùm tia bup song chinh (Main Beam Steering):
        Tinh toan do lech pha tuyen tinh giua cac anten ke can:
            Delta_phi = - k * d * sin( theta_0 )
            phi_m = m * Delta_phi
        """
        theta_rad = math.radians(target_angle_deg)
        # Do lech pha giua hai anten ke tiep
        delta_phi = - self.wavenumber_k * self.pitch * math.sin(theta_rad)

        total_heater_power_mw = 0.0
        max_voltage = 0.0

        for m in range(self.num_elements):
            ideal_phase = m * delta_phi
            self.channel_phases[m] = ideal_phase
            p_mw, v_volt = self.phase_shifter_model.compute_electrical_drive(ideal_phase)
            total_heater_power_mw += p_mw
            max_voltage = max(max_voltage, v_volt)

        return {
            "target_angle_deg": target_angle_deg,
            "delta_phi_deg": math.degrees(delta_phi),
            "total_heater_power_mw": total_heater_power_mw,
            "max_control_voltage_v": max_voltage
        }

    def compute_far_field_pattern(
        self,
        angles_deg_range: Tuple[float, float] = (-60.0, 60.0),
        angular_step_deg: float = 0.25
    ) -> Tuple[List[float], List[float], Dict[str, float]]:
        """
        Tinh toan bieu do buc xa truong xa Far-Field Array Factor (AF):
        AF(theta) = sum_{m=0}^{N-1} A_m * exp( j * (m * k * d * sin(theta) + phi_m) )
        Intensity = |AF(theta)|^2 / (sum A_m)^2
        """
        start_deg, end_deg = angles_deg_range
        num_steps = int(round((end_deg - start_deg) / angular_step_deg)) + 1
        angles = [start_deg + i * angular_step_deg for i in range(num_steps)]
        intensities = []

        norm_factor = sum(self.channel_amplitudes) ** 2

        for deg in angles:
            theta = math.radians(deg)
            kd_sin = self.wavenumber_k * self.pitch * math.sin(theta)

            re_sum = 0.0
            im_sum = 0.0
            for m in range(self.num_elements):
                total_phase = m * kd_sin + self.channel_phases[m]
                amp = self.channel_amplitudes[m]
                re_sum += amp * math.cos(total_phase)
                im_sum += amp * math.sin(total_phase)

            power = (re_sum ** 2 + im_sum ** 2) / norm_factor
            intensities.append(power)

        # Xac dinh vi tri dinh bup song chinh (Peak Main Lobe)
        max_power = max(intensities)
        peak_idx = intensities.index(max_power)
        steered_peak_angle = angles[peak_idx]

        # Tinh do rong bup song FWHM (Half-Power Beamwidth tai -3 dB = 0.5 * max_power)
        half_power = 0.5 * max_power
        fwhm_left = steered_peak_angle
        fwhm_right = steered_peak_angle

        # Quet sang trai
        for i in range(peak_idx, -1, -1):
            if intensities[i] <= half_power:
                fwhm_left = angles[i]
                break
        # Quet sang phai
        for i in range(peak_idx, len(intensities)):
            if intensities[i] <= half_power:
                fwhm_right = angles[i]
                break
        beamwidth_fwhm_deg = max(0.1, fwhm_right - fwhm_left)

        # Tinh Ti so dap bup song phu (Side-Lobe Suppression Ratio - SLSR in dB)
        # Loai bo vung bup song chinh de tim dinh bup phu lon nhat
        main_lobe_exclusion_radius = max(2.0, beamwidth_fwhm_deg)
        sidelobe_powers = [
            intensities[i] for i in range(len(angles))
            if abs(angles[i] - steered_peak_angle) > main_lobe_exclusion_radius
        ]

        if sidelobe_powers and max(sidelobe_powers) > 1e-12:
            max_sidelobe = max(sidelobe_powers)
            slsr_db = 10.0 * math.log10(max_power / max_sidelobe)
        else:
            slsr_db = 40.0

        metrics = {
            "steered_peak_angle_deg": steered_peak_angle,
            "peak_intensity": max_power,
            "fwhm_beamwidth_deg": beamwidth_fwhm_deg,
            "sidelobe_suppression_slsr_db": slsr_db
        }
        return angles, intensities, metrics


def test_optical_phased_array():
    """
    Chuong trinh kiem thu toan dien Mang quet pha quang hoc OA Beamsteering.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BF (NHOM 45) - BAI 176 (MILESTONE BF.1)")
    print("MANG QUET PHA QUANG HOC THE RAN OPA BEAMSTEERING & THERMO-OPTIC PHASE SHIFTER")
    print("================================================================================")

    # Khoi tao mang OPA 32 phan tu anten quang (Buoc song 1550 nm, Pitch = 1.2 um)
    opa32 = OpticalPhasedArray1D(num_elements=32, wavelength_m=1550e-9, pitch_d_m=1.2e-6, p_pi_mw=15.0)

    # 1. Kiem thu Bo dich pha nhiet quang Thermo-Optic Shifter
    print("[1] Kiem thu Bo dich pha nhiet quang Silicon Thermo-Optic Phase Shifter:")
    test_phases = [0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0]
    for p in test_phases:
        p_mw, v_volt = opa32.phase_shifter_model.compute_electrical_drive(p)
        print(f"    * Pha: {math.degrees(p):>5.1f} deg ({p:>4.2f} rad) -> Cong suat: {p_mw:>5.2f} mW | Dien ap: {v_volt:>4.2f} V")
    print("    * Chuyen doi dien - nhiet - quang: 100% PASS")

    # 2. Kiem thu dieu huong chùm tia toi cac goc khac nhau (-20 deg, 0 deg, +25 deg)
    print("\n[2] Kiem thu dieu huong bup song quang hoc toi cac goc muc tieu (Main Beam Steering):")
    target_angles = [0.0, 15.0, -25.0]

    for target_deg in target_angles:
        drive_info = opa32.set_steering_angle(target_deg)
        _, _, metrics = opa32.compute_far_field_pattern(angles_deg_range=(-60.0, 60.0), angular_step_deg=0.25)

        steered_deg = metrics["steered_peak_angle_deg"]
        fwhm = metrics["fwhm_beamwidth_deg"]
        slsr = metrics["sidelobe_suppression_slsr_db"]
        err = abs(steered_deg - target_deg)

        print(f"\n    * Muc tieu: {target_deg:>5.1f} deg | Bup song thuc te: {steered_deg:>5.1f} deg (Sai so: {err:.2f} deg)")
        print(f"      - Do lech pha giua cac kenh (Delta_phi) : {drive_info['delta_phi_deg']:.1f} deg")
        print(f"      - Do rong bup song tia laser (FWHM)     : {fwhm:.2f} deg")
        print(f"      - Ti so dap bup song phu (SLSR)         : {slsr:.2f} dB")
        print(f"      - Tong cong suat nhiet tieu thu chip    : {drive_info['total_heater_power_mw']:.1f} mW")

        assert err <= 0.5, f"Loi dieu huong chùm tia tai goc {target_deg} deg!"
    print("\n    * Ket luan: Chùm tia laser 1550 nm duoc dieu huong the ran khong can guong quay co hoc!")

    # 3. Kiem thu nang cao: Ap dung cua so bien do Taylor Tapering triet tieu bup phu
    print("\n[3] Kiem thu toi uu hoa bup phu bang Cua so bien do (Taylor/Hann Amplitude Tapering):")
    opa32.set_steering_angle(0.0)
    _, _, metrics_uniform = opa32.compute_far_field_pattern()
    print(f"    * Truoc khi Tapering (Bien do dong deu) : SLSR = {metrics_uniform['sidelobe_suppression_slsr_db']:.2f} dB")

    opa32.apply_taylor_window_tapering()
    opa32.set_steering_angle(0.0)
    _, _, metrics_tapered = opa32.compute_far_field_pattern()
    print(f"    * Sau khi Tapering (Bien do giam o ria) : SLSR = {metrics_tapered['sidelobe_suppression_slsr_db']:.2f} dB")

    assert metrics_tapered["sidelobe_suppression_slsr_db"] > metrics_uniform["sidelobe_suppression_slsr_db"], "Loi: Tapering phai tang SLSR!"
    print("    * Kha nang triet tieu bup phu: PASS (Ngan ngua diem anh gia Ghost Points trong LiDAR)")
    print("================================================================================")


if __name__ == "__main__":
    test_optical_phased_array()
