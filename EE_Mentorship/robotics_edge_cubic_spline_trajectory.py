"""
================================================================================
          MODULE P: ADVANCED ROBOTICS KINEMATICS & TRAJECTORY PLANNING
              MILESTONE P.2: QUỸ ĐẠO BẬC 3 MƯỢT MÀ (CUBIC TRAJECTORY GENERATOR)
================================================================================

TẠI SAO CẦN LẬP KẾ HOẠCH QUỸ ĐẠO BẬC 3 TRONG ROBOTICS?
Nếu điều khiển Drone bay giật cục giữa các điểm Waypoint:
- Gia tốc thay đổi đột ngột (Jerk cao) làm rung lắc khung cơ khí và cháy motor.
- Đa thức bậc 3 (Cubic Polynomial):
  s(t) = a0 + a1*t + a2*t^2 + a3*t^3
- Đảm bảo vận tốc đầu và cuối bằng 0 ($v_0 = v_f = 0$), quỹ đạo bay lướt êm ái như bay lượn!
"""

import numpy as np

def generate_cubic_trajectory_point(p0: float, pf: float, t: float, tf: float) -> float:
    """
    Trò đóng vai Kỹ sư Điều khiển Robotics:
    - a0 = p0
    - a1 = 0
    - a2 = 3*(pf - p0) / (tf**2)
    - a3 = -2*(pf - p0) / (tf**3)
    - p(t) = a0 + a2*(t**2) + a3*(t**3)
    - Trả về: p(t)
    """
    if t <= 0:
        return p0
    if t >= tf:
        return pf
    
    a0 = p0
    a2 = 3.0 * (pf - p0) / (tf ** 2)
    a3 = -2.0 * (pf - p0) / (tf ** 3)
    
    pos = a0 + a2 * (t ** 2) + a3 * (t ** 3)
    return pos


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EE: CUBIC POLYNOMIAL TRAJECTORY PLANNER")
    print("=========================================================\n")
    
    # Bay từ tọa độ p0 = 0m đến pf = 10m trong tổng thời gian tf = 2.0s
    # Tại thời điểm t = 1.0s (chính giữa hành trình), vị trí phải đúng bằng 5.0m
    pos_mid = generate_cubic_trajectory_point(p0=0.0, pf=10.0, t=1.0, tf=2.0)
    
    print("1. KET QUA HOACH DINH QUY DAO MUOT MA REAL-TIME:")
    print(f"   -> Vi tri Drone tai giua hanh trinh : {pos_mid:.2f} m")
    
    assert abs(pos_mid - 5.0) < 1e-5, "Loi Cubic Trajectory!"
    print("\n[THANH CONG] DA HOAN THANH BO HOACH DINH QUY DAO MUOT MA CHO DRONE VA TAY ROBOT!")
