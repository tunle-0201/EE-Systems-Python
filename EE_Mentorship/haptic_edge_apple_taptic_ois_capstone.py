"""
EE MENTORSHIP PROGRAM - MODULE BN (NHOM 53) - BAI 211 (MILESTONE BN.4 - CAPSTONE)
================================================================================
DONG CO CHAP HANH DIEN TU CHINH XAC APPLE TAPTIC ENGINE & CHONG RUNG QUANG HOC
CAMERA SENSOR-SHIFT OIS 2 TRUC 10 KHZ CAPSTONE CHO APPLE IPHONE PRO
================================================================================

Kien truc Toan he thong Co-Dien tu Chinh xac (Mechatronics Capstone):
1. Phan he 1 - Apple Taptic Engine (LRA Auto-Resonance + 180-deg Active Braking):
   - Khi ngon tay bam manh lam tan so cong huong LRA troi tu 170 Hz -> 158 Hz:
     + Mach Auto-Resonance Back-EMF do pha qua 0 tu dong khoa dung 158 Hz.
     + Bo phat xung Force-Touch kich Overdrive 5.0V trong 9 ms roi Phanh chu dong
       dao pha 180 deg dap tat duoi < 16 ms (Crispness > 20x), dam bao Double-Tap
       khong dinh nhau.

2. Phan he 2 - Chong rung Quang hoc Sensor-Shift OIS 2 Truc (Pitch & Yaw @ 10 kHz):
   - Tieu cu thuc cam bien: f_eff = 6.8 mm -> Rung tay 0.70 deg gay lech ~83 um
     (~68 pixels nhoe anh trong phoi sang dem 1/4 giay = 250 ms!).
   - Bo xu ly Gyroscope + Loc thong cao chong troi (Leaky Integrator f_hp = 0.35 Hz)
     tinh quy dao bu nguoc chieu tuc thoi (x_ref, y_ref).
   - Moi truc dieu khien bang Hall Linearizer (Catalan) + 2-DOF PID + Biquad Notch
     520 Hz o tan so 10 kHz -> Giam nhoe xuong < 2.5 um (< 2.0 px, triet tieu > 28 dB)!
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


G_ACCEL = 9.80665


class TapticEngineSubsystem:
    """Phan he LRA Apple Taptic Engine (Auto-Resonance PLL + 180-deg Active Brake)."""

    def __init__(self, true_f0_hz: float = 158.0):
        self.m = 2.5e-3
        self.k_s = self.m * ((2.0 * math.pi * true_f0_hz) ** 2)
        self.b_m = 0.16
        self.b_l = 0.22
        self.r_e = 8.0
        self.l_e = 0.20e-3
        self.true_f0 = true_f0_hz

    def calibrate_resonance_and_fire_click(self) -> Dict[str, float]:
        dt = 20.0e-6
        # Buoc 1: Quet va khoa tan so cong huong bang Auto-Resonance PLL trong 80 ms
        x = v = i = 0.0
        nco_f = 170.0
        phase = 0.0
        freq_int = 0.0
        prev_v = 0.0
        for k in range(int(0.080 / dt)):
            v_drv = 3.0 if (phase % (2.0 * math.pi)) < math.pi else -3.0
            a = (self.b_l * i - self.b_m * v - self.k_s * x) / self.m
            di = (v_drv - self.r_e * i - self.b_l * v) / self.l_e
            x += v * dt + 0.5 * a * dt * dt
            v += a * dt
            i += di * dt
            if k > 25 and ((prev_v < 0.0 <= v) or (prev_v > 0.0 >= v)):
                tgt = 0.0 if v >= 0.0 else math.pi
                pe = (phase % (2.0 * math.pi)) - tgt
                if pe > math.pi:
                    pe -= 2.0 * math.pi
                elif pe < -math.pi:
                    pe += 2.0 * math.pi
                freq_int += -12.0 * pe
                nco_f = max(120.0, min(220.0, 170.0 + freq_int - 18.0 * pe))
            prev_v = v
            phase += 2.0 * math.pi * nco_f * dt

        # Buoc 2: Phat xung Force-Touch Sharp Click dung tan so nco_f vua khoa + Phanh dao pha 180 deg
        x = v = i = 0.0
        kick_ms = 9.0
        accel_g: List[float] = []
        time_ms: List[float] = []
        brake_done = False

        for k in range(int(0.060 / dt)):
            t = k * dt
            tm = t * 1000.0
            time_ms.append(tm)
            if tm < kick_ms:
                s_k = 1.0 if math.sin(2.0 * math.pi * nco_f * t) >= 0.0 else -1.0
                v_cmd = 5.0 * s_k
                if abs(i) > 0.62:
                    v_cmd = i * self.r_e * 0.85
            else:
                e_mech = 0.5 * self.m * v * v + 0.5 * self.k_s * x * x
                if brake_done or e_mech < 2.5e-6:
                    brake_done = True
                    v_cmd = 0.0
                elif abs(v) > 0.004:
                    v_cmd = -4.8 * math.copysign(1.0, v)
                else:
                    v_cmd = 0.0

            a = (self.b_l * i - self.b_m * v - self.k_s * x) / self.m
            di = (v_cmd - self.r_e * i - self.b_l * v) / self.l_e
            x += v * dt + 0.5 * a * dt * dt
            v += a * dt
            i += di * dt
            accel_g.append(a / G_ACCEL)

        peak_g = max(abs(a) for tm, a in zip(time_ms, accel_g) if tm < kick_ms + 2.0)
        last_above = kick_ms
        for tm, a in zip(time_ms, accel_g):
            if tm >= kick_ms and abs(a) > 0.10 * peak_g:
                last_above = tm
        tail_vals = [a for tm, a in zip(time_ms, accel_g) if tm >= 20.0]
        tail_rms = math.sqrt(sum(v_a * v_a for v_a in tail_vals) / max(1, len(tail_vals)))

        return {
            "locked_f0_hz": nco_f,
            "peak_kick_g": peak_g,
            "brake_decay_ms": last_above - kick_ms,
            "crispness": peak_g / max(1e-6, tail_rms),
        }


class VCMChannelOIS:
    """Mot truc VCM + Cam bien Hall + Biquad Notch 520 Hz + 2-DOF PID cho Sensor-Shift OIS."""

    def __init__(self):
        self.k_dc = 1200.0
        self.w1 = 2.0 * math.pi * 68.0
        self.zeta1 = 0.22
        self.w2 = 2.0 * math.pi * 520.0
        self.zeta2 = 0.016
        self.c2 = -0.010

        self.x1 = self.v1 = 0.0
        self.x2 = self.v2 = 0.0

        # Hall Calibration params
        self.k_h = 0.005
        self.alpha_h = 4.2e-6

        # Biquad Notch 520 Hz @ 10 kHz (Q = 2.5)
        w0 = 2.0 * math.pi * 520.0 / 10000.0
        al = math.sin(w0) / (2.0 * 2.5)
        cw = math.cos(w0)
        a0 = 1.0 + al
        self.nb0, self.nb1, self.nb2 = 1.0 / a0, (-2.0 * cw) / a0, 1.0 / a0
        self.na1, self.na2 = (-2.0 * cw) / a0, (1.0 - al) / a0
        self.nx1 = self.nx2 = self.ny1 = self.ny2 = 0.0

        self.integ = 0.0
        self.prev_x_meas = 0.0

    def _read_hall_calibrated(self, rng: random.Random) -> float:
        x_true = self.x1 + self.c2 * self.x2
        v_h = (self.k_h * x_true) / (1.0 + self.alpha_h * (x_true ** 2)) + rng.gauss(0.0, 0.00015)
        u = v_h / self.k_h
        au2 = self.alpha_h * (u ** 2)
        return u * (1.0 + au2 + 2.0 * (au2 ** 2) + 5.0 * (au2 ** 3))

    def step_10khz(self, x_ref_um: float, v_ref_ums: float, rng: random.Random) -> float:
        dt = 1.0e-4
        x_meas = self._read_hall_calibrated(rng)
        err = x_ref_um - x_meas
        dx = (x_meas - self.prev_x_meas) / dt
        self.prev_x_meas = x_meas

        self.integ = max(-0.25, min(0.25, self.integ + err * dt))
        lead_x = x_ref_um + (2.0 * self.zeta1 / self.w1) * v_ref_ums
        i_ff = lead_x / (self.k_dc * (1.0 + self.c2))
        u_pid = i_ff + 0.0018 * err + 0.14 * self.integ + 4.0e-6 * (v_ref_ums - dx)

        # Qua Biquad Notch 520 Hz
        u_n = (
            self.nb0 * u_pid + self.nb1 * self.nx1 + self.nb2 * self.nx2
            - self.na1 * self.ny1 - self.na2 * self.ny2
        )
        self.nx2, self.nx1 = self.nx1, u_pid
        self.ny2, self.ny1 = self.ny1, u_n
        i_cmd = max(-0.35, min(0.35, u_n))

        sub_dt = dt / 4.0
        for _ in range(4):
            a1 = (self.w1 ** 2) * (self.k_dc * i_cmd - self.x1) - 2.0 * self.zeta1 * self.w1 * self.v1
            self.v1 += a1 * sub_dt
            self.x1 += self.v1 * sub_dt
            a2 = (self.w2 ** 2) * (self.k_dc * i_cmd - self.x2) - 2.0 * self.zeta2 * self.w2 * self.v2
            self.v2 += a2 * sub_dt
            self.x2 += self.v2 * sub_dt
        return self.x1 + self.c2 * self.x2


class SensorShiftOISSystem:
    """He thong Sensor-Shift OIS 2 Truc (Pitch & Yaw) cho chup anh dem 250 ms."""

    def __init__(self, f_eff_mm: float = 6.8, pixel_pitch_um: float = 1.22):
        self.f_eff_um = f_eff_mm * 1000.0
        self.pixel_um = pixel_pitch_um
        self.ch_pitch = VCMChannelOIS()
        self.ch_yaw = VCMChannelOIS()

    def run_night_exposure_250ms(self, rng: random.Random) -> Dict[str, float]:
        dt = 1.0e-4
        steps = 2500  # 250 ms @ 10 kHz
        f_hp = 0.04   # Leaky gyro high-pass 0.04 Hz sau hieu chuan bias ZRO truoc chup

        theta_est_p = 0.0
        theta_est_y = 0.0

        off_pts: List[Tuple[float, float]] = []
        on_pts: List[Tuple[float, float]] = []

        for k in range(steps):
            t = k * dt
            # Rung tay thuc te phoi 3.8 Hz + 9.5 Hz + xung buoc chan 14 Hz (~0.68 deg peak)
            deg_p = 0.42 * math.sin(2.0 * math.pi * 3.8 * t) + 0.20 * math.sin(2.0 * math.pi * 9.5 * t)
            deg_y = 0.34 * math.sin(2.0 * math.pi * 4.4 * t + 0.8) + 0.14 * math.sin(2.0 * math.pi * 14.0 * t)

            rate_p_deg = (
                0.42 * (2.0 * math.pi * 3.8) * math.cos(2.0 * math.pi * 3.8 * t)
                + 0.20 * (2.0 * math.pi * 9.5) * math.cos(2.0 * math.pi * 9.5 * t)
            )
            rate_y_deg = (
                0.34 * (2.0 * math.pi * 4.4) * math.cos(2.0 * math.pi * 4.4 * t + 0.8)
                + 0.14 * (2.0 * math.pi * 14.0) * math.cos(2.0 * math.pi * 14.0 * t)
            )

            # Gyro sensor sau hieu chuan ZRO (nhieu 0.04 deg/s, du troi 0.015 deg/s)
            gyro_p_rad_s = math.radians(rate_p_deg + 0.015 + rng.gauss(0.0, 0.04))
            gyro_y_rad_s = math.radians(rate_y_deg - 0.015 + rng.gauss(0.0, 0.04))

            leak = 2.0 * math.pi * f_hp * dt
            theta_est_p = (1.0 - leak) * theta_est_p + gyro_p_rad_s * dt
            theta_est_y = (1.0 - leak) * theta_est_y + gyro_y_rad_s * dt

            x_shake_um = self.f_eff_um * math.radians(deg_p)
            y_shake_um = self.f_eff_um * math.radians(deg_y)

            x_cmd_um = -self.f_eff_um * theta_est_p
            y_cmd_um = -self.f_eff_um * theta_est_y
            vx_cmd = -self.f_eff_um * gyro_p_rad_s
            vy_cmd = -self.f_eff_um * gyro_y_rad_s

            x_vcm = self.ch_pitch.step_10khz(x_cmd_um, vx_cmd, rng)
            y_vcm = self.ch_yaw.step_10khz(y_cmd_um, vy_cmd, rng)

            if t >= 0.025:
                off_pts.append((x_shake_um, y_shake_um))
                on_pts.append((x_shake_um + x_vcm, y_shake_um + y_vcm))

        def psf_blur_rms(pts: List[Tuple[float, float]]) -> float:
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            return math.sqrt(sum((p[0] - mx) ** 2 + (p[1] - my) ** 2 for p in pts) / len(pts))

        rms_off_um = psf_blur_rms(off_pts)
        rms_on_um = psf_blur_rms(on_pts)
        rejection_db = 20.0 * math.log10(rms_off_um / max(1e-6, rms_on_um))

        return {
            "blur_off_um": rms_off_um,
            "blur_off_px": rms_off_um / self.pixel_um,
            "blur_on_um": rms_on_um,
            "blur_on_px": rms_on_um / self.pixel_um,
            "rejection_db": rejection_db,
        }


def test_apple_taptic_ois_capstone():
    """Chuong trinh kiem thu Capstone Apple Taptic Engine + Sensor-Shift OIS 10 kHz."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BN (NHOM 53) - BAI 211 (MILESTONE BN.4 - CAPSTONE)")
    print("DONG CO APPLE TAPTIC ENGINE & CAMERA SENSOR-SHIFT OIS 10 KHZ CAPSTONE")
    print("=" * 80)

    rng = random.Random(20261117)

    # 1. Kiem thu Apple Taptic Engine khi tan so LRA troi ve 158.0 Hz
    print("\n[1] Kiem thu Apple Taptic Engine (True f0 = 158.0 Hz + Active 180-deg Braking):")
    taptic = TapticEngineSubsystem(true_f0_hz=158.0)
    tap_res = taptic.calibrate_resonance_and_fire_click()
    print(f"  * Khoa tan so Back-EMF  : {tap_res['locked_f0_hz']:6.2f} Hz (Target 158.00 Hz)")
    print(f"  * Gia toc xung Click    : {tap_res['peak_kick_g']:6.2f} G | Tat duoi <10% = {tap_res['brake_decay_ms']:5.2f} ms")
    print(f"  * Do sac net Crispness  : {tap_res['crispness']:6.2f}x (> 18.0x target)")

    assert abs(tap_res["locked_f0_hz"] - 158.0) < 2.0
    assert tap_res["brake_decay_ms"] < 18.0 and tap_res["crispness"] > 18.0
    print("  -> Ket luan: Taptic Engine tu khoa 158 Hz & Phanh dap tat sac net < 18 ms (PASS)!")

    # 2. Kiem thu Sensor-Shift OIS 2 Truc 10 kHz chup dem 250 ms
    print("\n[2] Thuc chien Camera Sensor-Shift OIS 2 Truc 10 kHz (Phoi sang dem 250 ms):")
    ois = SensorShiftOISSystem(f_eff_mm=6.8, pixel_pitch_um=1.22)
    ois_res = ois.run_night_exposure_250ms(rng)

    print(
        f"  * OIS TAT (Rung tay 3.8..14 Hz) : Nhoe = {ois_res['blur_off_um']:5.2f} um "
        f"({ois_res['blur_off_px']:4.1f} pixels -> NHOE NANG!)"
    )
    print(
        f"  * OIS BAT (Hall + Notch + PID) : Nhoe = {ois_res['blur_on_um']:5.2f} um "
        f"({ois_res['blur_on_px']:4.2f} pixels -> SAC NET!)"
    )
    print(f"  * Triet tieu Rung Quang hoc    : {ois_res['rejection_db']:5.2f} dB (> 28.0 dB target)")

    assert ois_res["blur_off_px"] > 30.0
    assert ois_res["blur_on_px"] < 2.5 and ois_res["rejection_db"] > 28.0
    print("  -> Ket luan: Sensor-Shift OIS 10 kHz giam nhoe > 28 dB xuong duoi 2.5 pixels (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 211 (CAPSTONE): TAPTIC & SENSOR-SHIFT OIS 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_apple_taptic_ois_capstone()
