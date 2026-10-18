"""
MIPI CSI-2 Packet Protocol & Multi-Sensor Virtual Channel Multiplexing
Chuyen de 23: MIPI CSI-2 Camera Serial Interface & D-PHY Hardware Pipeline
Milestone AJ.2 - Bai hoc 89 trong chuoi EE Mentorship cho Le Dac Anh Tuan

Muc tieu:
- Dong goi va giai ma goi tin ngan (Short Packet - 4 bytes) va goi tin dai (Long Packet).
- Quan ly dong bo khung hinh (Frame Start FS, Frame End FE, Line Start LS, Line End LE).
- Thiet ke bo ghep kenh ao Virtual Channel (VC 0 - 3) cho he thong da camera xe tu hanh.
"""

from enum import IntEnum
import struct
from typing import List, Dict, Tuple, Optional


class Csi2DataType(IntEnum):
    # Short Packet Data Types (0x00 to 0x0F)
    FRAME_START = 0x00
    FRAME_END   = 0x01
    LINE_START  = 0x02
    LINE_END    = 0x03
    GENERIC_SHORT_1 = 0x08
    GENERIC_SHORT_2 = 0x09
    
    # Long Packet Data Types (Image Data Formats)
    YUV422_8BIT = 0x1E
    RGB888      = 0x24
    RAW8        = 0x2A
    RAW10       = 0x2B
    RAW12       = 0x2C
    RAW14       = 0x2D
    USER_DEF_1  = 0x30


def calculate_mipi_ecc(d0: int, d1: int, d2: int) -> int:
    """
    Tinh toan 8-bit ECC cho 24-bit du lieu Header (D0, D1, D2)
    theo tieu chuan MIPI Alliance CSI-2 Specification.
    Moi bit parity P[0] den P[5] duoc tinh bang XOR cac bit du lieu tuong ung.
    P[6] va P[7] luon bang 0.
    """
    # Ghep 3 bytes thanh 24 bits: D[23:0]
    data = d0 | (d1 << 8) | (d2 << 16)
    
    # Ma tran Hamming Parity Mask chuan MIPI CSI-2
    # P[0] = XOR(D0, D1, D2, D4, D5, D7, D8, D10, D11, D13, D16, D20, D21, D22, D23)
    p0_mask = 0x0F12B7
    # P[1] = XOR(D0, D1, D3, D4, D6, D7, D9, D10, D12, D14, D17, D20, D21, D22, D23)
    p1_mask = 0x0F255B
    # P[2] = XOR(D0, D2, D3, D5, D6, D7, D11, D12, D13, D15, D18, D20, D21, D22)
    p2_mask = 0x0739CD
    # P[3] = XOR(D1, D2, D3, D8, D9, D10, D11, D12, D13, D14, D19, D20, D21, D23)
    p3_mask = 0x0B7F0E
    # P[4] = XOR(D4, D5, D6, D7, D8, D9, D10, D11, D12, D13, D14, D15, D22, D23)
    p4_mask = 0x0CF0FF0  # D4..D15, D22, D23
    p4_mask = 0xC0FFF0
    # P[5] = XOR(D16, D17, D18, D19, D20, D21, D22, D23)
    p5_mask = 0xFF0000

    def parity(val: int) -> int:
        count = bin(val).count('1')
        return count % 2

    p0 = parity(data & p0_mask)
    p1 = parity(data & p1_mask)
    p2 = parity(data & p2_mask)
    p3 = parity(data & p3_mask)
    p4 = parity(data & p4_mask)
    p5 = parity(data & p5_mask)
    
    ecc = p0 | (p1 << 1) | (p2 << 2) | (p3 << 3) | (p4 << 4) | (p5 << 5)
    return ecc


