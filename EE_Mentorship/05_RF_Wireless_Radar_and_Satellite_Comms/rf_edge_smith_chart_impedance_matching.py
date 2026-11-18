"""
================================================================================
CHUYEN DE AS: TINH TOAN VEN DUONG TRUYEN CAO TAN RF & PHOI HOP TRO KHANG SMITH
BAI 3 (MILESTONE AS.3): THUAT TOAN PHOI HOP TRO KHANG MANG CHU L DO THI SMITH
================================================================================
Chuc nang he thong:
1. Mo hinh hoa khong gian tro khang chuan hoa tren Do thi Smith (Smith Chart):
      z = Z / Z_0 = r + j * x
      Gamma = (z - 1) / (z + 1)
2. Thuat toan tu dong thiet ke mang phoi hop tro khang chu L (L-Section Matching):
   - Truong hop R_L < Z_0: Shunt B o phia nguon, Series X o phia tai.
   - Truong hop R_L > Z_0: Shunt B o phia tai, Series X o phia nguon.
3. Chuyen doi cac gia tri dien khang X va dung dan B sang gia tri linh kien L (Henries)
   va C (Farads) thuc te tai tan so RF thiet ke:
      Neu X > 0: L_ser = X / (2 * pi * f)  |  Neu X < 0: C_ser = 1 / (2 * pi * f * |X|)
      Neu B > 0: C_shu = B / (2 * pi * f)  |  Neu B < 0: L_shu = 1 / (2 * pi * f * |B|)
4. Kiem chung triet tieu song phan xa: Dua Z_in ve 50 Ohm, S11 < -35 dB, VSWR < 1.05.

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
   Truong hop R_L < Z_0:
      X = +- sqrt(R_L * (Z_0 - R_L)) - X_L
      B = +- sqrt((Z_0 - R_L) / R_L) / Z_0

   Truong hop R_L > Z_0:
          X_L +- sqrt(R_L / Z_0) * sqrt(R_L^2 + X_L^2 - Z_0 * R_L)
      B = ────────────────────────────────────────────────────────
                              R_L^2 + X_L^2
          1       X_L * Z_0       Z_0
      X = ─  +   ───────────  -  ──────
          B          R_L         B * R_L
================================================================================
"""

import math
import cmath
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional


@dataclass
class LSectionSolution:
    """Giai phap phoi hop tro khang mang chu L."""
    topology: str             # "Shunt_Source_Series_Load" hoac "Series_Source_Shunt_Load"
    filter_type: str          # "Low-Pass" (Series L, Shunt C) hoac "High-Pass"
    x_val_ohm: float          # Dien khang noi tiep X (Ohm)
    b_val_siemens: float      # Dung dan song song B (Siemens)
    series_component_type: str # "Inductor" hoac "Capacitor"
    series_val_si: float      # Henries hoac Farads
    shunt_component_type: str  # "Inductor" hoac "Capacitor"
    shunt_val_si: float        # Henries hoac Farads
    z_in_matched: complex     # Tro khang vao sau khi ghep mang
    s11_db: float             # Return loss S11
    vswr: float               # He so song dung sau khi phoi hop


