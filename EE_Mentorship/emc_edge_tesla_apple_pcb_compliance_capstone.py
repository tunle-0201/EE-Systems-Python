"""
Chuyen de AU: Tuong thich Dien tu EMC/EMI & Ky thuat Tiep dia PCB Toc do cao
Bai 135 (Milestone AU.4 - Capstone Project): Dong co tham dinh tuong thich dien tu EMC/EMI
                                             cho bo mach chu Apple Silicon & Tesla FSD HW4 Capstone

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Xay dung dong co mo phong giand doan duong hoi tiep Return Path Discontinuity (RPD)
          khi vet mach cao toc bang qua khe cat mat dat (Split Ground Plane Slot Crossing),
          tinh toan dien ap nay dat Ground Bounce va buc xa anten khe ho (Slot Antenna),
          tich hop tu stitching / via noi ground va bo quet pho EMI Compliance Scanner dat chuan
          CISPR 25 Class 5 (Tesla) va FCC Part 15 Class B (Apple).

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict, Optional


class ReturnPathDiscontinuityModel:
    """
    Mo hinh vat ly giand doan duong hoi tiep dong dien cao tan tren mat dat PCB.
    
    Phan tich toan hoc & vat ly dien tu:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   1. Vet mach lien tuc tren Ground Plane (Ly tuong):   │
    │      Dong hoi tiep chay ngay ben duoi vet mach         │
    │      Dien cam vong lap nho: L_loop ~ 0.2 nH/cm         │
    │                                                        │
    │   2. Vet mach cat ngang qua khe cat (Slot Crossing):   │
    │      Dong hoi tiep buoc phai di vong quanh khe ho      │
    │      Dien cam ky sinh tang vot:                        │
    │                                                        │
    │                           Slot_Length                  │
    │      L_slot (nH) = 5.0 * ─────────────                 │
    │                               1 cm                     │
    │                                                        │
    │   3. Dien ap nay dat (Ground Bounce / Delta-I Noise):  │
    │                                                        │
    │                        di                              │
    │      V_bounce = L_slot ───                             │
    │                        dt                              │
    │                                                        │
    │   4. Buc xa Anten khe ho (Slot Antenna Radiation):     │
    │      Khe ho mat dat hoat dong nhu mot anten tu truong  │
    │      kich thich dong dien dong pha tren toan bo mach!  │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        slot_length_mm: float = 20.0,
        slot_width_mm: float = 1.0,
        trace_height_above_plane_mm: float = 0.1,
        di_dt_amps_per_ns: float = 0.1  # 20 mA chuyen mach trong 200 ps = 0.1 A/ns
    ):
        self.slot_length_mm = float(slot_length_mm)
        self.slot_width_mm = float(slot_width_mm)
        self.h_mm = float(trace_height_above_plane_mm)
        self.di_dt = float(di_dt_amps_per_ns) * 1e9  # A/sec

        # Dien cam mat dat ly tuong khi khong co khe (0.2 nH/cm)
        self.l_ideal_henry = 0.2e-9 * (self.slot_length_mm / 10.0)

        # Dien cam tang them do dong dien phai di vong quanh khe
        # Xap xi dien cam vong lap khe: L_slot ~ 0.5 nH cho moi mm chieu dai khe
        self.l_slot_henry = 0.5e-9 * self.slot_length_mm

    def calculate_ground_bounce_volts(self, has_stitching_caps: bool = False) -> float:
        """
        Tinh dien ap nay dat Ground Bounce V = L * di/dt.
        Neu co tu stitching hoac via noi dat, dien cam bi kep ve muc nho.
        """
        l_eff = self.l_ideal_henry if has_stitching_caps else self.l_slot_henry
        return l_eff * self.di_dt

    def calculate_slot_radiation_efficiency(self, f_hz: float) -> float:
        """
        Tinh he so hieu qua buc xa cua khe ho so voi buoc song.
        Khi chieu dai khe Slot_Length dat nua buoc song lambda / 2,
        khe ho cong huong va buc xa cuc dai!
        """
        # Van toc truyen trong FR4 / Rogers (er_eff ~ 3.24)
        c = 3.0e8
        vp = c / math.sqrt(3.24)
        lambda_m = vp / max(1e3, f_hz)

        # Ti le chieu dai khe so voi nua buoc song
        slot_len_m = self.slot_length_mm * 1e-3
        ratio = slot_len_m / (lambda_m / 2.0)
        
        # He so khuech dai buc xa (dat dinh = 1.0 khi ratio = 1)
        return min(1.0, ratio ** 2)


