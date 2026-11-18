"""
================================================================================
          MODULE S: EMBEDDED DIGITAL POWER ELECTRONICS & FOC MOTOR CONTROL
    MILESTONE S.1: BIEN DOI CLARKE DONG DIEN 3 PHA SANG HE TRUC ALPHA-BETA
================================================================================

1. NGUYEN LY VAT LY & DIEN TU CONG SUAT (FIELD-ORIENTED CONTROL FOUNDATION):
   - Tai sao xe dien Tesla (Model 3/S/Y) va Drone bay hien dai khong the thieu FOC?
     + Dong co khong choi than (BLDC / PMSM) co 3 cuon day stator dat lech nhau 120 do
       trong khong gian (Pha A, Pha B, Pha C).
     + 3 dong dien xoay chieu Ia, Ib, Ic bien thien hinh sin lien tuc voi tan so cao.
     + Bo dieu khien PID thong thuong khong the bam theo kip 3 tin hieu sin xoay chieu 120 do nay!
   - Giai phap FOC (Field-Oriented Control - Dieu khien tua tu thong):
     + Buoc dau tien: Phep bien doi Clarke Transform!
     + Chuyen 3 dai luong xoay chieu lech 120 do (Khong gian 3 truc a-b-c)
       sang he toa do vuong goc 2 truc tinh 90 do (Alpha - Beta).
     + Truc Alpha nam trung voi truc pha A.
     + Truc Beta vuong goc 90 do so voi truc Alpha.

2. SO DO KHONG GIAN & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do hinh hoc phep chieu Clarke Transform (3 pha sang 2 truc vuong goc):

                Beta (Truc vuong goc 90 deg)
                 ▲
                 │      Phase B (120 deg)
                 │     /
                 │    /
                 │   /
   ──────────────┼──────────────► Alpha (Truc 0 deg, trung Phase A)
                /│\
               / │ \
              /  │  \
     Phase C /   │   \
    (240 deg)    │

   Dinh luat Kirchhoff ve dong dien (KCL) tai diem trung tinh:
   Ia + Ib + Ic = 0  ──►  Ic = -Ia - Ib (Chi can 2 cam bien dong shunt tren bo mach!)

   Cong thuc bien doi thuan Clarke (Forward Clarke Transform):

   I_alpha = Ia

             Ia + 2 * Ib
   I_beta  = ───────────
               sqrt(3)

   Cong thuc bien doi nguoc Clarke (Inverse Clarke Transform):

   Ia = I_alpha
   Ib = -0.5 * I_alpha + (sqrt(3) / 2) * I_beta
   Ic = -0.5 * I_alpha - (sqrt(3) / 2) * I_beta
"""

from typing import Tuple
import numpy as np


class ClarkeTransform:
    """
    Bo bien doi he toa do Clarke thuan va nghich cho he thong dieu khien dong co FOC.
    """
    def __init__(self):
        self.inv_sqrt3 = 1.0 / np.sqrt(3.0)
        self.sqrt3_over_2 = np.sqrt(3.0) / 2.0

    def forward(self, ia: float, ib: float, ic: float = None) -> Tuple[float, float]:
        """
        Bien doi Clarke thuan: (Ia, Ib, Ic) -> (I_alpha, I_beta)
        Neu ic khong duoc truyen vao, tu dong tinh theo KCL: ic = -ia - ib
        """
        i_alpha = float(ia)
        i_beta = float((ia + 2.0 * ib) * self.inv_sqrt3)
        return i_alpha, i_beta

    def inverse(self, i_alpha: float, i_beta: float) -> Tuple[float, float, float]:
        """
        Bien doi Clarke nguoc: (I_alpha, I_beta) -> (Ia, Ib, Ic)
        """
        ia = float(i_alpha)
        ib = float(-0.5 * i_alpha + self.sqrt3_over_2 * i_beta)
        ic = float(-0.5 * i_alpha - self.sqrt3_over_2 * i_beta)
        return ia, ib, ic


def compute_clarke_transform(ia: float, ib: float, ic: float) -> Tuple[float, float]:
    """
    Ham backward-compatible giu nguyen signature cua Milestone S.1.
    """
    engine = ClarkeTransform()
    return engine.forward(ia, ib, ic)


if __name__ == "__main__":
    print("=========================================================")
    print("   DIGITAL POWER ELECTRONICS: 3-PHASE CLARKE TRANSFORM")
    print("=========================================================\n")

    # 3 pha dong dien dong co lech nhau 120 do: Ia = 10.0A, Ib = -5.0A, Ic = -5.0A
    Ia = 10.0
    Ib = -5.0
    Ic = -5.0

    clarke = ClarkeTransform()
    i_a, i_b = clarke.forward(Ia, Ib, Ic)

    print("1. KET QUA BIEN DOI DONG DIEN 3 PHA SANG HE TRUC ALPHA-BETA:")
    print(f"   -> Dong dien 3 pha vao : Ia = {Ia:.2f}A, Ib = {Ib:.2f}A, Ic = {Ic:.2f}A")
    print(f"   -> Dong I_alpha (Truc A): {i_a:.2f} A")
    print(f"   -> Dong I_beta  (Truc B): {i_b:.2f} A")

    assert abs(i_a - 10.0) < 1e-5 and abs(i_b - 0.0) < 1e-5, "Loi Clarke Transform!"

    # 2. Thu nghiem bien doi nguoc Inverse Clarke Transform
    rec_ia, rec_ib, rec_ic = clarke.inverse(i_a, i_b)
    print("\n2. KIEM TRA BIEN DOI NGUOC (INVERSE CLARKE TRANSFORM):")
    print(f"   -> Phuc hoi Ia : {rec_ia:.2f} A")
    print(f"   -> Phuc hoi Ib : {rec_ib:.2f} A")
    print(f"   -> Phuc hoi Ic : {rec_ic:.2f} A")

    assert abs(rec_ia - Ia) < 1e-5 and abs(rec_ib - Ib) < 1e-5 and abs(rec_ic - Ic) < 1e-5

    print("\n[THANH CONG] DA HOAN THANH BIEN DOI CLARKE DIEU KHIEN DONG CO BLDC CHO DRONE!")
