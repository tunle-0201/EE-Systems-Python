"""
Chuyen de AU: Tuong thich Dien tu EMC/EMI & Ky thuat Tiep dia PCB Toc do cao
Bai 132 (Milestone AU.1): Buc xa vi sai (Differential Mode) vs Buc xa dong pha (Common Mode)

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Hieu ro nguon goc vat ly buc xa dien tu truong vi sai va dong pha, tinh toan cuong do
          dien truong buc xa E tai 3m va 10m, so sanh voi chuan FCC Class B va CISPR 25 Class 5
          cho phan cung Apple Silicon va Tesla Autopilot FSD.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict


class EMCRadiationModel:
    """
    Mo hinh tinh toan cuong do dien truong buc xa vi sai (DM) va dong pha (CM).
    
    Phan tich toan hoc & vat ly buc xa:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   1. Buc xa Vi sai (Vong lap dong dien nho Loop Area A):│
    │                                                        │
    │                    f^2 * I_DM * A                      │
    │   E_DM (uV/m) = 1.316e-8 * ──────────────              │
    │                             r                          │
    │                                                        │
    │      A: Dien tich vong lap = Chieu dai * Khoang cach s │
    │      Buc xa ty le voi f^2 va dien tich vong lap A      │
    │                                                        │
    │   2. Buc xa Dong pha (Day cap chieu dai L lam anten):  │
    │                                                        │
    │                    f * I_CM * L                        │
    │   E_CM (uV/m) = 0.1257 * ──────────────                │
    │                           r                            │
    │                                                        │
    │      L: Chieu dai day cap ket noi                      │
    │      Chu y: 5 uA dong pha co the pham chuan FCC,       │
    │             trong khi can toi 20 mA dong vi sai!       │
    │                                                        │
    │   3. Chuyen doi sang don vi dB(uV/m):                  │
    │                                                        │
    │   E_dB = 20 * log10( E_uV/m )                          │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    @staticmethod
    def calculate_dm_field_uv_per_m(
        f_hz: float,
        i_dm_amps: float,
        loop_area_m2: float,
        distance_m: float = 3.0
    ) -> float:
        """
        Tinh cuong do dien truong buc xa vi sai E_DM (don vi uV/m).
        """
        if distance_m <= 0.0:
            raise ValueError("Khoang cach do r phai duong")
        # Hang so buc xa vi sai: 1.316e-8
        val = 1.316e-8 * (f_hz ** 2) * i_dm_amps * loop_area_m2 / distance_m
        return max(1e-6, val)

    @staticmethod
    def calculate_cm_field_uv_per_m(
        f_hz: float,
        i_cm_amps: float,
        cable_length_m: float,
        distance_m: float = 3.0
    ) -> float:
        """
        Tinh cuong do dien truong buc xa dong pha E_CM (don vi uV/m).
        """
        if distance_m <= 0.0:
            raise ValueError("Khoang cach do r phai duong")
        # Hang so buc xa dong pha: 0.1257
        val = 0.1257 * f_hz * i_cm_amps * cable_length_m / distance_m
        return max(1e-6, val)

    @staticmethod
    def field_to_dbuv_per_m(e_uv_per_m: float) -> float:
        """Chuyen doi tu uV/m sang dBuV/m."""
        return 20.0 * math.log10(max(1e-6, e_uv_per_m))


