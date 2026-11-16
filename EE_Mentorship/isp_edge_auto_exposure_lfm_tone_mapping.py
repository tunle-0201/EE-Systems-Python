"""
EE MENTORSHIP PROGRAM - MODULE BL (NHOM 51) - BAI 202 (MILESTONE BL.3)
================================================================================
VONG DIEU KHIEN PHAN CUNG AUTO-EXPOSURE (AE), CHONG CHOP DEN LED GIAO THONG
(LED FLICKER MITIGATION - LFM) VA NEN DAI DONG ACES FILMIC TONE MAPPING LUT
CHO CAMERA XE TU HANH TESLA FSD & APPLE CAMERA ISP
================================================================================

Nguyen ly vat ly va Thiet ke he thong:
1. Vong hoi tiep kin Tu dong Phoi sang AE (Closed-Loop Log-Space Auto-Exposure):
   - Muc tieu do sang trung binh xam 18% (Y_target = 0.180, vung tre +/- 0.015 chong rung).
   - Uu tien tang thoi gian phoi sang T_exp truoc (den tran chong nhoe 10 ms) voi Gain = 1.0x
     de toi thieu hoa khuech dai nhieu, chi tang Analog Gain (1x..16x) khi T_exp da dat tran.

2. Chup chop den LED (LED Flicker Mitigation - LFM) - Bai toan song con xe tu lai:
   - Den giao thong & den hau LED hien dai bam xung PWM 90-120 Hz (duty chi 10-15%).
   - Neu dung cua so phoi sang ngan T_short = 1.0 ms ngoai troi nang, co > 80% xac suat
     cua so 1 ms lot dung vao khoang TAT cua xung PWM -> Camera bi "mu" den do!
   - Giai phap phan cung Split-Diode / Small Photodiode (SPD) LFM:
     Dat them 1 photodiode nho giam do nhay 16x va cho tich luy XUYEN SUOT ca chu ky
     11.1 ms -> Chup duoc it nhat 1 xung sang cua moi den LED >= 90 Hz bat ke pha!

3. Nen dai dong ACES Filmic Tone Mapping + Chuan Gamma sRGB OETF:
   - Anh tuyen tinh HDR 120 dB (tu 0.005 nguoi di bo trong bong ram den 45.0 den pha)
     khong the chia tuyen tinh ve 8-bit [0..255] vi se de bet nguoi di bo thanh 0/255.
   - Duong cong chu S phi tuyen ACES Filmic giu chi tiet bong toi ma van nen mem vung sang!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Cap nhat Phoi sang Khong gian Log voi He so Giam chan k_damping:
                              Y_target
     EV_next = EV_cur * ( ───────────────── )^k_damp
                           max(1e-4, Y_meas)

2. Duong cong ACES Filmic (Krzysztof Narkowicz) & Gamma sRGB:
               x * (2.51 * x + 0.03)
     f_ACES = ────────────────────────  (clip [0, 1])
              x * (2.43 * x + 0.59) + 0.14
--------------------------------------------------------------------------------
"""

import math
from typing import Dict, List, Tuple


class AutoExposureGovernor:
    """Bo dieu khien phoi sang vong kin (T_exp + Analog Gain) chong nhoe & chong giat."""

    def __init__(
        self,
        target_luma: float = 0.18,
        deadband: float = 0.015,
        t_min_s: float = 0.1e-3,
        t_max_blur_s: float = 10.0e-3,
        gain_min: float = 1.0,
        gain_max: float = 16.0,
        damping: float = 0.65,
    ):
        self.target = target_luma
        self.deadband = deadband
        self.t_min_s = t_min_s
        self.t_max_s = t_max_blur_s
        self.g_min = gain_min
        self.g_max = gain_max
        self.damping = damping

        self.t_exp_s = 2.0e-3
        self.analog_gain = 1.0

    @property
    def total_ev_gain(self) -> float:
        return self.t_exp_s * self.analog_gain

    def _allocate_t_and_gain(self, target_ev_product: float) -> None:
        # Kẹp trong dai phan cung [t_min * g_min .. t_max * g_max]
        ev_min = self.t_min_s * self.g_min
        ev_max = self.t_max_s * self.g_max
        ev_clamped = max(ev_min, min(ev_max, target_ev_product))

        # Uu tien toi da thoi gian phoi sang truoc khi tang Analog Gain de giam nhieu nhiet
        if ev_clamped <= self.t_max_s * self.g_min:
            self.t_exp_s = ev_clamped / self.g_min
            self.analog_gain = self.g_min
        else:
            self.t_exp_s = self.t_max_s
            self.analog_gain = ev_clamped / self.t_max_s

    def update_frame(self, scene_radiance_y: float) -> Dict[str, float]:
        meas_y = scene_radiance_y * self.total_ev_gain
        in_deadband = abs(meas_y - self.target) <= self.deadband

        if not in_deadband:
            ratio = self.target / max(1e-6, meas_y)
            next_ev = self.total_ev_gain * (ratio ** self.damping)
            self._allocate_t_and_gain(next_ev)
            meas_y = scene_radiance_y * self.total_ev_gain

        return {
            "measured_luma": meas_y,
            "t_exp_ms": self.t_exp_s * 1000.0,
            "analog_gain": self.analog_gain,
            "converged": abs(meas_y - self.target) <= self.deadband,
        }


