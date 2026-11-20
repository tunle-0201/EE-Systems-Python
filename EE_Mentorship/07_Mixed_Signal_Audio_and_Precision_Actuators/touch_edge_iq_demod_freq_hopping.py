"""
================================================================================
EE MENTORSHIP - MODULE BP (NHOM 55) - BAI 217 (MILESTONE BP.2)
GIAI DIEU CHE TRUC GIAO I/Q LOCK-IN, DONG BO VSYNC OLED & NHAY TAN NE NHIEU SAC
================================================================================
Muc tieu:
1. Mo hinh hoa nhieu bo sac xung (Charger Common-Mode Switching Noise 180 kHz +
   song hai 540 kHz + 60 Hz dien luoi) va nhieu quet man hinh OLED 120 Hz.
2. Thiet ke bo giai dieu che truc giao I/Q Lock-In dung cua so Hann triet tieu
   bup phu > 32 dB, tach chinh xac bien do dien dung C_m va goc pha RC.
3. Bo quet pho thu dong (TX-OFF Noise Scan) + Nhay tan thich nghi (Frequency Hopping)
   tu dong tranh tan so bi sac gay nhieu, nang SNR tu < 8 dB len > 32 dB.
================================================================================
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class NoiseEnvironment:
    """Kich ban nhieu phan cung trong dien thoai / xe dien."""

    charger_freq_hz: float = 180_000.0
    charger_amp_mv: float = 185.0       # Nhieu bo sac tau khong noi mass
    mains_60hz_mv: float = 42.0         # Nhieu 60 Hz tu tay cam / dien luoi
    oled_active_burst_mv: float = 260.0 # Xung nhieu khi man OLED 120 Hz dang quet hang
    thermal_noise_mv: float = 5.5       # Nhieu trang nhiet AFE


class IQCarrierDemodulator:
    """
    Bo thu giai dieu che Lock-In I/Q cua so Hann:
    - Nhan tin hieu Rx voi cos(2*pi*f_tx*t) va -sin(2*pi*f_tx*t)
    - Ap dung cua so Hann giam ro ri pho (Spectral Leakage) khi nhieu lech tan so.
    """

    def __init__(self, fs_hz: float = 2_400_000.0, n_cycles: int = 16) -> None:
        self.fs_hz = fs_hz
        self.n_cycles = n_cycles

    def synthesize_rx_waveform(
        self,
        f_tx_hz: float,
        tx_enabled: bool,
        cm_pf: float,
        rc_phase_lag_rad: float,
        env: NoiseEnvironment,
        oled_blanking_active: bool,
        rng: random.Random,
        tx_gain_mv_per_pf: float = 55.0,
    ) -> List[float]:
        """Tong hop chuoi mau dien ap Rx tai tan so lay mau fs_hz."""
        n_samples = max(64, int(round(self.n_cycles * self.fs_hz / f_tx_hz)))
        carrier_amp_mv = cm_pf * tx_gain_mv_per_pf if tx_enabled else 0.0

        samples: List[float] = []
        # Pha bat dong bo cua bo sac va OLED thay doi ngau nhien giua cac khung quet
        charger_phase = rng.uniform(0.0, 2.0 * math.pi)
        oled_phase = rng.uniform(0.0, 2.0 * math.pi)
        for n in range(n_samples):
            t = n / self.fs_hz
            sig = carrier_amp_mv * math.cos(2.0 * math.pi * f_tx_hz * t - rc_phase_lag_rad)
            n_charger = (
                env.charger_amp_mv * math.cos(2.0 * math.pi * env.charger_freq_hz * t + charger_phase)
                + 0.35 * env.charger_amp_mv * math.cos(2.0 * math.pi * (2.0 * env.charger_freq_hz) * t + 2.0 * charger_phase)
            )
            n_mains = env.mains_60hz_mv * math.sin(2.0 * math.pi * 60.0 * t + 0.2)
            # OLED VSYNC Blanking triet tieu nhieu quet pixel (0 mV khi dang blanking)
            n_oled = (
                0.0
                if oled_blanking_active
                else env.oled_active_burst_mv * math.cos(2.0 * math.pi * 125_000.0 * t + oled_phase)
            )
            n_therm = rng.gauss(0.0, env.thermal_noise_mv)
            samples.append(sig + n_charger + n_mains + n_oled + n_therm)
        return samples

    def demodulate_iq(
        self, samples: List[float], f_tx_hz: float
    ) -> Tuple[float, float, float, float]:
        """Tra ve (I_mv, Q_mv, Magnitude_mv, Phase_deg) dung cua so Hann."""
        n_len = len(samples)
        i_acc = 0.0
        q_acc = 0.0
        w_sum = 0.0

        for n, x in enumerate(samples):
            t = n / self.fs_hz
            w = 0.5 * (1.0 - math.cos(2.0 * math.pi * n / max(1, n_len - 1)))
            theta = 2.0 * math.pi * f_tx_hz * t
            i_acc += w * x * math.cos(theta)
            q_acc -= w * x * math.sin(theta)
            w_sum += w

        i_mv = (2.0 / w_sum) * i_acc
        q_mv = (2.0 / w_sum) * q_acc
        mag_mv = math.hypot(i_mv, q_mv)
        phase_deg = math.degrees(math.atan2(q_mv, i_mv))
        return i_mv, q_mv, mag_mv, phase_deg


class AdaptiveFrequencyHopper:
    """
    Bo quet pho thu dong (Passive Noise Spectrum Scan) & Nhay tan chong nhieu sac:
    - Quet cac tan so ung vien khi TX TAT hoan toan trong cua so VSYNC Blanking.
    - Chon tan so co muc nhieu thap nhat (tranh trung tan so bo sac va OLED).
    """

    def __init__(
        self,
        candidate_freqs_hz: List[float] | None = None,
        n_avg_frames: int = 4,
    ) -> None:
        self.candidates = candidate_freqs_hz or [
            115_000.0,
            150_000.0,
            180_000.0,
            225_000.0,
            270_000.0,
            315_000.0,
        ]
        self.n_avg_frames = n_avg_frames

    def scan_quietest_frequency(
        self,
        demod: IQCarrierDemodulator,
        env: NoiseEnvironment,
        rng: random.Random,
    ) -> Tuple[float, Dict[float, float]]:
        noise_map_mv: Dict[float, float] = {}
        for freq in self.candidates:
            mags_sq: List[float] = []
            for _ in range(self.n_avg_frames):
                rx_noise_only = demod.synthesize_rx_waveform(
                    f_tx_hz=freq,
                    tx_enabled=False,
                    cm_pf=0.0,
                    rc_phase_lag_rad=0.0,
                    env=env,
                    oled_blanking_active=True,
                    rng=rng,
                )
                _, _, mag_mv, _ = demod.demodulate_iq(rx_noise_only, freq)
                mags_sq.append(mag_mv * mag_mv)
            noise_map_mv[freq] = math.sqrt(sum(mags_sq) / len(mags_sq))

        best_freq = min(noise_map_mv, key=lambda f: noise_map_mv[f])
        return best_freq, noise_map_mv


def measure_touch_delta_snr(
    demod: IQCarrierDemodulator,
    f_tx_hz: float,
    env: NoiseEnvironment,
    oled_blanking_active: bool,
    rng: random.Random,
    cm_idle_pf: float = 2.20,
    cm_touch_pf: float = 1.78,
    n_trials: int = 24,
) -> Tuple[float, float, float]:
    """
    Do bien do C_m luc khong cham vs khi cham ngon tay (-0.42 pF),
    tra ve (delta_cm_est_pf, noise_std_pf, snr_db).
    """
    gain = 55.0
    idle_vals: List[float] = []
    touch_vals: List[float] = []

    for _ in range(n_trials):
        w_idle = demod.synthesize_rx_waveform(
            f_tx_hz, True, cm_idle_pf, 0.15, env, oled_blanking_active, rng, gain
        )
        _, _, mag_idle, _ = demod.demodulate_iq(w_idle, f_tx_hz)
        idle_vals.append(mag_idle / gain)

        w_touch = demod.synthesize_rx_waveform(
            f_tx_hz, True, cm_touch_pf, 0.15, env, oled_blanking_active, rng, gain
        )
        _, _, mag_touch, _ = demod.demodulate_iq(w_touch, f_tx_hz)
        touch_vals.append(mag_touch / gain)

    mean_idle = sum(idle_vals) / len(idle_vals)
    mean_touch = sum(touch_vals) / len(touch_vals)
    delta_est = mean_touch - mean_idle
    var_idle = sum((v - mean_idle) ** 2 for v in idle_vals) / max(1, len(idle_vals) - 1)
    noise_std_pf = math.sqrt(var_idle)
    snr_db = 20.0 * math.log10(max(abs(delta_est), 1e-6) / max(noise_std_pf, 1e-6))
    return delta_est, noise_std_pf, snr_db


def test_iq_demod_freq_hopping() -> None:
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BP (NHOM 55) - BAI 217 (MILESTONE BP.2)")
    print("GIAI DIEU CHE I/Q LOCK-IN, DONG BO VSYNC OLED & NHAY TAN NE NHIEU SAC")
    print("=" * 80)

    rng = random.Random(2026)
    demod = IQCarrierDemodulator(fs_hz=2_400_000.0, n_cycles=16)
    env = NoiseEnvironment(charger_freq_hz=180_000.0, charger_amp_mv=185.0)
    hopper = AdaptiveFrequencyHopper()

    # 1. Kich ban bi tan cong: f_tx = 180 kHz (trung dung song bo sac) & khong VSYNC
    delta_jam, noise_jam, snr_jam = measure_touch_delta_snr(
        demod, 180_000.0, env, oled_blanking_active=False, rng=rng
    )
    print("\n[1] Khi f_tx = 180 kHz bi trung song hai bo sac (khong VSYNC):")
    print(
        f"  * delta_C_m do duoc={delta_jam:+.3f} pF | Nhieu sigma={noise_jam*1000:.1f} fF | SNR={snr_jam:.2f} dB"
    )
    assert snr_jam < 14.0, "Ky vong SNR bi nhieu suy giam nang khi trung tan so sac!"

    # 2. Quet pho TX-OFF trong cua so VSYNC Blanking & Nhay tan sang kenh sach
    best_freq, noise_map = hopper.scan_quietest_frequency(demod, env, rng)
    print("\n[2] Quet pho TX-OFF (VSYNC Blanking) tim kenh sach:")
    for freq_hz, n_mv in noise_map.items():
        tag = " <-- CHON!" if freq_hz == best_freq else ""
        print(f"  * {freq_hz/1000:6.1f} kHz : Nhieu nen = {n_mv:7.2f} mV{tag}")
    assert abs(best_freq - 180_000.0) > 1_000.0, "Khong duoc chon 180 kHz bi nhieu!"

    # 3. Do lai tai tan so moi + bat OLED VSYNC Blanking
    delta_clean, noise_clean, snr_clean = measure_touch_delta_snr(
        demod, best_freq, env, oled_blanking_active=True, rng=rng
    )
    print("\n[3] Sau khi bat OLED VSYNC + Nhay tan sang kenh sach:")
    print(
        f"  * Kenh moi={best_freq/1000:.1f} kHz | delta_C_m={delta_clean:+.3f} pF (Muc tieu -0.420) | Nhieu={noise_clean*1000:.2f} fF | SNR={snr_clean:.2f} dB"
    )
    assert abs(delta_clean - (-0.420)) < 0.025
    assert snr_clean > 32.0, f"SNR sau nhay tan qua thap: {snr_clean:.2f} dB"

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 217: I/Q LOCK-IN & FREQUENCY HOPPING 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_iq_demod_freq_hopping()
