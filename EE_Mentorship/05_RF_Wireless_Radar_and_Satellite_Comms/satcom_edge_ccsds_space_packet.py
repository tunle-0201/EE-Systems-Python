"""
================================================================================
          MODULE AF: SATELLITE COMMUNICATIONS & SPACE LINK BUDGET
              MILESTONE AF.3: ĐÓNG GÓI CHUẨN KHÔNG GIAN CCSDS (SPACE PACKET PROTOCOL)
================================================================================

TẠI SAO TẤT CẢ CƠ QUAN HÀNG KHÔNG VŨ TRỤ (NASA, ESA, JAXA) PHẢI TUÂN THEO CHUẨN CCSDS?
Chuẩn CCSDS (Consultative Committee for Space Data Systems):
- Định nghĩa cấu trúc khung gói tin vũ trụ tiêu chuẩn (Packet Primary Header 6 bytes):
  + Packet Version Number (3 bits): Luôn bằng 000b.
  + Packet Type (1 bit): 0 = Telemetry (Báo cáo từ vệ tinh), 1 = Telecommand (Lệnh từ mặt đất).
  + Secondary Header Flag (1 bit): Có timestamp thời gian hay không.
  + Application Process ID - APID (11 bits): Xác định cảm biến nguồn (Camera, Pin, Động cơ).
  + Sequence Flags & Packet Sequence Count (16 bits): Số thứ tự gói tin để chống mất gói.
  + Packet Data Length (16 bits): Độ dài dữ liệu trừ 1.
"""

import struct

def encode_ccsds_primary_header(apid: int, seq_count: int, payload_length: int, is_command: bool = False) -> bytes:
    """
    Trò đóng vai Kỹ sư Giao thức Vũ trụ Quốc tế CCSDS:
    - field_1 (16 bits): Version(3 bits=0) | Type(1 bit) | SecHdr(1 bit=1) | APID(11 bits)
    - field_2 (16 bits): SeqFlags(2 bits=3: unsegmented) | SeqCount(14 bits)
    - field_3 (16 bits): Packet Data Length = payload_length - 1
    - Đóng gói bằng struct.pack('>HHH', field_1, field_2, field_3) (Big-Endian chuẩn vũ trụ!)
    """
    pkt_type = 1 if is_command else 0
    sec_hdr_flag = 1
    field_1 = ((0 & 0x07) << 13) | ((pkt_type & 0x01) << 12) | ((sec_hdr_flag & 0x01) << 11) | (apid & 0x07FF)
    
    seq_flags = 3  # 11b: Unsegmented standalone packet
    field_2 = ((seq_flags & 0x03) << 14) | (seq_count & 0x3FFF)
    field_3 = max(0, payload_length - 1) & 0xFFFF

    return struct.pack('>HHH', field_1, field_2, field_3)


if __name__ == "__main__":
    print("=========================================================")
    print("   SATCOM AVIONICS: CCSDS 133.0-B SPACE PACKET ENCODER")
    print("=========================================================\n")

    # Đóng gói gói tin Telemetry từ cảm biến pin năng lượng (APID = 0x12A = 298), gói thứ 42
    test_payload = b"BATTERY_VOLTAGE_28V_CURRENT_3.5A_TEMP_18C"
    ccsds_hdr = encode_ccsds_primary_header(apid=298, seq_count=42, payload_length=len(test_payload))

    full_packet = ccsds_hdr + test_payload

    print("1. KET QUA DONG GOI GOI TIN THEO CHUAN VU TRU QUOC TE CCSDS:")
    print(f"   -> Do dai Header CCSDS       : {len(ccsds_hdr)} bytes")
    print(f"   -> Ma Hex Header             : {ccsds_hdr.hex().upper()}")
    print(f"   -> Tong do dai goi truyen di : {len(full_packet)} bytes")

    assert len(ccsds_hdr) == 6 and ccsds_hdr[0] == 0x09 and ccsds_hdr[1] == 0x2A, "Loi CCSDS Header!"
    print("\n[THANH CONG] DA HOAN THANH DONG GOI CHUAN KHONG GIAN CCSDS CHO NASA DEEP SPACE NETWORK!")