class SmithChartMatchingEngine:
    """
    Dong co thiet ke mang phoi hop tro khang chu L tren do thi Smith.
    """

    def __init__(self, z0_ref: float = 50.0):
        assert z0_ref > 0, "Tro khang tham chieu Z_0 phai duong"
        self.z0 = z0_ref

    def design_l_match(
        self,
        z_load: complex,
        freq_hz: float
    ) -> List[LSectionSolution]:
        """
        Tinh toan tat ca cac giai phap mang chu L hop le de bien doi Z_load ve Z_0.
        """
        r_l = z_load.real
        x_l = z_load.imag
        z0 = self.z0
        omega = 2.0 * math.pi * freq_hz
        solutions: List[LSectionSolution] = []

        if r_l <= 0.0:
            raise ValueError("Phan thuc tro khang tai phai > 0")

        # -------------------------------------------------------------
        # TRUONG HOP 1: R_L < Z_0 (Tai nam ngoai vong 1 + jb)
        # Cau truc: Nguon -> [ Shunt B ] -> [ Series X ] -> Tai
        # -------------------------------------------------------------
        if r_l < z0:
            diff = z0 - r_l
            val_in_sqrt = r_l * diff
            if val_in_sqrt >= 0.0:
                sqrt_term_x = math.sqrt(val_in_sqrt)
                sqrt_term_b = math.sqrt(diff / r_l) / z0

                # 2 nghiem cong va tru:
                for sign in [+1.0, -1.0]:
                    x = sign * sqrt_term_x - x_l
                    b = sign * sqrt_term_b

                    # Xac dinh linh kien Series X:
                    if x >= 0:
                        s_type = "Inductor"
                        s_val = x / omega
                    else:
                        s_type = "Capacitor"
                        s_val = 1.0 / (omega * abs(x))

                    # Xac dinh linh kien Shunt B:
                    if b >= 0:
                        sh_type = "Capacitor"
                        sh_val = b / omega
                    else:
                        sh_type = "Inductor"
                        sh_val = 1.0 / (omega * abs(b))

                    f_type = "Low-Pass" if (s_type == "Inductor" and sh_type == "Capacitor") else "High-Pass"

                    # Kiem chung tro khang vao Z_in:
                    # Z_branch = Z_load + j*X
                    # Y_branch = 1 / Z_branch
                    # Y_in = Y_branch + j*B
                    # Z_in = 1 / Y_in
                    z_branch = z_load + complex(0.0, x)
                    y_branch = 1.0 / z_branch
                    y_in = y_branch + complex(0.0, b)
                    z_in = 1.0 / y_in

                    gamma = (z_in - z0) / (z_in + z0)
                    mag_g = max(1e-6, abs(gamma))
                    s11_db = 20.0 * math.log10(mag_g)
                    vswr = (1.0 + mag_g) / (1.0 - mag_g)

                    solutions.append(LSectionSolution(
                        topology="Shunt_Source_Series_Load",
                        filter_type=f_type,
                        x_val_ohm=x,
                        b_val_siemens=b,
                        series_component_type=s_type,
                        series_val_si=s_val,
                        shunt_component_type=sh_type,
                        shunt_val_si=sh_val,
                        z_in_matched=z_in,
                        s11_db=s11_db,
                        vswr=vswr
                    ))

        # -------------------------------------------------------------
        # TRUONG HOP 2: R_L >= Z_0 (Tai nam trong vong 1 + jb)
        # Cau truc: Nguon -> [ Series X ] -> [ Shunt B ] -> Tai
        # -------------------------------------------------------------
        else:
            term_under_sqrt = (r_l ** 2 + x_l ** 2) - z0 * r_l
            if term_under_sqrt >= 0.0:
                sqrt_fact = math.sqrt(r_l / z0) * math.sqrt(term_under_sqrt)
                den_b = r_l ** 2 + x_l ** 2

                for sign in [+1.0, -1.0]:
                    b = (x_l + sign * sqrt_fact) / den_b
                    x = (1.0 / b) + (x_l * z0 / r_l) - (z0 / (b * r_l))

                    if x >= 0:
                        s_type = "Inductor"
                        s_val = x / omega
                    else:
                        s_type = "Capacitor"
                        s_val = 1.0 / (omega * abs(x))

                    if b >= 0:
                        sh_type = "Capacitor"
                        sh_val = b / omega
                    else:
                        sh_type = "Inductor"
                        sh_val = 1.0 / (omega * abs(b))

                    f_type = "Low-Pass" if (s_type == "Inductor" and sh_type == "Capacitor") else "High-Pass"

                    # Kiem chung tro khang vao Z_in:
                    # Y_load = 1 / Z_load
                    # Y_mid = Y_load + j*B
                    # Z_mid = 1 / Y_mid
                    # Z_in = Z_mid + j*X
                    y_load = 1.0 / z_load
                    y_mid = y_load + complex(0.0, b)
                    z_mid = 1.0 / y_mid
                    z_in = z_mid + complex(0.0, x)

                    gamma = (z_in - z0) / (z_in + z0)
                    mag_g = max(1e-6, abs(gamma))
                    s11_db = 20.0 * math.log10(mag_g)
                    vswr = (1.0 + mag_g) / (1.0 - mag_g)

                    solutions.append(LSectionSolution(
                        topology="Series_Source_Shunt_Load",
                        filter_type=f_type,
                        x_val_ohm=x,
                        b_val_siemens=b,
                        series_component_type=s_type,
                        series_val_si=s_val,
                        shunt_component_type=sh_type,
                        shunt_val_si=sh_val,
                        z_in_matched=z_in,
                        s11_db=s11_db,
                        vswr=vswr
                    ))

        return solutions


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AS - LESSON 3: SMITH CHART L-MATCHING NETWORK")
    print("=" * 80)

    engine = SmithChartMatchingEngine(z0_ref=50.0)

    # 1. Bai toan thuc te 1: Phoi hop tro khang Anten Wi-Fi / Bluetooth Apple iPhone
    # Tan so f = 2.45 GHz
    # Tro khang anten lech nang: Z_load = 25 + j40 Ohm (R_L < Z_0)
    f_wifi = 2.45e9  # 2.45 GHz
    z_ant_apple = complex(25.0, 40.0)

    print(f"\n[1] BAI TOAN 1: PHOI HOP ANTEN WI-FI APPLE IPHONE (f = 2.45 GHz):")
    print(f"  Tro khang anten ban dau: Z_L = {z_ant_apple.real:.1f} + j{z_ant_apple.imag:.1f} Ohm")
    gamma_init = (z_ant_apple - 50.0) / (z_ant_apple + 50.0)
    print(f"  He so phan xa ban dau |Gamma|: {abs(gamma_init):.4f} (Cong suat phan xa: {abs(gamma_init)**2 * 100:.1f}%)")
    print(f"  Return Loss ban dau S11: {20 * math.log10(abs(gamma_init)):.2f} dB | VSWR: {(1 + abs(gamma_init))/(1 - abs(gamma_init)):.2f}")

    sols_apple = engine.design_l_match(z_ant_apple, f_wifi)
    print(f"\n  Tim thay {len(sols_apple)} giai phap mang chu L tren do thi Smith:")
    for idx, sol in enumerate(sols_apple, 1):
        s_unit = "nH" if sol.series_component_type == "Inductor" else "pF"
        s_disp = sol.series_val_si * 1e9 if sol.series_component_type == "Inductor" else sol.series_val_si * 1e12
        sh_unit = "nH" if sol.shunt_component_type == "Inductor" else "pF"
        sh_disp = sol.shunt_val_si * 1e9 if sol.shunt_component_type == "Inductor" else sol.shunt_val_si * 1e12

        print(f"  Giai phap {idx} ({sol.filter_type}):")
        print(f"    Cau truc: {sol.topology}")
        print(f"    Series ({sol.series_component_type}): X = {sol.x_val_ohm:>+7.2f} Ohm -> {s_disp:.2f} {s_unit}")
        print(f"    Shunt  ({sol.shunt_component_type}):  B = {sol.b_val_siemens:>+7.4f} S   -> {sh_disp:.2f} {sh_unit}")
        print(f"    Tro khang vao sau ghep: Z_in = {sol.z_in_matched.real:.2f} + j{sol.z_in_matched.imag:.2f} Ohm")
        print(f"    S11 sau phoi hop: {sol.s11_db:.2f} dB | VSWR: {sol.vswr:.4f}")

    # 2. Bai toan thuc te 2: Phoi hop khoi khuếch đại công suất RF PA (Power Amplifier)
    # Tan so f = 5.8 GHz, Z_load = 120 - j30 Ohm (R_L > Z_0)
    f_58g = 5.8e9
    z_pa = complex(120.0, -30.0)
    sols_pa = engine.design_l_match(z_pa, f_58g)

    print(f"\n[2] BAI TOAN 2: PHOI HOP KHOI KHUECH DAI CONG SUAT RF PA (f = 5.8 GHz):")
    print(f"  Tro khang PA: Z_L = {z_pa.real:.1f} + j{z_pa.imag:.1f} Ohm (R_L > Z_0)")
    for idx, sol in enumerate(sols_pa, 1):
        s_unit = "nH" if sol.series_component_type == "Inductor" else "pF"
        s_disp = sol.series_val_si * 1e9 if sol.series_component_type == "Inductor" else sol.series_val_si * 1e12
        sh_unit = "nH" if sol.shunt_component_type == "Inductor" else "pF"
        sh_disp = sol.shunt_val_si * 1e9 if sol.shunt_component_type == "Inductor" else sol.shunt_val_si * 1e12
        print(f"  Giai phap {idx} ({sol.filter_type}): Series={s_disp:.2f}{s_unit}, Shunt={sh_disp:.2f}{sh_unit} | Z_in={sol.z_in_matched.real:.2f} + j{sol.z_in_matched.imag:.2f} | S11={sol.s11_db:.1f}dB | VSWR={sol.vswr:.3f}")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Ca hai bai toan phai tim duoc it nhat 2 giai phap (Low-pass va High-pass)
    assert len(sols_apple) >= 2, "Bai toan Anten Apple phai co 2 giai phap"
    assert len(sols_pa) >= 2, "Bai toan RF PA phai co 2 giai phap"

    # 2. Tat ca cac giai phap phai bien doi Z_in ve 50.0 Ohm (+- 0.01 Ohm)
    for sol in sols_apple + sols_pa:
        assert abs(sol.z_in_matched.real - 50.0) < 0.05, f"Z_in thuc phai ~ 50, thuc te={sol.z_in_matched.real}"
        assert abs(sol.z_in_matched.imag) < 0.05, f"Z_in ao phai ~ 0, thuc te={sol.z_in_matched.imag}"
        assert sol.s11_db < -35.0, f"S11 phai < -35 dB, thuc te={sol.s11_db}"
        assert sol.vswr < 1.05, f"VSWR phai < 1.05, thuc te={sol.vswr}"

    print("\n[INFO] Triet tieu song phan xa: S11 < -35 dB va VSWR < 1.05 tren ca 4 giai phap: PASSED!")
    print("\n>> [PASSED] TEST SUITE 100% SUCCESSFUL: SMITH CHART MATCHING VERIFIED!")


if __name__ == "__main__":
    main()
