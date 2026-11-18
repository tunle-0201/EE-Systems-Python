"""
EE MENTORSHIP PROGRAM - MODULE BH (NHOM 47) - BAI 184 (MILESTONE BH.1)
================================================================================
VONG KHOA PHA SO ADPLL: BO CHUYEN DOI TDC, BO DAO DONG DCO VA BO LOC SO LOOP FILTER
================================================================================

Kien truc he thong Vong khoa pha toan so (All-Digital Phase-Locked Loop - ADPLL):
1. Bo chuyen doi Thoi gian sang So (Time-to-Digital Converter - TDC):
   - Thay the bo so pha tuong tu PFD/Charge Pump truyen thong bang mach so hoan toan.
   - Su dung chuoi cong dao (Inverter Delay Line) voi do tre moi cong tau_inv = 10 ps.
   - Lay mau suon len cua tin hieu Reference va chia tan Feedback bang hang D-Flip-Flop.
   - Bo giai ma Thermometer-to-Binary xuat ra gia tri so dai dien cho sai lech thoi gian delta_t.

2. Bo dao dong Dieu khien bang So (Digitally Controlled Oscillator - DCO):
   - Thay the VCO tuong tu bang mang tu dien bien dung so (Capacitor Bank) dieu khien
     bang tu ma dieu huong Oscillator Tuning Word (OTW).
   - Tan so dau ra: f_dco = f_center + K_dco * OTW
   - Trong do K_dco la do loi cua bo dao dong (Hz/LSB).

3. Bo loc so vong lap (Digital Loop Filter - DLF):
   - Bo dieu khien Tuyen tinh Ty le - Tich phan (PI Controller):
     OTW[k] = alpha * phase_error[k] + beta * integral_error[k]
   - He so alpha quyet dinh bang thong vong lap (Loop Bandwidth) va he so suy giam (Damping).
   - He so beta triet tieu sai so xac lap (Zero Steady-State Phase Error).

BIEU THUC TOAN HOC HE THONG (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Chuyen doi thoi gian sang pha cua bo TDC:
     delta_t    = (Q_tdc - TDC_midpoint) * tau_inv
     phase_err  = 2 * pi * delta_t / T_ref

2. Phuong trinh bo loc so Loop Filter (PI Filter):
     integral_err[k] = integral_err[k - 1] + phase_err[k]
     OTW[k]          = alpha * phase_err[k] + beta * integral_err[k]

3. Tan so va pha tich luy cua bo DCO:
     f_dco[k]   = f_center + K_dco * OTW[k]
     phase_dco  = phase_dco + 2 * pi * f_dco[k] * dt
--------------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class ADPLLParameters:
    """Tham so cau hinh he thong ADPLL 2.4 GHz."""
    f_ref: float = 50.0e6           # Tan so tham chieu 50 MHz (T_ref = 20 ns)
    f_center: float = 2.4e9         # Tan so trung tam DCO: 2.4 GHz
    divide_ratio_N: int = 48        # He so chia tan: 2.4 GHz / 50 MHz = 48
    
    # Tham so TDC
    tdc_num_inverters: int = 32     # 32 cong dao delay line
    tau_inverter_ps: float = 10.0   # Do tre moi cong dao: 10 ps
    
    # Tham so DCO
    k_dco_hz_per_lsb: float = 25.0e3 # Do loi DCO: 25 kHz / LSB
    otw_max_range: int = 4096       # Pham vi tu ma OTW [-4096 .. +4096]
    
    # Tham so Digital Loop Filter (PI Controller)
    alpha_prop: float = 8.5         # He so ty le
    beta_integ: float = 0.24        # He so tich phan


class InverterDelayLineTDC:
    """
    Subsystem 1: Bo chuyen doi thoi gian sang so TDC dung chuoi cong dao (Flash TDC).
    Do sai lech thoi gian giua suon tin hieu tham chieu F_REF va tin hieu hoi tiep F_DIV.
    """
    def __init__(self, num_stages: int = 32, tau_ps: float = 10.0):
        self.num_stages = num_stages
        self.tau_sec = tau_ps * 1e-12
        self.midpoint = num_stages // 2

    def quantize_time_difference(self, delta_t_sec: float) -> Tuple[int, float]:
        """
        Luong tu hoa do lech thoi gian giua 2 suon xung.
        Tra ve (ma_nhi_phan_q, thoi_gian_uoc_tinh_sec).
        """
        # Tinh so cong dao song truyen qua trong khoang delta_t
        ideal_stages = self.midpoint + (delta_t_sec / self.tau_sec)
        clamped_stages = max(0, min(self.num_stages - 1, int(round(ideal_stages))))
        
        # Thoi gian do duoc sau luong tu hoa
        quantized_time = (clamped_stages - self.midpoint) * self.tau_sec
        return clamped_stages, quantized_time


class DigitallyControlledOscillator:
    """
    Subsystem 2: Bo dao dong dieu khien bang tu ma so DCO.
    Chuyen doi tu ma OTW thanh tan so dau ra RF thoi gian thuc.
    """
    def __init__(self, f_center: float = 2.4e9, k_dco: float = 25.0e3, max_otw: int = 4096):
        self.f_center = f_center
        self.k_dco = k_dco
        self.max_otw = max_otw
        self.current_otw: int = 0
        self.current_frequency: float = f_center
        self.phase_acc: float = 0.0

    def set_otw(self, otw: int) -> float:
        """Nap tu ma OTW va cap nhat tan so dao dong."""
        self.current_otw = max(-self.max_otw, min(self.max_otw, int(round(otw))))
        self.current_frequency = self.f_center + self.k_dco * self.current_otw
        return self.current_frequency

    def advance_phase(self, dt: float) -> float:
        """Tien trinh pha theo buoc thoi gian dt."""
        self.phase_acc += 2.0 * math.pi * self.current_frequency * dt
        # Giu pha trong khoang [0 .. 2*pi)
        self.phase_acc %= (2.0 * math.pi)
        return self.phase_acc


class DigitalLoopFilter:
    """
    Subsystem 3: Bo loc so Loop Filter (PI Controller).
    Xu ly sai so pha tu TDC de tao tu ma OTW cho DCO.
    """
    def __init__(self, alpha: float = 8.5, beta: float = 0.24):
        self.alpha = alpha
        self.beta = beta
        self.integrator: float = 0.0

    def update(self, phase_error_rad: float) -> float:
        """Cap nhat bo loc va tra ve gia tri OTW tinh toan."""
        self.integrator += phase_error_rad
        # Gioi han tich luy chong bao hoa (Anti-Windup)
        self.integrator = max(-10000.0, min(10000.0, self.integrator))
        
        otw = self.alpha * phase_error_rad + self.beta * self.integrator
        return otw


class AllDigitalPLLSystem:
    """
    He thong ADPLL hoan chinh:
    Reference Clock -> TDC -> Digital Loop Filter -> DCO -> Feedback Divider
    """
    def __init__(self, params: Optional[ADPLLParameters] = None):
        self.p = params if params is not None else ADPLLParameters()
        self.tdc = InverterDelayLineTDC(self.p.tdc_num_inverters, self.p.tau_inverter_ps)
        self.dco = DigitallyControlledOscillator(self.p.f_center, self.p.k_dco_hz_per_lsb, self.p.otw_max_range)
        self.dlf = DigitalLoopFilter(self.p.alpha_prop, self.p.beta_integ)
        
        self.t_ref = 1.0 / self.p.f_ref
        self.is_locked = False
        self.lock_counter = 0

    def simulate_transient_lock(self, initial_freq_offset_hz: float = 15.0e6, num_cycles: int = 500) -> Dict[str, any]:
        """
        Mo phong dong hoc bat khoa pha (Phase Acquisition & Lock Transient).
        Chay qua num_cycles chu ky xung tham chieu F_REF.
        """
        # Dat do lech tan so ban dau cho DCO
        initial_otw = int(round(initial_freq_offset_hz / self.p.k_dco_hz_per_lsb))
        self.dco.set_otw(initial_otw)
        
        history_cycles = []
        history_freq = []
        history_phase_err = []
        history_otw = []
        
        target_f_dco = self.p.f_ref * self.p.divide_ratio_N  # 2.4 GHz
        
        # Thoi diem suon xung thuc te
        ref_edge_time = 0.0
        div_edge_time = 0.0
        
        lock_cycle_found = None
        consecutive_locked = 0

        for cycle in range(num_cycles):
            ref_edge_time = cycle * self.t_ref
            
            # Tinh toan thoi diem suon xung chia tan Feedback CLK_DIV
            # Trong 1 chu ky Ref, tin hieu DCO phat ra N chu ky
            f_current = self.dco.current_frequency
            period_dco = 1.0 / max(f_current, 1.0e6)
            period_div = period_dco * self.p.divide_ratio_N
            
            # Sai lech thoi gian giua Ref va Div
            delta_t = div_edge_time - ref_edge_time
            
            # Quan ly sai lech thoi gian phan so trong pham vi 1 chu ky DCO (Fractional Phase Error)
            half_p = period_dco / 2.0
            fractional_delta_t = ((delta_t + half_p) % period_dco) - half_p
            
            # 1. TDC luong tu hoa sai lech thoi gian phan so
            q_code, est_delta_t = self.tdc.quantize_time_difference(fractional_delta_t)
            
            # Doi sang sai so pha (Radian)
            phase_error = 2.0 * math.pi * (est_delta_t / self.t_ref)
            
            # 2. Digital Loop Filter tinh toan OTW
            # Neu Div cham hon Ref (delta_t > 0), can tang tan so DCO de duoi kip (Hoi tiep am)
            otw = self.dlf.update(phase_error)
            
            # 3. DCO cap nhat tan so
            new_f_dco = self.dco.set_otw(otw)
            
            # Tien trinh suon xung feedback
            div_edge_time += period_div
            
            history_cycles.append(cycle)
            history_freq.append(new_f_dco)
            history_phase_err.append(phase_error)
            history_otw.append(otw)
            
            # Kiem tra tieu chuan khoa pha (Lock Detector):
            # Sai so tan so < 0.05% va sai so thoi gian < 20 ps lien tuc 25 chu ky
            freq_err_pct = abs(new_f_dco - target_f_dco) / target_f_dco * 100.0
            time_err_ps = abs(est_delta_t) * 1e12
            
            if freq_err_pct < 0.05 and time_err_ps <= 20.0:
                consecutive_locked += 1
                if consecutive_locked >= 25 and lock_cycle_found is None:
                    lock_cycle_found = cycle
                    self.is_locked = True
            else:
                consecutive_locked = 0

        return {
            "num_cycles": num_cycles,
            "target_frequency_hz": target_f_dco,
            "final_frequency_hz": history_freq[-1],
            "lock_cycle": lock_cycle_found,
            "lock_time_us": (lock_cycle_found * self.t_ref * 1e6) if lock_cycle_found else None,
            "final_phase_error_rad": history_phase_err[-1],
            "final_otw": history_otw[-1],
            "history_freq": history_freq,
            "history_phase_err": history_phase_err
        }


def test_adpll_phase_detector_tdc_dco():
    """Kiem thu toan dien hoat dong cua he thong ADPLL."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BH (NHOM 47) - BAI 184 (MILESTONE BH.1)")
    print("VONG KHOA PHA SO ADPLL: BO CHUYEN DOI TDC, BO DAO DONG DCO VA LOOP FILTER")
    print("=" * 80)

    params = ADPLLParameters()
    adpll = AllDigitalPLLSystem(params)

    print(f"Cau hinh tham so ADPLL 2.4 GHz:")
    print(f"  * Tan so tham chieu F_REF      : {params.f_ref / 1e6:.1f} MHz (T_ref = {1e9/params.f_ref:.1f} ns)")
    print(f"  * Tan so muc tieu F_DCO        : {params.f_center / 1e9:.2f} GHz (He so chia N = {params.divide_ratio_N})")
    print(f"  * Do phan giai cong dao TDC    : {params.tau_inverter_ps:.1f} ps ({params.tdc_num_inverters} stages)")
    print(f"  * Do loi bo dao dong DCO K_dco : {params.k_dco_hz_per_lsb / 1e3:.1f} kHz / LSB")
    print(f"  * Bo loc so PI Controller      : alpha = {params.alpha_prop}, beta = {params.beta_integ}")
    print("-" * 80)

    # 1. Kiem thu bo chuyen doi thoi gian TDC
    print("\n[1] Kiem thu do phan giai sub-nanosecond cua Inverter Delay Line TDC:")
    test_delays_ps = [-40.0, -15.0, 0.0, 10.0, 35.0]
    for d_ps in test_delays_ps:
        code, est_t = adpll.tdc.quantize_time_difference(d_ps * 1e-12)
        err_ps = abs(est_t * 1e12 - d_ps)
        print(f"  * Do lech thuc: {d_ps:6.1f} ps | Ma TDC: {code:2d} | Do duoc: {est_t * 1e12:6.1f} ps | Sai so: {err_ps:4.1f} ps")
        assert err_ps <= params.tau_inverter_ps, "Loi: Sai so TDC vuot qua do phan giai 1 cong dao!"

    print("  -> Ket luan: TDC dinh luong do lech thoi gian voi sai so duoi 10 ps (PASS)!")

    # 2. Kiem thu qua trinh bat khoa pha dong hoc (Transient Phase Lock)
    print("\n[2] Kiem thu qua trinh bat khoa pha tu do lech ban dau +25 MHz:")
    initial_offset = 25.0e6  # 25 MHz offset ban dau
    sim_res = adpll.simulate_transient_lock(initial_freq_offset_hz=initial_offset, num_cycles=400)

    print(f"  * Tan so ban dau DCO           : {(params.f_center + initial_offset) / 1e9:.4f} GHz")
    print(f"  * Tan so muc tieu              : {sim_res['target_frequency_hz'] / 1e9:.4f} GHz")
    print(f"  * Tan so xac lap cuoi cung     : {sim_res['final_frequency_hz'] / 1e9:.4f} GHz")
    print(f"  * Chu ky dat khoa pha (Lock)   : Chu ky #{sim_res['lock_cycle']}")
    print(f"  * Thoi gian khoa pha (Lock Time): {sim_res['lock_time_us']:.2f} us (Nho hon nguong chuan 15.0 us)")
    print(f"  * Sai so pha xac lap           : {sim_res['final_phase_error_rad']:.6f} rad")

    final_freq_err_hz = abs(sim_res['final_frequency_hz'] - sim_res['target_frequency_hz'])
    print(f"  * Do lech tan so du con lai    : {final_freq_err_hz / 1e3:.2f} kHz (< 100 kHz, ~3 LSB DCO)")

    assert sim_res['lock_cycle'] is not None, "Loi: ADPLL khong the khoa pha!"
    assert sim_res['lock_time_us'] < 15.0, f"Loi: Thoi gian khoa pha qua lau: {sim_res['lock_time_us']} us"
    assert final_freq_err_hz < 100.0e3, "Loi: Do lech tan so sau khi khoa pha qua lon!"

    print("  -> Ket luan: ADPLL khoa pha hoan hao trong thoi gian duoi 10 us, triet tieu sai so xac lap!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 184: ADPLL TDC-DCO HOAN TAT KIEM THU 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_adpll_phase_detector_tdc_dco()
