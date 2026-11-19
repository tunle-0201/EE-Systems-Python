"""
EE MENTORSHIP PROGRAM - MODULE BO (NHOM 54) - BAI 214 (MILESTONE BO.3)
================================================================================
BO BIEN DOI CONG SUAT 4-SWITCH NON-INVERTING BUCK-BOOST (5V .. 48V USB-PD)
CHUYEN VUNG MUOT V_IN ≈ V_OUT & DIEU KHIEN VONG KEP CV/CC CHO USB-PD PPS
================================================================================

Nguyen ly vat ly Dien tu Cong suat:
1. Cau truc 4 khoa MOSFET Q1/Q2 (Nhanh Buck) - Cuon cam L - Q3/Q4 (Nhanh Boost):
   - Che do Buck (V_out < 0.82 * V_in): Q4 dong lien tuc, Q3 tat -> chi 2 FET Buck dong cat!
   - Che do Boost (V_out > 1.18 * V_in): Q1 dong lien tuc, Q2 tat -> chi 2 FET Boost dong cat!
   - Vung chuyen tiep Buck-Boost (0.82 <= V_out/V_in <= 1.18):
     Tranh vung chet Min-Off-Time khi V_in ≈ V_out bang luat dieu khien lien tuc m:
       D_boost(m) = 0.1525 * (m - 0.82) / 0.36
       D_buck(m)  = m * (1.0 - D_boost(m))
     -> Bao toan ty so ap V_out / V_in = D_buck / (1 - D_boost) = m TUYET DOI LIEN TUC!

2. Vong dieu khien kep CV/CC cho Programmable Power Supply (USB-PD PPS):
   - Cho phep dien thoai/laptop yeu cau chinh tung nac 20 mV va gioi han dong 50 mA.
   - Hai bo PI doc lap (CV dien ap & CC dong dien) ket hop qua bo chon MIN(i_cv, i_cc):
     Khi tai keo vuot nguong dong I_limit, bo dieu khien lap tuc ha dien ap dau ra
     de ghim dong o dung muc an toan (Constant-Current Thermal/Battery Protection)!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Phuong trinh Trang thai Trung binh Cuon cam & Tu loc (State-Space Averaged):
     L * dI_L / dt = D_buck * V_in - (1 - D_boost) * V_out - I_L * R_loop
     C * dV_o / dt = (1 - D_boost) * I_L - I_load
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class BuckBoostConfig:
    v_in: float = 16.0          # Dien ap pin 4S Li-Ion / bus trung gian: 16.0 V
    l_h: float = 6.8e-6         # Cuon cam cong suat: 6.8 uH
    r_dcr_ohm: float = 12.0e-3  # DCR cuon cam: 12 mOhm
    r_fet_ohm: float = 8.0e-3   # R_ds(on) moi MOSFET: 8 mOhm (tong 2 FET = 16 mOhm)
    c_out_f: float = 220.0e-6   # Dan tu dau ra: 220 uF
    f_sw_hz: float = 400.0e3    # Tan so dong cat: 400 kHz
    q_g_c: float = 14.0e-9      # Dien tich cong Gate moi FET
    v_drv: float = 5.0          # Dien ap driver: 5.0 V


def compute_smooth_duties(m_cmd: float) -> Tuple[float, float, str]:
    """
    Chuyen lenh ty so ap m = V_out / V_in sang (D_buck, D_boost, mode) lien tuc C1:
    Khong bao gio bi giat xung khi di ngang qua V_in == V_out (m = 1.0)!
    """
    m = max(0.05, min(3.5, m_cmd))
    if m <= 0.82:
        return m, 0.0, "BUCK"
    elif m >= 1.18:
        return 1.0, 1.0 - (1.0 / m), "BOOST"
    else:
        d_boost = 0.15254237 * ((m - 0.82) / 0.36)
        d_buck = m * (1.0 - d_boost)
        return d_buck, d_boost, "BUCK-BOOST"


class FourSwitchBuckBoostPPS:
    """Bo bien doi 4-Switch Buck-Boost co Vong kep CV/CC PPS & Tinh toan Hieu suat."""

    def __init__(self, cfg: BuckBoostConfig):
        self.c = cfg
        self.i_l = 0.0
        self.v_out = 5.0

    def compute_efficiency_pct(self, v_out: float, i_load: float, d_buck: float, d_boost: float, mode: str) -> float:
        i_l_rms = i_load / max(0.2, 1.0 - d_boost)
        p_out = v_out * i_load
        # Ton hao dan (2 FET + DCR cuon cam)
        p_cond = (i_l_rms ** 2) * (self.c.r_dcr_ohm + 2.0 * self.c.r_fet_ohm)
        # So nhanh MOSFET dang dong cat (2 trong Buck/Boost, 4 trong vung chuyen tiep)
        n_active_fets = 4.0 if mode == "BUCK-BOOST" else 2.0
        p_gate = n_active_fets * self.c.q_g_c * self.c.v_drv * self.c.f_sw_hz
        p_sw = 0.5 * max(self.c.v_in, v_out) * i_l_rms * 8.0e-9 * self.c.f_sw_hz * (n_active_fets / 2.0)
        p_core = 0.18
        p_loss = p_cond + p_gate + p_sw + p_core
        return (p_out / max(1e-6, p_out + p_loss)) * 100.0

    def simulate_sweep_and_pps(
        self, v_targets: List[Tuple[float, float, float, float]]
    ) -> List[Dict[str, float]]:
        """
        Mo phong Vong kep Current-Mode Control (Outer CV/CC -> Inner I_L Loop -> Unified m_cmd)
        qua cac giai doan: [(duration_ms, v_ref, i_limit, r_load_ohm), ...].
        """
        dt = 2.0e-6  # 2 us step (500 kHz digital loop)
        self.i_l = 1.0
        self.v_out = 5.0

        integ_v = 0.0
        integ_i = 0.0
        d_boost_prev = 0.0
        v_ref_slewed = 5.0
        summaries: List[Dict[str, float]] = []

        for dur_ms, v_ref, i_limit, r_load in v_targets:
            steps = int(dur_ms * 1e-3 / dt)
            max_step_glitch_v = 0.0
            last_mode = "BUCK"
            in_cc_mode = False
            d_buck = 0.3
            d_boost = 0.0

            for k in range(steps):
                # Dieu chinh mem v_ref theo chuan sườn ap USB-PD (15 V/ms)
                max_dv_ref = 15000.0 * dt
                if abs(v_ref - v_ref_slewed) <= max_dv_ref:
                    v_ref_slewed = v_ref
                elif v_ref > v_ref_slewed:
                    v_ref_slewed += max_dv_ref
                else:
                    v_ref_slewed -= max_dv_ref

                i_load = self.v_out / max(0.1, r_load)

                # 1. Vong ngoai CV & CC tinh dong tai muc tieu I_out_cmd (A)
                err_v = v_ref_slewed - self.v_out
                integ_v = max(-2.0, min(8.0, integ_v + 650.0 * err_v * dt))
                i_out_cv = (v_ref_slewed / max(0.1, r_load)) + 1.8 * err_v + integ_v

                err_i = i_limit - i_load
                integ_i = max(-1.5, min(6.0, integ_i + 550.0 * err_i * dt))
                i_out_cc = i_limit + 1.4 * err_i + integ_i

                if i_out_cc < i_out_cv:
                    i_out_cmd = i_out_cc
                    in_cc_mode = True
                    integ_v = max(-2.0, min(8.0, i_out_cmd - (v_ref_slewed / max(0.1, r_load))))
                else:
                    i_out_cmd = i_out_cv
                    in_cc_mode = False
                    integ_i = max(-2.0, min(8.0, i_out_cmd - i_limit))

                # Quy doi dong tai sang dong cuon cam muc tieu I_L_ref = I_out / (1 - D_boost)
                i_l_ref = max(-1.0, min(20.0, i_out_cmd / max(0.25, 1.0 - d_boost_prev)))

                # 2. Vong trong Current Loop giai m_cmd thong nhat qua moi che do Buck/BB/Boost
                r_loop = self.c.r_dcr_ohm + 2.0 * self.c.r_fet_ohm
                v_l_des = 0.55 * (i_l_ref - self.i_l)
                m_cmd = (self.v_out + (self.i_l * r_loop + v_l_des) / max(0.25, 1.0 - d_boost_prev)) / self.c.v_in

                d_buck, d_boost, mode = compute_smooth_duties(m_cmd)
                d_boost_prev = d_boost
                last_mode = mode

                # Tich phan 2 buoc phu (1 us) cho cuon cam & tu loc
                sub_dt = dt * 0.5
                for _ in range(2):
                    di_l = (d_buck * self.c.v_in - (1.0 - d_boost) * self.v_out - self.i_l * r_loop) / self.c.l_h
                    self.i_l = max(-2.0, self.i_l + di_l * sub_dt)
                    i_out_cur = self.v_out / max(0.1, r_load)
                    dv_o = ((1.0 - d_boost) * self.i_l - i_out_cur) / self.c.c_out_f
                    self.v_out = max(0.5, self.v_out + dv_o * sub_dt)

                if k > int(0.75 * steps):
                    target_expect = min(v_ref, i_limit * r_load)
                    max_step_glitch_v = max(max_step_glitch_v, abs(self.v_out - target_expect))

            i_load_end = self.v_out / max(0.1, r_load)
            eff = self.compute_efficiency_pct(self.v_out, i_load_end, d_buck, d_boost, last_mode)
            summaries.append({
                "v_ref": v_ref,
                "v_out": self.v_out,
                "i_out": i_load_end,
                "mode": last_mode,
                "cc_active": in_cc_mode,
                "ripple_dev_mv": max_step_glitch_v * 1000.0,
                "eff_pct": eff,
            })
        return summaries


def test_four_switch_buck_boost_pps():
    """Chuong trinh kiem thu 4-Switch Buck-Boost (5V -> 16V -> 48V) & PPS CV/CC Foldback."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BO (NHOM 54) - BAI 214 (MILESTONE BO.3)")
    print("BO BIEN DOI 4-SWITCH BUCK-BOOST (5..48V) & VONG KEP PPS CV/CC")
    print("=" * 80)

    cfg = BuckBoostConfig(v_in=16.0)
    conv = FourSwitchBuckBoostPPS(cfg)

    # 1. Kiem thu chuyen vung muot C1 tu Buck (5V) -> Buck-Boost (16V = V_in) -> Boost (28V, 48V)
    print("\n[1] Quet 3 che do dong cat (V_in = 16.0V -> 5V Buck -> 16V Overlap -> 48V EPR Boost):")
    stages = [
        (8.0, 5.0, 5.0, 1.67),    # 5V @ 3A (BUCK)
        (8.0, 16.0, 5.0, 4.00),   # 16V @ 4A (BUCK-BOOST V_in == V_out!)
        (8.0, 28.0, 5.0, 7.00),   # 28V @ 4A (BOOST)
        (10.0, 48.0, 5.0, 10.67), # 48V @ 4.5A (216W BOOST)
    ]
    res1 = conv.simulate_sweep_and_pps(stages)
    for r in res1:
        print(
            f"  * Target {r['v_ref']:4.1f}V ({r['mode']:10s}) -> V_out={r['v_out']:6.3f}V | "
            f"I={r['i_out']:4.2f}A | Sai lech={r['ripple_dev_mv']:5.1f} mV | Eff={r['eff_pct']:5.2f}%"
        )

    assert res1[0]["mode"] == "BUCK" and res1[0]["eff_pct"] > 95.0
    assert res1[1]["mode"] == "BUCK-BOOST" and res1[1]["ripple_dev_mv"] < 80.0 and res1[1]["eff_pct"] > 94.0
    assert res1[3]["mode"] == "BOOST" and abs(res1[3]["v_out"] - 48.0) < 0.15 and res1[3]["eff_pct"] > 95.0
    print("  -> Ket luan: Chuyen vung qua V_in == 16.0V khong giat (< 80 mV), hieu suat > 94% (PASS)!")

    # 2. Kiem thu USB-PD PPS buoc nhay tinh 20 mV & Vong bao ve ghim dong CC Foldback (3.00 A)
    print("\n[2] Kiem thu USB-PD PPS buoc nhay 20 mV (9.00V -> 9.02V) & Chuyen che do CC ghim 3.00 A:")
    conv_pps = FourSwitchBuckBoostPPS(cfg)
    pps_stages = [
        (14.0, 9.00, 3.00, 4.50),  # 9.00V @ 2.00A (Che do CV)
        (12.0, 9.02, 3.00, 4.51),  # Tang dung 20 mV (Che do CV)
        (12.0, 9.02, 3.00, 1.80),  # Tai nang keo 5.0A -> Phai tu ha ap ve 5.40V ghim dung 3.00A!
    ]
    res2 = conv_pps.simulate_sweep_and_pps(pps_stages)
    step_20mv_measured = (res2[1]["v_out"] - res2[0]["v_out"]) * 1000.0

    print(f"  * PPS Step 9.00V -> 9.02V (CV): Do duoc = +{step_20mv_measured:5.2f} mV (Muc tieu +20.0 mV)")
    print(
        f"  * Qua tai R=1.80 Ohm (I_lim=3A): CC_Mode={res2[2]['cc_active']} | "
        f"V_foldback={res2[2]['v_out']:5.2f}V | I_out={res2[2]['i_out']:5.3f}A"
    )

    assert abs(step_20mv_measured - 20.0) < 4.0 and not res2[1]["cc_active"]
    assert res2[2]["cc_active"] and abs(res2[2]["i_out"] - 3.00) < 0.08
    print("  -> Ket luan: PPS dat chinh xac 20 mV va tu dong ghim dong CC 3.00A an toan (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 214: 4-SWITCH BUCK-BOOST & PPS CV/CC HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_four_switch_buck_boost_pps()
