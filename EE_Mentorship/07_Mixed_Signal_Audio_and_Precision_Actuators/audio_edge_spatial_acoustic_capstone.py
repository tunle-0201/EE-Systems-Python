"""
================================================================================
CHUYEN DE AF: HARDWARE AUDIO DSP & I2S / PDM MICROPHONE BEAMFORMING
BAI 4: DONG CO THU AM KHONG GIAN VA LOC CHUM SONG BEAMFORMING CAPSTONE
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Tich hop toan chuoi Audio DSP cho Apple AirPods Pro & Tesla Cabin Voice
Ngon ngu: Python 3 thuan tuy, kien truc Module huong doi tuong thoi gian thuc
================================================================================
"""

import math
from typing import List, Tuple, Dict

from audio_edge_i2s_bus_protocol import (
    I2SConfig, I2STransmitter, I2SReceiver
)
from audio_edge_pdm_cic_decimation import (
    SigmaDeltaModulator1stOrder, CICDecimator3rdOrder
)
from audio_edge_microphone_beamforming import (
    MicrophoneArrayConfig, DelayAndSumBeamformer, fractional_delay_interpolate
)

# ------------------------------------------------------------------------------
# 1. BO LOC SO IIR BIQUAD BANDPASS (DAI THONG GIONG NOI 300 Hz - 3400 Hz)
# ------------------------------------------------------------------------------

class IIRBiquadBandpass:
    """
    Bo loc so IIR Biquad bac 2 (Direct Form II Transposed) loc thong dai tieng noi:
    fc = 1500 Hz, Q = 1.0, Fs = 48000 Hz.
    Triet tieu tieng ri am tram (Rumble < 200 Hz) va tieng rit cao tan (> 4000 Hz).
    """
    def __init__(self, f_center: float = 1500.0, Q: float = 1.0, fs: float = 48000.0):
        w0 = 2.0 * math.pi * f_center / fs
        alpha = math.sin(w0) / (2.0 * Q)

        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * math.cos(w0)
        a2 = 1.0 - alpha

        # Chuan hoa he so theo a0
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0

        # Bo nho trang thai tre
        self.z1 = 0.0
        self.z2 = 0.0

    def process_sample(self, x: float) -> float:
        """Loc 1 mau am thanh theo cau truc Transposed Direct Form II."""
        y = self.b0 * x + self.z1
        self.z1 = self.b1 * x - self.a1 * y + self.z2
        self.z2 = self.b2 * x - self.a2 * y
        return y

# ------------------------------------------------------------------------------
# 2. DONG CO THU AM KHONG GIAN TOAN CHUOI (SPATIAL ACOUSTIC CAPSTONE ENGINE)
# ------------------------------------------------------------------------------

class SpatialAcousticEngine:
    """
    Dong co thu am thanh khong gian tich hop toan chuoi:
    1. Mang 4 Micro MEMS PDM @ 3.072 MHz
    2. 4 Bo loc CIC Decimator 3rd-order (3.072 MHz -> 48 kHz PCM)
    3. Mang Beamformer Delay-and-Sum khoa bup song ve nguoi lai xe
    4. Bo loc tieng noi IIR Biquad Bandpass Filter
    5. Bo dong goi xuat bus I2S 24-bit Stereo
    """
    def __init__(self,
                 target_steer_deg: float = 25.0,
                 num_mics: int = 4,
                 mic_spacing: float = 0.035):
        self.num_mics = num_mics
        self.array_cfg = MicrophoneArrayConfig(num_mics=num_mics, mic_spacing=mic_spacing, sample_rate=48000)
        self.target_steer_rad = math.radians(target_steer_deg)

        # 4 bo loc CIC cho 4 kenh micro
        self.cic_filters = [CICDecimator3rdOrder(R=64, N=3, M=1) for _ in range(num_mics)]

        # Bo dinh huong chum song
        self.beamformer = DelayAndSumBeamformer(self.array_cfg)

        # Bo loc IIR Bandpass
        self.biquad = IIRBiquadBandpass(f_center=1500.0, Q=1.0, fs=48000.0)

        # Trinh phat I2S xuat tin hieu sang chip DSP
        self.i2s_cfg = I2SConfig(sample_rate=48000, bit_depth=24, slot_width=32)
        self.i2s_tx = I2STransmitter(self.i2s_cfg)

    def process_pdm_bitstream(self,
                              multichannel_pdm_bits: List[List[int]]) -> Tuple[List[float], List[Tuple[int, int, int]]]:
        """
        multichannel_pdm_bits: Danh sach 4 luong bit PDM tu 4 micro MEMS.
        Tra ve:
          - beamformed_audio: Tin hieu am thanh da bup song va loc sach
          - i2s_bitstream: Luong bit truyen tren bus phan cung I2S
        """
        total_pdm_bits = len(multichannel_pdm_bits[0])
        pcm_channels: List[List[float]] = [[] for _ in range(self.num_mics)]

        # Buoc 1: CIC Decimation cho tung micro
        for bit_idx in range(total_pdm_bits):
            for m in range(self.num_mics):
                bit = multichannel_pdm_bits[m][bit_idx]
                has_out, pcm_val = self.cic_filters[m].process_pdm_sample(bit)
                if has_out:
                    # Chuan hoa ve [-1.0, +1.0]
                    pcm_channels[m].append(pcm_val / 32768.0)

        # Buoc 2: Delay-and-Sum Beamforming dinh huong nguoi lai xe
        beamformed_raw = self.beamformer.process(pcm_channels, self.target_steer_rad)

        # Buoc 3: IIR Biquad Voice Bandpass Filtering
        filtered_audio: List[float] = []
        for s in beamformed_raw:
            filtered_audio.append(self.biquad.process_sample(s))

        # Buoc 4: Ma hoa xuat ra bus I2S Stereo (Kenh trai = Clean Speech, Kenh phai = Mic 0 Raw)
        full_i2s_stream: List[Tuple[int, int, int]] = []
        for i in range(len(filtered_audio)):
            # Chuyen thanh so nguyen 24-bit
            clean_int24 = int(filtered_audio[i] * 8000000.0)
            raw_mic0_int24 = int(pcm_channels[0][i] * 8000000.0)

            frame = self.i2s_tx.encode_frame(clean_int24, raw_mic0_int24)
            full_i2s_stream.extend(frame)

        return (filtered_audio, full_i2s_stream)

