"""
================================================================================
CHUYEN DE AI: PHASED ARRAY BEAMSTEERING & FMCW SYNTHETIC APERTURE RADAR (SAR)
BAI 3: THUAT TOAN TAI TAO ANH RADAR KHAU DO TONG HOP SAR BACKPROJECTION ALGORITHM
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Tai tao anh phan xa Radar 2D do phan giai cao xuyen suong mu cho Tesla FSD / Ve tinh
Ngon ngu: Python 3 thuan tuy, tich luy ket hop pha Coherent Backprojection tren luoi Pixel
================================================================================
"""

import math
from typing import List, Tuple, Dict

SPEED_OF_LIGHT = 299792458.0 # m/s

# ------------------------------------------------------------------------------
# 1. CAC THONG SO HE THONG RADAR SAR
# ------------------------------------------------------------------------------

class SARSystemConfig:
    """
    Cau hinh he thong Radar Khau do Tong hop SAR:
    - freq_center: Tan so song mang cao tan (vi du 10 GHz X-Band hoac 77 GHz mmWave)
    - bandwidth: Bang thong FMCW (vi du 1.5 GHz -> Do phan giai cu ly c / (2B) = 10 cm)
    - platform_speed: Van toc di chuyen cua xe / ve tinh (m/s)
    - prf: Tan so lap xung Pulse Repetition Frequency (Hz)
    """
    def __init__(self,
                 freq_center: float = 10.0e9, # 10 GHz (X-Band SAR)
                 bandwidth: float = 1.5e9,    # 1.5 GHz
                 platform_speed: float = 10.0,# 10 m/s
                 synthetic_length: float = 4.0): # Khau do tong hop ao dai 4.0m
        self.fc = freq_center
        self.bw = bandwidth
        self.v = platform_speed
        self.L_syn = synthetic_length

        self.wavelength = SPEED_OF_LIGHT / freq_center # 3.0 cm
        # Do phan giai cu ly ly thuyet: Delta_R = c / (2 * B)
        self.range_res = SPEED_OF_LIGHT / (2.0 * bandwidth) # 10.0 cm

# ------------------------------------------------------------------------------
# 2. BO TAI TAO ANH SAR BACKPROJECTION ALGORITHM (BPA)
# ------------------------------------------------------------------------------

class SARBackprojectionProcessor:
    """
    Bo xu ly anh SAR bang thuat toan chieu nguoc Coherent Backprojection:
    Tich luy nang luong dong pha tu moi vi tri xung radar vao tung pixel (x, y).
    I(x, y) = sum_k [ S_k(R_k) * exp(j * 4*pi*R_k / lambda) ]
    """
    def __init__(self, config: SARSystemConfig):
        self.cfg = config
        self.k_wavenumber = (2.0 * math.pi) / config.wavelength

    def simulate_radar_echoes(self,
                              radar_positions_x: List[float],
                              targets: List[Tuple[float, float, float]]) -> List[Dict[str, any]]:
        """
        Mo phong tin hieu thu nhan duoc doc theo quy dao bay:
        - radar_positions_x: Danh sach toa do X cua radar doc quy dao (Y = 0)
        - targets: Danh sach cac vat phan xa (x_tgt, y_tgt, rcs_sigma)
        Tra ve: Danh sach cac xung da nen cu ly (Range Profiles)
        """
        echoes = []
        for x_rad in radar_positions_x:
            pulse_data = []
            for x_t, y_t, rcs in targets:
                # Cu ly 2 chieu tu radar toi vat the
                dist = math.sqrt((x_t - x_rad) ** 2 + y_t ** 2)
                # Tin hieu phan xa co bien do rcs va pha quay 4*pi*dist / lambda
                phase = (4.0 * math.pi * dist) / self.cfg.wavelength
                pulse_data.append((dist, rcs, phase))
            echoes.append({"x_pos": x_rad, "targets_info": pulse_data})
        return echoes

    def reconstruct_image_grid(self,
                               echoes: List[Dict[str, any]],
                               grid_x: List[float],
                               grid_y: List[float]) -> List[List[float]]:
        """
        Tai tao ma tran anh 2D tren luoi pixel (grid_x, grid_y) bang Backprojection:
        Doi voi moi pixel (px, py):
          Khoang cach R_k = sqrt((px - x_k)^2 + py^2)
          Cong dong pha: Acc += rcs * exp(j * (phi_received - 4*pi*R_k/lambda))
        """
        num_y = len(grid_y)
        num_x = len(grid_x)
        image_intensity = [[0.0 for _ in range(num_x)] for _ in range(num_y)]

        for iy in range(num_y):
            py = grid_y[iy]
            for ix in range(num_x):
                px = grid_x[ix]

                coherent_real = 0.0
                coherent_imag = 0.0

                for pulse in echoes:
                    x_rad = pulse["x_pos"]
                    # Khoang cach tu radar den pixel (px, py)
                    r_pixel = math.sqrt((px - x_rad) ** 2 + py ** 2)
                    expected_phase = (4.0 * math.pi * r_pixel) / self.cfg.wavelength

                    # Kiem tra tin hieu phan xa tu cac vat the co trung cu ly r_pixel hay khong
                    for dist, rcs, rx_phase in pulse["targets_info"]:
                        # Neu khoang cach pixel gan voi khoang cach vat the (trong pham vi do phan giai Delta_R)
                        dist_diff = abs(r_pixel - dist)
                        if dist_diff < self.cfg.range_res:
                            # Ham envelope sinc/hanning thu nho khi lech cu ly
                            envelope = math.cos(0.5 * math.pi * (dist_diff / self.cfg.range_res))
                            # Bu pha (Phase Compensation)
                            phase_residual = rx_phase - expected_phase
                            coherent_real += rcs * envelope * math.cos(phase_residual)
                            coherent_imag += rcs * envelope * math.sin(phase_residual)

                # Cuong do sang pixel (Pixel Intensity) = |Coherent_Sum|^2
                intensity = coherent_real ** 2 + coherent_imag ** 2
                image_intensity[iy][ix] = intensity

        return image_intensity

