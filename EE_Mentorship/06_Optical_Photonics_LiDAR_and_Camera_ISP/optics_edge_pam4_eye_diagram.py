"""
================================================================================
          MODULE AH: EMBEDDED OPTICAL TRANSCEIVERS & PHOTONICS AVIONICS
              MILESTONE AH.1: ĐIỀU CHẾ QUANG PAM4 VÀ ĐỒ THỊ MẮT (EYE DIAGRAM METRICS)
================================================================================

TẠI SAO CÁC CỤM MÁY TÍNH AI (NVIDIA DGX, GOOGLE TPU) DÙNG QUANG PAM4 THAY VÌ NRZ?
Chuẩn NRZ nhị phân (2 mức điện áp 0 và 1) đã chạm giới hạn vật lý ở tốc độ 25 Gbps:
- Điều chế quang PAM4 (Pulse Amplitude Modulation 4-Level):
  + Mã hóa 2 bits thành 1 biểu tượng (Symbol) với 4 mức quang: [00, 01, 11, 10] (Mã Gray).
  + Tăng gấp đôi băng thông đường truyền lên 50G / 100G / 400G mà không cần tăng tần số!
  + Đồ thị mắt (Eye Diagram) có 3 mắt xếp chồng: Eye High, Eye Mid, Eye Low.
"""

import numpy as np

def encode_bits_to_pam4_symbols(bitstream: list) -> list:
    """
    Trò đóng vai Kỹ sư Quang điện tử:
    - Nhóm từng cặp 2 bits (b0, b1)
    - Ánh xạ theo bảng mã Gray:
      + '00' -> Mức 0 (-3.0)
      + '01' -> Mức 1 (-1.0)
      + '11' -> Mức 2 (+1.0)
      + '10' -> Mức 3 (+3.0)
    """
    gray_map = {
        (0, 0): -3.0,
        (0, 1): -1.0,
        (1, 1): 1.0,
        (1, 0): 3.0
    }
    symbols = []
    for i in range(0, len(bitstream), 2):
        pair = (bitstream[i], bitstream[i + 1])
        symbols.append(gray_map.get(pair, 0.0))
    return symbols

def calculate_pam4_eye_heights(received_symbols: list, noise_std: float = 0.1) -> tuple:
    """Đo độ mở của 3 tầng mắt quang (Eye Heights) để đánh giá chất lượng tín hiệu."""
    levels = [-3.0, -1.0, 1.0, 3.0]
    eye_low = (levels[1] - levels[0]) - 2.0 * noise_std
    eye_mid = (levels[2] - levels[1]) - 2.0 * noise_std
    eye_high = (levels[3] - levels[2]) - 2.0 * noise_std
    return eye_low, eye_mid, eye_high


if __name__ == "__main__":
    print("=========================================================")
    print("   PHOTONICS AVIONICS: PAM4 OPTICAL MODULATION & EYE")
    print("=========================================================\n")

    # Chuỗi 8 bits dữ liệu truyền quang: [0, 0, 0, 1, 1, 1, 1, 0]
    raw_bits = [0, 0, 0, 1, 1, 1, 1, 0]
    pam4_levels = encode_bits_to_pam4_symbols(raw_bits)
    h_low, h_mid, h_high = calculate_pam4_eye_heights(pam4_levels, noise_std=0.15)

    print("1. KET QUA ANH XA PAM4 GRAY CODING:")
    print(f"   -> Bitstream ban dau        : {raw_bits}")
    print(f"   -> 4 Mua muc dien ap quang  : {pam4_levels}")
    print(f"   -> Do mo 3 mat quang (Eye)  : Low={h_low:.2f}, Mid={h_mid:.2f}, High={h_high:.2f}")

    assert pam4_levels == [-3.0, -1.0, 1.0, 3.0] and h_mid > 1.5, "Loi PAM4 Optical Modulation!"
    print("\n[THANH CONG] DA HOAN THANH DIEU CHE QUANG TOC DO CAO PAM4 CHO DATA CENTER AI!")
