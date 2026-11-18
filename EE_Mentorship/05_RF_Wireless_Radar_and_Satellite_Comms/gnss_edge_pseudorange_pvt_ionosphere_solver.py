"""
EE MENTORSHIP PROGRAM - MODULE BK (NHOM 50) - BAI 198 (MILESTONE BK.3)
================================================================================
BO GIAI VI TRI GIA CU LY PSEUDORANGE PVT (GAUSS-NEWTON 4-AN), MO HINH KHI QUYEN
KLOBUCHAR / SAASTAMOINEN & TO HOP L1/L5 KHU TANG DIEN LY IONOSPHERE-FREE
================================================================================

Nguyen ly vat ly va Toan hoc cot loi:
1. Phuong trinh Gia cu ly (Pseudorange Observation Model):
     rho_i = || r_sat_i(t_tx) - r_user || + c * (dt_u - dt_s_i)
             + I_iono_i + T_tropo_i + d_Sagnac_i + epsilon_i

   Do dong ho thach anh bo thu re tien bi lech pha dt_u (~ms = hang tram km!),
   ta can toi thieu 4 ve tinh de giai he 4 an so: (X_u, Y_u, Z_u, b_u = c * dt_u).

2. Thuat toan Gauss-Newton Tuyet doi tu Tam Trai Dat (Cold-Start (0,0,0)):
   - Ma tran Hinh hoc (Line-of-Sight Jacobian H, kich thuoc M x 4):
     Hang thu i: [ -(X_i - X_u)/r_i,  -(Y_i - Y_u)/r_i,  -(Z_i - Z_u)/r_i,  1 ]
   - Cap nhat buoc lap Gauss-Newton trong so W:
     (H^T * W * H) * delta_x = H^T * W * (rho_corrected - rho_pred)

3. Mo hinh Suy hao Vat ly & Khu Dien ly Bang kep L1 + L5 (Apple / SpaceX / Tesla):
   - Hieu ung quay Trai Dat Sagnac: Trong 70 ms song bay tu quy dao 20,200 km,
     Trai Dat quay omega_e * tau lam lech toa do sat X, Y ~ 30 met!
   - Do tre tang Dien ly I_iono ~ 40.3 * TEC / f^2:
     Nho ket hop 2 tan so f_L1 = 1575.42 MHz va f_L5 = 1176.45 MHz:

              f_L1^2 * rho_L1 - f_L5^2 * rho_L5
     rho_IF = ─────────────────────────────────  -> Triet tieu 100% dien ly bac 1!
                       f_L1^2 - f_L5^2

4. He so Suy giam Do chinh xac Hinh hoc (DOP - Dilution of Precision):
     Q_enu = R_ecef2enu * (H^T * H)^(-1)_3x3 * R_ecef2enu^T
     GDOP = sqrt(trace((H^T * H)^(-1))),  PDOP = sqrt(q_EE + q_NN + q_UU)
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict


WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)
OMEGA_EARTH = 7.2921151467e-5
C_LIGHT = 299792458.0
F_L1_HZ = 1575.42e6
F_L5_HZ = 1176.45e6


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> Tuple[float, float, float]:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    n_curv = WGS84_A / math.sqrt(1.0 - WGS84_E2 * (sin_lat ** 2))
    x = (n_curv + alt_m) * cos_lat * math.cos(lon)
    y = (n_curv + alt_m) * cos_lat * math.sin(lon)
    z = (n_curv * (1.0 - WGS84_E2) + alt_m) * sin_lat
    return x, y, z


def ecef_to_geodetic(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Chuyen doi WGS84 ECEF -> (Lat deg, Lon deg, Alt m) bang thuat toan lap Bowring."""
    p = math.hypot(x, y)
    lon = math.atan2(y, x)
    lat = math.atan2(z, p * (1.0 - WGS84_E2))
    alt = 0.0
    for _ in range(8):
        sin_lat = math.sin(lat)
        n_curv = WGS84_A / math.sqrt(1.0 - WGS84_E2 * (sin_lat ** 2))
        alt = p / max(1e-12, math.cos(lat)) - n_curv
        lat = math.atan2(z, p * (1.0 - WGS84_E2 * (n_curv / (n_curv + alt))))
    return math.degrees(lat), math.degrees(lon), alt


