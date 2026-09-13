"""
================================================================================
          MODULE AG: HARDWARE-IN-THE-LOOP (HIL) & FLIGHT SIMULATION
              MILESTONE AG.1: TÍCH PHÂN ĐỘNG LỰC HỌC BAY RUNGE-KUTTA BẬC 4 (RK4)
================================================================================

TẠI SAO BÀI TOÁN MÔ PHỎNG VŨ TRỤ (NASA/SPACEX) CẤM DÙNG TÍCH PHÂN EULER ĐƠN GIẢN?
Phương pháp Euler (x_new = x + v * dt): Sai số tích lũy rất lớn làm quỹ đạo bay văng ra ngoài!
- Thuật toán **Runge-Kutta bậc 4 (RK4)**:
  + Lấy 4 mẫu độ dốc (k1, k2, k3, k4) tại đầu, giữa và cuối bước nhảy thời gian dt:
    k1 = f(t, y)
    k2 = f(t + dt/2, y + dt*k1/2)
    k3 = f(t + dt/2, y + dt*k2/2)
    k4 = f(t + dt,   y + dt*k3)
  + Trung bình trọng số: y_next = y + (dt / 6) * (k1 + 2*k2 + 2*k3 + k4)
  + Độ chính xác bậc O(dt^4), mô phỏng quỹ đạo bay hoàn hảo tuyệt đối!
"""

import numpy as np

def rk4_step(dynamics_func, y: np.ndarray, t: float, dt: float) -> np.ndarray:
    """
    Trò đóng vai Kỹ sư Mô phỏng Động lực học Tên lửa:
    - Tính k1 = dynamics_func(t, y)
    - Tính k2 = dynamics_func(t + dt/2, y + dt*k1/2)
    - Tính k3 = dynamics_func(t + dt/2, y + dt*k2/2)
    - Tính k4 = dynamics_func(t + dt, y + dt*k3)
    - y_next = y + (dt / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
    - Trả về: y_next
    """
    k1 = dynamics_func(t, y)
    k2 = dynamics_func(t + 0.5 * dt, y + 0.5 * dt * k1)
    k3 = dynamics_func(t + 0.5 * dt, y + 0.5 * dt * k2)
    k4 = dynamics_func(t + dt, y + dt * k3)
    
    y_next = y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return y_next


if __name__ == "__main__":
    print("=========================================================")
    print("   AEROSPACE HIL: 4TH-ORDER RUNGE-KUTTA (RK4) INTEGRATOR")
    print("=========================================================\n")

    # Mô hình rơi tự do có lực cản: dy/dt = [v, -g - 0.1*v]
    # y = [độ cao z, vận tốc v]
    def flight_dynamics(t, state):
        z, v = state[0], state[1]
        g = 9.81
        drag = 0.05 * v * abs(v)
        dz_dt = v
        dv_dt = -g - drag
        return np.array([dz_dt, dv_dt], dtype=np.float32)

    # Tên lửa xuất phát ở độ cao 1000m, đang bay lên với vận tốc +50 m/s
    state_0 = np.array([1000.0, 50.0], dtype=np.float32)
    dt_step = 0.1  # 100ms

    state_next = rk4_step(flight_dynamics, state_0, t=0.0, dt=dt_step)

    print("1. KET QUA TICH PHAN TRANG THAI BAY CHINH XAC RK4:")
    print(f"   -> Do cao ban dau    : {state_0[0]:.2f} m, Van toc: {state_0[1]:.2f} m/s")
    print(f"   -> Sau 0.1s (RK4)    : Do cao = {state_next[0]:.2f} m, Van toc = {state_next[1]:.2f} m/s")

    assert state_next[0] > 1000.0 and state_next[1] < 50.0, "Loi RK4 Flight Integrator!"
    print("\n[THANH CONG] DA HOAN THANH BO TICH PHAN PHUONG TRINH VI PHAN RK4 CHO MO PHONG BAY!")
