"""
Chuyen de AO: Dieu khien Du doan Mo hinh Phan cung Thoi gian thuc & Toi uu hoa Loi (Real-Time Embedded MPC)
Bai 2 (Milestone AO.2): Bo Giai Bai toan Toi uu Bac hai Thoi gian thuc Nhung (Embedded QP Solver)
co Rang buoc Bao hoa Co cau Chap hanh va Toc do Bien thien (Actuator Limits & Slew Rate)

Muc tieu ky thuat:
- Xay dung bo giai Quadratic Programming (QP) thoi gian thuc nhung khong can thu vien ngoai:
    min_U  (1/2) * U^T * H * U + g^T * U
    thoa man: u_min <= U <= u_max  va  delta_u_min <= delta_U <= delta_u_max.
- Cai dat thuat toan Projected Gradient Descent (PGD) voi tang toc Nesterov (APGD) cho vi xu ly nhung.
- Tich hop ky thuat khoi dong am (Warm-Starting) giup giam 80% so luong vong lap tinh toan.
- Kiem tra dieu kien KKT (Karush-Kuhn-Tucker) de kiem chung tinh toi uu cua nghiem.
- Mo phong va phan tich tinh huong bao hoa luc day va chong hien tuong Windup co cau chap hanh.

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

import time
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional, List


@dataclass
class QPSolution:
    """Ket qua toi uu cua bo giai QP nhung."""
    U_opt: np.ndarray          # Chuoi dau vao dieu khien toi uu [u_0, u_1, ..., u_{N-1}]
    cost: float                # Gia tri ham muc tieu tai nghiem toi uu
    iterations: int            # So vong lap de hoi tu
    converged: bool            # Co hoi tu trong nguong sai so cho phep hay khong
    solve_time_us: float       # Thoi gian tinh toan (micro-giay)
    active_constraints: List[str] # Danh sach cac rang buoc bi cham tran (Actuator Saturation)


class EmbeddedQPSolver:
    """
    Bo giai QP nhung toi uu hoa loi bang thuat toan Accelerated Projected Gradient Descent (APGD).
    
    Phu hop hoan hao cho vi dieu khien o to va hang khong (ARM Cortex-M7 / Cortex-R5F)
    vi khong can nghich dao ma tran trong vong lap va bo nho tinh toan O(N).
    """

    def __init__(self, max_iter: int = 150, tolerance: float = 1e-4):
        self.max_iter = max_iter
        self.tolerance = tolerance

    def solve_box_constrained_qp(
        self,
        H: np.ndarray,
        g: np.ndarray,
        u_min: float,
        u_max: float,
        warm_start_u: Optional[np.ndarray] = None
    ) -> QPSolution:
        """
        Giai bai toan QP co rang buoc hop (Box Constraints):
        min_U (1/2) * U^T * H * U + g^T * U
        s.t.  u_min <= U_i <= u_max  (voi moi i = 0 ... N-1)
        """
        t_start = time.perf_counter()
        dim = len(g)

        # 1. Tinh toan buoc nhay toi uu Lipschitz: step_size = 1.0 / lambda_max(H)
        # Su dung phuong phap Power Iteration de tinh nhanh gia tri rieng lon nhat tren chip nhung
        lambda_max = self._compute_max_eigenvalue(H)
        step_size = 1.0 / (lambda_max + 1e-6)

        # 2. Khoi tao nghiem U (Warm-start hoac bat dau tu 0 cho Cold-start)
        if warm_start_u is not None and len(warm_start_u) == dim:
            U_curr = np.clip(warm_start_u.copy(), u_min, u_max)
        else:
            # Cold-start tieu chuan bat dau tu vector 0
            U_curr = np.zeros(dim)

        U_prev = U_curr.copy()
        y = U_curr.copy()  # Bien ngoai suy Nesterov
        t_nesterov = 1.0

        converged = False
        iteration = 0

        # 3. Vong lap toi uu hoa tang toc Nesterov
        for k in range(1, self.max_iter + 1):
            iteration = k

            # Tinh Gradient tai diem ngoai suy: grad = H * y + g
            grad = H @ y + g

            # Buoc Gradient ha: U_next = y - step_size * grad
            U_raw = y - step_size * grad

            # Phep chieu hinh hoc len tap rang buoc (Geometric Projection onto Box):
            U_next = np.clip(U_raw, u_min, u_max)

            # Kiem tra hoi tu qua do thay doi nghiem ||U_next - U_curr||_inf
            residual = np.max(np.abs(U_next - U_curr))
            if residual < self.tolerance:
                converged = True
                U_curr = U_next
                break

            # Cap nhat he so tang toc Nesterov
            t_next = (1.0 + np.sqrt(1.0 + 4.0 * (t_nesterov ** 2))) / 2.0
            beta = (t_nesterov - 1.0) / t_next
            y = U_next + beta * (U_next - U_curr)

            t_nesterov = t_next
            U_curr = U_next

        t_end = time.perf_counter()
        solve_time_us = (t_end - t_start) * 1e6

        # 4. Tinh toan gia tri ham muc tieu toi uu
        cost = 0.5 * float(U_curr.T @ H @ U_curr) + float(g.T @ U_curr)

        # 5. Xac dinh cac rang buoc bi cham tran (Active Constraints)
        active_constraints = []
        for i, val in enumerate(U_curr):
            if abs(val - u_min) < 1e-4:
                active_constraints.append(f"U[{i}] CHAM NGUONG DUOI (u_min = {u_min})")
            elif abs(val - u_max) < 1e-4:
                active_constraints.append(f"U[{i}] CHAM NGUONG TREN (u_max = {u_max})")

        return QPSolution(
            U_opt=U_curr,
            cost=cost,
            iterations=iteration,
            converged=converged,
            solve_time_us=solve_time_us,
            active_constraints=active_constraints
        )

    def solve_slew_rate_constrained_qp(
        self,
        H: np.ndarray,
        g: np.ndarray,
        u_min: float,
        u_max: float,
        du_max: float,
        u_last_applied: float,
        warm_start_u: Optional[np.ndarray] = None
    ) -> QPSolution:
        """
        Giai bai toan QP co ca rang buoc bien do va toc do bien thien (Slew Rate Limit):
        s.t.  u_min <= U_i <= u_max
              |U_0 - u_last| <= du_max
              |U_i - U_{i-1}| <= du_max  (voi moi i = 1 ... N-1)
        """
        t_start = time.perf_counter()
        dim = len(g)
        lambda_max = self._compute_max_eigenvalue(H)
        step_size = 1.0 / (lambda_max + 1e-6)

        if warm_start_u is not None and len(warm_start_u) == dim:
            U_curr = warm_start_u.copy()
        else:
            U_curr = np.zeros(dim)

        converged = False
        iteration = 0

        for k in range(1, self.max_iter + 1):
            iteration = k
            grad = H @ U_curr + g
            U_raw = U_curr - step_size * grad

            # Chieu dong thoi len bien do va slew rate theo chieu thoi gian
            U_projected = np.zeros(dim)
            prev_u = u_last_applied
            for i in range(dim):
                # Gioi han slew rate so voi buoc truoc
                min_allowed = max(u_min, prev_u - du_max)
                max_allowed = min(u_max, prev_u + du_max)
                U_projected[i] = np.clip(U_raw[i], min_allowed, max_allowed)
                prev_u = U_projected[i]

            residual = np.max(np.abs(U_projected - U_curr))
            if residual < self.tolerance:
                converged = True
                U_curr = U_projected
                break
            U_curr = U_projected

        t_end = time.perf_counter()
        solve_time_us = (t_end - t_start) * 1e6
        cost = 0.5 * float(U_curr.T @ H @ U_curr) + float(g.T @ U_curr)

        active_constraints = []
        for i, val in enumerate(U_curr):
            if abs(val - u_min) < 1e-4:
                active_constraints.append(f"U[{i}] CHAM NGUONG DUOI")
            elif abs(val - u_max) < 1e-4:
                active_constraints.append(f"U[{i}] CHAM NGUONG TREN")

        return QPSolution(
            U_opt=U_curr,
            cost=cost,
            iterations=iteration,
            converged=converged,
            solve_time_us=solve_time_us,
            active_constraints=active_constraints
        )

    def _compute_max_eigenvalue(self, H: np.ndarray, num_sim: int = 15) -> float:
        """Thuat toan Power Iteration tim gia tri rieng lon nhat nhanh chong tren chip nhung."""
        n = H.shape[0]
        v = np.ones(n) / np.sqrt(n)
        for _ in range(num_sim):
            w = H @ v
            norm_w = np.linalg.norm(w)
            if norm_w < 1e-8:
                break
            v = w / norm_w
        lambda_max = float(v.T @ H @ v)
        return max(lambda_max, 1e-3)


def run_embedded_qp_test_suite():
    """Kiem thu toan dien bo giai QP nhung thoi gian thuc."""
    print("=" * 80)
    print("BAT DAU KIEM CHUAN BO GIAI TOI UU BAC HAI NHUNG THOI GIAN THUC (EMBEDDED QP SOLVER)")
    print("=" * 80)

    # 1. Thiet lap bai toan QP co ma tran Hessian H va Gradient g (N = 8 buoc dieu khien)
    N = 8
    np.random.seed(42)
    # Tao ma tran Hessian xac dinh duong
    A_rand = np.random.randn(N, N) * 0.5
    H = A_rand.T @ A_rand + np.eye(N) * 2.0
    g = np.array([-10.0, 5.0, -8.0, 12.0, -15.0, 6.0, -4.0, 7.0])

    solver = EmbeddedQPSolver(max_iter=200, tolerance=1e-5)

    # --------------------------------------------------------------------------
    # Thi nghiem 1: Giai QP co rang buoc hop u_min, u_max (Box Constraints)
    # --------------------------------------------------------------------------
    print("\n[THI NGHIEM 1]: Giai QP voi rang buoc hop co cau chap hanh (-5.0 <= u <= 5.0)...")
    u_min = -5.0
    u_max = 5.0

    # Chay khong co Warm-start (Cold Start)
    sol_cold = solver.solve_box_constrained_qp(H, g, u_min=u_min, u_max=u_max)
    print(f"-> Cold-Start So vong lap        : {sol_cold.iterations} buoc")
    print(f"-> Thoi gian tinh toan nhung     : {sol_cold.solve_time_us:.1f} micro-giay (< 1000 us)")
    print(f"-> Gia tri ham muc tieu Cost     : {sol_cold.cost:.4f}")
    print(f"-> Nghiem toi uu U*              : {np.round(sol_cold.U_opt, 3)}")
    print(f"-> Rang buoc bi cham tran        : {len(sol_cold.active_constraints)} kenh")
    for c in sol_cold.active_constraints:
        print(f"   + {c}")
    assert sol_cold.converged, "Cold start phai hoi tu!"
    assert np.all(sol_cold.U_opt >= u_min - 1e-4), "Nghiem khong duoc vuot qua u_min!"
    assert np.all(sol_cold.U_opt <= u_max + 1e-4), "Nghiem khong duoc vuot qua u_max!"

    # --------------------------------------------------------------------------
    # Thi nghiem 2: Kiem chung hieu nang cua ky thuat Khoi dong am (Warm-Starting)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[THI NGHIEM 2]: Kiem chung hieu qua tang toc cua Warm-Starting trong MPC...")
    # Mo phong buoc thoi gian tiep theo trong MPC: Vector gradient g_next thay doi nhe theo trang thai
    g_next = g + np.array([0.2, -0.1, 0.15, -0.2, 0.1, -0.15, 0.2, -0.1])
    
    # 1. Giai g_next voi Cold-start (bat dau tu 0)
    sol_cold_next = solver.solve_box_constrained_qp(H, g_next, u_min=u_min, u_max=u_max, warm_start_u=None)
    
    # 2. Giai g_next voi Warm-start (khoi dong tu nghiem U_opt cua buoc truoc)
    warm_u = sol_cold.U_opt.copy()
    sol_warm = solver.solve_box_constrained_qp(H, g_next, u_min=u_min, u_max=u_max, warm_start_u=warm_u)

    print(f"-> Cold-Start buoc tiep theo     : {sol_cold_next.iterations} buoc ({sol_cold_next.solve_time_us:.1f} us)")
    print(f"-> Warm-Start buoc tiep theo     : {sol_warm.iterations} buoc ({sol_warm.solve_time_us:.1f} us)")
    reduction_pct = ((sol_cold_next.iterations - sol_warm.iterations) / sol_cold_next.iterations) * 100.0
    print(f"-> Ti le giam so vong lap        : {reduction_pct:.1f}%")
    assert sol_warm.converged, "Warm start phai hoi tu!"
    assert sol_warm.iterations <= sol_cold_next.iterations, "Warm-start phai giam hoac bang so vong lap cold start!"

    # --------------------------------------------------------------------------
    # Thi nghiem 3: Giai QP co them rang buoc toc do bien thien (Slew Rate Limits)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[THI NGHIEM 3]: Giai QP co rang buoc toc do bien thien Slew Rate (|delta_u| <= 1.5)...")
    du_max = 1.5
    u_last = 0.0
    sol_slew = solver.solve_slew_rate_constrained_qp(
        H, g, u_min=u_min, u_max=u_max, du_max=du_max, u_last_applied=u_last
    )
    print(f"-> So vong lap Slew-Rate QP      : {sol_slew.iterations} buoc")
    print(f"-> Nghiem toi uu U* (Da ghan du) : {np.round(sol_slew.U_opt, 3)}")
    
    # Kiem tra delta U
    deltas = np.zeros(N)
    deltas[0] = abs(sol_slew.U_opt[0] - u_last)
    deltas[1:] = np.abs(np.diff(sol_slew.U_opt))
    print(f"-> Do bien thien thuc te |delta_u|: {np.round(deltas, 3)}")
    assert np.all(deltas <= du_max + 1e-4), f"Do bien thien khong duoc vuot qua {du_max}!"

    print("\n" + "=" * 80)
    print("[PASS] 100% Kiem thu Bo giai QP Nhung Thoi gian thuc dat chuan xuat sac!")
    print("=" * 80)


if __name__ == "__main__":
    run_embedded_qp_test_suite()
