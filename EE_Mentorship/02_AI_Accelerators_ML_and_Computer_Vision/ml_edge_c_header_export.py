"""
================================================================================
          MODULE E: EDGE AI & EMBEDDED NEURAL NETWORKS
              MILESTONE E.3: XUẤT MÔ HÌNH AI RA FILE NGUỒN C-HEADER DÀNH CHO ESP32/STM32
================================================================================

TẠI SAO CẦN XUẤT MÔ HÌNH AI RA MẢNG C-HEADER (`.h`)?
Các vi điều khiển phần cứng (như ESP32, STM32, Arduino):
- Không có môi trường Python runtime hay thư viện NumPy.
- Kỹ sư EE phải xuất các Trọng số W học được từ Python thành một Mảng C (`const float W_weights[]`).
- Nhúng trực tiếp mảng C này vào bộ nhớ Flash của vi điều khiển!

Nhiệm vụ của Kỹ sư trưởng trong hàm `export_weights_to_c_header(W, var_name="W_drone_weights")`:
1. Chuyển mảng W thành chuỗi format mảng C:
   `c_code = f"const float {var_name}[{len(W)}] = {{" + ", ".join([f"{val:.4f}f" for val in W]) + "};"`
2. Trả về: c_code
"""

import numpy as np

def export_weights_to_c_header(W, var_name="W_drone_weights"):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ C-Header Export từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Chuyển đổi mảng W thành chuỗi mảng C: const float var_name[N] = {val1f, val2f, ...};
    - Trả về: c_code
    """
    elements = [f"{val:.4f}f" for val in W]
    c_code = f"const float {var_name}[{len(W)}] = {{" + ", ".join(elements) + "};"
    return c_code



if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI: EXPORTING AI MODEL TO C-HEADER FOR STM32/ESP32")
    print("=========================================================\n")
    
    W_weights = np.array([3.1415, -2.7182, 0.5000, 1.2345])
    
    c_header_str = export_weights_to_c_header(W_weights, "W_drone_weights")
    
    if c_header_str is not None:
        print("1. KET QUA MA NGUON C-HEADER DANH CHO VI DIEU KHIEN EE:")
        print(f"   -> Ma C-Array nhung RAM Flash : {c_header_str}")
        
        # Kiểm tra tính chính xác
        assert "const float W_drone_weights[4]" in c_header_str, "Loi export ma C-Header!"
        
        print("\n[THANH CONG] TRO DA XUAT THANH CONG MO HINH AI THANH MANG C NHUNG THANG VAO CHIP EE!")
