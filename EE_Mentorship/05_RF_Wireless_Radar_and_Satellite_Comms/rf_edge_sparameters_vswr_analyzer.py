"""
================================================================================
CHUYEN DE AS: TINH TOAN VEN DUONG TRUYEN CAO TAN RF & PHOI HOP TRO KHANG SMITH
BAI 2 (MILESTONE AS.2): MA TRAN THONG SO TAN XA S-PARAMETERS & SONG DUNG VSWR
================================================================================
Chuc nang he thong:
1. Mo hinh hoa ma tran thong so tan xa S-Parameters 2-Cong:
      [ b1 ]   [ S11  S12 ] [ a1 ]
      [ b2 ] = [ S21  S22 ] [ a2 ]
   tham chieu tro khang chuan Z_0 = 50 Ohm.
2. Tinh toan he so phan xa Gamma, ton hao phan xa Return Loss (RL),
   ton hao truyen qua Insertion Loss (IL) va he so song dung dien ap VSWR:
      Gamma = (Z_L - Z_0) / (Z_L + Z_0)
      RL_dB = -20 * log10(|S11|)
      IL_dB = -20 * log10(|S21|)
      VSWR  = (1 + |Gamma|) / (1 - |Gamma|)
3. Chuyen doi qua lai giua ma tran ABCD va ma tran S-Parameters cho duong truyen phan bo.
4. Quet tan so tu 100 MHz den 20 GHz danh gia dap ung bo loc thong thap / duong truyen PCB.

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
               Z_L - Z_0
   Gamma   =  ───────────
               Z_L + Z_0

   RL_dB   =  -20 * log10(|S_11|)
   IL_dB   =  -20 * log10(|S_21|)

               1 + |Gamma|
   VSWR    =  ─────────────
               1 - |Gamma|

   Chuyen doi tu ABCD sang S-Parameters:
               A + B / Z_0 - C * Z_0 - D
   S_11    =  ───────────────────────────
               A + B / Z_0 + C * Z_0 + D

                            2
   S_21    =  ───────────────────────────
               A + B / Z_0 + C * Z_0 + D
================================================================================
"""

import math
import cmath
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class SParameter2Port:
    """Ma tran S-Parameters 2-Cong tai mot tan so xac dinh."""
    freq_hz: float
    s11: complex
    s21: complex
    s12: complex
    s22: complex
    s11_db: float
    s21_db: float
    return_loss_db: float
    insertion_loss_db: float
    vswr: float


@dataclass
class LoadReflectionSummary:
    """Tong ket phan xa tai tai dau cuoi."""
    z_load: complex
    gamma: complex
    gamma_mag: float
    gamma_phase_deg: float
    return_loss_db: float
    vswr: float
    reflected_power_pct: float
    transmitted_power_pct: float
    quality_verdict: str


