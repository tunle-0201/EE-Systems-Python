"""
================================================================================
          MODULE AA: ROBOTIC KINODYNAMICS & AUTONOMOUS MOTION PLANNING
          MILESTONE AA.1: ACKERMANN KINEMATIC BICYCLE MODEL FOR TESLA FSD
================================================================================

TAI SAO CAC HE THONG XE TU HANH (TESLA, WAYMO) DUNG MO HINH ACKERMANN BICYCLE?
- Khac voi robot banh xich (differential drive) co the xoay tron tai cho (turning
  radius = 0), oto thuong co co cau lai hinh hoc Ackermann voi banh truoc be lai
  va banh sau co dinh truc quay.
- Neu co tinh ep xe quay voi banh truoc vuot qua gioi han goc be lai (delta_max),
  banh xe se bi truot ngang (side-slip), lam mat kiem soat luc bam mat duong.

SO DO DONG HOC XE ACKERMANN BICYCLE MODEL (ASCII DIAGRAM):

               Y ^
                 |             Banh truoc (Front Wheel)
                 |               [====]  (Goc be lai delta)
                 |                /
                 |               /
                 |              /  Khoang cach truc co so L (Wheelbase)
                 |             /
                 |            /
                 |          [====]  Banh sau (Rear Wheel, toa do x, y)
                 +----------------------------> X
                          (Goc huong xe theta)

CAC CONG THUC DONG HOC VI PHAN (ASCII MATH BLOCKS):

1. Phuong trinh vi phan cap nhat trang thai:
   dx
   ── = v * cos(theta)
   dt

   dy
   ── = v * sin(theta)
   dt

   d(theta)     v
   ──────── = ───── * tan(delta)
      dt        L

2. Ban kinh quay vong toi thieu (Minimum Turning Radius R_min):
            L
   R = ────────────
       |tan(delta)|

   Khi goc lai dat cuc dai (delta = delta_max):
               L
   R_min = ──────────────
           tan(delta_max)

3. Truong hop bien (Edge Cases):
   - Khi xe chay thang (delta = 0): tan(delta) = 0 -> R = vo cung (infinity).
     Toc do goc d(theta)/dt = 0, xe giu nguyen huong di.
   - Khi xe lui (v < 0): Phuong trinh van dung dung, huong quay nguoc lai.
"""

from typing import Tuple, List, Dict, Any, Optional
import math


