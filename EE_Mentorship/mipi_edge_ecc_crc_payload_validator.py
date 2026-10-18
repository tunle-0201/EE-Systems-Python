"""
MIPI CSI-2 ECC SECDED Error Correction & RAW12 Payload Packing Validator
Chuyen de 23: MIPI CSI-2 Camera Serial Interface & D-PHY Hardware Pipeline
Milestone AJ.3 - Bai hoc 90 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Thiet ke bo giai ma va sua sai ECC Hamming SECDED (Single Error Correction, Double Error Detection).
- Thuat toan dong goi va giai nen diem anh cam bien RAW12 (2 pixels / 3 bytes).
- Kiem tra toan ven CRC-16 Payload va mo phong kha nang chong nhieu tia buc xa va xung dien EMI.
"""

import struct
from typing import List, Tuple, Dict, Optional


# Bang tra Syndrome sang vi tri bit loi cua MIPI CSI-2
# Syndrome S[5:0] tuong ung voi vi tri bit bi lat (D0..D23 hoac P0..P5)
SYNDROME_LOOKUP_TABLE = {
    # Parity bits loi don le
    0x01: ("PARITY", 0),
    0x02: ("PARITY", 1),
    0x04: ("PARITY", 2),
    0x08: ("PARITY", 3),
    0x10: ("PARITY", 4),
    0x20: ("PARITY", 5),
    
    # Data bits D[23:0] loi don le
    0x07: ("DATA", 0),   # P0, P1, P2
    0x0B: ("DATA", 1),   # P0, P1, P3
    0x0D: ("DATA", 2),   # P0, P2, P3
    0x0E: ("DATA", 3),   # P1, P2, P3
    0x13: ("DATA", 4),   # P0, P1, P4
    0x15: ("DATA", 5),   # P0, P2, P4
    0x16: ("DATA", 6),   # P1, P2, P4
    0x19: ("DATA", 7),   # P0, P3, P4
    0x1A: ("DATA", 8),   # P1, P3, P4
    0x1C: ("DATA", 9),   # P2, P3, P4
    0x17: ("DATA", 10),  # P0, P1, P2, P4
    0x1B: ("DATA", 11),  # P0, P1, P3, P4
    0x1D: ("DATA", 12),  # P0, P2, P3, P4
    0x1E: ("DATA", 13),  # P1, P2, P3, P4
    0x1F: ("DATA", 14),  # P0, P1, P2, P3, P4
    0x0F: ("DATA", 15),  # P0, P1, P2, P3
    0x23: ("DATA", 16),  # P0, P1, P5
    0x25: ("DATA", 17),  # P0, P2, P5
    0x26: ("DATA", 18),  # P1, P2, P5
    0x29: ("DATA", 19),  # P0, P3, P5
    0x2A: ("DATA", 20),  # P1, P3, P5
    0x2C: ("DATA", 21),  # P2, P3, P5
    0x27: ("DATA", 22),  # P0, P1, P2, P5
    0x2B: ("DATA", 23)   # P0, P1, P3, P5
}


def calculate_mipi_parity(data24: int) -> int:
    """
    Tinh 6 bits parity P[5:0] cho 24-bit du lieu Header.
    """
    p0_mask = 0x0F12B7
    p1_mask = 0x0F255B
    p2_mask = 0x0739CD
    p3_mask = 0x0B7F0E
    p4_mask = 0xC0FFF0
    p5_mask = 0xFF0000

    def parity(val: int) -> int:
        return bin(val).count('1') % 2

    p0 = parity(data24 & p0_mask)
    p1 = parity(data24 & p1_mask)
    p2 = parity(data24 & p2_mask)
    p3 = parity(data24 & p3_mask)
    p4 = parity(data24 & p4_mask)
    p5 = parity(data24 & p5_mask)

    return p0 | (p1 << 1) | (p2 << 2) | (p3 << 3) | (p4 << 4) | (p5 << 5)


