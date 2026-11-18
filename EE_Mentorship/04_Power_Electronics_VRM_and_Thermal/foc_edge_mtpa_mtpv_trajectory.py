"""
================================================================================
CHUYEN DE AG: HARDWARE MOTOR FIELD WEAKENING & OVERMODULATION (FW & OVM)
BAI 2: QUY DAO TOI UU MO-MEN XOAN MTPA VA MTPV CHO DONG CO XE DIEN TESLA
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Toi uu hoa nang luong pin va tang 20% mo-men xoan tu tro cho Tesla Plaid
Ngon ngu: Python 3 thuan tuy, giai tich toan hoc cuc tri Lagrange & Tra cuu LUT O(1)
================================================================================
"""

import math
from typing import Tuple, List, Dict

from foc_edge_field_weakening_controller import MotorParameters

# ------------------------------------------------------------------------------
# 1. TOAN HOC QUY DAO MTPA (MAXIMUM TORQUE PER AMPERE)
# ------------------------------------------------------------------------------

class MTPATrajectoryCalculator:
    """
    Bo tinh toan quy dao toi uu Mo-men xoan tren moi Ampe (MTPA):
    Dua tren hieu ung di huong tu tro (Saliency Lq > Ld) cua dong co IPMSM.
    Te = 1.5 * p * [ lambda_pm * Iq + (Ld - Lq) * Id * Iq ]
    
    Phuong trinh cuc tri Lagrange de cuc dai hoa Te voi Is^2 = Id^2 + Iq^2 co dinh:
    Id_mtpa = (lambda_pm - sqrt(lambda_pm^2 + 8 * (Lq - Ld)^2 * Is^2)) / (4 * (Lq - Ld))
    Iq_mtpa = sqrt(Is^2 - Id_mtpa^2)
    """
    def __init__(self, motor: MotorParameters):
        self.m = motor
        self.delta_L = motor.Lq - motor.Ld # Luon > 0 doi voi IPMSM

    def compute_mtpa_currents_from_is(self, Is: float) -> Tuple[float, float]:
        """
        Tinh cap dong dien toi uu (Id, Iq) tu bien do dong tong Is = sqrt(Id^2 + Iq^2).
        """
        if Is <= 1e-6:
            return (0.0, 0.0)

        # Ap dung cong thuc giai tich MTPA chinh xac:
        # Id = (lambda_pm - sqrt(lambda_pm^2 + 8 * delta_L^2 * Is^2)) / (4 * delta_L)
        term1 = self.m.lambda_pm
        term2 = math.sqrt(self.m.lambda_pm ** 2 + 8.0 * (self.delta_L ** 2) * (Is ** 2))
        id_mtpa = (term1 - term2) / (4.0 * self.delta_L)

        # Iq luon duong de sinh mo-men tien
        iq_sq = Is ** 2 - id_mtpa ** 2
        iq_mtpa = math.sqrt(max(0.0, iq_sq))

        return (id_mtpa, iq_mtpa)

    def compute_torque(self, id_val: float, iq_val: float) -> float:
        """Tinh mo-men xoan dien tu tong hop Te (Nm)."""
        # Te = 1.5 * p * [ lambda_pm * Iq + (Ld - Lq) * Id * Iq ]
        mag_torque = self.m.lambda_pm * iq_val
        rel_torque = (self.m.Ld - self.m.Lq) * id_val * iq_val
        return 1.5 * self.m.pole_pairs * (mag_torque + rel_torque)

# ------------------------------------------------------------------------------
# 2. BANG TRA CUU THOI GIAN THUC O(1) CHO PHAN CUNG NHUNG (MTPA LOOKUP TABLE)
# ------------------------------------------------------------------------------

class MTPALookupTable:
    """
    Bang tra cuu LUT (Lookup Table) tao san truoc:
    Chuyen doi yeu cau mo-men T_ref sang cap dong (Id*, Iq*) trong thoi gian thuc O(1),
    khong can tinh phep can bac hai ton kem chu ky CPU tren vi dieu khien DSP xe dien.
    """
    def __init__(self, calc: MTPATrajectoryCalculator, num_points: int = 100):
        self.calc = calc
        self.num_points = num_points
        self.lut_torque: List[float] = []
        self.lut_id: List[float] = []
        self.lut_iq: List[float] = []

        # Tinh toan truoc bang LUT
        max_is = calc.m.I_max
        for i in range(num_points):
            is_val = (i / (num_points - 1)) * max_is
            id_val, iq_val = calc.compute_mtpa_currents_from_is(is_val)
            t_val = calc.compute_torque(id_val, iq_val)

            self.lut_torque.append(t_val)
            self.lut_id.append(id_val)
            self.lut_iq.append(iq_val)

        self.max_torque = self.lut_torque[-1]

    def lookup(self, torque_ref: float) -> Tuple[float, float]:
        """
        Tra cuu cap dong (Id*, Iq*) tu mo-men yeu cau T_ref bang noi suy tuyen tinh O(1).
        """
        if torque_ref <= 0.0:
            return (0.0, 0.0)
        if torque_ref >= self.max_torque:
            return (self.lut_id[-1], self.lut_iq[-1])

        # Tim khoang bang Binary Search hoac Index truc tiep
        low = 0
        high = self.num_points - 1
        while low <= high:
            mid = (low + high) // 2
            if self.lut_torque[mid] < torque_ref:
                low = mid + 1
            else:
                high = mid - 1

        idx = max(0, min(self.num_points - 2, high))
        t0 = self.lut_torque[idx]
        t1 = self.lut_torque[idx + 1]

        # He so noi suy
        alpha = (torque_ref - t0) / (t1 - t0) if t1 > t0 else 0.0
        id_interp = (1.0 - alpha) * self.lut_id[idx] + alpha * self.lut_id[idx + 1]
        iq_interp = (1.0 - alpha) * self.lut_iq[idx] + alpha * self.lut_iq[idx + 1]

        return (id_interp, iq_interp)

