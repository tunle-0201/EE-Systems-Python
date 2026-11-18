"""
================================================================================
CHUYEN DE AG: HARDWARE MOTOR FIELD WEAKENING & OVERMODULATION (FW & OVM)
BAI 3: THUAT TOAN QUA DIEU CHE SPACE VECTOR OVERMODULATION (OVM1 & OVM2 SIX-STEP)
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Vay muon them 15.5% dien ap pin de but toc Launch Mode tren Tesla Plaid
Ngon ngu: Python 3 thuan tuy, hinh hoc luc giac bien tan & bien doi goc pha
================================================================================
"""

import math
from typing import Tuple, Dict, List

# ------------------------------------------------------------------------------
# 1. CAC THONG SO HINH HOC LUC GIAC BIEN TAN (INVERTER VOLTAGE HEXAGON)
# ------------------------------------------------------------------------------

class HexagonGeometry:
    """
    Hinh hoc luc giac dien ap bien tan 3 pha:
    - Vdc: Dien ap pin DC-link (Volt)
    - V_lin_max: Ban kinh vong tron noi tiep (Gioi han tuyen tinh):
      V_lin_max = Vdc / sqrt(3) ~ 0.5774 * Vdc
    - V_six_step: Dien ap song co ban che do Sau buoc (Six-step):
      V_six_step = (2 / pi) * Vdc ~ 0.6366 * Vdc (~ 1.1027 * V_lin_max)
    """
    def __init__(self, Vdc: float = 400.0):
        self.Vdc = Vdc
        self.V_lin_max = Vdc / math.sqrt(3.0)   # 230.94 V
        self.V_vertex = (2.0 / 3.0) * Vdc       # 266.67 V (Ban kinh dinh luc giac)
        self.V_six_step = (2.0 / math.pi) * Vdc # 254.65 V

    def get_hexagon_boundary(self, theta_in_sector: float) -> float:
        """
        Khoang cach tu tam luc giac toi canh luc giac tai goc theta (trong khoang [0, pi/3]):
        V_bound(theta) = (Vdc / sqrt(3)) / cos(theta - pi/6)
        """
        phi = theta_in_sector - (math.pi / 6.0)
        return self.V_lin_max / math.cos(phi)

# ------------------------------------------------------------------------------
# 2. BO QUA DIEU CHE SPACE VECTOR OVERMODULATION (OVM1 & OVM2)
# ------------------------------------------------------------------------------

