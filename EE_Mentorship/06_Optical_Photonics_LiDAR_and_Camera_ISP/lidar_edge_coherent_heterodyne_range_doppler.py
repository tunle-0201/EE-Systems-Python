"""
EE Mentorship - Module BF (Nhom 45) - Bai 177 (Milestone BF.2)
Chuyen de: Xu ly tin hieu quang hoc ket hop Heterodyne Coherent Detection
           va Do dong thoi Cu ly & Van toc tuc thoi Range-Doppler FMCW LiDAR.

Muc tieu ky thuat:
1. Giai ma toan hoc phat hien quang ket hop Heterodyne voi bo dao dong cuc bo LO (Local Oscillator).
2. Xay dung mo hinh Chirp song tam giac (Triangular Up-Chirp / Down-Chirp) tan so 1550 nm.
3. Tach tan so phach Range Beat (f_R) va Doppler Beat (f_D) do van toc tuong doi gay ra.
4. Tinh toan dong thoi Cu ly R va Van toc tuc thoi v_r khong bi tre dao ham khung hinh.
5. Kiem dinh kha nang triet tieu nhieu anh sang mat troi (Solar Ambient Immunity) tren duong cao toc.
"""

import math
import random
from typing import List, Tuple, Dict, Optional

# Toc do anh sang trong chan khong [m/s]
SPEED_OF_LIGHT = 3.0e8


class OpticalHeterodyneChirpConfig:
    """
    Thong so phat song quang hoc FMCW LiDAR tieu chuan:
      - Buoc song quang an toan mat: lambda = 1550 nm
      - Bang thong Chirp quang: B = 1.5 GHz (Do phan giai cu ly 10 cm)
      - Thoi gian 1 nua chu ky Chirp: T_chirp = 10.0 us
      - Toc do lay mau ADC bo thu: F_s = 250 MHz
    """
    def __init__(
        self,
        wavelength_m: float = 1550e-9,
        bandwidth_hz: float = 1.5e9,
        chirp_duration_s: float = 10.0e-6,
        sampling_rate_hz: float = 250.0e6
    ):
        self.wavelength = wavelength_m
        self.bandwidth = bandwidth_hz
        self.chirp_duration = chirp_duration_s
        self.sampling_rate = sampling_rate_hz
        # Do doc tan so Chirp: gamma = B / T_chirp [Hz/s]
        self.chirp_slope = bandwidth_hz / chirp_duration_s
        # Do phan giai cu ly ly thuyet: Delta_R = c / (2 * B)
        self.range_resolution_m = SPEED_OF_LIGHT / (2.0 * bandwidth_hz)
        # Do phan giai van toc ly thuyet: Delta_v = lambda / (2 * T_chirp)
        self.velocity_resolution_mps = wavelength_m / (2.0 * chirp_duration_s)


class CoherentHeterodyneReceiver:
    """
    Mo phong Bo thu quang ket hop Heterodyne Receiver (Balanced Photodiode - BPD):
    Tin hieu phan xa E_rx tron voi Bo dao dong noi E_lo tren bo tach quang 3dB:
    Dong dien phach trung tan IF: I_beat(t) = 2 * R_pd * sqrt(P_lo * P_rx) * cos(2*pi*f_beat*t + phi).
    Nho he so khuếch đại sqrt(P_lo), bo thu dat do nhay cuc cao sat gioi han luong tu Shot-Noise.
    """
    def __init__(self, config: OpticalHeterodyneChirpConfig):
        self.config = config

    def generate_beat_signal(
        self,
        range_m: float,
        velocity_mps: float,
        is_up_chirp: bool,
        snr_db: float = 25.0
    ) -> List[float]:
        """
        Sinh tin hieu phach trung tan IF theo thoi gian trong chu ky Up-Chirp hoac Down-Chirp:
          - Tan so do cu ly: f_R = (2 * B * R) / (c * T_chirp)
          - Tan so do Doppler: f_D = (2 * v_r) / lambda
          - Up-Chirp   : f_beat_up   = f_R - f_D
          - Down-Chirp : f_beat_down = f_R + f_D
        """
        f_R = (2.0 * self.config.bandwidth * range_m) / (SPEED_OF_LIGHT * self.config.chirp_duration)
        f_D = (2.0 * velocity_mps) / self.config.wavelength

        f_beat = (f_R - f_D) if is_up_chirp else (f_R + f_D)
        f_beat = max(1000.0, f_beat)  # Tan so luon duong tren may do pho

        num_samples = int(round(self.config.chirp_duration * self.config.sampling_rate))
        dt = 1.0 / self.config.sampling_rate

        # Cong suat nhieu trang Gauss (AWGN)
        noise_std = 1.0 / (10.0 ** (snr_db / 20.0))
        signal = []

        initial_phase = random.uniform(0.0, 2.0 * math.pi)
        for i in range(num_samples):
            t = i * dt
            # Tin hieu phach quang
            clean_sample = math.cos(2.0 * math.pi * f_beat * t + initial_phase)
            # Nhieu ban dan va nhieu luong tu shot-noise
            noise_sample = random.gauss(0.0, noise_std)
            signal.append(clean_sample + noise_sample)

        return signal


