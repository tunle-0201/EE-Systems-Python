"""
================================================================================
          MODULE W: ADVANCED EMBEDDED CRYPTO & POST-QUANTUM DEFENSE
              MILESTONE W.1: HÀM BĂM MẬT MÃ SHA-3 (KECCAK-256 SPONGE FUNCTION)
================================================================================

TẠI SAO CÁC HỆ THỐNG QUÂN SỰ & HÀNG KHÔNG VŨ TRỤ CHUYỂN TỪ SHA-2 SANG SHA-3?
Hàm băm SHA-3 (Keccak):
- Sử dụng cấu trúc bọt biển (Sponge Construction) hấp thụ (absorb) và ép xuất (squeeze).
- Miễn nhiễm 100% với các cuộc tấn công mở rộng chiều dài (Length Extension Attack).
- Đảm bảo gói tin chỉ lệnh bay Telemetry không bao giờ bị can thiệp chèn mã độc!
"""

import hashlib

def generate_telemetry_sha3_256(packet_bytes: bytes) -> str:
    """
    Trò đóng vai Kỹ sư Mật mã Hàng không vũ trụ:
    - Sử dụng hashlib.sha3_256() để băm gói tin
    - Trả về: Chuỗi hex digest 64 ký tự
    """
    hasher = hashlib.sha3_256()
    hasher.update(packet_bytes)
    return hasher.hexdigest()


if __name__ == "__main__":
    print("=========================================================")
    print("   DEFENSE AVIONICS: SHA-3 KECCAK-256 CRYPTO SPONGE")
    print("=========================================================\n")

    # Gói tin điều khiển bay: Bay lên độ cao 150m, Tốc độ 90km/h
    telemetry_cmd = b"CMD_ALT_150M_SPD_90KMH"
    digest = generate_telemetry_sha3_256(telemetry_cmd)

    print("1. KET QUA BAM GOI TIN LENH BAY BANG SHA-3 (256-BIT):")
    print(f"   -> Goi tin goc  : {telemetry_cmd.decode()}")
    print(f"   -> SHA-3 Digest : {digest}")
    print(f"   -> Do dai Hash  : {len(digest) * 4} bits (64 hex characters)")

    assert len(digest) == 64 and isinstance(digest, str), "Loi SHA-3 Keccak!"
    print("\n[THANH CONG] DA HOAN THANH HAM BAM SHA-3 KECCAK BAO MAT DU LIEU CHO DRONE!")
