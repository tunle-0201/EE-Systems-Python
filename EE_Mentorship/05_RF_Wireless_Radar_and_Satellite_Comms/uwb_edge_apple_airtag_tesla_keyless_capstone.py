"""
Apple AirTag Precision Finding & Tesla UWB Keyless Anti-Relay Defense Capstone
Chuyen de 26: Ultra-Wideband IEEE 802.15.4z & Time-of-Flight Secure Ranging
Milestone AM.4 - Bai hoc 103 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Dung hop toan chuoi cong nghe: Phan ung xung CIR, Suon dau LDE, Do khoang cach DS-TWR,
  va Do goc toi chenh pha PDoA de tao he toa do khong gian 2D/3D.
- Phong thu vat ly chong tan cong chuyen tiep song trom xe (Relay Attack Defense) tren Tesla Cybertruck.
- Dinh vi tim do that lac Precision Finding tren Apple AirTag / iPhone U1 chip voi sai so duoi 3 cm.
"""

import math
from enum import Enum
from typing import Dict, Tuple, Optional


SPEED_OF_LIGHT = 299792458.0  # m/s


class SecurityStatus(Enum):
    UNLOCKED_AUTHORIZED = "UNLOCKED_AUTHORIZED"  # Chu xe trong vung an toan (< 1.5m)
    LOCKED_OUT_OF_RANGE = "LOCKED_OUT_OF_RANGE"  # Chu xe o xa (> 1.5m), cua khoa
    RELAY_ATTACK_ALARM  = "RELAY_ATTACK_ALARM"   # Phat hien tan cong trom xe tu xa


class TeslaUwbPhoneKeyEngine:
    """
    Dong co xac thuc mo khoa xe khong chia UWB tren Tesla Model S Plaid & Cybertruck.
    Su dung Double-Sided Two-Way Ranging (DS-TWR) de chong tan cong chuyen tiep (Relay Attack).
    """
    def __init__(self, unlock_distance_threshold_m: float = 1.50):
        self.unlock_threshold_m = unlock_distance_threshold_m
        self.security_status = SecurityStatus.LOCKED_OUT_OF_RANGE

    def evaluate_ranging_and_security(self, measured_tof_sec: float, rssi_dbm: float) -> Dict[str, any]:
        """
        Kiem tra xac thuc an toan:
        - Neu chi dung Bluetooth RSSI: Tin hieu manh (vi du -55 dBm) bi khuat phuc boi bo kich song cua trom xe.
        - UWB xac thuc bang Time-of-Flight vat ly: Khoang cach ToF = c * ToF.
        - Neu RSSI manh (-55 dBm) ma ToF lai o xa (> 1.5 m) -> PHAT HIEN TAN CONG CHUYEN TIEP (RELAY ATTACK)!
        """
        calculated_distance_m = measured_tof_sec * SPEED_OF_LIGHT

        # Gia su bo kich song cua trom lam RSSI manh len nhu the dang o rat gan (-50 dBm den -65 dBm)
        is_rssi_strong_near = (rssi_dbm >= -65.0)

        if calculated_distance_m <= self.unlock_threshold_m:
            self.security_status = SecurityStatus.UNLOCKED_AUTHORIZED
            msg = "Xac thuc ToF hop le: Chu xe dung sat cua (< 1.5m) -> MO CUA XE"
        else:
            if is_rssi_strong_near:
                # Bat dong vat ly: RSSI manh nhung ToF o xa -> Dang bi kich song tan cong!
                self.security_status = SecurityStatus.RELAY_ATTACK_ALARM
                msg = "CANH BAO AN NINH: Phat hien tan cong chuyen tiep Relay Attack (Khuat phuc RSSI nhung ToF vuot nguong) -> KHOA XE VA BAO DONG!"
            else:
                self.security_status = SecurityStatus.LOCKED_OUT_OF_RANGE
                msg = "Chu xe o ngoai pham vi an toan -> Cua xe tiep tuc khoa"

        return {
            "status": self.security_status,
            "calculated_distance_m": calculated_distance_m,
            "rssi_dbm": rssi_dbm,
            "message": msg
        }


class AppleAirTagPrecisionEngine:
    """
    Dong co dinh vi khong gian chinh xac Precision Finding cua Apple AirTag va iPhone U1/U2.
    Ket hop khoang cach R tu DS-TWR va goc phuong vi theta tu PDoA mang anten kep.
    """
    def __init__(self, carrier_freq_hz: float = 6.4896e9):
        self.fc = carrier_freq_hz
        self.wavelength = SPEED_OF_LIGHT / carrier_freq_hz
        self.d_ant = 0.5 * self.wavelength

    def locate_target_2d(self, tof_sec: float, phase_diff_rad: float) -> Dict[str, any]:
        """
        Chuyen doi toa do Cuc (Polar: R, theta) sang toa do Descartes (Cartesian: X, Y):
        X = R * sin(theta)  (Do lech Phai / Trai so voi mui dien thoai)
        Y = R * cos(theta)  (Khoang cach thang Phia Truoc)
        """
        # 1. Tinh khoang cach ban kinh R
        R = tof_sec * SPEED_OF_LIGHT

        # 2. Tinh goc phuong vi theta tu PDoA
        sin_arg = (phase_diff_rad * self.wavelength) / (2.0 * math.pi * self.d_ant)
        sin_arg_clamped = max(-1.0, min(1.0, sin_arg))
        theta_rad = math.asin(sin_arg_clamped)
        theta_deg = math.degrees(theta_rad)

        # 3. Toa do Descartes
        x_m = R * math.sin(theta_rad)
        y_m = R * math.cos(theta_rad)

        return {
            "distance_m": R,
            "azimuth_deg": theta_deg,
            "coord_x_m": x_m,
            "coord_y_m": y_m
        }


