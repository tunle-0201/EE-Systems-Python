"""
================================================================================
          MODULE W: SATELLITE ATTITUDE DETERMINATION & CONTROL SYSTEMS (ADCS)
              MILESTONE W.4: CAPSTONE SATELLITE ADCS FLIGHT ENGINE
================================================================================

KIEN TRUC PHAN MEM BAY HE THONG XAC DINH VA DIEU KHIEN TU THE VE TINH (ADCS ENGINE):
Tren cac ve tinh khong gian thuong mai (SpaceX Starlink, Planet Labs SkySat, CubeSat 3U/6U):
- He thong ADCS la bo nao dieu huong trong moi pha cua vong doi nhiem vu quy dao:
  1. Pha 1 (Pha song con - Safe Hold Detumbling):
     Vua roi ong phong, B-Dot dung Magnetorquer dap tat van toc lon nhao xuong < 2 deg/s.
  2. Pha 2 (Pha nap dien - Sun Acquisition & Tracking):
     Giai ma Coarse Sun Sensors, kich hoat banh da RW huong tam pin Solar Cells vao Mat Troi.
  3. Pha 3 (Pha nhiem vu - Earth Observation & Payload Pointing):
     Khoa tu the ong kinh camera chup anh be mat Trai Dat voi do chinh xac duoi 0.1 do.
  4. Pha 4 (Pha bao tri - Momentum Dumping & Desaturation):
     Phat hien banh da quay gan kich tran RPM, phat lenh cho Magnetorquer xa dong luong vao
     tu truong Trai Dat ma khong gay rung lac anh chup.

SO DO KHOI DIEU KHIEN ADCS TOAN CHUOI (ASCII ARCHITECTURE BLOCK):

   [ Magnetometer 3-Axis ] ──> [ B-Dot Controller ] ────────> [ Magnetorquers ]
                                                               (Mx, My, Mz Coils)
                                                                     ^
   [ Sun Sensors 6-Axis ]  ──> [ Sun-Pointing Logic ]                |
                                     |                               |
                                     v                               |
   [ Star Tracker / Gyro ] ──> [ Quaternion PID ]   ──> [ Reaction Wheels (3-Axis) ]
                                                                     |
                               [ Momentum Monitor ] ─────────────────+
                               (Desaturation Trip)

BANG DIEU KHIEN CHE DO BAY (ADCS MISSION MODES):
- MODE_DETUMBLING      : Dap tat dong nang xoay bang B-Dot
- MODE_SUN_ACQUISITION : Khoa huong Mat Troi nap pin quang dien
- MODE_EARTH_POINTING  : Huong ong kinh xuong mat dat lam nhiem vu
- MODE_DESATURATION    : Xa dong luong banh da bang Magnetorquer
"""

from typing import Tuple, List, Dict, Any, Optional
import numpy as np

from adcs_edge_bdot_detumbling import compute_bdot_magnetic_dipole
from adcs_edge_sun_sensor_vector import extract_sun_unit_vector, compute_sun_pointing_angles
from adcs_edge_reaction_wheel_desat import compute_magnetic_desaturation_torque


class ADCSMissionMode:
    DETUMBLING = "MODE_DETUMBLING"
    SUN_ACQUISITION = "MODE_SUN_ACQUISITION"
    EARTH_POINTING = "MODE_EARTH_POINTING"
    DESATURATION = "MODE_DESATURATION"


class SatelliteADCSFlightEngine:
    """
    Dong co phan mem bay ADCS tich hop toan bo cac thuat toan dieu khien tu the ve tinh
    """
    def __init__(self, sat_mass_kg: float = 4.0):
        self.mass_kg = sat_mass_kg
        self.mode = ADCSMissionMode.DETUMBLING
        self.current_wheel_momentum = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    def process_flight_cycle(
        self,
        b_curr: np.ndarray,
        b_prev: np.ndarray,
        dt_sec: float,
        photodiode_currents: Dict[str, float],
        wheel_h: np.ndarray
    ) -> Dict[str, Any]:
        """
        Xu ly 1 chu ky dinh ky 100 ms (10 Hz) cua may tinh bay ADCS:
        """
        self.current_wheel_momentum = np.asarray(wheel_h, dtype=np.float32)

        # 1. Thuat toan B-Dot Detumbling
        m_detumble = compute_bdot_magnetic_dipole(b_curr, b_prev, dt=dt_sec, k_gain=1000.0)

        # 2. Thuat toan Coarse Sun Sensor
        sun_unit_vec, in_eclipse = extract_sun_unit_vector(photodiode_currents)
        sun_angles = compute_sun_pointing_angles(sun_unit_vec) if not in_eclipse else {'X': 90.0, 'Y': 90.0, 'Z': 90.0}

        # 3. Kiem tra va tinh toan xa dong luong banh da RW
        h_norm = float(np.linalg.norm(self.current_wheel_momentum))
        m_desat, tau_desat = compute_magnetic_desaturation_torque(self.current_wheel_momentum, b_curr, k_dump=0.05)

        # Quan ly chuyen trang thai Mission Mode State Machine
        if h_norm > 0.15:
            self.mode = ADCSMissionMode.DESATURATION
        elif in_eclipse:
            self.mode = ADCSMissionMode.EARTH_POINTING
        else:
            self.mode = ADCSMissionMode.SUN_ACQUISITION

        return {
            "mission_mode": self.mode,
            "bdot_dipole_m": m_detumble,
            "sun_vector": sun_unit_vec,
            "is_in_eclipse": in_eclipse,
            "sun_angles_deg": sun_angles,
            "wheel_momentum_norm": h_norm,
            "desat_torque": tau_desat,
            "desat_dipole": m_desat
        }