class RegulatoryLimits:
    """
    Cac duong gioi han chuan quoc te FCC Part 15 Class B va CISPR 25 Class 5.
    """
    @staticmethod
    def fcc_part15_class_b_limit_dbuv(f_hz: float, distance_m: float = 3.0) -> float:
        """
        Chuan FCC Part 15 Class B (Thiet bi dan dung / Apple) tai 3m.
        """
        f_mhz = f_hz / 1e6
        if f_mhz < 30.0:
            base_limit = 40.0
        elif 30.0 <= f_mhz < 88.0:
            base_limit = 40.0  # 100 uV/m = 40 dBuV/m
        elif 88.0 <= f_mhz < 216.0:
            base_limit = 43.5  # 150 uV/m = 43.5 dBuV/m
        elif 216.0 <= f_mhz < 960.0:
            base_limit = 46.0  # 200 uV/m = 46.0 dBuV/m
        else:
            base_limit = 54.0  # 500 uV/m = 54.0 dBuV/m

        # Neu do o khoang cach khac 3m, quy doi ty le 1/r (20 dB/decade)
        if distance_m != 3.0:
            base_limit += 20.0 * math.log10(3.0 / distance_m)

        return base_limit

    @staticmethod
    def cispr25_class5_radiated_limit_dbuv(f_hz: float) -> float:
        """
        Chuan CISPR 25 Class 5 (Thiet bi o to nghiem ngat nhat / Tesla) tai 1m.
        Dac biet nghiem ngat tai dai FM (76-108 MHz) de khong gay nhieu radio.
        """
        f_mhz = f_hz / 1e6
        if 30.0 <= f_mhz < 54.0:
            return 36.0
        elif 54.0 <= f_mhz < 70.0:
            return 30.0
        elif 76.0 <= f_mhz < 108.0:
            return 28.0  # Dai FM xe hoi cuc ky chat che
        elif 142.0 <= f_mhz < 175.0:
            return 26.0
        elif 200.0 <= f_mhz < 400.0:
            return 37.0
        elif 400.0 <= f_mhz < 1000.0:
            return 41.0
        else:
            return 45.0


class EMCRadiationAnalyzer:
    """
    Dong co phan tich pho buc xa, tinh toan Margin va canh bao vi pham chuan.
    """
    def __init__(self, target_standard: str = "FCC_Class_B", measurement_distance_m: float = 3.0):
        self.standard = target_standard
        self.distance_m = measurement_distance_m

    def evaluate_frequency_sweep(
        self,
        freq_list_hz: List[float],
        i_dm_amps: float,
        loop_area_m2: float,
        i_cm_amps: float,
        cable_length_m: float
    ) -> List[Dict[str, float]]:
        results = []
        for f in freq_list_hz:
            e_dm_uv = EMCRadiationModel.calculate_dm_field_uv_per_m(f, i_dm_amps, loop_area_m2, self.distance_m)
            e_cm_uv = EMCRadiationModel.calculate_cm_field_uv_per_m(f, i_cm_amps, cable_length_m, self.distance_m)

            # Tong cong cuong do dien truong (cong phan truong dien tong hop)
            e_total_uv = math.sqrt(e_dm_uv ** 2 + e_cm_uv ** 2)

            e_dm_db = EMCRadiationModel.field_to_dbuv_per_m(e_dm_uv)
            e_cm_db = EMCRadiationModel.field_to_dbuv_per_m(e_cm_uv)
            e_total_db = EMCRadiationModel.field_to_dbuv_per_m(e_total_uv)

            if self.standard == "FCC_Class_B":
                limit_db = RegulatoryLimits.fcc_part15_class_b_limit_dbuv(f, self.distance_m)
            else:
                limit_db = RegulatoryLimits.cispr25_class5_radiated_limit_dbuv(f)

            margin_db = limit_db - e_total_db
            is_pass = margin_db >= 0.0

            results.append({
                "frequency_hz": f,
                "e_dm_dbuv": e_dm_db,
                "e_cm_dbuv": e_cm_db,
                "e_total_dbuv": e_total_db,
                "limit_dbuv": limit_db,
                "margin_db": margin_db,
                "is_pass": is_pass
            })
        return results


