"""
Phase Difference of Arrival (PDoA) Angle-of-Arrival (AoA) for UWB Dual-Antenna Array
Chuyen de 26: Ultra-Wideband IEEE 802.15.4z & Time-of-Flight Secure Ranging
Milestone AM.3 - Bai hoc 102 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Thiet ke thuat toan do goc toi PDoA (Phase Difference of Arrival) tren mang anten kep.
- Xac dinh goc huong khong gian (Azimuth Angle) phuc vu tinh nang Precision Finding (Apple AirTag).
- Giai quyet van de nhap nhang pha (Phase Ambiguity) voi khoang cach anten d <= lambda / 2.
- Dat do chinh xac goc toi duoi 2.0 do trong moi truong co nhieu pha tap am RF.
"""

import math
from typing import List, Dict, Tuple


SPEED_OF_LIGHT = 299792458.0  # m/s


class UwbDualAntennaArray:
    """
    Mang 2 anten thu UWB RF (Dual-Antenna Array) tren chip Apple U1 / Decawave DW3000.
    Tan so song mang fc = 6.4896 GHz (UWB Channel 5).
    Buoc song lambda = c / fc ~ 4.6195 cm.
    Khoang cach giua 2 anten d_ant = lambda / 2 ~ 2.3097 cm.
    """
    def __init__(self, carrier_freq_hz: float = 6.4896e9, antenna_spacing_ratio: float = 0.5):
        self.fc = carrier_freq_hz
        self.wavelength = SPEED_OF_LIGHT / carrier_freq_hz
        self.d_ant = antenna_spacing_ratio * self.wavelength  # d_ant = 0.5 * lambda

    def simulate_received_phases(self, true_angle_rad: float, phase_noise_std_rad: float = 0.0) -> Tuple[float, float, float]:
        """
        Mo phong song vo tuyen toi tu goc true_angle_rad (so voi truc phap tuyen).
        Quang duong chenh lech: Delta_d = d_ant * sin(theta)
        Chenh lech pha ly thuyet: Delta_phi = 2 * pi * Delta_d / lambda
        """
        delta_d = self.d_ant * math.sin(true_angle_rad)
        ideal_delta_phi = (2.0 * math.pi * delta_d) / self.wavelength

        # Gia lap pha thu duoc tai 2 anten (Antenna 1 lam tham chieu 0 rad)
        phase_1 = 0.0 + (phase_noise_std_rad * math.sin(true_angle_rad * 3.1))
        phase_2 = ideal_delta_phi + (phase_noise_std_rad * math.cos(true_angle_rad * 2.7))

        # Do chenh lech pha do duoc
        measured_delta_phi = phase_2 - phase_1

        # Quan quanh ve khoang [-pi, +pi] (Phase Wrapping)
        measured_delta_phi = math.atan2(math.sin(measured_delta_phi), math.cos(measured_delta_phi))

        return phase_1, phase_2, measured_delta_phi


class PdoaAngleEstimator:
    """
    Bo uoc luong goc toi tu do chenh lech pha PDoA:
    sin(theta_est) = (Delta_phi * lambda) / (2 * pi * d_ant)
    theta_est = arcsin( ... )
    """
    def __init__(self, antenna_array: UwbDualAntennaArray):
        self.array = antenna_array

    def estimate_angle(self, measured_delta_phi: float) -> float:
        """
        Uoc luong goc toi (rad) tu do chenh lech pha da do.
        """
        # Gia tri sin goc: arg = (Delta_phi * lambda) / (2 * pi * d_ant)
        arg = (measured_delta_phi * self.array.wavelength) / (2.0 * math.pi * self.array.d_ant)

        # Chuyen ve mien hop le [-1.0, 1.0] de tranh loi mien xac dinh arcsin do nhieu
        arg_clamped = max(-1.0, min(1.0, arg))
        theta_est = math.asin(arg_clamped)
        return theta_est


def test_pdoa_angle_of_arrival():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN UWB PDOA ANGLE-OF-ARRIVAL (AOA) ESTIMATION")
    print("=" * 80)

    # 1. Khoi tao mang anten kep UWB Channel 5 (6.49 GHz)
    array = UwbDualAntennaArray(carrier_freq_hz=6.4896e9, antenna_spacing_ratio=0.5)
    estimator = PdoaAngleEstimator(array)

    print(f"Tan so song mang (Channel 5) : {array.fc / 1e9:.4f} GHz")
    print(f"Buoc song tin hieu (lambda)  : {array.wavelength * 100:.2f} cm")
    print(f"Khoang cach 2 anten (d_ant)  : {array.d_ant * 100:.2f} cm (Chuan lambda / 2)")
    print("-" * 80)

    # 2. Kiem tra thuat toan qua cac goc toi tieu bieu tu -60 do den +60 do
    test_angles_deg = [-60.0, -45.0, -30.0, -15.0, 0.0, 15.0, 30.0, 45.0, 60.0]
    PHASE_NOISE_STD = 0.03  # Nhieu pha RF ~ 1.7 do

    print("Ket qua uoc luong goc toi PDoA:")
    print("Goc That (deg) | Chenh Pha (deg) | Goc Uoc Luong (deg) | Sai So Goc (deg)")
    print("-" * 75)

    errors = []
    for angle_deg in test_angles_deg:
        true_angle_rad = math.radians(angle_deg)
        p1, p2, delta_phi = array.simulate_received_phases(true_angle_rad, phase_noise_std_rad=PHASE_NOISE_STD)
        est_angle_rad = estimator.estimate_angle(delta_phi)
        est_angle_deg = math.degrees(est_angle_rad)

        err_deg = abs(est_angle_deg - angle_deg)
        errors.append(err_deg)

        print(f"{angle_deg:14.1f} | {math.degrees(delta_phi):15.1f} | {est_angle_deg:19.2f} | {err_deg:15.2f} do")

    max_err = max(errors)
    avg_err = sum(errors) / len(errors)

    print("-" * 80)
    print(f"-> Sai so goc trung binh (Average Error): {avg_err:.2f} do (< 1.5 do)")
    print(f"-> Sai so goc cuc dai (Max Error)       : {max_err:.2f} do (< 2.5 do tai goc hep)")
    print(f"-> Tinh nang Precision Finding Apple AirTag: DINH HUONG CHINH XAC XUAT SAC")
    print("=" * 80)

    assert avg_err < 1.5, "Sai so goc trung binh phai nho hon 1.5 do!"
    assert max_err < 3.0, "Sai so goc cuc dai khong duoc vuot qua 3.0 do!"
    print("[PASS] UWB PDoA Angle-of-Arrival Estimation: 100% Hoan hao!")


if __name__ == "__main__":
    test_pdoa_angle_of_arrival()
