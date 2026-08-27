"""
================================================================================
          MODULE P: ADVANCED ROBOTICS KINEMATICS & TRAJECTORY PLANNING
              MILESTONE P.1: ĐẠI SỐ QUATERNION BIỂU DIỄN GÓC XOAY 3D (CHỐNG GIMBAL LOCK)
================================================================================

TẠI SAO CÁC KỸ SƯ HÀNG KHÔNG VŨ TRỤ (NASA, SPACEX, TESLA) DÙNG QUATERNION?
Nếu dùng 3 góc Euler (Roll, Pitch, Yaw):
- Khi góc Pitch = 90 độ, hệ tọa độ bị hiện tượng Khóa khớp (Gimbal Lock) - mất đi 1 bậc tự do!
- Đại số Quaternion 4 chiều $q = [w, x, y, z]$:
  + Triệt tiêu 100% hiện tượng Gimbal Lock.
  + Tính toán xoay vector 3D cực nhanh và mượt mà.
"""

import numpy as np

def quaternion_multiply(q1, q2):
    """
    Nhân 2 Quaternion q1 và q2: q = [w, x, y, z]
    Trò đóng vai Kỹ sư Robotics thiết kế tích Hamilton:
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + x1*y2 - y1*x2 + z1*w2
    """
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + x1*y2 - y1*x2 + z1*w2
    return np.array([w, x, y, z], dtype=np.float32)


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EE: 4D QUATERNION ROTATION ENGINE")
    print("=========================================================\n")
    
    # Quaternion đơn vị đại diện cho trạng thái ban đầu không xoay: [1, 0, 0, 0]
    q_identity = np.array([1.0, 0.0, 0.0, 0.0])
    
    # Quaternion xoay 90 độ quanh trục Z: w=cos(45°)=0.7071, z=sin(45°)=0.7071
    q_rot_z = np.array([0.7071, 0.0, 0.0, 0.7071])
    
    q_res = quaternion_multiply(q_identity, q_rot_z)
    
    print("1. KET QUA NHAN QUATERNION TRONG KHONG GIAN 3D:")
    print(f"   -> Quaternion sau khi xoay : {q_res}")
    
    assert abs(q_res[0] - 0.7071) < 1e-3 and abs(q_res[3] - 0.7071) < 1e-3, "Loi Quaternion!"
    print("\n[THANH CONG] DA HOAN THANH BO KHONG GIAN XOAY 4D QUATERNION CHO DRONE!")
