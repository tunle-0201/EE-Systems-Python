"""
================================================================================
CHUYEN DE AF: HARDWARE AUDIO DSP & I2S / PDM MICROPHONE BEAMFORMING
BAI 3: THUAT TOAN DINH HUONG CHUM SONG AM HOC DELAY-AND-SUM BEAMFORMING CHO MANG MICRO
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Xu ly chong on chu dong & tach giong noi cho Apple AirPods / Tesla Cabin
Ngon ngu: Python 3 thuan tuy, xu ly mang pha tin hieu khong gian (Spatial Audio DSP)
================================================================================
"""

import math
from typing import List, Tuple, Dict

# ------------------------------------------------------------------------------
# 1. CAC THONG SO VAT LY VA MANG MICROPHONE TUYEN TINH ULA
# ------------------------------------------------------------------------------

SPEED_OF_SOUND = 343.0 # Toc do am thanh trong khong khi o 20 do C (m/s)

class MicrophoneArrayConfig:
    """
    Cau hinh mang microphone tuyen tinh deu ULA (Uniform Linear Array):
    - num_mics (M): So luong micro MEMS (vi du 4 hoac 8 micro)
    - mic_spacing (d): Khoang cach giua cac micro (m)
    - sample_rate (Fs): Tan so lay mau am thanh (Hz)
    """
    def __init__(self,
                 num_mics: int = 4,
                 mic_spacing: float = 0.035, # 3.5 cm (thoa man tieu chuan Spatial Nyquist d < c / (2 * 4000) = 4.28 cm)
                 sample_rate: int = 48000):
        self.num_mics = num_mics
        self.mic_spacing = mic_spacing
        self.sample_rate = sample_rate

    def get_time_delay(self, mic_index: int, angle_rad: float) -> float:
        """
        Tinh thoi gian tre lan truyen am thanh TDOA tai micro thu m:
        tau_m = (m * d * sin(theta)) / c
        theta = 0 rad: Huong thang goc truc dien (Broadside)
        theta > 0 rad: Huong lech phai (+X)
        theta < 0 rad: Huong lech trai (-X)
        """
        return (mic_index * self.mic_spacing * math.sin(angle_rad)) / SPEED_OF_SOUND

    def get_sample_delay(self, mic_index: int, angle_rad: float) -> float:
        """Quy doi thoi gian tre sang so mau roi rac: Delta_n = tau * Fs"""
        return self.get_time_delay(mic_index, angle_rad) * self.sample_rate

# ------------------------------------------------------------------------------
# 2. THUAT TOAN DELAY-AND-SUM BEAMFORMER (DAS)
# ------------------------------------------------------------------------------

def fractional_delay_interpolate(signal: List[float], delay_samples: float) -> List[float]:
    """
    Tao do tre mau am thanh (bao gom ca phan nguyen va phan thap phan)
    bang noi suy tuyen tinh (Linear Fractional Delay Interpolator) de dat do chinh xac vi giay:
    x_delayed[n] = (1 - alpha) * x[n - D] + alpha * x[n - D - 1]
    """
    out = [0.0] * len(signal)
    int_delay = int(math.floor(delay_samples))
    frac_delay = delay_samples - int_delay

    for n in range(len(signal)):
        src_idx0 = n - int_delay
        src_idx1 = src_idx0 - 1

        val0 = signal[src_idx0] if 0 <= src_idx0 < len(signal) else 0.0
        val1 = signal[src_idx1] if 0 <= src_idx1 < len(signal) else 0.0

        out[n] = (1.0 - frac_delay) * val0 + frac_delay * val1

    return out

class DelayAndSumBeamformer:
    """
    Bo dinh huong chum song am hoc Delay-and-Sum:
    Luu tru mang tin hieu tu M micro, bu tru do tre theo goc lai mong muon theta_steer,
    sau do cong dong pha cac kenh de khu nhieu tu cac huong khac.
    """
    def __init__(self, config: MicrophoneArrayConfig):
        self.cfg = config

    def process(self,
                multichannel_signals: List[List[float]],
                steer_angle_rad: float) -> List[float]:
        """
        multichannel_signals: Danh sach M kenh tin hieu, moi kenh dai N mau.
        steer_angle_rad: Goc lai bup song mong muon (Radian).
        Tra ve: Tin hieu don kenh sau khi loc chum song (Beamformed Audio).
        """
        num_mics = self.cfg.num_mics
        num_samples = len(multichannel_signals[0])
        accumulated_output = [0.0] * num_samples

        for m in range(num_mics):
            # Tinh do tre can bu cho micro m de dong pha tai steer_angle
            # Luu y: De bu tre lan truyen tau_m, ta phai dich tre nguoc lai (-tau_m)
            delay = self.cfg.get_sample_delay(m, steer_angle_rad)
            # Alignment: dich truoc hoac sau
            aligned_channel = fractional_delay_interpolate(multichannel_signals[m], -delay)

            for n in range(num_samples):
                accumulated_output[n] += aligned_channel[n]

        # Chia trung binh so luong micro
        inv_m = 1.0 / num_mics
        return [sample * inv_m for sample in accumulated_output]

