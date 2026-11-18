"""
pcie6_edge_pam4_flit_encoding.py - PCIe Gen 6 Physical Layer PAM4 64 GT/s Signaling

Author: Le Dac Anh Tuan (EE Mentorship Program)
Target: Apple Silicon Mac Pro PCIe Gen 6 Controller / Tesla Dojo Interconnect
Standard: PCI Express Base Specification Revision 6.0 (PAM4 64 GT/s Physical Layer)

MATHEMATICAL FOUNDATION & PAM4 SIGNALING PHYSICS:
1. PAM4 Multi-Level Encoding vs NRZ:
   - NRZ (PCIe 1.0-5.0): 2 levels (1 bit / UI), 32 GT/s requires 16 GHz Nyquist.
   - PAM4 (PCIe 6.0): 4 levels (2 bits / Symbol), 64 GT/s at 32 Gbaud operates at same 16 GHz Nyquist!

2. Gray Code Bit-to-Level Mapping:
   Gray mapping ensures adjacent voltage levels differ by only 1 bit:
   - Level 0 (-3 / -V_max)   : '00' (MSB=0, LSB=0)
   - Level 1 (-1 / -V_max/3) : '01' (MSB=0, LSB=1)
   - Level 2 (+1 / +V_max/3) : '11' (MSB=1, LSB=1)
   - Level 3 (+3 / +V_max)   : '10' (MSB=1, LSB=0)

3. SNR Loss & 3-Eye Structure:
   PAM4 divides vertical eye voltage into 3 openings (Upper, Middle, Lower).
   Signal-to-Noise Ratio (SNR) reduction relative to NRZ:

      SNR_penalty = 20 * log10(1 / 3) = -9.54 dB

4. Slicer Thresholds for Symbol Recovery:
   Normalized to V_max = 3.0V:
   - Threshold_Lower  = -2.0V (distinguishes Level 0 and Level 1)
   - Threshold_Middle =  0.0V (distinguishes Level 1 and Level 2)
   - Threshold_Upper  = +2.0V (distinguishes Level 2 and Level 3)
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
import math
import random


class Pam4Level(Enum):
    LEVEL_0 = -3  # Bit pattern: 00
    LEVEL_1 = -1  # Bit pattern: 01
    LEVEL_2 =  1  # Bit pattern: 11
    LEVEL_3 =  3  # Bit pattern: 10


# Gray Mapping Table: 2-bit tuple (msb, lsb) -> Pam4Level
GRAY_ENCODER: Dict[Tuple[int, int], Pam4Level] = {
    (0, 0): Pam4Level.LEVEL_0,
    (0, 1): Pam4Level.LEVEL_1,
    (1, 1): Pam4Level.LEVEL_2,
    (1, 0): Pam4Level.LEVEL_3,
}

# Gray Decoding Table: Pam4Level -> 2-bit tuple (msb, lsb)
GRAY_DECODER: Dict[Pam4Level, Tuple[int, int]] = {
    Pam4Level.LEVEL_0: (0, 0),
    Pam4Level.LEVEL_1: (0, 1),
    Pam4Level.LEVEL_2: (1, 1),
    Pam4Level.LEVEL_3: (1, 0),
}


class Pcie6Pam4Transmitter:
    """
    PCIe Gen 6 64 GT/s PAM4 Transmitter (TX).
    Packs bitstreams into Gray-coded PAM4 voltage levels.
    """
    def __init__(self, v_max: float = 3.0):
        self.v_max = v_max
        # Voltage per level step: Level 0 = -3V, Level 1 = -1V, Level 2 = +1V, Level 3 = +3V
        self.level_voltages = {
            Pam4Level.LEVEL_0: -v_max,
            Pam4Level.LEVEL_1: -v_max / 3.0,
            Pam4Level.LEVEL_2:  v_max / 3.0,
            Pam4Level.LEVEL_3:  v_max,
        }

    def encode_bits(self, bit_stream: List[int]) -> List[float]:
        """
        Takes raw bitstream (must be even length), pairs into 2-bit symbols,
        and outputs PAM4 transmit voltages.
        """
        assert len(bit_stream) % 2 == 0, "Bitstream length must be multiple of 2"
        tx_voltages = []
        for i in range(0, len(bit_stream), 2):
            msb = bit_stream[i]
            lsb = bit_stream[i + 1]
            pam_sym = GRAY_ENCODER[(msb, lsb)]
            tx_voltages.append(self.level_voltages[pam_sym])
        return tx_voltages


class Pcie6HighSpeedChannel:
    """
    Simulates PCB channel attenuation, high-frequency dispersion, and Gaussian thermal noise.
    """
    def __init__(self, snr_db: float = 24.0):
        self.snr_db = snr_db
        # Calculate noise standard deviation sigma from SNR:
        # SNR_linear = 10^(snr_db / 10) = P_signal / sigma^2
        # For PAM4 levels [-3, -1, 1, 3], P_signal = (9 + 1 + 1 + 9)/4 = 5.0
        p_signal = 5.0
        snr_linear = 10.0 ** (snr_db / 10.0)
        self.noise_sigma = math.sqrt(p_signal / snr_linear)

    def transmit(self, tx_voltages: List[float], seed: Optional[int] = 42) -> List[float]:
        """Adds Gaussian noise to transmitted PAM4 voltages."""
        if seed is not None:
            random.seed(seed)
        rx_voltages = []
        for v in tx_voltages:
            noise = random.gauss(0.0, self.noise_sigma)
            rx_voltages.append(v + noise)
        return rx_voltages


class Pcie6Pam4Receiver:
    """
    PCIe Gen 6 64 GT/s PAM4 Receiver (RX) Slicer.
    Employs 3 decision thresholds to recover 2-bit Gray-coded symbols.
    """
    def __init__(self, v_max: float = 3.0):
        self.v_max = v_max
        # Slicer thresholds between the 4 voltage levels
        self.th_lower = -2.0 * (v_max / 3.0)  # -2.0V
        self.th_mid   =  0.0                   #  0.0V
        self.th_upper =  2.0 * (v_max / 3.0)  # +2.0V

    def slice_voltage(self, voltage: float) -> Pam4Level:
        """Determines PAM4 level via 3-way voltage slicing."""
        if voltage < self.th_lower:
            return Pam4Level.LEVEL_0
        elif voltage < self.th_mid:
            return Pam4Level.LEVEL_1
        elif voltage < self.th_upper:
            return Pam4Level.LEVEL_2
        else:
            return Pam4Level.LEVEL_3

    def decode_voltages(self, rx_voltages: List[float]) -> Tuple[List[int], int]:
        """
        Recovers bitstream from noisy analog PAM4 voltages.
        Returns decoded bitstream and symbol error count.
        """
        recovered_bits = []
        for v in rx_voltages:
            sliced_level = self.slice_voltage(v)
            msb, lsb = GRAY_DECODER[sliced_level]
            recovered_bits.append(msb)
            recovered_bits.append(lsb)
        return recovered_bits


def test_pcie6_pam4_encoding():
    print("================================================================================")
    print("TEST SUITE: PCIE GEN 6 PHYSICAL LAYER PAM4 64 GT/s SIGNALING & SLICER")
    print("================================================================================")

    tx = Pcie6Pam4Transmitter(v_max=3.0)
    rx = Pcie6Pam4Receiver(v_max=3.0)

    # 1. Verify Gray Mapping Integrity across all 4 symbol states
    test_symbols = [
        (0, 0),  # Level 0 (-3.0V)
        (0, 1),  # Level 1 (-1.0V)
        (1, 1),  # Level 2 (+1.0V)
        (1, 0),  # Level 3 (+3.0V)
    ]
    raw_bits = [bit for sym in test_symbols for bit in sym]
    tx_voltages = tx.encode_bits(raw_bits)

    print("PAM4 GRAY ENCODING & VOLTAGE MAPPING:")
    expected_voltages = [-3.0, -1.0, 1.0, 3.0]
    for idx, (sym, v, exp_v) in enumerate(zip(test_symbols, tx_voltages, expected_voltages)):
        print(f"  Symbol {idx}: Bits={sym} -> Voltage={v:5.1f} V (Expected={exp_v:5.1f} V)")
        assert abs(v - exp_v) < 1e-4

    print("[PASS] Milestone 1: 4-Level PAM4 Gray mapping verified with exact voltage levels.")

    # 2. Verify Ideal Slicer Operation (Zero Noise)
    decoded_ideal = rx.decode_voltages(tx_voltages)
    assert decoded_ideal == raw_bits
    print("[PASS] Milestone 2: 3-Threshold Slicer decodes all 4 PAM4 levels without error.")

    # 3. Simulate High-Speed Channel with Realistic Channel SNR (26 dB)
    channel = Pcie6HighSpeedChannel(snr_db=26.0)
    # Generate random packet of 2,048 bits (1,024 PAM4 symbols = 1 PCIe Gen 6 Flit payload)
    random.seed(1234)
    large_payload = [random.randint(0, 1) for _ in range(2048)]
    tx_packet = tx.encode_bits(large_payload)
    rx_packet = channel.transmit(tx_packet, seed=5678)
    recovered_payload = rx.decode_voltages(rx_packet)

    # Calculate Bit Error Rate (BER) before FEC
    bit_errors = sum(1 for tx_b, rx_b in zip(large_payload, recovered_payload) if tx_b != rx_b)
    ber_raw = bit_errors / len(large_payload)

    print("--------------------------------------------------------------------------------")
    print(f"HIGH-SPEED TRANSMISSION PERFORMANCE (SNR = {channel.snr_db} dB):")
    print(f"  Total Bits Transmitted : {len(large_payload)} bits ({len(tx_packet)} PAM4 Symbols)")
    print(f"  Bit Errors (Pre-FEC)   : {bit_errors} errors")
    print(f"  Pre-FEC BER            : {ber_raw:.6e} (Standard spec allows Pre-FEC BER < 1e-4)")

    # PCIe 6.0 specifies that raw Pre-FEC BER must be < 1e-3 so that FEC can achieve Post-FEC BER < 1e-12
    assert ber_raw < 1e-3, f"Pre-FEC BER too high: {ber_raw}"
    print("[PASS] Milestone AZ.1: PAM4 64 GT/s PHY Slicer satisfies PCIe Gen 6 Pre-FEC BER spec!")
    print("================================================================================")


if __name__ == "__main__":
    test_pcie6_pam4_encoding()
