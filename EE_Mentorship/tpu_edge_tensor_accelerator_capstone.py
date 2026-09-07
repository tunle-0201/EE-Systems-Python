"""
================================================================================
          MODULE AA CAPSTONE FINALE: BỘ VI XỬ LÝ NPU TENSOR ACCELERATOR HOÀN CHỈNH
================================================================================

TÍCH HỢP TOÀN BỘ NPU HARDWARE PIPELINE: AFFINE INT8 + INT4 NIBBLE PACKER + SYSTOLIC PE
"""

from tpu_edge_int8_affine_quantizer import compute_affine_quantization_params, quantize_float_to_uint8
from tpu_edge_int4_weight_packer import pack_int4_weights, unpack_int4_weights
from tpu_edge_systolic_dataflow import ProcessingElement
import numpy as np

def run_edge_npu_tensor_pipeline():
    # 1. Lượng tử hóa Int8 cho đầu vào cảm biến
    raw_input = np.array([0.0, 5.0, 10.0], dtype=np.float32)
    s, z = compute_affine_quantization_params(0.0, 10.0)
    q_in = quantize_float_to_uint8(raw_input, s, z)

    # 2. Đóng gói nén trọng số 4-bit vào Flash
    weights_4bit = [2, 7, 4, 15]
    packed_w = pack_int4_weights(weights_4bit)
    unpacked_w = unpack_int4_weights(packed_w, len(weights_4bit))

    # 3. Nạp trọng số vào PE Systolic và chạy tính tích vô hướng phần cứng
    pe = ProcessingElement(weight=unpacked_w[1])  # W = 7
    _, psum = pe.compute_step(in_act=int(q_in[1]), in_psum=0)

    return len(packed_w), unpacked_w[1], psum


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AA CAPSTONE: HARDWARE NPU TENSOR ENGINE")
    print("=========================================================\n")

    w_bytes, w_val, acc_res = run_edge_npu_tensor_pipeline()

    print("1. KET QUA HOAT DONG TOAN CHUOI NPU TENSOR ACCELERATOR:")
    print(f"   -> Kich thuoc khoi trong so pack  : {w_bytes} bytes (Nen 4-bit)")
    print(f"   -> Trong so nap vao PE thanh ghi  : {w_val}")
    print(f"   -> Ket qua MAC Unit Systolic tinh : {acc_res}")

    assert w_bytes == 2 and w_val == 7 and acc_res > 0, "Loi Capstone NPU Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE AA: NPU TENSOR CORES!")
    print("=========================================================")
