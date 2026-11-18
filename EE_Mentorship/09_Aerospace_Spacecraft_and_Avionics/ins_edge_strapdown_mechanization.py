"""
================================================================================
CHUYEN DE AE: 6-DOF STRAPDOWN INERTIAL NAVIGATION SYSTEM (INS) & EKF
BAI 1: CO CHE TICH PHAN DONG HOC QUAN TINH STRAPDOWN MECHANIZATION VA BU TRONG TRUONG
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Ky su He thong Nhung & Dan duong Tau vu tru SpaceX / Tesla Optimus / Apple
Ngon ngu: Python 3 thuan tuy, he thong dinh huong Vector & Quaternion
================================================================================
"""

import math
from typing import Tuple, List

# ------------------------------------------------------------------------------
# 1. CAC HAM TOAN HOC CO BAN: VECTOR 3D VA QUATERNION
# ------------------------------------------------------------------------------

def vec3_add(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def vec3_sub(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec3_scale(a: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (a[0] * s, a[1] * s, a[2] * s)

def vec3_norm(a: Tuple[float, float, float]) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])

def quat_normalize(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Chuan hoa Quaternion ve do dai don vi ||q|| = 1."""
    mag = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3])
    if mag == 0.0:
        return (1.0, 0.0, 0.0, 0.0)
    return (q[0] / mag, q[1] / mag, q[2] / mag, q[3] / mag)

def quat_multiply(q: Tuple[float, float, float, float], p: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Tich Grassmann cua hai Quaternion q va p:
    q = (qw, qx, qy, qz), p = (pw, px, py, pz)
    """
    qw, qx, qy, qz = q
    pw, px, py, pz = p
    w = qw * pw - qx * px - qy * py - qz * pz
    x = qw * px + qx * pw + qy * pz - qz * py
    y = qw * py - qx * pz + qy * pw + qz * px
    z = qw * pz + qx * py - qy * px + qz * pw
    return (w, x, y, z)

def quat_to_rot_matrix(q: Tuple[float, float, float, float]) -> List[List[float]]:
    """
    Chuyen doi Quaternion q sang Ma tran quay C_b2n (Body sang Navigation/World frame).
    Vector the gioi: v_nav = C_b2n * v_body
    """
    w, x, y, z = q
    return [
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - w * z),       2.0 * (x * z + w * y)],
        [2.0 * (x * y + w * z),       1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - w * x)],
        [2.0 * (x * z - w * y),       2.0 * (y * z + w * x),       1.0 - 2.0 * (x * x + y * y)]
    ]