def test_uwb_apple_tesla_capstone():
    print("=" * 80)
    print("BAT DAU MO PHONG UWB APPLE AIRTAG & TESLA KEYLESS DEFENSE CAPSTONE")
    print("=" * 80)

    # =========================================================================
    # THU THACH 1: DONG CO AN NINH MO KHOA XE TESLA CHONG TAN CONG RELAY ATTACK
    # =========================================================================
    print("THU THACH 1: Co che phong thu vat ly chong trom xe Relay Attack tren Tesla...")
    tesla_engine = TeslaUwbPhoneKeyEngine(unlock_distance_threshold_m=1.50)

    # Kich ban A: Chu xe hop le tien toi cua xe (Khoang cach thuc te 1.10 m, RSSI = -60 dBm)
    true_dist_valid = 1.10
    tof_valid = true_dist_valid / SPEED_OF_LIGHT
    res_valid = tesla_engine.evaluate_ranging_and_security(measured_tof_sec=tof_valid, rssi_dbm=-60.0)

    print("Kich ban A: Chu xe hop le toi gan cua xe (1.10 m):")
    print(f"-> Cu ly do duoc qua ToF  : {res_valid['calculated_distance_m']:.2f} m")
    print(f"-> Cuong do song RSSI     : {res_valid['rssi_dbm']:.1f} dBm")
    print(f"-> Trang thai bao mat     : {res_valid['status'].value}")
    assert res_valid["status"] == SecurityStatus.UNLOCKED_AUTHORIZED

    # Kich ban B: Ke trom dung may chuyen tiep Relay Attack
    # Dien thoai chu xe de trong phong ngu (cach xe 15 m). Ke trom dung may khuech dai BLE lam RSSI manh len -55 dBm.
    # Tuy nhien, may chuyen tiep tao ra do tre xu ly phan cung (Processing Latency ~ 25 ns = 7.5 m)
    # Khoang cach ToF thuc te bi keo dai: 15 m + 7.5 m = 22.5 m!
    print("-" * 80)
    print("Kich ban B: Ke trom thuc hien Relay Attack (Khuat phuc BLE RSSI -55 dBm)...")
    relay_tof = 22.5 / SPEED_OF_LIGHT
    res_attack = tesla_engine.evaluate_ranging_and_security(measured_tof_sec=relay_tof, rssi_dbm=-55.0)

    print(f"-> Cu ly do duoc qua ToF  : {res_attack['calculated_distance_m']:.2f} m (Vuot nguong 1.5m)")
    print(f"-> Cuong do song RSSI     : {res_attack['rssi_dbm']:.1f} dBm (Gia mao o rat gan)")
    print(f"-> Trang thai bao mat     : {res_attack['status'].value}")
    print(f"-> Ket qua phan ung he thong: {res_attack['message']}")
    assert res_attack["status"] == SecurityStatus.RELAY_ATTACK_ALARM

    # =========================================================================
    # THU THACH 2: DINH VI KHONG GIAN CHINH XAC PRECISION FINDING (APPLE AIRTAG)
    # Tim chiec chia khoa that lac tai toa do thuc te (X = 1.80 m, Y = 3.12 m)
    # =========================================================================
    print("-" * 80)
    print("THU THACH 2: Dinh vi khong gian Precision Finding tren Apple AirTag / iPhone U1...")
    airtag_engine = AppleAirTagPrecisionEngine(carrier_freq_hz=6.4896e9)

    # Toa do muc tieu that
    TRUE_X = 1.80  # m (Lech sang phai 1.8 m)
    TRUE_Y = 3.12  # m (Phia truoc 3.12 m)
    true_range = math.sqrt(TRUE_X**2 + TRUE_Y**2)  # ~ 3.60 m
    true_azimuth_rad = math.atan2(TRUE_X, TRUE_Y)  # ~ 0.5236 rad = 30.0 do

    ideal_tof = true_range / SPEED_OF_LIGHT
    ideal_phase_diff = (2.0 * math.pi * airtag_engine.d_ant * math.sin(true_azimuth_rad)) / airtag_engine.wavelength

    # Them nhieu nho phan cung ToF (+0.05 ns) va Phase Diff (+0.02 rad)
    measured_tof = ideal_tof + 0.05e-9
    measured_pdoa = ideal_phase_diff + 0.02

    res_airtag = airtag_engine.locate_target_2d(measured_tof, measured_pdoa)

    print(f"Toa do that cua AirTag            : X = {TRUE_X:.2f} m, Y = {TRUE_Y:.2f} m (Khoang cach: {true_range:.2f} m, Goc: {math.degrees(true_azimuth_rad):.1f} do)")
    print(f"Toa do Apple Precision Engine uoc luong: X = {res_airtag['coord_x_m']:.2f} m, Y = {res_airtag['coord_y_m']:.2f} m")
    print(f"-> Khoang cach hien thi tren iPhone: {res_airtag['distance_m']:.2f} m")
    print(f"-> Mui ten AR chi huong            : Chech sang phai {res_airtag['azimuth_deg']:.1f} do")

    pos_error_m = math.sqrt((res_airtag['coord_x_m'] - TRUE_X)**2 + (res_airtag['coord_y_m'] - TRUE_Y)**2)
    print(f"-> Sai so vi tri khong gian 2D     : {pos_error_m * 100:.1f} cm (< 5.0 cm)")

    assert pos_error_m < 0.05, "Sai so dinh vi Precision Finding phai nho hon 5 cm!"
    print("=" * 80)
    print("[PASS] Apple AirTag & Tesla UWB Keyless Anti-Relay Defense Capstone: 100% Hoan hao!")


if __name__ == "__main__":
    test_uwb_apple_tesla_capstone()
