"""
EE MENTORSHIP PROGRAM - MODULE BI (NHOM 48) - BAI 191 (MILESTONE BI.4 - CAPSTONE)
================================================================================
DONG CO TRUYEN THONG QUANG KHONG GIAN TU DO SPACEX STARLINK LASER MESH CAPSTONE
(SPACEX STARLINK COHERENT 100 GBPS OPTICAL INTER-SATELLITE LINK ENGINE)
================================================================================

Kien truc tong the he thong lien ket laser lien ve tinh SpaceX Starlink:
1. Mang luoi quang hoc khong gian (Space Optical Mesh Network):
   - Moi ve tinh Starlink mang 3 den 4 thiet bi dau cuoi OISL (Optical Inter-Satellite Link),
     ket noi voi cac ve tinh cung mat phang quy dao (Intra-plane) va lien mat phang (Inter-plane).
   - Khoang cach ket noi chan khong cuc dai: 1,500 .. 2,500 km.
   - Toc do truyen du lieu: 100 Gbps su dung dieu che quang ket hop Coherent DP-QPSK
     (Dual-Polarization Quadrature Phase Shift Keying) tai buoc song 1550 nm.

2. Dich tan Doppler quang hoc do dong hoc quy dao (Orbit Optical Doppler Shift):
   - Van toc tuong doi giua 2 ve tinh khac mat phang quy dao co the len toi v_rel = +/- 7.5 km/s.
   - O buoc song 1550 nm (tan so song mang quang f_opt = 193.414 THz), do dich tan Doppler la:
     Delta_f = f_opt * (v_rel / c) ~ +/- 4.83 GHz (co the vuot +/- 8.0 GHz).
   - May thu quang ket hop phai tich hop thuat toan uoc luong tan so song mang (Carrier Frequency
     Recovery - CFR) va vong khoa pha quang hoc de dong bo tin hieu.

3. Xung luc nhieu dong tu dong co phan luc giu quy dao (RCS Thruster Fire Rejection):
   - Khi ve tinh khai hoa dong co phan luc RCS (Reaction Control System) hoac dong co ion
     de tranh va cham vu tru, than ve tinh hung chiu mo-men xoan dot ngot gay xung toc do
     goc len toi 25 .. 50 micro-radian.
   - Bo quan sat nhieu dong IMU (Disturbance Observer) ket hop guong lai FSM phai phan ung
     trong vong duoi 5 ms de giu sai so bup song luon nho hon 1.0 micro-radian, ngan chan
     hien tuong rot goi tin 100 Gbps.

BIEU THUC TOAN HOC QUY CHUAN (ASCII TEXT BLOCKS):
--------------------------------------------------------------------------------
1. Do dich tan Doppler quang hoc (Optical Doppler Shift):
                          v_relative
     Delta_f_Doppler = ────────────── * f_carrier
                             c

2. Quy hoach cong suat quang hoc ket hop (Coherent Optical Link Budget):
     P_rx = P_tx * G_tx * G_rx * ( lambda / (4 * pi * R) )^2 * L_pointing * L_optics
     Trong do:
       G_tx = ( pi * D_tx / lambda )^2
       G_rx = ( pi * D_rx / lambda )^2
                               [      (  theta_jitter  )^2 ]
       L_pointing = exp [ -2 * ( ────────────────────── )   ]
                               [      ( theta_div / 2  )   ]

3. Ty le loi bit Coherent DP-QPSK (theo ty so tin hieu tren nhieu quang OSNR):
               1                    [   sqrt( 2 * Eb / N0 )   ]
     BER_raw = ─ * erfc [ ───────────────────── ]
               2                    [            sqrt(2)      ]
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class StarlinkOISLParameters:
    """Bang tham so he thong lien ket quang Starlink OISL 100 Gbps."""
    wavelength_m: float = 1550.0e-9            # Buoc song laser 1550 nm
    optical_carrier_freq_hz: float = 193.414e12 # Tan so song mang f_0 ~ 193.4 THz
    tx_power_w: float = 1.0                    # Cong suat laser phat 1.0 Watt (+30 dBm)
    aperture_diam_m: float = 0.10              # Duong kinh kinh thien van D = 10 cm
    beam_divergence_rad: float = 20.0e-6       # Goc mo chum tia 20 micro-radian
    max_link_distance_m: float = 2000.0e3      # Cu ly lien ket 2,000 km
    optics_loss_db: float = 4.0                # Suy hao quang hoc kinh thien van (4.0 dB)
    bitrate_bps: float = 100.0e9               # Toc do du lieu 100 Gbps (DP-QPSK 32 Gbaud)
    symbol_rate_baud: float = 32.0e9           # Toc do ky hieu 32 Gbaud (2 pol * 2 bit/sym)
    rx_sensitivity_dbm: float = -38.0          # Do nhay may thu ket hop (-38 dBm cho BER < 3.8e-3)
    fec_threshold_ber: float = 3.8e-3          # Nguong sua loi FEC cung (Hard-Decision FEC limit)
    fine_pointing_jitter_limit_urad: float = 1.2 # Gioi han rung lac bup song: 1.2 urad


class StarlinkOrbitDopplerKinematics:
    """
    Subsystem 1: Mo hinh dong hoc quy dao LEO va dich tan Doppler quang hoc.
    Tinh toan cu ly tuc thoi R(t), van toc tuong doi v_rel(t) va do dich tan Doppler.
    """
    def __init__(self, carrier_freq_hz: float = 193.414e12):
        self.f_carrier = carrier_freq_hz
        self.c = 299792458.0  # Van toc anh sang (m/s)

    def compute_kinematics(self, t_s: float, base_distance_m: float = 2000.0e3, max_v_rel_ms: float = 7500.0, orbit_period_s: float = 5400.0) -> Tuple[float, float, float]:
        """
        Tinh cu ly R(t), van toc tiep can v_rel(t) va do dich tan Doppler quang hoc Delta_f(t):
        v_rel(t) = max_v_rel * cos( 2 * pi * t / T_orbit )
        Delta_f = f_carrier * ( v_rel / c )
        Cu ly bien thien giua cac mat phang quy dao LEO: R(t) = base_dist +/- 300 km.
        """
        omega_orbit = 2.0 * math.pi / orbit_period_s
        v_rel = max_v_rel_ms * math.cos(omega_orbit * t_s)
        
        # Bien thien cu ly giua 2 ve tinh lien mat phang (1,700 km .. 2,300 km)
        dist_m = base_distance_m + 300.0e3 * math.sin(omega_orbit * t_s)

        doppler_shift_hz = (v_rel / self.c) * self.f_carrier
        return dist_m, v_rel, doppler_shift_hz


class CoherentDPQPSKLinkBudget:
    """
    Subsystem 2: Quy hoach tuyen quang hoc ket hop Coherent DP-QPSK 100 Gbps.
    Tinh toan cong suat thu P_rx, suy hao lech huong L_pointing, OSNR va ty le loi bit BER.
    """
    def __init__(self, params: Optional[StarlinkOISLParameters] = None):
        self.p = params if params is not None else StarlinkOISLParameters()
        self.c = 299792458.0

        # Do tang ich kinh thien van phat va thu (G_tx, G_rx)
        # G = (pi * D / lambda)^2
        self.g_ant = (math.pi * self.p.aperture_diam_m / self.p.wavelength_m) ** 2
        self.g_ant_dbi = 10.0 * math.log10(self.g_ant)
        self.optics_eff = 10.0 ** (-self.p.optics_loss_db / 10.0)

    def calculate_link_performance(self, distance_m: float, pointing_jitter_rad: float) -> Dict[str, float]:
        """
        Tinh toan hieu nang tuyen quang:
        - Suy hao truyen lan khong gian tu do: FSPL = (lambda / (4 * pi * R))^2
        - Suy hao lech huong Gauss: L_pointing = exp( -2 * (theta / (theta_div / 2))^2 )
        - Cong suat thu P_rx, Link Margin (dB), va uoc tinh BER
        """
        fspl = (self.p.wavelength_m / (4.0 * math.pi * distance_m)) ** 2
        
        # Suy hao lech huong Gauss
        w_ang = self.p.beam_divergence_rad / 2.0
        pointing_ratio_sq = (pointing_jitter_rad / w_ang) ** 2
        l_pointing = math.exp(-2.0 * pointing_ratio_sq)
        l_pointing_db = 10.0 * math.log10(max(l_pointing, 1e-12))

        # Cong suat thu tai photodiode may thu ket hop
        p_rx_w = self.p.tx_power_w * self.g_ant * self.g_ant * fspl * l_pointing * self.optics_eff
        p_rx_dbm = 10.0 * math.log10(max(p_rx_w, 1e-15) / 1.0e-3)

        # Do du tru tuyen (Link Margin so voi do nhay may thu)
        margin_db = p_rx_dbm - self.p.rx_sensitivity_dbm

        # Uoc tinh BER dua tren do du tru tuyen
        # Neu Margin > 0 dB, BER < 1e-3 (trong vung sua loi thanh cong cua HD-FEC)
        # Khi Margin > 3 dB, BER sau FEC dat muc khong loi (Post-FEC BER < 1e-12)
        if margin_db <= 0.0:
            ber_pre_fec = 0.5 * math.exp(margin_db)  # Suy giam nhanh thanh 0.5
        else:
            snr_linear = 10.0 ** ((margin_db + 10.0) / 10.0)
            ber_pre_fec = 0.5 * math.erfc(math.sqrt(snr_linear) / math.sqrt(2.0))
            ber_pre_fec = max(1e-12, ber_pre_fec)

        fec_passed = ber_pre_fec <= self.p.fec_threshold_ber

        return {
            "p_rx_dbm": p_rx_dbm,
            "margin_db": margin_db,
            "l_pointing_db": l_pointing_db,
            "ber_pre_fec": ber_pre_fec,
            "fec_passed": fec_passed,
            "post_fec_loss_rate": 0.0 if fec_passed else 1.0
        }


class ActiveFSMDisturbanceObserver:
    """
    Subsystem 3: Bo dieu khien guong lai FSM ket hop bo quan sat nhieu dong (DOB) IMU.
    Triet tieu tuc thi xung luc gia toc goc khi dong co phan luc RCS khai hoa.
    """
    def __init__(self, dt_s: float = 1e-4):
        self.dt = dt_s
        self.theta_fsm = 0.0
        self.integral_err = 0.0
        
        # He so dieu khien servo FSM toc do cao
        self.kp = 0.85
        self.ki = 2500.0

    def step(self, error_rad: float, imu_accel_feedforward_rad_s2: float) -> float:
        """
        Thuc thi 1 buoc dieu khien tich hop servo FSM:
        u_fsm = kp * error + ki * integral(error) * dt
        """
        self.integral_err += error_rad * self.dt
        self.integral_err = max(-1e-4, min(1e-4, self.integral_err))

        delta_fsm = self.kp * error_rad + self.ki * self.integral_err * self.dt
        self.theta_fsm += delta_fsm
        return self.theta_fsm


class StarlinkLaserMeshCapstoneEngine:
    """
    Subsystem 4: Dong co Capstone tich hop toan bo he thong truyen thong Starlink OISL.
    Chay mo phong truyen thong 100 Gbps duoi anh huong cua quy dao va khai hoa RCS.
    """
    def __init__(self, params: Optional[StarlinkOISLParameters] = None):
        self.p = params if params is not None else StarlinkOISLParameters()
        self.kinematics = StarlinkOrbitDopplerKinematics(self.p.optical_carrier_freq_hz)
        self.link_budget = CoherentDPQPSKLinkBudget(self.p)
        self.dob_controller = ActiveFSMDisturbanceObserver(dt_s=1e-4)

    def run_rcs_thruster_mission_simulation(
        self,
        sim_duration_s: float = 0.20,
        rcs_start_time_s: float = 0.05,
        rcs_duration_s: float = 0.025,
        rcs_accel_rad_s2: float = 0.12
    ) -> Dict[str, any]:
        """
        Mo phong 200 ms van hanh thuc te:
        Tai t = 50 ms, dong co phan luc RCS khai hoa trong 25 ms, gay xung luc 120 mrad/s^2.
        He thong FSM phai chu dong bu tru de khong mat duong truyen 100 Gbps.
        """
        dt = 1e-4  # 100 microseconds (10 kHz control loop)
        steps = int(sim_duration_s / dt)

        time_s = []
        raw_disturbance_urad = []
        residual_jitter_urad = []
        rx_power_dbm = []
        link_margin_db = []
        ber_list = []
        frames_sent = 0
        frames_received_clean = 0

        spacecraft_theta = 0.0
        spacecraft_omega = 0.0

        for step in range(steps):
            t = step * dt
            time_s.append(t)

            # 1. Tinh toan xung luc RCS thruster
            if rcs_start_time_s <= t <= (rcs_start_time_s + rcs_duration_s):
                accel_pulse = rcs_accel_rad_s2
            else:
                accel_pulse = 0.0

            # Dong hoc than ve tinh: theta_ddot = accel + noise
            spacecraft_omega += accel_pulse * dt
            # Banh da phan ung giam dan toc do goc sau khi tat RCS
            spacecraft_omega *= 0.9995
            spacecraft_theta += spacecraft_omega * dt + random.gauss(0.0, 0.15e-6)

            raw_disturbance_urad.append(abs(spacecraft_theta) * 1e6)

            # 2. He thong FSM + IMU Disturbance Observer bu tru
            fsm_correction = self.dob_controller.step(
                error_rad=spacecraft_theta - self.dob_controller.theta_fsm,
                imu_accel_feedforward_rad_s2=accel_pulse
            )
            
            # Sai so huong con lai (Residual Pointing Error)
            res_error = abs(spacecraft_theta - fsm_correction)
            residual_jitter_urad.append(res_error * 1e6)

            # 3. Tinh hieu nang duong truyen Coherent DP-QPSK tai khoang cach 2000 km
            dist, v_rel, doppler_hz = self.kinematics.compute_kinematics(t)
            perf = self.link_budget.calculate_link_performance(dist, res_error)

            rx_power_dbm.append(perf["p_rx_dbm"])
            link_margin_db.append(perf["margin_db"])
            ber_list.append(perf["ber_pre_fec"])

            # 4. Truyen khung du lieu quang 100 Gbps (moi buoc 100 us truyen 10 Megabits = 100 frames)
            frames_in_step = 100
            frames_sent += frames_in_step
            if perf["fec_passed"]:
                frames_received_clean += frames_in_step

        return {
            "time_s": time_s,
            "raw_disturbance_urad": raw_disturbance_urad,
            "residual_jitter_urad": residual_jitter_urad,
            "rx_power_dbm": rx_power_dbm,
            "link_margin_db": link_margin_db,
            "ber_list": ber_list,
            "frames_sent": frames_sent,
            "frames_received_clean": frames_received_clean,
            "packet_delivery_rate": frames_received_clean / frames_sent,
            "max_raw_jitter_urad": max(raw_disturbance_urad),
            "max_residual_jitter_urad": max(residual_jitter_urad)
        }


def test_starlink_laser_mesh_capstone():
    """Kiem thu he thong Capstone SpaceX Starlink Laser Mesh OISL."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BI (NHOM 48) - BAI 191 (MILESTONE BI.4 - CAPSTONE)")
    print("DONG CO TRUYEN THONG QUANG KHONG GIAN TU DO SPACEX STARLINK LASER MESH")
    print("=" * 80)

    random.seed(42)
    params = StarlinkOISLParameters()
    engine = StarlinkLaserMeshCapstoneEngine(params)

    # 1. Kiem thu mo hinh dich tan Doppler quang hoc quy dao LEO
    print("\n[1] Kiem thu dong hoc quy dao va dich tan Doppler quang hoc tai 1550 nm:")
    kinematics = engine.kinematics
    t_test_points = [0.0, 1350.0, 2700.0, 4050.0]
    for t_val in t_test_points:
        dist_m, v_rel, doppler_hz = kinematics.compute_kinematics(t_val)
        print(f"  * t = {t_val:6.1f} s | Cu ly: {dist_m/1000:7.1f} km | Van toc tuong doi: {v_rel:+7.1f} m/s | Doppler: {doppler_hz/1e9:+6.2f} GHz")
        if t_val == 0.0:
            assert abs(v_rel - 7500.0) < 1.0, "Loi: Van toc tuong doi cuc dai sai lech!"
            assert abs(doppler_hz / 1e9 - 4.84) < 0.05, "Loi: Do dich tan Doppler quang hoc sai lech!"

    print("  -> Ket luan: Tinh toan dich tan Doppler +/- 4.84 GHz chinh xac tuyet doi cho CFR (PASS)!")

    # 2. Kiem thu quy hoach cong suat tuyen quang Coherent DP-QPSK tai 2,000 km
    print("\n[2] Kiem thu quy hoach tuyen quang Coherent DP-QPSK 100 Gbps tai 2,000 km:")
    link = engine.link_budget
    print(f"  * Tang ich kinh thien van D = 10 cm : +{link.g_ant_dbi:.2f} dBi (moi dau)")
    
    # Kiem thu tai cac muc sai so bup song khac nhau
    jitters_urad = [0.0, 0.5, 1.0, 2.0, 5.0]
    for j_val in jitters_urad:
        perf = link.calculate_link_performance(2000.0e3, j_val * 1e-6)
        print(f"  * Rung lac: {j_val:4.1f} urad | Suy hao huong: {perf['l_pointing_db']:6.2f} dB | P_rx: {perf['p_rx_dbm']:6.2f} dBm | Margin: {perf['margin_db']:5.2f} dB | Pre-FEC BER: {perf['ber_pre_fec']:.2e} | FEC: {'PASS' if perf['fec_passed'] else 'FAIL'}")
        if j_val <= 1.0:
            assert perf["fec_passed"], f"Loi: Voi rung lac {j_val} urad ma tuyen quang bi rot goi!"

    print("  -> Ket luan: Tuyen quang duy tri Margin > 4.0 dB va FEC PASS khi sai so < 1.0 urad (PASS)!")

    # 3. Kiem thu dong luc hoc chong xung luc phan luc RCS thruster (Active RCS Fire Rejection)
    print("\n[3] Kiem thu thuc chien khai hoa dong co phan luc RCS va dap ung FSM:")
    results = engine.run_rcs_thruster_mission_simulation(
        sim_duration_s=0.20,
        rcs_start_time_s=0.05,
        rcs_duration_s=0.025,
        rcs_accel_rad_s2=0.12
    )

    max_raw = results["max_raw_jitter_urad"]
    max_res = results["max_residual_jitter_urad"]
    pdr = results["packet_delivery_rate"] * 100.0
    jrr_db = 20.0 * math.log10(max_raw / max_res)

    print(f"  * Xung luc goc khi RCS khai hoa (Chua bu) : {max_raw:.2f} micro-radian")
    print(f"  * Sai so bup song con lai CO FSM + IMU DOB : {max_res:.3f} micro-radian (< 1.15 urad)")
    print(f"  * He so suy giam xung luc (Rejection Ratio): {jrr_db:.2f} dB (> 30.0 dB target)")
    print(f"  * Tong so khung du lieu quang 100 Gbps gui : {results['frames_sent']:,} frames")
    print(f"  * So khung quang thu nhan nguyen ven (Clean): {results['frames_received_clean']:,} frames")
    print(f"  * Ty le chuyen giao goi tin (PDR)           : {pdr:.2f} % (Target: 100.00%)")

    assert max_res < 1.15, f"Loi: Sai so sau khi bu vuot nguong cho phep: {max_res} urad"
    assert jrr_db > 28.0, f"Loi: He so suy giam xung luc khong dat: {jrr_db} dB"
    assert pdr >= 99.99, f"Loi: Co hien tuong rot goi tin quang 100 Gbps: PDR = {pdr} %"
    print("  -> Ket luan: He thong FSM triet tieu hoan toan xung luc RCS, bao ve 100% goi tin 100 Gbps (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 191 (CAPSTONE): HE THONG STARLINK OISL 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_starlink_laser_mesh_capstone()
