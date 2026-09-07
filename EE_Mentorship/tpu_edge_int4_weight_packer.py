"""
================================================================================
          MODULE AA: EMBEDDED HARDWARE TENSOR ACCELERATION & NPU CORES
              MILESTONE AA.2: ĐÓNG GÓI TRỌNG SỐ 4-BIT (INT4 SUB-BYTE NIBBLE PACKER)
================================================================================

TẠI SAO CÁC MÔ HÌNH NGÔN NGỮ LỚN (LLM) & EDGE NPU DÙNG LƯỢNG TỬ HÓA 4-BIT (INT4)?
Một số nguyên 4-bit (Nibble) chỉ cần dải giá trị [0..15]:
- Trong bộ nhớ RAM thông thường, một địa chỉ nhỏ nhất là 1 Byte (8 bits).
- Kỹ thuật **Bit-Packing 2-trong-1**:
  + Gom 2 trọng số 4-bit (w_low, w_high) nhét vào đúng 1 Byte duy nhất!
  + packed_byte = (w_high << 4) | (w_low & 0x0F)
  + Tiết kiệm đúng 87.5% dung lượng bộ nhớ so với Float32!
"""

import numpy as np

def pack_int4_weights(w_list: list) -> bytearray:
    """
    Trò đóng vai Kỹ sư Nén Trọng số NPU:
    - w_list chứa danh sách các số nguyên 4-bit [0..15]
    - Cứ mỗi cặp (w0, w1): byte_val = (w1 << 4) | (w0 & 0x0F)
    - Trả về bytearray đã đóng gói (kích thước giảm 50% so với uint8)
    """
    packed = bytearray()
    for i in range(0, len(w_list), 2):
        w_low = w_list[i] & 0x0F
        w_high = (w_list[i + 1] & 0x0F) if (i + 1 < len(w_list)) else 0
        packed.append((w_high << 4) | w_low)
    return packed

def unpack_int4_weights(packed: bytearray, total_elements: int) -> list:
    """Giải nén bytearray về lại danh sách các số 4-bit ban đầu."""
    unpacked = []
    for b in packed:
        w_low = b & 0x0F
        w_high = (b >> 4) & 0x0F
        unpacked.append(w_low)
        if len(unpacked) < total_elements:
            unpacked.append(w_high)
    return unpacked


if __name__ == "__main__":
    print("=========================================================")
    print("   NPU ACCELERATOR: SUB-BYTE INT4 NIBBLE PACKER")
    print("=========================================================\n")

    # 4 trọng số 4-bit ban đầu: 3, 11, 7, 14
    raw_w = [3, 11, 7, 14]
    packed_bytes = pack_int4_weights(raw_w)
    recovered = unpack_int4_weights(packed_bytes, len(raw_w))

    print("1. KET QUA DONG GOI VA GIAI NEN TRONG SO INT4 4-BIT:")
    print(f"   -> Trong so goc (4 phan tu)   : {raw_w}")
    print(f"   -> Bo nho chiem dung sau pack : {len(packed_bytes)} bytes (Giam 50%!)")
    print(f"   -> Cac bytes ma hex da pack   : {[hex(b) for b in packed_bytes]}")
    print(f"   -> Trong so giai nen phuc hoi : {recovered}")

    assert len(packed_bytes) == 2 and raw_w == recovered, "Loi Int4 Packing!"
    print("\n[THANH CONG] DA HOAN THANH BO NEN TRONG SO SUB-BYTE INT4 NIBBLE CHO NPU!")