# ------------------------------------------------------------------------------
# 3. KICH BAN MO PHONG CAPSTONE: KHU TAP AM CABIN XE TESLA
# ------------------------------------------------------------------------------

def simulate_car_cabin_environment():
    """
    Kich ban kiem thu khong gian am hoc cabin xe Tesla / Apple AirPods Pro:
    - Nguoi lai xe (Target Voice) o goc +25 do: Tan so 1200 Hz, bien do am thanh 0.35.
    - Tieng on tieng coi xe ngoai duong (Noise Jammer) o goc -40 do: Tan so 2500 Hz, bien do manh 0.70.
    Mo phong 15 ms am thanh: 720 mau PCM @ 48 kHz -> 46,080 bit PDM @ 3.072 MHz cho moi micro.
    """
    num_mics = 4
    engine = SpatialAcousticEngine(target_steer_deg=25.0, num_mics=num_mics)

    fs_pcm = 48000
    r_decim = 64
    fs_pdm = fs_pcm * r_decim # 3,072,000 Hz
    num_pcm_samples = 720
    total_pdm_bits = num_pcm_samples * r_decim

    target_angle_rad = math.radians(25.0)
    noise_angle_rad = math.radians(-40.0)

    # Tao bo dieu che Sigma-Delta cho tung micro de sinh tin hieu PDM
    modulators = [SigmaDeltaModulator1stOrder() for _ in range(num_mics)]
    multichannel_pdm: List[List[int]] = [[] for _ in range(num_mics)]

    print("================================================================================")
    print("BAT DAU MO PHONG SPATIAL ACOUSTIC BEAMFORMING ENGINE (CAPSTONE)")
    print("================================================================================")
    print(f"Tan so PDM: {fs_pdm / 1e6:.3f} MHz | PCM Fs: {fs_pcm / 1e3:.1f} kHz | So Micro MEMS: {num_mics}")
    print("Nguon am: Nguoi lai xe @ +25 deg (1200 Hz) | Tieng on @ -40 deg (2500 Hz, Bien do x2)")
    print("--------------------------------------------------------------------------------")

    for bit_idx in range(total_pdm_bits):
        t = bit_idx / fs_pdm

        for m in range(num_mics):
            # Tre lan truyen am hoc cho micro m
            tau_target = engine.array_cfg.get_time_delay(m, target_angle_rad)
            tau_noise = engine.array_cfg.get_time_delay(m, noise_angle_rad)

            # Tin hieu giong noi muc tieu
            s_target = 0.35 * math.sin(2.0 * math.pi * 1200.0 * (t - tau_target))
            # Tin hieu tap am ngoai cabin
            s_noise = 0.70 * math.sin(2.0 * math.pi * 2500.0 * (t - tau_noise))

            # Tong am thanh di vao mang rung micro
            acoustic_in = s_target + s_noise
            # Clamp [-1.0, 1.0]
            acoustic_in = max(-1.0, min(1.0, acoustic_in))

            pdm_bit = modulators[m].step(acoustic_in)
            multichannel_pdm[m].append(pdm_bit)

    # Chay toan chuoi Spatial Acoustic Engine
    filtered_audio, i2s_stream = engine.process_pdm_bitstream(multichannel_pdm)

    # Tinh toan nang luong am thanh truoc va sau khi loc (bo qua 50 mau khoi dong)
    steady_filtered = filtered_audio[50:]
    rms_output = math.sqrt(sum(x * x for x in steady_filtered) / len(steady_filtered))

    # Giai ma I2S de xac minh tinh toan ven bus phan cung
    i2s_rx = I2SReceiver(engine.i2s_cfg)
    recovered_i2s_frames = i2s_rx.parse_stream(i2s_stream)

    print("--------------------------------------------------------------------------------")
    print("KET QUA TRICH XUAT GIONG NOI VA LOC CHUM SONG KHONG GIAN:")
    print(f"-> So luong mau PCM thu duoc        : {len(filtered_audio)} mau")
    print(f"-> Nang luong RMS giong noi sach     : {rms_output:.4f} (Ly thuyet tin hieu goc: ~0.247)")
    print(f"-> So luong khung truyen I2S giai ma : {len(recovered_i2s_frames)} frames (Khop 100%)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Nang luong giong noi mong muon (1200 Hz bien do 0.35 -> RMS thuan sin = 0.35 / sqrt(2) = 0.247)
    # Nho triet tieu tap am goc lech -40 deg, RMS ngõ ra phai hoi tu ve quanh 0.20 - 0.28!
    assert 0.15 <= rms_output <= 0.32, f"Loi: Nang luong giong noi sau loc khong hop ly: {rms_output}"
    # 2. Khung truyen I2S phai khop hoan toan so luong mau am thanh
    assert len(recovered_i2s_frames) == len(filtered_audio), "Loi: Khung truyen I2S bi mat mau!"
    print("[PASS] Capstone Spatial Acoustic Engine: Bup song dinh huong va loc tap am thanh cong tuyet doi!")

if __name__ == "__main__":
    simulate_car_cabin_environment()