class Csi2EccDecoder:
    """
    Bo giai ma sua sai ECC SECDED cho Header MIPI CSI-2 tren phan cung RX.
    """
    @staticmethod
    def decode_and_correct(header_bytes: bytes) -> Dict[str, any]:
        """
        Dau vao: 4 bytes [DI, D1, D2, ECC].
        Dau ra: Dict chua trang thai kiem tra (NO_ERROR, SINGLE_ERROR_CORRECTED, DOUBLE_ERROR_DETECTED)
        va 3 bytes du lieu da duoc sua loi (neu co).
        """
        if len(header_bytes) != 4:
            raise ValueError("Header phai gom dung 4 bytes!")

        di, d1, d2, ecc_received = struct.unpack("<BBBB", header_bytes)
        data24 = di | (d1 << 8) | (d2 << 16)
        
        # Tinh toan parity tren du lieu nhan duoc
        computed_parity = calculate_mipi_parity(data24)
        received_parity = ecc_received & 0x3F  # Chi lay 6 bits P[5:0]
        
        # Tinh Syndrome: S = P_computed XOR P_received
        syndrome = computed_parity ^ received_parity

        if syndrome == 0:
            return {
                "status": "NO_ERROR",
                "corrected_bytes": bytes([di, d1, d2]),
                "bit_corrected": None,
                "syndrome": 0x00
            }

        # Kiem tra trong bang tra syndrome
        if syndrome in SYNDROME_LOOKUP_TABLE:
            error_type, bit_idx = SYNDROME_LOOKUP_TABLE[syndrome]
            if error_type == "DATA":
                # Lat nguoc lai bit bi sai trong 24-bit data de sua loi
                corrected_data24 = data24 ^ (1 << bit_idx)
                c_di = corrected_data24 & 0xFF
                c_d1 = (corrected_data24 >> 8) & 0xFF
                c_d2 = (corrected_data24 >> 16) & 0xFF
                return {
                    "status": "SINGLE_ERROR_CORRECTED",
                    "corrected_bytes": bytes([c_di, c_d1, c_d2]),
                    "bit_corrected": f"DATA_BIT_{bit_idx}",
                    "syndrome": syndrome
                }
            else:
                # Loi bit parity, du lieu data24 van dung nguyen ven
                return {
                    "status": "SINGLE_ERROR_CORRECTED",
                    "corrected_bytes": bytes([di, d1, d2]),
                    "bit_corrected": f"PARITY_BIT_{bit_idx}",
                    "syndrome": syndrome
                }
        else:
            # Syndrome khong nam trong bang tra loi don -> Loi kep (Double Error Detected)
            return {
                "status": "DOUBLE_ERROR_DETECTED",
                "corrected_bytes": None,
                "bit_corrected": None,
                "syndrome": syndrome
            }


class MipiRaw12Codec:
    """
    Bo ma hoa va giai ma du lieu diem anh RAW12 theo chuan MIPI CSI-2.
    Quy cach: 2 pixel (12-bit moi pixel) dong goi thanh 3 bytes.
    Byte 0: Pixel 0 [11:4]
    Byte 1: Pixel 1 [11:4]
    Byte 2: (Pixel 1 [3:0] << 4) | (Pixel 0 [3:0])
    """
    @staticmethod
    def pack(pixels: List[int]) -> bytes:
        if len(pixels) % 2 != 0:
            raise ValueError("So luong pixel phai la so chan de dong goi RAW12!")

        packed_bytes = bytearray()
        for i in range(0, len(pixels), 2):
            p0 = pixels[i] & 0x0FFF
            p1 = pixels[i + 1] & 0x0FFF

            b0 = (p0 >> 4) & 0xFF
            b1 = (p1 >> 4) & 0xFF
            b2 = ((p1 & 0x0F) << 4) | (p0 & 0x0F)

            packed_bytes.extend([b0, b1, b2])

        return bytes(packed_bytes)

    @staticmethod
    def unpack(packed_bytes: bytes) -> List[int]:
        if len(packed_bytes) % 3 != 0:
            raise ValueError("Do dai byte phai la boi so cua 3 doi voi RAW12!")

        pixels = []
        for i in range(0, len(packed_bytes), 3):
            b0 = packed_bytes[i]
            b1 = packed_bytes[i + 1]
            b2 = packed_bytes[i + 2]

            p0 = (b0 << 4) | (b2 & 0x0F)
            p1 = (b1 << 4) | ((b2 >> 4) & 0x0F)

            pixels.extend([p0, p1])

        return pixels


