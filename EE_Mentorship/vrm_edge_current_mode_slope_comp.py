"""
EE MENTORSHIP PROGRAM - MODULE BJ (NHOM 49) - BAI 193 (MILESTONE BJ.2)
================================================================================
DIEU KHIEN CHE DO DONG DINH PCMC, BU DOC CHONG DAO DONG HA HAI VA CAM BIEN DCR
(PEAK CURRENT-MODE CONTROL, SLOPE COMPENSATION, LOSSLESS DCR & CURRENT SHARING)
================================================================================

Kien truc mach vong trong dieu khien dong dien cho bo nguon da pha VRM:
1. Cam bien dong khong ton hao qua cuon cam (Lossless Inductor DCR Current Sensing):
   - O dong tai 50 A/pha, dung dien tro shunt se gay ton hao nhiet khong lo.
   - Ky su dung mang loc R_cs - C_cs mac song song voi cuon cam co dien tro noi
     R_dcr. Khi hang so thoi gian khop nhau: R_cs * C_cs = L / R_dcr, dien ap
     tren tu V_cs(t) phan anh chinh xac tuyet doi I_L(t) * R_dcr ma khong mat 1 mW nao!
   - Tinh huong bien thuc te: khi cuon cam nong len (+80 deg C), R_dcr dong tang +31.4%,
     gay lech hang so thoi gian -> can mach bu nhiet NTC (Thermistor Tracking).

2. Dieu khien che do dong dinh (Peak Current-Mode Control - PCMC) & Dao dong Ha Hai:
   - Moi chu ky, MOSFET tren bat cho den khi dong cuon cam dat nguong I_cmd.
   - Khi he so chu ky D > 0.5, suon giam dong dien S_f lon hon suon tang S_n:
     He so khuech dai nhieu tung chu ky alpha = -S_f / S_n = -D / (1 - D) co tri
     tuyet doi lon hon 1! Gay ra dao dong ha hai (Sub-Harmonic Oscillation) chu ky
     rong - hep xen ke o tan so f_sw / 2.

3. Bu doc nhan tao (Artificial Slope Compensation):
   - Cong them doc bu S_e vao tin hieu dong do duoc (hoac tru vao nguong I_cmd).
   - He so suy giam nhieu moi tro thanh: alpha = -(S_f - S_e) / (S_n + S_e).
   - Chon S_e >= 0.5 * S_f dam bao |alpha| < 1 voi MOI chu ky D tu 0% den 99%;
     chon S_e = S_f cho dap ung triet nhieu trong dung 1 chu ky (Deadbeat Response)!

4. Can bang dong dien da pha chu dong (Active Phase Current Sharing):
   - Sai so san xuat (+/- 20% R_dcr va R_dson) lam pha co tro thap bi qua tai nhiet.
   - Vong lap chia se dong dien dieu chinh nguong I_cmd_k rieng cho tung pha dua
     tren sai lech so voi gia tri trung binh toan bo N pha, ep do lech xuong < 1%.

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Ham truyen dat mach cam bien dong khong ton hao DCR (Lossless DCR RC Sense):
                                 1 + s * (L / R_dcr)
     V_cs(s) = I_L(s) * R_dcr * ─────────────────────
                                 1 + s * (R_cs * C_cs)

2. Gia tri rieng nhieu dong dien PCMC tung chu ky (Cycle-to-Cycle Perturbation):
                delta_I[k+1]       -(S_f - S_e)
     alpha = ────────────────── = ─────────────── ,  voi S_n = (V_in - V_out)/L
                 delta_I[k]          S_n + S_e            S_f = V_out / L

3. Dieu kien on dinh tuyet doi cho moi Duty Cycle D in (0, 1):
     S_e >= 0.5 * S_f     (va Deadbeat toi uu khi S_e = S_f  =>  alpha = 0)
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class DCRSensingConfig:
    """Tham so cuon cam va mang loc cam bien dong khong ton hao RC."""
    l_h: float = 150.0e-9         # Dien cam danh dinh: 150 nH
    r_dcr_25c_ohm: float = 0.40e-3 # Dien tro cuon cam o 25 deg C: 0.40 mOhm
    r_cs_ohm: float = 1.875e3     # Dien tro cam bien: 1.875 kOhm
    c_cs_f: float = 200.0e-9      # Tu cam bien: 200 nF => R_cs * C_cs = 375 us = L / R_dcr
    alpha_cu_per_c: float = 0.00393 # He so nhiet dien tro dong (0.393 % / deg C)


class LosslessDCRSensingNetwork:
    """
    Subsystem 1: Mo phong mang loc RC cam bien dong khong ton hao DCR
    va anh huong cua troi nhiet do dong (Copper Thermal Drift).
    """

    def __init__(self, cfg: DCRSensingConfig):
        self.cfg = cfg

    def r_dcr_at_temp(self, temp_c: float) -> float:
        """Dien tro day dong thay doi theo nhiet do: R(T) = R_25 * [1 + alpha * (T - 25)]."""
        return self.cfg.r_dcr_25c_ohm * (1.0 + self.cfg.alpha_cu_per_c * (temp_c - 25.0))

    def simulate_step_sensing(
        self,
        i_step_a: float,
        temp_c: float,
        ntc_compensation: bool = False,
        duration_s: float = 2.0e-3,
        dt_s: float = 1.0e-6,
    ) -> Dict[str, float]:
        """
        Giai phuong trinh vi phan mach loc RC khi dong cuon cam nhay bac tu 0 -> i_step_a:
        V_L(t) = L * dI_L/dt + R_dcr(T) * I_L(t)  (gia su buoc nhay voi hang so tau_step = 5 us)
        C_cs * dV_cs/dt = (V_L(t) - V_cs(t)) / R_cs
        """
        r_dcr_hot = self.r_dcr_at_temp(temp_c)
        tau_rc = self.cfg.r_cs_ohm * self.cfg.c_cs_f
        tau_rise = 5.0e-6  # Thoi hang tang dong thuc te 5 us

        v_cs = 0.0
        i_l = 0.0
        steps = int(duration_s / dt_s)
        peak_ratio_error = 0.0
        v_cs_list: List[float] = []
        i_true_list: List[float] = []

        # Neu co NTC tracking: he so chia ty le bu lai do tang nhiet cua R_dcr
        gain_ntc = (self.cfg.r_dcr_25c_ohm / r_dcr_hot) if ntc_compensation else 1.0

        for step in range(steps):
            t = step * dt_s
            i_prev = i_l
            i_l = i_step_a * (1.0 - math.exp(-t / tau_rise))
            di_dt = (i_l - i_prev) / dt_s

            v_ind = self.cfg.l_h * di_dt + r_dcr_hot * i_l
            dv_cs_dt = (v_ind - v_cs) / tau_rc
            v_cs += dv_cs_dt * dt_s

            # Uoc tinh dong do duoc dua tren R_dcr danh dinh 25C (hoac co bu NTC)
            i_sensed = (v_cs / self.cfg.r_dcr_25c_ohm) * gain_ntc
            v_cs_list.append(i_sensed)
            i_true_list.append(i_l)

            if t > 30.0e-6:  # Sau qua trinh tang suon 5us
                err = abs(i_sensed - i_l) / i_step_a * 100.0
                if err > peak_ratio_error:
                    peak_ratio_error = err

        steady_sensed = v_cs_list[-1]
        dc_error_pct = abs(steady_sensed - i_step_a) / i_step_a * 100.0
        return {
            "r_dcr_hot_mohm": r_dcr_hot * 1000.0,
            "tau_l_us": (self.cfg.l_h / r_dcr_hot) * 1e6,
            "tau_rc_us": tau_rc * 1e6,
            "steady_sensed_a": steady_sensed,
            "dc_error_pct": dc_error_pct,
            "peak_transient_error_pct": peak_ratio_error,
        }


class PeakCurrentModeLoop:
    """
    Subsystem 2: Mo phong tung chu ky Peak Current-Mode Control (PCMC) va Slope Compensation.
    Chuyen biet de phan tich dao dong ha hai (Sub-harmonic Oscillation) khi D > 0.5.
    """

    def __init__(self, v_in: float = 5.0, v_out: float = 3.25, l_h: float = 200.0e-9, f_sw_hz: float = 500.0e3):
        self.v_in = v_in
        self.v_out = v_out
        self.l_h = l_h
        self.f_sw_hz = f_sw_hz
        self.t_sw = 1.0 / f_sw_hz

        self.s_n = (v_in - v_out) / l_h  # Slope len (A/s)
        self.s_f = v_out / l_h           # Slope xuong (A/s)
        self.duty_nominal = v_out / v_in

    def analytical_eigenvalue(self, slope_e_a_per_s: float) -> float:
        """
        Tinh gia tri rieng chu ky alpha = -(S_f - S_e) / (S_n + S_e).
        |alpha| < 1 => On dinh. |alpha| >= 1 => Dao dong ha hai f_sw / 2.
        """
        return -(self.s_f - slope_e_a_per_s) / (self.s_n + slope_e_a_per_s)

    def simulate_subharmonic_response(
        self,
        slope_e_ratio_of_sf: float,
        initial_perturbation_a: float = 1.5,
        num_cycles: int = 30,
    ) -> Dict[str, any]:
        """
        Mo phong dong thoi gian roi rac tung chu ky (Cycle-by-Cycle Map):
        Khoi tao dong thung lung I_valley[0] = I_valley_ss + initial_perturbation_a
        De thay ro dao dong rong-hep xen ke khi khong co bu doc va tat dan khi co bu doc!
        """
        s_e = slope_e_ratio_of_sf * self.s_f
        t_on_ss = self.duty_nominal * self.t_sw

        # Tai xac lap: I_peak_ss = I_cmd - S_e * t_on_ss, I_valley_ss = I_peak_ss - S_n * t_on_ss
        # Ta chon I_valley_ss = 10.0 A lam moc quy chieu
        i_valley_ss = 10.0
        i_peak_ss = i_valley_ss + self.s_n * t_on_ss
        i_cmd = i_peak_ss + s_e * t_on_ss

        i_valley = i_valley_ss + initial_perturbation_a
        duty_history: List[float] = []
        valley_history: List[float] = [i_valley]

        for _ in range(num_cycles):
            # Giai phuong trinh bat diem cat: i_valley + S_n * t_on = i_cmd - S_e * t_on
            t_on = (i_cmd - i_valley) / (self.s_n + s_e)
            # Gioi han vat ly duty trong [0.02*T_sw, 0.98*T_sw] (cham tuong bao hoa)
            t_on = max(0.02 * self.t_sw, min(0.98 * self.t_sw, t_on))
            t_off = self.t_sw - t_on

            i_peak = i_valley + self.s_n * t_on
            i_valley = i_peak - self.s_f * t_off

            duty_history.append(t_on / self.t_sw)
            valley_history.append(i_valley)

        # Do do dao dong ha hai o 6 chu ky cuoi (chenh lech duty chan - le)
        tail = duty_history[-6:]
        odd_even_swing = max(tail) - min(tail)
        return {
            "slope_e_a_per_us": s_e * 1e-6,
            "alpha_theory": self.analytical_eigenvalue(s_e),
            "duty_history": duty_history,
            "valley_history": valley_history,
            "steady_duty_swing": odd_even_swing,
            "is_stable": odd_even_swing < 0.005,
        }


class PhaseCurrentSharingBalancer:
    """
    Subsystem 3: Bo can bang dong dien chu dong cho 8 pha khi co sai so linh kien (+/- 20%).
    Mo phong hoat dong cua vong lap chia se dong dien PCMC giua 8 pha song song.
    """

    def __init__(self, r_dcr_phases_ohm: List[float], r_dson_phases_ohm: List[float], v_in: float = 12.0, v_out: float = 0.85):
        self.num_phases = len(r_dcr_phases_ohm)
        self.r_dcr = list(r_dcr_phases_ohm)
        self.r_dson = list(r_dson_phases_ohm)
        self.v_in = v_in
        self.v_out = v_out
        self.r_total = [dcr + dson for dcr, dson in zip(self.r_dcr, self.r_dson)]

    def simulate_without_sharing(self, i_load_total_a: float) -> Dict[str, float]:
        """Khi dung chung 1 dien ap dieu khien PWM (Voltage-Mode): dong chia ty le nghich voi tro!"""
        inv_r = [1.0 / r for r in self.r_total]
        sum_inv_r = sum(inv_r)
        i_phases = [i_load_total_a * (g / sum_inv_r) for g in inv_r]
        i_avg = i_load_total_a / self.num_phases
        imbalance_pct = ((max(i_phases) - min(i_phases)) / i_avg) * 100.0
        return {
            "i_phases": i_phases,
            "i_max_a": max(i_phases),
            "i_min_a": min(i_phases),
            "imbalance_pct": imbalance_pct,
        }

    def simulate_with_active_sharing(
        self,
        i_load_total_a: float,
        k_share: float = 0.015,
        k_v_loop: float = 8.0,
        iterations: int = 80,
    ) -> Dict[str, float]:
        """
        Vong lap can bang dong chu dong:
        Moi pha dieu chinh sai lech duty/dong dua tren (I_avg - I_k) va vong ap giu V_out.
        """
        i_phases = self.simulate_without_sharing(i_load_total_a)["i_phases"]
        v_ctrl_phases = [self.v_out for _ in range(self.num_phases)]
        i_avg_target = i_load_total_a / self.num_phases

        for _ in range(iterations):
            i_sum = sum(i_phases)
            i_mean = i_sum / self.num_phases
            # Vong ap ngoai bu tong dong tai
            v_bus_corr = k_v_loop * (i_load_total_a - i_sum) * 1e-4

            for k in range(self.num_phases):
                # Vong chia se dong trong: pha nao dong cao hon trung binh se giam dien ap lai
                share_err = i_mean - i_phases[k]
                v_ctrl_phases[k] += v_bus_corr + k_share * share_err * self.r_total[k]
                # Cap nhat dong xac lap theo mach dinh luat Ohm qua R_total[k]
                i_phases[k] = max(0.0, (v_ctrl_phases[k] - self.v_out + i_avg_target * 0.5e-3) / self.r_total[k])

            # Chuan hoa theo rang buoc Kirchhoff nut tai: sum(I_k) = I_load
            scale = i_load_total_a / max(1e-9, sum(i_phases))
            i_phases = [i * scale for i in i_phases]

        imbalance_pct = ((max(i_phases) - min(i_phases)) / i_avg_target) * 100.0
        return {
            "i_phases": i_phases,
            "i_max_a": max(i_phases),
            "i_min_a": min(i_phases),
            "imbalance_pct": imbalance_pct,
        }


def test_current_mode_slope_comp():
    """Kiem thu toan dien mach cam bien DCR, bu doc chong dao dong ha hai va can bang pha."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BJ (NHOM 49) - BAI 193 (MILESTONE BJ.2)")
    print("DIEU KHIEN DONG DINH PCMC, BU DOC CHONG DAO DONG HA HAI VA CAM BIEN DCR")
    print("=" * 80)

    # 1. Kiem thu cam bien dong khong ton hao Inductor DCR va bu nhiet NTC
    print("\n[1] Kiem thu mach cam bien dong khong ton hao Inductor DCR (35 A Step):")
    dcr_net = LosslessDCRSensingNetwork(DCRSensingConfig())
    res_25c = dcr_net.simulate_step_sensing(i_step_a=35.0, temp_c=25.0, ntc_compensation=False)
    res_105c_raw = dcr_net.simulate_step_sensing(i_step_a=35.0, temp_c=105.0, ntc_compensation=False)
    res_105c_ntc = dcr_net.simulate_step_sensing(i_step_a=35.0, temp_c=105.0, ntc_compensation=True)

    print(f"  * 25 deg C (Khop hang so tau_L = tau_RC = 375 us): Sensed = {res_25c['steady_sensed_a']:5.2f} A | Sai so = {res_25c['dc_error_pct']:5.2f}%")
    print(f"  * 105 deg C KHONG bu NTC (R_dcr tang +31.4%)     : Sensed = {res_105c_raw['steady_sensed_a']:5.2f} A | Sai so = {res_105c_raw['dc_error_pct']:5.2f}%")
    print(f"  * 105 deg C CO bu NTC (Tracking chinh xac)       : Sensed = {res_105c_ntc['steady_sensed_a']:5.2f} A | Sai so DC = {res_105c_ntc['dc_error_pct']:5.2f}%")

    assert res_25c["dc_error_pct"] < 1.0, "Loi: Tai 25 deg C hang so khop ma sai so > 1%!"
    assert res_105c_raw["dc_error_pct"] > 25.0, "Loi: Khong thay hien tuong troi nhiet khi dong nong len!"
    assert res_105c_ntc["dc_error_pct"] < 1.0, "Loi: Co bu NTC ma sai so DC van cao!"
    print("  -> Ket luan: Mang RC khop thoi gian doc dong chuan xac 0W ton hao; NTC giu sai so < 1% (PASS)!")

    # 2. Kiem thu dao dong ha hai PCMC o Duty Cycle D = 0.65 > 0.5 va bu doc Slope Compensation
    print("\n[2] Kiem thu dao dong ha hai Sub-Harmonic (D = 0.65 > 0.5) & Bu doc S_e:")
    pcmc = PeakCurrentModeLoop(v_in=5.0, v_out=3.25, l_h=200.0e-9, f_sw_hz=500.0e3)
    res_nocomp = pcmc.simulate_subharmonic_response(slope_e_ratio_of_sf=0.0, initial_perturbation_a=1.5)
    res_half = pcmc.simulate_subharmonic_response(slope_e_ratio_of_sf=0.50, initial_perturbation_a=1.5)
    res_deadbeat = pcmc.simulate_subharmonic_response(slope_e_ratio_of_sf=1.00, initial_perturbation_a=1.5)

    print(f"  * S_e = 0.00 * S_f (Khong bu)  : alpha = {res_nocomp['alpha_theory']:+6.3f} | Duty Swing = {res_nocomp['steady_duty_swing']:.4f} -> {'ON DINH' if res_nocomp['is_stable'] else 'MAT ON DINH (DAO DONG HA HAI)'}")
    print(f"  * S_e = 0.50 * S_f (Toi thieu) : alpha = {res_half['alpha_theory']:+6.3f} | Duty Swing = {res_half['steady_duty_swing']:.4f} -> {'ON DINH' if res_half['is_stable'] else 'MAT ON DINH'}")
    print(f"  * S_e = 1.00 * S_f (Deadbeat)  : alpha = {res_deadbeat['alpha_theory']:+6.3f} | Duty Swing = {res_deadbeat['steady_duty_swing']:.4f} -> {'ON DINH TUYET DOI (alpha=0)' if res_deadbeat['is_stable'] else 'MAT ON DINH'}")

    assert abs(res_nocomp["alpha_theory"]) > 1.0 and not res_nocomp["is_stable"], "Loi: Khi D=0.65 va S_e=0 bat buoc phai dao dong ha hai!"
    assert abs(res_half["alpha_theory"]) < 1.0 and res_half["is_stable"]
    assert abs(res_deadbeat["alpha_theory"]) < 1e-6 and res_deadbeat["steady_duty_swing"] < 1e-6
    print("  -> Ket luan: Bu doc S_e = S_f triet tieu dao dong ha hai trong dung 1 chu ky (PASS)!")

    # 3. Kiem thu can bang dong dien 8 pha khi linh kien lech +/- 20%
    print("\n[3] Kiem thu Active Phase Current Sharing cho 8 pha lech linh kien (+/- 20%):")
    # Sai so R_dcr va R_dson thuc te giua 8 pha tren bo mach VRM
    r_dcr_8 = [0.32e-3, 0.35e-3, 0.38e-3, 0.40e-3, 0.42e-3, 0.36e-3, 0.33e-3, 0.44e-3]
    r_dson_8 = [0.65e-3, 0.72e-3, 0.80e-3, 0.78e-3, 0.85e-3, 0.75e-3, 0.68e-3, 0.88e-3]
    balancer = PhaseCurrentSharingBalancer(r_dcr_8, r_dson_8)

    unbal = balancer.simulate_without_sharing(i_load_total_a=320.0)
    bal = balancer.simulate_with_active_sharing(i_load_total_a=320.0, k_share=0.25, iterations=180)

    print(f"  * KHONG can bang dong : Min={unbal['i_min_a']:5.2f}A | Max={unbal['i_max_a']:5.2f}A | Lech pha = {unbal['imbalance_pct']:5.2f}%")
    print(f"  * CO Active Sharing   : Min={bal['i_min_a']:5.2f}A | Max={bal['i_max_a']:5.2f}A | Lech pha = {bal['imbalance_pct']:5.2f}% (< 2.0%)")

    assert unbal["imbalance_pct"] > 20.0, "Loi: Sai so linh kien phai tao lech pha ro ret khi khong can bang!"
    assert bal["imbalance_pct"] < 2.0, f"Loi: Do lech pha sau can bang van cao: {bal['imbalance_pct']:.2f}%"
    print("  -> Ket luan: Vong lap Active Current Sharing ep do lech 8 pha xuong duoi 2% (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 193: DIEU KHIEN DONG DINH PCMC & DCR SENSING 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_current_mode_slope_comp()
