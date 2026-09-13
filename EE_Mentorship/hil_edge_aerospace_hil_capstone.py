"""
================================================================================
          MODULE AG CAPSTONE FINALE: DÀN MÔ PHỎNG PHẦN CỨNG HIL CHO KHÔNG GIAN
================================================================================

TÍCH HỢP TOÀN BỘ HIL AVIONICS PIPELINE: RK4 INTEGRATOR + NOISE INJECTOR + PRO-NAV
"""

from hil_edge_rk4_flight_integrator import rk4_step
from hil_edge_sensor_noise_injector import HILSensorNoiseInjector
from hil_edge_proportional_navigation import compute_proportional_navigation_accel
import numpy as np

def run_aerospace_hil_simulator_cycle():
    # 1. Tích phân RK4 cập nhật trạng thái vật lý thực của Drone
    def simple_missile_dynamics(t, state):
        pos, vel = state[:2], state[2:]
        return np.array([vel[0], vel[1], 0.0, -9.81], dtype=np.float32)

    s0 = np.array([0.0, 500.0, 100.0, 0.0], dtype=np.float32)
    s1 = rk4_step(simple_missile_dynamics, s0, t=0.0, dt=0.05)

    # 2. Bơm nhiễu cảm biến HIL vào số đo độ cao
    injector = HILSensorNoiseInjector(white_noise_std=0.05, bias_drift_std=0.001)
    measured_alt = injector.inject_noise(float(s1[1]), seed=42)

    # 3. Tính toán gia tốc dẫn đường đánh chặn Pro-Nav
    r_target = np.array([500.0, 50.0], dtype=np.float32)
    v_target = np.array([-150.0, 10.0], dtype=np.float32)
    a_steer = compute_proportional_navigation_accel(r_target, v_target, N_gain=3.5)

    return s1[0], measured_alt, np.linalg.norm(a_steer)


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AG CAPSTONE: AEROSPACE HIL FLIGHT SIMULATOR")
    print("=========================================================\n")

    x_true, alt_meas, a_mag = run_aerospace_hil_simulator_cycle()

    print("1. KET QUA CHU KY MO PHONG HIL REAL-TIME:")
    print(f"   -> Vi tri X vat ly thuc (RK4) : {x_true:.2f} m")
    print(f"   -> Do cao do duoc co nhieu HIL: {alt_meas:.2f} m")
    print(f"   -> Do lon gia toc Pro-Nav     : {a_mag:.2f} m/s2")

    assert x_true > 0 and abs(alt_meas - 500.0) < 2.0 and a_mag > 0, "Loi Capstone HIL Simulator!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE AG: AEROSPACE HIL TESTBENCH!")
    print("=========================================================")
