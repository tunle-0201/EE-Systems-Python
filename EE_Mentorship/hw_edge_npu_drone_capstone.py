"""
================================================================================
          MODULE J CAPSTONE FINALE: BỘ VI XỬ LÝ NPU NHÚNG CHO DRONE (NPU SIMULATOR)
================================================================================

TÍCH HỢP TOÀN BỘ PHẦN CỨNG TĂNG TỐC AI: MAC UNIT + SYSTOLIC ARRAY + VECTOR SIMD
"""

from hw_edge_mac_unit import HardwareMACUnit
from hw_edge_systolic_array import compute_2x2_systolic_array
from hw_edge_vector_simd import compute_128bit_simd_dot_product
import numpy as np

def run_edge_npu_accelerator_pipeline(sensor_inputs, model_weights):
    # 1. Khởi động mảng Systolic Array nhân ma trận nơ-ron
    A = np.array([[sensor_inputs[0], sensor_inputs[1]], [sensor_inputs[2], sensor_inputs[3]]])
    B = np.array([[model_weights[0], model_weights[1]], [model_weights[2], model_weights[3]]])
    sys_res = compute_2x2_systolic_array(A, B)
    
    # 2. Xử lý qua Vector SIMD 128-bit
    v_out = compute_128bit_simd_dot_product(sensor_inputs, model_weights)
    
    # 3. Thanh ghi MAC tích lũy chót
    mac = HardwareMACUnit()
    mac.process_mac(v_out, 1.0)
    return sys_res, v_out, mac.accumulator


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE J CAPSTONE: EMBEDDED DRONE NPU CO-PROCESSOR")
    print("=========================================================\n")
    
    inputs = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    weights = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    
    sys_m, simd_val, final_acc = run_edge_npu_accelerator_pipeline(inputs, weights)
    
    print("1. KET QUA HOAT DONG TOAN CHUOI PHAN CUNG EMBEDDED NPU:")
    print(f"   -> Systolic Array Output Matrix :\n{sys_m}")
    print(f"   -> Vector SIMD 128-bit Sum      : {simd_val:.2f}")
    print(f"   -> Final MAC Accumulator Value  : {final_acc:.2f}")
    
    assert final_acc == 5.0, "Loi Capstone NPU Simulator Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE J: NPU HARDWARE ACCELERATION!")
    print("=========================================================")
