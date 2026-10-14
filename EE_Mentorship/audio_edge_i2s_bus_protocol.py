"""
================================================================================
CHUYEN DE AF: HARDWARE AUDIO DSP & I2S / PDM MICROPHONE BEAMFORMING
BAI 1: GIAO THUC BUS AM THANH SO I2S VA MA HOA GIAI MA STEREO 24-BIT PCM
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Ky su Phan cung Audio & Chip Design tai Apple / Tesla / Qualcomm
Ngon ngu: Python 3 thuan tuy, mo phong bit-level phan cung giao tiep I2S
================================================================================
"""

import math
from typing import Tuple, List, Dict

# ------------------------------------------------------------------------------
# 1. CAC DINH NGHIA VA THONG SO PHAN CUNG BUS I2S (PHILIPS STANDARD)
# ------------------------------------------------------------------------------

class I2SConfig:
    """
    Cau hinh chuan giao tiep phan cung I2S:
    - BCLK (Bit Clock): Xung nhip truyen tung bit du lieu.
    - WS / LRCLK (Word Select / Left-Right Clock):
        WS = 0 -> Kenh Trai (Left Channel)
        WS = 1 -> Kenh Phai (Right Channel)
    - SD (Serial Data): Du lieu noi tiep truyen bit MSB truoc.
      Dac trung chuan Philips: Bit MSB xuat hien sau canh len WS 1 chu ky BCLK (1-bit delay).
    """
    def __init__(self,
                 sample_rate: int = 48000,    # Tan so lay mau 48 kHz (chuan Audio chuyen nghiep)
                 bit_depth: int = 24,          # Do phan giai 24-bit PCM
                 slot_width: int = 32):        # Khung truyen moi kenh 32-bit (chua 24-bit data + 8-bit padding)
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.slot_width = slot_width
        # Tan so BCLK = Fs * So_kenh * Slot_width = 48000 * 2 * 32 = 3.072 MHz
        self.bclk_frequency = sample_rate * 2 * slot_width

# ------------------------------------------------------------------------------
# 2. HAM XU LY BIT BOI PHAN CUNG: CHUYEN DOI BU HAI (TWO'S COMPLEMENT)
# ------------------------------------------------------------------------------

def pcm_to_twos_complement_bits(sample: int, bit_depth: int = 24) -> List[int]:
    """
    Chuyen doi so nguyen co dau sang chuoi bit ma bu hai (Two's complement) MSB -> LSB.
    Khoang gia tri 24-bit: -8,388,608 den +8,388,607.
    """
    max_val = (1 << (bit_depth - 1)) - 1
    min_val = -(1 << (bit_depth - 1))
    
    # Kẹp giá trị (Clamp/Saturate) chống tràn số
    clamped = max(min_val, min(max_val, sample))
    
    if clamped < 0:
        val = (1 << bit_depth) + clamped
    else:
        val = clamped
        
    bits = []
    for i in range(bit_depth - 1, -1, -1):
        bits.append((val >> i) & 1)
    return bits

def twos_complement_bits_to_pcm(bits: List[int], bit_depth: int = 24) -> int:
    """
    Giai ma chuoi bit bu hai tro ve so nguyen co dau (Signed PCM sample).
    """
    val = 0
    for b in bits:
        val = (val << 1) | b
        
    sign_bit = 1 << (bit_depth - 1)
    if val & sign_bit:
        # So am trong ma bu 2
        return val - (1 << bit_depth)
    return val

# ------------------------------------------------------------------------------
# 3. TRINH PHAT I2S TRANSMITTER (SERIALIZER) VA TRINH THU RECEIVER (DESERIALIZER)
# ------------------------------------------------------------------------------

class I2STransmitter:
    """
    Module phan cung I2S TX: Bien doi mau am thanh Stereo song song (Parallel)
    thanh luong bit noi tiep (Serial Bitstream) tren duong truyen SD.
    """
    def __init__(self, config: I2SConfig):
        self.cfg = config

    def encode_frame(self, left_sample: int, right_sample: int) -> List[Tuple[int, int, int]]:
        """
        Ma hoa 1 khung Stereo (1 chu ky WS = 2 slots = 64 chu ky BCLK):
        Tra ve danh sach cac tuple (BCLK_level, WS_level, SD_level) cho moi chu ky xung nhip.
        Chuan Philips I2S:
          - Slot Left: WS = 0. Sau khi WS chuyen sang 0, bit dau tien giu delay 1 BCLK, roi den MSB..LSB.
          - Slot Right: WS = 1. Sau khi WS chuyen sang 1, tre 1 BCLK roi den MSB..LSB.
        """
        left_bits = pcm_to_twos_complement_bits(left_sample, self.cfg.bit_depth)
        right_bits = pcm_to_twos_complement_bits(right_sample, self.cfg.bit_depth)

        # Them cac bit pad zero vao duoi neu slot_width > bit_depth (vi du 32-bit slot chua 24-bit)
        padding_zeros = [0] * (self.cfg.slot_width - self.cfg.bit_depth)
        left_payload = left_bits + padding_zeros
        right_payload = right_bits + padding_zeros

        stream: List[Tuple[int, int, int]] = []

        # Slot Trai (Left Channel, WS = 0)
        # Chu ky dau tien cua slot: 1-bit delay (I2S standard)
        stream.append((1, 0, 0)) # BCLK=1, WS=0, SD=0 (delay slot)
        for bit in left_payload[:-1]:
            stream.append((1, 0, bit))

        # Slot Phai (Right Channel, WS = 1)
        # Chu ky dau tien cua slot Right chua bit cuoi cung cua Left payload (hoac delay)
        last_left_bit = left_payload[-1]
        stream.append((1, 1, last_left_bit))
        for bit in right_payload[:-1]:
            stream.append((1, 1, bit))

        return stream