class AckermannVehicle:
    """
    Mo hinh xe tu hanh Ackermann Kinematic Bicycle Model.
    - x, y: Toa do tam truc banh sau (met)
    - theta: Goc huong dau xe (radian)
    - wheelbase (L): Khoang cach giua truc banh truoc va banh sau (met)
    - max_steer_angle: Goc be lai cuc dai cua banh truoc (radian)
    """

    def __init__(self, x: float = 0.0, y: float = 0.0, theta: float = 0.0,
                 wheelbase: float = 2.8, max_steer_deg: float = 35.0):
        self.x = float(x)
        self.y = float(y)
        self.theta = float(theta)
        self.wheelbase = float(wheelbase)
        self.max_steer_angle = math.radians(max_steer_deg)

    @property
    def min_turning_radius(self) -> float:
        """
        Tinh ban kinh quay vong toi thieu dua tren goc be lai cuc dai.
        R_min = L / tan(delta_max)
        """
        return self.wheelbase / math.tan(self.max_steer_angle)

    def calculate_turning_radius(self, steer_angle: float) -> float:
        """
        Tinh ban kinh quay vong tai goc be lai steer_angle.
        Neu steer_angle == 0, tra ve float('inf') (chay thang).
        """
        clamped_steer = max(-self.max_steer_angle, min(self.max_steer_angle, steer_angle))
        if abs(clamped_steer) < 1e-6:
            return float('inf')
        return self.wheelbase / abs(math.tan(clamped_steer))

    def step(self, v: float, steer_angle: float, dt: float) -> Tuple[float, float, float]:
        """
        Cap nhat trang thai xe sau khoang thoi gian dt:
        - v: Van toc dai cua xe (m/s)
        - steer_angle: Goc be lai banh truoc (radian)
        - dt: Buoc thoi gian tich phan (giay)
        Tra ve trang thai moi (x, y, theta).
        """
        # Gioi han goc lai trong pham vi vat ly cho phep
        delta = max(-self.max_steer_angle, min(self.max_steer_angle, steer_angle))

        # Tich phan vi phan Euler
        dx = v * math.cos(self.theta) * dt
        dy = v * math.sin(self.theta) * dt
        dtheta = (v / self.wheelbase) * math.tan(delta) * dt

        self.x += dx
        self.y += dy
        self.theta += dtheta

        # Chuan hoa theta ve khoang [-pi, pi]
        self.theta = (self.theta + math.pi) % (2.0 * math.pi) - math.pi

        return self.x, self.y, self.theta

    def simulate(self, v: float, steer_angle: float, duration: float, dt: float = 0.05) -> List[Tuple[float, float, float]]:
        """
        Mo phong quy dao di chuyen trong mot khoang thoi gian duration.
        Tra ve danh sach cac toa do [(x, y, theta), ...]
        """
        steps = int(duration / dt)
        trajectory = [(self.x, self.y, self.theta)]
        for _ in range(steps):
            new_state = self.step(v, steer_angle, dt)
            trajectory.append(new_state)
        return trajectory


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EDGE: ACKERMANN KINEMATIC BICYCLE MODEL")
    print("=========================================================\n")

    # 1. Khoi tao xe Tesla Model 3 (Wheelbase = 2.875m, Goc lai toi da = 35 do)
    vehicle = AckermannVehicle(x=0.0, y=0.0, theta=0.0, wheelbase=2.875, max_steer_deg=35.0)

    r_min = vehicle.min_turning_radius
    print(f"1. THONG SO XE ACKERMANN CO BAN:")
    print(f"   -> Chieu dai truc co so (L)   : {vehicle.wheelbase} m")
    print(f"   -> Goc lai toi da (delta_max) : {math.degrees(vehicle.max_steer_angle):.1f} do")
    print(f"   -> Ban kinh quay toi thieu    : {r_min:.2f} m\n")

    # 2. Test tinh ban kinh quay khi chay thang va khi be lai
    r_straight = vehicle.calculate_turning_radius(0.0)
    steer_20_deg = math.radians(20.0)
    r_turn_20 = vehicle.calculate_turning_radius(steer_20_deg)
    print("2. KIEM TRA BAN KINH QUAY TAI CAC GOC LAI KHAC NHAU:")
    print(f"   -> Khi steer = 0 do          : {r_straight} (Chay thang vo tan)")
    print(f"   -> Khi steer = 20 do         : {r_turn_20:.2f} m")
    assert math.isinf(r_straight), "Khi steer = 0 do, ban kinh quay phai la vo cung!"
    assert abs(r_turn_20 - (2.875 / math.tan(steer_20_deg))) < 1e-4

    # 3. Mo phong xe di thang 10 giay voi toc do 5 m/s
    print("\n3. MO PHONG XE CHAY THANG (v=5 m/s, steer=0 do, t=2s):")
    v_test = 5.0
    traj_straight = vehicle.simulate(v=v_test, steer_angle=0.0, duration=2.0, dt=0.1)
    print(f"   -> Toa do sau 2 giay         : x={vehicle.x:.2f} m, y={vehicle.y:.2f} m, theta={math.degrees(vehicle.theta):.2f} do")
    assert abs(vehicle.x - 10.0) < 0.1, "Xe chay thang voi v=5m/s trong 2s phai dat x xap xi 10m!"
    assert abs(vehicle.y) < 1e-3, "Toa do y phai bang 0 khi chay thang!"

    # 4. Mo phong xe cua trai voi goc lai toi da (delta = 35 do) trong 3 giay
    print("\n4. MO PHONG XE CUA TRAI GOC LAI TOI DA (delta=35 do, v=4 m/s, t=3s):")
    init_x, init_y, init_theta = vehicle.x, vehicle.y, vehicle.theta
    traj_turn = vehicle.simulate(v=4.0, steer_angle=vehicle.max_steer_angle, duration=3.0, dt=0.05)
    print(f"   -> Toa do xuat phat cua      : x={init_x:.2f} m, y={init_y:.2f} m")
    print(f"   -> Toa do sau khi cua 3 giay : x={vehicle.x:.2f} m, y={vehicle.y:.2f} m, theta={math.degrees(vehicle.theta):.2f} do")
    assert vehicle.theta > init_theta, "Xe phai quay dau sang trai (theta tang len)!"

    # 5. Kiem tra tinh huong bien: Goc lai vuot gioi han vat ly (Phai duoc clamp an toan)
    clamped_r = vehicle.calculate_turning_radius(math.radians(90.0))
    assert abs(clamped_r - r_min) < 1e-4, "Goc lai qua muc phai duoc han che ve r_min!"
    print(f"\n5. KIEM TRA GOC LAI VUOT NGUONG (90 do -> Clamp ve 35 do):")
    print(f"   -> Ban kinh thu duoc         : {clamped_r:.2f} m (Trung khop R_min)")

    print("\n[THANH CONG] DA HOAN THANH MO HINH DONG HOC ACKERMANN CHUAN CHO XE TU HANH TESLA!")
