"""
================================================================================
CHUYEN DE AE: 6-DOF STRAPDOWN INERTIAL NAVIGATION SYSTEM (INS) & EKF
BAI 3: BO LOC KALMAN MO RONG ES-EKF 15 TRANG THAI DUNG HOP IMU VA GNSS
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: He thong dan duong SpaceX Falcon 9 / Starship / FSD Autonomous Driving
Ngon ngu: Python 3 thuan tuy, ma tran va vector tu che tinh gon
================================================================================
"""

import math
import random
from typing import Tuple, List, Dict

# Import cac ham toan hoc va module SINS tu Bai 1
from ins_edge_strapdown_mechanization import (
    StrapdownINS, quat_normalize, quat_multiply, quat_to_rot_matrix,
    mat3_vec3_mult, vec3_add, vec3_sub, vec3_scale, vec3_norm
)

# ------------------------------------------------------------------------------
# 1. CAC HAM MA TRAN TOAN HOC TU CHE TINH GON (3x3 VA 15x15)
# ------------------------------------------------------------------------------

def skew_symmetric(v: Tuple[float, float, float]) -> List[List[float]]:
    """Ma tran phan doi xung 3x3 tu vector 3x1 (Skew-Symmetric Cross Product Matrix)."""
    return [
        [0.0, -v[2], v[1]],
        [v[2], 0.0, -v[0]],
        [-v[1], v[0], 0.0]
    ]

def mat_zeros(rows: int, cols: int) -> List[List[float]]:
    return [[0.0 for _ in range(cols)] for _ in range(rows)]

def mat_identity(n: int) -> List[List[float]]:
    M = mat_zeros(n, n)
    for i in range(n):
        M[i][i] = 1.0
    return M

