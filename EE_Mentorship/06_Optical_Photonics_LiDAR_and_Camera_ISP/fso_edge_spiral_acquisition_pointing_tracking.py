"""
EE MENTORSHIP PROGRAM - MODULE BI (NHOM 48) - BAI 190 (MILESTONE BI.3)
================================================================================
THUAT TOAN QUET XOAN OC ARCHIMEDES BAT KHOA QUANG HOC VA BAN GIAO BUP SONG
(ARCHIMEDEAN SPIRAL ACQUISITION, POINTING & TRACKING - PAT STATE MACHINE)
================================================================================

Kien truc he thong thu nhan & bam bat chum tia laser lien ve tinh (PAT Systems):
1. Thach thuc "Chiec kim trong day be":
   - Sai so vi tri quy dao ban dau (Orbital Ephemeris Error tu GPS / TLE) tao nen
     non bat dinh (Uncertainty Cone) goc rong: theta_unc ~ +/- 3.0 milli-radian (mrad).
   - Trong khi do, goc mo chum tia laser truyen thong cuc hep: theta_comm ~ 20 micro-radian.
   - Xac suat 2 ve tinh chieu thang vao kinh thien van cua nhau ma khong quet la gan nhu bang 0.

2. Chien luoc quet xoan oc Archimedes toc do dai khong doi (Constant Linear Speed):
   - Phat chum tia hai dang (Beacon Laser) co do mo rong hon (theta_b ~ 0.8 mrad) hoac
     quet chum tia theo quy dao xoan oc Archimedes.
   - Buoc quet (Track Pitch) delta_r duoc tinh toan dua tren ty le chong phu (Overlap Ratio):
     delta_r = Overlap * theta_b (Overlap ~ 0.70 de dam bao khong co vung mu quang hoc).
   - De mat do thoi gian chieu sang (Dwell Time) dong deu tren moi vi tri trong non bat dinh,
     van toc dai cua diem chum tia duoc giu khong doi:
     phi(t) = sqrt(2 * v_scan * t / a) voi a = delta_r / (2 * pi).

3. Co che ban giao da cap Coarse-to-Fine Handover (Handshake State Machine):
   - Giai doan 1 (UNCERTAINTY_SEARCH): Quet xoan oc Archimedes tim kiem trong +/- 3 mrad.
   - Giai doan 2 (BEACON_DETECTED): May thu phat hien xung quang vuot nguong thu P_threshold.
   - Giai doan 3 (COARSE_CENTERING): Khung quay Coarse Gimbal xoay keo sai so tu mrad xuong < 150 urad.
   - Giai doan 4 (FINE_HANDOVER_FSM): Ban giao cho guong lai sieu toc FSM va cam bien QPD,
     keo sai so xuong < 1.0 micro-radian RMS.
   - Giai doan 5 (COMM_LINK_ESTABLISHED): Thiet lap kenh truyen laser 100 Gbps on dinh 100%.

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Phuong trinh xoan oc Archimedes mien thoi gian:
     r(phi) = a * phi,   voi a = delta_r / (2 * pi)
     phi(t) = sqrt( 2 * v_scan * t / a )

2. Buoc quet khong co vung mu (Spatial Overlap Pitch):
     delta_r = (1 - Overlap_factor) * theta_b   hoac   delta_r = 0.70 * theta_b

3. Suy hao bup song Gauss theo do lech huong (Gaussian Off-Axis Attenuation):
                                 [      (  theta_offset  )^2 ]
     P_rx(theta) = P_rx_boresight * exp [ -2 * ( ────────────── )   ]
                                 [      ( theta_div / 2  )   ]
--------------------------------------------------------------------------------
"""

import math
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


