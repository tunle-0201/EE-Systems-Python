"""
================================================================================
          MODULE AA: ROBOTIC KINODYNAMICS & AUTONOMOUS MOTION PLANNING
          MILESTONE AA.2: DYNAMIC WINDOW APPROACH (DWA) OBSTACLE AVOIDANCE
================================================================================

TAI SAO THUAT TOAN DWA LA TIEU CHUAN TRONG NE TRAP VAT CAN THOI GIAN THUC?
- Khi xe tu hanh hoac robot chuyen dong o toc do cao, no co quan tinh dong luc hoc.
- Khong the re dot ngot hoac dung ngay lap tuc ma phai tuan thu gioi han gia toc
  cua dong co va he thong phanh.
- Dynamic Window Approach (DWA) lay mau truc tiep trong khong gian van toc (v, omega)
  kha thi trong cua so thoi gian ngan dt, du doan quy dao tuong lai, tinh toan
  khoang cach an toan toi vat can LiDAR va chon ra quy dao toi uu nhat.

SO DO KHONG GIAN CUA SO VAN TOC DONG DWA (ASCII DIAGRAM):

           omega ^
                 |         [ Khong gian van toc dong V_d ]
                 |        +───────────────────────────────+
                 |        |  (v_min, omega_max)           |
                 |        |                               |
                 |        |       * (v_curr, omega_curr)  |
                 |        |                               |
                 |        |  (v_max, omega_min)           |
                 |        +───────────────────────────────+
                 +───────────────────────────────────────────> v
                                (Van toc dai)

TOAN HOC HAM DANH GIA CHI PHI DWA (ASCII MATH BLOCKS):

1. Khong gian van toc dong kha thi (Dynamic Window V_d):
   v_min = max(0, v_curr - a_lin_max * dt)
   v_max = min(v_limit, v_curr + a_lin_max * dt)

   omega_min = max(-omega_limit, omega_curr - a_ang_max * dt)
   omega_max = min(+omega_limit, omega_curr + a_ang_max * dt)

2. Dieu kien phanh an toan (Admissible Velocities V_a):
   Van toc khong duoc vuot qua nguong phanh truoc vat can gan nhat:
   v <= sqrt(2 * dist_to_obstacle * a_lin_max)

3. Ham danh gia toi uu quy dao (Trajectory Objective Function):
   G(v, omega) = alpha * Heading(v, omega) + beta * Clearance(v, omega) + gamma * Velocity(v, omega)

   Trong do:
   - Heading   : Do lech goc giua mui xe o cuoi quy dao va toa do dich.
   - Clearance : Khoang cach ngan nhat tu quy dao toi vat can gan nhat.
                 (Neu nho hon ban kinh robot -> Loai bo quy dao vi se dam).
   - Velocity  : Uu tien duy tri toc do cao de toi dich nhanh nhat.
"""

from typing import Tuple, List, Dict, Any, Optional
import math


