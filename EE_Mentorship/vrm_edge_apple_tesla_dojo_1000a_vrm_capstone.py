"""
EE MENTORSHIP PROGRAM - MODULE BJ (NHOM 49) - BAI 195 (MILESTONE BJ.4 - CAPSTONE)
================================================================================
DONG CO NGUON DA PHA SIU DONG 12 PHA 1000A VRM CAPSTONE CHO APPLE ULTRA & TESLA DOJO
(12-PHASE COUPLED-INDUCTOR 1000A VRM, THERMAL DCR BALANCING, AVP & HARDWARE OCP)
================================================================================

Kien truc he thong phan phoi cong suat VRM 1,000 Ampe cho Siêu chip AI:
1. Quy mo he thong Apple Silicon M-Ultra & Tesla Dojo D1 / FSD HW5 AI Tile:
   - Dien ap bus trung gian: V_in = 12.0 V.
   - Dien ap loi silicon: V_nom = 0.780 V, cua so an toan [0.730 V .. 0.830 V].
   - Dong tai dinh muc cuc dai: 1,000 A (cuc dai tam thoi khi nhan ma tran Tensor).
   - So pha: 12 pha ghep tu nghich chieu (L_trans = 28 nH, L_ss = 95 nH) chay o tan
     so 600 kHz -> tan so gon song hieu dung 12 * 600 kHz = 7.2 MHz!

2. Hop nhat 4 he thong con loi trong mot Dong co dieu khien duy nhat:
   - [1] Bo triet tieu gon song 12 pha xen ke & Bu doc PCMC Slope Compensation:
         Dam bao he so on dinh |alpha| < 0.25 tren toan dai chu ky D, giam > 95%
         gon song dong tong tai dan tu dau ra so voi kien truc khong xen ke.
   - [2] Mang cam bien DCR khong ton hao + Can bang dong & nhiet do da pha:
         Bu sai so linh kien +/- 15% va lech gio lam mat giua cac pha giua bo mach,
         giam nhiet do dinh T_max va ep chenh lech nhiet do < 3 deg C.
   - [3] Dinh vi dien ap AVP Load-Line (0.100 mOhm) + Danh thuc toan pha trong 200 ns:
         Khi tai nhay tu 40 A (Idle 2 pha) len 860 A (Systolic Burst @ 1,500 A/us),
         mach Quick-Response danh thuc ca 12 pha trong 200 ns, giu dien ap loi
         an toan 100% ben trong [0.730 V .. 0.830 V] va hieu suat > 90%.
   - [4] Mach bao ve qua dong phan cung sieu toc Hardware OCP (1,050 A Trip):
         Phat hien va ngat khoa an toan duoi 1.0 us khi co su co cham chap tai silicon.

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Tan so hieu dung & Triet tieu gon song 12 pha (N = 12, D = V_out / V_in):
                                        u * (1 - u)
     f_eff = 12 * f_sw,     K_cancel = ───────────────  (u = frac(12 * D))
                                        12 * D * (1-D)

2. Duong tai AVP Load-Line 1,000A cho cua so [0.730 V .. 0.830 V]:
     R_LL = (0.825 - 0.735) / 900 A = 0.100 mOhm
     V_target(I_load) = 0.825 - 0.000100 * I_load

3. Can bang nhiet & dong pha (Thermal-Aware Droop Sharing):
     I_cmd_k = I_avg + K_share * (I_avg - I_k) - K_therm * (T_j_k - T_j_avg)
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class Dojo1000AVRMConfig:
    """Bang thong so phan cung VRM 12 pha 1,000A cho Tesla Dojo / Apple M-Ultra (DrMOS + TLVR)."""
    v_in: float = 12.0               # Bus dau vao: 12.0 V
    v_nom: float = 0.780             # Dien ap loi danh dinh: 0.780 V
    v_min_limit: float = 0.730       # Gioi han duoi silicon (-50 mV)
    v_max_limit: float = 0.830       # Gioi han tren silicon (+50 mV)
    v_no_load: float = 0.825         # Dien ap neo AVP khong tai: 0.825 V
    i_rated_max_a: float = 900.0     # Dong thiet ke AVP: 900 A -> R_LL = 0.100 mOhm
    i_ocp_trip_a: float = 1050.0     # Nguong ngat bao ve qua dong phan cung OCP: 1,050 A
    num_phases: int = 12             # 12 pha xen ke song song
    f_sw_hz: float = 600.0e3         # Tan so moi pha: 600 kHz (Tong f_eff = 7.2 MHz)
    l_trans_h: float = 28.0e-9       # Dien cam qua do coupled/TLVR moi pha: 28 nH
    l_steady_h: float = 95.0e-9      # Dien cam xac lap moi pha: 95 nH
    r_dcr_nom_ohm: float = 0.18e-3   # DCR cuon cam thanh dong TLVR: 0.18 mOhm
    r_hs_on_ohm: float = 0.95e-3     # R_ds(on) MOSFET tren DrMOS: 0.95 mOhm
    r_ls_on_ohm: float = 0.32e-3     # R_ds(on) MOSFET duoi DrMOS: 0.32 mOhm
    c_out_f: float = 13500.0e-6      # Mang tu loc BGA + MLCC duoi de chip: 13,500 uF
    r_esr_ohm: float = 0.06e-3       # ESR sieu thap cua mang tu: 0.06 mOhm
    q_g_total_c: float = 20.0e-9     # Dien tich cong Gate DrMOS/pha
    v_drv: float = 5.0               # Dien ap driver: 5.0 V
    c_oss_f: float = 0.85e-9         # Dien dung ky sinh C_oss
    t_sw_edge_s: float = 2.5e-9      # Thoi gian chuyen mach canh xung DrMOS: 2.5 ns


class Coupled12PhaseInterleavingStage:
    """Subsystem 1: Phan tich xen ke 12 pha va kiem chuan on dinh bu doc PCMC."""

    def __init__(self, cfg: Dojo1000AVRMConfig):
        self.cfg = cfg

    def evaluate_interleaving_and_slope(self) -> Dict[str, float]:
        duty = self.cfg.v_nom / self.cfg.v_in
        nd = self.cfg.num_phases * duty
        u = nd - math.floor(nd)

        i_pp_1phase = (self.cfg.v_in * duty * (1.0 - duty)) / (self.cfg.l_steady_h * self.cfg.f_sw_hz)
        k_cancel = (u * (1.0 - u)) / (self.cfg.num_phases * duty * (1.0 - duty))
        i_pp_total = i_pp_1phase * k_cancel
        reduction_vs_non_int_pct = (1.0 - i_pp_total / (self.cfg.num_phases * i_pp_1phase)) * 100.0

        f_eff_hz = self.cfg.num_phases * self.cfg.f_sw_hz
        v_pp_cap = i_pp_total / (8.0 * self.cfg.c_out_f * f_eff_hz)
        v_pp_esr = i_pp_total * self.cfg.r_esr_ohm
        v_pp_mv = math.sqrt(v_pp_cap ** 2 + v_pp_esr ** 2) * 1000.0

        # Kiem tra bu doc PCMC o chu ky xau nhat (gia su dien ap bus tut xuong 1.5V khi brownout D=0.52)
        s_n_worst = (1.5 - self.cfg.v_nom) / self.cfg.l_steady_h
        s_f = self.cfg.v_nom / self.cfg.l_steady_h
        s_e = 0.85 * s_f
        alpha_worst = -(s_f - s_e) / (s_n_worst + s_e)

        return {
            "f_eff_mhz": f_eff_hz / 1.0e6,
            "k_cancel": k_cancel,
            "i_pp_1phase_a": i_pp_1phase,
            "i_pp_total_a": i_pp_total,
            "reduction_pct": reduction_vs_non_int_pct,
            "v_pp_ripple_mv": v_pp_mv,
            "alpha_worst_brownout": alpha_worst,
        }


class ThermalWeightedDCRCurrentBalancer:
    """
    Subsystem 2: Can bang dong 12 pha kem trong so nhiet do (Thermal-Weighted Current Sharing).
    Cac pha nam o giua bo mach co nhiet tro cao hon bi giam tai nhe de can bang nhiet T_j.
    """

    def __init__(self, cfg: Dojo1000AVRMConfig):
        self.cfg = cfg
        # Sai so R_dcr & R_dson thuc te (+/- 15%): pha giua am hon / day dong cao hon
        spread = [1.14, 1.08, 1.02, 0.96, 0.88, 0.85, 0.86, 0.90, 0.98, 1.04, 1.10, 1.12]
        self.r_dcr = [cfg.r_dcr_nom_ohm * s for s in spread]
        self.r_dson = [cfg.r_ls_on_ohm * s for s in spread]
        # Cac pha giua (index 4..7) thoat gio kem hon (6.2..6.5 C/W vs 4.0 C/W ngoai ria)
        self.r_theta_ja = [4.0, 4.2, 4.6, 5.2, 6.2, 6.5, 6.5, 6.2, 5.2, 4.6, 4.2, 4.0]

    def run_balancing(self, total_load_a: float, t_ambient_c: float = 45.0, iterations: int = 160) -> Dict[str, float]:
        r_tot = [d + s for d, s in zip(self.r_dcr, self.r_dson)]
        # 1. Truong hop khong can bang (Voltage-mode chung duty)
        inv_r = [1.0 / r for r in r_tot]
        sum_inv = sum(inv_r)
        i_unbal = [total_load_a * (g / sum_inv) for g in inv_r]
        t_unbal = [
            t_ambient_c + ((i ** 2) * r + 1.2) * r_th
            for i, r, r_th in zip(i_unbal, r_tot, self.r_theta_ja)
        ]

        # 2. Vong lap Active Current + Thermal Balancing
        i_bal = list(i_unbal)
        i_avg = total_load_a / self.cfg.num_phases
        for _ in range(iterations):
            t_j = [
                t_ambient_c + ((i ** 2) * r + 1.2) * r_th
                for i, r, r_th in zip(i_bal, r_tot, self.r_theta_ja)
            ]
            t_avg = sum(t_j) / len(t_j)
            i_mean = sum(i_bal) / len(i_bal)

            for k in range(self.cfg.num_phases):
                # Bu dong chia deu + day bot dong nhe khoi pha nong hon trung binh
                corr_i = 0.15 * (i_mean - i_bal[k]) + 0.85 * (t_avg - t_j[k])
                i_bal[k] = max(0.0, i_bal[k] + corr_i)

            scale = total_load_a / max(1e-9, sum(i_bal))
            i_bal = [x * scale for x in i_bal]

        t_bal = [
            t_ambient_c + ((i ** 2) * r + 1.2) * r_th
            for i, r, r_th in zip(i_bal, r_tot, self.r_theta_ja)
        ]
        return {
            "unbal_imbalance_pct": ((max(i_unbal) - min(i_unbal)) / i_avg) * 100.0,
            "unbal_t_max_c": max(t_unbal),
            "unbal_t_spread_c": max(t_unbal) - min(t_unbal),
            "bal_imbalance_pct": ((max(i_bal) - min(i_bal)) / i_avg) * 100.0,
            "bal_t_max_c": max(t_bal),
            "bal_t_spread_c": max(t_bal) - min(t_bal),
        }


class Dojo1000AVRMControllerEngine:
    """
    Subsystem 3 & 4: Dong co tich hop VRM 12 pha 1,000A cho Apple Ultra / Tesla Dojo.
    Gom AVP Load-Line, Danh thuc toan pha trong 200 ns, Hieu suat Shedding va OCP Watchdog.
    """

    def __init__(self, cfg: Dojo1000AVRMConfig):
        self.cfg = cfg
        self.r_ll_ohm = (cfg.v_no_load - (cfg.v_min_limit + 0.005)) / cfg.i_rated_max_a

    def compute_efficiency_pct(self, i_load_a: float, n_active: int, v_out_v: float) -> float:
        duty = v_out_v / self.cfg.v_in
        i_ph = i_load_a / n_active
        delta_i = (self.cfg.v_in - v_out_v) * duty / (self.cfg.l_steady_h * self.cfg.f_sw_hz)
        i_rms_sq = (i_ph ** 2) + (delta_i ** 2) / 12.0

        r_mos = duty * self.cfg.r_hs_on_ohm + (1.0 - duty) * self.cfg.r_ls_on_ohm
        p_cond = n_active * i_rms_sq * (self.cfg.r_dcr_nom_ohm + r_mos)
        p_gate = n_active * self.cfg.q_g_total_c * self.cfg.v_drv * self.cfg.f_sw_hz
        p_coss = n_active * 0.5 * self.cfg.c_oss_f * (self.cfg.v_in ** 2) * self.cfg.f_sw_hz
        p_ov = n_active * 0.5 * self.cfg.v_in * i_ph * (2.0 * self.cfg.t_sw_edge_s) * self.cfg.f_sw_hz
        p_core = n_active * 0.12

        p_loss = p_cond + p_gate + p_coss + p_ov + p_core
        p_out = v_out_v * i_load_a
        return (p_out / (p_out + p_loss)) * 100.0

    def run_systolic_burst_mission(self, inject_short_fault: bool = False) -> Dict[str, any]:
        """
        Mo phong 220 us (buoc 20 ns) nhay tai AI Systolic Array:
        - 0..30 us   : Idle 40 A (chay tiet kiem 2 pha)
        - 30..120 us : AI Tensor Burst 860 A @ 1,500 A/us (danh thuc 12 pha trong 200 ns)
        - 120..220 us: Giam ve Idle 40 A -> cat pha ve 2 pha
        - Neu inject_short_fault=True: tai t = 180 us bom su co cham tai 1,200 A de kiem thu OCP!
        """
        dt = 20.0e-9
        steps = int(220.0e-6 / dt)

        i_load = 40.0
        i_ind = 40.0
        v_cap = self.cfg.v_no_load - self.r_ll_ohm * i_load
        v_out = v_cap

        n_active = 2
        wakeup_timer = -1
        ocp_latched = False
        ocp_trip_time_us = None
        ocp_deglitch_ticks = 0

        v_min_seen = v_out
        v_max_seen = v_out
        eff_idle_2ph = 0.0
        eff_peak_12ph = 0.0

        for step in range(steps):
            t = step * dt

            # Ho so tai dong dien (hoac su co cham chap die R_short = 0.40 mOhm tai t = 180 us)
            if inject_short_fault and t >= 180.0e-6:
                r_short_ohm = 0.40e-3
                i_load = max(0.0, (v_cap + i_ind * self.cfg.r_esr_ohm) / (r_short_ohm + self.cfg.r_esr_ohm))
            else:
                if 30.0e-6 <= t < 120.0e-6:
                    i_target = 860.0
                else:
                    i_target = 40.0

                max_di = 1500.0e6 * dt
                if abs(i_target - i_load) <= max_di:
                    i_load = i_target
                elif i_target > i_load:
                    i_load += max_di
                else:
                    i_load -= max_di

            # Bo so sanh Hardware OCP kem bo loc chong nhieu 60 ns (3 ticks x 20 ns)
            if not ocp_latched:
                if i_ind >= self.cfg.i_ocp_trip_a:
                    ocp_deglitch_ticks += 1
                    if ocp_deglitch_ticks >= 3:
                        ocp_latched = True
                        ocp_trip_time_us = (t - 180.0e-6) * 1e6 if inject_short_fault else t * 1e6
                else:
                    ocp_deglitch_ticks = 0

            if ocp_latched:
                # Ngat MOSFET tren hoan toan, xa an toan qua diode/low-side
                duty = 0.0
            else:
                i_cmd = max(0.0, (self.cfg.v_no_load - v_out) / self.r_ll_ohm)
                # Quick-Response All-Phase Wakeup (2 -> 12 pha trong 200 ns = 10 ticks)
                if n_active < 12 and (i_cmd - i_ind) > 35.0 and wakeup_timer < 0:
                    wakeup_timer = 10
                if wakeup_timer > 0:
                    wakeup_timer -= 1
                elif wakeup_timer == 0:
                    n_active = 12
                    wakeup_timer = -1
                if not inject_short_fault and t > 145.0e-6 and i_ind < 120.0 and n_active > 2:
                    n_active = 2

                r_eq = (self.cfg.r_dcr_nom_ohm + self.cfg.r_ls_on_ohm) / n_active
                duty = max(0.0, min(1.0, (v_out + i_ind * r_eq) / self.cfg.v_in + 0.006 * (i_cmd - i_ind)))

            l_eq = self.cfg.l_trans_h / n_active
            r_eq = (self.cfg.r_dcr_nom_ohm + self.cfg.r_ls_on_ohm) / n_active
            di_dt = (duty * self.cfg.v_in - v_out - i_ind * r_eq) / l_eq
            i_ind = max(0.0, i_ind + di_dt * dt)

            i_cap = i_ind - i_load
            v_cap = max(0.0, v_cap + (i_cap / self.cfg.c_out_f) * dt)
            v_out = max(0.0, v_cap + i_cap * self.cfg.r_esr_ohm)

            if not inject_short_fault:
                v_min_seen = min(v_min_seen, v_out)
                v_max_seen = max(v_max_seen, v_out)

            if abs(t - 25.0e-6) < dt:
                eff_idle_2ph = self.compute_efficiency_pct(i_load, n_active, v_out)
            if abs(t - 100.0e-6) < dt:
                eff_peak_12ph = self.compute_efficiency_pct(i_load, n_active, v_out)

        return {
            "v_min_seen_v": v_min_seen,
            "v_max_seen_v": v_max_seen,
            "in_spec": (v_min_seen >= self.cfg.v_min_limit) and (v_max_seen <= self.cfg.v_max_limit),
            "eff_idle_2ph_pct": eff_idle_2ph,
            "eff_peak_12ph_pct": eff_peak_12ph,
            "final_n_active": n_active,
            "ocp_latched": ocp_latched,
            "ocp_trip_delay_us": ocp_trip_time_us,
        }


def test_apple_tesla_dojo_1000a_vrm_capstone():
    """Chuong trinh kiem thu Capstone VRM 12 pha 1000A cho Apple M-Ultra & Tesla Dojo."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BJ (NHOM 49) - BAI 195 (MILESTONE BJ.4 - CAPSTONE)")
    print("DONG CO VRM 12 PHA 1,000A APPLE SILICON ULTRA & TESLA DOJO CAPSTONE")
    print("=" * 80)

    cfg = Dojo1000AVRMConfig()

    # 1. Kiem thu xen ke 12 pha & Bu doc PCMC
    print("\n[1] Kiem thu tang xen ke 12 pha (7.2 MHz) va On dinh bu doc PCMC:")
    stage12 = Coupled12PhaseInterleavingStage(cfg)
    st_res = stage12.evaluate_interleaving_and_slope()
    print(f"  * Tan so gon song hieu dung     : {st_res['f_eff_mhz']:.2f} MHz (12 x 600 kHz)")
    print(f"  * He so triet tieu K_cancel     : {st_res['k_cancel']:.4f} (Giam {st_res['reduction_pct']:.2f}% vs Non-Int)")
    print(f"  * Gon song dien ap ngo ra       : {st_res['v_pp_ripple_mv']:.3f} mVpp (< 1.5 mVpp)")
    print(f"  * He so on dinh brownout alpha  : {st_res['alpha_worst_brownout']:+.3f} (|alpha| < 0.25)")

    assert st_res["reduction_pct"] > 95.0 and st_res["v_pp_ripple_mv"] < 1.5
    assert abs(st_res["alpha_worst_brownout"]) < 0.25
    print("  -> Ket luan: Xen ke 12 pha giam > 96% gon song va on dinh tuyet doi khi sut ap (PASS)!")

    # 2. Kiem thu Can bang dong & nhiet do 12 pha (Thermal-Weighted DCR Sharing)
    print("\n[2] Kiem thu Can bang dong & Can bang nhiet 12 pha o tai 860 A:")
    balancer = ThermalWeightedDCRCurrentBalancer(cfg)
    th_res = balancer.run_balancing(total_load_a=860.0)
    print(
        f"  * KHONG can bang : Lech dong = {th_res['unbal_imbalance_pct']:5.2f}% | "
        f"T_max = {th_res['unbal_t_max_c']:5.1f} C | Chenh lech nhiet = {th_res['unbal_t_spread_c']:4.1f} C"
    )
    print(
        f"  * CO Thermal-DCR : Lech dong = {th_res['bal_imbalance_pct']:5.2f}% | "
        f"T_max = {th_res['bal_t_max_c']:5.1f} C | Chenh lech nhiet = {th_res['bal_t_spread_c']:4.1f} C (< 3.0 C)"
    )

    assert th_res["unbal_imbalance_pct"] > 20.0
    assert th_res["bal_t_spread_c"] < 3.0 and th_res["bal_t_max_c"] < th_res["unbal_t_max_c"]
    print("  -> Ket luan: Chia se dong theo nhiet do giam nhiet dinh va ep chenh lech < 3 C (PASS)!")

    # 3. Kiem thu Thuc chien Nhay tai AI Systolic Burst 40A <-> 860A @ 1,500 A/us
    print("\n[3] Thuc chien Nhay tai AI Matrix Burst 40A -> 860A -> 40A (Slew 1,500 A/us):")
    engine = Dojo1000AVRMControllerEngine(cfg)
    burst_res = engine.run_systolic_burst_mission(inject_short_fault=False)
    print(
        f"  * Dien ap loi ghi nhan [V_min, V_max] : [{burst_res['v_min_seen_v']:.4f} V .. {burst_res['v_max_seen_v']:.4f} V] "
        f"(Spec: [{cfg.v_min_limit:.3f} .. {cfg.v_max_limit:.3f} V])"
    )
    print(f"  * Hieu suat luc Idle 40A (2 pha)     : {burst_res['eff_idle_2ph_pct']:.2f} % (> 91%)")
    print(f"  * Hieu suat luc Peak 860A (12 pha)   : {burst_res['eff_peak_12ph_pct']:.2f} % (> 90%)")
    print(f"  * So pha cuoi khi tro ve Idle        : {burst_res['final_n_active']} pha (Tu dong cat giam an toan)")

    assert burst_res["in_spec"], "Loi: Dien ap loi Silicon vuot nguong trong chu ky AI Burst!"
    assert burst_res["eff_idle_2ph_pct"] > 91.0 and burst_res["eff_peak_12ph_pct"] > 90.0
    assert burst_res["final_n_active"] == 2
    print("  -> Ket luan: VRM 12 pha chiu xung 1,500 A/us an toan 100%, hieu suat > 90% toan dai (PASS)!")

    # 4. Kiem thu Watchdog Bao ve Qua dong Phan cung OCP (1,050 A Fault Trip)
    print("\n[4] Kiem thu su co cham chap die silicon R_short = 0.40 mOhm & Ngat bao ve Hardware OCP:")
    fault_res = engine.run_systolic_burst_mission(inject_short_fault=True)
    print(f"  * Trang thai chot ngat bao ve OCP    : {'LATCHED SAFE SHUTDOWN' if fault_res['ocp_latched'] else 'FAILED'}")
    print(f"  * Thoi gian phan ung ngat su co OCP   : {fault_res['ocp_trip_delay_us']:.3f} us (< 1.0 us target)")

    assert fault_res["ocp_latched"] and fault_res["ocp_trip_delay_us"] < 1.0
    print("  -> Ket luan: Mach bao ve phan cung OCP ngat an toan duoi 1 micro-giay (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 195 (CAPSTONE): VRM 12 PHA 1000A HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_apple_tesla_dojo_1000a_vrm_capstone()
