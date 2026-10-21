"""
Double-Sided Two-Way Ranging (DS-TWR) & Clock Drift Compensation for UWB
Chuyen de 26: Ultra-Wideband IEEE 802.15.4z & Time-of-Flight Secure Ranging
Milestone AM.2 - Bai hoc 101 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Mo phong giao thuc do khoang cach hai chieu Single-Sided (SS-TWR) va Double-Sided (DS-TWR).
- Phan tich anh huong nghiem trong cua sai so troi xung nhip thach anh (Clock Drift ppm) len do chinh xac.
- Chung minh cong thuc DS-TWR triet tieu sai so bac nhat cua thach anh, dat do chinh xac duoi 1 cm.
"""

import math
from typing import Dict, Tuple


SPEED_OF_LIGHT = 299792458.0  # m/s


class UwbNodeClock:
    """
    Mo phong bo dao dong thach anh cua nut UWB (Apple iPhone / Tesla Key).
    Moi nut co tan so thach anh danh dinh 64 GHz (chu ky 15.65 picogiay)
    nhung bi troi tan so (Clock Drift) theo tri so ppm (Parts Per Million).
    """
    def __init__(self, name: str, clock_drift_ppm: float = 0.0):
        self.name = name
        self.ppm = clock_drift_ppm
        # He so ti le thoi gian thuc te: clock_rate = 1.0 + ppm * 1e-6
        self.clock_rate = 1.0 + clock_drift_ppm * 1e-6

    def local_duration_from_ideal(self, ideal_duration_sec: float) -> float:
        """Thoi gian ma nut do duoc tren dong ho cuc bo cua minh"""
        return ideal_duration_sec * self.clock_rate


class DoubleSidedTwoWayRangingSimulator:
    """
    Gia lap giao thuc truyen tin 3 buoc chuan IEEE 802.15.4z:
    Nut A (Initiator - vi du: Apple iPhone) <---> Nut B (Responder - vi du: Tesla Car)
    1. A -> B : POLL packet
    2. B -> A : RESPONSE packet
    3. A -> B : FINAL packet
    """
    def __init__(self, node_a: UwbNodeClock, node_b: UwbNodeClock, true_distance_m: float):
        self.node_a = node_a
        self.node_b = node_b
        self.distance_m = true_distance_m
        self.ideal_tof_sec = true_distance_m / SPEED_OF_LIGHT

    def run_ranging_protocols(self, reply_delay_b_ms: float = 1.0, reply_delay_a_ms: float = 1.2) -> Dict[str, any]:
        """
        Thuc thi ca 2 giao thuc SS-TWR va DS-TWR tren cung mot dieu kien thuc te:
        Dau vao:
            reply_delay_b_ms: Thoi gian nut B cho de xu ly va phat Response (ms)
            reply_delay_a_ms: Thoi gian nut A cho de xu ly va phat Final (ms)
        """
        tof = self.ideal_tof_sec
        reply_b_ideal = reply_delay_b_ms * 1e-3
        reply_a_ideal = reply_delay_a_ms * 1e-3

        # ---------------------------------------------------------------------
        # KHOANG THOI GIAN LY TUONG
        # ---------------------------------------------------------------------
        # Luot 1: A phat POLL -> B nhan -> B cho reply_b -> B phat RESPONSE -> A nhan
        round_a1_ideal = tof + reply_b_ideal + tof  # T_round1 tren A
        # Luot 2: B phat RESPONSE -> A nhan -> A cho reply_a -> A phat FINAL -> B nhan
        round_b2_ideal = tof + reply_a_ideal + tof  # T_round2 tren B

        # ---------------------------------------------------------------------
        # THOI GIAN DO DUOC TREN DONG HO CUC BO TUNG NUT (BI LECH BOI PPM)
        # ---------------------------------------------------------------------
        # Nut A do thoi gian bang dong ho cua minh:
        T_round1 = self.node_a.local_duration_from_ideal(round_a1_ideal)
        T_reply2 = self.node_a.local_duration_from_ideal(reply_a_ideal)

        # Nut B do thoi gian bang dong ho cua minh:
        T_reply1 = self.node_b.local_duration_from_ideal(reply_b_ideal)
        T_round2 = self.node_b.local_duration_from_ideal(round_b2_ideal)

        # ---------------------------------------------------------------------
        # 1. GIAI THUAT SINGLE-SIDED TWR (SS-TWR): Chi dung T_round1 va T_reply1
        # ---------------------------------------------------------------------
        # ToF_SS = (T_round1 - T_reply1) / 2
        tof_ss = 0.5 * (T_round1 - T_reply1)
        dist_ss = tof_ss * SPEED_OF_LIGHT

        # ---------------------------------------------------------------------
        # 2. GIAI THUAT DOUBLE-SIDED TWR (DS-TWR) BAT DOI XUNG CHUAN IEEE 802.15.4z
        # ToF_DS = (T_round1 * T_round2 - T_reply1 * T_reply2) /
        #          (T_round1 + T_round2 + T_reply1 + T_reply2)
        # ---------------------------------------------------------------------
        numerator = (T_round1 * T_round2) - (T_reply1 * T_reply2)
        denominator = T_round1 + T_round2 + T_reply1 + T_reply2
        tof_ds = numerator / denominator
        dist_ds = tof_ds * SPEED_OF_LIGHT

        return {
            "true_dist_m": self.distance_m,
            "true_tof_ns": self.ideal_tof_sec * 1e9,
            "T_round1_ms": T_round1 * 1e3,
            "T_reply1_ms": T_reply1 * 1e3,
            "T_round2_ms": T_round2 * 1e3,
            "T_reply2_ms": T_reply2 * 1e3,
            "tof_ss_ns": tof_ss * 1e9,
            "dist_ss_m": dist_ss,
            "error_ss_cm": (dist_ss - self.distance_m) * 100.0,
            "tof_ds_ns": tof_ds * 1e9,
            "dist_ds_m": dist_ds,
            "error_ds_cm": (dist_ds - self.distance_m) * 100.0
        }