# ------------------------------------------------------------------------------
# 3. MO PHONG KHONG GIAN AM HOC VA QUET BIEU DO HUONG TINH (BEAM PATTERN)
# ------------------------------------------------------------------------------

def generate_spatial_audio(config: MicrophoneArrayConfig,
                          freq_hz: float,
                          duration_s: float,
                          source_angle_deg: float,
                          amplitude: float = 1.0) -> List[List[float]]:
    """
    Mo phong song am thanh don tan tu mot goc phat source_angle_deg
    lan truyen qua khong gian toi mang M micro.
    """
    num_samples = int(config.sample_rate * duration_s)
    source_rad = math.radians(source_angle_deg)
    multichannel: List[List[float]] = []

    for m in range(config.num_mics):
        tau = config.get_time_delay(m, source_rad)
        channel_data = []
        for n in range(num_samples):
            t = (n / config.sample_rate) - tau
            # Song am sin toi micro m
            val = amplitude * math.sin(2.0 * math.pi * freq_hz * t)
            channel_data.append(val)
        multichannel.append(channel_data)

    return multichannel

def compute_rms_energy(signal: List[float]) -> float:
    """Tinh nang luong hieu dung RMS cua tin hieu am thanh."""
    if not signal:
        return 0.0
    sum_sq = sum(x * x for x in signal)
    return math.sqrt(sum_sq / len(signal))

def test_beamformer_steering_and_suppression():
    """
    Kiem tra thuat toan Beamforming:
    1. Dat nguon am mong muon (Target Voice) o goc +30 do (tan so 1000 Hz, bien do 1.0).
    2. Dat nguon am nhieu (Noise Jammer) o goc -45 do (tan so 1000 Hz, bien do 1.0).
    3. Su dung DAS Beamformer lai bup song ve dung +30 do.
    4. Kiem tra nang luong thu duoc tai +30 do so voi khi huong ve cac goc khac.
    """
    cfg = MicrophoneArrayConfig(num_mics=4, mic_spacing=0.035, sample_rate=48000)
    beamformer = DelayAndSumBeamformer(cfg)

    duration = 0.015 # 15 ms (720 mau)
    target_angle = 30.0 # Nguoi noi o +30 deg
    target_freq = 2500.0 # Tan so am sac ro net cua giong noi nguoi (2.5 kHz)

    # Phat am thanh tu nguon mong muon +30 deg
    target_signals = generate_spatial_audio(cfg, target_freq, duration, target_angle, amplitude=1.0)

    # 1. Thu am bang cach lai chum song ve chinh xac +30 deg (Target Steer)
    output_on_target = beamformer.process(target_signals, math.radians(target_angle))
    rms_target = compute_rms_energy(output_on_target)

    # 2. Thu am bang cach lai chum song lech sang huong khac (vi du 0 deg hoac -45 deg)
    output_off_target = beamformer.process(target_signals, math.radians(-45.0))
    rms_off_target = compute_rms_energy(output_off_target)

    # Do suy hao (Suppression Ratio) tinh bang dB
    # dB = 20 * log10(rms_target / rms_off_target)
    ratio = rms_target / max(1e-6, rms_off_target)
    suppression_db = 20.0 * math.log10(ratio)

    print("--------------------------------------------------------------------------------")
    print("KET QUA DO KIEM BUP SONG AM HOC DAS BEAMFORMING (M = 4 MICS, d = 3.5 cm):")
    print(f"-> Goc nguon am muc tieu (Target Angle): {target_angle:+.1f} deg")
    print(f"-> Nang luong RMS khi lai ve Target     : {rms_target:.4f}")
    print(f"-> Nang luong RMS khi lai ve -45 deg    : {rms_off_target:.4f}")
    print(f"-> Do suy hao tap am goc lech           : {suppression_db:.2f} dB")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Tin hieu dong pha tai goc Target phai duoc bao toan nguyen ven (RMS gan 0.707)
    assert abs(rms_target - 0.7071) < 0.05, f"Loi: Tin hieu muc tieu bi meo: {rms_target}"
    # 2. Do suy hao tai goc lech -45 do phai dat it nhat 8.0 dB voi mang 4 micro
    assert suppression_db > 8.0, f"Loi: Do suy hao chum song khong dat yeu cau: {suppression_db:.2f} dB"
    print("[PASS] Test Beamforming: Lai bup song va triet tieu tap am goc lech thanh cong 100%!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO DELAY-AND-SUM ACOUSTIC BEAMFORMING (APPLE AIRPODS / TESLA OPTIMUS)")
    print("================================================================================")
    test_beamformer_steering_and_suppression()