class LEDFlickerSimulator:
    """So sanh Camera man chup ngan (1 ms) vs Cam bien LFM Split-Diode (11.1 ms) truoc den PWM."""

    @staticmethod
    def integrate_pwm_led(
        t_start_s: float,
        t_int_s: float,
        pwm_freq_hz: float = 100.0,
        pwm_duty: float = 0.10,
        led_peak_flux: float = 100.0,
        attenuation: float = 1.0,
        steps: int = 400,
    ) -> float:
        """Tich phan nang luong den PWM tren cua so [t_start, t_start + t_int]."""
        period = 1.0 / pwm_freq_hz
        on_time = pwm_duty * period
        dt = t_int_s / steps
        acc_energy = 0.0
        for k in range(steps):
            t_mid = t_start_s + (k + 0.5) * dt
            if (t_mid % period) < on_time:
                acc_energy += (led_peak_flux / attenuation) * dt
        return acc_energy


class FilmicToneMapper:
    """Toan tu ACES Filmic Tone Mapping + IEC sRGB OETF Gamma chuyen HDR -> 8-bit [0..255]."""

    @staticmethod
    def aces_filmic(x: float) -> float:
        v = max(0.0, x)
        num = v * (2.51 * v + 0.03)
        den = v * (2.43 * v + 0.59) + 0.14
        return max(0.0, min(1.0, num / den))

    @staticmethod
    def linear_to_srgb_byte(c_lin: float) -> int:
        c = max(0.0, min(1.0, c_lin))
        if c <= 0.0031308:
            s = 12.92 * c
        else:
            s = 1.055 * (c ** (1.0 / 2.4)) - 0.055
        return int(round(max(0.0, min(1.0, s)) * 255.0))

    @classmethod
    def hdr_to_srgb_byte(cls, hdr_val: float, exposure_key: float = 1.0) -> int:
        mapped = cls.aces_filmic(hdr_val * exposure_key)
        return cls.linear_to_srgb_byte(mapped)