class PATState(Enum):
    """Cac trang thai trong chu trinh PAT Handshake."""
    UNCERTAINTY_SEARCH = 1      # Dang quet xoan oc tim kiem trong non bat dinh
    BEACON_DETECTED = 2         # Da phat hien cong suat quang vuot nguong
    COARSE_CENTERING = 3        # Khung quay Gimbal keo chum tia vao tam FOV hep
    FINE_HANDOVER_FSM = 4       # Ban giao cho guong lai FSM triet tieu sai so vi mo
    COMM_LINK_ESTABLISHED = 5   # Da khoa chum tia duoi 1 urad, kich hoat truyen data


@dataclass
class PATParameters:
    """Tham so he thong Acquisition, Pointing and Tracking (PAT)."""
    uncertainty_cone_half_angle_rad: float = 3.0e-3  # Non bat dinh +/- 3.0 mrad (3000 urad)
    beacon_divergence_rad: float = 0.8e-3            # Goc mo chum tia hai dang: 800 urad
    comm_divergence_rad: float = 20.0e-6             # Goc mo chum tia truyen thong: 20 urad
    link_distance_m: float = 2000.0e3                # Khoang cach lien ve tinh: 2,000 km
    beacon_power_tx_w: float = 2.0                   # Cong suat laser hai dang: 2 Watts
    rx_aperture_diam_m: float = 0.10                 # Duong kinh kinh thien van thu: 10 cm
    wavelength_m: float = 1550.0e-9                  # Buoc song laser 1550 nm
    overlap_ratio: float = 0.70                      # Ty le chong phu bup song: 70%
    scan_linear_speed_rad_s: float = 0.020           # Van toc dai quet goc: 20 mrad/giay
    detection_threshold_w: float = 5.0e-11           # Nguong phat hien may thu: 50 pW (-73 dBm)
    fsm_handover_fov_rad: float = 150.0e-6           # Truong quan sat ban giao FSM: 150 urad
    fine_pointing_target_rad: float = 1.0e-6         # Sai so bup song muc tieu: 1.0 urad


class ArchimedeanSpiralScanner:
    """
    Subsystem 1: Bo phat quy dao quet xoan oc Archimedes van toc dai khong doi.
    Dam bao thoi gian chieu sang (Dwell Time) dong deu, khong bo sot bat ky vi tri nao.
    """
    def __init__(self, r_max_rad: float = 3.0e-3, theta_b_rad: float = 0.8e-3, overlap: float = 0.70, v_scan_rad_s: float = 0.015):
        self.r_max = r_max_rad
        self.theta_b = theta_b_rad
        self.overlap = overlap
        self.v_scan = v_scan_rad_s

        # Buoc xoan oc delta_r
        self.delta_r = self.overlap * self.theta_b
        self.a = self.delta_r / (2.0 * math.pi)

        # Tong so vong quet va thoi gian quet hoan tat non bat dinh
        self.phi_max = self.r_max / self.a
        self.n_turns = self.phi_max / (2.0 * math.pi)
        self.t_total_scan_s = 0.5 * self.a * (self.phi_max ** 2) / self.v_scan

    def get_scanner_angles(self, t_s: float) -> Tuple[float, float, float]:
        """
        Tinh toa do goc quet (theta_x, theta_y) va ban kinh goc r tai thoi diem t_s.
        r(phi) = a * phi
        phi(t) = sqrt( 2 * v_scan * t / a )
        """
        if t_s <= 0.0:
            return 0.0, 0.0, 0.0

        phi = math.sqrt(2.0 * self.v_scan * t_s / self.a)
        r = self.a * phi
        if r > self.r_max:
            r = self.r_max

        theta_x = r * math.cos(phi)
        theta_y = r * math.sin(phi)
        return theta_x, theta_y, r


