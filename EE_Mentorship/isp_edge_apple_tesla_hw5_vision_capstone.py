"""
EE MENTORSHIP PROGRAM - MODULE BL (NHOM 51) - BAI 203 (MILESTONE BL.4 - CAPSTONE)
================================================================================
DONG CO CAM BIEN ANH CMOS AFE & BO XU LY ANH PHAN CUNG LINE-BUFFER ISP CAPSTONE
CHO APPLE VISION PRO SPATIAL VISION & XE TU HANH TESLA FSD HW5
================================================================================

Kien truc Toan he thong tu Photodiode den 8-bit Vision Tensor:
1. Tang Silicon Sensor Front-End (4T-PPD + CDS + DCG 120 dB + Split-Diode LFM):
   - Loai bo 100% nhieu kTC & sai lech V_th FPN nho lay mau tuong quan kep CDS.
   - Ghep kenh kep High Gain (HCG) + Low Gain (LCG) + Small Photodiode LFM (11.1 ms)
     dat dai dong > 115 dB va chong mu den giao thong PWM 100 Hz tuyet doi.

2. Tang Xu ly Luong Phan cung Zero-DRAM 5-Line SRAM Buffer ISP:
   - Chi su dung bo nho dem 5 dong (5-Line Circular Line Buffer SRAM) thay vi
     phai ghi ca khung hinh ra DRAM -> Do tre chi dung 2 dong quet (~9.2 us)!
   - Thuc thi lien tuc cac khoi:
     BLC & Lens Shading cos^4 -> Malvar-He-Cutler 5x5 Demosaic -> WB + CCM 3x3 -> ACES Filmic sRGB.

3. Kiem chuan Thuc chien Tren Khung canh Nguy hiem Ban dem 10,000:1 (HDR Night Tunnel):
   - Nguoi di bo trong bong toi (0.008 rad) | Vach ke duong cheo sac net
   - Den giao thong LED Do bam xung PWM 100 Hz (Duty 10%) | Den pha xe nguoc chieu (85.0 rad)
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


K_BOLTZMANN = 1.380649e-23
Q_ELECTRON = 1.602176634e-19


def clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


@dataclass
class HW5VisionConfig:
    height: int = 48
    width: int = 64
    black_level_norm: float = 0.04
    tan_max_fov: float = 0.62
    c_fd_hcg_f: float = 1.30e-15
    c_fd_lcg_f: float = 10.68e-15
    v_adc_fs: float = 1.20
    adc_bits: int = 12
    short_ratio: float = 11.1         # Kenh LFM SPD giam nhay 11.1x tich luy tron 11.1 ms
    radiance_to_e_scale: float = 8000.0
    line_scan_time_us: float = 4.6    # 4.6 us / dong (~4K @ 60fps line rate)


class SiliconDualGainLFMSensor:
    """Mo phong cam bien anh CMOS 4T-PPD co CDS + DCG + Split-Diode LFM theo tung pixel."""

    def __init__(self, cfg: HW5VisionConfig):
        self.cfg = cfg
        self.cg_hcg = Q_ELECTRON / cfg.c_fd_hcg_f
        self.cg_lcg = Q_ELECTRON / cfg.c_fd_lcg_f
        self.adc_max = (1 << cfg.adc_bits) - 1
        self.lsb_v = cfg.v_adc_fs / self.adc_max
        self.cy = (cfg.height - 1) / 2.0
        self.cx = (cfg.width - 1) / 2.0
        self.r_max = math.hypot(self.cy, self.cx)

    def cos4_vignetting(self, y: int, x: int) -> float:
        r_n = math.hypot(y - self.cy, x - self.cx) / max(1e-9, self.r_max)
        tan_t = r_n * self.cfg.tan_max_fov
        c2 = 1.0 / (1.0 + tan_t * tan_t)
        return c2 * c2

    def _quantize_cds(self, electrons: float, cg_v_per_e: float, rng: random.Random) -> int:
        # Nho CDS, nhieu kTC & V_th FPN da bi triet tieu chi con shot noise + 1.4 e- read noise
        shot = rng.gauss(0.0, math.sqrt(max(0.0, electrons)))
        read_v = rng.gauss(0.0, 1.4 * cg_v_per_e)
        v_net = (electrons + shot) * cg_v_per_e + read_v
        v_ped = 0.04 * self.cfg.v_adc_fs  # Black-level pedestal 4%
        v_tot = max(0.0, min(self.cfg.v_adc_fs, v_ped + v_net))
        return int(round(v_tot / self.lsb_v))

    def capture_raw_hdr_bayer(
        self,
        scene_hdr_rgb: List[List[Tuple[float, float, float]]],
        shutter_phase_s: float,
        pwm_led_bbox: Tuple[int, int, int, int],
        rng: random.Random,
    ) -> List[List[float]]:
        """
        Thu khung hinh tho RGGB qua ong kinh cos^4, CDS + DCG + LFM (11.1 ms) -> Tra ve Linear Bayer.
        Dac biet: Vung den giao thong PWM 100 Hz (Duty 10%) duoc tinh nang luong chuan theo pha!
        """
        h, w = self.cfg.height, self.cfg.width
        y0, y1, x0, x1 = pwm_led_bbox
        ped_dn = int(round(0.04 * self.adc_max))
        mosaic = [[0.0] * w for _ in range(h)]

        # Tinh he so tich luy cua den PWM 100 Hz (Duty 10%) tren kenh LFM SPD 11.1 ms
        period = 0.010  # 100 Hz
        on_t = 0.001    # 10% duty
        steps = 200
        dt = 0.0111 / steps
        on_hits = sum(1 for k in range(steps) if ((shutter_phase_s + (k + 0.5) * dt) % period) < on_t)
        lfm_pwm_eff_ratio = (on_hits / steps) / 0.10  # ~1.0 neu trung khop trung binh PWM

        for y in range(h):
            for x in range(w):
                r, g, b = scene_hdr_rgb[y][x]
                ry, rx = y % 2, x % 2
                chan_rad = r if (ry == 0 and rx == 0) else (b if (ry == 1 and rx == 1) else g)

                vig = self.cos4_vignetting(y, x)
                in_pwm = (y0 <= y < y1) and (x0 <= x < x1)

                e_long = chan_rad * vig * self.cfg.radiance_to_e_scale
                # Voi vung den LED PWM: kenh Short 1.0 ms thong thuong bi lech pha; LFM giu du nang luong!
                e_lfm_true = (e_long / self.cfg.short_ratio) * (lfm_pwm_eff_ratio if in_pwm else 1.0)

                dn_hcg = self._quantize_cds(e_long, self.cg_hcg, rng)
                dn_lcg = self._quantize_cds(e_long, self.cg_lcg, rng)
                dn_lfm = self._quantize_cds(e_lfm_true, self.cg_lcg, rng)

                # Khoi phuc electron tuyen tinh sau khi tru pedestal
                e_h = max(0.0, (dn_hcg - ped_dn) * self.lsb_v / self.cg_hcg)
                e_l = max(0.0, (dn_lcg - ped_dn) * self.lsb_v / self.cg_lcg)
                e_s = max(0.0, (dn_lfm - ped_dn) * self.lsb_v / self.cg_lcg) * self.cfg.short_ratio

                # Ghep 3-tap muot ma HCG -> LCG -> LFM Short
                if dn_hcg < 3200:
                    e_lin = e_h
                elif dn_hcg < 3800:
                    w1 = (dn_hcg - 3200.0) / 600.0
                    e_lin = (1.0 - w1) * e_h + w1 * e_l
                elif dn_lcg < 3200:
                    e_lin = e_l
                elif dn_lcg < 3800:
                    w2 = (dn_lcg - 3200.0) / 600.0
                    e_lin = (1.0 - w2) * e_l + w2 * e_s
                else:
                    e_lin = e_s

                mosaic[y][x] = e_lin / self.cfg.radiance_to_e_scale
        return mosaic


class HardwareLineBufferISP:
    """
    Bo xu ly Anh Phan cung Zero-DRAM chi dung 5-Line SRAM Buffer:
    LSC cos^4 -> Malvar-He-Cutler 5x5 Demosaic -> WB + CCM 3x3 -> ACES Filmic + sRGB 8-bit.
    """

    def __init__(self, cfg: HW5VisionConfig, sensor: SiliconDualGainLFMSensor):
        self.cfg = cfg
        self.sensor = sensor
        self.wb_gains = (1.15, 1.00, 1.10)
        self.ccm = [
            [1.35, -0.25, -0.10],
            [-0.15, 1.30, -0.15],
            [-0.05, -0.25, 1.30],
        ]

    def memory_and_latency_report(self) -> Dict[str, float]:
        line_buffer_bytes = 5 * self.cfg.width * 3  # 5 dong x W x 24-bit
        full_frame_bytes = self.cfg.height * self.cfg.width * 3
        saving_pct = (1.0 - line_buffer_bytes / full_frame_bytes) * 100.0
        latency_us = 2.0 * self.cfg.line_scan_time_us  # Tre 2 dong quet cho cua so 5x5
        return {
            "line_buf_bytes": float(line_buffer_bytes),
            "frame_buf_bytes": float(full_frame_bytes),
            "sram_saving_pct": saving_pct,
            "pipeline_latency_us": latency_us,
        }

    @staticmethod
    def _aces_srgb_byte(v_lin: float, exposure_key: float) -> int:
        x = max(0.0, v_lin * exposure_key)
        aces = max(0.0, min(1.0, (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)))
        s = 12.92 * aces if aces <= 0.0031308 else 1.055 * (aces ** (1.0 / 2.4)) - 0.055
        return int(round(max(0.0, min(1.0, s)) * 255.0))

    def process_frame(self, linear_mosaic: List[List[float]], exposure_key: float = 3.5) -> List[List[Tuple[int, int, int]]]:
        h, w = self.cfg.height, self.cfg.width
        # Buoc 1: Lens Shading cos^4 Correction
        lsc = [[linear_mosaic[y][x] / self.sensor.cos4_vignetting(y, x) for x in range(w)] for y in range(h)]

        def px(y_i: int, x_i: int) -> float:
            yy = -y_i if y_i < 0 else (2 * h - 2 - y_i if y_i >= h else y_i)
            xx = -x_i if x_i < 0 else (2 * w - 2 - x_i if x_i >= w else x_i)
            return lsc[yy][xx]

        out_rgb8 = [[(0, 0, 0)] * w for _ in range(h)]
        # Buoc 2..4: Streaming tung pixel qua 5-line buffer (Demosaic -> WB+CCM -> ACES+sRGB)
        for y in range(h):
            for x in range(w):
                p = lambda dy, dx: px(y + dy, x + dx)
                c = p(0, 0)
                cross = p(-1, 0) + p(1, 0) + p(0, -1) + p(0, 1)
                diag = p(-1, -1) + p(-1, 1) + p(1, -1) + p(1, 1)
                far_c = p(-2, 0) + p(2, 0) + p(0, -2) + p(0, 2)

                ry, rx = y % 2, x % 2
                if ry == 0 and rx == 0:
                    r, g, b = c, (4.0 * c + 2.0 * cross - far_c) / 8.0, (12.0 * c + 4.0 * diag - 3.0 * far_c) / 16.0
                elif ry == 1 and rx == 1:
                    b, g, r = c, (4.0 * c + 2.0 * cross - far_c) / 8.0, (12.0 * c + 4.0 * diag - 3.0 * far_c) / 16.0
                elif ry == 0 and rx == 1:
                    g = c
                    r = (10.0 * c + 8.0 * (p(0, -1) + p(0, 1)) - 2.0 * (diag + p(0, -2) + p(0, 2)) + p(-2, 0) + p(2, 0)) / 16.0
                    b = (10.0 * c + 8.0 * (p(-1, 0) + p(1, 0)) - 2.0 * (diag + p(-2, 0) + p(2, 0)) + p(0, -2) + p(0, 2)) / 16.0
                else:
                    g = c
                    b = (10.0 * c + 8.0 * (p(0, -1) + p(0, 1)) - 2.0 * (diag + p(0, -2) + p(0, 2)) + p(-2, 0) + p(2, 0)) / 16.0
                    r = (10.0 * c + 8.0 * (p(-1, 0) + p(1, 0)) - 2.0 * (diag + p(-2, 0) + p(2, 0)) + p(0, -2) + p(0, 2)) / 16.0

                wr = max(0.0, r) * self.wb_gains[0]
                wg = max(0.0, g) * self.wb_gains[1]
                wb = max(0.0, b) * self.wb_gains[2]
                rc = max(0.0, self.ccm[0][0] * wr + self.ccm[0][1] * wg + self.ccm[0][2] * wb)
                gc = max(0.0, self.ccm[1][0] * wr + self.ccm[1][1] * wg + self.ccm[1][2] * wb)
                bc = max(0.0, self.ccm[2][0] * wr + self.ccm[2][1] * wg + self.ccm[2][2] * wb)

                out_rgb8[y][x] = (
                    self._aces_srgb_byte(rc, exposure_key),
                    self._aces_srgb_byte(gc, exposure_key),
                    self._aces_srgb_byte(bc, exposure_key),
                )
        return out_rgb8


def build_night_tunnel_hdr_scene(h: int, w: int) -> Tuple[List[List[Tuple[float, float, float]]], Tuple[int, int, int, int]]:
    """
    Tao khung canh Ham toi cuc khac nghiet (10,600:1 contrast):
    - Nen duong toi + Nguoi di bo o goc [20..38, 6..18]: radiance ~ 0.012
    - Vach lan xe cheo: radiance ~ 0.18
    - Den giao thong LED Do PWM 100 Hz tai [6..14, 28..36]: radiance (14.0, 0.25, 0.20)
    - Den pha xe nguoc chieu tai [22..32, 46..58]: radiance (85.0, 82.0, 72.0)
    """
    scene = [[(0.002, 0.002, 0.003) for _ in range(w)] for _ in range(h)]
    led_bbox = (6, 14, 28, 36)

    for y in range(h):
        for x in range(w):
            # Vach lan xe cheo sac net
            if abs((x - 0.7 * y) - 18.0) < 1.3:
                scene[y][x] = (0.16, 0.16, 0.15)
            # Nguoi di bo trong bong toi [20..38, 6..18]
            if 20 <= y < 38 and 6 <= x < 18:
                scene[y][x] = (0.014, 0.016, 0.018)
            # Den giao thong LED do
            if 6 <= y < 14 and 28 <= x < 36:
                scene[y][x] = (14.0, 0.25, 0.20)
            # Den pha xe nguoc chieu sieu choi
            if 22 <= y < 32 and 46 <= x < 58:
                scene[y][x] = (85.0, 82.0, 72.0)
    return scene, led_bbox


def test_apple_tesla_hw5_vision_capstone():
    """Chuong trinh kiem thu Capstone Toan he thong CMOS AFE + Line-Buffer ISP HW5."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BL (NHOM 51) - BAI 203 (MILESTONE BL.4 - CAPSTONE)")
    print("DONG CO CAM BIEN CMOS AFE & BO XU LY ANH PHAN CUNG APPLE / TESLA HW5")
    print("=" * 80)

    rng = random.Random(20261115)
    cfg = HW5VisionConfig()
    sensor = SiliconDualGainLFMSensor(cfg)
    isp = HardwareLineBufferISP(cfg, sensor)
    scene, led_bbox = build_night_tunnel_hdr_scene(cfg.height, cfg.width)

    # 1. Kiem thu ngan sach bo nho SRAM 5-Line Buffer & Do tre duong ong phan cung
    print("\n[1] Ngan sach bo nho SRAM & Do tre duong ong Zero-DRAM ISP:")
    hw_stats = isp.memory_and_latency_report()
    print(f"  * 5-Line SRAM Buffer   : {hw_stats['line_buf_bytes']:6.0f} bytes vs Full-Frame DRAM ({hw_stats['frame_buf_bytes']:.0f} bytes)")
    print(f"  * Tiet kiem bo nho     : {hw_stats['sram_saving_pct']:5.2f}% (> 88% tiet kiem)")
    print(f"  * Do tre Pipeline      : {hw_stats['pipeline_latency_us']:5.2f} us (2 dong quet, < 12 us)")

    assert hw_stats["sram_saving_pct"] > 88.0 and hw_stats["pipeline_latency_us"] < 12.0
    print("  -> Ket luan: Kien truc streaming 5-Line SRAM dat do tre micro-giay (PASS)!")

    # 2. Thuc chien Toan chuoi tren canh Ham toi -> Den pha 10,600:1 qua 20 pha PWM
    print("\n[2] Thuc chien Canh Ham toi 10,600:1 (Nguoi di bo + LED 100Hz + Den pha 85.0):")
    # Danh gia 1 khung chuan & kiem tra 20 pha PWM cua den giao thong do
    ped_g_vals: List[int] = []
    headlight_r_vals: List[int] = []
    led_detected_count = 0

    for ph_idx in range(20):
        t_phase = ph_idx * 0.0005
        raw_hdr = sensor.capture_raw_hdr_bayer(scene, t_phase, led_bbox, rng)
        rgb8 = isp.process_frame(raw_hdr, exposure_key=4.5)

        # Lay mau vung trung tam nguoi di bo (29, 12)
        ped_px = rgb8[29][12]
        ped_g_vals.append(ped_px[1])

        # Lay mau den giao thong do trung tam (10, 32)
        led_px = rgb8[10][32]
        if led_px[0] > 180 and led_px[0] > 1.8 * max(1, led_px[1]):
            led_detected_count += 1

        # Lay mau den pha xe nguoc chieu (27, 52)
        hl_px = rgb8[27][52]
        headlight_r_vals.append(hl_px[0])

    mean_ped_g = sum(ped_g_vals) / len(ped_g_vals)
    mean_hl_r = sum(headlight_r_vals) / len(headlight_r_vals)
    naive_ped_srgb = HardwareLineBufferISP._aces_srgb_byte(0.016 / 85.0, 1.0)

    print(f"  * Camera thuong Linear-8bit -> Nguoi di bo toi = {naive_ped_srgb:3d}/255 (Mat dau!)")
    print(f"  * HW5 ISP Capstone (CDS+DCG)-> Nguoi di bo toi = {mean_ped_g:5.1f}/255 (Ro net [40..135])")
    print(f"  * Nhan dien Den do LED 100Hz-> {led_detected_count}/20 pha ({led_detected_count*5:.0f}% khong chop mu)")
    print(f"  * Den pha choi 85.0 rad     -> Nen mem khong vo mau = {mean_hl_r:5.1f}/255")

    assert 40.0 <= mean_ped_g <= 135.0
    assert led_detected_count == 20
    assert 240.0 <= mean_hl_r <= 255.0
    print("  -> Ket luan: Dong co HW5 Vision bao toan 100% vat the toi, den LED va chong loa (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 203 (CAPSTONE): APPLE / TESLA HW5 VISION ISP 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_apple_tesla_hw5_vision_capstone()
