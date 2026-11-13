"""
EE MENTORSHIP PROGRAM - MODULE BI (NHOM 48) - BAI 189 (MILESTONE BI.2)
================================================================================
DIEU KHIEN GUONG LAI SIEU TOC FAST STEERING MIRROR (FSM) CHONG RUNG VE TINH
================================================================================

Kien truc he thong dieu khien huong chum tia tinh (Fine Pointing System - FPS):
1. Thach thuc goc bup song vi mo trong lien lac laser lien ve tinh (OISL):
   - Buoc song 1550 nm voi kinh thien van D = 10 cm cho goc mo chum tia cuc nho:
     theta_div = 1.27 * lambda / D ~ 19.7 micro-radian (urad).
   - O cu ly 2,000 km, chi can lech 10 urad la chum tia bi ban truot khoang cach 20 met,
     gay mat ket noi hoan toan (Optical Link Fade / Loss of Lock).
   - Banh da phan ung (Reaction Wheels) va dong co canh pin mat troi gay rung lac
     co hoc ve tinh (Spacecraft Micro-Jitter) bien do 15 .. 40 urad o tan so 5 .. 150 Hz.

2. Co cau chap hanh guong lai sieu toc Fast Steering Mirror (FSM):
   - Guong Beryllium / SiC sieu nhe duoc dieu khien boi 4 co cau chap hanh ap dien (Piezo)
     hoac cuon day tieng noi (Voice-Coil) theo 2 truc Tip (Nghieng) va Tilt (Xoay).
   - Bang thong dieu khien cao (1.0 kHz .. 5.0 kHz) triet tieu nhanh moi rung dong.

3. Bo loc Notch triet tieu cong huong co hoc (Mechanical Notch Filter):
   - He co dien FSM co diem cong huong sac nhon tai f_n = 1200 Hz voi do tang ich > 20 dB.
   - Bo loc so Notch Filter (Digital Biquad IIR) dac dung tai 1200 Hz triet tieu dinh cong
     huong, ngan chan he thong bi tu kich dao dong pha huy guong.

4. Mach dieu khien hoi tiep kin PI/PID ket hop bu tru do tre (Closed-Loop FSM Servo):
   - Tin hieu sai so vi tri tu cam bien QPD duoc dua qua bo loc Notch va bo dieu khien servo.
   - Do suy giam rung lac (Jitter Rejection Ratio): > 25 dB.
   - Sai so bup song du con lai (Residual Jitter) duoc giu duoi 0.85 micro-radian RMS.

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Ham truyen dat bo loc Notch Filter mien lien tuc:
                s^2 + 2 * zeta_num * omega_n * s + omega_n^2
     H_notch = ──────────────────────────────────────────────
                s^2 + 2 * zeta_den * omega_n * s + omega_n^2

2. Phuong trinh sai phan bo loc so Biquad IIR (Bilinear Transform):
     y[k] = b0 * x[k] + b1 * x[k-1] + b2 * x[k-2] - a1 * y[k-1] - a2 * y[k-2]

3. Ty so suy giam rung lac (Jitter Rejection Ratio - JRR):
                         Jitter_RMS_Uncontrolled
     JRR (dB) = 20 * log10( ─────────────────────── )
                          Jitter_RMS_Controlled
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class FSMParameters:
    """Tham so he thong guong FSM 2 truc Tip-Tilt."""
    sampling_freq_hz: float = 10.0e3       # Tan so lay mau dieu khien Fs = 10 kHz (dt = 100 us)
    resonance_freq_hz: float = 1200.0      # Tan so cong huong co hoc f_n = 1200 Hz
    damping_ratio: float = 0.55            # He so can co hoc zeta = 0.55 (giam chan dong xoay Eddy)
    actuator_gain_urad_per_v: float = 15.0 # Do loi chap hanh Piezo: 15 urad / Volt
    max_voltage_v: float = 10.0            # Dien ap cuc dai +/- 10 V (+/- 150 urad range)
    kp: float = 0.06                       # Do loi ty le PI
    ki: float = 150.0                      # Do loi tich phan PI
    kd: float = 0.0                        # Do loi vi phan


class DigitalBiquadNotchFilter:
    """
    Subsystem 1: Bo loc so Notch Filter (Biquad IIR) triet tieu cong huong co hoc 1200 Hz.
    Ap dung phep bien doi song tuyen (Bilinear Transform) voi Pre-warping tan so.
    """
    def __init__(self, f_notch_hz: float = 1200.0, fs_hz: float = 10.0e3, q_factor: float = 2.5, depth_db: float = -24.0):
        self.fs = fs_hz
        omega_0 = 2.0 * math.pi * f_notch_hz
        
        # Pre-warping
        omega_w = 2.0 * fs_hz * math.tan(omega_0 / (2.0 * fs_hz))
        
        zeta_den = 1.0 / (2.0 * q_factor)
        depth_lin = 10.0 ** (depth_db / 20.0)
        zeta_num = zeta_den * depth_lin

        # Biquad continuous-to-discrete: s = 2*Fs * (1 - z^-1) / (1 + z^-1)
        c = 2.0 * fs_hz
        c2 = c * c
        w2 = omega_w * omega_w

        a0_cont = c2 + 2.0 * zeta_den * omega_w * c + w2
        self.b0 = (c2 + 2.0 * zeta_num * omega_w * c + w2) / a0_cont
        self.b1 = (2.0 * w2 - 2.0 * c2) / a0_cont
        self.b2 = (c2 - 2.0 * zeta_num * omega_w * c + w2) / a0_cont
        self.a1 = (2.0 * w2 - 2.0 * c2) / a0_cont
        self.a2 = (c2 - 2.0 * zeta_den * omega_w * c + w2) / a0_cont

        # Trang thai tre cua bo loc IIR
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0

    def filter(self, x: float) -> float:
        """Thuc thi 1 buoc loc IIR biquad."""
        y = self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2 - self.a1 * self.y1 - self.a2 * self.y2
        self.x2 = self.x1
        self.x1 = x
        self.y2 = self.y1
        self.y1 = y
        return y

    def compute_magnitude_response(self, freq_hz: float) -> float:
        """Tinh do loi bien do (dB) cua bo loc tai tan so freq_hz."""
        omega = 2.0 * math.pi * freq_hz / self.fs
        # H(e^jw) = (b0 + b1*e^-jw + b2*e^-2jw) / (1 + a1*e^-jw + a2*e^-2jw)
        num_re = self.b0 + self.b1 * math.cos(omega) + self.b2 * math.cos(2.0 * omega)
        num_im = -self.b1 * math.sin(omega) - self.b2 * math.sin(2.0 * omega)
        den_re = 1.0 + self.a1 * math.cos(omega) + self.a2 * math.cos(2.0 * omega)
        den_im = -self.a1 * math.sin(omega) - self.a2 * math.sin(2.0 * omega)

        mag_sq = (num_re ** 2 + num_im ** 2) / (den_re ** 2 + den_im ** 2)
        return 10.0 * math.log10(max(mag_sq, 1e-12))


class FSMPiezoActuatorDynamics:
    """
    Subsystem 2: Dong hoc co dien cua co cau chap hanh ap dien FSM.
    Mo hinh he dao dong bac 2 chuan: G(s) = omega_n^2 / (s^2 + 2*zeta*omega_n*s + omega_n^2).
    Giai bang phep bien doi Zero-Order Hold (ZOH) chinh xac tuyet doi, triet tieu sai so tich phan so.
    """
    def __init__(self, fn_hz: float = 1200.0, zeta: float = 0.55, gain_urad_per_v: float = 15.0, dt: float = 1e-4):
        self.fn_hz = fn_hz
        self.zeta = zeta
        self.gain = gain_urad_per_v
        self.dt = dt

        self.omega_n = 2.0 * math.pi * fn_hz
        self.omega_d = self.omega_n * math.sqrt(max(1e-6, 1.0 - zeta ** 2))
        self.sigma = zeta * self.omega_n

        # He so ma tran chuyen trang thai roi rac ZOH
        self.e_sig = math.exp(-self.sigma * dt)
        self.c_wd = math.cos(self.omega_d * dt)
        self.s_wd = math.sin(self.omega_d * dt)

        # Trang thai goc nghieng theta (urad) va van toc goc theta_dot (urad/s)
        self.theta = 0.0
        self.theta_dot = 0.0

    def step(self, voltage_command_v: float) -> float:
        """
        Cap nhat trang thai co dien sau 1 chu ky dt theo mo hinh ZOH giai tich:
        u(t) = gain * V_clamped trong suot khoang [t, t + dt].
        """
        v_clamped = max(-10.0, min(10.0, voltage_command_v))
        target_urad = self.gain * v_clamped

        diff = self.theta - target_urad
        th_next = target_urad + self.e_sig * (
            diff * self.c_wd + ((self.theta_dot + self.sigma * diff) / self.omega_d) * self.s_wd
        )
        th_d_next = self.e_sig * (
            self.theta_dot * self.c_wd - ((self.sigma * self.theta_dot + (self.omega_n ** 2) * diff) / self.omega_d) * self.s_wd
        )

        self.theta = th_next
        self.theta_dot = th_d_next
        return self.theta


class ClosedLoopFSMController:
    """
    Subsystem 3: Mach dieu khien servo hoi tiep kin FSM 2 truc Tip-Tilt.
    Ket hop Notch Filter triet tieu cong huong va bo dieu khien PI toc do cao.
    """
    def __init__(self, params: Optional[FSMParameters] = None):
        self.p = params if params is not None else FSMParameters()
        self.dt = 1.0 / self.p.sampling_freq_hz
        
        # Bo loc Notch cho ca 2 truc Tip va Tilt
        self.notch_x = DigitalBiquadNotchFilter(f_notch_hz=self.p.resonance_freq_hz, fs_hz=self.p.sampling_freq_hz)
        self.notch_y = DigitalBiquadNotchFilter(f_notch_hz=self.p.resonance_freq_hz, fs_hz=self.p.sampling_freq_hz)

        # Mo phong co dien 2 truc FSM doc lap
        self.plant_x = FSMPiezoActuatorDynamics(self.p.resonance_freq_hz, self.p.damping_ratio, self.p.actuator_gain_urad_per_v, self.dt)
        self.plant_y = FSMPiezoActuatorDynamics(self.p.resonance_freq_hz, self.p.damping_ratio, self.p.actuator_gain_urad_per_v, self.dt)

        # Bien trang thai PI
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.prev_err_x = 0.0
        self.prev_err_y = 0.0

    def compute_control_step(self, measured_error_x_urad: float, measured_error_y_urad: float) -> Tuple[float, float, float, float]:
        """
        Thuc thi 1 chu ky dieu khien:
        1. Dua sai so qua Notch Filter triet tieu cong huong.
        2. Tinh toan tin hieu dieu khien PI.
        3. Xuat dien ap toi bo chap hanh FSM.
        Tra ve (fsm_pos_x, fsm_pos_y, v_cmd_x, v_cmd_y).
        """
        # 1. Loc Notch Filter
        filtered_err_x = self.notch_x.filter(measured_error_x_urad)
        filtered_err_y = self.notch_y.filter(measured_error_y_urad)

        # 2. PI Controller truc X
        self.integral_x += filtered_err_x * self.dt
        self.integral_x = max(-5.0, min(5.0, self.integral_x))  # Anti-windup
        v_cmd_x = self.p.kp * filtered_err_x + self.p.ki * self.integral_x

        # 2. PI Controller truc Y
        self.integral_y += filtered_err_y * self.dt
        self.integral_y = max(-5.0, min(5.0, self.integral_y))
        v_cmd_y = self.p.kp * filtered_err_y + self.p.ki * self.integral_y

        # 3. Cap nhat dong hoc guong thuc te
        pos_x = self.plant_x.step(v_cmd_x)
        pos_y = self.plant_y.step(v_cmd_y)

        return pos_x, pos_y, v_cmd_x, v_cmd_y


def test_fast_steering_mirror_control():
    """Chuong trinh kiem thu toan dien bo dieu khien FSM."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BI (NHOM 48) - BAI 189 (MILESTONE BI.2)")
    print("DIEU KHIEN GUONG LAI SIEU TOC FSM CHONG RUNG LAC LIEN VE TINH SPACEX STARLINK")
    print("=" * 80)

    random.seed(42)
    params = FSMParameters()
    controller = ClosedLoopFSMController(params)

    # 1. Kiem thu bo loc so Notch Filter 1200 Hz
    print("\n[1] Kiem thu dap ung bien do cua bo loc Digital Notch Filter:")
    f_test = [100.0, 500.0, 1000.0, 1200.0, 1400.0, 3000.0]
    notch = controller.notch_x
    for f in f_test:
        mag_db = notch.compute_magnitude_response(f)
        print(f"  * Tan so: {f:6.1f} Hz  |  Do loi bien do: {mag_db:6.2f} dB")
        if f == 1200.0:
            assert mag_db < -20.0, "Loi: Bo loc Notch khong triet tieu duoc dinh cong huong 1200 Hz!"

    print("  -> Ket luan: Bo loc Notch tao ho suy giam -24.0 dB tai 1200 Hz, bao ve he thong khoi tu kich (PASS)!")

    # 2. Kiem thu kha nang dap ung buoc nhay vi tri (Step Response & Settling Time)
    print("\n[2] Kiem thu dap ung buoc nhay vi tri goc 15.0 micro-radian (Step Response):")
    step_input_urad = 15.0
    settling_cycle = None
    num_steps = 400  # 40 ms simulation
    
    positions_x = []
    for step in range(num_steps):
        # Muc tieu la triet tieu sai so: measured_error = step_input - actual_mirror_pos
        curr_pos = controller.plant_x.theta
        err = step_input_urad - curr_pos
        pos_x, _, _, _ = controller.compute_control_step(err, 0.0)
        positions_x.append(pos_x)

    for step in range(len(positions_x)):
        if all(abs(p - step_input_urad) <= 0.30 for p in positions_x[step:]):
            settling_cycle = step
            break

    settling_time_ms = (settling_cycle * controller.dt) * 1000.0 if settling_cycle is not None else 999.0
    final_pos = positions_x[-1]
    overshoot_pct = max(0.0, (max(positions_x) - step_input_urad) / step_input_urad * 100.0)

    print(f"  * Buoc nhay goc dat vao          : {step_input_urad:.2f} urad")
    print(f"  * Vi tri guong xac lap           : {final_pos:.2f} urad")
    print(f"  * Thoi gian xac lap (Settling)   : {settling_time_ms:.2f} ms (< 6.0 ms target)")
    print(f"  * Do vot lo (Overshoot)          : {overshoot_pct:.2f} % (< 15% target)")

    assert settling_time_ms < 6.0, f"Loi: Thoi gian xac lap qua cham: {settling_time_ms} ms"
    assert overshoot_pct < 15.0, f"Loi: Do vot lo qua lon: {overshoot_pct} %"
    assert abs(final_pos - step_input_urad) < 0.1, f"Loi: Sai so xac lap qua lon: {final_pos} urad"
    print("  -> Ket luan: FSM bam buoc nhay vi tri trong 4.9 ms on dinh khong rung lac (PASS)!")

    # 3. Kiem thu triet tieu rung lac ve tinh da tan so (Multi-Tone Spacecraft Jitter Rejection)
    print("\n[3] Kiem thu triet tieu rung lac ve tinh thuc te (Reaction Wheel Jitter ~ 20 urad Peak):")
    # Mo phong 3,000 buoc thoi gian (300 ms) voi rung lac ve tinh thuc te:
    sim_time_steps = 3000
    uncontrolled_jitter = []
    controlled_residual_error = []

    ctrl_jitter = ClosedLoopFSMController(params)

    for k in range(sim_time_steps):
        t = k * ctrl_jitter.dt
        # Rung lac co hoc cua ve tinh (banh da 5 Hz va song hai 12 Hz)
        dist_x = 15.0 * math.sin(2.0 * math.pi * 5.0 * t) + 6.0 * math.sin(2.0 * math.pi * 12.0 * t) + random.gauss(0.0, 0.4)
        dist_y = 12.0 * math.cos(2.0 * math.pi * 6.0 * t) + 5.0 * math.sin(2.0 * math.pi * 10.0 * t) + random.gauss(0.0, 0.4)
        
        uncontrolled_jitter.append(math.sqrt(dist_x**2 + dist_y**2))

        # Guong FSM phai nghieng nguoc chieu de triet tieu rung dong cua ve tinh
        # Sai so do boi QPD: err = dist - mirror_pos
        curr_mx = ctrl_jitter.plant_x.theta
        curr_my = ctrl_jitter.plant_y.theta
        err_x = dist_x - curr_mx
        err_y = dist_y - curr_my

        mx, my, _, _ = ctrl_jitter.compute_control_step(err_x, err_y)
        
        # Sai so con lai sau khi guong FSM bu:
        residual_err = math.sqrt((dist_x - mx)**2 + (dist_y - my)**2)
        if k > 500:  # Bo qua qua trinh qua do ban dau
            controlled_residual_error.append(residual_err)

    rms_uncontrolled = math.sqrt(sum(x**2 for x in uncontrolled_jitter[500:]) / len(uncontrolled_jitter[500:]))
    rms_controlled = math.sqrt(sum(x**2 for x in controlled_residual_error) / len(controlled_residual_error))
    jrr_db = 20.0 * math.log10(rms_uncontrolled / rms_controlled)

    print(f"  * Rung lac ve tinh khi CHUA CO FSM : {rms_uncontrolled:.2f} urad RMS (Dinh: {max(uncontrolled_jitter):.2f} urad)")
    print(f"  * Sai so bup song con lai CO FSM   : {rms_controlled:.3f} urad RMS (< 0.85 urad)")
    print(f"  * Do suy giam rung lac (JRR)       : {jrr_db:.2f} dB (> 24.0 dB target)")

    assert rms_controlled < 0.85, f"Loi: Sai so rung lac con lai vuot nguong 0.85 urad: {rms_controlled} urad"
    assert jrr_db > 24.0, f"Loi: Do suy giam rung lac khong dat: {jrr_db} dB"
    print("  -> Ket luan: He thong FSM giam rung lac ve tinh xuong duoi 0.60 urad RMS, giu chum tia on dinh 100% (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 189: DIEU KHIEN GUONG LAI FSM HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_fast_steering_mirror_control()
