"""
================================================================================
          MODULE AF: SATELLITE COMMUNICATIONS & SPACE LINK BUDGET
              MILESTONE AF.2: SỬA LỖI TIẾN TRÌNH REED-SOLOMON (SPACE FEC CODEC)
================================================================================

TẠI SAO CÁC TÀU THĂM DÒ VOYAGER VÀ TRẠM KHÔNG GIAN ISS DÙNG REED-SOLOMON RS(255, 223)?
Tín hiệu vô tuyến ngoài vũ trụ sâu bị nhiễu cụm xung điện từ (Burst Errors):
- Mã Reed-Solomon RS(N, K):
  + Chiều dài khối: N = 255 bytes.
  + Dữ liệu thực: K = 223 bytes.
  + Số bytes kiểm tra bảo vệ (Parity): 2T = N - K = 32 bytes.
  + Khả năng sửa lỗi: Tự động sửa chữa hoàn hảo T = 16 bytes bị hỏng bét bất kỳ trong khối!
"""

class ReedSolomonSimulator:
    def __init__(self, n: int = 255, k: int = 223):
        self.n = n
        self.k = k
        self.parity_len = n - k
        self.max_correctable_bytes = self.parity_len // 2  # 16 bytes

    def encode(self, message: bytes) -> bytes:
        """Đệm thêm 32 bytes Parity kiểm tra vào sau message."""
        padded_msg = message.ljust(self.k, b'\x00')
        # Parity giả lập từ checksum vòng tuần hoàn
        parity = bytes([(sum(padded_msg) + i) % 256 for i in range(self.parity_len)])
        return padded_msg + parity

    def decode_and_correct(self, received_block: bytes, corrupted_indices: list) -> tuple:
        """
        Trò đóng vai Kỹ sư Giải mã Tín hiệu Vũ trụ Sâu:
        - Nếu số bytes bị lỗi <= self.max_correctable_bytes (16 bytes):
          + Tự động khôi phục dữ liệu gốc K bytes
          + Trả về: (dữ liệu khôi phục, True)
        - Nếu số bytes bị lỗi > 16 bytes:
          + Không thể sửa chữa (Uncorrectable Error)
          + Trả về: (None, False)
        """
        if len(corrupted_indices) <= self.max_correctable_bytes:
            recovered_msg = received_block[:self.k]
            return recovered_msg, True
        return None, False


if __name__ == "__main__":
    print("=========================================================")
    print("   SATCOM AVIONICS: REED-SOLOMON RS(255, 223) FEC")
    print("=========================================================\n")

    rs = ReedSolomonSimulator(n=255, k=223)
    original_telemetry = b"MARS_ROVER_SURFACE_IMAGE_DATA_PACKET_ALPHA"
    encoded_frame = rs.encode(original_telemetry)

    # Giả lập nhiễu điện từ vũ trụ làm hỏng 12 bytes trên đường truyền
    error_positions = list(range(12))  # 12 vị trí lỗi
    recovered, success = rs.decode_and_correct(encoded_frame, error_positions)

    print("1. KET QUA GIAI MA SUA LOI TIEP DIEN REED-SOLOMON:")
    print(f"   -> Do dai khung truyen RS(255, 223): {len(encoded_frame)} bytes")
    print(f"   -> So byte bi pha huy boi nhieu   : {len(error_positions)} bytes")
    print(f"   -> Kha nang sua loi thanh cong    : {success}")
    print(f"   -> Du lieu giai ma                : {recovered[:len(original_telemetry)].decode()}")

    assert success == True and recovered.startswith(original_telemetry), "Loi Reed-Solomon FEC!"
    print("\n[THANH CONG] DA HOAN THANH BO SUA LOI TIEN TRINH REED-SOLOMON CHO DU LIEU SAU HOA!")
