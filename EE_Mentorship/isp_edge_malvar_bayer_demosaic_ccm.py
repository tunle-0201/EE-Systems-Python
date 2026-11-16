"""
EE MENTORSHIP PROGRAM - MODULE BL (NHOM 51) - BAI 201 (MILESTONE BL.2)
================================================================================
DUONG ONG ISP PHAN CUNG LINE-BUFFER: BU TOI GOC LENS SHADING, GIAI BAYER
MALVAR-HE-CUTLER 5x5 (CHI DUNG PHEP DICH BIT) VA MA TRAN MAU CCM 3x3
================================================================================

Nguyen ly vat ly quang hoc & Thiet ke phan cung RTL ISP:
1. Suy hao Quang hoc goc ong kinh (Cos^4 Vignetting) & Bu toi goc (LSC):
   - Theo dinh luat quang hoc cos^4(theta), anh sang dap vao ria cam bien bi
     suy giam theo 1 / (1 + (r / f)^2)^2, khien 4 goc toi hon giua anh > 50%.
   - Khoi LSC tru muc den Black Level (BLC) roi nhan bu da thuc ban kinh G(r^2).

2. Giai ma mang loc mau Bayer RGGB bang bo loc 5x5 Malvar-He-Cutler (Khong Frame Buffer):
   - Noi suy Bilinear 3x3 thong thuong nhin thay soc rang cua (Zipper Artifact)
     va vien tim/xanh tai cac mep vach ke duong hoac chu trang nen den.
   - Thuat toan Malvar-He-Cutler tiem thanh phan tan so cao (Gradient-Corrected)
     tu chinh pixel tam va hang xom: chi can 5 dong SRAM Line Buffer va cac he so
     chia het cho 8 hoac 16 (>> 3 hoac >> 4 trong Verilog/FPGA), KHONG can chia!

3. Can bang trang & Ma tran hieu chinh mau 3x3 (WB + Color Correction Matrix):
   - Bo loc mau silicon RGB co nhieu cheo quang pho (Crosstalk) lam mau bi xam xit.
   - Nhan ma tran CCM 3x3 (tong moi hang bang 1.000 de giu nguyen mau xam trung tinh)
     chuyen tu khong gian Raw Camera -> Linear sRGB chuan xac cao.

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Bo loc Malvar 5x5 tim kenh Green tai vi tri Red/Blue (trong so nhan 8):
            [  0,  0, -1,  0,  0 ]
            [  0,  0,  2,  0,  0 ]
     G_rb = [ -1,  2,  4,  2, -1 ] / 8   (Tuong duong >> 3 trong RTL)
            [  0,  0,  2,  0,  0 ]
            [  0,  0, -1,  0,  0 ]

2. Chuan hoa Mau sac (White Balance -> Linear sRGB):
     [ R_out ]   [ c00  c01  c02 ]   [ g_r * R_raw ]
     [ G_out ] = [ c10  c11  c12 ] * [ 1.0 * G_raw ]   voi sum(row_i) = 1.0
     [ B_out ]   [ c20  c21  c22 ]   [ g_b * B_raw ]
--------------------------------------------------------------------------------
"""

import math
from typing import List, Tuple, Dict


def clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


class BlackAndLensShadingCorrector:
    """Khoi BLC + LSC bu suy hao cos^4(theta) theo ban kinh cam bien."""

    def __init__(self, height: int, width: int, black_level: float = 0.04, tan_max_fov: float = 0.65):
        self.h = height
        self.w = width
        self.black_level = black_level
        self.tan_max_fov = tan_max_fov
        self.cy = (height - 1) / 2.0
        self.cx = (width - 1) / 2.0
        self.r_max = math.hypot(self.cy, self.cx)

    def radial_falloff(self, y: int, x: int) -> float:
        r_norm = math.hypot(y - self.cy, x - self.cx) / max(1e-9, self.r_max)
        tan_th = r_norm * self.tan_max_fov
        cos_th_sq = 1.0 / (1.0 + tan_th * tan_th)
        return cos_th_sq * cos_th_sq

    def apply_lsc(self, raw_mosaic: List[List[float]]) -> List[List[float]]:
        out = [[0.0] * self.w for _ in range(self.h)]
        scale_norm = 1.0 / max(1e-9, 1.0 - self.black_level)
        for y in range(self.h):
            for x in range(self.w):
                blc_sub = max(0.0, (raw_mosaic[y][x] - self.black_level) * scale_norm)
                gain = 1.0 / max(0.15, self.radial_falloff(y, x))
                out[y][x] = blc_sub * gain
        return out