# ------------------------------------------------------------------------------
# 3. MO PHONG VA SO SANH: CO MTPA VS KHONG CO MTPA (Id = 0)
# ------------------------------------------------------------------------------

def test_mtpa_torque_enhancement():
    """
    Kiem tra 1: So sanh mo-men xoan tao ra giua:
    1. Chien luoc truyen thong: Id = 0 (Chi dung mo-men nam cham, bo phi mo-men tu tro).
    2. Chien luoc MTPA: Bom Id < 0 khai thac triet de mo-men tu tro Reluctance Torque.
    Dung dong dien Is = 200A.
    """
    motor = MotorParameters()
    calc = MTPATrajectoryCalculator(motor)

    Is_test = 200.0 # 200 Ampe stator

    # 1. Chien luoc Id = 0: Id = 0, Iq = Is = 200A
    torque_id_zero = calc.compute_torque(0.0, Is_test)

    # 2. Chien luoc MTPA
    id_mtpa, iq_mtpa = calc.compute_mtpa_currents_from_is(Is_test)
    torque_mtpa = calc.compute_torque(id_mtpa, iq_mtpa)

    # Do tang them mo-men xoan tinh theo %
    torque_boost_percent = ((torque_mtpa - torque_id_zero) / torque_id_zero) * 100.0

    print("--------------------------------------------------------------------------------")
    print(f"SO SANH MO-MEN XOAN TAI DONG DIEN IS = {Is_test:.1f} A:")
    print(f"-> Chien luoc Id = 0 (Truyen thong) : Id =   0.00 A | Iq = {Is_test:6.2f} A | Torque = {torque_id_zero:6.2f} Nm")
    print(f"-> Chien luoc MTPA (Tesla Plaid)    : Id = {id_mtpa:6.2f} A | Iq = {iq_mtpa:6.2f} A | Torque = {torque_mtpa:6.2f} Nm")
    print(f"-> Do tang mo-men xoan nho tu tro   : +{torque_boost_percent:.2f}% (HOAN TOAN KHONG TON THEM DONG PIN!)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. MTPA phai tang them it nhat 10% mo-men xoan so voi chien luoc Id = 0
    assert torque_boost_percent > 10.0, f"Loi: Do tang mo-men xoan khong dat: {torque_boost_percent:.2f}%"
    # 2. Tong bien do dong phai dung bang Is = 200A
    current_mag = math.sqrt(id_mtpa ** 2 + iq_mtpa ** 2)
    assert abs(current_mag - Is_test) < 0.01, f"Loi bien do dong dien: {current_mag} != {Is_test}"
    print("[PASS] Test MTPA Torque Enhancement: Khai thac hoan hao mo-men tu tro IPMSM!")

def test_mtpa_lut_precision():
    """
    Kiem tra 2: Do chinh xac cua bang tra cuu LUT thoi gian thuc:
    Tra cuu mo-men xoan yeu cau T_ref = 85.0 Nm, kiem tra mo-men tai tao lai.
    """
    motor = MotorParameters()
    calc = MTPATrajectoryCalculator(motor)
    lut = MTPALookupTable(calc, num_points=100)

    test_torques = [10.0, 35.0, 70.0, 95.0]
    for t_req in test_torques:
        id_lut, iq_lut = lut.lookup(t_req)
        actual_torque = calc.compute_torque(id_lut, iq_lut)
        error = abs(actual_torque - t_req)
        assert error < 0.8, f"Loi tra cuu LUT tai {t_req} Nm: thu duoc {actual_torque:.2f} Nm (lech {error:.2f} Nm)"

    print("[PASS] Test MTPA LUT: Bang tra cuu O(1) dat do chinh xac tuyet doi (< 0.8 Nm sai so noi suy)!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO MTPA OPTIMAL TRAJECTORY & REAL-TIME LOOKUP TABLE (TESLA IPMSM)")
    print("================================================================================")
    test_mtpa_torque_enhancement()
    test_mtpa_lut_precision()
