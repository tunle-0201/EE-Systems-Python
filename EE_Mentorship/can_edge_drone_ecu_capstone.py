"""
================================================================================
          MODULE M CAPSTONE FINALE: MẠNG CAN-BUS ĐA NỐT TRÊN XE TỰ HÀNH & DRONE
================================================================================

TÍCH HỢP TOÀN BỘ KIẾN TRÚC CAN-BUS: ENCODER + BIT STUFFING + ARBITRATION
"""

from can_edge_packet_encoder import encode_can_standard_frame
from can_edge_bit_stuffing import apply_can_bit_stuffing
from can_edge_arbitration_bus import simulate_can_bus_arbitration
import struct

def run_drone_can_network_bus():
    # 1. Hai nốt ECU cùng phát gói tin lên bus
    frame1 = encode_can_standard_frame(0x100, b"MOTOR_ON")
    frame2 = encode_can_standard_frame(0x050, b"ESTOP") # Khẩn cấp ID thấp
    
    # 2. Tranh chấp bus
    winner = simulate_can_bus_arbitration(0x100, 0x050)
    
    # 3. Bit stuffing đồng bộ
    stuffed = apply_can_bit_stuffing("11111000001")
    return len(frame1), winner, stuffed


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE M CAPSTONE: FULL VEHICLE CAN-BUS NETWORK")
    print("=========================================================\n")
    
    f_len, w_node, st_bits = run_drone_can_network_bus()
    
    print("1. KET QUA HOAT DONG TOAN CHUOI CAN-BUS REAL-TIME:")
    print(f"   -> Do dai Frame 1          : {f_len} Bytes")
    print(f"   -> Node Thang tranh chap   : 0x{w_node:03X}")
    print(f"   -> Bit stream sau Stuffing : {st_bits}")
    
    assert w_node == 0x050, "Loi CAN Capstone Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE M: EMBEDDED CAN-BUS!")
    print("=========================================================")
