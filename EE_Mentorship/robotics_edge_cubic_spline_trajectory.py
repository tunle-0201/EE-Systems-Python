"""
================================================================================
          MODULE P: ADVANCED ROBOTICS KINEMATICS & TRAJECTORY PLANNING
    MILESTONE P.2: QUY DAO BAC 3 CUBIC SPLINE TRIET TIEU GIAT CUC (JERK-FREE)
================================================================================

1. NGUYEN LY VAT LY & KY THUAT (ROBOTICS TRAJECTORY PLANNING):
   - Khi dieu khien Drone bay giua cac Waypoint hoac canh tay Robot cong nghiep:
     + Neu dung noi suy tuyen tinh (Linear Interpolation): Van toc thay doi dot ngot
       tai diem bat dau va ket thuc.
     + Gia toc tien den vo cung (Infinite Acceleration Spike)!
     + Dao ham bac 3 (Jerk = da/dt) cuc lon gay rung giat khung co khi,
       qua tai dong co va lam hong hop so / gimbal cam bien.
   - Giai phap Ky su Dieu khien: Quy dao da thuc bac 3 (Cubic Polynomial Trajectory):
     Dam bao van toc dau va cuoi deu bang 0 (v0 = vf = 0). Drone luot di va dung
     lai em ai tuyet doi!

2. HE PHUONG TRINH TOAN HOC & DIEU KIEN BIEN (ASCII MATH BLOCKS):

   So do so sanh Van toc: Noi suy bac 1 (Giat cuc) vs Quy dao bac 3 (Em ai):
   
   Van toc noi suy tuyen tinh:               Van toc quy dao bac 3:
   v(t)                                      v(t)
    ▲   ┌───────────────┐                     ▲          ╭──────╮
    │   │ (Giat khung!) │                     │        ╭╯        ╰╮
    │   │               │                     │       ╭╯          ╰╮ (Em ai)
    └───┴───────────────┴────► t              └───────┴────────────┴────► t
       t=0             t=tf                          t=0          t=tf

   Phuong trinh vi tri, van toc va gia toc:
   p(t) = a0 + a1*t + a2*t^2 + a3*t^3
   v(t) = a1 + 2*a2*t + 3*a3*t^2
   a(t) = 2*a2 + 6*a3*t

   Dieu kien bien (Boundary Conditions):
   p(0)  = p0  ──> a0 = p0
   v(0)  = 0   ──> a1 = 0
   p(tf) = pf  ──> a0 + a2*tf^2 + a3*tf^3 = pf
   v(tf) = 0   ──> 2*a2*tf + 3*a3*tf^2 = 0

   Nghiem giai tich cua he he so (Closed-form Coefficients):

            3 * (pf - p0)
     a2 = ─────────────────
                 tf^2

           -2 * (pf - p0)
     a3 = ─────────────────
                 tf^3
"""

from typing import Tuple
import numpy as np


class CubicTrajectoryPlanner:
    """
    Bo hoach dinh quy dao da thuc bac 3 cho Drone va tay Robot.
    """
    def __init__(self, p0: float, pf: float, tf: float):
        self.p0 = float(p0)
        self.pf = float(pf)
        self.tf = float(tf)
        
        # Tinh toan he so bac 3
        self.a0 = self.p0
        self.a1 = 0.0
        self.a2 = 3.0 * (self.pf - self.p0) / (self.tf ** 2)
        self.a3 = -2.0 * (self.pf - self.p0) / (self.tf ** 3)

    def evaluate(self, t: float) -> Tuple[float, float, float]:
        """
        Tinh toan trang thai tai thoi diem t:
        - Vi tri p(t) = a0 + a2*t^2 + a3*t^3
        - Van toc v(t) = 2*a2*t + 3*a3*t^2
        - Gia toc a(t) = 2*a2 + 6*a3*t
        Tra ve bo 3 gia tri: (pos, vel, acc)
        """
        if t <= 0.0:
            return self.p0, 0.0, 2.0 * self.a2
        if t >= self.tf:
            return self.pf, 0.0, 2.0 * self.a2 + 6.0 * self.a3 * self.tf

        pos = self.a0 + self.a2 * (t ** 2) + self.a3 * (t ** 3)
        vel = 2.0 * self.a2 * t + 3.0 * self.a3 * (t ** 2)
        acc = 2.0 * self.a2 + 6.0 * self.a3 * t
        return pos, vel, acc


def generate_cubic_trajectory_point(p0: float, pf: float, t: float, tf: float) -> float:
    """
    Ham backward-compatible giu nguyen signature cua Milestone P.2.
    """
    planner = CubicTrajectoryPlanner(p0=p0, pf=pf, tf=tf)
    pos, _, _ = planner.evaluate(t)
    return pos


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EE: CUBIC POLYNOMIAL TRAJECTORY PLANNER")
    print("=========================================================\n")

    # Bay tu toa do p0 = 0.0m den pf = 10.0m trong tong thoi gian tf = 2.0s
    planner = CubicTrajectoryPlanner(p0=0.0, pf=10.0, tf=2.0)

    # 1. Kiem tra tai thoi diem ban dau t = 0.0s
    p_start, v_start, a_start = planner.evaluate(0.0)
    print("1. TRANG THAI KHOI HANH (t = 0.0s):")
    print(f"   -> Vi tri   : {p_start:.2f} m")
    print(f"   -> Van toc  : {v_start:.2f} m/s  (Triet tieu van toc dot ngot)")
    assert np.isclose(p_start, 0.0) and np.isclose(v_start, 0.0)

    # 2. Kiem tra tai thoi diem chinh giua hanh trinh t = 1.0s (Nua thoi gian tf)
    p_mid, v_mid, a_mid = planner.evaluate(1.0)
    print("\n2. TRANG THAI CHINH GIUA HANH TRINH (t = 1.0s):")
    print(f"   -> Vi tri   : {p_mid:.2f} m  (Phai dat dung 50% quang duong = 5.0m)")
    print(f"   -> Van toc  : {v_mid:.2f} m/s  (Van toc dat cuc dai tai diem uon)")
    print(f"   -> Gia toc  : {a_mid:.2f} m/s^2 (Gia toc chuyen doi dau = 0)")
    assert np.isclose(p_mid, 5.0, atol=1e-5)
    assert np.isclose(a_mid, 0.0, atol=1e-5)

    # 3. Kiem tra tai thoi diem den dich t = 2.0s
    p_end, v_end, a_end = planner.evaluate(2.0)
    print("\n3. TRANG THAI CAP BEN DICH (t = 2.0s):")
    print(f"   -> Vi tri   : {p_end:.2f} m")
    print(f"   -> Van toc  : {v_end:.2f} m/s  (Dung han khong bi giat)")
    assert np.isclose(p_end, 10.0) and np.isclose(v_end, 0.0)

    print("\n[THANH CONG] DA HOAN THANH BO HOACH DINH QUY DAO MUOT MA CHO DRONE VA TAY ROBOT!")
