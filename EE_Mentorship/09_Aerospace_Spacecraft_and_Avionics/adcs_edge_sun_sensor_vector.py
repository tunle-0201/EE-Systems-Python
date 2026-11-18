"""
================================================================================
          MODULE W: SATELLITE ATTITUDE DETERMINATION & CONTROL SYSTEMS (ADCS)
              MILESTONE W.2: COARSE SUN SENSOR VECTOR EXTRACTION
================================================================================

VAI TRO THIET YEU CUA CAM BIEN MAT TROI (SUN SENSORS) TRONG DINH HUONG VE TINH:
Sau khi ham quay B-Dot on dinh, ve tinh phai lap tuc tim huong Mat Troi:
1. Huong truc vuong goc cua tam pin quang dien Solar Panels ve phia Mat Troi de thu
   duoc cong suat sac toi da: P = P_max * cos(theta) -> theta phai tien ve 0 do!
2. Tranh de ong kinh camera do tham khong gian (Payload Optical Sensors) bi anh sang
   Mat Troi chieu thang truc tiep lam chay cam bien CMOS/CCD Focal Plane Array!

NGUYEN LY DO DONG QUANG DIEN TREN 6 MAT THAN VE TINH (ASCII TEXT BLOCK):
CubeSat duoc gan 6 Photodiode tren 6 mat truc: [+X, -X, +Y, -Y, +Z, -Z]:

                    +Z (Mat dinh)
                      ^
                      |     +Y (Mat ben)
                      |    /
                      |   /
                      +-------> +X (Mat truoc)
                     /
                    /
                  -X, -Y, -Z o cac mat doi dien

Dong quang dien sinh ra theo dinh luat Lambert:
         I_diode = I_max * max(0.0, cos(theta_incidence))

CONG THUC TRICH XUAT VECTOR HUONG MAT TROI DON VI (UNIT SUN VECTOR):

         S_x = I(+X) - I(-X)
         S_y = I(+Y) - I(-Y)
         S_z = I(+Z) - I(-Z)

         S_raw = [ S_x,  S_y,  S_z ]

                     S_raw
         S_unit = ───────────
                   ||S_raw||

XU LY TINH HUONG BIEN: VUNG TOI NGUYET THUC (ECLIPSE TRANSITION):
Khi ve tinh bay vao bong toi cua Trai Dat, toan bo 6 mat deu co I = 0 mA:
-> BMS/ADCS phai phat hien co bao Eclipse de tranh loi chia cho 0 va giu nguyen goc quay!
"""

from typing import Tuple, List, Dict, Any, Optional
import numpy as np


def extract_sun_unit_vector(currents_6axis: Dict[str, float], eclipse_threshold_ma: float = 0.05) -> Tuple[np.ndarray, bool]:
    """
    Trich xuat vector don vi huong Mat Troi tu dong quang dien 6 mat ve tinh:
    - currents_6axis: Dict chua gia tri dong quang dien cua 6 mat (mA)
      {'+X': ..., '-X': ..., '+Y': ..., '-Y': ..., '+Z': ..., '-Z': ...}
    - eclipse_threshold_ma: Nguong toi thieu de phan biet vung sang va vung toi
    Tra ve: (S_unit_vector_3d, is_in_eclipse)
    """
    sx = float(currents_6axis.get('+X', 0.0) - currents_6axis.get('-X', 0.0))
    sy = float(currents_6axis.get('+Y', 0.0) - currents_6axis.get('-Y', 0.0))
    sz = float(currents_6axis.get('+Z', 0.0) - currents_6axis.get('-Z', 0.0))

    vec = np.array([sx, sy, sz], dtype=np.float32)
    norm = float(np.linalg.norm(vec))

    # Kiem tra tinh huong bien: Vung toi Eclipse
    if norm < eclipse_threshold_ma:
        # Ve tinh dang trong vung toi cua Trai Dat, tra ve vector 0 va co Eclipse = True
        return np.zeros(3, dtype=np.float32), True

    unit_vec = vec / norm
    return np.asarray(unit_vec, dtype=np.float32), False


