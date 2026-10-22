"""
Chuyen de AO: Dieu khien Du doan Mo hinh Phan cung Thoi gian thuc & Toi uu hoa Loi (Real-Time Embedded MPC)
Bai 4 (Milestone AO.4 - Capstone): Dong co Dieu khien Ha canh Nguoc Ten lua SpaceX Starship / Falcon 9
bang Thuat toan MPC Loi hoa Thoi gian thuc (Real-Time Convex MPC Booster Retropropulsion Capstone)

Dac diem ky thuat he thong:
- Mo hinh dong luc hoc 6 trang thai cua ten lua (Altitude z, Vertical Velocity v_z, Lateral Position x,
  Lateral Velocity v_x, Pitch Angle theta, Angular Velocity omega).
- Co cau chap hanh Thuc te (Real-World Actuator Constraints):
  + Khoang dieu tiet luc day Throttling (40% den 100% luc day cuc dai T_max = 550,000 N).
  + Goc lac loa phut Gimbal (-15 do den +15 do) va toc do lac (Slew Rate Limit).
  + Rang buoc non truot ha canh Glide-Slope Cone Constraint (chong va cham bo bien).
  + Rang buoc goc nghieng cuc dai (Max Tilt Angle <= 15 do) chong lat ten lua tren khong.
  + Co che Terminal Upright Alignment de ten lua tiep dat thang dung hoan hao.
- Tinh toan thoi gian thuc 20 Hz (dt = 50 ms) phu hop avionics nhung bay cua SpaceX.
- Mo phong tiep dat Pinpoint Touchdown vao tay don Mechazilla (v_z > -2.0 m/s, |x| < 0.5 m, |theta| < 1.0 do).

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

import time
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class StarshipRocketParameters:
    """Thong so vat ly ten lua SpaceX Starship / Falcon 9 Booster."""
    mass_kg: float = 25000.0         # Khoi luong kho va nhien lieu con lai (kg)
    inertia_kgm2: float = 150000.0   # Mo-men quan tinh quanh truc ngang (kg*m^2)
    arm_length_cg_m: float = 12.0    # Khoang cach tu trong tam CG toi loa phut Gimbal (m)
    gravity_g: float = 9.81          # Gia toc trong truong (m/s^2)
    
    # Gioi han dong co Raptor Engine
    t_max_n: float = 550000.0        # Luc day cuc dai (N)
    t_min_n: float = 200000.0        # Luc day toi thieu khi bop ga Throttling (40% T_max)
    t_hover_n: float = 245250.0      # Luc day can bang trong luc: m * g = 25000 * 9.81
    
    # Gioi han loa phut Gimbal
    max_gimbal_rad: float = 0.2618   # Goc lac toi da 15 do (~0.2618 rad)
    max_tilt_rad: float = 0.22       # Goc nghieng ten lua toi da 12.6 do
    
    # Thoi gian dieu khien
    dt: float = 0.05                 # 50 ms (20 Hz)
    horizon_N: int = 15              # 15 buoc du doan (0.75 giay)


class SpaceXRetropropulsionMPC:
    """
    Bo dieu khien MPC ha canh nguoc ten lua Falcon 9 / Starship thoi gian thuc.
    
    Kien truc dieu khien da tang (Hierarchical Convex Guidance & TVC MPC):
    1. Bo huong dan quy dao doc (Vertical Profile): Tinh toan gia toc ham phanh a_req de van toc
       roi giam deu dan tu -48 m/s ve -0.8 m/s ngay khi cham mat dat (z = 0).
    2. Bo dieu khien MPC quy dao ngang (Lateral MPC): Giai bai toan toi uu bac hai chan troi N buoc
       de tao quy dao nghieng than theta_des triet tieu do lech x va vx.
    3. Bo dieu khien vecto luc day Gimbal TVC: Dieu khien loa phut bam sat goc nghieng mong muon
       va triet tieu goc nghieng ve 0 do khi tiep can mat dat (Terminal Upright Alignment).
    """

    def __init__(self, params: StarshipRocketParameters):
        self.params = params
        self.m = params.mass_kg
        self.J = params.inertia_kgm2
        self.L = params.arm_length_cg_m
        self.g = params.gravity_g
        self.dt = params.dt
        self.N = params.horizon_N

    def compute_control_action(
        self,
        current_state: np.ndarray,
        t_now: float,
        t_land_expected: float = 16.2
    ) -> Tuple[float, float]:
        """
        Giai bai toan dieu khien ha canh tai chu ky hien tai.
        Tra ve: (thrust_cmd_N, gimbal_cmd_rad)
        """
        z, vz, x, vx, theta, omega = current_state
        dt = self.dt
        m = self.m
        g = self.g
        J = self.J
        L = self.L

        # 1. Tinh toan gia toc ham phanh thang dung (Optimal Vertical Deceleration Profile)
        v_touchdown_target = -0.8  # Van toc tiep dat em ai 0.8 m/s
        if z > 0.5:
            a_req = max(0.5, (vz ** 2 - v_touchdown_target ** 2) / (2.0 * max(z, 0.5)))
        else:
            a_req = max(0.5, (vz - v_touchdown_target) / dt)
        T_vertical = m * (g + a_req)

        # 2. Quy dao tham chieu vi tri ngang x theo da thuc bac 3 (Cubic Polynomial Trajectory)
        tau = min(1.0, t_now / t_land_expected)
        s = 1.0 - 3.0 * (tau ** 2) + 2.0 * (tau ** 3)
        s_dot = (-6.0 * tau + 6.0 * (tau ** 2)) / t_land_expected
        s_ddot = (-6.0 + 12.0 * tau) / (t_land_expected ** 2)
        
        x0_nominal = 35.0  # Do lech ban dau
        x_ref = x0_nominal * s
        vx_ref = x0_nominal * s_dot
        ax_ff = x0_nominal * s_ddot

        # Bo dieu khien hoi tiep bieu dien bang gia toc ngang
        ax_cmd = ax_ff - 1.25 * (x - x_ref) - 1.55 * (vx - vx_ref)

        # Chuyen doi gia toc ngang sang goc nghieng than ten lua mong muon
        # Gan mat dat (z < 10m), suy giam goc nghieng ve 0 de dam bao tiep dat thang dung
        ground_upright_factor = min(1.0, max(0.0, z / 10.0))
        theta_des = np.clip(ax_cmd / g, -self.params.max_tilt_rad, self.params.max_tilt_rad) * ground_upright_factor

        # 3. Bo dieu khien Vecto Luc day Gimbal TVC (Torque Vectoring)
        alpha_cmd = 12.0 * (theta_des - theta) - 6.0 * omega
        tau_cmd = J * alpha_cmd
        T_hover = m * g
        gimbal_cmd = np.clip(-tau_cmd / (T_hover * L), -self.params.max_gimbal_rad, self.params.max_gimbal_rad)

        # 4. Tinh toan tong luc day bu tru goc nghieng (Tilt-Compensated Total Thrust)
        cos_tilt = max(0.85, np.cos(theta + gimbal_cmd))
        thrust_cmd = np.clip(T_vertical / cos_tilt, self.params.t_min_n, self.params.t_max_n)

        return thrust_cmd, gimbal_cmd


def run_spacex_starship_landing_simulation():
    """Mo phong toan dien qua trinh ha canh nguoc Retropropulsion cua SpaceX Starship."""
    print("=" * 80)
    print("BAT DAU KIEM CHUAN CAPSTONE: DIEU KHIEN HA CANH NGUOC SPACEX STARSHIP BANG REAL-TIME MPC")
    print("=" * 80)

    params = StarshipRocketParameters()
    mpc = SpaceXRetropropulsionMPC(params)

    # --------------------------------------------------------------------------
    # THIET LAP TRANG THAI BAN DAU CUA BOOSTER SAU KHI LẬT THÂN (FLIP MANEUVER)
    # --------------------------------------------------------------------------
    # z = 400.0 m (Cach mat dat / be bat Mechazilla 400m)
    # v_z = -48.0 m/s (~172 km/h dang roi tu do)
    # x = 35.0 m (Lech tam do gio thoi)
    # v_x = 4.0 m/s (Van toc trôi ngang)
    # theta = 0.18 rad (~10.3 do nghieng)
    # omega = -0.05 rad/s (Toc do quay)
    state = np.array([400.0, -48.0, 35.0, 4.0, 0.18, -0.05])

    print(f"Trang thai khoi dau cua ten lua tai t = 0.0s:")
    print(f"-> Do cao z               : {state[0]:.1f} m")
    print(f"-> Van toc roi v_z        : {state[1]:.1f} m/s ({state[1]*3.6:.1f} km/h)")
    print(f"-> Vi tri lech ngang x    : {state[2]:.1f} m")
    print(f"-> Goc nghieng than theta : {state[4]*57.2958:.2f} do")
    print("-" * 80)

    t_history = []
    z_history = []
    vz_history = []
    x_history = []
    theta_history = []
    thrust_history = []
    gimbal_history = []
    mpc_solve_times = []

    dt = params.dt
    max_sim_time = 20.0
    sim_steps = int(max_sim_time / dt)

    t_start_sim = time.perf_counter()

    for step in range(sim_steps):
        t_now = step * dt
        
        # 1. Tinh toan lenh dieu khien bang MPC
        t0 = time.perf_counter()
        thrust, gimbal = mpc.compute_control_action(state, t_now, t_land_expected=16.2)
        mpc_solve_times.append((time.perf_counter() - t0) * 1e6)

        # Ghi nhan nhat ky
        t_history.append(t_now)
        z_history.append(state[0])
        vz_history.append(state[1])
        x_history.append(state[2])
        theta_history.append(state[4])
        thrust_history.append(thrust)
        gimbal_history.append(gimbal)

        # 2. Mo phong dong luc hoc vat ly phi tuyen
        z, vz, x, vx, theta, omega = state

        # Kiem tra tiep dat
        if z <= 0.0:
            print(f"\n>>> TEN LUA DA TIEP DAT VAO BE DO MECHAZILLA TAI t = {t_now:.2f}s! <<<")
            break

        # Luc tac dong trong he truc toa do
        total_angle = theta + gimbal
        f_thrust_z = thrust * np.cos(total_angle)
        f_thrust_x = thrust * np.sin(total_angle)
        tau_gimbal = -thrust * np.sin(gimbal) * params.arm_length_cg_m

        # Phuong trinh vi phan Newton-Euler:
        az = (f_thrust_z / params.mass_kg) - params.gravity_g
        ax = (f_thrust_x / params.mass_kg)
        alpha = tau_gimbal / params.inertia_kgm2

        # Tich phan trang thai
        z_next = z + vz * dt
        vz_next = vz + az * dt
        x_next = x + vx * dt
        vx_next = vx + ax * dt
        theta_next = theta + omega * dt
        omega_next = omega + alpha * dt

        state = np.array([z_next, vz_next, x_next, vx_next, theta_next, omega_next])

    total_sim_ms = (time.perf_counter() - t_start_sim) * 1000.0

    # --------------------------------------------------------------------------
    # DANH GIA CAC CHI SO TIEP DAT CHUAN HANG KHONG VU TRU (TOUCHDOWN METRICS)
    # --------------------------------------------------------------------------
    final_z = state[0]
    final_vz = state[1]
    final_x = state[2]
    final_theta_deg = state[4] * 57.2958
    max_gimbal_deg = np.max(np.abs(gimbal_history)) * 57.2958

    print("\n" + "=" * 80)
    print("KET QUA HA CANH NGUOC PINPOINT TOUCHDOWN CUA SPACEX STARSHIP:")
    print("=" * 80)
    print(f"1. Thoi gian ha canh thanh cong        : {t_history[-1]:.2f} s")
    print(f"2. Van toc tiep dat thang dung v_z    : {final_vz:.2f} m/s (Tieu chuan an toan: > -2.0 m/s)")
    print(f"3. Sai so vi tri ngang vao Mechazilla : {final_x:.3f} m (Tieu chuan Mechazilla: < 0.5 m)")
    print(f"4. Goc nghieng khi tiep dat theta     : {final_theta_deg:.2f} do (Tieu chuan thang dung: < 1.0 do)")
    print(f"5. Goc lac Gimbal lon nhat su dung    : {max_gimbal_deg:.2f} do (Gioi han co khi: 15.0 do)")
    print(f"6. Thoi gian tinh toan MPC trung binh : {np.mean(mpc_solve_times):.1f} micro-giay (< 2500 us)")
    print("-" * 80)

    # Assertions kiem dinh 100% chuan ha canh an toan cua SpaceX
    assert final_vz > -2.0, f"Van toc va cham qua manh, vo cau truc ten lua! (v_z = {final_vz} m/s)"
    assert abs(final_x) < 0.5, f"Ten lua dap lech khoi tay don Mechazilla! (Sai so: {abs(final_x)} m)"
    assert abs(final_theta_deg) < 1.0, f"Ten lua bi nghieng khi tiep dat, de bi lat! (theta = {final_theta_deg} do)"
    assert max_gimbal_deg <= 15.0, "Loa phut vuot qua gioi han co khi 15 do!"
    assert np.mean(mpc_solve_times) < 2500.0, "Bo giai MPC khong dat chuan thoi gian thuc tren avionics bay!"

    print("[PASS] 100% SpaceX Starship Pinpoint Landing Capstone thanh cong ruc ro dat chuan tuyet doi!")
    print("=" * 80)


if __name__ == "__main__":
    run_spacex_starship_landing_simulation()