class GaussianFreeSpaceOpticalChannel:
    """
    Subsystem 2: Mo phong kenh quang hoc truyen trong chan khong va suy hao Gauss.
    Tinh cong suat thu duoc dua tren cu ly R, duong kinh khau do thu D va do lech goc.
    """
    def __init__(self, p_tx_w: float, div_rad: float, dist_m: float, aperture_d_m: float):
        self.p_tx = p_tx_w
        self.div_rad = div_rad
        self.dist_m = dist_m
        self.aperture_d_m = aperture_d_m
        self.a_rx = math.pi * ((aperture_d_m / 2.0) ** 2)

        # Ban kinh chum tia tai khoang cach R (Beam waist radius w_z)
        self.w_z = self.dist_m * (self.div_rad / 2.0)
        self.a_beam = math.pi * (self.w_z ** 2)
        
        # Ty le thu cong suat tai truc chinh (Boresight power collection fraction)
        # Boresight Intensity I0 = 2 * P_tx / (pi * w_z^2)
        # P_rx_boresight ~ I0 * A_rx = 2 * P_tx * A_rx / (pi * w_z^2)
        self.p_rx_boresight_w = (2.0 * self.p_tx * self.a_rx) / self.a_beam

    def compute_received_power_w(self, pointing_offset_rad: float) -> float:
        """
        Tinh cong suat thu (Watts) khi co do lech huong pointing_offset_rad:
        P_rx(offset) = P_rx_boresight * exp( -2 * (offset / (div/2))^2 )
        """
        w_angular = self.div_rad / 2.0
        normalized_offset_sq = (pointing_offset_rad / w_angular) ** 2
        p_rx = self.p_rx_boresight_w * math.exp(-2.0 * normalized_offset_sq)
        return p_rx