class DWAPlanner:
    """
    Bo lap ke hoach chuyen dong cuc bo Dynamic Window Approach (DWA).
    """

    def __init__(self,
                 max_speed: float = 2.0,
                 max_yaw_rate_deg: float = 90.0,
                 max_accel: float = 2.0,
                 max_yaw_accel_deg: float = 180.0,
                 robot_radius: float = 0.2,
                 predict_time: float = 3.0,
                 dt: float = 0.1):
        self.max_speed = float(max_speed)
        self.max_yaw_rate = math.radians(max_yaw_rate_deg)
        self.max_accel = float(max_accel)
        self.max_yaw_accel = math.radians(max_yaw_accel_deg)
        self.robot_radius = float(robot_radius)
        self.predict_time = float(predict_time)
        self.dt = float(dt)

        # Trong so toi uu hoa ham muc tieu G(v, omega)
        self.alpha_heading = 0.5
        self.beta_clearance = 2.0
        self.gamma_velocity = 0.8

    def calc_dynamic_window(self, current_v: float, current_omega: float) -> Tuple[float, float, float, float]:
        """
        Tinh toan cua so van toc kha thi V_d dua tren quan tinh gia toc:
        Tra ve (v_min, v_max, omega_min, omega_max)
        """
        v_min = max(0.0, current_v - self.max_accel * self.dt)
        v_max = min(self.max_speed, current_v + self.max_accel * self.dt)

        omega_min = max(-self.max_yaw_rate, current_omega - self.max_yaw_accel * self.dt)
        omega_max = min(self.max_yaw_rate, current_omega + self.max_yaw_accel * self.dt)

        return v_min, v_max, omega_min, omega_max

    def predict_trajectory(self, x: float, y: float, theta: float,
                           v: float, omega: float) -> List[Tuple[float, float, float]]:
        """
        Du doan quy dao hinh hoc trong khoang thoi gian predict_time.
        Tra ve danh sach cac vi tri tuong lai [(x_t, y_t, theta_t), ...]
        """
        traj = [(x, y, theta)]
        curr_x, curr_y, curr_theta = x, y, theta
        time_steps = int(self.predict_time / self.dt)

        for _ in range(time_steps):
            curr_x += v * math.cos(curr_theta) * self.dt
            curr_y += v * math.sin(curr_theta) * self.dt
            curr_theta += omega * self.dt
            traj.append((curr_x, curr_y, curr_theta))

        return traj

    def calc_obstacle_distance(self, traj: List[Tuple[float, float, float]],
                               obstacles: List[Tuple[float, float]]) -> float:
        """
        Tinh khoang cach ngan nhat tu quy dao du doan toi cac vat can.
        Neu co bat ky diem nao tren quy dao dam vao vat can (khoang cach <= robot_radius),
        tra ve 0.0 (quy dao khong hop le).
        """
        min_dist = float('inf')
        for px, py, _ in traj:
            for ox, oy in obstacles:
                dist = math.hypot(px - ox, py - oy)
                if dist <= self.robot_radius:
                    return 0.0  # Va cham!
                if dist < min_dist:
                    min_dist = dist
        return min_dist

    def plan(self, x: float, y: float, theta: float,
             current_v: float, current_omega: float,
             goal: Tuple[float, float],
             obstacles: List[Tuple[float, float]],
             v_samples: int = 20, omega_samples: int = 31) -> Tuple[float, float, Optional[List[Tuple[float, float, float]]]]:
        """
        Thuc thi thuat toan DWA de tim cap van toc toi uu nhat (v_best, omega_best).
        Tra ve: (best_v, best_omega, best_trajectory)
        """
        v_min, v_max, omega_min, omega_max = self.calc_dynamic_window(current_v, current_omega)

        best_cost = -float('inf')
        best_v = 0.0
        best_omega = 0.0
        best_trajectory = None

        v_step = (v_max - v_min) / max(1, v_samples - 1) if v_max > v_min else 0.0
        omega_step = (omega_max - omega_min) / max(1, omega_samples - 1) if omega_max > omega_min else 0.0

        for i in range(v_samples):
            v = v_min + i * v_step
            for j in range(omega_samples):
                omega = omega_min + j * omega_step

                traj = self.predict_trajectory(x, y, theta, v, omega)
                dist_to_obs = self.calc_obstacle_distance(traj, obstacles)

                # Neu quy dao gay va cham, bo qua ngay lap tuc
                if dist_to_obs <= 0.0:
                    continue

                # 1. Tien do huong ve dich den (Progress toward Goal)
                last_x, last_y, last_theta = traj[-1]
                curr_dist_to_goal = math.hypot(goal[0] - x, goal[1] - y)
                final_dist = math.hypot(goal[0] - last_x, goal[1] - last_y)
                progress = curr_dist_to_goal - final_dist

                # 2. Danh gia goc huong toi dich (Heading Alignment) - Chuan hoa [0, 1]
                goal_angle = math.atan2(goal[1] - last_y, goal[0] - last_x)
                angle_diff = abs((goal_angle - last_theta + math.pi) % (2.0 * math.pi) - math.pi)
                heading_bonus = (math.pi - angle_diff) / math.pi

                # 3. Danh gia khoang cach an toan (Obstacle Penalty)
                if dist_to_obs < 1.2:
                    obs_penalty = 1.0 / max(0.1, dist_to_obs)
                else:
                    obs_penalty = 0.0

                # 4. Uu tien toc do di chuyen (Velocity Score)
                vel_score = v / self.max_speed if self.max_speed > 0 else 0.0

                # Tong chi phi tong hop G(v, omega)
                total_cost = (2.0 * progress +
                              0.5 * heading_bonus +
                              0.5 * vel_score -
                              0.8 * obs_penalty)

                if total_cost > best_cost:
                    best_cost = total_cost
                    best_v = v
                    best_omega = omega
                    best_trajectory = traj

        # Neu khong co quy dao nao tranh duoc va cham, phanh dung khan cap!
        if best_trajectory is None:
            return 0.0, 0.0, None

        return best_v, best_omega, best_trajectory


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EDGE: DYNAMIC WINDOW APPROACH (DWA) PLANNER")
    print("=========================================================\n")

    # 1. Khoi tao DWA Planner voi thong so chuan
    planner = DWAPlanner(
        max_speed=2.0,
        max_yaw_rate_deg=90.0,
        max_accel=2.0,
        max_yaw_accel_deg=180.0,
        robot_radius=0.2,
        predict_time=3.0
    )

    # 2. Thiet lap tinh huong: Robot o toa do (0, 0), van toc hien tai 1.0 m/s huong theta=0 do.
    #    Dich den o (10, 0). Co mot vat can LiDAR o toa do (2.0, 0.0) chan giua duong di thang.
    goal_pos = (10.0, 0.0)
    obstacles_ahead = [(2.0, 0.0)]

    print("1. KICH BAN MO PHONG: VAT CAN CHUONG NGAI VAT O TOA DO (2.0, 0.0):")
    print(f"   -> Toa do xuat phat      : (0.0, 0.0), theta = 0.0 do, v = 1.0 m/s")
    print(f"   -> Toa do dich den       : {goal_pos}")
    print(f"   -> Vi tri vat can LiDAR  : {obstacles_ahead}")

    # Tinh toan nuoc di toi uu tu DWA
    v_opt, omega_opt, traj_opt = planner.plan(
        x=0.0, y=0.0, theta=0.0,
        current_v=1.0, current_omega=0.0,
        goal=goal_pos, obstacles=obstacles_ahead
    )

    print("\n2. KET QUA QUYET DINH VAN TOC TOI UU DWA:")
    print(f"   -> Van toc dai lua chon (v)      : {v_opt:.2f} m/s")
    print(f"   -> Toc do goc be lai (omega)     : {math.degrees(omega_opt):.2f} do/s")

    assert traj_opt is not None, "DWA phai tim ra duoc quy dao tranh va cham hop le!"
    assert abs(omega_opt) > 1e-2, "Do co vat can ngay phia truoc mat, omega phai be lai de ne!"
    print(f"   -> Danh gia tranh va cham        : THANH CONG (Robot tu dong be lai {math.degrees(omega_opt):.1f} do/s vuot vat can)\n")

    # 3. Kich ban duong thong thoang khong co vat can:
    # Robot phai duy tri huong di thang va tang toc toi da ve phia dich
    v_clear, omega_clear, _ = planner.plan(
        x=0.0, y=0.0, theta=0.0,
        current_v=1.0, current_omega=0.0,
        goal=(10.0, 0.0), obstacles=[]
    )
    print("3. KICH BAN DUONG THONG THOANG (KHONG CO VAT CAN):")
    print(f"   -> Van toc lua chon (v)          : {v_clear:.2f} m/s")
    print(f"   -> Toc do goc lua chon (omega)   : {math.degrees(omega_clear):.2f} do/s")
    assert abs(omega_clear) < 1e-2, "Khi duong thang thoang, robot phai giu nguyen goc di thang (omega = 0)!"
    assert v_clear > 1.0, "Robot phai tang toc ve phia dich!"

    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN NE TRAP VAT CAN DWA CHO ROBOT TU HANH!")