def run_satellite_adcs_flight_engine() -> Tuple[float, float, float]:
    """
    Ham tich hop dong bo capstone kiem tra toan chuoi cac milestone W.1, W.2, W.3
    Tra ve: (M_detumble_x, Sun_vector_x, Tau_dump_y)
    """
    # 1. Ham quay B-Dot sau khi tach ten lua
    b_curr = np.array([30e-6, 5e-6, 10e-6], dtype=np.float32)
    b_prev = np.array([20e-6, 5e-6, 10e-6], dtype=np.float32)
    m_detumble = compute_bdot_magnetic_dipole(b_curr, b_prev, dt=0.1, k_gain=1000.0)

    # 2. Xac dinh huong Mat Troi don vi de quay pin quang dien
    solar_diodes = {'+X': 10.0, '-X': 0.0, '+Y': 0.0, '-Y': 0.0, '+Z': 0.0, '-Z': 0.0}
    sun_vector, _ = extract_sun_unit_vector(solar_diodes)

    # 3. Xa dong luong banh da bao hoa truc Y
    h_wheel = np.array([0.0, 0.2, 0.0], dtype=np.float32)
    _, tau_dump = compute_magnetic_desaturation_torque(h_wheel, b_curr, k_dump=0.05)

    return float(m_detumble[0]), float(sun_vector[0]), float(tau_dump[1])


if __name__ == "__main__":
    print("=========================================================")
    print("   CAPSTONE: SATELLITE ADCS FLIGHT SOFTWARE ENGINE")
    print("=========================================================\n")

    # 1. Kiem tra toan chuoi capstone qua ham wrapper
    m_x, s_x, tau_y = run_satellite_adcs_flight_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI SATELLITE ADCS ENGINE:")
    print(f"   -> B-Dot Magnetic Dipole Mx (A.m2) : {m_x:.3f}")
    print(f"   -> Sun Vector Chi huong mat +X     : {s_x:.2f}")
    print(f"   -> Mo-men xa dong luong banh da    : {tau_y:.6e} N.m\n")

    assert m_x < 0.0, "Mo-men B-Dot truc X phai mang dau am de chong lai su tang Bx!"
    assert abs(s_x - 1.0) < 1e-4, "Vector Mat Troi phai chi thang vao mat +X!"
    assert tau_y < 0.0, "Mo-men xa banh da phai mang dau am de giam dong luong Hy duong!"

    # 2. Kiem tra he thong dong co bay da che do (Full Mission Mode Flight Engine)
    engine = SatelliteADCSFlightEngine(sat_mass_kg=4.0)

    b_now = np.array([28e-6, -4e-6, 15e-6], dtype=np.float32)
    b_old = np.array([25e-6, -4e-6, 15e-6], dtype=np.float32)
    diodes = {'+X': 8.0, '-X': 0.0, '+Y': 6.0, '-Y': 0.0, '+Z': 0.0, '-Z': 0.0}
    h_wheels_high = np.array([0.0, 0.18, 0.0], dtype=np.float32)  # Dong luong cao > 0.15

    telemetry = engine.process_flight_cycle(
        b_curr=b_now,
        b_prev=b_old,
        dt_sec=0.1,
        photodiode_currents=diodes,
        wheel_h=h_wheels_high
    )

    print("2. TELEMETRY MAY TINH BAY ADCS THOI GIAN THUC:")
    print(f"   -> Che do bay tu dong (Mode)       : {telemetry['mission_mode']}")
    print(f"   -> Dong luong banh da tong ||H||  : {telemetry['wheel_momentum_norm']:.3f} N.m.s")
    print(f"   -> Vector Mat Troi nhan dien      : [{telemetry['sun_vector'][0]:.2f}, {telemetry['sun_vector'][1]:.2f}, {telemetry['sun_vector'][2]:.2f}]")
    print(f"   -> Goc huong Mat Troi truc X      : {telemetry['sun_angles_deg']['X']:.1f} do")
    print(f"   -> Mo-men xa tu truong Desat      : {np.linalg.norm(telemetry['desat_torque']):.6e} N.m")

    assert telemetry["mission_mode"] == ADCSMissionMode.DESATURATION, "Phai tu dong chuyen sang Mode DESATURATION khi dong luong > 0.15!"

    print("\n=========================================================")
    print("[THANH CONG] TOT NGHIEP XUAT SAC CAPSTONE MODULE W: SATELLITE ADCS SYSTEMS!")
    print("=========================================================")