class PCBEMIScannerEngine:
    """
    Dong co quet va kiem chuan pho tuong thich dien tu EMC (Radiated & Conducted).
    Danh gia tuan thu tieu chuan CISPR 25 Class 5 (Tesla) va FCC Class B (Apple).
    """
    def __init__(self, target_standard: str = "CISPR_25_Class_5"):
        self.standard = target_standard

    def get_limit_dbuv_per_m(self, f_hz: float) -> float:
        f_mhz = f_hz / 1e6
        if self.standard == "CISPR_25_Class_5":
            # Chuan o to nghiem ngat tai 1m
            if 30.0 <= f_mhz < 54.0:
                return 36.0
            elif 54.0 <= f_mhz < 70.0:
                return 30.0
            elif 76.0 <= f_mhz < 108.0:
                return 28.0  # Dai FM xe hoi Tesla
            elif 142.0 <= f_mhz < 175.0:
                return 26.0
            elif 200.0 <= f_mhz < 400.0:
                return 37.0
            elif 400.0 <= f_mhz < 1000.0:
                return 41.0
            else:
                return 45.0
        else:
            # FCC Part 15 Class B tai 3m
            if f_mhz < 88.0:
                return 40.0
            elif 88.0 <= f_mhz < 216.0:
                return 43.5
            elif 216.0 <= f_mhz < 960.0:
                return 46.0
            else:
                return 54.0

    def scan_board_configuration(
        self,
        freq_list_hz: List[float],
        rpd_model: ReturnPathDiscontinuityModel,
        has_stitching: bool,
        has_cmc: bool,
        has_ssc: bool
    ) -> Dict[str, any]:
        """
        Mo phong quet pho buc xa tong the cua bo mach voi cac giai phap EMC duoc kich hoat.
        """
        v_bounce = rpd_model.calculate_ground_bounce_volts(has_stitching_caps=has_stitching)
        results = []
        worst_margin_db = 999.0
        failed_frequencies = []

        for f in freq_list_hz:
            limit_db = self.get_limit_dbuv_per_m(f)

            # Cuong do buc xa co ban tu dong dien cao toc
            # V_bounce kich thich dong dien dong pha: I_CM ~ V_bounce / Z_chassis (Z ~ 150 Ohm)
            i_cm_induced = v_bounce / 150.0

            # Neu co cuon cam chan CMC, suy giam dong pha 25 dB
            if has_cmc:
                i_cm_induced *= 0.056  # Giam 25 dB

            # Hieu qua buc xa anten khe
            slot_eff = rpd_model.calculate_slot_radiation_efficiency(f)
            # Neu co stitching, slot bi triet tieu
            if has_stitching:
                slot_eff *= 0.01

            # Cuong do buc xa dong pha co ban tai 1m
            e_cm_uv = 0.1257 * f * i_cm_induced * 1.0 / 1.0
            e_rad_db = 20.0 * math.log10(max(1e-3, e_cm_uv)) + (10.0 * math.log10(max(1e-4, slot_eff)))

            # Neu co Spread Spectrum Clocking (SSC), giam dinh them 12 dB o hoa tan
            if has_ssc:
                e_rad_db -= 12.0

            margin_db = limit_db - e_rad_db
            is_pass = margin_db >= 0.0

            if margin_db < worst_margin_db:
                worst_margin_db = margin_db

            if not is_pass:
                failed_frequencies.append(f)

            results.append({
                "frequency_hz": f,
                "e_field_dbuv": e_rad_db,
                "limit_dbuv": limit_db,
                "margin_db": margin_db,
                "is_pass": is_pass
            })

        overall_pass = len(failed_frequencies) == 0
        return {
            "v_bounce_volts": v_bounce,
            "worst_margin_db": worst_margin_db,
            "overall_pass": overall_pass,
            "failed_frequencies": failed_frequencies,
            "points": results
        }


