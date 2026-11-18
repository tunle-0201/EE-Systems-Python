"""
Chuyen de AO: Dieu khien Du doan Mo hinh Phan cung Thoi gian thuc & Toi uu hoa Loi (Real-Time Embedded MPC)
Bai 1 (Milestone AO.1): Mo hinh Khong gian Trang thai Roi rac hoa & Ma tran Du doan Chan troi N-buoc

Muc tieu ky thuat:
- Xay dung mo hinh khong gian trang thai thoi gian lien tuc: dx/dt = A*x + B*u.
- Roi rac hoa bang phuong phap Zero-Order Hold (ZOH) Taylor Expansion bac 3: A_d, B_d.
- Tinh toan ma tran chan troi du doan (Prediction Horizon N-steps Batch Matrices): S_x, S_u.
- Kiem tra tinh on dinh cua he thong roi rac qua tri rieng (Eigenvalues |lambda| < 1).
- Chuyen doi bai toan toi uu MPC ve dang ma tran bac hai Hessian H va Gradient g.

Luu y: Toan bo chuoi in tren console su dung tieng Viet khong dau / Tieng Anh de tuong thich 100%
voi bang ma cp1252 tren he dieu hanh Windows.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, List


@dataclass
class ContinuousStateSpace:
    """He thong khong gian trang thai lien tuc: dx/dt = A*x + B*u, y = C*x + D*u."""
    A: np.ndarray  # Ma tran dong hoc he thong (n x n)
    B: np.ndarray  # Ma tran tac dong dieu khien (n x m)
    C: np.ndarray  # Ma tran do luong dau ra (p x n)
    D: np.ndarray  # Ma tran truyen thang (p x m)


@dataclass
class DiscreteStateSpace:
    """He thong khong gian trang thai roi rac: x[k+1] = A_d*x[k] + B_d*u[k], y[k] = C_d*x[k] + D_d*u[k]."""
    A_d: np.ndarray
    B_d: np.ndarray
    C_d: np.ndarray
    D_d: np.ndarray
    dt: float


class StateSpaceDiscretizer:
    """
    Bo roi rac hoa he thong khong gian trang thai bang phuong phap giu bac 0 (Zero-Order Hold - ZOH).
    
    Cong thuc Taylor Expansion cho ma tran mu:
    A_d = I + A * dt + (1/2) * A^2 * dt^2 + (1/6) * A^3 * dt^3
    B_d = (I * dt + (1/2) * A * dt^2 + (1/6) * A^2 * dt^3) * B
    """

    @staticmethod
    def discretize_zoh(sys_c: ContinuousStateSpace, dt: float, order: int = 3) -> DiscreteStateSpace:
        n = sys_c.A.shape[0]
        I = np.eye(n)
        
        # Tinh toan A_d bang chuoi Taylor
        A_d = I.copy()
        A_power = I.copy()
        factorial = 1.0
        for k in range(1, order + 1):
            factorial *= k
            A_power = A_power @ sys_c.A
            A_d += (A_power * (dt ** k)) / factorial

        # Tinh toan B_d bang chuoi tich phan
        B_integral = I * dt
        A_power = I.copy()
        factorial = 1.0
        for k in range(1, order + 1):
            factorial *= (k + 1)
            A_power = A_power @ sys_c.A
            B_integral += (A_power * (dt ** (k + 1))) / factorial
        B_d = B_integral @ sys_c.B

        C_d = sys_c.C.copy()
        D_d = sys_c.D.copy()

        return DiscreteStateSpace(A_d=A_d, B_d=B_d, C_d=C_d, D_d=D_d, dt=dt)

    @staticmethod
    def check_stability(A_d: np.ndarray) -> Tuple[bool, np.ndarray]:
        """
        Kiem tra do on dinh Asymptotic Stability cua he roi rac:
        He on dinh khi va chi khi tat ca cac gia tri rieng nam trong vong tron don vi: |lambda_i| < 1.0.
        """
        eigenvalues = np.linalg.eigvals(A_d)
        magnitudes = np.abs(eigenvalues)
        is_stable = np.all(magnitudes < 1.0)
        return is_stable, eigenvalues


class MPCPredictionHorizon:
    """
    Xay dung cac ma tran du doan chan troi N-buoc cho bo dieu khien MPC.
    
    Dang vector gop (Batch Formulation):
    X = [x_1; x_2; ...; x_N]
    U = [u_0; u_1; ...; u_{N-1}]
    
    X = S_x * x_0 + S_u * U
    """

    def __init__(self, sys_d: DiscreteStateSpace, horizon_N: int):
        self.sys_d = sys_d
        self.N = horizon_N
        self.n_states = sys_d.A_d.shape[0]
        self.n_inputs = sys_d.B_d.shape[1]

        self.S_x, self.S_u = self._build_prediction_matrices()

    def _build_prediction_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        n = self.n_states
        m = self.n_inputs
        N = self.N
        A_d = self.sys_d.A_d
        B_d = self.sys_d.B_d

        # Khoi tao S_x kich thuoc (N*n, n)
        S_x = np.zeros((N * n, n))
        A_power = A_d.copy()
        for i in range(N):
            S_x[i * n:(i + 1) * n, :] = A_power
            A_power = A_power @ A_d

        # Khoi tao S_u kich thuoc (N*n, N*m)
        S_u = np.zeros((N * n, N * m))
        for row in range(N):
            for col in range(row + 1):
                power = row - col
                if power == 0:
                    block = B_d
                else:
                    A_pow = np.linalg.matrix_power(A_d, power)
                    block = A_pow @ B_d
                S_u[row * n:(row + 1) * n, col * m:(col + 1) * m] = block

        return S_x, S_u

    def build_qp_cost_matrices(self, Q_diag: List[float], R_diag: List[float], x_0: np.ndarray, x_ref: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Chuyen doi ham mat mat MPC ve dang ma tran bac hai chuan:
        Cost(U) = (1/2) * U^T * H * U + g^T * U
        
        Q: Ma tran phat sai so trang thai (State Weighting Matrix)
        R: Ma tran phat nang luong dieu khien (Actuator Effort Weighting Matrix)
        """
        n = self.n_states
        m = self.n_inputs
        N = self.N

        Q_block = np.diag(Q_diag)
        R_block = np.diag(R_diag)

        # Q_bar: (N*n, N*n) block diagonal
        Q_bar = np.kron(np.eye(N), Q_block)
        # R_bar: (N*m, N*m) block diagonal
        R_bar = np.kron(np.eye(N), R_block)

        # X_ref_bar: vector tham chieu (N*n, 1)
        X_ref = np.tile(x_ref, (N, 1)).reshape(-1, 1)
        x_0_col = x_0.reshape(-1, 1)

        # Hessian Matrix H = 2 * (S_u^T * Q_bar * S_u + R_bar)
        # De chuan hoa dang 1/2 * U^T * H * U, ta dinh nghia H = 2 * (...)
        H = 2.0 * (self.S_u.T @ Q_bar @ self.S_u + R_bar)
        
        # Gradient Vector g = 2 * S_u^T * Q_bar * (S_x * x_0 - X_ref)
        error_free_response = (self.S_x @ x_0_col) - X_ref
        g = 2.0 * (self.S_u.T @ Q_bar @ error_free_response).flatten()

        return H, g