def test_emc_radiation():
    print("================================================================================")
    print("TEST SUITE: BUC XA DIEN TU TRUONG VI SAI VS DONG PHA VA CHUAN FCC/CISPR")
    print("================================================================================")

    # 1. Kiem tra tinh chat nhay cam: 5 uA dong pha vs 20 mA dong vi sai o 100 MHz
    f_test = 100e6  # 100 MHz
    r_test = 3.0    # 3m
    cable_len = 1.0 # 1m
    loop_area = 5e-5 # 5 cm x 1 mm = 50 mm^2 = 5e-5 m^2 (vong vi sai tren PCB)

    # Tinh buc xa cua 20 mA dong vi sai
    i_dm = 0.020  # 20 mA
    e_dm_uv = EMCRadiationModel.calculate_dm_field_uv_per_m(f_test, i_dm, loop_area, r_test)
    e_dm_db = EMCRadiationModel.field_to_dbuv_per_m(e_dm_uv)

    # Tinh buc xa cua chi 35 uA dong pha (so voi 20 mA dong vi sai)
    i_cm = 35.0e-6  # 35 uA
    e_cm_uv = EMCRadiationModel.calculate_cm_field_uv_per_m(f_test, i_cm, cable_len, r_test)
    e_cm_db = EMCRadiationModel.field_to_dbuv_per_m(e_cm_uv)

    fcc_limit = RegulatoryLimits.fcc_part15_class_b_limit_dbuv(f_test, r_test)

    print(f"[1] So sanh muc do buc xa tai 100 MHz (Khoang cach 3m, Gioi han FCC = {fcc_limit:.1f} dBuV/m):")
    print(f"    - Dong vi sai I_DM = 20 mA (Vong lap {loop_area*1e6:.0f} mm2): E_DM = {e_dm_db:.2f} dBuV/m")
    print(f"    - Dong dong pha I_CM = 35 uA (Day cap {cable_len:.1f} m):      E_CM = {e_cm_db:.2f} dBuV/m")
    
    # Chung minh: Chi 35 uA dong pha da dat xap xi nguong gioi han 43.5 dBuV/m cua FCC!
    assert abs(e_cm_db - 43.3) < 1.0, "Buc xa dong pha phai xap xi 43.3 dBuV/m"
    assert e_dm_db < 35.0, "Buc xa vi sai vong nho phai thap hon dang ke"
    print("    -> Ket luan vang: Buc xa dong pha nguy hiem hon hang ngan lan so voi vi sai!")

    # 2. Kiem tra quet dai tan so voi thiet ke toi uu Apple Silicon (vong lap nho, I_CM duoc loc tot)
    analyzer_apple = EMCRadiationAnalyzer(target_standard="FCC_Class_B", measurement_distance_m=3.0)
    freqs = [50e6, 100e6, 200e6, 400e6, 800e6]
    sweep_clean = analyzer_apple.evaluate_frequency_sweep(
        freq_list_hz=freqs,
        i_dm_amps=0.010,       # 10 mA
        loop_area_m2=5e-6,     # 5 mm2 (PCB 4 lop voi lop ground lien ke sat trace 0.1mm)
        i_cm_amps=1.0e-6,      # 1 uA (co cuon cam loc CMC)
        cable_length_m=0.5     # Cap USB-C ngan 0.5m
    )

    print(f"\n[2] Kiem tra quet dai tan so bo mach Apple Silicon voi cap USB-C:")
    all_pass = True
    for pt in sweep_clean:
        print(f"    f = {pt['frequency_hz']/1e6:5.1f} MHz | E_total = {pt['e_total_dbuv']:5.1f} dBuV/m | Limit = {pt['limit_dbuv']:5.1f} dBuV/m | Margin = {pt['margin_db']:5.1f} dB | Pass={pt['is_pass']}")
        if not pt['is_pass']:
            all_pass = False

    assert all_pass is True, "Bo mach duoc toi uu phai PASS 100% chuan FCC Class B"

    # 3. Kiem tra tinh huong vi pham CISPR 25 Class 5 cua xe dien Tesla do ranh Ground bi cat
    analyzer_tesla = EMCRadiationAnalyzer(target_standard="CISPR_25_Class_5", measurement_distance_m=1.0)
    # Ranh bi cat lam loop area tang len 500 mm2 va dong pha tang len 25 uA
    sweep_faulty = analyzer_tesla.evaluate_frequency_sweep(
        freq_list_hz=[80e6, 100e6], # Dai FM
        i_dm_amps=0.030,
        loop_area_m2=5e-4,    # 500 mm2
        i_cm_amps=25.0e-6,    # 25 uA
        cable_length_m=1.5    # Day harness o to 1.5m
    )
    print(f"\n[3] Kiem tra bo mach loi tao nhieu tren dai FM xe hoi Tesla (CISPR 25 Class 5):")
    fm_pt = sweep_faulty[1] # 100 MHz
    print(f"    f = 100 MHz | E_total = {fm_pt['e_total_dbuv']:.1f} dBuV/m | Limit = {fm_pt['limit_dbuv']:.1f} dBuV/m | Margin = {fm_pt['margin_db']:.1f} dB")
    assert fm_pt['is_pass'] is False, "Bo mach loi phai FAIL chuan CISPR 25 Class 5 o dai FM"
    print("    -> Phat hien FAIL chuan CISPR 25 chinh xac!")

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AU.1 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_emc_radiation()
