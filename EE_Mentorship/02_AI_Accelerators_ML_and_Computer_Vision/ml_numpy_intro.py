"""
================================================================================
          MODULE B: MACHINE LEARNING & NUMPY MATRIX OPERATIONS
              MILESTONE B.1: CHUYỂN ĐỔI MA TRẬN DỮ LIỆU CẢM BIẾN
================================================================================

Trong Machine Learning và AI, ta không dùng List của Python để tính toán 
vì nó rất chậm. Ta dùng NumPy Array (Mảng Ma Trận Đa Chiều).

Bài toán:
Trò có dữ liệu 3 Cảm biến Drone (Mỗi cảm biến đo 3 thông số: Temp, Volt, Altitude):
Raw Data = [
    [25.0, 3.7, 100.0],  # Cảm biến 1
    [26.5, 3.6, 102.5],  # Cảm biến 2
    [24.8, 3.8, 99.5]    # Cảm biến 3
]

Nhiệm vụ 2 phút của trò:
Hoàn thành TODO 1: Chuyển đổi `raw_sensor_data` thành Mảng NumPy bằng lệnh `np.array()`
"""

import numpy as np

# Dữ liệu dạng List truyền thống của Python
raw_sensor_data = [
    [25.0, 3.7, 100.0],
    [26.5, 3.6, 102.5],
    [24.8, 3.8, 99.5]
]

def convert_to_numpy_matrix(data_list):
    """
    TODO 1: Chuyển đổi danh sách List thành NumPy Array.
    Cú pháp: return np.array(data_list)
    """
    return np.array(data_list)


if __name__ == "__main__":
    print("=== NHẬP MÔN MACHINE LEARNING: MA TRẬN NUMPY ===")
    
    # 1. Chuyển đổi sang Ma trận NumPy
    matrix = convert_to_numpy_matrix(raw_sensor_data)
    
    print(f"\n1. Dạng Ma trận NumPy (2D Tensor):\n{matrix}")
    print(f"   -> Kích thước ma trận (Shape): {matrix.shape} (3 hàng, 3 cột)")
    print(f"   -> Kiểu dữ liệu trong RAM (Dtype): {matrix.dtype}")

    # 2. Phép toán Vectơ thần tốc của AI (Không dùng vòng lặp for!)
    # Tính trung bình cộng của từng cột (0: Temp, 1: Volt, 2: Altitude)
    averages = np.mean(matrix, axis=0)
    
    print(f"\n2. Kết quả tính toán của AI (Vectorized Execution):")
    print(f"   -> Nhiệt độ trung bình : {averages[0]:.2f} °C")
    print(f"   -> Điện áp trung bình  : {averages[1]:.2f} V")
    print(f"   -> Độ cao trung bình   : {averages[2]:.2f} m")
    
    print("\n[THÀNH CÔNG] TRÒ ĐÃ HOÀN THÀNH BÀI HỌC 2 PHÚT VỀ MA TRẬN AI!")
