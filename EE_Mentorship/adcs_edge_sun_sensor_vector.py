"""
================================================================================
          MODULE AE: SATELLITE ATTITUDE DETERMINATION & CONTROL (ADCS)
              MILESTONE AE.2: XÁC ĐỊNH VECTOR MẶT TRỜI (TRI-AXIAL SUN SENSOR)
================================================================================

TẠI SAO CẦN CẢM BIẾN MẶT TRỜI (SUN SENSOR) ĐỂ ĐỊNH VỊ TƯ THẾ TRONG QUỸ ĐẠO?
Vệ tinh cần quay tấm pin quang điện (Solar Panels) hướng thẳng về phía Mặt Trời:
- 6 cảm biến quang Diode gắn trên 6 mặt vệ tinh: [+X, -X, +Y, -Y, +Z, -Z].
- Cường độ dòng điện quang tỉ lệ thuận với góc chiếu ánh sáng:
  I_x = I_max * cos(theta_x)
- Vector định hướng Mặt Trời đơn vị (Unit Sun Vector S):
  S_raw = [I_+x - I_-x, I_+y - I_-y, I_+z - I_-z]
  S_unit = S_raw / norm(S_raw)
"""

import numpy as np

def extract_sun_unit_vector(currents_6axis: dict) -> np.ndarray:
    """
    currents_6axis: {'+X': 1.0, '-X': 0.0, '+Y': 0.5, '-Y': 0.0, '+Z': 0.0, '-Z': 0.0}
    Trò đóng vai Kỹ sư Định vị Không gian:
    - Tính sx = currents_6axis['+X'] - currents_6axis['-X']
    - Tính sy = currents_6axis['+Y'] - currents_6axis['-Y']
    - Tính sz = currents_6axis['+Z'] - currents_6axis['-Z']
    - Chuẩn hóa thành vector đơn vị: S_unit = S / np.linalg.norm(S)
    """
    sx = currents_6axis.get('+X', 0.0) - currents_6axis.get('-X', 0.0)
    sy = currents_6axis.get('+Y', 0.0) - currents_6axis.get('-Y', 0.0)
    sz = currents_6axis.get('+Z', 0.0) - currents_6axis.get('-Z', 0.0)
    
    vec = np.array([sx, sy, sz], dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        return vec / norm
    return np.array([0.0, 0.0, 0.0], dtype=np.float32)


if __name__ == "__main__":
    print("=========================================================")
    print("   SATELLITE ADCS: COARSE SUN SENSOR VECTOR EXTRACTION")
    print("=========================================================\n")

    # Ánh sáng mặt trời chiếu mạnh vào mặt +X và một phần vào mặt +Y
    photodiodes = {'+X': 8.0, '-X': 0.0, '+Y': 6.0, '-Y': 0.0, '+Z': 0.0, '-Z': 0.0}
    sun_vec = extract_sun_unit_vector(photodiodes)

    print("1. KET QUA XAC DINH HUONG MAT TROI DON VI (UNIT VECTOR):")
    print(f"   -> Dong quang 6 mat (mA)      : {photodiodes}")
    print(f"   -> Vector Mat Troi S (x, y, z): [{sun_vec[0]:.3f}, {sun_vec[1]:.3f}, {sun_vec[2]:.3f}]")
    print(f"   -> Do dai vector (Norm)       : {np.linalg.norm(sun_vec):.3f}")

    assert abs(np.linalg.norm(sun_vec) - 1.0) < 1e-5 and sun_vec[0] == 0.8 and sun_vec[1] == 0.6, "Loi Sun Sensor!"
    print("\n[THANH CONG] DA HOAN THANH BO DINH HUONG MAT TROI QUAY PIN NANG LUONG CHO VE TINH!")