def test_auto_exposure_lfm_tone_mapping():
    """Chuong trinh kiem thu Vong AE, Chong chop den LED LFM & ACES Filmic Tone Mapping."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BL (NHOM 51) - BAI 202 (MILESTONE BL.3)")
    print("AUTO-EXPOSURE AE, CHONG CHOP DEN LED LFM & ACES FILMIC TONE MAPPING")
    print("=" * 80)

    # 1. Kiem thu Vong hoi tiep kin Auto-Exposure khi xe ra/vao ham toi <-> nang gat
    print("\n[1] Kiem thu Vong dieu khien AE (Vao ham toi 2.5 -> Ra nang 120.0):")
    ae = AutoExposureGovernor()
    tunnel_hist = [ae.update_frame(scene_radiance_y=2.5) for _ in range(10)]
    dark_final = tunnel_hist[-1]

    sun_hist = [ae.update_frame(scene_radiance_y=120.0) for _ in range(10)]
    bright_final = sun_hist[-1]

    print(
        f"  * Trong ham (Rad=2.5) : Y_meas={dark_final['measured_luma']:.3f} | "
        f"T_exp={dark_final['t_exp_ms']:.2f} ms | Gain={dark_final['analog_gain']:.2f}x | Conv={dark_final['converged']}"
    )
    print(
        f"  * Ra nang (Rad=120.0) : Y_meas={bright_final['measured_luma']:.3f} | "
        f"T_exp={bright_final['t_exp_ms']:.2f} ms | Gain={bright_final['analog_gain']:.2f}x | Conv={bright_final['converged']}"
    )

    assert dark_final["converged"] and dark_final["t_exp_ms"] == 10.0 and dark_final["analog_gain"] > 5.0
    assert bright_final["converged"] and bright_final["analog_gain"] == 1.0 and bright_final["t_exp_ms"] < 2.0
    print("  -> Ket luan: AE tu dong hoi tu < 10 khung va uu tien giu Gain=1x luc du sang (PASS)!")

    # 2. Kiem thu Chong chop den LED PWM 100 Hz (10% Duty Cycle) qua 20 pha bat ky
    print("\n[2] Kiem thu Chup chop den giao thong LED PWM 100 Hz (Duty 10%) tren 20 pha:")
    n_phases = 20
    std_misses = 0
    lfm_flux_list: List[float] = []
    detect_thresh = 2.0  # Nguong nhan dien den (true avg flux = 10.0)

    for idx in range(n_phases):
        t0 = idx * 0.0005  # Quet 20 pha lech nhau qua tron 1 chu ky 10 ms cua den 100 Hz
        e_std = LEDFlickerSimulator.integrate_pwm_led(t0, t_int_s=1.0e-3, pwm_freq_hz=100.0, pwm_duty=0.10, attenuation=1.0)
        flux_std = e_std / 1.0e-3
        # Cam bien LFM SPD tich luy 11.1 ms voi bo loc quang giam nhay 11.1x (t_eff = 1.0 ms)
        e_lfm = LEDFlickerSimulator.integrate_pwm_led(t0, t_int_s=11.1e-3, pwm_freq_hz=100.0, pwm_duty=0.10, attenuation=11.1)
        flux_lfm = e_lfm / (11.1e-3 / 11.1)

        if flux_std < detect_thresh:
            std_misses += 1
        lfm_flux_list.append(flux_lfm)

    lfm_misses = sum(1 for v in lfm_flux_list if v < detect_thresh)
    lfm_min = min(lfm_flux_list)
    lfm_max = max(lfm_flux_list)

    print(f"  * Camera Short-Exp thuong (1.0 ms)  : Bi MU den LED = {std_misses}/20 frames ({std_misses*5}%)!")
    print(
        f"  * Cam bien LFM SPD (11.1 ms / 11.1x): Bi MU = {lfm_misses}/20 frames | "
        f"Phat hien = 100% (Min..Max Flux = {lfm_min:.2f}..{lfm_max:.2f}, Target 10.0)"
    )

    assert std_misses >= 14 and lfm_misses == 0 and lfm_min >= 8.0
    print("  -> Ket luan: LFM xoa 100% loi mu den giao thong PWM tren camera tu lai (PASS)!")

    # 3. So sanh Linear Clipping vs ACES Filmic Tone Mapping tren canh HDR 9,000:1
    print("\n[3] So sanh Nen anh Linear vs ACES Filmic (Nguoi di bo 0.02 vs Den pha 45.0):")
    shadow_pedestrian = 0.02
    headlight_glare = 45.0

    # Neu chia tuyen tinh theo dinh den pha 45.0 roi ap sRGB
    naive_ped_byte = FilmicToneMapper.linear_to_srgb_byte(shadow_pedestrian / headlight_glare)
    # Dung ACES Filmic voi exposure_key = 4.0 de day nguoi di bo len ma van giu mem vung den pha
    aces_ped_byte = FilmicToneMapper.hdr_to_srgb_byte(shadow_pedestrian, exposure_key=4.0)
    aces_glare_byte = FilmicToneMapper.hdr_to_srgb_byte(headlight_glare, exposure_key=4.0)

    print(f"  * Chia Linear theo den pha -> Nguoi di bo = {naive_ped_byte:3d}/255 (Mat hut trong toi!)")
    print(f"  * ACES Filmic + sRGB       -> Nguoi di bo = {aces_ped_byte:3d}/255 | Den pha = {aces_glare_byte:3d}/255")

    assert naive_ped_byte <= 6 and 60 <= aces_ped_byte <= 140 and 245 <= aces_glare_byte <= 255
    print("  -> Ket luan: ACES Filmic bao toan nguoi di bo lan chi tiet den pha cho FSD (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 202: AE + LFM + ACES TONE MAPPING HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_auto_exposure_lfm_tone_mapping()
