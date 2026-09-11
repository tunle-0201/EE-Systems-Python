"""
================================================================================
          MODULE AE CAPSTONE FINALE: HỆ THỐNG ĐIỀU KHIỂN TƯ THẾ VỆ TINH TOÀN DIỆN
================================================================================

TÍCH HỢP TOÀN BỘ SATELLITE ADCS: B-DOT DETUMBLING + SUN SENSOR + REACTION WHEEL
"""

from adcs_edge_bdot_detumbling import compute_bdot_magnetic_dipole
from adcs_edge_sun_sensor_vector import extract_sun_unit_vector
from adcs_edge_reaction_wheel_desat import compute_magnetic_desaturation_torque
import numpy as np

def run_satellite_adcs_flight_engine():
    # 1. Hãm quay B-Dot sau khi tách tên lửa
    b_curr = np.array([30e-6, 5e-6, 10e-6], dtype=np.float32)
    b_prev = np.array([20e-6, 5e-6, 10e-6], dtype=np.float32)
    m_detumble = compute_bdot_magnetic_dipole(b_curr, b_prev, dt=0.1, k_gain=1000.0)

    # 2. Xác định hướng Mặt Trời để quay pin quang điện
    solar_diodes = {'+X': 10.0, '-X': 0.0, '+Y': 0.0, '-Y': 0.0, '+Z': 0.0, '-Z': 0.0}
    sun_vector = extract_sun_unit_vector(solar_diodes)

    # 3. Xả động lượng bánh đà bão hòa
    h_wheel = np.array([0.0, 0.2, 0.0], dtype=np.float32)
    _, tau_dump = compute_magnetic_desaturation_torque(h_wheel, b_curr, k_dump=0.05)

    return m_detumble[0], sun_vector[0], tau_dump[1]


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AE CAPSTONE: SATELLITE ADCS FLIGHT ENGINE")
    print("=========================================================\n")

    m_x, s_x, tau_y = run_satellite_adcs_flight_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI SATELLITE ADCS ENGINE:")
    print(f"   -> B-Dot Magnetic Dipole Mx (A.m2) : {m_x:.3f}")
    print(f"   -> Sun Vector Chi huong mat +X     : {s_x:.2f}")
    print(f"   -> Mo-men xa dong luong banh da    : {tau_y:.6f}")

    assert m_x < 0 and s_x == 1.0 and tau_y < 0, "Loi Capstone ADCS!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE AE: SATELLITE ADCS SYSTEMS!")
    print("=========================================================")
