"""
EE MENTORSHIP PROGRAM - MODULE BN (NHOM 53) - BAI 210 (MILESTONE BN.3)
================================================================================
DIEU KHIEN DONG VONG CUON DAY AM THANH VOICE COIL MOTOR (VCM) KEM CAM BIEN HALL
TUYEN TINH HOA, BO LOC BIQUAD NOTCH KHU CONG HUONG LA XEP & PID 10 KHZ
CHO CAMERA CHONG RUNG QUANG HOC APPLE IPHONE OIS / AUTOFOCUS
================================================================================

Nguyen ly vat ly & Thiet ke Vong dieu khien Phan cung:
1. Tuyen tinh hoa Cam bien Tu truong Hall Effect (Magnetic Dipole Nonlinearity):
   - Khi nam cham vi sai di chuyen +/- 180 um qua chip Hall, cam ung tu giam phi
     tuyen o 2 bien theo dang S-curve:
       V_hall(x) = K_h * x / (1 + alpha_h * x^2)  (Sai lech phi tuyen ~ 8-12%)
   - Bo bu da thuc bac 3 (3rd-order Polynomial Calibrator) ep sai so do ve < 0.25 um.

2. Cong huong La xep Thu cap (Secondary Flexure Mode ~520 Hz) & Biquad Notch:
   - Ngoai tan so co ban cua khoi cam bien/thau kinh (f_1 ~ 68 Hz), thanh lo xo kim
     loai mong luon co mode dao dong uon phu tai f_2 = 520 Hz (dinh nhon Q_2 = 18).
   - Neu tang he so PID de dat bang thong cao (~150 Hz), dinh 520 Hz vuot nguong 0 dB
     o pha -180 deg gay tu kich rung re camera!
   - Bo loc so Biquad Notch 10 kHz dat tai f_0 = 520 Hz cat sau dinh cong huong > 22 dB:

              1 - 2*cos(w0)*z^(-1) + z^(-2)
     H(z) = b0 * ──────────────────────────────   voi b0 = 1 / (1 + alpha)
              1 - 2*b0*cos(w0)*z^(-1) + (2*b0-1)*z^(-2)

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. He co dien VCM 2 Mode phi dong vi (Rigid Body 68 Hz - Flexure Mode 520 Hz, Q=28):
     x_total(t) = x_rigid(t) - 0.010 * x_flex(t)  (Cong huong 520 Hz gay tu kich neu thieu Notch!)

2. Chuan sai so vi tri muc tieu duoi 1 pixel (~1.22 um tren iPhone Pro):
     RMS Tracking Error < 1.2 um @ 8 Hz Hand-Shake Tracking
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


class HallEffectSensor:
    """Mo hinh Cam bien Tu truong Hall phi tuyen & Bo hieu chuan da thuc bac 3."""

    def __init__(self, k_v_per_um: float = 0.005, alpha_nl: float = 4.2e-6):
        self.k_h = k_v_per_um
        self.alpha = alpha_nl

    def read_voltage(self, x_um: float) -> float:
        # V = K_h * x / (1 + alpha * x^2) -> meo nen o vung bien +/- 180 um
        return (self.k_h * x_um) / (1.0 + self.alpha * (x_um ** 2))

    def measure_raw_linear_um(self, v_hall: float) -> float:
        return v_hall / self.k_h

    def measure_calibrated_um(self, v_hall: float) -> float:
        """Khai trien nguoc chinh xac Lagrange (he so Catalan 1, 1, 2, 5): x = u*(1 + a*u^2 + 2*a^2*u^4 + 5*a^3*u^6)."""
        u = v_hall / self.k_h
        a_u2 = self.alpha * (u ** 2)
        return u * (1.0 + a_u2 + 2.0 * (a_u2 ** 2) + 5.0 * (a_u2 ** 3))


class BiquadNotchFilter:
    """Bo loc so IIR Biquad Notch triet tieu dinh cong huong co hoc 520 Hz @ 10 kHz."""

    def __init__(self, f_notch_hz: float = 520.0, f_sample_hz: float = 10000.0, q_notch: float = 4.5):
        w0 = 2.0 * math.pi * f_notch_hz / f_sample_hz
        alpha = math.sin(w0) / (2.0 * q_notch)
        cos_w0 = math.cos(w0)
        a0 = 1.0 + alpha

        self.b0 = 1.0 / a0
        self.b1 = (-2.0 * cos_w0) / a0
        self.b2 = 1.0 / a0
        self.a1 = (-2.0 * cos_w0) / a0
        self.a2 = (1.0 - alpha) / a0

        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0

    def reset(self) -> None:
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0

    def process(self, x0: float) -> float:
        y0 = self.b0 * x0 + self.b1 * self.x1 + self.b2 * self.x2 - self.a1 * self.y1 - self.a2 * self.y2
        self.x2, self.x1 = self.x1, x0
        self.y2, self.y1 = self.y1, y0
        return y0

    def magnitude_db(self, freq_hz: float, f_sample_hz: float = 10000.0) -> float:
        w = 2.0 * math.pi * freq_hz / f_sample_hz
        z1 = complex(math.cos(-w), math.sin(-w))
        z2 = z1 * z1
        num = self.b0 + self.b1 * z1 + self.b2 * z2
        den = 1.0 + self.a1 * z1 + self.a2 * z2
        return 20.0 * math.log10(max(1e-9, abs(num / den)))


class VCMDualModePlant:
    """
    Mo hinh VCM 2 bac tu do phi dong vi (f1 = 68 Hz rigid-body - f2 = 520 Hz flexure Q=20)
    Nhan dong dien dieu khien I_cmd (A) -> Tra ve dich chuyen thuc te x (um).
    """

    def __init__(self, k_dc_um_per_a: float = 1200.0, flex_coupling: float = -0.010):
        self.k_dc = k_dc_um_per_a
        self.w1 = 2.0 * math.pi * 68.0
        self.zeta1 = 0.22
        self.w2 = 2.0 * math.pi * 520.0
        self.zeta2 = 0.016  # Q2 = 31.2 -> dinh cong huong 520 Hz cuc sac!
        self.c2 = flex_coupling

        self.x1 = self.v1 = 0.0
        self.x2 = self.v2 = 0.0

    def step(self, i_cmd_a: float, dt: float = 1.0e-4) -> float:
        # Sub-step 4 lan (25 us) de tich phan chinh xac mode 520 Hz
        sub_dt = dt / 4.0
        for _ in range(4):
            a1 = (self.w1 ** 2) * (self.k_dc * i_cmd_a - self.x1) - 2.0 * self.zeta1 * self.w1 * self.v1
            self.v1 += a1 * sub_dt
            self.x1 += self.v1 * sub_dt

            a2 = (self.w2 ** 2) * (self.k_dc * i_cmd_a - self.x2) - 2.0 * self.zeta2 * self.w2 * self.v2
            self.v2 += a2 * sub_dt
            self.x2 += self.v2 * sub_dt

        return self.x1 + self.c2 * self.x2


def simulate_vcm_closed_loop(use_notch: bool, duration_s: float = 0.16) -> Dict[str, float]:
    """Chay vong kin PID 10 kHz cho Step 100 um (0..80 ms) & Sine Hand-Shake 100 um @ 8 Hz (80..160 ms)."""
    plant = VCMDualModePlant()
    hall = HallEffectSensor()
    notch = BiquadNotchFilter(f_notch_hz=520.0, f_sample_hz=10000.0, q_notch=2.5)

    dt = 1.0e-4  # 10 kHz
    steps = int(duration_s / dt)

    # Bo dieu khien PID (Derivative-on-Measurement chong kich xung) + Feedforward + Anti-Windup
    # Zero tich phan ki/kp < tan so cat vong de giu Phase Margin cao!
    kp, ki, kd = 0.0018, 0.14, 4.0e-6
    integ = 0.0
    prev_x_meas = 0.0

    step_errs: List[float] = []
    sine_errs: List[float] = []
    max_step_pos = 0.0

    for k in range(steps):
        t = k * dt
        if t < 0.080:
            x_ref = 100.0
            v_ref = 0.0
        else:
            w_s = 2.0 * math.pi * 8.0
            x_ref = 100.0 * math.cos(w_s * (t - 0.080))
            v_ref = -100.0 * w_s * math.sin(w_s * (t - 0.080))

        # Do vi tri qua Hall Sensor (co hieu chuan tuyen tinh)
        x_meas = hall.measure_calibrated_um(hall.read_voltage(plant.x1 + plant.c2 * plant.x2))
        err = x_ref - x_meas
        dx_meas = (x_meas - prev_x_meas) / dt
        prev_x_meas = x_meas

        integ = max(-0.25, min(0.25, integ + err * dt))
        # Feedforward 2-DOF: bu vi tri, giam chan & van toc tham chieu v_ref triet tieu lech pha 8 Hz
        lead_x = x_ref + (2.0 * plant.zeta1 / plant.w1) * v_ref
        i_ff = lead_x / (plant.k_dc * (1.0 + plant.c2))
        u_pid = i_ff + kp * err + ki * integ + kd * (v_ref - dx_meas)
        u_cmd = notch.process(u_pid) if use_notch else u_pid
        u_clamped = max(-0.35, min(0.35, u_cmd))

        x_true = plant.step(u_clamped, dt)

        if t < 0.080:
            max_step_pos = max(max_step_pos, x_true)
            if t >= 0.035:
                step_errs.append(x_true - x_ref)
        else:
            if t >= 0.100:
                sine_errs.append(x_true - x_ref)

    step_rms = math.sqrt(sum(e * e for e in step_errs) / len(step_errs))
    sine_rms = math.sqrt(sum(e * e for e in sine_errs) / len(sine_errs))
    overshoot_pct = max(0.0, ((max_step_pos - 100.0) / 100.0) * 100.0)
    return {"step_rms_um": step_rms, "sine_rms_um": sine_rms, "overshoot_pct": overshoot_pct}


def test_vcm_hall_ois_notch_control():
    """Chuong trinh kiem thu Hall Linearizer, Biquad Notch & Vong kin VCM 10 kHz."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BN (NHOM 53) - BAI 210 (MILESTONE BN.3)")
    print("VCM + CAM BIEN HALL TUYEN TINH HOA, BIQUAD NOTCH 520 HZ & PID 10 KHZ")
    print("=" * 80)

    # 1. Kiem thu Hieu chuan phi tuyen cam bien Hall Effect +/- 160 um
    print("\n[1] Kiem thu Hieu chuan phi tuyen Cam bien Hall tai bien x = 160.0 um:")
    hall = HallEffectSensor()
    v_edge = hall.read_voltage(160.0)
    raw_um = hall.measure_raw_linear_um(v_edge)
    cal_um = hall.measure_calibrated_um(v_edge)
    err_raw = abs(raw_um - 160.0)
    err_cal = abs(cal_um - 160.0)

    print(f"  * Chua hieu chuan (Tuyen tinh tho) : {raw_um:6.2f} um (Sai so {err_raw:5.2f} um = {err_raw/1.22:.1f} pixels!)")
    print(f"  * Da hieu chuan da thuc bac 5      : {cal_um:6.2f} um (Sai so {err_cal:5.3f} um < 0.25 um)")

    assert err_raw > 14.0 and err_cal < 0.25
    print("  -> Ket luan: Hieu chuan Hall cat giam sai so bien tu ~15 um xuong < 0.25 um (PASS)!")

    # 2. Kiem thu dap ung tan so Bo loc Biquad Notch 520 Hz & Vong kin VCM 10 kHz
    print("\n[2] Kiem thu Vong kin VCM 10 kHz (PID Khong Notch vs PID + Biquad Notch 520 Hz):")
    notch = BiquadNotchFilter(f_notch_hz=520.0, f_sample_hz=10000.0, q_notch=2.5)
    atten_520 = notch.magnitude_db(520.0)
    passband_10hz = notch.magnitude_db(10.0)
    print(f"  * Dap ung Biquad Notch  : Tai 10 Hz = {passband_10hz:+.3f} dB | Tai 520 Hz = {atten_520:+.1f} dB")

    res_no_notch = simulate_vcm_closed_loop(use_notch=False)
    res_notch = simulate_vcm_closed_loop(use_notch=True)

    print(
        f"  * KHONG Notch (Rung 520 Hz): Step RMS = {res_no_notch['step_rms_um']:5.2f} um | "
        f"Overshoot = {res_no_notch['overshoot_pct']:5.1f}% -> MAT ON DINH!"
    )
    print(
        f"  * CO Notch 520 Hz          : Step RMS = {res_notch['step_rms_um']:5.2f} um | "
        f"Sine 8Hz RMS = {res_notch['sine_rms_um']:5.2f} um | Overshoot = {res_notch['overshoot_pct']:4.1f}%"
    )

    assert atten_520 < -25.0 and abs(passband_10hz) < 0.05
    assert res_no_notch["step_rms_um"] > 20.0  # Rung re do dinh 520 Hz
    assert res_notch["step_rms_um"] < 1.0 and res_notch["sine_rms_um"] < 2.0
    print("  -> Ket luan: Biquad Notch triet dinh cong huong la xep, giu VCM bam < 1.0 um (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 210: VCM HALL & BIQUAD NOTCH 10 KHZ HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_vcm_hall_ois_notch_control()