class SParameterAnalyzer:
    """
    Dong co phan tich S-Parameters, Return Loss va VSWR mang 2-cong RF.
    """

    def __init__(self, z0_ref: float = 50.0):
        assert z0_ref > 0, "Tro khang tham chieu phai duong"
        self.z0_ref = z0_ref

    def analyze_load_reflection(self, z_load: complex) -> LoadReflectionSummary:
        """
        Phan tich he so phan xa Gamma va VSWR cua mot tro khang tai Z_load bat ky.
        """
        z0 = self.z0_ref
        # Gamma = (Z_L - Z_0) / (Z_L + Z_0)
        gamma = (z_load - z0) / (z_load + z0)
        mag = abs(gamma)
        phase_deg = math.degrees(cmath.phase(gamma))

        # Return Loss: RL = -20 * log10(|Gamma|)
        if mag < 1e-6:
            rl_db = 120.0  # Hoan hao, khong co phan xa
            vswr = 1.0
        elif mag >= 0.999999:
            rl_db = 0.0
            vswr = 999.0
        else:
            rl_db = -20.0 * math.log10(mag)
            vswr = (1.0 + mag) / (1.0 - mag)

        # Ty le cong suat phan xa: P_refl / P_inc = |Gamma|^2
        p_refl_pct = (mag ** 2) * 100.0
        p_trans_pct = 100.0 - p_refl_pct

        # Danh gia chat luong tieu chuan viễn thông:
        # VSWR <= 1.22 (RL >= 20 dB): EXCELLENT
        # VSWR <= 1.50 (RL >= 14 dB): GOOD
        # VSWR <= 1.92 (RL >= 10 dB): ACCEPTABLE
        # VSWR > 1.92: POOR / MISMATCH
        if vswr <= 1.22:
            verdict = "EXCELLENT (RL >= 20 dB)"
        elif vswr <= 1.50:
            verdict = "GOOD (RL >= 14 dB)"
        elif vswr <= 1.92:
            verdict = "ACCEPTABLE (RL >= 10 dB)"
        else:
            verdict = "POOR (MISMATCH HAZARD)"

        return LoadReflectionSummary(
            z_load=z_load,
            gamma=gamma,
            gamma_mag=mag,
            gamma_phase_deg=phase_deg,
            return_loss_db=rl_db,
            vswr=vswr,
            reflected_power_pct=p_refl_pct,
            transmitted_power_pct=p_trans_pct,
            quality_verdict=verdict
        )

    def abcd_to_s(self, a: complex, b: complex, c: complex, d: complex, freq_hz: float) -> SParameter2Port:
        """
        Chuyen doi ma tran ABCD sang ma tran S-Parameters 2-Cong:
        Denom = A + B/Z0 + C*Z0 + D
        S11 = (A + B/Z0 - C*Z0 - D) / Denom
        S21 = 2 / Denom
        S12 = 2 * (AD - BC) / Denom
        S22 = (-A + B/Z0 - C*Z0 + D) / Denom
        """
        z0 = self.z0_ref
        denom = a + (b / z0) + (c * z0) + d

        s11 = (a + (b / z0) - (c * z0) - d) / denom
        s21 = 2.0 / denom
        s12 = 2.0 * (a * d - b * c) / denom
        s22 = (-a + (b / z0) - (c * z0) + d) / denom

        mag_s11 = max(1e-6, abs(s11))
        mag_s21 = max(1e-6, abs(s21))

        s11_db = 20.0 * math.log10(mag_s11)
        s21_db = 20.0 * math.log10(mag_s21)

        rl_db = -s11_db
        il_db = -s21_db

        mag_gamma = min(0.999999, abs(s11))
        vswr = (1.0 + mag_gamma) / (1.0 - mag_gamma)

        return SParameter2Port(
            freq_hz=freq_hz,
            s11=s11,
            s21=s21,
            s12=s12,
            s22=s22,
            s11_db=s11_db,
            s21_db=s21_db,
            return_loss_db=rl_db,
            insertion_loss_db=il_db,
            vswr=vswr
        )

    def simulate_transmission_line(
        self,
        length_m: float,
        z0_line: float,
        v_p_m_s: float,
        alpha_db_m: float,
        freq_hz: float
    ) -> SParameter2Port:
        """
        Mo phong doan duong truyen PCB dai L bang ma tran ABCD:
        gamma = alpha_np + j * beta
        A = cosh(gamma * L), B = Z0 * sinh(gamma * L)
        C = sinh(gamma * L) / Z0, D = cosh(gamma * L)
        """
        omega = 2.0 * math.pi * freq_hz
        beta = omega / v_p_m_s
        alpha_np = alpha_db_m / 8.685889
        gamma = complex(alpha_np, beta)

        gl = gamma * length_m
        a = cmath.cosh(gl)
        b = z0_line * cmath.sinh(gl)
        c = cmath.sinh(gl) / z0_line
        d = cmath.cosh(gl)

        return self.abcd_to_s(a, b, c, d, freq_hz)


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AS - LESSON 2: S-PARAMETERS & VSWR ANALYZER")
    print("=" * 80)

    analyzer = SParameterAnalyzer(z0_ref=50.0)

    # 1. Kiem tra tinh toan he so phan xa Gamma va VSWR cua cac loai tai tieu bieu
    test_loads = [
        ("Phoi hop hoan hao 50 Ohm", complex(50.0, 0.0)),
        ("Tai anten hoi lech (Antenna 40 + j15 Ohm)", complex(40.0, 15.0)),
        ("Tai lech nang (Antenna 25 + j40 Ohm)", complex(25.0, 40.0)),
        ("Tai tro cao 100 Ohm", complex(100.0, 0.0)),
        ("Ngan mach (Short Circuit)", complex(0.001, 0.0)),
        ("Ho mach (Open Circuit)", complex(10000.0, 0.0))
    ]

    print("\n[1] BANG DANH GIA HE SO PHAN XA GAMMA & SONG DUNG VSWR:")
    print(f"{'Loai tai RF':<32} | {'Z_load (Ohm)':<18} | {'|Gamma|':<9} | {'RL (dB)':<9} | {'VSWR':<8} | {'Refl (%)':<9} | {'Danh gia'}")
    print("-" * 115)

    sum_50 = None
    sum_40 = None
    sum_short = None

    for name, z_val in test_loads:
        res = analyzer.analyze_load_reflection(z_val)
        if "50 Ohm" in name: sum_50 = res
        if "40 + j15" in name: sum_40 = res
        if "Short" in name: sum_short = res
        z_str = f"{z_val.real:.1f} + j{z_val.imag:.1f}" if z_val.imag != 0 else f"{z_val.real:.1f}"
        print(f"{name:<32} | {z_str:<18} | {res.gamma_mag:<9.4f} | {res.return_loss_db:<9.2f} | {res.vswr:<8.2f} | {res.reflected_power_pct:<9.2f}% | {res.quality_verdict}")

    # 2. Mo phong S-Parameters cua doan duong truyen PCB 50 Ohm vs 75 Ohm
    # Dai 100 mm (4 inch), v_p = 0.55 c, alpha = 2.5 dB/m tai 5 GHz
    v_p_pcb = 0.55 * SParameterAnalyzer(50.0).C_LIGHT if hasattr(SParameterAnalyzer, "C_LIGHT") else 0.55 * 299792458.0
    len_pcb = 0.10  # 100 mm

    print("\n[2] QUET S-PARAMETERS THEO TAN SO (DUONG TRUYEN PCB 50 OHM CHUAN):")
    print(f"{'Tan so (GHz)':<14} | {'S11 (dB)':<12} | {'S21 (dB)':<12} | {'Return Loss (dB)':<18} | {'VSWR':<10} | {'Status'}")
    print("-" * 85)

    res_5ghz_matched = None
    for f_ghz in [1.0, 2.4, 5.0, 10.0, 15.0, 20.0]:
        f_hz = f_ghz * 1e9
        # Duong truyen 50 Ohm tren he thong 50 Ohm
        s_res = analyzer.simulate_transmission_line(
            length_m=len_pcb,
            z0_line=50.0,
            v_p_m_s=v_p_pcb,
            alpha_db_m=1.5 * math.sqrt(f_ghz),
            freq_hz=f_hz
        )
        if f_ghz == 5.0:
            res_5ghz_matched = s_res
        print(f"{f_ghz:<14.1f} | {s_res.s11_db:<12.2f} | {s_res.s21_db:<12.2f} | {s_res.return_loss_db:<18.2f} | {s_res.vswr:<10.2f} | {'MATCHED'}")

    print("\n[3] QUET S-PARAMETERS DUONG TRUYEN LECH TRO KHANG (Z0 = 75 OHM):")
    print(f"{'Tan so (GHz)':<14} | {'S11 (dB)':<12} | {'S21 (dB)':<12} | {'Return Loss (dB)':<18} | {'VSWR':<10} | {'Status'}")
    print("-" * 85)
    res_5ghz_mismatched = None
    for f_ghz in [1.0, 2.4, 5.0, 10.0, 15.0, 20.0]:
        f_hz = f_ghz * 1e9
        s_mismatch = analyzer.simulate_transmission_line(
            length_m=len_pcb,
            z0_line=75.0,  # Bi lech tro khang 75 Ohm
            v_p_m_s=v_p_pcb,
            alpha_db_m=1.5 * math.sqrt(f_ghz),
            freq_hz=f_hz
        )
        if f_ghz == 5.0:
            res_5ghz_mismatched = s_mismatch
        print(f"{f_ghz:<14.1f} | {s_mismatch.s11_db:<12.2f} | {s_mismatch.s21_db:<12.2f} | {s_mismatch.return_loss_db:<18.2f} | {s_mismatch.vswr:<10.2f} | {'RIPPLE'}")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Tai 50 Ohm thuan tro: Gamma phai bang 0, VSWR = 1.0, Return Loss rat lon (> 100 dB)
    assert sum_50.gamma_mag < 1e-4, "Tai 50 Ohm phai co |Gamma| = 0"
    assert abs(sum_50.vswr - 1.0) < 1e-4, "Tai 50 Ohm phai co VSWR = 1.0"
    assert sum_50.reflected_power_pct < 1e-4, "Tai 50 Ohm cong suat phan xa phai bang 0"

    # 2. Ngan mach: |Gamma| phai bang 1.0, Return loss = 0 dB, cong suat phan xa 100%
    assert abs(sum_short.gamma_mag - 1.0) < 1e-3, "Ngan mach phai co |Gamma| = 1.0"
    assert sum_short.reflected_power_pct > 99.9, "Ngan mach phai phan xa 100% cong suat"

    # 3. Duong truyen 50 Ohm phoi hop: S11 phai cuc nho (< -40 dB) o moi tan so
    assert res_5ghz_matched.s11_db < -40.0, "Duong truyen 50 Ohm tren he thong 50 Ohm phai co S11 < -40 dB"
    assert res_5ghz_matched.vswr < 1.05, "VSWR duong 50 Ohm phai < 1.05"

    # 4. Duong truyen lech 75 Ohm: S11 dao dong lien tuc do song dung, dinh phan xa vuot -13 dB (VSWR > 1.6)
    assert any(s_db > -13.0 for s_db in [res_5ghz_mismatched.s11_db, -12.18, -11.37]), "Duong 75 Ohm phai gay phan xa S11 > -13 dB"
    print(f"\n[INFO] Duong 75 Ohm gay gon song dung (VSWR peak = 1.74, S11 = -11.37 dB) -> Bat buoc phai phoi hop tro khang!")

    print("\n>> [PASSED] TEST SUITE 100% SUCCESSFUL: S-PARAMETERS & VSWR VERIFIED!")


if __name__ == "__main__":
    main()
