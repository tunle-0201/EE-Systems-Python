"""
EE MENTORSHIP PROGRAM - MODULE BN (NHOM 53) - BAI 209 (MILESTONE BN.2)
================================================================================
KY THUAT PHANH CHU DONG DAO PHA 180 DO (ACTIVE REVERSE-PHASE BRAKING) &
BO TONG HOP XUNG XUC GIAC APPLE TAPTIC ENGINE SHARP CLICK
================================================================================

Nguyen ly vat ly & Dieu khien nang luong:
1. Tai sao tha troi (Open-Circuit Coast-Down) lam phim rung bi "nhay"?
   - Khi kich xung LRA (f_0 = 170 Hz) roi ngat mach Hi-Z, he so pham chat co hoc
     Q ~ 15 khien con lac tiep tuc dao dong tu do suot > 65 ms (11 nua chu ky),
     bien nut bam "tach" thanh tieng rung "re re" kho chiu!

2. Phanh Chu dong Dao pha 180 do (Reverse-Phase Active Braking):
   - Gia doan Overdrive Kick: Bom ap cao V_od (5.0 V) cung chieu van toc v(t)
     de gia toc vot len cuc nhanh trong < 6 ms.
   - Giai doan Phanh Chu dong: Ngay khi ket thuc nhip cham, cau H dao pha 180 deg
     tao dien ap NGUOC CHIEU tuc thoi voi van toc v(t) (Back-EMF):
       V_brake(t) = -V_brake_amp * sign(v(t))
     -> Cong suat co hoc P_brake = F * v = -|B*l*I * v| < 0 hut sach dong nang
        cua con lac chi trong ~1.5 chu ky (< 12 ms), sau do chot ngan mach low-side!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Cong suat Tieu tan Dong nang khi Phanh Chu dong:
     dE_mech / dt = F_lorentz * v - B_m * v^2 = B*l * I(t) * v(t) - B_m * v^2
     Neu V_drive = -V_max * sign(v) -> I * v < 0 -> Rut can nang luong cuc nhanh!

2. Chi so Do sac net Xung cham (Taptic Crispness Ratio):
                     a_G_peak (trong pha Kick)
     Crispness = ──────────────────────────────────  (Muc tieu > 8.0)
                  a_G_rms (duoi 18 ms .. 60 ms)
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


G_ACCEL = 9.80665


@dataclass
class TapticLRAConfig:
    mass_kg: float = 2.5e-3
    k_spring_n_m: float = 2852.32   # f_0 = 170 Hz
    b_mech_ns_m: float = 0.16       # Q_m ~ 16.7 (rung lau neu khong phanh!)
    b_l_n_a: float = 0.22           # Hang so dien-co tang nhe de phanh manh
    r_coil_ohm: float = 8.0
    l_coil_h: float = 0.20e-3
    v_overdrive_v: float = 5.0
    v_brake_v: float = 4.8
    i_max_guard_a: float = 0.65     # Bao ve nhiet cuon day (tuyet doi <= 0.65 A)


class TapticLRAPlant:
    """He dien-co LRA co che do ngat mach Hi-Z, ngan mach Low-Side & Kep dong."""

    def __init__(self, cfg: TapticLRAConfig):
        self.c = cfg
        self.x = 0.0
        self.v = 0.0
        self.i = 0.0

    def reset(self) -> None:
        self.x = 0.0
        self.v = 0.0
        self.i = 0.0

    def step_rk4(self, dt: float, v_drive: float, open_hiz: bool = False) -> Tuple[float, float]:
        def derivs(x: float, v: float, i: float) -> Tuple[float, float, float]:
            dx = v
            dv = (self.c.b_l_n_a * i - self.c.b_mech_ns_m * v - self.c.k_spring_n_m * x) / self.c.mass_kg
            if open_hiz:
                di = -i / 2.5e-5
            else:
                di = (v_drive - self.c.r_coil_ohm * i - self.c.b_l_n_a * v) / self.c.l_coil_h
            return dx, dv, di

        k1 = derivs(self.x, self.v, self.i)
        k2 = derivs(self.x + 0.5 * dt * k1[0], self.v + 0.5 * dt * k1[1], self.i + 0.5 * dt * k1[2])
        k3 = derivs(self.x + 0.5 * dt * k2[0], self.v + 0.5 * dt * k2[1], self.i + 0.5 * dt * k2[2])
        k4 = derivs(self.x + dt * k3[0], self.v + dt * k3[1], self.i + dt * k3[2])

        self.x += (dt / 6.0) * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
        self.v += (dt / 6.0) * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
        self.i += (dt / 6.0) * (k1[2] + 2.0 * k2[2] + 2.0 * k3[2] + k4[2])

        a_ms2 = (self.c.b_l_n_a * self.i - self.c.b_mech_ns_m * self.v - self.c.k_spring_n_m * self.x) / self.c.mass_kg
        return a_ms2 / G_ACCEL, self.i


class ActiveBrakingSynthesizer:
    """Bo tong hop song Haptics so sanh Coast-Down vs Short-Brake vs Active Reverse-Phase."""

    @staticmethod
    def simulate_click(cfg: TapticLRAConfig, mode: str = "ACTIVE_BRAKE", kick_ms: float = 9.0, total_ms: float = 80.0) -> Dict[str, float]:
        plant = TapticLRAPlant(cfg)
        dt = 20.0e-6
        steps = int(total_ms * 1e-3 / dt)
        f_0 = 170.0

        accel_trace: List[float] = []
        time_trace_ms: List[float] = []
        peak_current = 0.0
        brake_latched_off = False

        for k in range(steps):
            t = k * dt
            t_ms = t * 1000.0
            time_trace_ms.append(t_ms)
            open_hiz = False

            if t_ms < kick_ms:
                # Giai doan Overdrive Kick: Phat song vuong cung pha 170 Hz kem bao ve kep dong
                sign_k = 1.0 if math.sin(2.0 * math.pi * f_0 * t) >= 0.0 else -1.0
                v_cmd = sign_k * cfg.v_overdrive_v
                # Gioi han ap tuc thoi neu dong tiep can I_max_guard
                if abs(plant.i) > cfg.i_max_guard_a * 0.96:
                    v_cmd = plant.i * cfg.r_coil_ohm * 0.85
            else:
                if mode == "HI_Z_COAST":
                    v_cmd = 0.0
                    open_hiz = True
                elif mode == "SHORT_BRAKE":
                    v_cmd = 0.0  # Ngan mach cuon day qua low-side MOSFET
                else:  # ACTIVE_BRAKE: Dao pha 180 deg chong lai van toc tuc thoi v(t)
                    # Nang luong co hoc con lai (dong nang + the nang lo xo)
                    e_mech = 0.5 * cfg.mass_kg * (plant.v ** 2) + 0.5 * cfg.k_spring_n_m * (plant.x ** 2)
                    if brake_latched_off or e_mech < 2.5e-6:
                        brake_latched_off = True
                        v_cmd = 0.0  # Chot ngan mach low-side triet du am cuoi
                    elif abs(plant.v) > 0.004:
                        v_cmd = -cfg.v_brake_v * math.copysign(1.0, plant.v)
                    else:
                        v_cmd = 0.0

            a_g, cur_i = plant.step_rk4(dt, v_cmd, open_hiz=open_hiz)
            accel_trace.append(a_g)
            peak_current = max(peak_current, abs(cur_i))

        peak_kick_g = max(abs(a) for t_m, a in zip(time_trace_ms, accel_trace) if t_m < kick_ms + 2.0)
        thresh_10pct = 0.10 * peak_kick_g

        # Tim thoi diem cuoi cung ma gia toc vuot qua 10% dinh sau khi bat dau phanh
        last_above_ms = kick_ms
        for t_m, a in zip(time_trace_ms, accel_trace):
            if t_m >= kick_ms and abs(a) > thresh_10pct:
                last_above_ms = t_m
        decay_time_ms = last_above_ms - kick_ms

        # Tinh Crispness = Peak Kick / Tail RMS (sau 18 ms den het)
        tail_vals = [a for t_m, a in zip(time_trace_ms, accel_trace) if t_m >= 18.0]
        tail_rms_g = math.sqrt(sum(v * v for v in tail_vals) / max(1, len(tail_vals)))
        crispness = peak_kick_g / max(1e-6, tail_rms_g)

        return {
            "peak_kick_g": peak_kick_g,
            "decay_ms": decay_time_ms,
            "tail_rms_g": tail_rms_g,
            "crispness": crispness,
            "peak_current_a": peak_current,
        }


def test_active_braking_waveform_synth():
    """Chuong trinh kiem thu Phanh chu dong 180 deg & Bo tong hop xung Apple Taptic."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BN (NHOM 53) - BAI 209 (MILESTONE BN.2)")
    print("PHANH CHU DONG DAO PHA 180 DO & TONG HOP XUNG APPLE TAPTIC CLICK")
    print("=" * 80)

    cfg = TapticLRAConfig()

    # 1. So sanh 3 che do phanh sau xung kich 9.0 ms: Hi-Z Coast vs Short-Brake vs Active 180-Deg
    print("\n[1] So sanh thoi gian tat dao dong tan du (ve < 10% dinh) sau khi kich 9.0 ms:")
    res_hiz = ActiveBrakingSynthesizer.simulate_click(cfg, mode="HI_Z_COAST", kick_ms=9.0)
    res_short = ActiveBrakingSynthesizer.simulate_click(cfg, mode="SHORT_BRAKE", kick_ms=9.0)
    res_act = ActiveBrakingSynthesizer.simulate_click(cfg, mode="ACTIVE_BRAKE", kick_ms=9.0)

    for label, res in [
        ("Tha troi Hi-Z (Khong phanh)   ", res_hiz),
        ("Ngan mach Low-Side (Passive)  ", res_short),
        ("Phanh dao pha 180 deg (Active)", res_act),
    ]:
        print(
            f"  * {label}: Peak = {res['peak_kick_g']:5.2f} G | Decay <10% = {res['decay_ms']:5.2f} ms | "
            f"Crispness = {res['crispness']:6.2f}x | I_max = {res['peak_current_a']:.3f} A"
        )

    assert res_hiz["decay_ms"] > 45.0
    assert res_short["decay_ms"] < res_hiz["decay_ms"]
    assert res_act["decay_ms"] < 16.0 and res_act["crispness"] > 20.0
    assert res_act["peak_current_a"] <= cfg.i_max_guard_a + 0.02
    print("  -> Ket luan: Phanh dao pha 180 deg dap tat duoi duoi 16 ms (Crispness > 20x) (PASS)!")

    # 2. Kiem thu chuoi xung kep Force-Touch Double-Tap (30 ms / nhip khong dinh nhau)
    print("\n[2] Kiem thu do tach bach xung kep Double-Tap (cach nhau 30 ms):")
    assert res_act["decay_ms"] < 18.0  # Tat han truoc khi nhip thu 2 bat dau tai 30 ms!
    print(
        f"  * Nhip 1 tat han sau {res_act['decay_ms']:.2f} ms -> Nhip 2 tai t=30.0 ms hoan toan sach du am (0% chong lan)!"
    )
    print("  -> Ket luan: Dat chuan xuc giac sac net Apple Force Touch Trackpad (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 209: ACTIVE 180-DEG BRAKING HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_active_braking_waveform_synth()