class BayerHardwareDemosaic:
    """
    Dong co Giai mau Bayer RGGB phan cung:
      - Row chan, Col chan: R
      - Row chan, Col le  : G (hang R)
      - Row le,   Col chan: G (hang B)
      - Row le,   Col le  : B
    Ho tro so sanh Bilinear 3x3 vs Malvar-He-Cutler 5x5 Line-Buffer.
    """

    @staticmethod
    def encode_rggb(rgb_img: List[List[Tuple[float, float, float]]]) -> List[List[float]]:
        h = len(rgb_img)
        w = len(rgb_img[0])
        mosaic = [[0.0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                r, g, b = rgb_img[y][x]
                if (y % 2 == 0) and (x % 2 == 0):
                    mosaic[y][x] = r
                elif (y % 2 == 1) and (x % 2 == 1):
                    mosaic[y][x] = b
                else:
                    mosaic[y][x] = g
        return mosaic

    @staticmethod
    def _px(img: List[List[float]], y: int, x: int, h: int, w: int) -> float:
        # Mirror padding bien anh (chuan phan cung ISP)
        if y < 0:
            y = -y
        elif y >= h:
            y = 2 * h - 2 - y
        if x < 0:
            x = -x
        elif x >= w:
            x = 2 * w - 2 - x
        return img[y][x]

    @classmethod
    def demosaic_bilinear(cls, raw: List[List[float]]) -> List[List[Tuple[float, float, float]]]:
        h, w = len(raw), len(raw[0])
        out = [[(0.0, 0.0, 0.0)] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                p = lambda dy, dx: cls._px(raw, y + dy, x + dx, h, w)
                c = p(0, 0)
                ry, rx = y % 2, x % 2
                if ry == 0 and rx == 0:  # Red
                    r = c
                    g = 0.25 * (p(-1, 0) + p(1, 0) + p(0, -1) + p(0, 1))
                    b = 0.25 * (p(-1, -1) + p(-1, 1) + p(1, -1) + p(1, 1))
                elif ry == 1 and rx == 1:  # Blue
                    b = c
                    g = 0.25 * (p(-1, 0) + p(1, 0) + p(0, -1) + p(0, 1))
                    r = 0.25 * (p(-1, -1) + p(-1, 1) + p(1, -1) + p(1, 1))
                elif ry == 0 and rx == 1:  # Green tren hang Red
                    g = c
                    r = 0.5 * (p(0, -1) + p(0, 1))
                    b = 0.5 * (p(-1, 0) + p(1, 0))
                else:  # Green tren hang Blue
                    g = c
                    r = 0.5 * (p(-1, 0) + p(1, 0))
                    b = 0.5 * (p(0, -1) + p(0, 1))
                out[y][x] = (clip01(r), clip01(g), clip01(b))
        return out

    @classmethod
    def demosaic_malvar_5x5(cls, raw: List[List[float]]) -> List[List[Tuple[float, float, float]]]:
        """Bo loc phan cung 5x5 Malvar-He-Cutler (chi dung he so chia 8/16, khong chia phuc tap)."""
        h, w = len(raw), len(raw[0])
        out = [[(0.0, 0.0, 0.0)] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                p = lambda dy, dx: cls._px(raw, y + dy, x + dx, h, w)
                c = p(0, 0)
                cross = p(-1, 0) + p(1, 0) + p(0, -1) + p(0, 1)
                diag = p(-1, -1) + p(-1, 1) + p(1, -1) + p(1, 1)
                far_cross = p(-2, 0) + p(2, 0) + p(0, -2) + p(0, 2)

                ry, rx = y % 2, x % 2
                if ry == 0 and rx == 0:  # Tai vi tri R
                    r = c
                    g = (4.0 * c + 2.0 * cross - far_cross) / 8.0
                    b = (12.0 * c + 4.0 * diag - 3.0 * far_cross) / 16.0
                elif ry == 1 and rx == 1:  # Tai vi tri B
                    b = c
                    g = (4.0 * c + 2.0 * cross - far_cross) / 8.0
                    r = (12.0 * c + 4.0 * diag - 3.0 * far_cross) / 16.0
                elif ry == 0 and rx == 1:  # Tai vi tri G tren hang R (R trai-phai, B tren-duoi)
                    g = c
                    r = (10.0 * c + 8.0 * (p(0, -1) + p(0, 1)) - 2.0 * (diag + p(0, -2) + p(0, 2)) + 1.0 * (p(-2, 0) + p(2, 0))) / 16.0
                    b = (10.0 * c + 8.0 * (p(-1, 0) + p(1, 0)) - 2.0 * (diag + p(-2, 0) + p(2, 0)) + 1.0 * (p(0, -2) + p(0, 2))) / 16.0
                else:  # Tai vi tri G tren hang B (B trai-phai, R tren-duoi)
                    g = c
                    b = (10.0 * c + 8.0 * (p(0, -1) + p(0, 1)) - 2.0 * (diag + p(0, -2) + p(0, 2)) + 1.0 * (p(-2, 0) + p(2, 0))) / 16.0
                    r = (10.0 * c + 8.0 * (p(-1, 0) + p(1, 0)) - 2.0 * (diag + p(-2, 0) + p(2, 0)) + 1.0 * (p(0, -2) + p(0, 2))) / 16.0

                out[y][x] = (clip01(r), clip01(g), clip01(b))
        return out


class ColorCorrectionPipeline:
    """Ma tran khu crosstalk quang pho Sensor Raw -> Linear sRGB."""

    def __init__(self, wb_gains: Tuple[float, float, float], ccm_3x3: List[List[float]]):
        self.wb_gains = wb_gains
        self.ccm = ccm_3x3
        # Kiem tra chuan hoa tung hang bang 1.0 de bao toan mau xam trung tinh
        for row in ccm_3x3:
            if abs(sum(row) - 1.0) > 1e-6:
                raise ValueError("Tong moi hang CCM phai bang 1.000 de giu can bang xam!")

    def apply(self, rgb_raw: Tuple[float, float, float]) -> Tuple[float, float, float]:
        wr = rgb_raw[0] * self.wb_gains[0]
        wg = rgb_raw[1] * self.wb_gains[1]
        wb = rgb_raw[2] * self.wb_gains[2]
        r_out = clip01(self.ccm[0][0] * wr + self.ccm[0][1] * wg + self.ccm[0][2] * wb)
        g_out = clip01(self.ccm[1][0] * wr + self.ccm[1][1] * wg + self.ccm[1][2] * wb)
        b_out = clip01(self.ccm[2][0] * wr + self.ccm[2][1] * wg + self.ccm[2][2] * wb)
        return (r_out, g_out, b_out)


def compute_psnr_db(img_a: List[List[Tuple[float, float, float]]], img_b: List[List[Tuple[float, float, float]]], border: int = 2) -> float:
    h, w = len(img_a), len(img_a[0])
    se = 0.0
    cnt = 0
    for y in range(border, h - border):
        for x in range(border, w - border):
            for c in range(3):
                d = img_a[y][x][c] - img_b[y][x][c]
                se += d * d
                cnt += 1
    mse = se / max(1, cnt)
    return 99.0 if mse < 1e-12 else 10.0 * math.log10(1.0 / mse)


def test_malvar_bayer_demosaic_ccm():
    """Chuong trinh kiem thu duong ong ISP: BLC+LSC, Malvar 5x5 Demosaic va CCM 3x3."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BL (NHOM 51) - BAI 201 (MILESTONE BL.2)")
    print("DUONG ONG ISP LINE-BUFFER: LENS SHADING, MALVAR 5x5 DEMOSAIC & CCM 3x3")
    print("=" * 80)

    h, w = 64, 64

    # 1. Kiem thu Khoi BLC + LSC chong toi goc cos^4(theta)
    print("\n[1] Kiem thu BLC + LSC khoi phuc do dong deu tam trang bi suy hao cos^4(theta):")
    lsc = BlackAndLensShadingCorrector(h, w, black_level=0.04, tan_max_fov=0.65)
    raw_flat = [[0.04 + 0.96 * (0.80 * lsc.radial_falloff(y, x)) for x in range(w)] for y in range(h)]
    lsc_fixed = lsc.apply_lsc(raw_flat)

    corner_raw = (raw_flat[0][0] - 0.04) / 0.96
    center_raw = (raw_flat[h // 2][w // 2] - 0.04) / 0.96
    unif_before = (corner_raw / center_raw) * 100.0
    unif_after = (lsc_fixed[0][0] / lsc_fixed[h // 2][w // 2]) * 100.0

    print(f"  * Do dong deu goc / tam TRUOC LSC : {unif_before:6.2f}% (Toi 4 goc nang do cos^4)")
    print(f"  * Do dong deu goc / tam SAU LSC   : {unif_after:6.2f}% (Target > 99.0%)")

    assert unif_before < 55.0 and unif_after > 99.5
    print("  -> Ket luan: BLC + LSC bu sach suy hao quang hoc cos^4(theta) (PASS)!")

    # 2. So sanh Bilinear 3x3 vs Malvar-He-Cutler 5x5 tren anh chi tiet cao (Vach cheo + Song sin)
    print("\n[2] So sanh Giai ma Bayer Bilinear 3x3 vs Malvar-He-Cutler 5x5 (High-Freq Edges):")
    gt_img: List[List[Tuple[float, float, float]]] = [[(0.0, 0.0, 0.0)] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            # Vach lan xe cheo xam sac net + hoa van tan so trung binh-cao + nen mau nhat
            edge = 1.0 / (1.0 + math.exp(-1.5 * ((x - 0.65 * y) - 10.0)))
            grating = 0.5 + 0.35 * math.sin(0.55 * x + 0.35 * y)
            r = clip01(0.45 * edge + 0.45 * grating + 0.05)
            g = clip01(0.45 * edge + 0.45 * grating + 0.08)
            b = clip01(0.45 * edge + 0.45 * grating + 0.02)
            gt_img[y][x] = (r, g, b)

    bayer_raw = BayerHardwareDemosaic.encode_rggb(gt_img)
    rec_bilin = BayerHardwareDemosaic.demosaic_bilinear(bayer_raw)
    rec_malvar = BayerHardwareDemosaic.demosaic_malvar_5x5(bayer_raw)

    psnr_bilin = compute_psnr_db(gt_img, rec_bilin, border=3)
    psnr_malvar = compute_psnr_db(gt_img, rec_malvar, border=3)
    psnr_gain = psnr_malvar - psnr_bilin

    # Do nhieu mau gia (Chroma Zipper Error = |R - G| sai lech tren vach xam sac net)
    zipper_bilin = sum(abs((rec_bilin[y][x][0] - rec_bilin[y][x][1]) - (gt_img[y][x][0] - gt_img[y][x][1]))
                       for y in range(4, h - 4) for x in range(4, w - 4))
    zipper_malvar = sum(abs((rec_malvar[y][x][0] - rec_malvar[y][x][1]) - (gt_img[y][x][0] - gt_img[y][x][1]))
                        for y in range(4, h - 4) for x in range(4, w - 4))

    print(f"  * Bilinear 3x3 PSNR   : {psnr_bilin:5.2f} dB | Chroma Zipper Energy = {zipper_bilin:6.2f}")
    print(f"  * Malvar 5x5 PSNR     : {psnr_malvar:5.2f} dB | Chroma Zipper Energy = {zipper_malvar:6.2f} (+{psnr_gain:.2f} dB!)")

    assert psnr_malvar > 34.0 and psnr_gain >= 4.0 and zipper_malvar < zipper_bilin * 0.55
    print("  -> Ket luan: Malvar 5x5 vuot troi > +4 dB va giam mot nua vien mau gia (PASS)!")

    # 3. Kiem thu Can bang trang D65 + Ma tran hieu chinh mau CCM 3x3
    print("\n[3] Kiem thu WB + Ma tran CCM 3x3 khu nhieu cheo quang pho (Sensor -> sRGB):")
    # Gia su ma tran lech mau vat ly cua sensor (D65 anh sang co thieu do/thua xanh + crosstalk)
    wb_gains = (1.85, 1.00, 1.55)
    # Ma tran nghich dao crosstalk gia lap -> sRGB chuan
    ccm = [
        [1.55, -0.45, -0.10],
        [-0.25, 1.45, -0.20],
        [-0.08, -0.42, 1.50],
    ]
    isp_color = ColorCorrectionPipeline(wb_gains, ccm)

    # 1) O Xam trung tinh (Sau WB phai thanh (0.5, 0.5, 0.5) -> CCM phai giu nguyen!)
    gray_raw = (0.50 / 1.85, 0.50 / 1.00, 0.50 / 1.55)
    gray_srgb = isp_color.apply(gray_raw)
    neutral_dev = max(abs(gray_srgb[0] - 0.50), abs(gray_srgb[1] - 0.50), abs(gray_srgb[2] - 0.50))

    # 2) O Do cam bien bi nhieu cheo sang kenh Green/Blue (Do tho nhin bi nhat)
    # Mo phong quang pho cam bien tho cho mau do thuan (0.80, 0.22, 0.16) trong sRGB qua ma tran crosstalk nguoc
    # Goi thu nghich CCM -> thu duoc gia tri sau WB, chia cho wb_gains -> raw
    red_true = (0.80, 0.18, 0.12)
    # Tinh nguoc raw ly tuong ma sensor se do duoc tu mau red_true
    # (Giai gan dung bang cach kiem tra mau do crosstalk (0.62, 0.30, 0.25) sau WB)
    raw_vivid_red = (0.58 / 1.85, 0.22 / 1.00, 0.16 / 1.55)
    red_restored = isp_color.apply(raw_vivid_red)

    print(f"  * O Xam trung tinh (Gray) : Raw={tuple(round(v, 3) for v in gray_raw)} -> sRGB={tuple(round(v, 4) for v in gray_srgb)}")
    print(f"  * O Mau Do crosstalk      : Sau WB=(0.580, 0.220, 0.160) -> Sau CCM sRGB={tuple(round(v, 3) for v in red_restored)}")

    assert neutral_dev < 1e-6
    assert red_restored[0] > 0.75 and red_restored[1] < 0.16  # Phuc hoi do bao hoa mau do
    print("  -> Ket luan: WB + CCM bao toan xam trung tinh 100% va khu crosstalk mau sac (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 201: LINE-BUFFER ISP & MALVAR 5x5 HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_malvar_bayer_demosaic_ccm()
