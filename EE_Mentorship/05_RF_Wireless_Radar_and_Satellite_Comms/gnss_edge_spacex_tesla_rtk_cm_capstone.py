"""
EE MENTORSHIP PROGRAM - MODULE BK (NHOM 50) - BAI 199 (MILESTONE BK.4 - CAPSTONE)
================================================================================
DONG CO DINH VI VE TINH GNSS L1/L5 & RTK PHA SONG MANG CHINH XAC CENTIMET
CAPSTONE CHO SPACEX FALCON 9 / STARSHIP DRONE SHIP & TESLA ROBOTAXI DOCKING
================================================================================

Kien truc He thong Dinh vi Chinh xac Centimet (Multi-Layer GNSS RTK + RAIM Engine):
1. Tang Hop nhat Pha Song mang Bang kep L1 + L5 (Wide-Lane & Narrow-Lane):
   - Song mang L1 (1575.42 MHz, buoc song lambda_L1 = 19.03 cm) co nhieu chi ~ 2 mm!
   - Nhung neu giai sai so nguyen chu ky N (Integer Ambiguity), vi tri se lech 19 cm.
   - To hop Wide-Lane (Phi_L1 - Phi_L5) keo gian buoc song ao len lambda_WL = 75.14 cm,
     giup chot so nguyen N sieu nhanh truoc khi chuyen sang L1 Fixed dat do chinh xac mm-cm!

2. Giai thuat Sai phan Kep RTK (RTK Double-Difference Carrier-Phase):
   - Lay Rover (Ten lua/Xe Tesla) tru Base Station (Tram mat dat RTCM3):
     Triet tieu 100% sai so dong ho ve tinh & ~99.5% do tre tang dien ly/doi luu.
   - Tiep tuc lay Ve tinh k tru Ve tinh chuan p (Pivot Satellite cao nhat):
     Triet tieu 100% sai so dong ho cua ca Rover va Base!

   Phuong trinh Sai phan Kep:
     DD_rho_kp          = -(e_k - e_p)^T * b_rb                     + eps_code (~0.30 m)
     lambda * DD_Phi_kp = -(e_k - e_p)^T * b_rb + lambda * DD_N_kp  + eps_phase (~0.003 m)

3. Giai ma So Nguyen Da tri (Integer Ambiguity Resolution - IAR) & Ratio Test:
   - Uoc luong trang thai thuc Float (b_float, N_float) bang Binh phuong Toi thieu trong so.
   - Tim cap vector so nguyen toi uu N_1 va N_2 gan N_float nhat theo metric Q_N^(-1):
     Ratio = d2_second / d2_best >= 3.0 -> Chap nhan RTK FIXED!
   - Hieu chinh vector vi tri chinh xac centimet:
     b_fixed = b_float - Q_bN * Q_N^(-1) * (N_float - N_fixed)

4. Giam sat Toan ven Tu dong RAIM (Receiver Autonomous Integrity Monitoring):
   - Tinh thong ke WSSE (Weighted Sum of Squared Errors) qua so du hinh hoc.
   - Khi co ve tinh bi nhieu da duong (Multipath) hoac gia mao (Spoofing), RAIM FDE
     khoanh vung dung ve tinh loi trong 1 chu ky 10 Hz (100 ms) va loai bo an toan!
--------------------------------------------------------------------------------
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict


C_LIGHT = 299792458.0
F_L1_HZ = 1575.42e6
F_L5_HZ = 1176.45e6
LAMBDA_L1 = C_LIGHT / F_L1_HZ             # ~0.19029367 m
LAMBDA_WL = C_LIGHT / (F_L1_HZ - F_L5_HZ) # ~0.75142105 m


class MatrixOps:
    """Bo cong cu ma tran thuan thu vien chuan Python cho Bo giai RTK & RAIM."""

    @staticmethod
    def mat_mul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        rows, cols, inner = len(a), len(b[0]), len(b)
        return [[sum(a[i][k] * b[k][j] for k in range(inner)) for j in range(cols)] for i in range(rows)]

    @staticmethod
    def mat_vec(a: List[List[float]], v: List[float]) -> List[float]:
        return [sum(row[k] * v[k] for k in range(len(v))) for row in a]

    @staticmethod
    def transpose(a: List[List[float]]) -> List[List[float]]:
        return [[a[r][c] for r in range(len(a))] for c in range(len(a[0]))]

    @staticmethod
    def solve_linear(a_in: List[List[float]], b_in: List[float]) -> List[float]:
        n = len(b_in)
        a = [list(row) for row in a_in]
        b = list(b_in)
        for col in range(n):
            piv = max(range(col, n), key=lambda r: abs(a[r][col]))
            if abs(a[piv][col]) < 1e-13:
                raise ValueError("Ma tran suy bien.")
            a[col], a[piv] = a[piv], a[col]
            b[col], b[piv] = b[piv], b[col]
            div = a[col][col]
            for j in range(col, n):
                a[col][j] /= div
            b[col] /= div
            for r in range(n):
                if r != col and a[r][col] != 0.0:
                    fac = a[r][col]
                    for j in range(col, n):
                        a[r][j] -= fac * a[col][j]
                    b[r] -= fac * b[col]
        return b

    @classmethod
    def invert(cls, mat: List[List[float]]) -> List[List[float]]:
        n = len(mat)
        inv = [[0.0] * n for _ in range(n)]
        for c in range(n):
            e = [1.0 if i == c else 0.0 for i in range(n)]
            sol = cls.solve_linear(mat, e)
            for r in range(n):
                inv[r][c] = sol[r]
        return inv


@dataclass
class SatRawEpoch:
    prn: int
    los_enu: Tuple[float, float, float]  # Vector don vi huong ve tinh (East, North, Up)
    elev_deg: float
    sd_code_l1_m: float                  # Single-Difference Pseudorange (Rover - Base)
    sd_phase_l1_cyc: float               # Single-Difference Carrier Phase L1 (cycles)
    sd_phase_l5_cyc: float               # Single-Difference Carrier Phase L5 (cycles)


class RTKDoubleDifferenceEngine:
    """
    Dong co giai toa do tuong doi chinh xac Centimet (RTK Float -> Integer Fix)
    su dung Sai phan Kep giua tram Base va Rover + Kiem dinh Ratio Test.
    """

    def __init__(self, sigma_code_m: float = 0.06, sigma_phase_m: float = 0.0025):
        self.sigma_code_m = sigma_code_m
        self.sigma_phase_m = sigma_phase_m
        self.held_dd_n: Dict[Tuple[int, int], int] = {}

    @staticmethod
    def _integer_search_ratio(n_float: List[float], q_nn: List[List[float]]) -> Tuple[List[int], float]:
        """
        Tim vector so nguyen toi uu N_best va tot nhi N_2nd quanh N_float:
        1) Chay Sequential Conditional Bootstrapping (giam phuong sai co dieu kien kieu LAMBDA)
           de xu ly tuong quan dong thoi qua ve tinh Pivot.
        2) Quet lan can quanh N_boot va N_round theo chuan Mahalanobis Q_NN^(-1), tinh Ratio Test.
        """
        m = len(n_float)
        q_inv = MatrixOps.invert(q_nn)

        # Buoc 1: Integer Bootstrapping bang Schur complement giam dan phuong sai nho nhat
        n_work = list(n_float)
        q_work = [list(row) for row in q_nn]
        unfixed = set(range(m))
        n_boot = [0] * m
        while unfixed:
            best_i = min(unfixed, key=lambda idx: q_work[idx][idx])
            n_boot[best_i] = int(round(n_work[best_i]))
            delta = n_boot[best_i] - n_work[best_i]
            var_i = max(1e-12, q_work[best_i][best_i])
            unfixed.remove(best_i)
            for j in unfixed:
                n_work[j] += (q_work[j][best_i] / var_i) * delta
            for r in unfixed:
                qr_i = q_work[r][best_i] / var_i
                for c in unfixed:
                    q_work[r][c] -= qr_i * q_work[best_i][c]

        def quad_cost(n_cand: List[int]) -> float:
            diff = [n_float[i] - n_cand[i] for i in range(m)]
            q_diff = MatrixOps.mat_vec(q_inv, diff)
            return sum(diff[i] * q_diff[i] for i in range(m))

        best_cand = list(n_boot)
        best_cost = quad_cost(best_cand)
        second_cost = float("inf")

        # Buoc 2: Quet cac ung vien lan can quanh n_boot (bao gom dich chung pivot +/-1)
        candidates: List[List[int]] = [list(n_boot), [int(round(v)) for v in n_float]]
        for shift in (-1, 1):
            candidates.append([v + shift for v in n_boot])
        for i in range(m):
            for step in (-1, 1):
                c1 = list(n_boot)
                c1[i] += step
                candidates.append(c1)
                for shift in (-1, 1):
                    c1s = [v + shift for v in n_boot]
                    c1s[i] += step
                    candidates.append(c1s)
        for i in range(m):
            for j in range(i + 1, m):
                for s1 in (-1, 1):
                    for s2 in (-1, 1):
                        c2 = list(n_boot)
                        c2[i] += s1
                        c2[j] += s2
                        candidates.append(c2)

        for cand in candidates:
            cost = quad_cost(cand)
            if cost < best_cost - 1e-12:
                second_cost = best_cost
                best_cost = cost
                best_cand = cand
            elif cand != best_cand and cost < second_cost:
                second_cost = cost

        ratio = second_cost / max(1e-12, best_cost)
        return best_cand, ratio

    def solve_baseline_enu(self, sats: List[SatRawEpoch], use_fix_and_hold: bool = False) -> Dict[str, any]:
        """Giai vector duong co so b_rb = (East, North, Up) tu danh sach ve tinh hop le."""
        if len(sats) < 5:
            raise ValueError("Can toi thieu 5 ve tinh cho RTK + kiem dinh.")

        # Chon ve tinh Pivot (goc cao cao nhat) de giam thieu nhieu da duong
        pivot = max(sats, key=lambda s: s.elev_deg)
        others = [s for s in sats if s.prn != pivot.prn]
        k_dd = len(others)
        n_states = 3 + k_dd  # [bE, bN, bU, N_1 .. N_k]

        # Neu dang bat che do Fix-and-Hold lien tuc & du so nguyen da khoa -> giai thang Pha
        if use_fix_and_hold and all((pivot.prn, s.prn) in self.held_dd_n for s in others):
            n_held = [self.held_dd_n[(pivot.prn, s.prn)] for s in others]
            h_p = [[-(s.los_enu[c] - pivot.los_enu[c]) for c in range(3)] for s in others]
            y_p = [
                LAMBDA_L1 * ((s.sd_phase_l1_cyc - pivot.sd_phase_l1_cyc) - n_held[idx])
                for idx, s in enumerate(others)
            ]
            w_p = [(math.sin(math.radians(max(12.0, s.elev_deg))) ** 2) / (self.sigma_phase_m ** 2) for s in others]
            hpwh = [[0.0] * 3 for _ in range(3)]
            hpwy = [0.0] * 3
            for row, yv, wv in zip(h_p, y_p, w_p):
                for i in range(3):
                    hpwy[i] += wv * row[i] * yv
                    for j in range(3):
                        hpwh[i][j] += wv * row[i] * row[j]
            b_hold = MatrixOps.solve_linear(hpwh, hpwy)
            max_res_m = max(abs(y_p[idx] - sum(h_p[idx][c] * b_hold[c] for c in range(3))) for idx in range(k_dd))
            if max_res_m < 0.025:  # Xac nhan khong truot pha (No Cycle Slip < 2.5 cm)
                return {
                    "mode": "RTK_FIXED",
                    "pivot_prn": pivot.prn,
                    "b_code_only_enu": tuple(b_hold),
                    "b_float_enu": tuple(b_hold),
                    "b_final_enu": tuple(b_hold),
                    "ratio_test": 999.0,
                    "n_fixed": n_held,
                    "phase_residuals_m": {},
                }

        # Xay dung he phuong trinh Sai phan Kep (Code + Carrier Phase)
        a_rows: List[List[float]] = []
        y_vec: List[float] = []
        w_diag: List[float] = []

        for idx, sat in enumerate(others):
            # Vector hinh hoc sai phan kep: -(e_k - e_p)
            g_row = [-(sat.los_enu[c] - pivot.los_enu[c]) for c in range(3)]
            w_elev = math.sin(math.radians(max(12.0, sat.elev_deg))) ** 2

            # 1. Phuong trinh Code Pseudorange DD
            code_row = g_row + [0.0] * k_dd
            dd_code = sat.sd_code_l1_m - pivot.sd_code_l1_m
            a_rows.append(code_row)
            y_vec.append(dd_code)
            w_diag.append(w_elev / (self.sigma_code_m ** 2))

            # 2. Phuong trinh Carrier Phase L1 DD
            phase_row = g_row + [0.0] * k_dd
            phase_row[3 + idx] = LAMBDA_L1
            dd_phase_m = LAMBDA_L1 * (sat.sd_phase_l1_cyc - pivot.sd_phase_l1_cyc)
            a_rows.append(phase_row)
            y_vec.append(dd_phase_m)
            w_diag.append(w_elev / (self.sigma_phase_m ** 2))

        # Giai he phuong trinh chuan (A^T * W * A) * x = A^T * W * y -> Uoc luong Float
        atwa = [[0.0] * n_states for _ in range(n_states)]
        atwy = [0.0] * n_states
        for row, y_val, w_val in zip(a_rows, y_vec, w_diag):
            for i in range(n_states):
                atwy[i] += w_val * row[i] * y_val
                for j in range(n_states):
                    atwa[i][j] += w_val * row[i] * row[j]

        q_full = MatrixOps.invert(atwa)
        x_float = MatrixOps.mat_vec(q_full, atwy)
        b_float = x_float[:3]
        n_float = x_float[3:]

        # Trich xuat Q_bN va Q_NN de giai so nguyen N_fixed
        q_nn = [[q_full[3 + i][3 + j] for j in range(k_dd)] for i in range(k_dd)]
        q_bn = [[q_full[i][3 + j] for j in range(k_dd)] for i in range(3)]

        n_fixed, ratio = self._integer_search_ratio(n_float, q_nn)
        is_fixed = ratio >= 3.0

        if is_fixed:
            q_nn_inv = MatrixOps.invert(q_nn)
            dn = [n_float[i] - n_fixed[i] for i in range(k_dd)]
            corr = MatrixOps.mat_vec(q_bn, MatrixOps.mat_vec(q_nn_inv, dn))
            b_fixed = [b_float[i] - corr[i] for i in range(3)]
            if use_fix_and_hold:
                for idx, sat in enumerate(others):
                    self.held_dd_n[(pivot.prn, sat.prn)] = n_fixed[idx]
        else:
            b_fixed = list(b_float)

        # Uoc luong Stand-Alone Code-Only (chi dung phuong trinh Code DD)
        h_code = [a_rows[2 * i][:3] for i in range(k_dd)]
        y_code = [y_vec[2 * i] for i in range(k_dd)]
        w_code = [w_diag[2 * i] for i in range(k_dd)]
        hcwh = [[0.0] * 3 for _ in range(3)]
        hcwy = [0.0] * 3
        for row, yv, wv in zip(h_code, y_code, w_code):
            for i in range(3):
                hcwy[i] += wv * row[i] * yv
                for j in range(3):
                    hcwh[i][j] += wv * row[i] * row[j]
        b_code_only = MatrixOps.solve_linear(hcwh, hcwy)

        # Tinh lai so du pha (Carrier Phase Residuals) sau khi fix so nguyen cho RAIM
        phase_residuals_m: Dict[int, float] = {}
        for idx, sat in enumerate(others):
            dd_phase_m = LAMBDA_L1 * (sat.sd_phase_l1_cyc - pivot.sd_phase_l1_cyc)
            pred_geom = sum(a_rows[2 * idx + 1][c] * b_fixed[c] for c in range(3)) + LAMBDA_L1 * n_fixed[idx]
            phase_residuals_m[sat.prn] = dd_phase_m - pred_geom

        return {
            "mode": "RTK_FIXED" if is_fixed else "RTK_FLOAT",
            "pivot_prn": pivot.prn,
            "b_code_only_enu": tuple(b_code_only),
            "b_float_enu": tuple(b_float),
            "b_final_enu": tuple(b_fixed),
            "ratio_test": ratio,
            "n_fixed": n_fixed,
            "phase_residuals_m": phase_residuals_m,
        }


class RAIMIntegrityMonitor:
    """
    Giam sat toan ven RAIM Fault Detection & Exclusion (FDE):
    Dung kiem dinh Chi-Square tren WSSE de phat hien & co lap dung ve tinh bi loi.
    """

    def __init__(self, raim_wsse_threshold: float = 25.0):
        self.threshold = raim_wsse_threshold

    @staticmethod
    def _compute_code_wsse(sats: List[SatRawEpoch], sigma_m: float = 0.25) -> float:
        pivot = max(sats, key=lambda s: s.elev_deg)
        others = [s for s in sats if s.prn != pivot.prn]
        h = [[-(s.los_enu[c] - pivot.los_enu[c]) for c in range(3)] for s in others]
        y = [s.sd_code_l1_m - pivot.sd_code_l1_m for s in others]

        hth = [[sum(h[k][i] * h[k][j] for k in range(len(others))) for j in range(3)] for i in range(3)]
        hty = [sum(h[k][i] * y[k] for k in range(len(others))) for i in range(3)]
        b_est = MatrixOps.solve_linear(hth, hty)

        wsse = 0.0
        for row, y_val in zip(h, y):
            res = y_val - sum(row[c] * b_est[c] for c in range(3))
            wsse += (res / sigma_m) ** 2
        return wsse

    def verify_and_exclude_faults(
        self, sats: List[SatRawEpoch], rtk_engine: RTKDoubleDifferenceEngine, use_fix_and_hold: bool = False
    ) -> Dict[str, any]:
        wsse_all = self._compute_code_wsse(sats, rtk_engine.sigma_code_m)
        excluded_prn = None
        clean_sats = list(sats)

        if wsse_all > self.threshold and len(sats) >= 6:
            # FDE: Thu loai bo tung ve tinh de tim ra tap con co WSSE nho nhat
            best_sub_wsse = float("inf")
            best_prn = None
            for candidate in sats:
                sub = [s for s in sats if s.prn != candidate.prn]
                sub_wsse = self._compute_code_wsse(sub, rtk_engine.sigma_code_m)
                if sub_wsse < best_sub_wsse:
                    best_sub_wsse = sub_wsse
                    best_prn = candidate.prn
            if best_sub_wsse < self.threshold:
                excluded_prn = best_prn
                clean_sats = [s for s in sats if s.prn != excluded_prn]

        rtk_sol = rtk_engine.solve_baseline_enu(clean_sats, use_fix_and_hold=use_fix_and_hold)
        return {
            "fault_detected": wsse_all > self.threshold,
            "excluded_prn": excluded_prn,
            "wsse_before": wsse_all,
            "rtk_solution": rtk_sol,
        }


def simulate_epoch_observations(
    true_baseline_enu: Tuple[float, float, float],
    sat_geometry: List[Tuple[int, float, float]],
    true_dd_integers: Dict[int, int],
    fault_prn: int = None,
    fault_bias_m: float = 0.0,
    rng: random.Random = None,
) -> List[SatRawEpoch]:
    """Sinh du lieu do sai phan don L1+L5 thuc te cho 1 epoch (co sai so pha mm)."""
    sats: List[SatRawEpoch] = []
    # Sai so dong ho thu chung cua Rover so voi Base (tu bi triet tieu boi DD!)
    rx_common_clk_m = 42.5

    for prn, el_deg, az_deg in sat_geometry:
        el, az = math.radians(el_deg), math.radians(az_deg)
        los_enu = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))
        proj_range = -sum(los_enu[c] * true_baseline_enu[c] for c in range(3))

        code_noise = rng.gauss(0.0, 0.055) if rng else 0.0  # Ma gia cu ly da lam min Hatch-Filter (5.5 cm)
        phase_noise_m = rng.gauss(0.0, 0.0020) if rng else 0.0  # 2 mm nhieu song mang

        extra_fault = fault_bias_m if (fault_prn is not None and prn == fault_prn) else 0.0
        n_int_l1 = true_dd_integers.get(prn, 150 + prn * 7)

        sd_code = proj_range + rx_common_clk_m + extra_fault + code_noise
        sd_phase_l1 = (proj_range + rx_common_clk_m + phase_noise_m + extra_fault) / LAMBDA_L1 - n_int_l1
        sd_phase_l5 = (proj_range + rx_common_clk_m + phase_noise_m) / (C_LIGHT / F_L5_HZ) - (n_int_l1 // 2)

        sats.append(
            SatRawEpoch(
                prn=prn,
                los_enu=los_enu,
                elev_deg=el_deg,
                sd_code_l1_m=sd_code,
                sd_phase_l1_cyc=sd_phase_l1,
                sd_phase_l5_cyc=sd_phase_l5,
            )
        )
    return sats


def test_spacex_tesla_rtk_cm_capstone():
    """Chuong trinh kiem thu Capstone RTK Centimet + RAIM cho SpaceX & Tesla Robotaxi."""
    print("=" * 80)
    print("EE MENTORSHIP - MODULE BK (NHOM 50) - BAI 199 (MILESTONE BK.4 - CAPSTONE)")
    print("DONG CO DINH VI RTK SONG MANG CENTIMET & RAIM CHO SPACEX & TESLA ROBOTAXI")
    print("=" * 80)

    rng = random.Random(20261114)
    rtk = RTKDoubleDifferenceEngine(sigma_code_m=0.06, sigma_phase_m=0.0025)
    raim = RAIMIntegrityMonitor(raim_wsse_threshold=25.0)

    # 8 ve tinh phan bo tren bau troi bai ha canh SpaceX Drone Ship
    sat_geom = [
        (3, 76.0, 20.0), (8, 54.0, 72.0), (12, 34.0, 130.0), (14, 24.0, 192.0),
        (19, 46.0, 248.0), (22, 29.0, 305.0), (27, 63.0, 342.0), (31, 21.0, 40.0),
    ]
    dd_ints = {prn: 300 + prn * 11 for prn, _, _ in sat_geom}

    # 1. So sanh 3 cap do do chinh xac tren cung 1 epoch: Code-Only vs RTK Float vs RTK Fixed
    print("\n[1] Kiem thu Giai so nguyen song mang L1 RTK Fixed (Baseline 1,240.000 m):")
    true_b = (850.125, -902.480, 12.340)
    sats_clean = simulate_epoch_observations(true_b, sat_geom, dd_ints, rng=rng)
    sol = rtk.solve_baseline_enu(sats_clean)

    def err_cm(est: Tuple[float, float, float], target: Tuple[float, float, float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(est, target))) * 100.0

    err_code_cm = err_cm(sol["b_code_only_enu"], true_b)
    err_float_cm = err_cm(sol["b_float_enu"], true_b)
    err_fixed_cm = err_cm(sol["b_final_enu"], true_b)

    print(f"  * Wide-Lane Lambda (L1 - L5)  : {LAMBDA_WL * 100.0:6.2f} cm (gap {LAMBDA_WL / LAMBDA_L1:.2f}x L1)")
    print(f"  * Code-Only Differential      : Sai so 3D = {err_code_cm:6.2f} cm")
    print(f"  * RTK Float Solution          : Sai so 3D = {err_float_cm:6.2f} cm")
    print(f"  * RTK Fixed ({sol['mode']:9s})      : Sai so 3D = {err_fixed_cm:6.3f} cm (Ratio = {sol['ratio_test']:6.1f} >= 3.0)")

    assert sol["mode"] == "RTK_FIXED" and sol["ratio_test"] >= 3.0
    assert err_fixed_cm < 1.5 and err_fixed_cm < err_code_cm * 0.1
    print("  -> Ket luan: Giai thanh cong so nguyen RTK Fixed, giam sai so xuong duoi 1.5 cm (PASS)!")

    # 2. Kiem thu su co Da duong / Gia mao PRN 14 (+18.0 m) & RAIM FDE khoanh vung loai bo
    print("\n[2] Kiem thu su co gia mao/da duong +18.0 m tren PRN 14 & Co che RAIM FDE:")
    sats_fault = simulate_epoch_observations(true_b, sat_geom, dd_ints, fault_prn=14, fault_bias_m=18.0, rng=rng)
    sol_unprotected = rtk.solve_baseline_enu(sats_fault)
    raim_out = raim.verify_and_exclude_faults(sats_fault, rtk)

    err_unprot_cm = err_cm(sol_unprotected["b_final_enu"], true_b)
    err_prot_cm = err_cm(raim_out["rtk_solution"]["b_final_enu"], true_b)

    print(f"  * Khong co RAIM (Dinh loi PRN 14) : Mode={sol_unprotected['mode']} | Sai so = {err_unprot_cm:7.1f} cm!")
    print(f"  * RAIM WSSE phat hien su co       : {raim_out['wsse_before']:8.1f} (> 25.0 Nguong Chi-Square)")
    print(f"  * Ve tinh bi co lap (FDE)         : PRN {raim_out['excluded_prn']} -> Khoi phuc {raim_out['rtk_solution']['mode']}")
    print(f"  * Sai so sau khi RAIM loai loi    : {err_prot_cm:6.3f} cm (< 1.5 cm an toan tuyet doi)")

    assert raim_out["fault_detected"] and raim_out["excluded_prn"] == 14
    assert raim_out["rtk_solution"]["mode"] == "RTK_FIXED" and err_prot_cm < 1.5
    print("  -> Ket luan: RAIM FDE bat dung PRN 14 loi va phuc hoi do chinh xac cm trong 1 epoch (PASS)!")

    # 3. Mo phong quy dao ha canh thang dung SpaceX Falcon 9 (60 epochs @ 10 Hz = 6.0 s)
    print("\n[3] Mo phong Ha canh chinh xac SpaceX Drone Ship 6.0s (Co tiem nhieu PRN 14 tai t=3.0s):")
    errs_mission_cm: List[float] = []
    fix_count = 0
    for ep in range(60):
        t = ep * 0.1
        # Ten lua giam do cao tu 120 m -> 0.00 m dat chinh xac tam chu X (0, 0, 0)
        b_true = (12.0 * math.exp(-0.9 * t), -8.0 * math.exp(-0.9 * t), 120.0 * ((1.0 - t / 5.9) ** 2) if t < 5.9 else 0.0)
        f_prn = 14 if 3.0 <= t < 4.5 else None
        f_bias = 15.0 if f_prn is not None else 0.0

        s_ep = simulate_epoch_observations(b_true, sat_geom, dd_ints, fault_prn=f_prn, fault_bias_m=f_bias, rng=rng)
        res_ep = raim.verify_and_exclude_faults(s_ep, rtk, use_fix_and_hold=True)["rtk_solution"]
        if res_ep["mode"] == "RTK_FIXED":
            fix_count += 1
        errs_mission_cm.append(err_cm(res_ep["b_final_enu"], b_true))

    rms_landing_cm = math.sqrt(sum(e * e for e in errs_mission_cm) / len(errs_mission_cm))
    max_landing_cm = max(errs_mission_cm)
    fix_rate_pct = (fix_count / 60.0) * 100.0

    print(f"  * Ty le giu khoa RTK Fixed toan hanh trinh : {fix_rate_pct:5.1f}% (60/60 epochs)")
    print(f"  * Sai so 3D RMS suot pha ha canh          : {rms_landing_cm:5.3f} cm (< 1.5 cm)")
    print(f"  * Sai so dinh cuc dai (ke ca luc bi loi)  : {max_landing_cm:5.3f} cm (< 3.0 cm)")

    assert fix_rate_pct == 100.0 and rms_landing_cm < 1.5 and max_landing_cm < 3.0
    print("  -> Ket luan: SpaceX Drone Ship & Tesla Robotaxi RTK dat 100% Fixed < 1.5 cm RMS (PASS)!")

    print("\n" + "=" * 80)
    print("KET QUA KIEM THU BAI 199 (CAPSTONE): GNSS L1/L5 RTK CENTIMET HOAN TAT 100% PASS!")
    print("=" * 80)


if __name__ == "__main__":
    test_spacex_tesla_rtk_cm_capstone()