class SpaceVectorOvermodulator:
    """
    Bo xu ly qua dieu che SVPWM:
    - Vung 1 (Tuyen tinh Linear): Mi <= 1.0 -> Giu nguyen vector goc va do lon.
    - Vung 2 (Overmodulation Mode 1 - OVM1): 1.0 < Mi <= 1.05:
      Co ngan vector cham dung canh luc giac (Magnitude Scaling), giu nguyen goc pha.
    - Vung 3 (Overmodulation Mode 2 - OVM2): 1.05 < Mi <= 1.155:
      Bien doi ca bien do va goc pha (Angle Modification), don vector vao 6 dinh luc giac.
    - Vung 4 (Six-step Mode): Mi >= 1.155 -> Khoa vector tai 6 dinh luc giac.
    """
    def __init__(self, geom: HexagonGeometry):
        self.geom = geom

    def process_voltage_vector(self,
                               v_alpha: float,
                               v_beta: float) -> Tuple[float, float, str]:
        """
        Dau vao: Vector dien ap (v_alpha, v_beta) do bo dieu khien FOC yeu cau.
        Tra ve: (v_alpha_mod, v_beta_mod, mode_str) sau khi xu ly qua dieu che.
        """
        # Tinh bien do va goc pha trong he toa do cuc
        v_mag = math.sqrt(v_alpha * v_alpha + v_beta * v_beta)
        if v_mag < 1e-6:
            return (0.0, 0.0, "LINEAR")

        theta = math.atan2(v_beta, v_alpha)
        if theta < 0.0:
            theta += 2.0 * math.pi

        # Xac dinh Sector (1 den 6) va goc cuc bo trong Sector [0, pi/3]
        sector = int(theta / (math.pi / 3.0)) # 0 den 5
        sector_base_angle = sector * (math.pi / 3.0)
        theta_local = theta - sector_base_angle

        # He so dieu che Mi = V_mag / V_lin_max
        Mi = v_mag / self.geom.V_lin_max

        # --- CHE DO 1: VUNG TUYEN TINH (LINEAR ZONE, Mi <= 1.0) ---
        if Mi <= 1.0:
            return (v_alpha, v_beta, "LINEAR")

        # Canh luc giac tai goc theta_local
        v_boundary = self.geom.get_hexagon_boundary(theta_local)

        # --- CHE DO 2: OVERMODULATION MODE 1 (1.0 < Mi <= 1.05) ---
        if Mi <= 1.05:
            # Neu vector nam ngoai bien luc giac thi co ngan ve bien, giu nguyen goc theta
            if v_mag > v_boundary:
                v_mag_mod = v_boundary
            else:
                v_mag_mod = v_mag
            theta_mod = theta
            mode_str = "OVM1"

        # --- CHE DO 3: OVERMODULATION MODE 2 (1.05 < Mi < 1.155) ---
        elif Mi < 1.155:
            # Tinh goc giu dinh (Holding Angle alpha_h): Tang dan tu 0 den pi/6 khi Mi tang tu 1.05 den 1.155
            progress = (Mi - 1.05) / (1.155 - 1.05)
            alpha_h = progress * (math.pi / 6.0)

            # Don goc ve cac dinh:
            # Goc dinh gan nhat la 0 hoac pi/3
            if theta_local < alpha_h:
                # Don ve dinh dau sector (theta_local = 0)
                theta_local_mod = 0.0
                v_mag_mod = self.geom.V_vertex
            elif theta_local > (math.pi / 3.0 - alpha_h):
                # Don ve dinh cuoi sector (theta_local = pi/3)
                theta_local_mod = math.pi / 3.0
                v_mag_mod = self.geom.V_vertex
            else:
                # O giua: Bam theo canh luc giac
                theta_local_mod = theta_local
                v_mag_mod = self.geom.get_hexagon_boundary(theta_local_mod)

            theta_mod = sector_base_angle + theta_local_mod
            mode_str = "OVM2"

        # --- CHE DO 4: SIX-STEP (Mi >= 1.155) ---
        else:
            # Khoa hoan toan tai dinh gan nhat cua sector
            if theta_local < (math.pi / 6.0):
                theta_local_mod = 0.0
            else:
                theta_local_mod = math.pi / 3.0
            v_mag_mod = self.geom.V_vertex
            theta_mod = sector_base_angle + theta_local_mod
            mode_str = "SIX_STEP"

        # Chuyen nguoc ve toa do alpha-beta
        v_alpha_mod = v_mag_mod * math.cos(theta_mod)
        v_beta_mod = v_mag_mod * math.sin(theta_mod)

        return (v_alpha_mod, v_beta_mod, mode_str)

# ------------------------------------------------------------------------------
# 3. MO PHONG VA KIEM CHUNG TANG TRUONG DIEN AP KHAI THAC
# ------------------------------------------------------------------------------