def test_two_way_ranging():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN UWB TWO-WAY RANGING & CLOCK DRIFT COMPENSATION")
    print("=" * 80)

    # 1. Thiet lap thong so thi nghiem thuc te
    # Khoang cach giua iPhone va xe Tesla: 8.50 m (ToF ~ 28.35 ns)
    TRUE_DISTANCE_M = 8.50
    # Thach anh iPhone chuan (+0 ppm), thach anh xe Tesla bi troi tan so (+25 ppm)
    CLOCK_DRIFT_B_PPM = 25.0

    node_a = UwbNodeClock(name="Apple_iPhone", clock_drift_ppm=0.0)
    node_b = UwbNodeClock(name="Tesla_Cybertruck", clock_drift_ppm=CLOCK_DRIFT_B_PPM)

    sim = DoubleSidedTwoWayRangingSimulator(node_a, node_b, true_distance_m=TRUE_DISTANCE_M)
    res = sim.run_ranging_protocols(reply_delay_b_ms=1.0, reply_delay_a_ms=1.2)

    print(f"Khoang cach thuc te (Ground Truth): {res['true_dist_m']:.3f} m (ToF ly tuong: {res['true_tof_ns']:.3f} ns)")
    print(f"Do lech thach anh thuc te         : Node B (Tesla) = +{CLOCK_DRIFT_B_PPM:.1f} ppm")
    print(f"Thoi gian cho phan hoi firmware   : T_reply1 = {res['T_reply1_ms']:.3f} ms, T_reply2 = {res['T_reply2_ms']:.3f} ms")
    print("-" * 80)

    # 2. So sanh hieu nang SS-TWR vs DS-TWR
    print("Ket qua so sanh giua hai giao thuc Two-Way Ranging:")
    print("Giao Thuc Ranging         | ToF Do Duoc (ns) | Cu Ly Tinh Duoc | Sai So Do (cm)")
    print("-" * 75)
    print(f"Single-Sided TWR (SS-TWR) | {res['tof_ss_ns']:16.3f} | {res['dist_ss_m']:13.3f} m | {res['error_ss_cm']:12.1f} cm (SAI LECH THAM HOA)")
    print(f"Double-Sided TWR (DS-TWR) | {res['tof_ds_ns']:16.3f} | {res['dist_ds_m']:13.3f} m | {res['error_ds_cm']:12.3f} cm (CHINH XAC TUYET DOI)")
    print("-" * 80)

    # 3. Danh gia toan hoc
    # Sai so ly thuyet cua SS-TWR: Error = 0.5 * T_reply * ppm = 0.5 * 1ms * 25ppm = 12.5 ns -> 3.747 m
    expected_ss_error_m = 0.5 * (1.0e-3) * (CLOCK_DRIFT_B_PPM * 1e-6) * SPEED_OF_LIGHT
    print(f"-> Sai so ly thuyet SS-TWR do lech thach anh : {expected_ss_error_m * 100:.1f} cm (3.75 m)")
    print(f"-> Sai so thuc te SS-TWR                    : {abs(res['error_ss_cm']):.1f} cm")
    print(f"-> Sai so thuc te DS-TWR triet tieu Clock    : {abs(res['error_ds_cm']):.3f} cm (< 0.1 cm)")
    print(f"-> Do cai thien chinh xac nho DS-TWR         : {abs(res['error_ss_cm']) / max(0.0001, abs(res['error_ds_cm'])):,.0f} LAN!")
    print("=" * 80)

    assert abs(res['error_ds_cm']) < 1.0, "Sai so cua DS-TWR phai nho hon 1.0 cm!"
    assert abs(res['error_ss_cm']) > 300.0, "SS-TWR phai bi sai lech tram trong do troi thach anh!"
    print("[PASS] Double-Sided Two-Way Ranging & Clock Drift Compensation: 100% Hoan hao!")


if __name__ == "__main__":
    test_two_way_ranging()
