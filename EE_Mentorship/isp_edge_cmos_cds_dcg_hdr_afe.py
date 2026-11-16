"""
EE MENTORSHIP PROGRAM - MODULE BL (NHOM 51) - BAI 200 (MILESTONE BL.1)
================================================================================
MACH DOC CAM BIEN ANH CMOS 4T-PPD AFE: TRIET TIEU NHIEU kTC BANG CDS,
BO CHUYEN DOI ADC COT SONG SONG & GHEP KENH HDR KEP 120 dB (DCG + SHORT TAP)
CHO CAMERA APPLE IPHONE / VISION PRO & TESLA FSD HW5
================================================================================

Nguyen ly vat ly ban dan & Toan hoc cot loi:
1. Nhieu nhiet Reset kTC & Sai lech nguong FPN tren Diode quang 4T-PPD:
   - Khi reset tu ky sinh Floating Diffusion C_fd truoc moi khung hinh,
     nhieu nhiet kTC dong bang ngau nhien tren nut cam bien voi do lech chuan:
       sigma_V_kTC = sqrt( k_B * T / C_fd )
   - Tai T = 330 K (57 deg C) va C_fd = 1.4 fF (Do loi chuyen doi cao HCG = 114.4 uV/e-):
     sigma_V_kTC = 1.804 mV rms -> Tuong duong 15.8 electron nhieu! Lam mu vung toi.

2. Lay mau Tuong quan Kep (Correlated Double Sampling - CDS):
   - Lay mau dien ap Reset ngay truoc khi mo cong truyen TX:
       V_rst = V_ref + v_kTC + v_offset_SF + n_1
   - Mo cong TX do N_e quang dien tu vao C_fd va lay mau tin hieu:
       V_sig = V_ref + v_kTC + v_offset_SF - N_e * CG + n_2
   - Mach tru vi sai analog/digital CDS:
       V_cds = V_rst - V_sig = N_e * CG + (n_1 - n_2)
     -> Triet tieu 100% nhieu kTC va 100% sai lech V_th cua Transistor nguon theo (FPN)!

3. Kien truc Dai dong 120 dB cho O to Tu lai (Dual Conversion Gain + Short Exp):
   - HCG (C_fd nho = 1.3 fF, CG = 123 uV/e-): Nhay sieu cao cho vung toi (read noise 1.3 e-).
   - LCG (Bat them tu phu thanh C_fd = 10.6 fF, CG = 15 uV/e-): Dung gieng lon 75,000 e-.
   - Kenh Phoi sang ngan T_short = T_long / 16: Mo rong gioi han bao hoa len 1,200,000 e-!

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. He so chuyen doi Dien tich -> Dien ap (Conversion Gain):
              q_e (1.602e-19 C)
     CG = ────────────────────────  (V / electron)
                  C_fd

2. Dai dong Dynamic Range (DR):
                   N_sat_effective
     DR_dB = 20 * log10( ─────────────── )
                    N_noise_read_HCG
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


K_BOLTZMANN = 1.380649e-23
Q_ELECTRON = 1.602176634e-19


@dataclass
class CMOS4TPixelConfig:
    """Thong so vat ly pixel CMOS 4T-PPD cong nghe Dual Conversion Gain (DCG)."""
    temp_k: float = 330.0            # Nhiet do die silicon: 57 deg C
    c_fd_hcg_f: float = 1.30e-15     # Tu FD che do High Gain: 1.30 fF -> ~123.2 uV/e-
    c_fd_lcg_f: float = 10.68e-15    # Tu FD che do Low Gain : 10.68 fF -> ~15.0 uV/e-
    v_adc_fs: float = 1.20           # Dai dien ap dau vao Single-Slope ADC 12-bit: 1.20 V
    adc_bits: int = 12               # Do phan giai 12-bit (0..4095 DN)
    short_exp_ratio: float = 16.0    # Ty le phoi sang ngan T_long / T_short = 16x
    sf_amp_noise_v: float = 115.0e-6 # Nhieu nhiet 1/f + trang cua mach Source Follower + ADC


class ColumnSingleSlopeADC:
    """Bo chuyen doi ADC doc cot song song 12-bit Single-Slope Ramp."""

    def __init__(self, v_fs: float = 1.20, bits: int = 12):
        self.v_fs = v_fs
        self.max_dn = (1 << bits) - 1
        self.lsb_v = v_fs / self.max_dn

    def convert(self, v_analog: float) -> int:
        v_clamped = max(0.0, min(self.v_fs, v_analog))
        return int(round(v_clamped / self.lsb_v))

    def to_volts(self, dn: int) -> float:
        return dn * self.lsb_v


class CMOSPixelAFE:
    """Mo phong mach Analog Front-End 4T-PPD co va khong co CDS tren cot ADC."""

    def __init__(self, cfg: CMOS4TPixelConfig):
        self.cfg = cfg
        self.cg_hcg = Q_ELECTRON / cfg.c_fd_hcg_f
        self.cg_lcg = Q_ELECTRON / cfg.c_fd_lcg_f
        self.sigma_ktc_hcg = math.sqrt(K_BOLTZMANN * cfg.temp_k / cfg.c_fd_hcg_f)
        self.sigma_ktc_lcg = math.sqrt(K_BOLTZMANN * cfg.temp_k / cfg.c_fd_lcg_f)
        self.adc = ColumnSingleSlopeADC(cfg.v_adc_fs, cfg.adc_bits)

    def readout_hcg_pixel(
        self, n_electrons: float, pixel_vth_offset_v: float, use_cds: bool, rng: random.Random
    ) -> float:
        """
        Doc gia tri uoc luong theo electron cho kenh HCG:
        - use_cds=False: Chi lay mau tin hieu 1 lan -> hung tron nhieu kTC + V_th FPN.
        - use_cds=True : Tru mau Reset - Signal -> Triet tieu 100% kTC & V_th FPN!
        """
        v_ktc = rng.gauss(0.0, self.sigma_ktc_hcg)
        n1 = rng.gauss(0.0, self.cfg.sf_amp_noise_v)
        n2 = rng.gauss(0.0, self.cfg.sf_amp_noise_v)

        # Them dien ap nen Black-Level Pedestal (50 mV) de ADC khong bi cat cut phan am cua nhieu
        v_pedestal = 0.050
        v_rst_sample = v_ktc + pixel_vth_offset_v + n1
        v_sig_rel = n_electrons * self.cg_hcg + v_ktc + pixel_vth_offset_v + n2

        if use_cds:
            v_net = v_pedestal + (v_sig_rel - v_rst_sample)
        else:
            v_net = v_pedestal + v_sig_rel

        dn = self.adc.convert(v_net)
        return (self.adc.to_volts(dn) - v_pedestal) / self.cg_hcg

    def capture_triple_tap_dns(
        self, true_electrons_long: float, pixel_vth_offset_v: float, rng: random.Random
    ) -> Tuple[int, int, int]:
        """
        Chup dong thoi 3 kenh 12-bit CDS cho 1 diem anh:
        (DN_HCG_long, DN_LCG_long, DN_LCG_short)
        """
        # 1. HCG Long (nhay cuc cao, bao hoa ~ 9,700 e-)
        shot_long = rng.gauss(0.0, math.sqrt(max(0.0, true_electrons_long)))
        e_long = max(0.0, true_electrons_long + shot_long)
        n_cds_h = rng.gauss(0.0, math.sqrt(2.0) * self.cfg.sf_amp_noise_v)
        v_hcg = e_long * self.cg_hcg + n_cds_h
        dn_hcg = self.adc.convert(v_hcg)

        # 2. LCG Long (tu lon, bao hoa ~ 80,000 e-)
        n_cds_l = rng.gauss(0.0, math.sqrt(2.0) * self.cfg.sf_amp_noise_v)
        v_lcg = e_long * self.cg_lcg + n_cds_l
        dn_lcg = self.adc.convert(v_lcg)

        # 3. LCG Short (phoi sang T_long / 16 -> dai hieu dung len ~ 1,280,000 e-!)
        true_e_short = true_electrons_long / self.cfg.short_exp_ratio
        e_short = max(0.0, true_e_short + rng.gauss(0.0, math.sqrt(max(0.0, true_e_short))))
        n_cds_s = rng.gauss(0.0, math.sqrt(2.0) * self.cfg.sf_amp_noise_v)
        v_short = e_short * self.cg_lcg + n_cds_s
        dn_short = self.adc.convert(v_short)

        return dn_hcg, dn_lcg, dn_short


class DualConversionGainHDRFusion:
    """
    Bo ghep kenh Linear HDR 120 dB tu 3 dong du lieu 12-bit (HCG, LCG_long, LCG_short)
    kem chuyen tiep mem (Feathered Cross-Fade) chong giat SNR tai nguong ghep.
    """

    def __init__(self, afe: CMOSPixelAFE):
        self.afe = afe
        self.adc = afe.adc

    def reconstruct_linear_electrons(self, dn_hcg: int, dn_lcg: int, dn_short: int) -> float:
        e_from_hcg = self.adc.to_volts(dn_hcg) / self.afe.cg_hcg
        e_from_lcg = self.adc.to_volts(dn_lcg) / self.afe.cg_lcg
        e_from_short = (self.adc.to_volts(dn_short) / self.afe.cg_lcg) * self.afe.cfg.short_exp_ratio

        # Vung chuyen tiep 1: HCG (0..3800 DN) <-> LCG (75% .. 92% Full Scale = 3072 .. 3768 DN)
        lo_1, hi_1 = 3000.0, 3800.0
        if dn_hcg <= lo_1:
            e_stage1 = e_from_hcg
        elif dn_hcg >= hi_1:
            e_stage1 = e_from_lcg
        else:
            w = (dn_hcg - lo_1) / (hi_1 - lo_1)
            e_stage1 = (1.0 - w) * e_from_hcg + w * e_from_lcg

        # Vung chuyen tiep 2: LCG_long <-> LCG_short (75% .. 92% Full Scale cua LCG)
        if dn_lcg <= lo_1:
            return e_stage1
        elif dn_lcg >= hi_1:
            return e_from_short
        else:
            w2 = (dn_lcg - lo_1) / (hi_1 - lo_1)
            return (1.0 - w2) * e_stage1 + w2 * e_from_short


def test_cmos_cds_dcg_hdr_afe():
    """Chuong trinh kiem thu mach doc 4T-PPD CDS & Ghep kenh HDR 120 dB."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BL (NHOM 51) - BAI 200 (MILESTONE BL.1)")
    print("CAM BIEN CMOS 4T-PPD AFE: TRIET TIEU kTC BANG CDS & HDR KEP 120 dB")
    print("=" * 80)

    rng = random.Random(20261115)
    cfg = CMOS4TPixelConfig()
    afe = CMOSPixelAFE(cfg)
    hdr = DualConversionGainHDRFusion(afe)

    print(
        f"\n[Thong so vat ly 4T-PPD] CG_HCG = {afe.cg_hcg*1e6:6.2f} uV/e- | "
        f"CG_LCG = {afe.cg_lcg*1e6:5.2f} uV/e- | Nhieu kTC tho HCG = {afe.sigma_ktc_hcg*1e3:4.2f} mV"
    )

    # 1. Kiem thu Monte-Carlo 2,000 pixel toi (12 e- signal) co FPN V_th +/- 0.8 mV & nhieu kTC
    print("\n[1] Kiem thu triet tieu nhieu kTC & V_th FPN tren 2,000 pixel vung toi (12 e-):")
    true_dark_e = 12.0
    errs_nocds: List[float] = []
    errs_cds: List[float] = []
    for _ in range(2000):
        v_fpn = rng.gauss(0.0, 0.80e-3)
        est_nocds = afe.readout_hcg_pixel(true_dark_e, v_fpn, use_cds=False, rng=rng)
        est_cds = afe.readout_hcg_pixel(true_dark_e, v_fpn, use_cds=True, rng=rng)
        errs_nocds.append(est_nocds - true_dark_e)
        errs_cds.append(est_cds - true_dark_e)

    rms_nocds = math.sqrt(sum(e * e for e in errs_nocds) / len(errs_nocds))
    rms_cds = math.sqrt(sum(e * e for e in errs_cds) / len(errs_cds))
    gain_db = 20.0 * math.log10(rms_nocds / rms_cds)

    print(f"  * KHONG CDS (Hung tron kTC + FPN) : Read Noise RMS = {rms_nocds:5.2f} e- (Mat chi tiet toi!)")
    print(f"  * CO CDS (Reset - Signal Diff)    : Read Noise RMS = {rms_cds:5.2f} e- (Giam {gain_db:.1f} dB nhieu!)")

    assert rms_nocds > 14.0 and rms_cds < 2.2 and gain_db > 18.0
    print("  -> Ket luan: Mach lay mau CDS xoa sach nhieu kTC & FPN (> 18 dB cai thien) (PASS)!")

    # 2. Kiem thu dai dong 120 dB tren thang chieu sang tu 10 e- (ham toi) -> 1,100,000 e- (den pha)
    print("\n[2] Kiem thu tuyen tinh HDR 120 dB tu 10 e- (Ham toi) den 1,100,000 e- (Den pha xe):")
    test_levels = [10.0, 100.0, 2000.0, 8000.0, 35000.0, 120000.0, 500000.0, 1100000.0]
    rel_errors: List[float] = []

    for level in test_levels:
        trials = 250
        acc = 0.0
        for _ in range(trials):
            d_h, d_l, d_s = afe.capture_triple_tap_dns(level, 0.5e-3, rng)
            acc += hdr.reconstruct_linear_electrons(d_h, d_l, d_s)
        mean_est = acc / trials
        rel_err_pct = abs(mean_est - level) / level * 100.0
        rel_errors.append(rel_err_pct)
        print(
            f"  * Input = {level:10.1f} e- | HDR Tai tao = {mean_est:10.1f} e- | "
            f"Sai so tuyen tinh = {rel_err_pct:4.2f}%"
        )

    eff_fwc = (cfg.v_adc_fs / afe.cg_lcg) * cfg.short_exp_ratio
    dr_db = 20.0 * math.log10(eff_fwc / rms_cds)
    print(f"  * Dai dong he thong dat duoc    : {dr_db:5.2f} dB (Effective FWC = {eff_fwc:,.0f} e-)")

    assert dr_db >= 115.0 and max(rel_errors) < 3.5
    print("  -> Ket luan: Kien truc DCG + Short Exposure dat > 115 dB va tuyen tinh < 3.5% (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 200: CMOS 4T-PPD CDS & 120 dB DCG HDR HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_cmos_cds_dcg_hdr_afe()