def test_overmodulation_modes():
    """
    Kiem tra 1: Xu ly vector qua 4 che do (LINEAR, OVM1, OVM2, SIX_STEP).
    """
    geom = HexagonGeometry(Vdc=400.0)
    ovm = SpaceVectorOvermodulator(geom)

    # 1. Test Linear: Mi = 0.8
    v_lin = geom.V_lin_max * 0.8
    va, vb, mode = ovm.process_voltage_vector(v_lin, 0.0)
    assert mode == "LINEAR", f"Loi: Phai la LINEAR, thu duoc {mode}"
    assert abs(math.sqrt(va*va + vb*vb) - v_lin) < 1e-4

    # 2. Test OVM1: Mi = 1.03
    v_ovm1 = geom.V_lin_max * 1.03
    # Huong 30 do (pi/6) noi khoang cach den bien la nho nhat (V_lin_max = 230.94V)
    va, vb, mode = ovm.process_voltage_vector(v_ovm1 * math.cos(math.pi/6), v_ovm1 * math.sin(math.pi/6))
    assert mode == "OVM1", f"Loi: Phai la OVM1, thu duoc {mode}"
    # Do o 30 do, bien luc giac dung bang V_lin_max, nen vector phai bi co ngan ve V_lin_max
    v_res = math.sqrt(va*va + vb*vb)
    assert abs(v_res - geom.V_lin_max) < 1e-3, f"Loi OVM1 co ngan: {v_res} != {geom.V_lin_max}"

    # 3. Test OVM2: Mi = 1.10
    v_ovm2 = geom.V_lin_max * 1.10
    va, vb, mode = ovm.process_voltage_vector(v_ovm2 * math.cos(0.05), v_ovm2 * math.sin(0.05))
    assert mode == "OVM2", f"Loi: Phai la OVM2, thu duoc {mode}"

    # 4. Test SIX_STEP: Mi = 1.20
    v_six = geom.V_lin_max * 1.20
    va, vb, mode = ovm.process_voltage_vector(v_six * math.cos(0.1), v_six * math.sin(0.1))
    assert mode == "SIX_STEP", f"Loi: Phai la SIX_STEP, thu duoc {mode}"
    v_res_six = math.sqrt(va*va + vb*vb)
    assert abs(v_res_six - geom.V_vertex) < 1e-3, f"Loi SIX_STEP vertex: {v_res_six} != {geom.V_vertex}"

    print("[PASS] Test 1: 4 che do dieu che (LINEAR, OVM1, OVM2, SIX_STEP) hoat dong hoan hao!")

def test_voltage_utilization_boost():
    """
    Kiem tra 2: Do tang dien ap khai thac duoc tu pin:
    So sanh bien do trung binh chu ky giua Linear Limit va Six-Step Mode.
    """
    geom = HexagonGeometry(Vdc=400.0)
    ovm = SpaceVectorOvermodulator(geom)

    # Quet 360 do voi vector yeu cau cuc dai
    num_samples = 360
    sum_v_mag_ovm = 0.0

    for deg in range(num_samples):
        rad = math.radians(deg)
        v_req_mag = geom.V_lin_max * 1.20 # Yeu cau vuot nguong 20%
        va_raw = v_req_mag * math.cos(rad)
        vb_raw = v_req_mag * math.sin(rad)

        va_mod, vb_mod, _ = ovm.process_voltage_vector(va_raw, vb_raw)
        sum_v_mag_ovm += math.sqrt(va_mod * va_mod + vb_mod * vb_mod)

    avg_v_ovm = sum_v_mag_ovm / num_samples
    voltage_boost_percent = ((avg_v_ovm - geom.V_lin_max) / geom.V_lin_max) * 100.0

    print("--------------------------------------------------------------------------------")
    print(f"KHAI THAC DIEN AP PIN QUA OVERMODULATION (Vdc = {geom.Vdc:.1f} V):")
    print(f"-> Gioi han tuyen tinh V_lin_max : {geom.V_lin_max:.2f} V (100.0%)")
    print(f"-> Dien ap trung binh Overmodulation: {avg_v_ovm:.2f} V")
    print(f"-> Ty le dien ap tang them tu pin  : +{voltage_boost_percent:.2f}% (Tang cong suat dinh dong co!)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # Dien ap khai thac duoc phai tang them tu +10% den +16% so voi gioi han tuyen tinh
    assert 10.0 <= voltage_boost_percent <= 16.0, f"Loi: Ty le tang dien ap khong hop ly: {voltage_boost_percent:.2f}%"
    print("[PASS] Test 2: Overmodulation giup tang +15.5% dien ap dinh cho che do but toc Launch Mode!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO SPACE VECTOR OVERMODULATION (OVM1, OVM2 & SIX-STEP TRANSITION)")
    print("================================================================================")
    test_overmodulation_modes()
    test_voltage_utilization_boost()