def ecef_to_enu_matrix(lat_deg: float, lon_deg: float) -> List[List[float]]:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sl, cl = math.sin(lat), math.cos(lat)
    so, co = math.sin(lon), math.cos(lon)
    return [
        [-so, co, 0.0],
        [-sl * co, -sl * so, cl],
        [cl * co, cl * so, sl],
    ]


class LinearAlgebra4x4:
    """Bo giai ma tran dac thuan Python (Gauss-Jordan Elimination + Nghich dao ma tran)."""

    @staticmethod
    def solve_linear_system(a_in: List[List[float]], b_in: List[float]) -> List[float]:
        n = len(b_in)
        a = [list(row) for row in a_in]
        b = list(b_in)

        for col in range(n):
            pivot_row = max(range(col, n), key=lambda r: abs(a[r][col]))
            if abs(a[pivot_row][col]) < 1e-14:
                raise ValueError("Ma tran suy bien trong Gauss-Newton.")
            a[col], a[pivot_row] = a[pivot_row], a[col]
            b[col], b[pivot_row] = b[pivot_row], b[col]

            div = a[col][col]
            for j in range(col, n):
                a[col][j] /= div
            b[col] /= div

            for r in range(n):
                if r != col and abs(a[r][col]) > 0.0:
                    factor = a[r][col]
                    for j in range(col, n):
                        a[r][j] -= factor * a[col][j]
                    b[r] -= factor * b[col]
        return b

    @classmethod
    def invert_matrix(cls, mat: List[List[float]]) -> List[List[float]]:
        n = len(mat)
        inv = [[0.0] * n for _ in range(n)]
        for col in range(n):
            e = [1.0 if i == col else 0.0 for i in range(n)]
            sol = cls.solve_linear_system(mat, e)
            for row in range(n):
                inv[row][col] = sol[row]
        return inv


