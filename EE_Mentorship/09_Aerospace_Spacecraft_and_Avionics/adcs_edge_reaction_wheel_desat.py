"""
================================================================================
          MODULE W: SATELLITE ATTITUDE DETERMINATION & CONTROL SYSTEMS (ADCS)
              MILESTONE W.3: REACTION WHEEL MAGNETIC DESATURATION
================================================================================

HIEN TUONG BAO HOA DONG LUONG BANH DA PHAN LUC (REACTION WHEEL SATURATION):
Tren cac ve tinh do tham quan su va vien thong (SpaceX Starlink, NASA CubeSat):
- Banh da phan luc (Reaction Wheels - RW) quay o toc do 3000 - 8000 RPM.
- Theo dinh luat bao toan mo-men dong luong: Gia toc banh da sinh ra noi mo-men
  chinh xac xoay than ve tinh huong ong kinh chup anh ma khong can ton nhien lieu day.
- Tuy nhien, cac nhieu dong khong gian ben ngoai (Ap suat photon buc xa Mat Troi,
  gradient trong truong Trai Dat, khi quyen loang LEO) lien tuc truyen dong luong vao than ve tinh.
- Banh da phai quay ngay cang nhanh de chong lai nhieu dong cho den khi cham kich tran
  toc do toi da cua dong co BLDC (vi du 8000 RPM) -> Banh da bi BAO HOA (Saturation),
  mat hoan toan kha nang dieu khien tu the!

THUAT TOAN XA DONG LUONG TU TRUONG (MAGNETIC MOMENTUM DUMPING):
De ha toc do banh da ve 0 RPM ma khong lam ve tinh bi xoay mat phuong huong:
1. Mo-men ngoai luc can thiet de triet tieu dong luong du thua:

         Tau_desat = -k_dump * (H_wheel - H_nominal)

2. Tinh toan mo-men tu M can thiet phat ra tu cuon day Magnetorquer:
   Vi Tau_ext = M x B, dung dong nhat thuc vector giai ra M:

                     B x Tau_desat
             M = ─────────────────────
                       ||B||^2

3. Mo-men ngoai luc thuc te do tu truong Trai Dat tao ra:

         Tau_applied = M x B

   Dong thoi, bo dieu khien banh da RW giam toc do Motor de hap thu mo-men nay,
   dua banh da tro ve trang thai an toan ma than ve tinh van giu nguyen toa do chup anh!
"""

from typing import Tuple, List, Dict, Any, Optional
import numpy as np


def compute_magnetic_desaturation_torque(
    wheel_momentum_h: np.ndarray,
    B_field: np.ndarray,
    k_dump: float = 0.05,
    m_max: float = 0.2
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Thuat toan xa dong luong banh da bang tu truong Trai Dat:
    - wheel_momentum_h: Vector dong luong hien tai cua 3 banh da [Hx, Hy, Hz] (N.m.s)
    - B_field: Vector tu truong Trai Dat do boi Magnetometer (Tesla)
    - k_dump: He so toc do xa dong luong
    - m_max: Gioi han vat ly mo-men cuon Magnetorquer (A.m^2)
    Tra ve: (M_dipole, Tau_applied)
    """
    tau_desat = -k_dump * wheel_momentum_h
    b_norm_sq = float(np.dot(B_field, B_field))

    if b_norm_sq < 1e-12:
        return np.zeros(3, dtype=np.float32), np.zeros(3, dtype=np.float32)

    # Tinh vector mo-men luong cuc tu: M = (B x Tau_desat) / ||B||^2
    m_calc = np.cross(B_field, tau_desat) / b_norm_sq
    # Kep an toan dong dien cuon Magnetorquer
    m_clamped = np.clip(m_calc, -m_max, m_max)

    # Mo-men thuc te tac dong len ve tinh: Tau = M x B
    tau_applied = np.cross(m_clamped, B_field)
    return np.asarray(m_clamped, dtype=np.float32), np.asarray(tau_applied, dtype=np.float32)


def simulate_wheel_desaturation_process(
    initial_h: np.ndarray,
    B_field: np.ndarray,
    k_dump: float = 0.05,
    dt_sec: float = 10.0,
    steps: int = 40
) -> List[float]:
    """
    Mo phong qua trinh xa dong luong giam toc banh da theo thoi gian
    """
    h_curr = np.copy(initial_h)
    h_history = []

    for _ in range(steps):
        _, tau_ext = compute_magnetic_desaturation_torque(h_curr, B_field, k_dump=k_dump)
        # Banh da hap thu mo-men ngoai luc de giam toc: dH = Tau_ext * dt
        h_curr = h_curr + tau_ext * dt_sec
        h_history.append(float(np.linalg.norm(h_curr)))

    return h_history


if __name__ == "__main__":
    print("=========================================================")
    print("   SATELLITE ADCS: REACTION WHEEL MAGNETIC DESATURATION")
    print("=========================================================\n")

    # 1. Kiem tra tinh toan mo-men xa dong luong tuc thoi
    # Banh da truc Z bi tich tu dong luong: H_z = 0.50 N.m.s
    # Tu truong Trai Dat: B = [0, 30 uT, 0] (huong theo truc Y)
    H_wheel = np.array([0.0, 0.0, 0.50], dtype=np.float32)
    B_earth = np.array([0.0, 30e-6, 0.0], dtype=np.float32)

    dipole_M, applied_tau = compute_magnetic_desaturation_torque(H_wheel, B_earth, k_dump=0.1, m_max=0.2)

    print("1. KET QUA TINH TOAN MO-MEN XA DONG LUONG TUC THOI:")
    print(f"   -> Dong luong banh da H (Nms)       : {H_wheel}")
    print(f"   -> Tu truong Trai Dat B (uT)        : {B_earth * 1e6}")
    print(f"   -> Mo-men tu cuon Magnetorquer M     : {dipole_M} A.m2")
    print(f"   -> Mo-men co hoc sinh ra Tau_ext    : {applied_tau} N.m")

    # Mo-men ngoai luc truc Z phai mang dau am de chong lai H_z duong
    assert applied_tau[2] < 0.0, "Mo-men sinh ra phai nguoc chieu de ha toc banh da!"
    print("   -> Chieu mo-men ham dong luong       : CHINH XAC (Tau_z < 0 triet tieu H_z)\n")

    # 2. Mo phong qua trinh xa dong luong banh da CubeSat (H_nom = 2.0 mN.m.s)
    print("2. MO PHONG TIEN TRINH XA DONG LUONG BANH DA CUBESAT (H = 2.0 mN.m.s):")
    h_cubesat = np.array([0.0, 0.0, 2.0e-3], dtype=np.float32)
    h_norms = simulate_wheel_desaturation_process(h_cubesat, B_earth, k_dump=0.08, dt_sec=10.0, steps=40)

    print(f"   -> Dong luong ban dau ||H|| (mNms)  : {h_norms[0] * 1e3:.3f}")
    print(f"   -> Dong luong sau 200 giay          : {h_norms[19] * 1e3:.3f}")
    print(f"   -> Dong luong sau 400 giay          : {h_norms[-1] * 1e3:.3f} (Ha ve an toan)")

    assert h_norms[-1] < h_norms[0], "Dong luong banh da phai giam lien tuc theo thoi gian!"
    assert h_norms[-1] < 1.0e-3, "Dong luong phai duoc xa xuong duoi muc 1.0 mN.m.s!"

    print("\n[THANH CONG] THUAT TOAN DESATURATION DA GIAI PHONG DONG LUONG BANH DA AN TOAN!")