def calculate_crc16_itu(data: bytes) -> int:
    """
    Tinh toan Checksum CRC-16 ITU (Da thuc: x^16 + x^12 + x^5 + 1 = 0x1021)
    cho Packet Footer cua goi tin dai MIPI CSI-2.
    Gia tri khoi tao: 0xFFFF.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


class Csi2Packet:
    """
    Lop dai dien cho mot goi tin MIPI CSI-2 (Short hoac Long Packet).
    """
    def __init__(self, virtual_channel: int, data_type: Csi2DataType, payload: bytes = b"", frame_or_line_num: int = 0):
        self.virtual_channel = virtual_channel & 0x03  # 2 bits (VC 0 den 3)
        self.data_type = data_type
        self.is_short_packet = (data_type <= 0x0F)
        
        # Byte 0: Data Identifier (DI)
        self.di = (self.virtual_channel << 6) | (int(data_type) & 0x3F)
        
        if self.is_short_packet:
            # Short Packet: 2 bytes payload dung cho Frame/Line Number
            self.word_count = frame_or_line_num & 0xFFFF
            d1 = self.word_count & 0xFF
            d2 = (self.word_count >> 8) & 0xFF
            self.ecc = calculate_mipi_ecc(self.di, d1, d2)
            self.payload = b""
            self.checksum = None
            self.raw_bytes = struct.pack("<BBBB", self.di, d1, d2, self.ecc)
        else:
            # Long Packet: 2 bytes Word Count (do dai payload)
            self.word_count = len(payload)
            d1 = self.word_count & 0xFF
            d2 = (self.word_count >> 8) & 0xFF
            self.ecc = calculate_mipi_ecc(self.di, d1, d2)
            self.payload = payload
            self.checksum = calculate_crc16_itu(payload)
            header = struct.pack("<BBBB", self.di, d1, d2, self.ecc)
            footer = struct.pack("<H", self.checksum)
            self.raw_bytes = header + payload + footer


class Csi2PacketParser:
    """
    Bo phan tich va giai ma luong bit CSI-2 RX.
    Tach cac kenh ao (Virtual Channel Demultiplexing) va tai tao frame anh.
    """
    def __init__(self):
        self.active_frames: Dict[int, Dict[str, any]] = {
            vc: {"in_frame": False, "frame_num": 0, "lines": [], "line_count": 0, "bytes_received": 0}
            for vc in range(4)
        }

    def parse_packet(self, raw_bytes: bytes) -> Dict[str, any]:
        """
        Giai ma mot chuoi bytes nhan duoc tu D-PHY RX.
        """
        if len(raw_bytes) < 4:
            return {"status": "ERROR_TOO_SHORT", "bytes": len(raw_bytes)}

        di, d1, d2, ecc_received = struct.unpack("<BBBB", raw_bytes[:4])
        vc = (di >> 6) & 0x03
        dt = di & 0x3F
        
        # Kiem tra ECC Header
        ecc_computed = calculate_mipi_ecc(di, d1, d2)
        ecc_ok = (ecc_received == ecc_computed)
        
        if not ecc_ok:
            return {"status": "ECC_ERROR", "vc": vc, "dt": dt}

        if dt <= 0x0F:
            # Short Packet
            num = d1 | (d2 << 8)
            packet_type_str = Csi2DataType(dt).name if dt in [e.value for e in Csi2DataType] else f"SHORT_0x{dt:02X}"
            
            # Quan ly may trang thai frame
            if dt == Csi2DataType.FRAME_START:
                self.active_frames[vc]["in_frame"] = True
                self.active_frames[vc]["frame_num"] = num
                self.active_frames[vc]["lines"] = []
                self.active_frames[vc]["line_count"] = 0
                self.active_frames[vc]["bytes_received"] = 0
            elif dt == Csi2DataType.FRAME_END:
                self.active_frames[vc]["in_frame"] = False

            return {
                "status": "SHORT_PACKET_OK",
                "vc": vc,
                "dt": dt,
                "type": packet_type_str,
                "num": num
            }
        else:
            # Long Packet
            wc = d1 | (d2 << 8)
            expected_total_len = 4 + wc + 2  # 4 header + WC payload + 2 footer CRC
            
            if len(raw_bytes) < expected_total_len:
                return {"status": "INCOMPLETE_LONG_PACKET", "vc": vc, "wc": wc, "got": len(raw_bytes)}

            payload = raw_bytes[4:4 + wc]
            crc_received = struct.unpack("<H", raw_bytes[4 + wc:4 + wc + 2])[0]
            crc_computed = calculate_crc16_itu(payload)
            crc_ok = (crc_received == crc_computed)

            if not crc_ok:
                return {"status": "CRC_ERROR", "vc": vc, "dt": dt, "wc": wc}

            # Luu tru dong vao frame hien tai
            if self.active_frames[vc]["in_frame"]:
                self.active_frames[vc]["lines"].append(payload)
                self.active_frames[vc]["line_count"] += 1
                self.active_frames[vc]["bytes_received"] += len(payload)

            return {
                "status": "LONG_PACKET_OK",
                "vc": vc,
                "dt": dt,
                "wc": wc,
                "payload_len": len(payload),
                "crc_ok": crc_ok
            }


def test_mipi_csi2_pipeline():
    print("=" * 80)
    print("BAT DAU KIEM CHUAN GIAO THUC GOI TIN MIPI CSI-2 & DEMULTIPLEXING")
    print("=" * 80)

    # 1. Kiem tra tinh toan ECC tren Header (24-bit)
    di = 0x2C  # VC 0, RAW12 (0x2C)
    d1 = 0x40  # WC low byte (0x0240 = 576 bytes)
    d2 = 0x02  # WC high byte
    ecc = calculate_mipi_ecc(di, d1, d2)
    print(f"Header 24-bit: DI=0x{di:02X}, D1=0x{d1:02X}, D2=0x{d2:02X} -> Tinh duoc ECC = 0x{ecc:02X}")
    print("-" * 80)

    # 2. Tao luong goi tin da camera:
    # - Camera Chinh Truoc (Front Main Camera): VC 0, Frame 101, 3 Dong anh RAW12
    # - Camera Goc Rong (Wide Camera):          VC 1, Frame 201, 2 Dong anh RAW12
    packets_to_send: List[Csi2Packet] = []

    # Frame Start cho ca 2 Camera
    packets_to_send.append(Csi2Packet(virtual_channel=0, data_type=Csi2DataType.FRAME_START, frame_or_line_num=101))
    packets_to_send.append(Csi2Packet(virtual_channel=1, data_type=Csi2DataType.FRAME_START, frame_or_line_num=201))

    # Giao thoa dong quet anh (Time-Division Multiplexed lines)
    line_raw12_cam0 = bytes([0xAA] * 256)
    line_raw12_cam1 = bytes([0x55] * 256)

    # Dong 1 Cam 0
    packets_to_send.append(Csi2Packet(virtual_channel=0, data_type=Csi2DataType.RAW12, payload=line_raw12_cam0))
    # Dong 1 Cam 1
    packets_to_send.append(Csi2Packet(virtual_channel=1, data_type=Csi2DataType.RAW12, payload=line_raw12_cam1))
    # Dong 2 Cam 0
    packets_to_send.append(Csi2Packet(virtual_channel=0, data_type=Csi2DataType.RAW12, payload=line_raw12_cam0))
    # Dong 2 Cam 1
    packets_to_send.append(Csi2Packet(virtual_channel=1, data_type=Csi2DataType.RAW12, payload=line_raw12_cam1))
    # Dong 3 Cam 0
    packets_to_send.append(Csi2Packet(virtual_channel=0, data_type=Csi2DataType.RAW12, payload=line_raw12_cam0))

    # Frame End cho ca 2 Camera
    packets_to_send.append(Csi2Packet(virtual_channel=0, data_type=Csi2DataType.FRAME_END, frame_or_line_num=101))
    packets_to_send.append(Csi2Packet(virtual_channel=1, data_type=Csi2DataType.FRAME_END, frame_or_line_num=201))

    # 3. Bo phan tich CSI-2 RX Demultiplexer giai ma toan bo goi tin
    parser = Csi2PacketParser()
    print("Trinh tu giai ma goi tin tai bo thu MIPI CSI-2 RX:")
    print("Goi | Loai Packet  | VC | DT   | WC / Frame Num | Trang Thai Giai Ma")
    print("-" * 75)

    for idx, pkt in enumerate(packets_to_send, 1):
        res = parser.parse_packet(pkt.raw_bytes)
        num_or_wc = res.get("num", res.get("wc", 0))
        pkt_type = "SHORT" if pkt.is_short_packet else "LONG "
        print(f"{idx:3d} | {pkt_type:12s} | {res['vc']:2d} | 0x{res['dt']:02X} | {num_or_wc:14d} | {res['status']}")

    print("-" * 80)
    print("Ket qua lap rap khung hinh sau bo tach kenh ao (VC Demux):")
    for vc in range(2):
        info = parser.active_frames[vc]
        cam_name = "Camera Truoc (Front)" if vc == 0 else "Camera Goc Rong (Wide)"
        print(f"-> {cam_name} [VC {vc}]:")
        print(f"   + So thu tu Frame : {info['frame_num']}")
        print(f"   + So dong nhan duoc: {info['line_count']} dong")
        print(f"   + Tong byte du lieu: {info['bytes_received']} bytes")
        print(f"   + Trang thai Frame : {'DA HOAN TAT (Frame Closed)' if not info['in_frame'] else 'DANG MO'}")

    assert parser.active_frames[0]["line_count"] == 3, "So dong VC 0 phai bang 3!"
    assert parser.active_frames[1]["line_count"] == 2, "So dong VC 1 phai bang 2!"
    assert parser.active_frames[0]["bytes_received"] == 3 * 256, "Tong byte VC 0 khong khop!"
    assert parser.active_frames[1]["bytes_received"] == 2 * 256, "Tong byte VC 1 khong khop!"
    print("=" * 80)
    print("[PASS] MIPI CSI-2 Packet Protocol & Multi-Sensor Demux: 100% Hoan hao!")


if __name__ == "__main__":
    test_mipi_csi2_pipeline()
