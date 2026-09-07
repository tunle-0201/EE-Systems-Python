"""
================================================================================
          MODULE AA: EMBEDDED HARDWARE TENSOR ACCELERATION & NPU CORES
              MILESTONE AA.1: LƯỢNG TỬ HÓA TUYẾN TÍNH INT8 (AFFINE QUANTIZATION)
================================================================================

TẠI SAO CÁC CHIP NPU (APPLE NEURAL ENGINE, GOOGLE TPU) DÙNG AFFINE QUANTIZATION?
Chuyển đổi số thực Float32 sang số nguyên không âm UInt8 [0..255]:
  q = round(r / S) + Z
- S (Scale): Tỷ lệ co dãn bước nhảy.
- Z (Zero-point): Điểm không thực tế, bảo đảm số 0.0 thực tế ánh xạ chính xác
  vào một số nguyên nguyên vẹn để không bị mất mát khi đệm ma trận (Zero-Padding)!
- Giải lượng tử hóa: r_approx = S * (q - Z)
"""

import numpy as np

def compute_affine_quantization_params(r_min: float, r_max: float, q_min: int = 0, q_max: int = 255):
    """
    Trò đóng vai Kỹ sư Biên dịch Mô hình NPU:
    - S = (r_max - r_min) / (q_max - q_min)
    - Z = round((0.0 - r_min) / S) + q_min
    - Kẹp Z trong dải [q_min..q_max]
    """
    S = (r_max - r_min) / (q_max - q_min)
    Z = int(np.round((0.0 - r_min) / S)) + q_min
    Z = int(np.clip(Z, q_min, q_max))
    return S, Z

def quantize_float_to_uint8(r_array: np.ndarray, S: float, Z: int) -> np.ndarray:
    q = np.round(r_array / S) + Z
    return np.clip(q, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    print("=========================================================")
    print("   NPU ACCELERATOR: AFFINE INT8 QUANTIZATION ENGINE")
    print("=========================================================\n")

    # Mảng trọng số nơ-ron Float32 ban đầu: [-10.0 .. +30.0]
    weights_fp32 = np.array([-10.0, 0.0, 10.0, 30.0], dtype=np.float32)
    scale, zero_pt = compute_affine_quantization_params(-10.0, 30.0)

    quantized_u8 = quantize_float_to_uint8(weights_fp32, scale, zero_pt)
    reconstructed = scale * (quantized_u8.astype(np.float32) - zero_pt)

    print("1. KET QUA LUONG TU HOA AFFINE INT8 TREN NPU:")
    print(f"   -> Scale (S)              : {scale:.4f}")
    print(f"   -> Zero-Point (Z)         : {zero_pt}")
    print(f"   -> Mang UInt8 sau nen     : {quantized_u8}")
    print(f"   -> Gia tri tai tao xap xi : {reconstructed}")

    # So 0.0 phai duoc anh xa chinh xac tuyet doi vao zero_pt
    assert quantized_u8[1] == zero_pt and np.allclose(weights_fp32, reconstructed, atol=0.2), "Loi Affine Quantization!"
    print("\n[THANH CONG] DA HOAN THANH ENGINE LUONG TU HOA INT8 KHONG MAT MAT SO 0 CHO NPU!")