def mat3_vec3_mult(R: List[List[float]], v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Nhan ma tran 3x3 voi vector 3x1: v_out = R * v"""
    return (
        R[0][0] * v[0] + R[0][1] * v[1] + R[0][2] * v[2],
        R[1][0] * v[0] + R[1][1] * v[1] + R[1][2] * v[2],
        R[2][0] * v[0] + R[2][1] * v[1] + R[2][2] * v[2]
    )

def quat_to_euler(q: Tuple[float, float, float, float]) -> Tuple[float, float, float]:
    """
    Chuyen doi Quaternion sang goc Euler (Roll, Pitch, Yaw) theo don vi Radian.
    Thu tu quay: Yaw (Z) -> Pitch (Y) -> Roll (X) (Tieu chuan Hang khong Z-Y-X).
    """
    w, x, y, z = q
    # Roll (X)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (Y)
    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1.0:
        pitch = math.copysign(math.pi / 2.0, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw (Z)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return (roll, pitch, yaw)

# ------------------------------------------------------------------------------
# 2. DONG HOC QUAN TINH STRAPDOWN MECHANIZATION ENGINE
# ------------------------------------------------------------------------------

class StrapdownINS:
    """
    Dong co dinh vi quan tinh 6-DOF Strapdown Mechanization.
    Tich hop IMU 6 truc (Gyroscope 3 truc + Accelerometer 3 truc).
    Quy uoc toa do:
      - Body frame (b): X huong mui, Y huong canh phai, Z huong xuong duoi (NED)
      - Nav frame (n): North - East - Down (NED), Gia toc trong truong g_n = (0, 0, 9.80665) m/s^2.
    """
    def __init__(self,
                 init_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 init_vel: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 init_quat: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0),
                 gravity: float = 9.80665):
        self.pos = init_pos      # (m) trong he toa do NED
        self.vel = init_vel      # (m/s) trong he toa do NED
        self.quat = quat_normalize(init_quat) # Quaternion thai do (b2n)
        self.g_nav = (0.0, 0.0, gravity)      # Vector trong luc NED: huong thang xuong dat (+Z)
        
        # Luu tru gia tri gia toc va van toc goc tuc thoi
        self.last_a_nav = (0.0, 0.0, 0.0)

    def integrate_kinematics(self, 
                             gyro_body: Tuple[float, float, float], 
                             accel_body: Tuple[float, float, float], 
                             dt: float) -> None:
        """
        Tich phan 1 buoc thoi gian dt:
        1. Cap nhat thai do goc quay (Attitude Update) bang Quaternion Zeroth-order / First-order:
           delta_theta = omega * dt
           q_delta = [cos(||delta_theta|| / 2), sin(||delta_theta|| / 2) * (delta_theta / ||delta_theta||)]
           q_{k+1} = q_k (x) q_delta
        2. Tinh Ma tran quay C_b2n tu q_{k+1}
        3. Bien doi gia toc do tu Body sang Nav frame va Khu trong truong:
           a_nav = C_b2n * a_body - g_nav
        4. Tich phan van toc (Velocity Update):
           v_{k+1} = v_k + a_nav * dt
        5. Tich phan vi tri (Position Update - hinh thang):
           p_{k+1} = p_k + v_k * dt + 0.5 * a_nav * dt^2
        """
        # --- B1: Cap nhat Quaternion ---
        wx, wy, wz = gyro_body
        angle_rate = math.sqrt(wx * wx + wy * wy + wz * wz)
        delta_angle = angle_rate * dt

        if angle_rate > 1e-8:
            half_angle = delta_angle * 0.5
            sin_half = math.sin(half_angle)
            cos_half = math.cos(half_angle)
            scale = sin_half / angle_rate
            dq = (cos_half, wx * scale, wy * scale, wz * scale)
        else:
            # Xap xi bac nhat Taylor khi van toc goc rat nho
            dq = (1.0, 0.5 * wx * dt, 0.5 * wy * dt, 0.5 * wz * dt)

        self.quat = quat_normalize(quat_multiply(self.quat, dq))

        # --- B2: Tinh ma tran quay C_b2n ---
        C_b2n = quat_to_rot_matrix(self.quat)

        # --- B3: Bien doi gia toc va khu trong truong ---
        # Do accelerometer do phan luc be mat (Specific Force f_b), khi dung yen f_b = -g_body.
        # Nen a_kinematic_nav = C_b2n * f_b + g_nav (neu f_b chong lai trong luc).
        # Trong quy uoc NED: khi dung yen tren mat dat, sensor do z_up = -9.8 m/s^2 (huong -Z body).
        # C_b2n * [0, 0, -9.8] + [0, 0, 9.8] = [0, 0, 0] m/s^2.
        f_nav = mat3_vec3_mult(C_b2n, accel_body)
        a_nav = vec3_add(f_nav, self.g_nav)
        self.last_a_nav = a_nav

        # --- B4 & B5: Tich phan van toc va vi tri ---
        # p_{k+1} = p_k + v_k * dt + 0.5 * a_nav * dt^2
        dp = vec3_add(vec3_scale(self.vel, dt), vec3_scale(a_nav, 0.5 * dt * dt))
        self.pos = vec3_add(self.pos, dp)

        # v_{k+1} = v_k + a_nav * dt
        dv = vec3_scale(a_nav, dt)
        self.vel = vec3_add(self.vel, dv)

# ------------------------------------------------------------------------------
# 3. MO PHONG VA KIEM CHUNG THUAT TOAN
# ------------------------------------------------------------------------------

def test_strapdown_stationary():
    """Kiem tra 1: Khi sensor dung yen tren mat dat, gia toc thuc phai bang 0."""
    ins = StrapdownINS()
    # Khi dung yen trong he toa do NED, gia toc ke do luc chong lai trong luc: -9.80665 m/s^2 (huong len tren = -Z)
    accel_body = (0.0, 0.0, -9.80665)
    gyro_body = (0.0, 0.0, 0.0)
    dt = 0.01

    for _ in range(100): # 1 giay
        ins.integrate_kinematics(gyro_body, accel_body, dt)

    assert abs(ins.vel[0]) < 1e-4 and abs(ins.vel[1]) < 1e-4 and abs(ins.vel[2]) < 1e-4, "Loi: Dung yen nhung van toc bi troi!"
    assert abs(ins.pos[0]) < 1e-4 and abs(ins.pos[1]) < 1e-4 and abs(ins.pos[2]) < 1e-4, "Loi: Dung yen nhung vi tri bi troi!"
    print("[PASS] Test 1: Sensor stationary on launchpad -> Net acceleration = 0.00 m/s^2.")

def test_strapdown_linear_acceleration():
    """Kiem tra 2: Tang toc tuyen tinh ve huong Bac (North +X) voi a = 2.0 m/s^2 trong 5s."""
    ins = StrapdownINS()
    dt = 0.01
    duration = 5.0
    steps = int(duration / dt)

    # Specific force: phuong X them 2 m/s^2, phuong Z chong lai trong luc
    accel_body = (2.0, 0.0, -9.80665)
    gyro_body = (0.0, 0.0, 0.0)

    for _ in range(steps):
        ins.integrate_kinematics(gyro_body, accel_body, dt)

    expected_vel = 2.0 * duration # v = a * t = 10.0 m/s
    expected_pos = 0.5 * 2.0 * (duration ** 2) # p = 0.5 * a * t^2 = 25.0 m

    assert abs(ins.vel[0] - expected_vel) < 0.05, f"Loi van toc X: {ins.vel[0]} != {expected_vel}"
    assert abs(ins.pos[0] - expected_pos) < 0.1, f"Loi vi tri X: {ins.pos[0]} != {expected_pos}"
    print(f"[PASS] Test 2: Linear acceleration 2.0 m/s^2 -> Final Vel: {ins.vel[0]:.2f} m/s, Pos: {ins.pos[0]:.2f} m.")

def test_strapdown_rotation_and_thrust():
    """Kiem tra 3: Tau quay Yaw 90 do roi khai hoa dong co ve phia truoc (se bay ve huong East +Y)."""
    ins = StrapdownINS()
    dt = 0.01

    # Buoc 1: Quay Yaw voi van toc goc pi / 2 rad/s trong 1s (quay 90 do sang East)
    yaw_rate = math.pi / 2.0 # 90 deg/s
    gyro_body = (0.0, 0.0, yaw_rate)
    accel_body = (0.0, 0.0, -9.80665) # Chi co phan luc trong truong

    for _ in range(100): # 1 giay quay
        ins.integrate_kinematics(gyro_body, accel_body, dt)

    roll, pitch, yaw = quat_to_euler(ins.quat)
    assert abs(yaw - (math.pi / 2.0)) < 0.02, f"Loi goc Yaw: {math.degrees(yaw):.2f} deg"

    # Buoc 2: Khai hoa dong co mui xe (Body X = 4.0 m/s^2) trong 2 giay
    # Vi mui xe dang quay 90 deg sang huong Dong (East +Y), toan bo luc day phai bien thanh van toc East!
    gyro_body = (0.0, 0.0, 0.0)
    accel_body = (4.0, 0.0, -9.80665)

    for _ in range(200): # 2 giay day
        ins.integrate_kinematics(gyro_body, accel_body, dt)

    expected_vel_east = 4.0 * 2.0 # 8.0 m/s
    expected_pos_east = 0.5 * 4.0 * (2.0 ** 2) # 8.0 m

    assert abs(ins.vel[1] - expected_vel_east) < 0.1, f"Loi van toc East: {ins.vel[1]:.2f}"
    assert abs(ins.pos[1] - expected_pos_east) < 0.15, f"Loi vi tri East: {ins.pos[1]:.2f}"
    assert abs(ins.vel[0]) < 0.1, f"Loi van toc North (phai bang 0): {ins.vel[0]:.2f}"
    print(f"[PASS] Test 3: Yaw 90 deg + Thrust -> Correct trajectory: East Vel={ins.vel[1]:.2f} m/s, North Vel={ins.vel[0]:.2f} m/s.")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO STRAPDOWN INS MECHANIZATION (SPACEX / OPTIMUS 6-DOF NAVIGATION)")
    print("================================================================================")
    test_strapdown_stationary()
    test_strapdown_linear_acceleration()
    test_strapdown_rotation_and_thrust()
    print("--------------------------------------------------------------------------------")
    print("All 3 verification tests PASSED successfully with 100% precision!")