def test_emc_pcb_compliance_capstone():
    print("================================================================================")
    print("TEST SUITE CAPSTONE: THAM DINH EMC/EMI BO MACH APPLE SILICON & TESLA FSD HW4")
    print("================================================================================")

    # 1. Kiem tra giand doan duong hoi tiep tren khe cat Ground 20 mm
    rpd = ReturnPathDiscontinuityModel(
        slot_length_mm=20.0,
        slot_width_mm=1.0,
        trace_height_above_plane_mm=0.1,
        di_dt_amps_per_ns=0.1 # 20 mA trong 200 ps = 0.1 A/ns
    )

    # Khi khong co tu stitching: L_slot = 0.5 nH * 20 = 10 nH
    v_bounce_bad = rpd.calculate_ground_bounce_volts(has_stitching_caps=False)
    # Khi co tu stitching: L_eff = 0.4 nH
    v_bounce_good = rpd.calculate_ground_bounce_volts(has_stitching_caps=True)

    print(f"[1] Phan tich dien ap nay dat Ground Bounce khi cat qua khe ho 20 mm:")
    print(f"    - Khong co tu Stitching: L = {rpd.l_slot_henry*1e9:.1f} nH  | V_bounce = {v_bounce_bad*1000:.1f} mV")
    print(f"    - Co tu Stitching via:   L = {rpd.l_ideal_henry*1e9:.2f} nH | V_bounce = {v_bounce_good*1000:.2f} mV")
    
    assert v_bounce_bad >= 0.8, "Khong co stitching, V_bounce phai dat gan 1V do L = 10 nH"
    assert v_bounce_good < 0.05, "Co stitching, V_bounce phai giam duoi 50 mV"
    print("    -> Tu stitching via giup giam dien ap nay dat tren 25 lan!")

    # 2. Quet kiem chuan pho CISPR 25 Class 5 cho Tesla FSD Autopilot
    scanner_tesla = PCBEMIScannerEngine(target_standard="CISPR_25_Class_5")
    freq_sweep = [50e6, 80e6, 100e6, 150e6, 300e6, 600e6, 900e6]

    # Cau hinh A: Bo mach bi loi thiet ke (Cat khe ground, khong CMC, khong SSC)
    rep_bad = scanner_tesla.scan_board_configuration(
        freq_list_hz=freq_sweep,
        rpd_model=rpd,
        has_stitching=False,
        has_cmc=False,
        has_ssc=False
    )
    print(f"\n[2] Danh gia Cau hinh A (Loi khe ho mat dat, khong CMC, khong SSC):")
    print(f"    - Worst Margin: {rep_bad['worst_margin_db']:.1f} dB | Ket qua: PASS={rep_bad['overall_pass']}")
    print(f"    - So tan so vi pham: {len(rep_bad['failed_frequencies'])} / {len(freq_sweep)}")
    assert rep_bad['overall_pass'] is False, "Cau hinh A phai FAIL nang chuan CISPR 25"
    assert rep_bad['worst_margin_db'] < -15.0, "Worst margin phai am nang tren -15 dB"

    # Cau hinh B: Bo sung tu Stitching via khuyen mat dat
    rep_stitching = scanner_tesla.scan_board_configuration(
        freq_list_hz=freq_sweep,
        rpd_model=rpd,
        has_stitching=True,
        has_cmc=False,
        has_ssc=False
    )
    print(f"\n[3] Danh gia Cau hinh B (Them tu Stitching via noi mat dat):")
    print(f"    - Worst Margin: {rep_stitching['worst_margin_db']:.1f} dB (Cai thien hon {rep_stitching['worst_margin_db'] - rep_bad['worst_margin_db']:.1f} dB)")

    # Cau hinh C: Thiet ke toi uu toan dien chuan Apple Silicon & Tesla FSD HW4
    # (Co Stitching Via + Cuon cam CMC + Spread Spectrum Clocking SSC)
    rep_golden = scanner_tesla.scan_board_configuration(
        freq_list_hz=freq_sweep,
        rpd_model=rpd,
        has_stitching=True,
        has_cmc=True,
        has_ssc=True
    )
    print(f"\n[4] Danh gia Cau hinh C (Toi uu toan dien: Stitching + CMC + SSC):")
    print(f"    - Worst Margin: +{rep_golden['worst_margin_db']:.1f} dB | Ket qua: PASS={rep_golden['overall_pass']}")
    for pt in rep_golden["points"]:
        print(f"      f = {pt['frequency_hz']/1e6:5.0f} MHz | E_field = {pt['e_field_dbuv']:5.1f} dBuV/m | Limit = {pt['limit_dbuv']:5.1f} dBuV/m | Margin = +{pt['margin_db']:4.1f} dB")

    assert rep_golden['overall_pass'] is True, "Cau hinh toi uu phai PASS 100% chuan CISPR 25"
    assert rep_golden['worst_margin_db'] >= 6.0, "Thiet ke phan cung phai co it nhat 6 dB Safety Margin"
    print("    -> Dat tieu chuan an toan tuong thich dien tu cao cap cho Tesla Robotaxi & Apple SoC!")

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AU.4 CAPSTONE DA THANH CONG 100%!")


if __name__ == "__main__":
    test_emc_pcb_compliance_capstone()