def calculate_crc16_itu(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def test_ecc_crc_and_raw12_pipeline():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN ECC SECDED ERROR CORRECTION & RAW12 PACKING")
    print("=" * 80)

    # 1. Thu nghiem Dong goi va Giai nen diem anh RAW12
    # Gia lap 6 pixel do sang cao cap tu camera Tesla HDR (0 den 4095)
    original_pixels = [100, 2048, 4095, 0, 1234, 3456]
    packed_raw12 = MipiRaw12Codec.pack(original_pixels)
    unpacked_pixels = MipiRaw12Codec.unpack(packed_raw12)

    print("Kiem tra thuat toan nen RAW12 (2 pixels / 3 bytes):")
    print(f"-> Pixel goc        : {original_pixels}")
    print(f"-> Byte da dong goi : {[hex(b) for b in packed_raw12]} (Do dai: {len(packed_raw12)} bytes)")
    print(f"-> Pixel giai nen   : {unpacked_pixels}")
    assert original_pixels == unpacked_pixels, "Loi thuat toan dong goi/giai nen RAW12!"
    print("-> Tinh toan CRC-16 Payload anh RAW12:")
    crc_orig = calculate_crc16_itu(packed_raw12)
    print(f"   + Checksum CRC-16: 0x{crc_orig:04X}")
    print("-" * 80)

    # 2. Thu nghiem ECC Hamming SECDED
    # Header goc: DI = 0x2C (VC0, RAW12), WC = 0x0180 (384 bytes)
    di = 0x2C
    wc = 0x0180
    d1 = wc & 0xFF
    d2 = (wc >> 8) & 0xFF
    ecc_orig = calculate_mipi_parity(di | (d1 << 8) | (d2 << 16))
    header_clean = struct.pack("<BBBB", di, d1, d2, ecc_orig)

    print("Kiem tra Bo giai ma ECC SECDED Header:")
    # Kich ban A: Khong co loi
    res_clean = Csi2EccDecoder.decode_and_correct(header_clean)
    print(f"[Kich ban A] Khong loi: Trang thai = {res_clean['status']}, Syndrome = 0x{res_clean['syndrome']:02X}")
    assert res_clean["status"] == "NO_ERROR"

    # Kich ban B: Gay loi 1 bit don le tren Data (lat bit D5 trong d1)
    # d1 ban dau la 0x80 (0b10000000) -> D5 thuoc bit 5 cua d1 -> 13 trong 24 bit
    # Lat bit 12: d1 ^= (1 << 4)
    corrupted_data_1bit = header_clean[0:1] + bytes([header_clean[1] ^ 0x10]) + header_clean[2:4]
    res_1bit = Csi2EccDecoder.decode_and_correct(corrupted_data_1bit)
    print(f"[Kich ban B] Nhieu 1-bit tren Data: Trang thai = {res_1bit['status']}")
    print(f"             Vi tri da sua: {res_1bit['bit_corrected']}, Du lieu khoi phuc khop 100%: {res_1bit['corrected_bytes'] == header_clean[:3]}")
    assert res_1bit["status"] == "SINGLE_ERROR_CORRECTED"
    assert res_1bit["corrected_bytes"] == header_clean[:3]

    # Kich ban C: Gay loi 1 bit tren Parity (lat bit P2)
    corrupted_parity_1bit = header_clean[0:3] + bytes([header_clean[3] ^ 0x04])
    res_p1bit = Csi2EccDecoder.decode_and_correct(corrupted_parity_1bit)
    print(f"[Kich ban C] Nhieu 1-bit tren Parity: Trang thai = {res_p1bit['status']}, Vi tri: {res_p1bit['bit_corrected']}")
    assert res_p1bit["status"] == "SINGLE_ERROR_CORRECTED"
    assert res_p1bit["corrected_bytes"] == header_clean[:3]

    # Kich ban D: Nhieu buc xa nang - Gay loi kep 2 bits (Double Bit Error: lat D0 va D1 tren DI)
    # Bit D0 co syndrome 0x07, bit D1 co syndrome 0x0B -> Tong syndrome = 0x07 ^ 0x0B = 0x0C
    # 0x0C khong nam trong bang tra loi don -> Bo giai ma phat hien Double Error Detected!
    corrupted_2bits = bytes([header_clean[0] ^ 0x03, header_clean[1], header_clean[2], header_clean[3]])
    res_2bits = Csi2EccDecoder.decode_and_correct(corrupted_2bits)
    print(f"[Kich ban D] Nhieu buc xa 2-bit: Trang thai = {res_2bits['status']}, Syndrome = 0x{res_2bits['syndrome']:02X}")
    assert res_2bits["status"] == "DOUBLE_ERROR_DETECTED"
    assert res_2bits["corrected_bytes"] is None

    # Kich ban E: Kiem tra phat hien loi bit tren Payload bang CRC-16
    corrupted_payload = packed_raw12[:4] + bytes([packed_raw12[4] ^ 0x01]) + packed_raw12[5:]
    crc_corrupted = calculate_crc16_itu(corrupted_payload)
    print("-" * 80)
    print("Kiem tra CRC-16 phat hien loi du lieu Payload:")
    print(f"-> CRC goc        : 0x{crc_orig:04X}")
    print(f"-> CRC sau khi lat bit: 0x{crc_corrupted:04X} -> Phat hien bat dong 100%!")
    assert crc_orig != crc_corrupted, "CRC-16 phai phat hien su sai khac khi bi lat bit!"

    print("=" * 80)
    print("[PASS] MIPI CSI-2 ECC SECDED & RAW12 Payload Validator: 100% Hoan hao!")


if __name__ == "__main__":
    test_ecc_crc_and_raw12_pipeline()