class AtmosphericErrorModels:
    """Cac mo hinh sai so vat ly trong truyen song GNSS: Dien ly, Doi luu & Sagnac."""

    @staticmethod
    def klobuchar_iono_delay_m(elev_deg: float, azim_deg: float, lat_deg: float, lon_deg: float, gps_tow_s: float) -> float:
        """Mo hinh Klobuchar uoc luong do tre tang Dien ly cho bang tan L1 (don vi: met)."""
        el_sc = max(0.05, elev_deg / 180.0)
        az_rad = math.radians(azim_deg)
        psi = 0.0137 / (el_sc + 0.11) - 0.022

        phi_i = (lat_deg / 180.0) + psi * math.cos(az_rad)
        phi_i = max(-0.416, min(0.416, phi_i))
        lam_i = (lon_deg / 180.0) + (psi * math.sin(az_rad)) / math.cos(phi_i * math.pi)
        phi_m = phi_i + 0.064 * math.cos((lam_i - 1.617) * math.pi)

        t_local = (43200.0 * lam_i + gps_tow_s) % 86400.0
        amp = 2.8e-8 + 1.2e-8 * phi_m  # He so chuan ngay nang hoat dong mat troi trung binh
        per = 1.2e5 - 2.0e4 * phi_m
        x_phase = 2.0 * math.pi * (t_local - 50400.0) / per
        f_slant = 1.0 + 16.0 * ((0.53 - el_sc) ** 3)

        if abs(x_phase) < 1.57:
            t_iono_s = f_slant * (5.0e-9 + amp * (1.0 - (x_phase ** 2) / 2.0 + (x_phase ** 4) / 24.0))
        else:
            t_iono_s = f_slant * 5.0e-9
        return t_iono_s * C_LIGHT

    @staticmethod
    def saastamoinen_tropo_delay_m(elev_deg: float, alt_m: float = 15.0) -> float:
        """Do tre tang Doi luu (Kho + Uot) theo do cao goc ve tinh & cao do nguoi dung."""
        el_rad = math.radians(max(5.0, elev_deg))
        alt_clamped = max(0.0, min(40000.0, alt_m))
        p_hpa = 1013.25 * (max(0.001, 1.0 - 2.2557e-5 * alt_clamped) ** 5.2568)
        zhd = 0.002277 * p_hpa
        zwd = 0.12  # Thanh phan hoi nuoc am tieu chuan
        mapping = 1.0 / math.sqrt((math.sin(el_rad) ** 2) + 0.002001)
        return (zhd + zwd) * mapping

    @staticmethod
    def ionosphere_free_l1_l5(rho_l1: float, rho_l5: float) -> float:
        """To hop tuyen tinh L1+L5 triet tieu hoan toan do tre dien ly bac 1."""
        f1_sq = F_L1_HZ ** 2
        f5_sq = F_L5_HZ ** 2
        return (f1_sq * rho_l1 - f5_sq * rho_l5) / (f1_sq - f5_sq)

    @staticmethod
    def apply_sagnac_correction(sat_pos: Tuple[float, float, float], transit_time_s: float) -> Tuple[float, float, float]:
        """Quay toa do ve tinh nguoc chieu quay Trai Dat trong khoang thoi gian song truyen."""
        theta = OMEGA_EARTH * transit_time_s
        c_th, s_th = math.cos(theta), math.sin(theta)
        xs, ys, zs = sat_pos
        return (xs * c_th + ys * s_th, -xs * s_th + ys * c_th, zs)


@dataclass
class SatelliteObservation:
    prn: int
    sat_pos_tx_ecef: Tuple[float, float, float]
    sat_clock_corr_m: float
    rho_l1_m: float
    rho_l5_m: float
    elev_deg: float
    azim_deg: float