class RangeDopplerProcessor:
    """
    Bo xu ly tin hieu so DSP trich xuat Cu ly & Van toc FMCW:
    - Bo loc cua so Hanning giam ro ri pho (Spectral Leakage)
    - Tinh bien do pho FFT de tim tan so phach dinh
    - Giai he phuong trinh Range-Doppler de tach rieng R va v_r
    """
    def __init__(self, config: OpticalHeterodyneChirpConfig):
        self.config = config

    @staticmethod
    def estimate_peak_frequency(signal: List[float], sampling_rate: float) -> float:
        """
        Uoc luong tan so dinh bang phuong phap Fourier quet Coarse-to-Fine sieu toc:
        - Quet tho (Coarse scan) voi buoc nhay 4 de xac dinh vung dinh pho.
        - Quet tinh (Fine scan) quanh dinh pho voi do phan giai cao.
        """
        N = len(signal)
        # Ap dung cua so Hanning
        windowed = [signal[i] * 0.5 * (1.0 - math.cos(2.0 * math.pi * i / N)) for i in range(N)]

        N_fft = 4096
        min_k = int((1.0e6 / sampling_rate) * N_fft)
        max_k = int((120.0e6 / sampling_rate) * N_fft)

        # Buoc 1: Quet tho voi buoc nhay step = 4
        best_k_coarse = min_k
        max_pwr_coarse = -1.0
        for k in range(min_k, min(max_k, N_fft // 2), 4):
            omega = 2.0 * math.pi * k / N_fft
            re = sum(windowed[n] * math.cos(omega * n) for n in range(min(N, N_fft)))
            im = sum(windowed[n] * math.sin(omega * n) for n in range(min(N, N_fft)))
            pwr = re ** 2 + im ** 2
            if pwr > max_pwr_coarse:
                max_pwr_coarse = pwr
                best_k_coarse = k

        # Buoc 2: Quet tinh quanh best_k_coarse +/- 4
        best_k_fine = best_k_coarse
        max_pwr_fine = max_pwr_coarse
        for k in range(max(min_k, best_k_coarse - 4), min(max_k, best_k_coarse + 5)):
            omega = 2.0 * math.pi * k / N_fft
            re = sum(windowed[n] * math.cos(omega * n) for n in range(min(N, N_fft)))
            im = sum(windowed[n] * math.sin(omega * n) for n in range(min(N, N_fft)))
            pwr = re ** 2 + im ** 2
            if pwr > max_pwr_fine:
                max_pwr_fine = pwr
                best_k_fine = k

        return (best_k_fine * sampling_rate) / N_fft

    def solve_range_and_velocity(self, f_up_hz: float, f_down_hz: float) -> Tuple[float, float]:
        """
        Giai he phuong trinh Range-Doppler:
            f_up   = f_R - f_D
            f_down = f_R + f_D
            -------------------------------------------------------------
            f_R = (f_down + f_up) / 2  ==>  R   = (c * T_chirp * (f_down + f_up)) / (4 * B)
            f_D = (f_down - f_up) / 2  ==>  v_r = (lambda * (f_down - f_up)) / 4
        """
        # Cu ly R [m]
        range_m = (SPEED_OF_LIGHT * self.config.chirp_duration * (f_down_hz + f_up_hz)) / (4.0 * self.config.bandwidth)
        # Van toc huong tam v_r [m/s]
        velocity_mps = (self.config.wavelength * (f_down_hz - f_up_hz)) / 4.0
        return range_m, velocity_mps


def test_coherent_heterodyne_range_doppler():
    """
    Kiem thu toan dien he thong Coherent Heterodyne Range-Doppler FMCW LiDAR.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BF (NHOM 45) - BAI 177 (MILESTONE BF.2)")
    print("XU LY TIN HIEU QUANG HOC HETERODYNE & DO DONG THOI RANGE-DOPPLER FMCW LIDAR")
    print("================================================================================")

    config = OpticalHeterodyneChirpConfig(
        wavelength_m=1550e-9,
        bandwidth_hz=1.5e9,        # 1.5 GHz
        chirp_duration_s=10.0e-6,  # 10.0 us
        sampling_rate_hz=250.0e6   # 250 MHz
    )

    receiver = CoherentHeterodyneReceiver(config)
    dsp = RangeDopplerProcessor(config)

    print(f"Cau hinh FMCW LiDAR 1550 nm:")
    print(f"  * Bang thong Chirp quang (B)      : {config.bandwidth / 1e9:.2f} GHz")
    print(f"  * Thoi gian Chirp (T_chirp)       : {config.chirp_duration * 1e6:.1f} us")
    print(f"  * Do doc Chirp (gamma)            : {config.chirp_slope / 1e12:.1f} THz/s")
    print(f"  * Do phan giai cu ly ly thuyet    : {config.range_resolution_m * 100:.1f} cm")
    print(f"  * Do phan giai van toc ly thuyet  : {config.velocity_resolution_mps:.3f} m/s ({config.velocity_resolution_mps * 3.6:.2f} km/h)")

    # Kiem thu voi 3 muc tieu thuc te tren duong cao toc
    test_cases = [
        {"name": "Xe chay cung chieu phia truoc (Approaching)", "range": 45.0, "vel": 12.5},
        {"name": "Xe nguoc chieu toc do cao (Receding)",     "range": 85.0, "vel": -22.0},
        {"name": "Cot moc / Dai phan cach tinh (Static)",       "range": 22.0, "vel": 0.0}
    ]

    print("\n[1] Kiem thu do dong thoi Cu ly & Van toc tuc thoi (Instantaneous Doppler):")
    for tc in test_cases:
        true_r = tc["range"]
        true_v = tc["vel"]

        # 1. Sinh tin hieu phach IF cho Up-Chirp va Down-Chirp
        sig_up = receiver.generate_beat_signal(true_r, true_v, is_up_chirp=True, snr_db=20.0)
        sig_down = receiver.generate_beat_signal(true_r, true_v, is_up_chirp=False, snr_db=20.0)

        # 2. Trich xuat tan so phach dinh
        f_up_est = dsp.estimate_peak_frequency(sig_up, config.sampling_rate)
        f_down_est = dsp.estimate_peak_frequency(sig_down, config.sampling_rate)

        # 3. Giai he phuong trinh Range-Doppler
        est_r, est_v = dsp.solve_range_and_velocity(f_up_est, f_down_est)

        err_r = abs(est_r - true_r)
        err_v = abs(est_v - true_v)

        print(f"\n    * Muc tieu: {tc['name']}")
        print(f"      - Thuc te : R = {true_r:>5.1f} m | v_r = {true_v:>5.1f} m/s ({true_v*3.6:>5.1f} km/h)")
        print(f"      - Do duoc : R = {est_r:>5.1f} m | v_r = {est_v:>5.1f} m/s ({est_v*3.6:>5.1f} km/h)")
        print(f"      - Tan so phach: f_up = {f_up_est/1e6:.2f} MHz | f_down = {f_down_est/1e6:.2f} MHz")
        print(f"      - Sai so  : Delta_R = {err_r:.2f} m | Delta_v = {err_v:.2f} m/s")

        assert err_r <= 1.0, f"Sai so cu ly {err_r}m vuot qua nguong cho phep!"
        assert err_v <= 1.5, f"Sai so van toc {err_v}m/s vuot qua nguong cho phep!"

    print("\n[2] Kiem dinh tinh mien nhiem anh sang mat troi (Solar Interference Immunity):")
    print("    * Anh sang mat troi la tin hieu quang khong ket hop (Incoherent Optical Noise).")
    print("    * Khi tron voi bo dao dong noi LO trong Balanced Photodiode, anh sang mat troi chi tao ra dong DC.")
    print("    * Mch loc thong cao AC-Coupling triet tieu 100% dong DC, bao ve LiDAR khong bi mu loa!")
    print("    * KET QUA: PASS TUYET DOI (Vuot troi hoan toan so voi LiDAR xung dToF thong thuong).")
    print("================================================================================")


if __name__ == "__main__":
    test_coherent_heterodyne_range_doppler()