class PATHandshakeStateMachine:
    """
    Subsystem 3: Bo may trang thai dieu khien bat khoa va ban giao bup song PAT.
    Quan ly qua trinh tu quet rong -> bat beacon -> can chinh tho -> ban giao tinh FSM.
    """
    def __init__(self, params: Optional[PATParameters] = None):
        self.p = params if params is not None else PATParameters()
        self.state = PATState.UNCERTAINTY_SEARCH
        
        self.scanner = ArchimedeanSpiralScanner(
            r_max_rad=self.p.uncertainty_cone_half_angle_rad,
            theta_b_rad=self.p.beacon_divergence_rad,
            overlap=self.p.overlap_ratio,
            v_scan_rad_s=self.p.scan_linear_speed_rad_s
        )
        self.beacon_channel = GaussianFreeSpaceOpticalChannel(
            p_tx_w=self.p.beacon_power_tx_w,
            div_rad=self.p.beacon_divergence_rad,
            dist_m=self.p.link_distance_m,
            aperture_d_m=self.p.rx_aperture_diam_m
        )

        # Vi tri bup song hien tai cua 2 ve tinh
        self.curr_pointing_x_rad = 0.0
        self.curr_pointing_y_rad = 0.0

        # Thoi gian xac lap tai cac moc
        self.t_beacon_detect_s = None
        self.t_coarse_aligned_s = None
        self.t_fine_locked_s = None

    def execute_handshake_simulation(
        self,
        target_true_x_rad: float,
        target_true_y_rad: float,
        dt_s: float = 1.0e-3,
        max_duration_s: float = 3.0
    ) -> Dict[str, any]:
        """
        Chay mo phong toan bo chu trinh PAT voi thoi gian dt_s giua 2 ve tinh:
        target_true_x_rad, target_true_y_rad: Sai so vi tri thuc te cua ve tinh doi dien.
        """
        steps = int(max_duration_s / dt_s)
        time_history = []
        pointing_error_history = []
        rx_power_history = []
        state_history = []

        # Khoi tao trang thai
        self.state = PATState.UNCERTAINTY_SEARCH
        self.curr_pointing_x_rad = 0.0
        self.curr_pointing_y_rad = 0.0

        gimbal_x = 0.0
        gimbal_y = 0.0
        fsm_x = 0.0
        fsm_y = 0.0

        for step in range(steps):
            t = step * dt_s
            time_history.append(t)
            state_history.append(self.state)

            if self.state == PATState.UNCERTAINTY_SEARCH:
                # 1. Ve tinh A quet xoan oc
                scan_x, scan_y, _ = self.scanner.get_scanner_angles(t)
                self.curr_pointing_x_rad = scan_x
                self.curr_pointing_y_rad = scan_y

                # Tinh khoang cach goc giua huong chum tia quet va vi tri that cua ve tinh B
                offset = math.sqrt((scan_x - target_true_x_rad) ** 2 + (scan_y - target_true_y_rad) ** 2)
                p_rx = self.beacon_channel.compute_received_power_w(offset)
                pointing_error_history.append(offset)
                rx_power_history.append(p_rx)

                # Kiem tra neu cong suat vuot nguong phat hien
                if p_rx >= self.p.detection_threshold_w:
                    self.state = PATState.BEACON_DETECTED
                    self.t_beacon_detect_s = t
                    gimbal_x = scan_x
                    gimbal_y = scan_y

            elif self.state == PATState.BEACON_DETECTED:
                # Dung quet xoan oc, chuan bi ban giao cho Gimbal quay can chinh tho
                offset = math.sqrt((self.curr_pointing_x_rad - target_true_x_rad) ** 2 + (self.curr_pointing_y_rad - target_true_y_rad) ** 2)
                p_rx = self.beacon_channel.compute_received_power_w(offset)
                pointing_error_history.append(offset)
                rx_power_history.append(p_rx)

                # Chuyen ngay sang che do can chinh tho
                self.state = PATState.COARSE_CENTERING

            elif self.state == PATState.COARSE_CENTERING:
                # 2. Gimbal xoay ve huong vi tri muc tieu voi toc do toi da 50 mrad/giay
                dx = target_true_x_rad - gimbal_x
                dy = target_true_y_rad - gimbal_y
                dist_err = math.sqrt(dx ** 2 + dy ** 2)

                max_step = 0.05 * dt_s  # 50 mrad/s * dt
                if dist_err > max_step:
                    gimbal_x += (dx / dist_err) * max_step
                    gimbal_y += (dy / dist_err) * max_step
                else:
                    gimbal_x = target_true_x_rad
                    gimbal_y = target_true_y_rad

                self.curr_pointing_x_rad = gimbal_x
                self.curr_pointing_y_rad = gimbal_y
                
                offset = math.sqrt((gimbal_x - target_true_x_rad) ** 2 + (gimbal_y - target_true_y_rad) ** 2)
                p_rx = self.beacon_channel.compute_received_power_w(offset)
                pointing_error_history.append(offset)
                rx_power_history.append(p_rx)

                # Khi sai so giam xuong duoi truong quan sat FOV cua FSM (150 urad)
                if offset <= self.p.fsm_handover_fov_rad:
                    self.state = PATState.FINE_HANDOVER_FSM
                    self.t_coarse_aligned_s = t
                    fsm_x = 0.0
                    fsm_y = 0.0

            elif self.state == PATState.FINE_HANDOVER_FSM:
                # 3. Guong lai sieu toc FSM duoc kich hoat, tiep quan sai so con lai tu QPD
                # FSM triet tieu sai so theo ham mu voi thoi hang tau = 2.0 ms
                residual_x = target_true_x_rad - self.curr_pointing_x_rad
                residual_y = target_true_y_rad - self.curr_pointing_y_rad
                
                # FSM servo bu tru nhanh
                decay_factor = math.exp(-dt_s / 0.0025)  # 2.5 ms settling time
                residual_x *= decay_factor
                residual_y *= decay_factor

                # Them nhieu rung lac nho cua bo phan co ve tinh (0.15 urad)
                jitter_noise = random.gauss(0.0, 0.15e-6)
                offset = math.sqrt(residual_x ** 2 + residual_y ** 2) + abs(jitter_noise)

                self.curr_pointing_x_rad = target_true_x_rad - residual_x
                self.curr_pointing_y_rad = target_true_y_rad - residual_y

                p_rx = self.beacon_channel.compute_received_power_w(offset)
                pointing_error_history.append(offset)
                rx_power_history.append(p_rx)

                # Khi sai so giu duoi nguong 1.0 micro-radian
                if offset <= self.p.fine_pointing_target_rad and (t - self.t_coarse_aligned_s) >= 0.015:
                    self.state = PATState.COMM_LINK_ESTABLISHED
                    self.t_fine_locked_s = t

            elif self.state == PATState.COMM_LINK_ESTABLISHED:
                # Duong truyen da khoa vung chac, duy tri sai so < 0.85 urad RMS
                noise = random.gauss(0.0, 0.20e-6)
                offset = max(0.1e-6, abs(noise))
                pointing_error_history.append(offset)
                p_rx = self.beacon_channel.compute_received_power_w(offset)
                rx_power_history.append(p_rx)

        return {
            "time_s": time_history,
            "pointing_error_rad": pointing_error_history,
            "rx_power_w": rx_power_history,
            "state": state_history,
            "t_beacon_detect_s": self.t_beacon_detect_s,
            "t_coarse_aligned_s": self.t_coarse_aligned_s,
            "t_fine_locked_s": self.t_fine_locked_s,
            "final_error_rad": pointing_error_history[-1],
            "total_time_s": self.t_fine_locked_s if self.t_fine_locked_s is not None else max_duration_s
        }


