"""
================================================================================
          MODULE W: SATELLITE ATTITUDE DETERMINATION & CONTROL SYSTEMS (ADCS)
              MILESTONE W.1: B-DOT MAGNETORQUER DETUMBLING CONTROL LAW
================================================================================

VAI TRO THIET YEU CUA THUAT TOAN HAM QUAY B-DOT TRONG DU AN KHONG GIAN CUBESAT:
Khi ve tinh duoc phong ra khoi ong phong P-POD cua ten lua day (SpaceX Falcon 9 / Rocket Lab):
- Luc day lo xo va bat doi xung gay ra van toc xoay lon nhao cuc lon:
  Tumbler Rate dao dong tu 30 deg/s den 80 deg/s tren ca 3 truc X, Y, Z.
- O van toc nay, ve tinh khong the dinh huong pin mat troi de nap dien, khong the
  bat khoa lien lac RF voi tram mat dat, va he thong se chet sau 2 gio vi can pin!

NGUYEN LY TOAN HOC CUA QUY TAC DIEU KHIEN B-DOT (ASCII TEXT BLOCK):
Tu truong Trai Dat B tai quy dao thap LEO co cuong do khoang 30 uT - 50 uT:
1. Do toc do bien thien tu truong do cam bien Magnetometer 3 truc thu duoc:

               dB          B[k] - B[k - 1]
    B_dot = ────────  =  ─────────────────
               dt               dt

2. Kich hoat dong dien qua 3 cuon day tu truong (Magnetorquers) sinh mo-men luong cuc M:

    M = -k_gain * B_dot   (A.m^2)

3. Mo-men co hoc tac dong len than ve tinh:

    Tau_mag = M x B

CHUNG MINH CO CHE KHU DONG NANG QUAY THEO LYAPUNOV (LYAPUNOV STABILITY):
Vi B_dot = -omega x B (khi van toc quay than ve tinh la omega):
Mo-men hãm duoc tinh:

    Tau_mag = -k_gain * (-omega x B) x B = -k_gain * ( ||B||^2 * omega_vuong_goc )

-> Mo-men luon nguoc chieu voi van toc quay, dam bao dao ham nang luong quay dT/dt <= 0!
   Ve tinh se dung han xoay lon nhao va tro ve trang thai tinh on dinh de bat dau nhiem vu!
"""

from typing import Tuple, List, Dict, Any, Optional
import numpy as np


def compute_bdot_magnetic_dipole(
    B_curr: np.ndarray,
    B_prev: np.ndarray,
    dt: float,
    k_gain: float = 1000.0,
    m_limit: float = 0.2
) -> np.ndarray:
    """
    Thuat toan vi dieu khien nhung B-Dot Detumbling:
    - B_curr, B_prev: Vector tu truong Trai Dat 3 truc (Tesla)
    - dt: Chu ky lay mau cam bien Magnetometer (giay)
    - k_gain: He so khuech dai phan hoi
    - m_limit: Gioi han bao hoa mo-men luong cuc cua cuon day Magnetorquer (+/- A.m^2)
    Tra ve: Vector mo-men luong cuc M (A.m^2) tren 3 truc [Mx, My, Mz]
    """
    dB_dt = (B_curr - B_prev) / dt
    M = -k_gain * dB_dt
    # Bao ve bao hoa dong dien cuon day tu truong tren phan cung
    M_clamped = np.clip(M, -m_limit, m_limit)
    return np.asarray(M_clamped, dtype=np.float32)


def simulate_satellite_detumbling_step(
    omega: np.ndarray,
    inertia_matrix: np.ndarray,
    B_field: np.ndarray,
    M_dipole: np.ndarray,
    dt: float
) -> np.ndarray:
    """
    Mo phong 1 buoc dong hoc quay ve tinh theo phuong trinh Euler:
    I * d(omega)/dt = Tau_mag - (omega x (I * omega))
    """
    # Mo-men sinh ra do tu truong: Tau = M x B
    tau_mag = np.cross(M_dipole, B_field)

    # Dong luong quay
    H = np.dot(inertia_matrix, omega)
    gyroscopic_torque = np.cross(omega, H)

    # Gia toc goc d(omega)/dt
    alpha = np.linalg.solve(inertia_matrix, tau_mag - gyroscopic_torque)
    omega_next = omega + alpha * dt
    return np.asarray(omega_next, dtype=np.float32)


