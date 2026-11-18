"""
================================================================================
          MODULE AA: EMBEDDED HARDWARE TENSOR ACCELERATION & NPU CORES
              MILESTONE AA.3: LUỒNG DỮ LIỆU MẢNG SYSTOLIC CỐ ĐỊNH TRỌNG SỐ
================================================================================

TẠI SAO GOOGLE TPU VÀ CÁC CHIP NPU THỜI HIỆN ĐẠI CHỌN WEIGHT-STATIONARY?
Kiến trúc Weight-Stationary (Cố định trọng số):
- Trọng số W được nạp vào thanh ghi nội bộ của từng phần tử xử lý PE (Processing Element) và đứng yên.
- Dữ liệu kích hoạt (Activation X) chảy từ trái sang phải qua từng chu kỳ xung nhịp.
- Kết quả tích lũy (Partial Sums) chảy từ trên xuống dưới.
- Tiết kiệm 90% điện năng truy xuất bộ nhớ DRAM/SRAM!
"""

class ProcessingElement:
    def __init__(self, weight: int):
        self.weight = weight
        self.acc = 0

    def compute_step(self, in_act: int, in_psum: int):
        """Tính output_psum = in_psum + (in_act * weight), chuyển tiếp act sang phải."""
        out_psum = in_psum + (in_act * self.weight)
        out_act = in_act
        return out_act, out_psum


if __name__ == "__main__":
    print("=========================================================")
    print("   NPU ACCELERATOR: WEIGHT-STATIONARY SYSTOLIC PE CORE")
    print("=========================================================\n")

    # 1 PE cố định trọng số W = 5
    pe = ProcessingElement(weight=5)

    # Chu kỳ 1: Dữ liệu kích hoạt Act = 3 đi vào, tổng tích lũy trước đó = 10
    out_a, out_p = pe.compute_step(in_act=3, in_psum=10)

    print("1. KET QUA BUOC TINH TOAN CUA PHAN TU PHAN CUNG PE:")
    print(f"   -> Trong so co dinh trong PE (W)  : {pe.weight}")
    print(f"   -> Tin hieu kich hoat di vao (X)  : 3")
    print(f"   -> Tong tich luy di xuong duoi    : {out_p} (10 + 3*5 = 25)")
    print(f"   -> Tin hieu tiep tuc chuyen sang  : {out_a}")

    assert out_p == 25 and out_a == 3, "Loi Systolic PE!"
    print("\n[THANH CONG] DA HOAN THANH MO PHONG LUONG DU LIEU SYSTOLIC ARRAY CHO GOOGLE TPU!")