def compute_sun_pointing_angles(s_unit: np.ndarray) -> Dict[str, float]:
    """
    Tinh goc lech giua vector Mat Troi va cac truc toa do ve tinh (do):
    cos(theta) = S_unit[axis]
    """
    angles_deg = {}
    axes = ['X', 'Y', 'Z']
    for idx, axis in enumerate(axes):
        cos_val = np.clip(s_unit[idx], -1.0, 1.0)
        ang = np.rad2deg(np.arccos(cos_val))
        angles_deg[axis] = float(ang)
    return angles_deg


if __name__ == "__main__":
    print("=========================================================")
    print("   SATELLITE ADCS: TRI-AXIAL SUN SENSOR VECTOR EXTRACTION")
    print("=========================================================\n")

    # 1. Kich ban chieu sang goc nghieng: Mat +X don 8.0 mA, Mat +Y don 6.0 mA
    photodiodes_sun = {'+X': 8.0, '-X': 0.0, '+Y': 6.0, '-Y': 0.0, '+Z': 0.0, '-Z': 0.0}
    sun_vec, in_eclipse = extract_sun_unit_vector(photodiodes_sun)
    pointing_angles = compute_sun_pointing_angles(sun_vec)

    print("1. KET QUA XAC DINH HUONG MAT TROI KHI CO NANG (SUNLIT REGION):")
    print(f"   -> Dong quang 6 mat (mA)      : {photodiodes_sun}")
    print(f"   -> Vector Mat Troi S (x, y, z): [{sun_vec[0]:.3f}, {sun_vec[1]:.3f}, {sun_vec[2]:.3f}]")
    print(f"   -> Do dai vector (Norm)       : {np.linalg.norm(sun_vec):.3f}")
    print(f"   -> Goc lech voi truc +X       : {pointing_angles['X']:.2f} do (cos = 0.8)")
    print(f"   -> Goc lech voi truc +Y       : {pointing_angles['Y']:.2f} do (cos = 0.6)")
    print(f"   -> Trang thai Eclipse (Vung toi): {'CO' if in_eclipse else 'KHONG (DANG DON NANG)'}\n")

    # Kiem tra Assertions
    assert in_eclipse is False, "He thong khong duoc bao Eclipse khi dong > 0!"
    assert abs(np.linalg.norm(sun_vec) - 1.0) < 1e-5, "Vector phai duoc chuan hoa ve do dai 1.0!"
    assert abs(sun_vec[0] - 0.8) < 1e-4 and abs(sun_vec[1] - 0.6) < 1e-4, "Sai lech vector thanh phan!"

    # 2. Kich ban tinh huong bien: Vong nguyet thuc Eclipse (Dong quang dien toan bo = 0)
    print("2. KIEM THU TINH HUONG BIEN: VE TINH VAO VUNG TOI TRAI DAT (ECLIPSE):")
    photodiodes_dark = {'+X': 0.01, '-X': 0.0, '+Y': 0.0, '-Y': 0.0, '+Z': 0.0, '-Z': 0.0}
    dark_vec, dark_eclipse = extract_sun_unit_vector(photodiodes_dark, eclipse_threshold_ma=0.05)

    print(f"   -> Dong quang trong vung toi  : {photodiodes_dark}")
    print(f"   -> Phat hien trang thai Eclipse: {'[XAC NHAN ECLIPSE]' if dark_eclipse else 'LOI'}")
    print(f"   -> Vector xuat ra             : {dark_vec}")

    assert dark_eclipse is True, "Phai phat hien chinh xac trang thai Eclipse khi dong < 0.05 mA!"
    assert np.all(dark_vec == 0.0), "Vector trong vung toi phai la [0, 0, 0] de tranh tinh toan sai!"

    print("\n[THANH CONG] BO DINH HUONG MAT TROI XAC DINH CHINH XAC VECTOR DON VI VA AN TOAN KHI ECLIPSE!")
