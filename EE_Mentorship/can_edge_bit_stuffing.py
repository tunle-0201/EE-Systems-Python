"""
================================================================================
          MODULE M: EMBEDDED CAN-BUS & VEHICLE NETWORK PROTOCOLS
              MILESTONE M.2: THUẬT TOÁN CHÈN BIT ĐỒNG BỘ PHẦN CỨNG (BIT STUFFING)
================================================================================

TẠI SAO PHẦN CỨNG CAN-BUS CẦN CHÈN BIT (BIT STUFFING)?
Trên bus CAN không có dây Clock riêng (Asynchronous Serial):
- Nếu truyền 5 bit giống nhau liên tiếp (ví dụ 11111 hoặc 00000).
- Bộ thu phát CAN Transceiver sẽ bị mất đồng bộ xung nhịp (Clock Drift).
- Quy tắc Bit Stuffing: Cứ sau 5 bit giống nhau liên tiếp, phần cứng TỰ ĐỘNG CHÈN 1 bit ngược dấu!
"""

def apply_can_bit_stuffing(bit_stream: str) -> str:
    """
    Trò đóng vai Kỹ sư phần cứng CAN logic:
    - Duyệt qua từng bit trong bit_stream
    - Nếu đếm được 5 bit giống nhau liên tiếp:
      + Chèn bit đối nghịch (nếu là '1' chèn '0', nếu là '0' chèn '1')
      + Reset bộ đếm = 0
    - Trả về: stuffed_stream
    """
    stuffed = []
    consecutive_count = 1
    
    for i in range(len(bit_stream)):
        stuffed.append(bit_stream[i])
        if i > 0 and bit_stream[i] == bit_stream[i-1]:
            consecutive_count += 1
            if consecutive_count == 5:
                # Chèn bit đảo dấu
                opposite_bit = '0' if bit_stream[i] == '1' else '1'
                stuffed.append(opposite_bit)
                consecutive_count = 0
        else:
            consecutive_count = 1
            
    return "".join(stuffed)


if __name__ == "__main__":
    print("=========================================================")
    print("   VEHICLE EE SYSTEMS: CAN-BUS BIT STUFFING ENGINE")
    print("=========================================================\n")
    
    raw_bits = "111111" # 6 bit '1' liên tiếp
    stuffed_bits = apply_can_bit_stuffing(raw_bits)
    
    print("1. KET QUA PHAP CHEN BIT DONG BO PHAN CUNG CAN-BUS:")
    print(f"   -> Luong bit tho ban dau : {raw_bits}")
    print(f"   -> Luong bit sau Bit Stuff: {stuffed_bits} (Da chen bit 0 vao giua!)")
    
    assert stuffed_bits == "1111101", "Loi thuat toan Bit Stuffing!"
    print("\n[THANH CONG] DA HOAN THANH CO CHE DONG BO XUNG NHIP BIT STUFFING PHAN CUNG CAN!")
