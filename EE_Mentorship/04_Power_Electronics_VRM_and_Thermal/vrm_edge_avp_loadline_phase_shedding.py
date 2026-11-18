"""
EE MENTORSHIP PROGRAM - MODULE BJ (NHOM 49) - BAI 194 (MILESTONE BJ.3)
================================================================================
DINH VI DIEN AP THICH NGHI AVP LOAD-LINE VA CAT PHA DONG ACTIVE PHASE SHEDDING
(ADAPTIVE VOLTAGE POSITIONING, ALL-PHASE QUICK RESPONSE & EFFICIENCY OPTIMIZATION)
================================================================================

Kien truc toi uu dien ap qua do va hieu suat toan dai cho VRM sieu dong:
1. Nguyen ly Dinh vi Dien ap Thich nghi (Adaptive Voltage Positioning - AVP Load-Line):
   - Dai dien ap an toan cua loi silicon so cap phep dao dong trong [V_min, V_max],
     vi du V_nom = 0.850V +/- 45 mV => [0.805 V .. 0.895 V] (tong cua so 90 mV).
   - Neu giu cung V_ref = 0.850V (Zero Load-Line), moi cu nhay tai hay nha tai
     chi duoc phep lech toi da NUA cua so (45 mV) -> Lang phi 50% ngan sach tu loc!
   - Voi AVP, bo VRM co tinh ha tuyen tinh dien ap theo dong tai voi tro khang ao R_LL:
     V_target(I_load) = V_no_load - R_LL * I_load
     + Khi khong tai (Idle): neo san o muc cao (~ 0.890V), san sang chiu sut ap
       nhay tai len 350A ma su dung TRON VEN cua so 85 mV xuong 0.805V!
     + Khi day tai (Full Load 350A): ha san xuong muc thap (~ 0.815V), san sang
       chot nha tai dot ngot ve 0A ma dung TRON VEN cua so len 0.895V khong qua ap!
   -> Ket qua kinh dien: Giam 50% so luong tu dien MLCC/Polymer dat tien tren PCB
      nhung van bao ve 100% chip khong bao gio vuot nguong V_min/V_max!

2. Co che Phuc hoi Sieu toc Toan Pha (Quick-Response All-Phase Turn-On):
   - Khi co nhay tai cuc manh dI/dt lon lam V_out tut qua nguong Comparator nhanh,
     bo dieu khien pha bo qua lech pha xen ke, kich dong thoi TAT CA cac pha
     song song de bom dong cuon cam voi dien cam hieu dung giam N lan: L_eq = L / N.

3. Cat Pha Dong Thong Minh co Tre (Active Phase Shedding with Hysteresis):
   - O muc tai thap (Idle 15A), giu ca 8 pha chay gay ton hao dong cat C_oss va
     Gate-Drive khong doi (~ 3.5W) lam hieu suat rot xuong ~ 77%.
   - Tu dong cat bot pha (8 -> 4 -> 2 -> 1 pha) theo nguong dong kem vong tre
     Hysteresis chong nhap nhay, giu hieu suat VRM tren 92% tu 15A toi 400A!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Phuong trinh duong tai AVP Load-Line (Adaptive Voltage Positioning):
                           V_max_tol - V_min_tol
     R_LL (Ohm) = ─────────────────────────────────────────
                               I_load_max
     V_target(I) = V_no_load - R_LL * I_load

2. Dien dung toi thieu khi nha tai dot ngot (Load-Dump Charge Conservation):
     * Khong AVP (Chi co V_tol / 2):      C_min_noAVP = (L_eq * I_step^2) / (V_out * V_tol)
     * Co AVP (Dung tron ven V_tol):     C_min_AVP   = 0.5 * C_min_noAVP  (Tiet kiem 50% tu!)

3. Ton hao he thong N_act pha hoat dong o dong tai I_load:
     I_ph = I_load / N_act
     P_loss = N_act * [ (I_ph^2 + I_pp^2/12) * R_cond + P_sw_fixed + P_sw_vi(I_ph) ]
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class AVPVRMConfig:
    """Tham so he thong VRM 8 pha ho tro AVP va Active Phase Shedding."""
    v_in: float = 12.0               # Dien ap dau vao 12.0 V
    v_nom: float = 0.850             # Dien ap danh dinh 0.850 V
    v_min_limit: float = 0.805       # Gioi han duoi silicon (-45 mV)
    v_max_limit: float = 0.895       # Gioi han tren silicon (+45 mV)
    num_phases_max: int = 8          # So pha cuc dai: 8 pha
    i_max_a: float = 350.0           # Dong dinh muc cuc dai: 350 A
    l_trans_h: float = 32.0e-9       # Dien cam qua do hieu dung TLVR/Coupled: 32 nH
    l_steady_h: float = 100.0e-9     # Dien cam xac lap tung pha: 100 nH
    r_dcr_ohm: float = 0.32e-3       # Dien tro DCR moi cuon cam
    r_hs_on_ohm: float = 1.40e-3     # R_ds(on) MOSFET tren (High-Side)
    r_ls_on_ohm: float = 0.55e-3     # R_ds(on) MOSFET duoi (Low-Side)
    c_out_f: float = 3800.0e-6       # Dan tu dau ra: 3,800 uF (tiet kiem mot nua nho AVP!)
    r_esr_ohm: float = 0.14e-3       # ESR tuong duong cua dan tu: 0.14 mOhm
    f_sw_hz: float = 600.0e3         # Tan so dong cat moi pha: 600 kHz
    q_g_total_c: float = 28.0e-9     # Tong dien tich cong gate 2 MOSFET/pha (nC)
    v_drv: float = 5.0               # Dien ap kich gate driver: 5.0 V
    c_oss_f: float = 1.2e-9          # Dien dung ngo ra ky sinh C_oss (F)
    t_sw_edge_s: float = 4.5e-9      # Thoi gian len/xuong canh xung dong cat (4.5 ns)


class AVPLoadLineDesigner:
    """Subsystem 1: Tinh toan tro khang Load-Line AVP va so sanh dung luong tu can thiet."""

    @staticmethod
    def compute_optimal_loadline(cfg: AVPVRMConfig) -> Dict[str, float]:
        """
        Thiet ke R_LL va dien ap neo khong tai V_no_load sao cho trong toan dai [0, I_max],
        V_out nam giua [v_min + ripple_margin, v_max - ripple_margin].
        """
        # Du phong 4 mV moi dau cho gon song dong cat + dung sai ADC
        guard_v = 0.004
        v_top = cfg.v_max_limit - guard_v      # 0.891 V tai I = 0
        v_bot = cfg.v_min_limit + guard_v      # 0.809 V tai I = I_max
        r_ll = (v_top - v_bot) / cfg.i_max_a

        # Dien dung toi thieu khi nha tai I_max -> 0 (Load Dump Conservation)
        l_eq = cfg.l_trans_h / cfg.num_phases_max
        v_tol_total = cfg.v_max_limit - cfg.v_min_limit
        c_min_no_avp = (l_eq * (cfg.i_max_a ** 2)) / (cfg.v_nom * v_tol_total)
        c_min_avp = 0.5 * c_min_no_avp

        return {
            "v_no_load_v": v_top,
            "v_full_load_v": v_bot,
            "r_ll_mohm": r_ll * 1000.0,
            "r_ll_ohm": r_ll,
            "c_min_no_avp_uf": c_min_no_avp * 1e6,
            "c_min_avp_uf": c_min_avp * 1e6,
            "cap_saving_pct": 50.0,
        }


class AVPTransientClosedLoopSim:
    """
    Subsystem 2: Mo phong vong kin qua do khi tai nhay bac 10A -> 350A -> 10A.
    So sanh truc tiep bo dieu ap Khong AVP (Zero Load-Line) vs Co AVP Current-Mode.
    """

    def __init__(self, cfg: AVPVRMConfig):
        self.cfg = cfg

    def simulate_load_step_burst(
        self,
        enable_avp: bool,
        r_ll_ohm: float,
        v_no_load: float,
        dt_s: float = 20.0e-9,
    ) -> Dict[str, float]:
        """
        Chay mo phong qua do trong 160 us voi buoc dt = 20 ns:
        - 0..20 us   : Tai nhe 10 A
        - 20..90 us  : Nhay tai cuc dai 350 A (toc do tang 1000 A/us)
        - 90..160 us : Nha tai dot ngot ve 10 A (toc do giam 1000 A/us)
        """
        total_time_s = 160.0e-6
        steps = int(total_time_s / dt_s)
        l_eq = self.cfg.l_trans_h / self.cfg.num_phases_max
        r_eq = (self.cfg.r_dcr_ohm + self.cfg.r_ls_on_ohm) / self.cfg.num_phases_max

        # Khoi tao trang thai xac lap tai 10 A
        i_load = 10.0
        i_ind = 10.0
        v_cap = (v_no_load - r_ll_ohm * i_load) if enable_avp else self.cfg.v_nom
        v_out = v_cap
        prev_v = v_out

        # Bien dieu khien cho che do Voltage-Mode khong AVP
        integ = v_cap / self.cfg.v_in

        v_min_seen = v_out
        v_max_seen = v_out
        quick_response_triggered = 0

        for step in range(steps):
            t = step * dt_s
            if t < 20.0e-6:
                i_load_target = 10.0
            elif t < 90.0e-6:
                i_load_target = 350.0
            else:
                i_load_target = 10.0

            max_di = 1000.0e6 * dt_s  # 1,000 A/us edge rate cua chip AI hien dai
            if abs(i_load_target - i_load) <= max_di:
                i_load = i_load_target
            elif i_load_target > i_load:
                i_load += max_di
            else:
                i_load -= max_di

            if enable_avp:
                # Current-Mode AVP: vong ngoai la do dan G_m = 1 / R_LL ra lenh dong I_cmd
                i_cmd = max(0.0, (v_no_load - v_out) / r_ll_ohm)
                i_err = i_cmd - i_ind
                if abs(i_err) > 40.0:
                    quick_response_triggered += 1
                duty = (v_out + i_ind * r_eq) / self.cfg.v_in + 0.015 * i_err
                duty = max(0.0, min(1.0, duty))
            else:
                # Bo dieu khien Voltage-Mode PID co dien giu cung V_nom
                v_err = self.cfg.v_nom - v_out
                dv_dt = (v_out - prev_v) / dt_s
                integ += 3.5e5 * v_err * dt_s
                integ = max(0.0, min(0.95, integ))
                duty = max(0.0, min(1.0, integ + 22.0 * v_err - 2.0e-5 * dv_dt))
                if duty == 1.0 or duty == 0.0:
                    quick_response_triggered += 1

            prev_v = v_out

            # Cap nhat dong cuon cam tuong duong N pha va tu dau ra
            di_dt = (duty * self.cfg.v_in - v_out - i_ind * r_eq) / l_eq
            i_ind = max(0.0, i_ind + di_dt * dt_s)

            i_cap = i_ind - i_load
            v_cap += (i_cap / self.cfg.c_out_f) * dt_s
            v_out = v_cap + i_cap * self.cfg.r_esr_ohm

            if v_out < v_min_seen:
                v_min_seen = v_out
            if v_out > v_max_seen:
                v_max_seen = v_out

        in_spec = (v_min_seen >= self.cfg.v_min_limit) and (v_max_seen <= self.cfg.v_max_limit)
        return {
            "v_min_seen_v": v_min_seen,
            "v_max_seen_v": v_max_seen,
            "total_swing_mv": (v_max_seen - v_min_seen) * 1000.0,
            "quick_response_ticks": quick_response_triggered,
            "in_spec": in_spec,
        }


class ActivePhaseSheddingManager:
    """
    Subsystem 3: Bo quan ly cat pha dong kem Hysteresis (Active Phase Shedding)
    va tinh toan hieu suat toan dai tai tu 15A den 350A.
    """

    def __init__(self, cfg: AVPVRMConfig):
        self.cfg = cfg
        self.current_phases = cfg.num_phases_max

    def update_active_phases(self, i_load_a: float) -> int:
        """
        Cap nhat so pha hoat dong (1, 2, 4, 8) voi vung tre Hysteresis
        de tranh hien tuong nhap nhay (Phase Chattering) tai bien nguong.
        """
        while True:
            n = self.current_phases
            next_n = n
            if n == 1:
                if i_load_a > 38.0:
                    next_n = 2
            elif n == 2:
                if i_load_a < 26.0:
                    next_n = 1
                elif i_load_a > 78.0:
                    next_n = 4
            elif n == 4:
                if i_load_a < 58.0:
                    next_n = 2
                elif i_load_a > 165.0:
                    next_n = 8
            elif n == 8:
                if i_load_a < 130.0:
                    next_n = 4
            self.current_phases = next_n
            if next_n == n:
                break
        return self.current_phases

    def compute_efficiency_pct(self, i_load_a: float, n_active: int, v_out_v: float = 0.85) -> Dict[str, float]:
        """
        Tinh chi tiet tung thanh phan ton hao (Conduction, Switching, Gate, Coss, Core)
        va hieu suat tong the eta (%) cua bo VRM.
        """
        duty = v_out_v / self.cfg.v_in
        i_ph = i_load_a / n_active
        delta_i_1 = (self.cfg.v_in - v_out_v) * duty / (self.cfg.l_steady_h * self.cfg.f_sw_hz)
        i_rms_sq = (i_ph ** 2) + (delta_i_1 ** 2) / 12.0

        r_mosfet_avg = duty * self.cfg.r_hs_on_ohm + (1.0 - duty) * self.cfg.r_ls_on_ohm
        r_total_phase = self.cfg.r_dcr_ohm + r_mosfet_avg

        p_cond = n_active * i_rms_sq * r_total_phase
        p_gate = n_active * self.cfg.q_g_total_c * self.cfg.v_drv * self.cfg.f_sw_hz
        p_coss = n_active * 0.5 * self.cfg.c_oss_f * (self.cfg.v_in ** 2) * self.cfg.f_sw_hz
        p_sw_overlap = n_active * 0.5 * self.cfg.v_in * i_ph * (2.0 * self.cfg.t_sw_edge_s) * self.cfg.f_sw_hz
        p_core = n_active * 0.10  # Ton hao tu tre loi ferit moi pha (~0.10W @ 600kHz)

        p_loss_total = p_cond + p_gate + p_coss + p_sw_overlap + p_core
        p_out = v_out_v * i_load_a
        eff_pct = (p_out / (p_out + p_loss_total)) * 100.0
        return {
            "n_active": n_active,
            "p_out_w": p_out,
            "p_loss_w": p_loss_total,
            "efficiency_pct": eff_pct,
        }


def test_avp_loadline_and_phase_shedding():
    """Chuong trinh kiem thu toan dien AVP Load-Line va Cat pha dong."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BJ (NHOM 49) - BAI 194 (MILESTONE BJ.3)")
    print("DINH VI DIEN AP THICH NGHI AVP LOAD-LINE & CAT PHA DONG PHASE SHEDDING")
    print("=" * 80)

    cfg = AVPVRMConfig()

    # 1. Thiet ke duong tai AVP Load-Line & Uoc tinh tiet kiem tu loc PCB
    print("\n[1] Thiet ke thong so duong tai AVP Load-Line [0.805V .. 0.895V]:")
    avp_design = AVPLoadLineDesigner.compute_optimal_loadline(cfg)
    print(f"  * Dien ap khong tai (I=0A)  : {avp_design['v_no_load_v']:.4f} V")
    print(f"  * Dien ap day tai (I=350A)  : {avp_design['v_full_load_v']:.4f} V")
    print(f"  * Tro khang ao R_LL         : {avp_design['r_ll_mohm']:.4f} mOhm")
    print(f"  * Tu toi thieu (Khong AVP)  : {avp_design['c_min_no_avp_uf']:7.1f} uF")
    print(f"  * Tu toi thieu (Co AVP)     : {avp_design['c_min_avp_uf']:7.1f} uF (Tiet kiem {avp_design['cap_saving_pct']:.0f}% tu!)")

    c_pcb_uf = cfg.c_out_f * 1e6
    assert avp_design["c_min_avp_uf"] < c_pcb_uf < avp_design["c_min_no_avp_uf"], (
        f"Loi: Dan tu {c_pcb_uf}uF phai du cho AVP nhung thieu cho he thuong!"
    )
    print("  -> Ket luan: AVP giam mot nua dung luong tu loc PCB bat buoc (PASS)!")

    # 2. Kiem thu qua do 10A <-> 350A voi dan tu 3,800 uF (Khong AVP vs Co AVP)
    print(f"\n[2] Mo phong qua do nhay tai 10A -> 350A -> 10A (Dan tu C_out = {c_pcb_uf:,.0f} uF):")
    sim = AVPTransientClosedLoopSim(cfg)
    res_no_avp = sim.simulate_load_step_burst(enable_avp=False, r_ll_ohm=0.0, v_no_load=cfg.v_nom)
    res_avp = sim.simulate_load_step_burst(
        enable_avp=True, r_ll_ohm=avp_design["r_ll_ohm"], v_no_load=avp_design["v_no_load_v"]
    )

    print(
        f"  * KHONG AVP (Zero LL): V_min = {res_no_avp['v_min_seen_v']:.4f} V | "
        f"V_max = {res_no_avp['v_max_seen_v']:.4f} V | Swing = {res_no_avp['total_swing_mv']:5.1f} mV -> "
        f"{'PASS' if res_no_avp['in_spec'] else 'VI PHAM NGUONG AP!'}"
    )
    print(
        f"  * CO AVP Load-Line   : V_min = {res_avp['v_min_seen_v']:.4f} V | "
        f"V_max = {res_avp['v_max_seen_v']:.4f} V | Swing = {res_avp['total_swing_mv']:5.1f} mV -> "
        f"{'AN TOAN 100% TRONG SPEC!' if res_avp['in_spec'] else 'VI PHAM!'}"
    )

    assert not res_no_avp["in_spec"], f"Loi: Khi dung {c_pcb_uf}uF va khong co AVP, he thong phai vi pham nguong!"
    assert res_avp["in_spec"], (
        f"Loi: He AVP phai giu dien ap trong [{cfg.v_min_limit}, {cfg.v_max_limit}] nhung do duoc "
        f"[{res_avp['v_min_seen_v']:.4f}, {res_avp['v_max_seen_v']:.4f}]!"
    )
    print(f"  -> Ket luan: Cung dan tu {c_pcb_uf:,.0f}uF, AVP triet tieu 100% loi vuot ap/sut ap (PASS)!")

    # 3. Kiem thu hieu suat toan dai & vung tre Hysteresis cua Active Phase Shedding
    print("\n[3] Kiem thu Cat pha dong Active Phase Shedding (15A -> 350A):")
    shedder = ActivePhaseSheddingManager(cfg)
    shedder.current_phases = 8
    load_profile = [15.0, 30.0, 50.0, 120.0, 250.0, 350.0]
    for i_ld in load_profile:
        # Cho thay doi huong di xuong/di len hop ly
        n_opt = shedder.update_active_phases(i_ld)
        eff_all8 = shedder.compute_efficiency_pct(i_ld, n_active=8)
        eff_shed = shedder.compute_efficiency_pct(i_ld, n_active=n_opt)
        print(
            f"  * Tai {i_ld:5.1f}A | Luon bat 8 pha: {eff_all8['efficiency_pct']:5.2f}% "
            f"| Active Shedding ({n_opt} pha): {eff_shed['efficiency_pct']:5.2f}%"
        )

    # Kiem tra rieng tai 15A (phai giam ve 1 pha va tang hieu suat > 9.0%)
    shedder.current_phases = 2
    n_idle = shedder.update_active_phases(15.0)
    eff_8_15a = shedder.compute_efficiency_pct(15.0, 8)["efficiency_pct"]
    eff_shed_15a = shedder.compute_efficiency_pct(15.0, n_idle)["efficiency_pct"]

    # Kiem tra Hysteresis chong nhap nhay quanh nguong 32A (tu 1 pha -> 32A van giu 1 pha, tu 2 pha -> 32A van giu 2 pha)
    shedder.current_phases = 1
    stay_1 = shedder.update_active_phases(32.0)
    shedder.current_phases = 2
    stay_2 = shedder.update_active_phases(32.0)

    assert n_idle == 1 and eff_shed_15a > 92.0 and (eff_shed_15a - eff_8_15a) > 9.0
    assert stay_1 == 1 and stay_2 == 2, "Loi: Vong tre Hysteresis khong ngan chan duoc chattering tai 32A!"
    print("  -> Ket luan: Cat pha dong nang hieu suat Idle tu 83.6% len 93.1% va chong chattering 100% (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 194: AVP LOAD-LINE & ACTIVE PHASE SHEDDING 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_avp_loadline_and_phase_shedding()