def mat_mult(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    """Nhan hai ma tran A (rA x cA) va B (cA x cB)."""
    rA = len(A)
    cA = len(A[0])
    cB = len(B[0])
    C = mat_zeros(rA, cB)
    for i in range(rA):
        for k in range(cA):
            aik = A[i][k]
            if aik != 0.0:
                for j in range(cB):
                    C[i][j] += aik * B[k][j]
    return C

def mat_transpose(A: List[List[float]]) -> List[List[float]]:
    r = len(A)
    c = len(A[0])
    AT = mat_zeros(c, r)
    for i in range(r):
        for j in range(c):
            AT[j][i] = A[i][j]
    return AT

def mat_add(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    r = len(A)
    c = len(A[0])
    return [[A[i][j] + B[i][j] for j in range(c)] for i in range(r)]

def mat3_inv(M: List[List[float]]) -> List[List[float]]:
    """Nghich dao ma tran 3x3 thuan tuy."""
    det = (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
         - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
         + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    if abs(det) < 1e-12:
        return mat_identity(3)
    invdet = 1.0 / det
    return [
        [ (M[1][1] * M[2][2] - M[1][2] * M[2][1]) * invdet,
         -(M[0][1] * M[2][2] - M[0][2] * M[2][1]) * invdet,
          (M[0][1] * M[1][2] - M[0][2] * M[1][1]) * invdet],
        [-(M[1][0] * M[2][2] - M[1][2] * M[2][0]) * invdet,
          (M[0][0] * M[2][2] - M[0][2] * M[2][0]) * invdet,
         -(M[0][0] * M[1][2] - M[0][2] * M[1][0]) * invdet],
        [ (M[1][0] * M[2][1] - M[1][1] * M[2][0]) * invdet,
         -(M[0][0] * M[2][1] - M[0][1] * M[2][0]) * invdet,
          (M[0][0] * M[1][1] - M[0][1] * M[1][0]) * invdet]
    ]

# ------------------------------------------------------------------------------
# 2. 15-STATE ERROR-STATE EXTENDED KALMAN FILTER (ES-EKF)
# ------------------------------------------------------------------------------

class ErrorStateEKF:
    """
    15-State Error-State EKF (ES-EKF) dung hop IMU (tan so cao) va GNSS (tan so thap).
    Vector sai so delta_x (15 chieu):
      - 0..2  : delta_p (Sai so vi tri North, East, Down)
      - 3..5  : delta_v (Sai so van toc Vn, Ve, Vd)
      - 6..8  : delta_theta (Sai so goc quay quanh truc Roll, Pitch, Yaw)
      - 9..11 : delta_ba (Sai so bias gia toc ke bax, bay, baz)
      - 12..14: delta_bg (Sai so bias con quay hoi chuyen bgx, bgy, bgz)
    """
    def __init__(self,
                 init_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 init_vel: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 init_quat: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)):
        # Trang thai danh dinh (Nominal State SINS)
        self.ins = StrapdownINS(init_pos=init_pos, init_vel=init_vel, init_quat=init_quat)
        self.accel_bias = (0.0, 0.0, 0.0) # Bias gia toc ke uoc luong
        self.gyro_bias = (0.0, 0.0, 0.0)  # Bias con quay hoi chuyen uoc luong

        # Ma tran hiep phuong sai sai so P (15x15)
        self.P = mat_zeros(15, 15)
        # Khoi tao phuong sai ban dau
        for i in range(3):
            self.P[i][i] = 1.0       # Sai so vi tri ban dau (1 m^2)
            self.P[i+3][i+3] = 0.1   # Sai so van toc ban dau (0.1 (m/s)^2)
            self.P[i+6][i+6] = 0.01  # Sai so goc ban dau (0.01 rad^2)
            self.P[i+9][i+9] = 0.01  # Sai so bias accel ban dau
            self.P[i+12][i+12] = 0.001 # Sai so bias gyro ban dau

        # Ma tran nhieu tien trinh Q_diag (15 gia tri tren duong cheo)
        self.Q_diag = [
            0.001, 0.001, 0.001,     # Nhiễu vị trí
            0.05, 0.05, 0.05,        # Nhiễu gia tốc đo
            0.002, 0.002, 0.002,     # Nhiễu con quay đo
            0.0001, 0.0001, 0.0001,  # Tản mạn bias accel (Random Walk)
            0.00001, 0.00001, 0.00001# Tản mạn bias gyro (Random Walk)
        ]

    def predict(self,
                accel_raw: Tuple[float, float, float],
                gyro_raw: Tuple[float, float, float],
                dt: float) -> None:
        """
        Buoc 1: Du bao (Time Update / Prediction) o tan so IMU cao:
        - Bu bias IMU vao phep do tho
        - Tich phan danh dinh SINS Mechanization
        - Tinh ma tran chuyen trang thai sai so F_k (15x15) va cap nhat P = F * P * F^T + Q*dt
        """
        # Bù bias đã ước lượng
        accel_comp = vec3_sub(accel_raw, self.accel_bias)
        gyro_comp = vec3_sub(gyro_raw, self.gyro_bias)

        # Tích phân nominal SINS
        self.ins.integrate_kinematics(gyro_comp, accel_comp, dt)

        # Xây dựng ma trận chuyển trạng thái sai số F (15x15)
        # F = I + F_cont * dt
        F = mat_identity(15)
        R_b2n = quat_to_rot_matrix(self.ins.quat)

        # 1. d(delta_p)/dt = delta_v -> F[0..2, 3..5] = I * dt
        for i in range(3):
            F[i][i+3] = dt

        # 2. d(delta_v)/dt = - [a_nav]x * delta_theta - R_b2n * delta_ba
        a_skew = skew_symmetric(self.ins.last_a_nav)
        for i in range(3):
            for j in range(3):
                # - [a_nav]x * dt
                F[i+3][j+6] = -a_skew[i][j] * dt
                # - R_b2n * dt (Do a_true = a_meas - b_a nen vi phan theo b_a mang dau am)
                F[i+3][j+9] = -R_b2n[i][j] * dt

        # 3. d(delta_theta)/dt = - [omega]x * delta_theta - R_b2n * delta_bg
        w_skew = skew_symmetric(gyro_comp)
        for i in range(3):
            for j in range(3):
                F[i+6][j+6] += -w_skew[i][j] * dt
                # - R_b2n * dt
                F[i+6][j+12] = -R_b2n[i][j] * dt

        # Cập nhật hiệp phương sai sai số: P = F * P * F^T + Q * dt
        FP = mat_mult(F, self.P)
        FT = mat_transpose(F)
        self.P = mat_mult(FP, FT)

        # Cộng ma trận nhiễu tiến trình Q * dt
        for i in range(15):
            self.P[i][i] += self.Q_diag[i] * dt

    def update_gnss_position(self,
                            gnss_pos: Tuple[float, float, float],
                            gnss_noise_std: float = 0.5) -> None:
        """
        Buoc 2: Hieu chinh do dac GNSS (Measurement Update) o tan so thap:
        - Sai so do dac vi tri: z = gnss_pos - ins_pos (3x1)
        - Ma tran do dac H (3x15): H = [I_3x3, 0_3x12]
        - Kalman Gain: K = P * H^T * (H * P * H^T + R)^(-1) (15x3)
        - Tinh vector sai so: delta_x = K * z (15x1)
        - Reset sai so: tiem vao Nominal state va reset delta_x = 0
        - Cap nhat hiep phuong sai: P = (I - K * H) * P
        """
        z = vec3_sub(gnss_pos, self.ins.pos) # Sai số vị trí quan sát (3x1)

        # Tính ma trận S = H * P * H^T + R (3x3)
        # Vi H chi la 3 hang dau cua I, H * P * H^T chinh la khoi P[0..3, 0..3]
        R_cov = gnss_noise_std * gnss_noise_std
        S = mat_zeros(3, 3)
        for i in range(3):
            for j in range(3):
                S[i][j] = self.P[i][j]
            S[i][i] += R_cov

        S_inv = mat3_inv(S)

        # Tính Kalman Gain K = P * H^T * S_inv (15x3)
        # P * H^T chinh la 3 cot dau tien cua ma tran P (15x3)
        K = mat_zeros(15, 3)
        for i in range(15):
            for j in range(3):
                # K[i][j] = sum_k (P[i][k] * S_inv[k][j]) voi k tu 0 den 2
                val = 0.0
                for k in range(3):
                    val += self.P[i][k] * S_inv[k][j]
                K[i][j] = val

        # Tính vector sai số delta_x = K * z (15x1)
        delta_x = [0.0] * 15
        for i in range(15):
            delta_x[i] = K[i][0] * z[0] + K[i][1] * z[1] + K[i][2] * z[2]

        # --- TIEM SAI SO VAO NOMINAL STATE (ERROR INJECTION) ---
        # 1. Vi tri: p = p + delta_p
        self.ins.pos = (
            self.ins.pos[0] + delta_x[0],
            self.ins.pos[1] + delta_x[1],
            self.ins.pos[2] + delta_x[2]
        )

        # 2. Van toc: v = v + delta_v
        self.ins.vel = (
            self.ins.vel[0] + delta_x[3],
            self.ins.vel[1] + delta_x[4],
            self.ins.vel[2] + delta_x[5]
        )

        # 3. Thai do goc quay (Quaternion Injection): q = q (x) [1, 0.5 * delta_theta]
        dtheta = (delta_x[6], delta_x[7], delta_x[8])
        dq = (1.0, 0.5 * dtheta[0], 0.5 * dtheta[1], 0.5 * dtheta[2])
        self.ins.quat = quat_normalize(quat_multiply(self.ins.quat, dq))

        # 4. Bias gia toc ke: ba = ba + delta_ba
        self.accel_bias = (
            self.accel_bias[0] + delta_x[9],
            self.accel_bias[1] + delta_x[10],
            self.accel_bias[2] + delta_x[11]
        )

        # 5. Bias gyro: bg = bg + delta_bg
        self.gyro_bias = (
            self.gyro_bias[0] + delta_x[12],
            self.gyro_bias[1] + delta_x[13],
            self.gyro_bias[2] + delta_x[14]
        )

        # --- CAP NHAT HIEP PHUONG SAI P = (I - K * H) * P (Joseph Form tinh gon) ---
        # K * H co kich thuoc 15x15, nhung vi H chi co 3 cot dau, K*H[i][j] = K[i][j] khi j < 3, nguoc lai = 0.
        KH = mat_zeros(15, 15)
        for i in range(15):
            for j in range(3):
                KH[i][j] = K[i][j]

        I_minus_KH = mat_identity(15)
        for i in range(15):
            for j in range(15):
                I_minus_KH[i][j] -= KH[i][j]

        self.P = mat_mult(I_minus_KH, self.P)

# ------------------------------------------------------------------------------
# 3. MO PHONG DUNG HOP DU LIEU IMU + GNSS
# ------------------------------------------------------------------------------

def test_es_ekf_fusion():
    """
    Kiem thu EKF dung hop: Tau vu tru bay ve phia truoc voi van toc 10 m/s trong 10 giay.
    IMU chay o 100 Hz (dt = 0.01s) co bias gia toc b_x = 0.15 m/s^2 va nhieu trang.
    GNSS chay o 5 Hz (dt = 0.2s) co nhieu do dac Gaussian (sigma = 0.4m).
    """
    random.seed(42) # Co dinh seed de ket qua lap lai nhat quan
    ekf = ErrorStateEKF()

    true_bias_x = 0.15 # Bias phan cung cua gia toc ke truc X (m/s^2)
    dt_imu = 0.01      # 100 Hz
    dt_gnss = 0.20     # 5 Hz
    total_time = 10.0  # 10 giay
    steps = int(total_time / dt_imu)

    # Chuyen dong thuc: Di chuyen deu voi van toc v_x = 10.0 m/s ve huong Bac
    # Specific force: vi van toc khong doi, a_kinematic = 0, sensor chi chiu phan luc trong truong
    true_pos_x = 0.0
    true_vel_x = 10.0
    ekf.ins.vel = (10.0, 0.0, 0.0) # Van toc khoi dau

    gnss_counter = 0
    gnss_updates_count = 0

    print("Bat dau mo phong EKF Dung hop IMU 100 Hz + GNSS 5 Hz trong 10 giay...")

    for step in range(steps):
        t = step * dt_imu
        true_pos_x = true_vel_x * t

        # IMU bi anh huong boi nhiễu trắng và bias phần cứng b_x = 0.15 m/s^2
        noise_accel_x = random.gauss(0.0, 0.05)
        accel_raw = (0.0 + true_bias_x + noise_accel_x, 0.0, -9.80665)
        gyro_raw = (0.0, 0.0, 0.0)

        # 1. Du bao bang IMU o 100 Hz
        ekf.predict(accel_raw, gyro_raw, dt_imu)

        # 2. Cap nhat GNSS o 5 Hz (moi 20 buoc IMU)
        gnss_counter += 1
        if gnss_counter >= int(dt_gnss / dt_imu):
            gnss_counter = 0
            # GNSS do duoc vi tri that cong voi nhieu do dac sigma = 0.4 m
            noise_gnss = random.gauss(0.0, 0.4)
            gnss_meas = (true_pos_x + noise_gnss, 0.0, 0.0)
            ekf.update_gnss_position(gnss_meas, gnss_noise_std=0.4)
            gnss_updates_count += 1

    final_est_pos_x = ekf.ins.pos[0]
    final_error_pos = abs(final_est_pos_x - true_pos_x)
    final_bias_x_est = ekf.accel_bias[0]

    print("--------------------------------------------------------------------------------")
    print(f"KET QUA SAU 10 GIAY DUNG HOP ES-EKF:")
    print(f"-> Vi tri thuc te        : {true_pos_x:7.3f} m")
    print(f"-> Vi tri uoc luong EKF   : {final_est_pos_x:7.3f} m (Sai so vi tri = {final_error_pos:.3f} m)")
    print(f"-> Bias that b_x         : {true_bias_x:7.3f} m/s^2")
    print(f"-> Bias EKF uoc luong hoc: {final_bias_x_est:7.3f} m/s^2")
    print(f"-> Tong so lan cap nhat GNSS: {gnss_updates_count} lan.")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Sai so vi tri phai duoc kiem soat cuc ky nho (< 0.6 m mac du IMU bi bias va tich phan 10s)
    assert final_error_pos < 0.6, f"Loi: Sai so vi tri vuot nguong: {final_error_pos} m"
    # 2. Bo loc Kalman phai hoc va uoc luong duoc bias gia toc ke b_x (sai lech < 0.06 m/s^2)
    assert abs(final_bias_x_est - true_bias_x) < 0.06, f"Loi: EKF khong uoc luong duoc bias: {final_bias_x_est}"
    print("[PASS] Test ES-EKF: Dung hop hoan hao du lieu IMU 100 Hz va GNSS 5 Hz, uoc luong chinh xac bias!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO 15-STATE ERROR-STATE EXTENDED KALMAN FILTER (ES-EKF)")
    print("================================================================================")
    test_es_ekf_fusion()
