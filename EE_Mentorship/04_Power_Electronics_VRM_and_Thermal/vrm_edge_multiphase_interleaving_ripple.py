"""
EE MENTORSHIP PROGRAM - MODULE BJ (NHOM 49) - BAI 192 (MILESTONE BJ.1)
================================================================================
KIEN TRUC NGUON DA PHA XEN KE MULTI-PHASE VRM VA TRIET TIEU GON SONG DONG DIEN
(MULTI-PHASE INTERLEAVED BUCK TOPOLOGY, RIPPLE CANCELLATION & COUPLED INDUCTORS)
================================================================================

Kien truc cung cap nguon sieu dong cho sieu chip AI (Apple Silicon Ultra / Tesla Dojo):
1. Thach thuc dong dien 500 A .. 1,000 A o dien ap 0.75 V:
   - Mot mach Buck don pha (1-Phase) khong the chiu noi dong tai 1,000 A do bao hoa
     tu thong loi ferit, ton hao dong I^2 * R_dc qua lon va gon song tu dau ra khong lo.
   - Giai phap cong nghiep: Mach Buck Da Pha Xen Ke (N-Phase Interleaved VRM, N = 8..16 pha)
     mac song song, kich xung lech pha nhau dung mot goc 360 / N do.

2. Hieu ung Triet Tieu Gon Song Dong Dien (Interleaved Ripple Cancellation):
   - Khi N pha lech nhau deu 1/N chu ky T_sw, tan so gon song tong tai tu dau ra
     tang gap N lan: f_eff = N * f_sw.
   - Cac suon tang va giam cua dong dien qua tung cuon cam triet tieu lan nhau.
   - Dac biet tai cac he so chu ky dac trung D = k / N (vi du V_out = 1.5V, V_in = 12V
     voi N = 8 pha -> D = 1/8), gon song tong bi triet tieu ve 0 Ampe tuyet doi!

3. Cuon cam ghep nghich chieu (Inverse-Coupled Inductors):
   - Ghep tu tinh 2 cuon cam ke nhau nguoc chieu voi he so ghep k_c (0.5 .. 0.85).
   - O trang thai xac lap (Steady-state), tu thong triet tieu giam gon song pha, giam ton
     hao loi sat va ton hao dan MOSFET.
   - O trang thai qua do (Load Step Transient) khi ca 2 pha dong thoi bat hoac tat,
     dien cam hieu dung giam xuong L_trans = L * (1 - k_c), tang toc do dap ung dI/dt
     len gap 2 den 4 lan!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. He so triet tieu gon song dong dien chuan hoa (Normalized Ripple Ratio):
     Goi m = floor(N * D) va u = N * D - m (phan le cua N * D):

                          u * (1 - u)
     K_cancel(N, D) = ─────────────────────
                        N * D * (1 - D)

2. Gon song dien ap ngo ra voi tu dien loc (ESR + Capacitive Ripple):
                      Delta_I_total                     Delta_I_total
     Delta_V_out = ────────────────────── + sqrt(...) ~ ─────────────── + Delta_I_total * R_esr
                     8 * C_out * (N * f_sw)               8 * C * N * f_sw

3. Phuong trinh vi phan cuon cam ghep nghich chieu 2 pha (Inverse Coupled):
     [ v1 ]   [  L   -M ] [ di1 / dt ]         M = k_c * L
     [ v2 ] = [ -M    L ] [ di2 / dt ]
     Dien cam qua do (Transient Inductance): L_trans = L * (1 - k_c)
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class MultiPhaseVRMParams:
    """Tham so phan cung bo nguon da pha VRM."""
    v_in: float = 12.0              # Dien ap bus dau vao: 12.0 V
    v_out: float = 0.85             # Dien ap loi silicon muc tieu: 0.85 V
    num_phases: int = 8             # So pha hoat dong song song (N = 8 pha)
    f_sw_hz: float = 600.0e3        # Tan so dong cat moi pha: 600 kHz
    inductance_h: float = 120.0e-9  # Dien cam moi pha: 120 nH
    r_dcr_ohm: float = 0.35e-3      # Dien tro noi tiep cuon cam DCR: 0.35 mOhm
    c_out_f: float = 4000.0e-6      # Tong dien dung tu dau ra: 4,000 uF (MLCC + Bulk)
    r_esr_ohm: float = 0.15e-3      # Dien tro ESR tuong duong cua dan tu: 0.15 mOhm
    i_load_a: float = 320.0         # Dong tai DC tieu thu boi chip: 320 A (40A/pha)


class RippleCancellationAnalyzer:
    """
    Subsystem 1: Phan tich giai tich hieu ung triet tieu gon song va chon so pha toi uu.
    """

    @staticmethod
    def single_phase_ripple_a(v_in: float, v_out: float, l_h: float, f_sw_hz: float) -> float:
        """
        Tinh bien do gon song dinh-dinh (peak-to-peak) cua 1 pha don le:
        Delta_I_1 = V_in * D * (1 - D) / (L * f_sw)
        """
        duty = v_out / v_in
        return (v_in * duty * (1.0 - duty)) / (l_h * f_sw_hz)

    @staticmethod
    def normalized_cancellation_factor(num_phases: int, duty: float) -> float:
        """
        Tinh ty so triet tieu gon song K_cancel = Delta_I_total / Delta_I_1.
        K_cancel = [u * (1 - u)] / [N * D * (1 - D)] voi u = frac(N * D).
        Khi N * D la so nguyen, K_cancel = 0 (triet tieu 100% gon song dong dien).
        """
        if duty <= 0.0 or duty >= 1.0:
            return 0.0
        nd = num_phases * duty
        m = math.floor(nd)
        u = nd - m
        # Kiem tra truong hop gan so nguyen do sai so dau phay dong
        if abs(u) < 1e-12 or abs(u - 1.0) < 1e-12:
            return 0.0
        denom = num_phases * duty * (1.0 - duty)
        return (u * (1.0 - u)) / denom

    @classmethod
    def total_output_ripple_a(cls, p: MultiPhaseVRMParams) -> Dict[str, float]:
        """Tinh chi tiet gon song don pha, gon song tong xen ke va phan tram triet tieu."""
        duty = p.v_out / p.v_in
        i_pp_1phase = cls.single_phase_ripple_a(p.v_in, p.v_out, p.inductance_h, p.f_sw_hz)
        k_cancel = cls.normalized_cancellation_factor(p.num_phases, duty)
        i_pp_total_interleaved = i_pp_1phase * k_cancel

        # So sanh voi truong hop mac N pha cung luc nhung KHONG xen ke (N * Delta_I_1)
        i_pp_non_interleaved = p.num_phases * i_pp_1phase
        reduction_vs_non_interleaved_pct = (
            (1.0 - i_pp_total_interleaved / i_pp_non_interleaved) * 100.0
            if i_pp_non_interleaved > 0.0
            else 0.0
        )

        f_eff_hz = p.num_phases * p.f_sw_hz
        v_pp_cap = i_pp_total_interleaved / (8.0 * p.c_out_f * f_eff_hz)
        v_pp_esr = i_pp_total_interleaved * p.r_esr_ohm
        # Tong bien do dinh-dinh xap xi cho mach Buck da pha
        v_pp_total_v = math.sqrt(v_pp_cap ** 2 + v_pp_esr ** 2)

        return {
            "duty": duty,
            "i_pp_1phase_a": i_pp_1phase,
            "k_cancel": k_cancel,
            "i_pp_total_interleaved_a": i_pp_total_interleaved,
            "i_pp_non_interleaved_a": i_pp_non_interleaved,
            "reduction_pct": reduction_vs_non_interleaved_pct,
            "f_eff_mhz": f_eff_hz / 1.0e6,
            "v_pp_total_mv": v_pp_total_v * 1000.0,
        }


class InterleavedTimeDomainSimulator:
    """
    Subsystem 2: Mo phong mien thoi gian tung buoc (Time-Domain Cycle-Accurate)
    cua N pha Buck xen ke voi dien cam thuc te, DCR va mang tu loc ESR/C_out.
    """

    def __init__(self, params: MultiPhaseVRMParams):
        self.p = params
        self.t_sw = 1.0 / params.f_sw_hz
        self.duty = params.v_out / params.v_in
        # Khoi tao dong dien cac pha o diem xac lap ban dau cho nhanh hoi tu
        i_dc_phase = params.i_load_a / params.num_phases
        self.i_phases: List[float] = [i_dc_phase for _ in range(params.num_phases)]
        self.v_cap = params.v_out

    def _reset_steady_state_guess(self) -> None:
        """Dat trang thai ban dau dung tai diem xac lap ly thuyet de do ripple chinh xac."""
        i_dc = self.p.i_load_a / self.p.num_phases
        i_pp_1 = RippleCancellationAnalyzer.single_phase_ripple_a(
            self.p.v_in, self.p.v_out, self.p.inductance_h, self.p.f_sw_hz
        )
        for k in range(self.p.num_phases):
            # Pha tau tai thoi diem t = 0 co goc lech pha phi_k = k / N
            phase_frac = (1.0 - (k / self.p.num_phases)) % 1.0
            if phase_frac < self.duty:
                # Dang trong vung ON: di tu -Ipp/2 len +Ipp/2
                offset = -0.5 * i_pp_1 + (phase_frac / self.duty) * i_pp_1
            else:
                # Dang trong vung OFF: di tu +Ipp/2 xuong -Ipp/2
                offset = 0.5 * i_pp_1 - ((phase_frac - self.duty) / (1.0 - self.duty)) * i_pp_1
            self.i_phases[k] = i_dc + offset
        self.v_cap = self.p.v_out

    def run_cycles(self, num_cycles: int = 80, steps_per_cycle: int = 400) -> Dict[str, float]:
        """Chay mo phong mien thoi gian trong num_cycles chu ky T_sw voi noi suy canh xung PWM."""
        self._reset_steady_state_guess()
        dt = self.t_sw / steps_per_cycle
        d_tau = 1.0 / steps_per_cycle
        total_steps = num_cycles * steps_per_cycle

        # Thu thap du lieu o chu ky cuoi cung sau khi mach LC da on dinh hoan toan
        measure_start = (num_cycles - 1) * steps_per_cycle
        i_tot_samples: List[float] = []
        v_out_samples: List[float] = []
        i_p0_samples: List[float] = []

        v_drop_dcr_ss = (self.p.i_load_a / self.p.num_phases) * self.p.r_dcr_ohm
        for step in range(total_steps):
            t = step * dt
            i_sum = 0.0
            for k in range(self.p.num_phases):
                # Noi suy ty le thoi gian ON trong buoc dt de triet tieu sai so luong tu hoa PWM
                tau_start = ((t / self.t_sw) - (k / self.p.num_phases)) % 1.0
                if tau_start + d_tau <= self.duty:
                    on_frac = 1.0
                elif tau_start < self.duty:
                    on_frac = (self.duty - tau_start) / d_tau
                elif tau_start + d_tau > 1.0:
                    # Xu ly truong hop canh len bat dau o cuoi buoc dt
                    wrap_on = (tau_start + d_tau) - 1.0
                    on_frac = min(wrap_on, self.duty) / d_tau
                else:
                    on_frac = 0.0

                v_sw = self.p.v_in * on_frac
                di_dt = (v_sw + v_drop_dcr_ss - self.v_cap - self.i_phases[k] * self.p.r_dcr_ohm) / self.p.inductance_h
                self.i_phases[k] += di_dt * dt
                i_sum += self.i_phases[k]

            i_cap = i_sum - self.p.i_load_a
            self.v_cap += (i_cap / self.p.c_out_f) * dt
            v_out_inst = self.v_cap + i_cap * self.p.r_esr_ohm

            if step >= measure_start:
                i_tot_samples.append(i_sum)
                v_out_samples.append(v_out_inst)
                i_p0_samples.append(self.i_phases[0])

        return {
            "sim_i_pp_phase0_a": max(i_p0_samples) - min(i_p0_samples),
            "sim_i_pp_total_a": max(i_tot_samples) - min(i_tot_samples),
            "sim_v_pp_out_mv": (max(v_out_samples) - min(v_out_samples)) * 1000.0,
            "sim_v_mean_out_v": sum(v_out_samples) / len(v_out_samples),
        }


class CoupledInductorPair:
    """
    Subsystem 3: Mo hinh 2 cuon cam ghep tu tinh nghich chieu (Inverse-Coupled Inductors).
    So sanh giua Uncoupled vs Inverse-Coupled khi chung cung toc do dap ung qua do L_trans.
    """

    def __init__(self, l_self_h: float, coupling_coeff: float, v_in: float, v_out: float, f_sw_hz: float):
        if not (0.0 <= coupling_coeff < 0.95):
            raise ValueError("He so ghep k_c phai nam trong khoang [0.0, 0.95).")
        self.l_self = l_self_h
        self.k_c = coupling_coeff
        self.v_in = v_in
        self.v_out = v_out
        self.f_sw = f_sw_hz

    def transient_inductance_h(self) -> float:
        """Dien cam hieu dung khi ca 2 pha cung tang/giam dong thoi: L_trans = L * (1 - k_c)."""
        return self.l_self * (1.0 - self.k_c)

    def transient_slew_rate_a_per_us(self) -> float:
        """Toc do bien thien dong moi pha (A/us) khi co buoc nhay tai lon: (Vin - Vout) / L_trans."""
        l_tr = self.transient_inductance_h()
        return ((self.v_in - self.v_out) / l_tr) * 1.0e-6

    def simulate_steady_state_ripple_a(self, steps_per_cycle: int = 1000) -> float:
        """
        Mo phong chinh xac phuong trinh ma tran vi phan 2x2 cua cap cuon cam ghep nghich chieu:
        [di1/dt]   1 / [L * (1 - k_c^2)] * [ 1   k_c ] [ v1 ]
        [di2/dt] =                         [ k_c  1  ] [ v2 ]
        """
        duty = self.v_out / self.v_in
        t_sw = 1.0 / self.f_sw
        dt = t_sw / steps_per_cycle
        denom = self.l_self * (1.0 - self.k_c ** 2)

        i1, i2 = 0.0, 0.0
        # Chay 2 chu ky, do o chu ky thu 2 (he L khong co tro nen chu ky tuan hoan ngay lap tuc)
        i1_trace: List[float] = []
        for cycle in range(2):
            for s in range(steps_per_cycle):
                tau1 = (s / steps_per_cycle) % 1.0
                tau2 = ((s / steps_per_cycle) - 0.5) % 1.0
                v1 = (self.v_in - self.v_out) if tau1 < duty else (-self.v_out)
                v2 = (self.v_in - self.v_out) if tau2 < duty else (-self.v_out)

                di1_dt = (v1 + self.k_c * v2) / denom
                di2_dt = (self.k_c * v1 + v2) / denom
                i1 += di1_dt * dt
                i2 += di2_dt * dt

                if cycle == 1:
                    i1_trace.append(i1)

        return max(i1_trace) - min(i1_trace)


def test_multiphase_interleaving_ripple():
    """Chuong trinh kiem thu toan dien kien truc VRM da pha xen ke & cuon cam ghep."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BJ (NHOM 49) - BAI 192 (MILESTONE BJ.1)")
    print("KIEN TRUC NGUON DA PHA XEN KE MULTI-PHASE VRM & TRIET TIEU GON SONG")
    print("=" * 80)

    # 1. Kiem thu luat triet tieu gon song theo ty le Duty Cycle & Magic Points
    print("\n[1] Phan tich he so triet tieu gon song K_cancel(N=8 pha, V_in=12V):")
    p_base = MultiPhaseVRMParams(v_in=12.0, v_out=0.85, num_phases=8)
    v_outs_test = [0.75, 0.85, 1.50, 3.00, 4.50]  # 1.5V (D=1/8), 3.0V (D=2/8), 4.5V (D=3/8) la Magic Points!
    for v_o in v_outs_test:
        p_test = MultiPhaseVRMParams(v_in=12.0, v_out=v_o, num_phases=8)
        res = RippleCancellationAnalyzer.total_output_ripple_a(p_test)
        print(
            f"  * V_out = {v_o:4.2f}V (D={res['duty']:.4f}) | Ipp_1phase = {res['i_pp_1phase_a']:5.2f}A "
            f"| K_cancel = {res['k_cancel']:.4f} | Ipp_Total = {res['i_pp_total_interleaved_a']:5.2f}A "
            f"| Giam vs Non-Int = {res['reduction_pct']:6.2f}%"
        )
        if abs(v_o - 1.50) < 1e-6 or abs(v_o - 3.00) < 1e-6:
            assert res["k_cancel"] == 0.0, f"Loi: Tai D = k/N ({v_o}V) gon song phai triet tieu ve 0!"
            assert res["i_pp_total_interleaved_a"] == 0.0

    # Kiem tra muc tieu tai V_out = 0.85V
    res_core = RippleCancellationAnalyzer.total_output_ripple_a(p_base)
    assert res_core["reduction_pct"] > 93.0, "Loi: Ty le triet tieu gon song xen ke khong dat > 93%!"
    print("  -> Ket luan: Tai D = k/N triet tieu 100% gon song; tai 0.85V giam > 94% dong gon song (PASS)!")

    # 2. Kiem thu doi chieu mo phong mien thoi gian vs cong thuc giai tich
    print("\n[2] Kiem thu mo phong mien thoi gian (Time-Domain) N=8 pha tai V_out = 0.85V:")
    sim = InterleavedTimeDomainSimulator(p_base)
    sim_res = sim.run_cycles(num_cycles=80, steps_per_cycle=400)

    print(f"  * Gon song 1 pha (Giai tich vs Mo phong) : {res_core['i_pp_1phase_a']:6.3f} A vs {sim_res['sim_i_pp_phase0_a']:6.3f} A")
    print(f"  * Gon song tong 8 pha (Giai tich vs MP)  : {res_core['i_pp_total_interleaved_a']:6.3f} A vs {sim_res['sim_i_pp_total_a']:6.3f} A")
    print(f"  * Dien ap trung binh dau ra               : {sim_res['sim_v_mean_out_v']:6.4f} V (Target: 0.8500 V)")
    print(f"  * Gon song dien ap ngo ra Delta_V_out     : {sim_res['sim_v_pp_out_mv']:6.3f} mVpp (< 2.0 mVpp)")

    assert abs(sim_res["sim_i_pp_phase0_a"] - res_core["i_pp_1phase_a"]) < 0.25
    assert abs(sim_res["sim_i_pp_total_a"] - res_core["i_pp_total_interleaved_a"]) < 0.25
    assert sim_res["sim_v_pp_out_mv"] < 2.0, "Loi: Gon song dien ap ngo ra vuot nguong 2 mVpp!"
    print("  -> Ket luan: Mo phong mien thoi gian khop ly thuyet giai tich tuyet doi (PASS)!")

    # 3. Kiem thu uu the cua cuon cam ghep nghich chieu (Inverse-Coupled Inductors)
    print("\n[3] So sanh Cuon cam don (Uncoupled) vs Cuon cam ghep nghich chieu (Coupled k_c=0.70):")
    # Giu cung toc do dap ung qua do L_trans = 120 nH cho ca 2 giai phap:
    # Uncoupled: L_self = 120 nH, k_c = 0.0 -> L_trans = 120 nH
    # Coupled  : L_self = 120 nH / (1 - 0.70) = 400 nH, k_c = 0.70 -> L_trans = 120 nH (Giong het!)
    uncoupled = CoupledInductorPair(l_self_h=120.0e-9, coupling_coeff=0.0, v_in=12.0, v_out=1.20, f_sw_hz=600.0e3)
    coupled = CoupledInductorPair(l_self_h=400.0e-9, coupling_coeff=0.70, v_in=12.0, v_out=1.20, f_sw_hz=600.0e3)

    slew_unc = uncoupled.transient_slew_rate_a_per_us()
    slew_cpl = coupled.transient_slew_rate_a_per_us()
    rip_unc = uncoupled.simulate_steady_state_ripple_a()
    rip_cpl = coupled.simulate_steady_state_ripple_a()
    ripple_saving_pct = (1.0 - rip_cpl / rip_unc) * 100.0

    print(f"  * Uncoupled (L=120nH, k=0.00): L_trans = {uncoupled.transient_inductance_h()*1e9:5.1f} nH | Slew = {slew_unc:5.1f} A/us | Ripple/pha = {rip_unc:5.2f} A")
    print(f"  * Coupled   (L=400nH, k=0.70): L_trans = {coupled.transient_inductance_h()*1e9:5.1f} nH | Slew = {slew_cpl:5.1f} A/us | Ripple/pha = {rip_cpl:5.2f} A")
    print(f"  -> Ket qua: Cung toc do qua do 90 A/us, cuon cam ghep giam gon song pha them {ripple_saving_pct:.1f}%!")

    assert abs(slew_unc - slew_cpl) < 1e-6, "Loi: L_trans phai bang nhau de so sanh cong bang!"
    assert ripple_saving_pct > 40.0, "Loi: Cuon cam ghep nghich chieu khong giam duoc > 40% gon song pha!"
    print("  -> Ket luan: Cuon cam ghep nghich chieu vua tang toc dap ung vua giam ton hao loi sat (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 192: NGUON DA PHA XEN KE MULTI-PHASE VRM 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_multiphase_interleaving_ripple()