# ------------------------------------------------------------------------------
# 3. MO PHONG VA KIEM CHUNG TAI TAO ANH SAR 2D
# ------------------------------------------------------------------------------

def test_sar_backprojection_imaging():
    """
    Kiem tra tai tao anh SAR:
    - Quy dao radar: Di chuyen doc truc X tu -2.0m den +2.0m (Khau do tong hop L_syn = 4.0m)
    - Dat 2 vat can kim loai (Targets) trong suong mu:
      Target 1 tai: (X = 0.0m, Y = 15.0m) voi RCS = 1.0
      Target 2 tai: (X = 1.0m, Y = 15.0m) voi RCS = 0.8
    - Luoi pixel tao anh: X tu -1.0m den +2.0m (buoc 0.1m), Y tu 14.0m den 16.0m (buoc 0.1m)
    - Kiem tra xem 2 diem sang cuc dai tren anh 2D co trung khop vi tri (0, 15) va (1, 15) hay khong!
    """
    cfg = SARSystemConfig(freq_center=10e9, bandwidth=1.5e9, synthetic_length=4.0)
    bpa = SARBackprojectionProcessor(cfg)

    # 41 vi tri phat xung radar doc quy dao X tu -2.0m den +2.0m (moi buoc 10 cm)
    num_pulses = 41
    radar_x_positions = [-2.0 + i * (4.0 / (num_pulses - 1)) for i in range(num_pulses)]

    # 2 vat can muc tieu
    true_targets = [
        (0.0, 15.0, 1.0), # Target 1
        (1.0, 15.0, 0.8)  # Target 2
    ]

    # 1. Mo phong thu nhan tin hieu radar
    echoes = bpa.simulate_radar_echoes(radar_x_positions, true_targets)

    # 2. Xay dung luoi pixel tao anh 2D (Grid 31 x 21 diem anh)
    grid_x = [-1.0 + i * 0.1 for i in range(31)] # -1.0m den +2.0m
    grid_y = [14.0 + j * 0.1 for j in range(21)] # 14.0m den 16.0m

    print("Bat dau thuat toan SAR Coherent Backprojection tai tao anh 2D...")
    img = bpa.reconstruct_image_grid(echoes, grid_x, grid_y)

    # Tim 2 diem anh co cuong do sang cuc dai tren toan bo buc anh
    all_pixels = []
    for iy in range(len(grid_y)):
        for ix in range(len(grid_x)):
            all_pixels.append((img[iy][ix], grid_x[ix], grid_y[iy]))

    all_pixels.sort(key=lambda item: item[0], reverse=True)

    peak1_intensity, peak1_x, peak1_y = all_pixels[0]

    # Tim diem dinh thu hai cach xa diem thu nhat it nhat 0.5m
    peak2_intensity = 0.0
    peak2_x = 0.0
    peak2_y = 0.0
    for intens, x, y in all_pixels:
        dist_to_p1 = math.sqrt((x - peak1_x)**2 + (y - peak1_y)**2)
        if dist_to_p1 >= 0.5:
            peak2_intensity = intens
            peak2_x = x
            peak2_y = y
            break

    print("--------------------------------------------------------------------------------")
    print(f"KET QUA TAI TAO ANH RADAR KHAU DO TONG HOP 2D (SAR BACKPROJECTION):")
    print(f"-> Vi tri that Vat 1: (X =  0.0 m, Y = 15.0 m) | Phat hien SAR: (X = {peak1_x:4.1f} m, Y = {peak1_y:4.1f} m)")
    print(f"-> Vi tri that Vat 2: (X =  1.0 m, Y = 15.0 m) | Phat hien SAR: (X = {peak2_x:4.1f} m, Y = {peak2_y:4.1f} m)")
    print(f"-> Do phan giai cu ly Delta_R dat duoc : {cfg.range_res * 100.0:.1f} cm (Do rong xung FMCW 1.5 GHz)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Toa do vat the 1 phai phat hien dung tai (0.0, 15.0) sai so duoi 1 pixel (0.1m)
    err1 = math.sqrt((peak1_x - 0.0)**2 + (peak1_y - 15.0)**2)
    assert err1 <= 0.15, f"Loi toa do Vat 1: ({peak1_x}, {peak1_y}) lech {err1:.2f} m"
    # 2. Toa do vat the 2 phai phat hien dung tai (1.0, 15.0) sai so duoi 1 pixel (0.1m)
    err2 = math.sqrt((peak2_x - 1.0)**2 + (peak2_y - 15.0)**2)
    assert err2 <= 0.15, f"Loi toa do Vat 2: ({peak2_x}, {peak2_y}) lech {err2:.2f} m"
    print("[PASS] Test SAR Imaging: Tai tao anh phan xa 2D chinh xac 100%, nhin xuyen qua suong mu!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO SYNTHETIC APERTURE RADAR (SAR) COHERENT BACKPROJECTION 2D IMAGING")
    print("================================================================================")
    test_sar_backprojection_imaging()
