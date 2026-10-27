"""
================================================================================
CHUYEN DE AS: TINH TOAN VEN DUONG TRUYEN CAO TAN RF & PHOI HOP TRO KHANG SMITH
BAI 1 (MILESTONE AS.1): MO HINH DUONG TRUYEN CAO TAN MICROSTRIP & SKIN EFFECT
================================================================================
Chuc nang he thong:
1. Tinh toan tro khang dac tinh Z_0 va hang so dien moi hieu dung eps_eff
   theo mo hinh giai tich chinh xac Hammerstad-Jensen cho duong truyen Microstrip.
2. Tinh van toc lan truyen song v_p va do tre lan truyen tren bo mach PCB:
      v_p  = c / sqrt(eps_eff)
      t_pd = 1 / v_p  (picoseconds / mm)
3. Mo hinh hoa hieu ung be mat (Skin Effect) tai tan so multi-GHz:
      Do sau tham nhap delta = 1 / sqrt(pi * f * mu_0 * sigma_cu)
      Dien tro AC ty le voi can bac hai cua tan so: R_ac(f) ~ sqrt(f)
4. Tinh toan tong suy hao duong truyen alpha_tot = alpha_conductor + alpha_dielectric
   tinh theo dB/inch va dB/meter tren vat lieu PCB cao cap (FR-4 vs Rogers RO4350B).

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
               eps_r + 1   eps_r - 1               1
   eps_eff  = ───────── + ───────── * ──────────────────────────
                   2           2       sqrt(1 + 12 * (h / W))

   Khi W / h > 1 (Truong hop duong truyen PCB 50 Ohm pho bien):
                     120 * pi
   Z_0      = ──────────────────────────────────────────────────────────
              sqrt(eps_eff) * [ W/h + 1.393 + 0.667 * ln(W/h + 1.444) ]

   alpha_c  = 8.686 * (R_ac / (2 * Z_0))  [dB/m]
   alpha_d  = 27.3 * (eps_r / (eps_r - 1)) * ((eps_eff - 1) / sqrt(eps_eff)) * (tan_delta / lambda_0)  [dB/m]
================================================================================
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class MicrostripGeometry:
    """Thong so hinh hoc va vat lieu duong truyen Microstrip."""
    w_mm: float          # Do rong duong dong PCB (mm)
    h_mm: float          # Do day lop dien moi cach dien (mm)
    t_copper_um: float   # Do day la dong (thuong 35 um = 1 oz copper)
    eps_r: float         # Hang so dien moi tuong doi (FR-4: ~4.3, Rogers: ~3.66)
    tan_delta: float     # He so ton hao dien moi (FR-4: 0.02, Rogers: 0.0037)
    conductivity: float  # Do dan dien cua dong (5.8e7 S/m)


@dataclass
class TransmissionLineMetrics:
    """Chi so vat ly cua duong truyen cao tan."""
    z0_ohms: float
    eps_eff: float
    v_p_m_per_s: float
    v_p_ratio_c: float
    t_pd_ps_per_mm: float
    skin_depth_um_1ghz: float
    attenuation_c_db_per_m: float
    attenuation_d_db_per_m: float
    attenuation_tot_db_per_m: float
    attenuation_tot_db_per_inch: float


class MicrostripModelEngine:
    """
    Dong co tinh toan tham so duong truyen cao tan Microstrip chuan cong nghiep.
    """

    C_LIGHT = 299792458.0  # Van toc anh sang trong chan khong (m/s)
    MU_0 = 4.0 * math.pi * 1e-7  # Do tu tham chan khong (H/m)

    def __init__(self, geo: MicrostripGeometry):
        assert geo.w_mm > 0, "Do rong w phai duong"
        assert geo.h_mm > 0, "Do day h phai duong"
        self.geo = geo

    def calculate_effective_permittivity(self) -> float:
        """
        Tinh hang so dien moi hieu dung theo Hammerstad-Jensen:
        eps_eff = (eps_r + 1)/2 + ((eps_r - 1)/2) * (1 / sqrt(1 + 12*(h/W)))
        """
        w = self.geo.w_mm
        h = self.geo.h_mm
        eps_r = self.geo.eps_r

        term1 = (eps_r + 1.0) / 2.0
        term2 = (eps_r - 1.0) / 2.0
        geom_factor = 1.0 / math.sqrt(1.0 + 12.0 * (h / w))
        eps_eff = term1 + term2 * geom_factor
        return eps_eff

    def calculate_characteristic_impedance(self, eps_eff: float) -> float:
        """
        Tinh tro khang dac tinh Z_0.
        """
        u = self.geo.w_mm / self.geo.h_mm

        if u <= 1.0:
            # Duong hep
            num = 60.0
            ln_term = math.log((8.0 / u) + 0.25 * u)
            z0 = (num / math.sqrt(eps_eff)) * ln_term
        else:
            # Duong rong (Pho bien nhat de dat 50 Ohm tren PCB)
            den = u + 1.393 + 0.667 * math.log(u + 1.444)
            z0 = (120.0 * math.pi) / (math.sqrt(eps_eff) * den)

        return z0

    def calculate_skin_depth(self, freq_hz: float) -> float:
        """
        Do sau tham nhap be mat (Skin Depth):
        delta = 1 / sqrt(pi * f * mu_0 * sigma)
        """
        omega = 2.0 * math.pi * freq_hz
        delta = 1.0 / math.sqrt(math.pi * freq_hz * self.MU_0 * self.geo.conductivity)
        return delta

    def calculate_loss_at_frequency(
        self,
        freq_hz: float,
        z0: float,
        eps_eff: float
    ) -> Tuple[float, float, float]:
        """
        Tinh toan ton hao kim loai (Conductor loss) va ton hao dien moi (Dielectric loss) o tan so f.
        Tra ve (alpha_c_db_m, alpha_d_db_m, alpha_tot_db_m).
        """
        w_m = self.geo.w_mm * 1e-3
        t_m = self.geo.t_copper_um * 1e-6
        delta = self.calculate_skin_depth(freq_hz)

        # Dien tro AC tren don vi chieu dai: R_ac = 1 / (sigma * chu_vi_hieu_dung * delta)
        # Chu vi mat cat duong truyen chu nhat ~ 2 * (w + t)
        p_eff = 2.0 * (w_m + t_m)
        r_ac = 1.0 / (self.geo.conductivity * p_eff * delta)

        # Suy hao do dien tro dan alpha_c (Np/m -> dB/m):
        alpha_c_np = r_ac / (2.0 * z0)
        alpha_c_db = 8.685889 * alpha_c_np

        # Suy hao dien moi alpha_d:
        # lambda_0 = c / f
        lambda_0 = self.C_LIGHT / freq_hz
        eps_r = self.geo.eps_r
        term_eps = (eps_r / (eps_r - 1.0)) * ((eps_eff - 1.0) / math.sqrt(eps_eff))
        alpha_d_db = 27.2875 * term_eps * (self.geo.tan_delta / lambda_0)

        alpha_tot_db = alpha_c_db + alpha_d_db
        return alpha_c_db, alpha_d_db, alpha_tot_db

    def analyze(self, freq_hz: float = 1.0e9) -> TransmissionLineMetrics:
        """
        Tong hop phan tich toan dien duong truyen o tan so xac dinh.
        """
        eps_eff = self.calculate_effective_permittivity()
        z0 = self.calculate_characteristic_impedance(eps_eff)

        # Van toc lan truyen v_p
        v_p = self.C_LIGHT / math.sqrt(eps_eff)
        v_p_ratio = v_p / self.C_LIGHT

        # Do tre lan truyen (Propagation Delay): ps / mm
        # t_pd = 1 / v_p (s/m) = 1e12 ps / 1e3 mm = 1e9 / v_p
        t_pd = (1.0 / v_p) * 1e12 * 1e-3  # ps/mm

        skin_depth_1g = self.calculate_skin_depth(1.0e9) * 1e6  # um

        alpha_c, alpha_d, alpha_tot = self.calculate_loss_at_frequency(freq_hz, z0, eps_eff)
        alpha_inch = alpha_tot * 0.0254  # 1 inch = 0.0254 m

        return TransmissionLineMetrics(
            z0_ohms=z0,
            eps_eff=eps_eff,
            v_p_m_per_s=v_p,
            v_p_ratio_c=v_p_ratio,
            t_pd_ps_per_mm=t_pd,
            skin_depth_um_1ghz=skin_depth_1g,
            attenuation_c_db_per_m=alpha_c,
            attenuation_d_db_per_m=alpha_d,
            attenuation_tot_db_per_m=alpha_tot,
            attenuation_tot_db_per_inch=alpha_inch
        )


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AS - LESSON 1: RF MICROSTRIP TRANSMISSION LINE")
    print("=" * 80)

    # So sanh 2 vat lieu che tao bo mach cao toc:
    # 1. Tieu chuan FR-4 (Gia re, dung cho bo mach thuong, eps_r = 4.3, tan_delta = 0.02)
    # 2. Rogers RO4350B (Cao cap, dung cho Apple RF Front-End, Tesla Radar & Starlink, eps_r = 3.66, tan_delta = 0.0037)

    # Thiet ke duong truyen microstrip tren do day dien moi h = 0.20 mm (8 mil)
    # De dat tro khang gan 50 Ohm:
    # Tren FR-4: w ~ 0.38 mm (15 mil)
    # Tren Rogers RO4350B: w ~ 0.44 mm (17.3 mil)

    geo_fr4 = MicrostripGeometry(
        w_mm=0.38,
        h_mm=0.20,
        t_copper_um=35.0,
        eps_r=4.3,
        tan_delta=0.02,
        conductivity=5.8e7
    )

    geo_rogers = MicrostripGeometry(
        w_mm=0.44,
        h_mm=0.20,
        t_copper_um=35.0,
        eps_r=3.66,
        tan_delta=0.0037,
        conductivity=5.8e7
    )

    engine_fr4 = MicrostripModelEngine(geo_fr4)
    engine_rogers = MicrostripModelEngine(geo_rogers)

    res_fr4 = engine_fr4.analyze(freq_hz=5.0e9)  # 5 GHz
    res_rogers = engine_rogers.analyze(freq_hz=5.0e9)

    print("\n[1] SO SANH TRO KHANG VA TOC DO LAN TRUYEN (T_pd):")
    print(f"{'Thong so duong truyen':<30} | {'FR-4 (Standard PCB)':<22} | {'Rogers RO4350B (High-Speed)':<25}")
    print("-" * 85)
    print(f"{'Tro khang dac tinh Z_0 (Ohm)':<30} | {res_fr4.z0_ohms:<22.2f} | {res_rogers.z0_ohms:<25.2f}")
    print(f"{'Dien moi hieu dung eps_eff':<30} | {res_fr4.eps_eff:<22.3f} | {res_rogers.eps_eff:<25.3f}")
    print(f"{'Van toc lan truyen (% c)':<30} | {res_fr4.v_p_ratio_c * 100:<22.1f} | {res_rogers.v_p_ratio_c * 100:<25.1f}")
    print(f"{'Do tre t_pd (ps / mm)':<30} | {res_fr4.t_pd_ps_per_mm:<22.2f} | {res_rogers.t_pd_ps_per_mm:<25.2f}")
    print(f"{'Do sau Skin Depth tai 1 GHz':<30} | {res_fr4.skin_depth_um_1ghz:<22.2f} um | {res_rogers.skin_depth_um_1ghz:<25.2f} um")

    print("\n[2] PHAN TICH SUY HAO DUONG TRUYEN TAI 5 GHz (LOSS COMPARISON):")
    print(f"{'Thanh phan ton hao':<30} | {'FR-4 (dB / inch)':<22} | {'Rogers RO4350B (dB / inch)':<25}")
    print("-" * 85)
    print(f"{'Ton hao dong (Conductor)':<30} | {res_fr4.attenuation_c_db_per_m * 0.0254:<22.4f} | {res_rogers.attenuation_c_db_per_m * 0.0254:<25.4f}")
    print(f"{'Ton hao dien moi (Dielectric)':<30} | {res_fr4.attenuation_d_db_per_m * 0.0254:<22.4f} | {res_rogers.attenuation_d_db_per_m * 0.0254:<25.4f}")
    print(f"{'TONG SUY HAO TAI 5 GHz':<30} | {res_fr4.attenuation_tot_db_per_inch:<22.4f} | {res_rogers.attenuation_tot_db_per_inch:<25.4f}")

    # 3. Quet suy hao theo dai tan so tu 1 GHz den 20 GHz
    print("\n[3] QUET TON HAO THEO TAN SO (1 GHz -> 20 GHz tren duong truyen dai 6 inch):")
    print(f"{'Tan so f (GHz)':<16} | {'Skin Depth (um)':<18} | {'Suy hao FR-4 (dB/6in)':<24} | {'Suy hao Rogers (dB/6in)':<25}")
    print("-" * 90)
    for f_ghz in [1.0, 2.4, 5.0, 10.0, 15.0, 20.0]:
        f_hz = f_ghz * 1e9
        d_um = engine_fr4.calculate_skin_depth(f_hz) * 1e6
        _, _, l_fr4 = engine_fr4.calculate_loss_at_frequency(f_hz, res_fr4.z0_ohms, res_fr4.eps_eff)
        _, _, l_rog = engine_rogers.calculate_loss_at_frequency(f_hz, res_rogers.z0_ohms, res_rogers.eps_eff)
        l_fr4_6in = l_fr4 * 0.0254 * 6.0
        l_rog_6in = l_rog * 0.0254 * 6.0
        print(f"{f_ghz:<16.1f} | {d_um:<18.2f} | {l_fr4_6in:<24.2f} | {l_rog_6in:<25.2f}")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Tro khang thiet ke phai nam trong dai tieu chuan 50 Ohm (+- 2.5 Ohm)
    assert abs(res_fr4.z0_ohms - 50.0) < 2.5, f"FR-4 Z_0 phai ~ 50 Ohm, thuc te={res_fr4.z0_ohms:.2f}"
    assert abs(res_rogers.z0_ohms - 50.0) < 2.5, f"Rogers Z_0 phai ~ 50 Ohm, thuc te={res_rogers.z0_ohms:.2f}"
    print("\n[INFO] Tro khang dac tinh Microstrip Z_0 ~ 50 Ohm chuan xac: PASSED!")

    # 2. Do sau tham nhap Skin depth tai 1 GHz phai khoang 2.0 - 2.1 um
    assert 2.0 <= res_fr4.skin_depth_um_1ghz <= 2.2, f"Skin depth 1GHz sai lech: {res_fr4.skin_depth_um_1ghz:.2f} um"

    # 3. Do tre lan truyen t_pd phai nam trong dai 5.5 - 7.0 ps/mm
    assert 5.5 <= res_fr4.t_pd_ps_per_mm <= 7.0, f"t_pd FR-4 sai lech: {res_fr4.t_pd_ps_per_mm:.2f} ps/mm"
    assert 5.5 <= res_rogers.t_pd_ps_per_mm <= 7.0, f"t_pd Rogers sai lech: {res_rogers.t_pd_ps_per_mm:.2f} ps/mm"

    # 4. Tai 10 GHz, suy hao cua FR-4 phai gap it nhat 2.5 lan Rogers RO4350B (do tan_delta cao hon 5 lan)
    _, _, l_fr4_10g = engine_fr4.calculate_loss_at_frequency(10e9, res_fr4.z0_ohms, res_fr4.eps_eff)
    _, _, l_rog_10g = engine_rogers.calculate_loss_at_frequency(10e9, res_rogers.z0_ohms, res_rogers.eps_eff)
    loss_ratio = l_fr4_10g / l_rog_10g
    print(f"[INFO] Ty le suy hao giua FR-4 va Rogers o 10 GHz: {loss_ratio:.2f}x (Rogers vuot troi)")
    assert loss_ratio > 2.5, "FR-4 phai co suy hao cao gap it nhat 2.5 lan Rogers o 10 GHz"

    print("\n>> [PASSED] TEST SUITE 100% SUCCESSFUL: RF MICROSTRIP TRANSMISSION LINE VERIFIED!")


if __name__ == "__main__":
    main()
