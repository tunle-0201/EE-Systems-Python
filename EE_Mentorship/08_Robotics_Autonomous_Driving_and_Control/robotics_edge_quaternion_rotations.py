"""
================================================================================
          MODULE P: ADVANCED ROBOTICS KINEMATICS & TRAJECTORY PLANNING
    MILESTONE P.1: DAI SO 4D QUATERNION GOC XOAY 3D CHONG KHOA KHOP GIMBAL LOCK
================================================================================

1. NGUYEN LY VAT LY & KY THUAT (AEROSPACE & ROBOTICS FOUNDATION):
   - Khi dieu khien Drone hoac canh tay Robot trong khong gian 3D, neu dung 3 goc
     Euler truyen thong (Roll phi, Pitch theta, Yaw psi):
     + Khi Pitch = 90 do, truc Roll va truc Yaw bi trung khop voi nhau.
     + He thong mat hoan toan 1 bac tu do quay (Hien tuong Gimbal Lock)!
     + Thuat toan dieu khien bi chia cho 0, khien he thong nhan sai goc va rot Drone!
   - Giai phap NASA, SpaceX va Tesla Autopilot: Dai so Quaternion 4 chieu:
     q = [w, x, y, z] trong do w la phan thuc, (x, y, z) la phan ao 3D.
     + Triet tieu 100% hien tuong Gimbal Lock.
     + Giam chi phi tinh toan: khong can ma tran xoay 3x3 cong kenh (9 phep tinh).

2. SO DO HINH HOC & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do hien tuong Gimbal Lock vs Khong gian 4D Hypersphere:
   
   [ 3 Goc Euler 3D ]                      [ 4D Unit Quaternion ]
   Truc Roll (X) ──┐                        q = [w, x, y, z]
   Truc Pitch (Y) ─┼──> Pitch = 90 deg ──>  Ban kinh mat cau = 1
   Truc Yaw (Z) ───┘    (Khoa khop!)        sqrt(w^2 + x^2 + y^2 + z^2) = 1.0
                        Roll va Yaw trung   (Muot ma 360 do moi huong!)

   Cong thuc chuyen doi Axis-Angle sang Quaternion:
   Goc xoay theta quanh vector truc don vi u = [ux, uy, uz]:
   
   w = cos(theta / 2)
   x = ux * sin(theta / 2)
   y = uy * sin(theta / 2)
   z = uz * sin(theta / 2)

   Tich Hamilton giua 2 Quaternion (Hamilton Product q = q1 * q2):
   
   w = w1*w2 - x1*x2 - y1*y2 - z1*z2
   x = w1*x2 + x1*w2 + y1*z2 - z1*y2
   y = w1*y2 - x1*z2 + y1*w2 + z1*x2
   z = w1*z2 + x1*y2 - y1*x2 + z1*w2

   Xoay vector 3D v = [vx, vy, vz] bang phep bien doi lien hop:
   p = [0, vx, vy, vz]  (Pure Quaternion)
   q_conj = [w, -x, -y, -z]
   p_rot = q * p * q_conj
   v_rot = [p_rot.x, p_rot.y, p_rot.z]
"""

import numpy as np


def quaternion_normalize(q: np.ndarray) -> np.ndarray:
    """
    Chuan hoa Quaternion ve do dai don vi (Unit Quaternion):
               q
    q_norm = ───────
             || q ||
    """
    norm = np.linalg.norm(q)
    if norm < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return q / norm


def quaternion_from_axis_angle(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    """
    Tao Quaternion don vi tu vector truc quay va goc xoay theta (radian).
    """
    axis = np.asarray(axis, dtype=np.float64)
    axis_norm = np.linalg.norm(axis)
    if axis_norm < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    u = axis / axis_norm
    half_angle = angle_rad / 2.0
    w = np.cos(half_angle)
    xyz = u * np.sin(half_angle)
    return np.array([w, xyz[0], xyz[1], xyz[2]], dtype=np.float64)


def quaternion_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """
    Nhan 2 Quaternion q1 va q2 theo tich Hamilton:
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + x1*y2 - y1*x2 + z1*w2
    """
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2

    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    return np.array([w, x, y, z], dtype=np.float64)


def quaternion_conjugate(q: np.ndarray) -> np.ndarray:
    """
    Tinh Quaternion lien hop:
    q_conj = [w, -x, -y, -z]
    """
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float64)


def rotate_vector_by_quaternion(v: np.ndarray, q: np.ndarray) -> np.ndarray:
    """
    Xoay vector 3D v trong khong gian bang Quaternion q:
    p_rot = q * [0, v] * q_conj
    v_rot = p_rot[1:4]
    """
    v = np.asarray(v, dtype=np.float64)
    p = np.array([0.0, v[0], v[1], v[2]], dtype=np.float64)
    q_norm = quaternion_normalize(q)
    q_conj = quaternion_conjugate(q_norm)
    p_rot = quaternion_multiply(quaternion_multiply(q_norm, p), q_conj)
    return p_rot[1:4]


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EE: 4D QUATERNION ROTATION ENGINE")
    print("=========================================================\n")

    # 1. Thu nghiem phep nhan Quaternion don vi (Identity)
    q_identity = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    # Xoay 90 do quanh truc Z: w = cos(45 deg) = 0.70710678, z = sin(45 deg) = 0.70710678
    q_rot_z90 = quaternion_from_axis_angle([0, 0, 1], np.pi / 2.0)
    q_res = quaternion_multiply(q_identity, q_rot_z90)

    print("1. KET QUA NHAN QUATERNION TRONG KHONG GIAN 4D:")
    print(f"   -> Quaternion sau khi xoay 90 do Z: {q_res}")
    assert np.isclose(q_res[0], np.sqrt(2) / 2.0, atol=1e-5)
    assert np.isclose(q_res[3], np.sqrt(2) / 2.0, atol=1e-5)

    # 2. Xoay vector toa do 3D thuc te cua Drone:
    # Vector ban dau huong theo truc X: v = [1.0, 0.0, 0.0]
    # Sau khi xoay 90 do quanh truc Z, vector phai huong theo truc Y: [0.0, 1.0, 0.0]
    v_initial = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    v_rotated = rotate_vector_by_quaternion(v_initial, q_rot_z90)

    print("\n2. XOAY VECTOR TOA DO 3D DRONE (v_rot = q * v * q*):")
    print(f"   -> Vector ban dau (Huong X) : {v_initial}")
    print(f"   -> Vector sau khi xoay 90 do: [{v_rotated[0]:.4f}, {v_rotated[1]:.4f}, {v_rotated[2]:.4f}]")
    assert np.isclose(v_rotated[0], 0.0, atol=1e-5)
    assert np.isclose(v_rotated[1], 1.0, atol=1e-5)
    assert np.isclose(v_rotated[2], 0.0, atol=1e-5)

    # 3. Kiem tra tinh chat chuan hoa (Unit norm)
    q_norm_check = np.linalg.norm(q_res)
    print(f"\n3. KIEM TRA DO DAI QUATERNION (UNIT NORM): {q_norm_check:.6f}")
    assert np.isclose(q_norm_check, 1.0, atol=1e-6)

    print("\n[THANH CONG] DA HOAN THANH BO KHONG GIAN XOAY 4D QUATERNION CHO DRONE!")