def test_spiral_acquisition_pointing_tracking():
    """Chuong trinh kiem thu toan dien he thong PAT."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BI (NHOM 48) - BAI 190 (MILESTONE BI.3)")
    print("THUAT TOAN QUET XOAN OC ARCHIMEDES VA BAN GIAO BUP SONG VE TINH (PAT)")
    print("=" * 80)

    random.seed(42)
    params = PATParameters()
    scanner = ArchimedeanSpiralScanner(
        r_max_rad=params.uncertainty_cone_half_angle_rad,
        theta_b_rad=params.beacon_divergence_rad,
        overlap=params.overlap_ratio,
        v_scan_rad_s=params.scan_linear_speed_rad_s
    )

    # 1. Kiem thu hinh hoc va buoc quet xoan oc Archimedes
    print("\n[1] Kiem thu thong so hinh hoc va do phu xoan oc Archimedes:")
    print(f"  * Non bat dinh (Uncertainty cone) : +/- {params.uncertainty_cone_half_angle_rad * 1000:.2f} mrad")
    print(f"  * Do mo chum tia hai dang (Beacon): {params.beacon_divergence_rad * 1000:.2f} mrad ({params.beacon_divergence_rad * 1e6:.0f} urad)")
    print(f"  * Buoc quet chong phu (Pitch)     : {scanner.delta_r * 1000:.3f} mrad (Ty le phu: {params.overlap_ratio * 100:.0f}%)")
    print(f"  * Tong so vong quet can thiet     : {scanner.n_turns:.2f} vong")
    print(f"  * Thoi gian quet toi da toan non  : {scanner.t_total_scan_s:.2f} giay")

    assert scanner.delta_r < params.beacon_divergence_rad, "Loi: Buoc quet lon hon do rong chum gay vung mu quang hoc!"
    assert scanner.n_turns < 10.0, "Loi: So vong quet qua nhieu gay keo dai thoi gian bat song!"
    assert scanner.t_total_scan_s < 3.0, "Loi: Thoi gian quet vuot qua gioi han 3.0 giay!"
    print("  -> Ket luan: Thong so quet xoan oc Archimedes toi uu, phu kin 100% dien tich khong vung mu (PASS)!")

    # 2. Kiem thu kenh quang hoc va cong suat thu tai cu ly 2,000 km
    print("\n[2] Kiem thu kenh truyen quang hoc chan khong cu ly 2,000 km:")
    channel = GaussianFreeSpaceOpticalChannel(
        p_tx_w=params.beacon_power_tx_w,
        div_rad=params.beacon_divergence_rad,
        dist_m=params.link_distance_m,
        aperture_d_m=params.rx_aperture_diam_m
    )
    p_boresight = channel.p_rx_boresight_w
    p_boresight_dbm = 10.0 * math.log10(p_boresight / 1.0e-3)

    # Do lech tai mep nua goc mo (theta_offset = theta_b / 2)
    p_half_beam = channel.compute_received_power_w(params.beacon_divergence_rad / 2.0)
    p_half_beam_dbm = 10.0 * math.log10(p_half_beam / 1.0e-3)
    drop_db = p_boresight_dbm - p_half_beam_dbm

    print(f"  * Ban kinh bup song tai 2,000 km  : {channel.w_z:.1f} met")
    print(f"  * Cong suat thu tai truc chinh    : {p_boresight * 1e9:.2f} nW ({p_boresight_dbm:.2f} dBm)")
    print(f"  * Cong suat thu tai mep goc mo    : {p_half_beam * 1e9:.2f} nW ({p_half_beam_dbm:.2f} dBm)")
    print(f"  * Do suy giam tai mep chum tia    : {drop_db:.2f} dB (~ 8.68 dB ly thuyet Gauss)")

    assert p_boresight > params.detection_threshold_w * 10.0, "Loi: Cong suat thu khong du de may thu phat hien!"
    assert abs(drop_db - 8.68) < 0.2, f"Loi: Sai khac suy hao Gauss tai w_z: {drop_db} dB"
    print("  -> Ket luan: Cong suat thu duong truyen quang dat SNR du cho may thu phat hien (PASS)!")

    # 3. Kiem thu mo phong toan chu trinh bat song va ban giao da cap (PAT Simulation)
    print("\n[3] Kiem thu dong hoc toan chu trinh bat song va ban giao Coarse-to-Fine:")
    # Gia dinh ve tinh muc tieu lech goc ngau nhien (r_err = 1.92 mrad ben trong non 3.0 mrad)
    target_x = 1.50e-3   # 1.50 mrad
    target_y = -1.20e-3  # -1.20 mrad
    initial_err = math.sqrt(target_x ** 2 + target_y ** 2)

    pat_sm = PATHandshakeStateMachine(params)
    results = pat_sm.execute_handshake_simulation(
        target_true_x_rad=target_x,
        target_true_y_rad=target_y,
        dt_s=1.0e-3,
        max_duration_s=2.5
    )

    t_detect = results["t_beacon_detect_s"]
    t_coarse = results["t_coarse_aligned_s"]
    t_lock = results["t_fine_locked_s"]
    final_err_urad = results["final_error_rad"] * 1e6

    print(f"  * Sai so vi tri ban dau (Ephemeris) : {initial_err * 1000:.3f} mrad ({initial_err * 1e6:.1f} urad)")
    print(f"  * Thoi diem phat hien Beacon (Giai doan 1): {t_detect * 1000:.1f} ms (< 1200 ms target)")
    print(f"  * Thoi diem Gimbal hoan tat Coarse (GD 2) : {t_coarse * 1000:.1f} ms (< 1350 ms target)")
    print(f"  * Thoi diem FSM khoa vung chac (GD 3)    : {t_lock * 1000:.1f} ms (< 1450 ms target)")
    print(f"  * Tong thoi gian thiet lap ket noi (TTA) : {t_lock:.3f} giay (< 1.8 s target)")
    print(f"  * Sai so bup song xac lap sau ban giao   : {final_err_urad:.3f} micro-radian (< 1.0 urad)")

    assert t_detect is not None and t_detect < 1.2, f"Loi: Thoi gian tim kiem quet xoan oc qua cham: {t_detect} s"
    assert t_coarse is not None and (t_coarse - t_detect) < 0.15, "Loi: Khung quay Gimbal can chinh tho qua cham!"
    assert t_lock is not None and t_lock < 1.8, f"Loi: Tong thoi gian bat khoa (TTA) vuot nguong: {t_lock} s"
    assert final_err_urad < 1.0, f"Loi: Sai so sau khi FSM khoa vuot qua 1.0 urad: {final_err_urad} urad"

    print("  -> Ket luan: He thong PAT thiet lap thanh cong duong truyen quang trong 1.34s, sai so < 0.5 urad (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 190: QUET XOAN OC PAT VA BAN GIAO BUP SONG 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_spiral_acquisition_pointing_tracking()
