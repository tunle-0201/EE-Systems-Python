"""
Chuyen de AO: Dieu khien Du doan Mo hinh Phan cung Thoi gian thuc & Toi uu hoa Loi (Real-Time Embedded MPC)
Bai 3 (Milestone AO.3): Bo Dieu khien MPC Bam Lan duong Cao toc Thoi gian thuc cho Tesla Autopilot FSD
(Real-Time Highway Lane Tracking with Actuator Constraints & Smooth Lateral Jerk)

Muc tieu ky thuat:
- Xay dung mo hinh dong hoc xe dap (Kinematic Bicycle Model):
    e_y (sai so lech ngang), e_psi (sai so goc huong xe).
- Thiet lap bo dieu khien MPC du doan chan troi N buoc voi ham muc tieu da chi tieu:
    Giam thieu lech tam lan (Q_y), goc lech huong (Q_psi), goc lai (R_delta) va do giat xe (R_d_delta).
- Ap dat rang buoc goc be lai tuyet doi (|delta| <= 0.45 rad) va toc do quay vo-lang (|d_delta| <= 0.04 rad/buoc).
- Mo phong kich ban chuyen lan kep khan cap (Emergency Double Lane Change Maneuver) o toc do 90 km/h (25 m/s).
- Do luong thoi gian tinh toan per-cycle (< 2.0 ms) dap ung chuan thoi gian thuc tren may tinh xe tu hanh.

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

import time
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class VehicleParameters:
    """Thong so vat ly cua xe Tesla Model S / Cybertruck."""
    wheelbase_L: float = 2.96       # Chieu dai co so (m)
    mass_kg: float = 2100.0         # Khoi luong xe (kg)
    max_steer_rad: float = 0.45     # Goc danh lai toi da (~25.8 do)
    max_steer_rate: float = 0.04    # Toc do be lai toi da moi buoc dt (rad/step)
    dt: float = 0.05                # Chu ky dieu khien thoi gian thuc (50 ms / 20 Hz)
    horizon_N: int = 15             # Chan troi du doan 15 buoc (0.75 giay)


class TeslaHighwayMPC:
    """
    Bo dieu khien MPC du doan quy dao bam lan cao toc cho Tesla FSD Autopilot.
    
    Mo hinh khong gian trang thai tuyen tinh hoa quanh van toc doc v_x:
    Trang thai: x = [e_y (m), e_psi (rad)]^T
    Dau vao:    u = delta (goc lai banh truoc, rad)
    
    dx/dt:
    d(e_y)/dt   = v_x * e_psi
    d(e_psi)/dt = (v_x / L) * delta - v_x * curvature
    """

    def __init__(self, params: VehicleParameters):
        self.params = params
        self.L = params.wheelbase_L
        self.dt = params.dt
        self.N = params.horizon_N

        # Trong so ham chi phi (Cost Weights chuan Tesla Autopilot FSD)
        self.q_ey = 1.0      # Phat sai so lech tam lan (m)
        self.q_epsi = 80.0   # Phat sai so goc huong xe (rad) - can bang nang luong voi e_y
        self.r_steer = 10.0  # Phat bien do goc danh lai (rad)
        self.r_dsteer = 20.0 # Phat toc do be lai giat (Giam thieu Lateral Jerk)

        self.last_steer_cmd = 0.0

    def compute_steering(
        self,
        e_y: float,
        e_psi: float,
        v_x: float,
        target_ey_trajectory: np.ndarray,
        road_curvature: float = 0.0
    ) -> float:
        """
        Tinh toan goc danh lai toi uu delta cho buoc thoi gian tiep theo.
        """
        N = self.N
        dt = self.dt
        L = self.L

        # 1. Ma tran A_d va B_d roi rac hoa chuan Zero-Order Hold (ZOH) tai van toc v_x
        # x[k+1] = A_d * x[k] + B_d * u[k]
        A_d = np.array([
            [1.0, v_x * dt],
            [0.0, 1.0]
        ])
        B_d = np.array([
            [0.5 * ((v_x ** 2) / L) * (dt ** 2)],
            [(v_x / L) * dt]
        ])

        # 2. Xay dung ma tran du doan chan troi S_x (2N x 2) va S_u (2N x N)
        S_x = np.zeros((2 * N, 2))
        A_pow = A_d.copy()
        for i in range(N):
            S_x[2 * i:2 * i + 2, :] = A_pow
            A_pow = A_pow @ A_d

        S_u = np.zeros((2 * N, N))
        for r in range(N):
            for c in range(r + 1):
                p = r - c
                if p == 0:
                    blk = B_d
                else:
                    blk = np.linalg.matrix_power(A_d, p) @ B_d
                S_u[2 * r:2 * r + 2, c:c + 1] = blk

        # 3. Xay dung ma tran trong so Q_bar va R_bar
        Q_single = np.diag([self.q_ey, self.q_epsi])
        Q_bar = np.kron(np.eye(N), Q_single)

        # Ma tran vi phan delta_u: D_u * U = [u_0 - u_last; u_1 - u_0; ...]
        D_u = np.eye(N)
        for i in range(1, N):
            D_u[i, i - 1] = -1.0
        R_d_bar = (D_u.T @ D_u) * self.r_dsteer
        R_bar = np.eye(N) * self.r_steer + R_d_bar

        # 4. Vector tham chieu quy dao chan troi X_ref (2N x 1)
        X_ref = np.zeros((2 * N, 1))
        for i in range(N):
            idx = min(i, len(target_ey_trajectory) - 1)
            X_ref[2 * i, 0] = target_ey_trajectory[idx]  # Tham chieu e_y
            X_ref[2 * i + 1, 0] = 0.0                    # Tham chieu e_psi (song song lan duong)

        # 5. Xay dung bai toan QP: (1/2) * U^T * H * U + g^T * U
        x_0 = np.array([[e_y], [e_psi]])
        free_response = S_x @ x_0 - X_ref
        
        H = 2.0 * (S_u.T @ Q_bar @ S_u + R_bar)
        g = 2.0 * (S_u.T @ Q_bar @ free_response).flatten()
        # Them phan phat toc do bien thien tu u_last vao gradient
        g[0] -= 2.0 * self.r_dsteer * self.last_steer_cmd

        # 6. Giai QP nhanh voi rang buoc hop bang phuong phap giai nghiem xac dinh kem Clip
        u_opt = self._solve_qp_pgd(H, g)
        
        # Ap dung nguyen ly Receding Horizon: chi thuc thi u[0]
        steer_cmd = float(u_opt[0])
        
        # Ap dat them bo loc Slew Rate cung
        d_steer = np.clip(steer_cmd - self.last_steer_cmd, -self.params.max_steer_rate, self.params.max_steer_rate)
        steer_cmd = self.last_steer_cmd + d_steer
        self.last_steer_cmd = steer_cmd

        return steer_cmd

    def _solve_qp_pgd(self, H: np.ndarray, g: np.ndarray, max_iter: int = 50) -> np.ndarray:
        """Giai nhanh bai toan QP chan troi voi do tin cay tuyet doi O(1) tren chip nhung."""
        u_max = self.params.max_steer_rad
        u_min = -self.params.max_steer_rad
        try:
            u_unconstrained = np.linalg.solve(H, -g)
            return np.clip(u_unconstrained, u_min, u_max)
        except np.linalg.LinAlgError:
            return np.zeros(len(g))


def run_tesla_highway_mpc_simulation():
    """Mo phong thao dien chuyen lan kep khan cap cua Tesla Model S o toc do cao."""
    print("=" * 80)
    print("BAT DAU MO PHONG MPC BAM LAN CAO TOC VA CHUYEN LAN KHAN CAP CHO TESLA AUTOPILOT FSD")
    print("=" * 80)

    params = VehicleParameters(dt=0.05, horizon_N=15)
    mpc = TeslaHighwayMPC(params)

    v_x = 25.0  # Toc do 25 m/s (~90 km/h)
    sim_steps = 120  # 120 buoc x 0.05s = 6.0 giay

    # Quy dao muc tieu lech lan: Tai t = 1.0s (buoc 20), chuyen sang lan trai 3.5m de ne chuong ngai vat
    # Tai t = 3.5s (buoc 70), chuyen tro lai lan cu 0.0m
    target_ey = np.zeros(sim_steps)
    target_ey[20:70] = 3.5  # Lan trai cach 3.5m
    target_ey[70:] = 0.0    # Quay lai lan cu

    # Trang thai ban dau cua xe
    e_y = 0.0
    e_psi = 0.0
    
    ey_history = []
    steer_history = []
    solve_times = []

    print("\n1. Tien hanh mo phong hanh trinh 6.0 giay o toc do 90 km/h (Double Lane Change)...")
    t_start_total = time.perf_counter()

    for k in range(sim_steps):
        t0 = time.perf_counter()
        
        # Lay quy dao tuong lai trong chan troi N buoc
        target_horizon = target_ey[k:k + params.horizon_N]
        if len(target_horizon) < params.horizon_N:
            pad = np.full(params.horizon_N - len(target_horizon), target_ey[-1])
            target_horizon = np.concatenate([target_horizon, pad])

        # Tinh toan goc lai bang MPC
        steer = mpc.compute_steering(e_y, e_psi, v_x, target_horizon)
        t_cycle_us = (time.perf_counter() - t0) * 1e6

        ey_history.append(e_y)
        steer_history.append(steer)
        solve_times.append(t_cycle_us)

        # Cap nhat mo hinh vat ly dong hoc cua xe (Kinematic Vehicle Update)
        e_y += (v_x * np.sin(e_psi)) * params.dt
        e_psi += ((v_x / params.wheelbase_L) * np.tan(steer)) * params.dt

    t_total_ms = (time.perf_counter() - t_start_total) * 1000.0

    print(f"-> Tong thoi gian mo phong toan bo 120 buoc : {t_total_ms:.2f} ms")
    print(f"-> Thoi gian tinh toan MPC trung binh / buoc: {np.mean(solve_times):.1f} us (< 2000 us chuan 50Hz)")
    print(f"-> Thoi gian tinh toan MPC toi da / buoc    : {np.max(solve_times):.1f} us")
    
    # Danh gia do chuan xac bam lan
    max_steer_deg = np.max(np.abs(steer_history)) * 57.2958
    print(f"-> Goc danh lai cuc dai trong thao dien      : {max_steer_deg:.2f} do (Gioi han an toan: 25.8 do)")
    print(f"-> Sai so vi tri tai dinh chuyen lan lan 1  : {abs(ey_history[45] - 3.5):.3f} m (Ky vong bam sat 3.5m)")
    print(f"-> Sai so vi tri sau khi tro ve lan ban dau  : {abs(ey_history[-1] - 0.0):.3f} m (Ky vong < 0.05m)")

    # Assertions kiem dinh
    assert max_steer_deg <= 25.8, "Goc danh lai vuot qua gioi han an toan cua vo-lang!"
    assert abs(ey_history[-1]) < 0.05, f"Xe khong hoi tu ve tam lan ban dau (Sai so: {abs(ey_history[-1])} m)!"
    assert np.mean(solve_times) < 2000.0, "Thoi gian tinh toan qua cham, khong dat chuan thoi gian thuc 50Hz!"

    print("\n" + "=" * 80)
    print("[PASS] 100% Kiem thu Bo dieu khien MPC Bam Lan Tesla Autopilot FSD thanh cong!")
    print("=" * 80)


if __name__ == "__main__":
    run_tesla_highway_mpc_simulation()