def run_state_space_mpc_test():
    """Kiem thu toan dien bo roi rac hoa va ma tran du doan MPC."""
    print("=" * 80)
    print("BAT DAU KIEM CHUAN MO HINH ROI RAC HOA KHONG GIAN TRANG THAI VA CHAN TROI MPC")
    print("=" * 80)

    # Vi du he thong vat ly: Con lac nguoc tren xe hoac dong hoc bieu dien goc nghieng ten lua
    # Trang thai x = [vi tri x (m), van toc v (m/s), goc nghieng theta (rad), van toc goc omega (rad/s)]
    # Dau vao u = [luc day F (N)]
    A_cont = np.array([
        [0.0, 1.0, 0.0,  0.0],
        [0.0, -0.1, 0.5, 0.0],
        [0.0, 0.0, 0.0,  1.0],
        [0.0, 0.0, 9.81, -0.2]
    ])
    B_cont = np.array([
        [0.0],
        [0.8],
        [0.0],
        [1.5]
    ])
    C_cont = np.eye(4)
    D_cont = np.zeros((4, 1))

    sys_c = ContinuousStateSpace(A=A_cont, B=B_cont, C=C_cont, D=D_cont)
    dt = 0.05  # Chu ky lay mau 50 ms (20 Hz)
    horizon_N = 10  # Chan troi du doan 10 buoc (0.5 giay)

    print(f"1. Roi rac hoa he thong voi chu ky dt = {dt*1000:.1f} ms...")
    sys_d = StateSpaceDiscretizer.discretize_zoh(sys_c, dt=dt, order=3)
    
    print("-> Ma tran A_d (4x4):")
    print(np.round(sys_d.A_d, 4))
    print("\n-> Ma tran B_d (4x1):")
    print(np.round(sys_d.B_d, 4))

    # Kiem tra gia tri rieng
    is_stable, eigs = StateSpaceDiscretizer.check_stability(sys_d.A_d)
    print(f"\n2. Kiem tra tinh on dinh cua he thong roi rac:")
    print(f"-> Gia tri rieng (Eigenvalues): {np.round(eigs, 4)}")
    print(f"-> Do lon gia tri rieng (Magnitudes): {np.round(np.abs(eigs), 4)}")
    print(f"-> Ket luan on dinh: {'He on dinh' if is_stable else 'He khong on dinh tu than (Can bo dieu khien MPC hoi tiep)'}")

    # Xay dung ma tran du doan chan troi
    print(f"\n3. Xay dung ma tran du doan chan troi N = {horizon_N} buoc...")
    mpc_pred = MPCPredictionHorizon(sys_d, horizon_N=horizon_N)
    print(f"-> Kich thuoc ma tran S_x: {mpc_pred.S_x.shape} (Ky vong: ({horizon_N*4}, 4))")
    print(f"-> Kich thuoc ma tran S_u: {mpc_pred.S_u.shape} (Ky vong: ({horizon_N*4}, {horizon_N*1}))")
    assert mpc_pred.S_x.shape == (horizon_N * 4, 4), "Kich thuoc S_x khong chinh xac!"
    assert mpc_pred.S_u.shape == (horizon_N * 4, horizon_N * 1), "Kich thuoc S_u khong chinh xac!"

    # Chuyen doi sang dang QP Hessian H va Gradient g
    print(f"\n4. Tinh toan ma tran bac hai Hessian H va Gradient g cua bai toan QP...")
    Q_diag = [10.0, 1.0, 20.0, 2.0]  # Phat sai so vi tri va goc nghieng
    R_diag = [0.1]                    # Phat luc day dieu khien
    x_0 = np.array([1.0, 0.0, 0.1, 0.0])  # Vi tri ban dau lech 1m, nghieng 0.1 rad
    x_ref = np.array([0.0, 0.0, 0.0, 0.0]) # Muc tieu keo ve 0

    H, g = mpc_pred.build_qp_cost_matrices(Q_diag, R_diag, x_0, x_ref)
    print(f"-> Kich thuoc Hessian H : {H.shape} (Ky vong: ({horizon_N}, {horizon_N}))")
    print(f"-> Kich thuoc Gradient g: {g.shape} (Ky vong: ({horizon_N},))")

    # Kiem tra Hessian phai doi xung va xac dinh duong (Symmetric Positive Definite - SPD)
    is_symmetric = np.allclose(H, H.T, atol=1e-8)
    eigs_H = np.linalg.eigvals(H)
    is_positive_definite = np.all(eigs_H > 0)
    print(f"-> Hessian doi xung (Symmetric)         : {is_symmetric}")
    print(f"-> Hessian xac dinh duong (Positive Def): {is_positive_definite} (Min eig: {np.min(eigs_H):.4f})")
    assert is_symmetric, "Hessian phai doi xung!"
    assert is_positive_definite, "Hessian phai xac dinh duong de dam bao cuc tieu duy nhat!"

    print("\n" + "=" * 80)
    print("[PASS] 100% Kiem thu Roi rac hoa va Ma tran Chan troi MPC thanh cong!")
    print("=" * 80)


if __name__ == "__main__":
    run_state_space_mpc_test()
