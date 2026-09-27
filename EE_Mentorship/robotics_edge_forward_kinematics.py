"""
================================================================================
          MODULE P: ADVANCED ROBOTICS KINEMATICS & TRAJECTORY PLANNING
    MILESTONE P.3: DONG HOC THUAN FORWARD KINEMATICS CANH TAY ROBOT 2 KHOP
================================================================================

1. NGUYEN LY CO HOC & DONG HOC ROBOT (FORWARD KINEMATICS & DH CONVENTION):
   - Khi dieu khien canh tay robot gap vat the tren Drone hoac day chuyen san xuat:
     + Bo doc Encoder tai cac dong co Servo chi tra ve goc xoay (theta1, theta2).
     + Bo dieu khien trung tam can biet chinh xac toa do (x, y) cua dau kep
       End-Effector trong khong gian de gap trung vat the.
   - Phep tinh Dong hoc thuan (Forward Kinematics):
     Bien doi tu khong gian goc khop (Joint Space: theta1, theta2)
     sang khong gian toa do Descartes (Task/Cartesian Space: x, y).

2. SO DO CO KHI & MA TRAN BIEN DOI (ASCII BLOCKS):

   So do hinh hoc Canh tay Robot phang 2 bac tu do (2-DOF Planar Arm):

                         (x, y) End-Effector (Dau kep gap vat)
                           o
                          /
                      L2 /
                        /  theta2 (Goc tuong doi giua link 2 va link 1)
                       o (Khop 2: x1, y1)
                      /
                  L1 /
                    /  theta1 (Goc quay so voi truc hoanh X)
      ─────────────o (Goc toa do Base: 0, 0)

   Cong thuc toa do luong giac dau kep:
   x = L1 * cos(theta1) + L2 * cos(theta1 + theta2)
   y = L1 * sin(theta1) + L2 * sin(theta1 + theta2)

   Ma tran bien doi dong nhat 3x3 (Denavit-Hartenberg Homogeneous Transform):
   T_0_1 = [
     [ cos(theta1), -sin(theta1),  L1 * cos(theta1) ],
     [ sin(theta1),  cos(theta1),  L1 * sin(theta1) ],
     [           0,            0,                 1 ]
   ]

   Ma tran vi phan Jacobian J (Van toc dau kep v = J * omega):
   J = [
     [ -L1*sin(theta1) - L2*sin(theta1+theta2),  -L2*sin(theta1+theta2) ],
     [  L1*cos(theta1) + L2*cos(theta1+theta2),   L2*cos(theta1+theta2) ]
   ]
   Dinh thuc Jacobian det(J) = L1 * L2 * sin(theta2)
   Diem ky di (Singularity): xay ra khi theta2 = 0 hoac pi (tay duoi thang hoac gap sat)!
"""

from typing import Tuple
import numpy as np


class TwoLinkPlanarArm:
    """
    Mo hinh canh tay Robot phang 2-DOF voi phep tinh Dong hoc thuan va ma tran Jacobian.
    """
    def __init__(self, L1: float, L2: float):
        self.L1 = float(L1)
        self.L2 = float(L2)

    def forward_kinematics(self, theta1_rad: float, theta2_rad: float) -> Tuple[float, float]:
        """
        Tinh toa do diem cuoi End-Effector (x, y) tu goc khop (theta1, theta2):
        x = L1 * cos(theta1) + L2 * cos(theta1 + theta2)
        y = L1 * sin(theta1) + L2 * sin(theta1 + theta2)
        """
        x = self.L1 * np.cos(theta1_rad) + self.L2 * np.cos(theta1_rad + theta2_rad)
        y = self.L1 * np.sin(theta1_rad) + self.L2 * np.sin(theta1_rad + theta2_rad)
        return float(x), float(y)

    def get_joint_positions(self, theta1_rad: float, theta2_rad: float) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        """
        Tra ve toa do cua ca 3 diem khop: (Base, Joint2, EndEffector)
        """
        p0 = (0.0, 0.0)
        p1 = (float(self.L1 * np.cos(theta1_rad)), float(self.L1 * np.sin(theta1_rad)))
        p2 = self.forward_kinematics(theta1_rad, theta2_rad)
        return p0, p1, p2

    def compute_jacobian(self, theta1_rad: float, theta2_rad: float) -> np.ndarray:
        """
        Tinh ma tran Jacobian J(theta) kich thuoc 2x2.
        """
        s1 = np.sin(theta1_rad)
        c1 = np.cos(theta1_rad)
        s12 = np.sin(theta1_rad + theta2_rad)
        c12 = np.cos(theta1_rad + theta2_rad)

        j11 = -self.L1 * s1 - self.L2 * s12
        j12 = -self.L2 * s12
        j21 = self.L1 * c1 + self.L2 * c12
        j22 = self.L2 * c12

        return np.array([[j11, j12], [j21, j22]], dtype=np.float64)

    def is_singularity(self, theta2_rad: float, tol: float = 1e-4) -> bool:
        """
        Kiem tra trang thai ky di: khi sin(theta2) ~ 0
        """
        det = self.L1 * self.L2 * np.sin(theta2_rad)
        return abs(det) < tol