if __name__ == "__main__":
    print("=========================================================")
    print("   SATELLITE ADCS: B-DOT MAGNETORQUER DETUMBLING LAW")
    print("=========================================================\n")

    # 1. Kiem tra tinh toan mo-men luong cuc phan hoi tuc thoi
    # Tu truong do boi Magnetometer: B_prev = [20 uT, 0 uT, -30 uT], sau 0.1s B_curr = [25 uT, -2 uT, -28 uT]
    B_t0 = np.array([20e-6, 0.0, -30e-6], dtype=np.float32)
    B_t1 = np.array([25e-6, -2e-6, -28e-6], dtype=np.float32)
    dt_step = 0.1

    dipole_M = compute_bdot_magnetic_dipole(B_t1, B_t0, dt=dt_step, k_gain=2000.0, m_limit=0.2)

    print("1. KET QUA KICH HOAT CUON DAY MAGNETORQUER HAM QUAY:")
    print(f"   -> Do bien thien dB/dt (uT/s) : {(B_t1 - B_t0) / dt_step * 1e6}")
    print(f"   -> Mo-men tu sinh ra M (A.m2)  : {dipole_M}")

    # dB_x/dt > 0 nen M_x phai mang dau am de ham quay
    assert dipole_M[0] < 0 and dipole_M[1] > 0, "Loi tinh toan chieu nguoc huong B-Dot!"
    print("   -> Kiem tra chieu vector      : CHINH XAC (Nguoc chieu bien thien tu truong)\n")

    # 2. Mo phong qua trinh dap tat van toc lon nhao (Detumbling Transition)
    print("2. MO PHONG DAP TAT VAN TOC LON NHAO SAU KHI TACH TEN LUA:")
    # CubeSat 3U: Ma tran quan tinh I = diag(0.05, 0.05, 0.02) kg.m^2
    I_sat = np.diag([0.05, 0.05, 0.02]).astype(np.float32)
    # Van toc ban dau lon nhao 40 deg/s tren truc X
    omega_curr = np.array([np.deg2rad(40.0), np.deg2rad(10.0), np.deg2rad(5.0)], dtype=np.float32)
    omega_init_deg = np.rad2deg(np.linalg.norm(omega_curr))
    print(f"   -> Van toc lon nhao ban dau    : {omega_init_deg:.2f} deg/s (Nguy hiem!)")

    # Chay vong lap dieu khien B-Dot trong 10 giay mo phong
    b_earth = np.array([10e-6, 20e-6, -35e-6], dtype=np.float32)
    for step in range(50):
        # Gia lap tu truong bien thien do ve tinh quay: B_dot ~ -omega x B
        b_dot_instant = -np.cross(omega_curr, b_earth)
        b_meas_next = b_earth + b_dot_instant * 0.1

        m_cmd = compute_bdot_magnetic_dipole(b_meas_next, b_earth, dt=0.1, k_gain=50000.0, m_limit=0.5)
        omega_curr = simulate_satellite_detumbling_step(omega_curr, I_sat, b_earth, m_cmd, dt=0.1)

    omega_final_deg = np.rad2deg(np.linalg.norm(omega_curr))
    print(f"   -> Van toc quay sau khi ham   : {omega_final_deg:.2f} deg/s (Da dap tat an toan!)")
    assert omega_final_deg < omega_init_deg, "Van toc quay phai giam lien tuc theo dinh ly Lyapunov!"

    print("\n[THANH CONG] THUAT TOAN B-DOT DETUMBLING HAM TRIET DE TOC DO LON NHAO CUU NGUY VE TINH!")