class I2SReceiver:
    """
    Module phan cung I2S RX: Giai ma luong bit tu cac duong BCLK, WS, SD
    thanh cac mau am thanh Stereo 24-bit PCM hoan chinh.
    """
    def __init__(self, config: I2SConfig):
        self.cfg = config
        self.current_ws = 0
        self.bit_counter = 0
        self.shift_reg = 0
        self.received_frames: List[Tuple[int, int]] = []
        
        self.left_sample_temp = 0
        self.right_sample_temp = 0

    def parse_stream(self, stream: List[Tuple[int, int, int]]) -> List[Tuple[int, int]]:
        """
        Mo phong may trang thai may thu I2S (I2S Hardware State Machine):
        Lay mau du lieu SD tai canh len cua BCLK.
        """
        recovered_samples: List[Tuple[int, int]] = []
        left_bits_collected: List[int] = []
        right_bits_collected: List[int] = []

        prev_ws = stream[0][1]
        slot_bit_idx = 0

        for bclk, ws, sd in stream:
            # Phat hien su thay doi canh cua WS (Left/Right transition)
            if ws != prev_ws:
                slot_bit_idx = 0
                prev_ws = ws

            # Theo chuan I2S, bo qua chu ky dau tien cua slot (1 BCLK delay)
            if slot_bit_idx == 0:
                slot_bit_idx += 1
                continue

            # Thu thap cac bit du lieu chinh (24-bit MSB first)
            data_idx = slot_bit_idx - 1
            if data_idx < self.cfg.bit_depth:
                if ws == 0:
                    left_bits_collected.append(sd)
                else:
                    right_bits_collected.append(sd)

            slot_bit_idx += 1

            # Khi da thu du 24 bit cho ca Left va Right
            if len(left_bits_collected) == self.cfg.bit_depth and len(right_bits_collected) == self.cfg.bit_depth:
                l_val = twos_complement_bits_to_pcm(left_bits_collected, self.cfg.bit_depth)
                r_val = twos_complement_bits_to_pcm(right_bits_collected, self.cfg.bit_depth)
                recovered_samples.append((l_val, r_val))
                left_bits_collected.clear()
                right_bits_collected.clear()

        return recovered_samples

# ------------------------------------------------------------------------------
# 4. MO PHONG VA KIEM CHUNG CHUAN XAC BUS I2S
# ------------------------------------------------------------------------------

def test_i2s_twos_complement():
    """Kiem tra 1: Chuyen doi ma bu 2 cho cac gia tri gioi han 24-bit."""
    test_cases = [0, 1, -1, 1000, -1000, 8388607, -8388608]
    for val in test_cases:
        bits = pcm_to_twos_complement_bits(val, bit_depth=24)
        recovered = twos_complement_bits_to_pcm(bits, bit_depth=24)
        assert recovered == val, f"Loi bu 2: goc {val} != khoi phuc {recovered}"
    print("[PASS] Test 1: Two's complement 24-bit codec verified with 100% precision.")

def test_i2s_stereo_loopback():
    """
    Kiem tra 2: Phat va thu am thanh Stereo qua bus I2S:
    - Kenh Trai: Song sin tan so 440 Hz (Note A4)
    - Kenh Phai: Song sin tan so 880 Hz (Note A5)
    Tan so lay mau 48 kHz, thoi gian 0.005s (240 mau).
    """
    cfg = I2SConfig(sample_rate=48000, bit_depth=24, slot_width=32)
    tx = I2STransmitter(cfg)
    rx = I2SReceiver(cfg)

    duration = 0.005 # 5 ms
    num_samples = int(cfg.sample_rate * duration)
    amplitude = 4000000 # Bien do am thanh 24-bit

    original_stereo_pairs: List[Tuple[int, int]] = []
    full_bitstream: List[Tuple[int, int, int]] = []

    for n in range(num_samples):
        t = n / cfg.sample_rate
        # Kenh trai 440 Hz
        left_val = int(amplitude * math.sin(2.0 * math.pi * 440.0 * t))
        # Kenh phai 880 Hz
        right_val = int(amplitude * math.sin(2.0 * math.pi * 880.0 * t))

        original_stereo_pairs.append((left_val, right_val))
        frame_bits = tx.encode_frame(left_val, right_val)
        full_bitstream.extend(frame_bits)

    # Thu va giai ma bitstream
    recovered_pairs = rx.parse_stream(full_bitstream)

    assert len(recovered_pairs) == len(original_stereo_pairs), (
        f"Loi so luong mau: Goc {len(original_stereo_pairs)} != Thu {len(recovered_pairs)}"
    )

    for i in range(len(original_stereo_pairs)):
        orig_l, orig_r = original_stereo_pairs[i]
        rec_l, rec_r = recovered_pairs[i]
        assert orig_l == rec_l, f"Loi kenh Trai tai mau {i}: {orig_l} != {rec_l}"
        assert orig_r == rec_r, f"Loi kenh Phai tai mau {i}: {orig_r} != {rec_r}"

    print(f"[PASS] Test 2: I2S Loopback Stereo verified successfully: {num_samples} samples recovered bit-exact!")
    print(f"       Total BCLK cycles simulated: {len(full_bitstream)} cycles @ 3.072 MHz.")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO HARDWARE AUDIO I2S BUS PROTOCOL & 24-BIT STEREO CODEC")
    print("================================================================================")
    test_i2s_twos_complement()
    test_i2s_stereo_loopback()
    print("--------------------------------------------------------------------------------")
    print("All I2S verification tests PASSED successfully with zero bit errors!")