def compute_2link_forward_kinematics(L1: float, L2: float, theta1_rad: float, theta2_rad: float):
    """
    Ham backward-compatible giu nguyen signature cua Milestone P.3.
    """
    arm = TwoLinkPlanarArm(L1=L1, L2=L2)
    return arm.forward_kinematics(theta1_rad, theta2_rad)


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EE: 2-LINK FORWARD KINEMATICS ENGINE")
    print("=========================================================\n")

    # Canh tay robot co 2 dot dai L1 = 1.0m, L2 = 1.0m
    arm = TwoLinkPlanarArm(L1=1.0, L2=1.0)

    # 1. Kiem tra tinh huong 1: Tay gap vuong goc (theta1 = 0 rad, theta2 = pi/2 rad)
    # -> Dot 1 nam tren truc X: (1.0, 0.0)
    # -> Dot 2 huong thang dung len tren: (1.0, 1.0)
    x1, y1 = arm.forward_kinematics(theta1_rad=0.0, theta2_rad=np.pi / 2.0)
    print("1. TRUONG HOP 1 - TAY GAP VUONG GOC (theta1 = 0 deg, theta2 = 90 deg):")
    print(f"   -> Toa do X dau kep : {x1:.2f} m")
    print(f"   -> Toa do Y dau kep : {y1:.2f} m")
    assert np.isclose(x1, 1.0, atol=1e-5) and np.isclose(y1, 1.0, atol=1e-5)

    # 2. Kiem tra tinh huong 2: Tay duoi thang cuc dai (theta1 = 0 rad, theta2 = 0 rad)
    # -> Ca 2 dot duoi thang tren truc X: (1.0 + 1.0 = 2.0m, 0.0m)
    x2, y2 = arm.forward_kinematics(theta1_rad=0.0, theta2_rad=0.0)
    print("\n2. TRUONG HOP 2 - TAY DUOI THANG CUC DAI (theta1 = 0 deg, theta2 = 0 deg):")
    print(f"   -> Toa do X dau kep : {x2:.2f} m  (Phai dat tam vuon toi da = L1 + L2 = 2.0m)")
    print(f"   -> Toa do Y dau kep : {y2:.2f} m")
    assert np.isclose(x2, 2.0, atol=1e-5) and np.isclose(y2, 0.0, atol=1e-5)

    # 3. Kiem tra diem ky di (Singularity Check):
    # Khi theta2 = 0, tay duoi thang, khong the di chuyen ra xa them nua -> Ky di!
    is_singular = arm.is_singularity(theta2_rad=0.0)
    print(f"\n3. KIEM TRA DIEM KY DI (SINGULARITY): {'DUNG' if is_singular else 'SAI'} (det(J) = 0)")
    assert is_singular

    print("\n[THANH CONG] DA HOAN THANH TINH TOAN DONG HOC THUAN FORWARD KINEMATICS CHO ROBOT!")