class GaussNewtonPVTSolver:
    """Bo giai vi tri PVT (X, Y, Z, Clock Bias) va DOP Geometry bang Gauss-Newton."""

    @staticmethod
    def solve_pvt(
        observations: List[SatelliteObservation],
        mode: str = "L1_L5_IF",
        approx_lat_lon_tow: Tuple[float, float, float] = (34.0, -118.4, 50400.0),
        max_iters: int = 12,
    ) -> Dict[str, any]:
        x_u, y_u, z_u, b_u = 0.0, 0.0, 0.0, 0.0  # Khoi tao lanh tu tam Trai Dat (0, 0, 0)!
        iters_done = 0

        for it in range(max_iters):
            iters_done = it + 1
            h_mat: List[List[float]] = []
            weights: List[float] = []
            residuals: List[float] = []

            lat_est, lon_est, alt_est = approx_lat_lon_tow[0], approx_lat_lon_tow[1], 20.0
            if math.sqrt(x_u ** 2 + y_u ** 2 + z_u ** 2) > 1.0e6:
                lat_est, lon_est, alt_est = ecef_to_geodetic(x_u, y_u, z_u)

            for obs in observations:
                # 1. Hieu chinh goc quay Sagnac
                sx0, sy0, sz0 = obs.sat_pos_tx_ecef
                geom_approx = math.sqrt((sx0 - x_u) ** 2 + (sy0 - y_u) ** 2 + (sz0 - z_u) ** 2)
                sx, sy, sz = AtmosphericErrorModels.apply_sagnac_correction(obs.sat_pos_tx_ecef, geom_approx / C_LIGHT)
                r_geo = math.sqrt((sx - x_u) ** 2 + (sy - y_u) ** 2 + (sz - z_u) ** 2)

                # 2. Hieu chinh do tre khi quyen theo che do thu
                tropo = AtmosphericErrorModels.saastamoinen_tropo_delay_m(obs.elev_deg, max(0.0, alt_est))
                if mode == "UNCORRECTED_L1":
                    rho_corr = obs.rho_l1_m + obs.sat_clock_corr_m
                    sx, sy, sz = sx0, sy0, sz0  # Co tinh bo qua Sagnac de thay sai so tho
                    r_geo = geom_approx
                elif mode == "KLOBUCHAR_L1":
                    iono = AtmosphericErrorModels.klobuchar_iono_delay_m(
                        obs.elev_deg, obs.azim_deg, lat_est, lon_est, approx_lat_lon_tow[2]
                    )
                    rho_corr = obs.rho_l1_m + obs.sat_clock_corr_m - iono - tropo
                else:  # L1_L5_IF
                    rho_if = AtmosphericErrorModels.ionosphere_free_l1_l5(obs.rho_l1_m, obs.rho_l5_m)
                    rho_corr = rho_if + obs.sat_clock_corr_m - tropo

                h_mat.append([-(sx - x_u) / r_geo, -(sy - y_u) / r_geo, -(sz - z_u) / r_geo, 1.0])
                weights.append(math.sin(math.radians(max(10.0, obs.elev_deg))) ** 2)
                residuals.append(rho_corr - (r_geo + b_u))

            # H^T * W * H va H^T * W * residuals
            htwh = [[0.0] * 4 for _ in range(4)]
            htwr = [0.0] * 4
            for i in range(len(observations)):
                w = weights[i]
                hi = h_mat[i]
                ri = residuals[i]
                for r in range(4):
                    htwr[r] += w * hi[r] * ri
                    for c in range(4):
                        htwh[r][c] += w * hi[r] * hi[c]

            dx = LinearAlgebra4x4.solve_linear_system(htwh, htwr)
            x_u += dx[0]
            y_u += dx[1]
            z_u += dx[2]
            b_u += dx[3]

            if math.sqrt(dx[0] ** 2 + dx[1] ** 2 + dx[2] ** 2) < 1e-4:
                break

        # Tinh chi so hinh hoc DOP tu (H^T * H)^(-1)
        hth = [[0.0] * 4 for _ in range(4)]
        for hi in h_mat:
            for r in range(4):
                for c in range(4):
                    hth[r][c] += hi[r] * hi[c]
        cov_ecef = LinearAlgebra4x4.invert_matrix(hth)

        lat_out, lon_out, alt_out = ecef_to_geodetic(x_u, y_u, z_u)
        rot = ecef_to_enu_matrix(lat_out, lon_out)
        # Q_enu = R * Cov_xyz * R^T
        cov_xyz = [[cov_ecef[r][c] for c in range(3)] for r in range(3)]
        tmp = [[sum(cov_xyz[r][k] * rot[j][k] for k in range(3)) for j in range(3)] for r in range(3)]
        q_enu = [[sum(rot[i][k] * tmp[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

        gdop = math.sqrt(cov_ecef[0][0] + cov_ecef[1][1] + cov_ecef[2][2] + cov_ecef[3][3])
        pdop = math.sqrt(q_enu[0][0] + q_enu[1][1] + q_enu[2][2])
        hdop = math.sqrt(q_enu[0][0] + q_enu[1][1])
        vdop = math.sqrt(q_enu[2][2])

        return {
            "ecef": (x_u, y_u, z_u),
            "clock_bias_m": b_u,
            "geodetic": (lat_out, lon_out, alt_out),
            "iters": iters_done,
            "gdop": gdop,
            "pdop": pdop,
            "hdop": hdop,
            "vdop": vdop,
        }


def build_constellation_observations(
    true_lat: float,
    true_lon: float,
    true_alt: float,
    sat_el_az: List[Tuple[int, float, float]],
    clock_bias_m: float,
    iono_storm_scale: float = 1.0,
    noise_sigma_m: float = 0.08,
    seed: int = 198,
) -> List[SatelliteObservation]:
    """Sinh du lieu do gia cu ly L1/L5 co Sagnac, Klobuchar, Saastamoinen va nhieu nhiet."""
    rng = random.Random(seed)
    xu, yu, zu = geodetic_to_ecef(true_lat, true_lon, true_alt)
    rot_enu = ecef_to_enu_matrix(true_lat, true_lon)
    # R_enu2ecef = rot_enu^T
    obs_list: List[SatelliteObservation] = []

    for prn, el_deg, az_deg in sat_el_az:
        el = math.radians(el_deg)
        az = math.radians(az_deg)
        # Vector don vi huong ve tinh trong ENU: (sin(az)*cos(el), cos(az)*cos(el), sin(el))
        u_enu = [math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)]
        u_ecef = [sum(rot_enu[j][i] * u_enu[j] for j in range(3)) for i in range(3)]

        # Khoang cach xien tu nguoi dung den quy dao GPS (~26,560 km tinh tu tam Trai Dat)
        r_earth_proj = xu * u_ecef[0] + yu * u_ecef[1] + zu * u_ecef[2]
        r_orbit = 26560000.0
        r_sat_user = -r_earth_proj + math.sqrt(r_earth_proj ** 2 + r_orbit ** 2 - (xu ** 2 + yu ** 2 + zu ** 2))

        sat_rx = (xu + r_sat_user * u_ecef[0], yu + r_sat_user * u_ecef[1], zu + r_sat_user * u_ecef[2])
        # Vi tri tai thoi diem phat song (chua quay Sagnac nguoc lai tu goc ECEF(t_rx))
        theta = OMEGA_EARTH * (r_sat_user / C_LIGHT)
        c_th, s_th = math.cos(theta), math.sin(theta)
        sat_tx = (sat_rx[0] * c_th - sat_rx[1] * s_th, sat_rx[0] * s_th + sat_rx[1] * c_th, sat_rx[2])

        sat_clk = 120.0 * math.sin(prn)
        iono_l1 = iono_storm_scale * AtmosphericErrorModels.klobuchar_iono_delay_m(el_deg, az_deg, true_lat, true_lon, 50400.0)
        iono_l5 = iono_l1 * ((F_L1_HZ / F_L5_HZ) ** 2)
        tropo = AtmosphericErrorModels.saastamoinen_tropo_delay_m(el_deg, true_alt)

        rho_l1 = r_sat_user + clock_bias_m - sat_clk + iono_l1 + tropo + rng.gauss(0.0, noise_sigma_m)
        rho_l5 = r_sat_user + clock_bias_m - sat_clk + iono_l5 + tropo + rng.gauss(0.0, noise_sigma_m)

        obs_list.append(
            SatelliteObservation(
                prn=prn,
                sat_pos_tx_ecef=sat_tx,
                sat_clock_corr_m=sat_clk,
                rho_l1_m=rho_l1,
                rho_l5_m=rho_l5,
                elev_deg=el_deg,
                azim_deg=az_deg,
            )
        )
    return obs_list


def test_pseudorange_pvt_ionosphere_solver():
    """Chuong trinh kiem thu bo giai vi tri PVT 4-an, Khu dien ly L1/L5 va Hinh hoc DOP."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BK (NHOM 50) - BAI 198 (MILESTONE BK.3)")
    print("GIAI VI TRI PSEUDORANGE PVT, KHI QUYEN KLOBUCHAR & TO HOP L1/L5")
    print("=" * 80)

    # Toa do bai phong / xuong SpaceX Hawthorne CA (33.9207 N, -118.3278 W, alt 40 m)
    true_lat, true_lon, true_alt = 33.9207, -118.3278, 40.0
    true_ecef = geodetic_to_ecef(true_lat, true_lon, true_alt)
    true_clk_bias_m = 450000.0  # +1.5 ms dong ho thu lech -> 450 km!

    # 8 ve tinh phan bo tot quanh bau troi
    good_sats = [
        (3, 78.0, 15.0), (8, 52.0, 75.0), (12, 32.0, 135.0), (14, 18.0, 195.0),
        (19, 44.0, 250.0), (22, 24.0, 310.0), (27, 62.0, 345.0), (31, 16.0, 35.0),
    ]

    # 1. So sanh 3 cap do xu ly trong dieu kien Bao mat troi (Ionospheric Storm 3.0x TEC)
    print("\n[1] Giai vi tri PVT tu tam Trai Dat (Cold Start 0,0,0) khi bao Dien ly 3.0x TEC:")
    storm_obs = build_constellation_observations(
        true_lat, true_lon, true_alt, good_sats, true_clk_bias_m, iono_storm_scale=3.0, noise_sigma_m=0.05
    )

    def pos_err_3d(sol_ecef: Tuple[float, float, float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(sol_ecef, true_ecef)))

    res_raw = GaussNewtonPVTSolver.solve_pvt(storm_obs, mode="UNCORRECTED_L1")
    res_klob = GaussNewtonPVTSolver.solve_pvt(storm_obs, mode="KLOBUCHAR_L1")
    res_if = GaussNewtonPVTSolver.solve_pvt(storm_obs, mode="L1_L5_IF")

    err_raw = pos_err_3d(res_raw["ecef"])
    err_klob = pos_err_3d(res_klob["ecef"])
    err_if = pos_err_3d(res_if["ecef"])
    clk_err_if = abs(res_if["clock_bias_m"] - true_clk_bias_m)

    print(f"  * Raw L1 (Khong sua khi quyen/Sagnac) : 3D Error = {err_raw:7.2f} m (Iters={res_raw['iters']})")
    print(f"  * Single-Band Klobuchar L1 (Mo hinh)  : 3D Error = {err_klob:7.2f} m (Con sai so bao 3x TEC!)")
    print(f"  * Dual-Band L1+L5 Ionosphere-Free     : 3D Error = {err_if:7.3f} m | Clock Error = {clk_err_if:.3f} m")

    assert err_raw > 25.0 and err_klob > 5.0
    assert err_if < 0.60 and clk_err_if < 0.60 and res_if["iters"] <= 7
    print("  -> Ket luan: Gauss-Newton hoi tu <= 7 buoc; L1+L5 IF triet tieu 100% bao dien ly (PASS)!")

    # 2. So sanh hinh hoc ve tinh Tot (PDOP thap) vs Bi che khuat hem pho do thi (Urban Canyon)
    print("\n[2] Phan tich hinh hoc ve tinh DOP: Bau troi mo vs Hem pho do thi (Urban Canyon):")
    poor_sats = [
        (3, 82.0, 15.0), (8, 76.0, 60.0), (19, 71.0, 110.0), (27, 74.0, 175.0),
    ]
    poor_obs = build_constellation_observations(
        true_lat, true_lon, true_alt, poor_sats, true_clk_bias_m, iono_storm_scale=1.0, noise_sigma_m=0.05
    )
    res_poor = GaussNewtonPVTSolver.solve_pvt(poor_obs, mode="L1_L5_IF")

    print(f"  * Bau troi mo (8 ve tinh tan deu) : PDOP = {res_if['pdop']:5.2f} | GDOP = {res_if['gdop']:5.2f} | HDOP = {res_if['hdop']:4.2f}")
    print(f"  * Hem pho (4 ve tinh chum dinh)   : PDOP = {res_poor['pdop']:5.2f} | GDOP = {res_poor['gdop']:5.2f} -> CANH BAO HINH HOC XAU!")

    assert res_if["pdop"] < 2.2 and res_if["gdop"] < 2.6
    assert res_poor["pdop"] > 12.0
    print("  -> Ket luan: He so DOP phat hien chinh xac suy giam hinh hoc ve tinh trong do thi (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 198: PSEUDORANGE PVT & L1/L5 IONO-FREE HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_pseudorange_pvt_ionosphere_solver()
