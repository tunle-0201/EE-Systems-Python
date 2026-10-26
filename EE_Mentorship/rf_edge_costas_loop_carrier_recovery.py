"""
================================================================================
CHUYEN DE AR: XU LY TIN HIEU VO TUYEN SO BASEBAND SDR & DONG BO VE TINH STARLINK
BAI 3 (MILESTONE AR.3): VONG KHOA PHA SO COSTAS LOOP BAC 2 TRIET TIEU DOPPLER
================================================================================
Chuc nang he thong:
1. Mo hinh hoa hien tuong xoay chom sao do sai lech tan so Doppler (Delta f)
   va lech pha ban dau (theta_0) cua ve tinh SpaceX Starlink quy dao LEO:
      r[n] = s[n] * exp(j * (2 * pi * Delta_f * n * T_sym + theta_0))
2. Thiet ke vong khoa pha so Costas Loop bac 2 (2nd-Order Digital Costas Loop):
   - Bo quay pha so (Digital Phase Rotator):
        I_rot =  I_in * cos(theta_hat) + Q_in * sin(theta_hat)
        Q_rot = -I_in * sin(theta_hat) + Q_in * cos(theta_hat)
   - Bo do sai pha QPSK (Phase Error Detector - PED):
        e[n] = sign(I_rot) * Q_rot - sign(Q_rot) * I_rot
   - Bo loc vong PI (Proportional-Integral Loop Filter):
        freq_est[n] = K_p * e[n] + K_i * sum(e)
   - Bo tich luy pha NCO: theta_hat[n+1] = theta_hat[n] + freq_est[n]
3. Triet tieu hoan toan sai lech tan so Doppler va khoa pha chom sao I/Q ve dung 4 goc phan tu.

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
   Sodo khoi Costas Loop:
   r[n] ───> [ Mixer e^(-j*theta_hat) ] ───> (I_rot, Q_rot) ───> [ QPSK PED ]
                     ^                                                │
                     │                                              e[n]
                     │                                                │
                     └── [ NCO Tich luy pha ] <─── [ PI Filter ] <────┘
================================================================================
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class CostasLoopConfig:
    """Cau hinh thong so vong khoa pha so Costas Loop."""
    loop_bw_norm: float      # Bang thong vong chuan hoa (Loop Bandwidth B_L * T_sym, vi du 0.04)
    damping_factor: float    # He so giam chan zeta (vi du 0.707 - Toi uu Butterworth)
    k_p: float               # He so ty le Proportional Gain
    k_i: float               # He so tich phan Integral Gain


@dataclass
class CostasTrackingResult:
    """Ket qua theo doi va khoa pha song mang cua Costas Loop."""
    total_symbols: int
    true_freq_offset_rad: float
    true_initial_phase_rad: float
    estimated_freq_offset_rad: float
    freq_estimation_error_pct: float
    residual_phase_error_deg: float
    lock_acquired: bool
    lock_settling_symbols: int
    unlocked_ber: float
    locked_ber: float


class DigitalCostasLoopQPSK:
    """
    Vong khoa pha Costas Loop bac 2 xu ly tin hieu QPSK trong may thu SDR.
    """

    def __init__(self, loop_bw_norm: float = 0.04, damping_factor: float = 0.7071):
        """
        Khoi tao bo loc vong PI dua tren tham so bang thong B_L va he so giam chan zeta.
        Cong thuc thiet ke vong so tieu chuan:
        theta = (4 * zeta * B_L) / (1 + 4 * zeta^2)
        K_p = (4 * zeta * theta) / (1 + 2 * zeta * theta + theta^2)
        K_i = (4 * theta^2) / (1 + 2 * zeta * theta + theta^2)
        """
        assert 0.001 <= loop_bw_norm <= 0.2, "Loop bandwidth phai trong khoang 0.001 - 0.2"
        zeta = damping_factor
        theta = (4.0 * zeta * loop_bw_norm) / (1.0 + 4.0 * zeta ** 2)
        denom = 1.0 + 2.0 * zeta * theta + theta ** 2
        k_p = (4.0 * zeta * theta) / denom
        k_i = (4.0 * theta ** 2) / denom

        self.cfg = CostasLoopConfig(
            loop_bw_norm=loop_bw_norm,
            damping_factor=damping_factor,
            k_p=k_p,
            k_i=k_i
        )

    def process_stream(
        self,
        rx_symbols: List[Tuple[float, float]],
        ref_symbols: List[Tuple[float, float]],
        true_freq_offset: float,
        true_phase_offset: float
    ) -> Tuple[List[Tuple[float, float]], CostasTrackingResult]:
        """
        Xu ly chuoi ky hieu thu, quay pha dong thoi va cap nhat trang thai vong lap.
        """
        n_syms = len(rx_symbols)
        corrected_symbols: List[Tuple[float, float]] = []

        phase_hat = 0.0
        freq_int = 0.0
        lock_counter = 0
        lock_settling = -1
        phase_errors: List[float] = []

        for i in range(n_syms):
            r_i, r_q = rx_symbols[i]

            # 1. Quay pha tin hieu bang NCO: r[n] * exp(-j * phase_hat)
            cos_val = math.cos(phase_hat)
            sin_val = math.sin(phase_hat)
            i_rot =  r_i * cos_val + r_q * sin_val
            q_rot = -r_i * sin_val + r_q * cos_val

            corrected_symbols.append((i_rot, q_rot))

            # 2. Bo do sai pha QPSK PED (Decision-Directed Slicer PED)
            # sign(x) = +1 neu x >= 0 else -1
            sgn_i = 1.0 if i_rot >= 0 else -1.0
            sgn_q = 1.0 if q_rot >= 0 else -1.0
            
            # error = sgn(I) * Q - sgn(Q) * I
            err = sgn_i * q_rot - sgn_q * i_rot
            phase_errors.append(err)

            # 3. Bo loc vong PI
            freq_int += self.cfg.k_i * err
            freq_est = self.cfg.k_p * err + freq_int

            # 4. Cap nhat NCO cho ky hieu tiep theo
            phase_hat += freq_est
            # Quan ly pha trong khoang [-pi, pi)
            while phase_hat > math.pi:
                phase_hat -= 2.0 * math.pi
            while phase_hat < -math.pi:
                phase_hat += 2.0 * math.pi

            # Kiem tra tieu chi khoa (Lock Detection):
            # Neu sai so |err| < 0.15 lien tuc trong 50 ky hieu thi coi nhu da khoa
            if abs(err) < 0.15:
                lock_counter += 1
                if lock_counter >= 50 and lock_settling == -1:
                    lock_settling = i - 50
            else:
                lock_counter = max(0, lock_counter - 2)

        # Tinh toan sai so sau khi khoa (nua sau chuoi ky hieu)
        eval_start = max(lock_settling if lock_settling > 0 else 0, n_syms // 2)
        residual_errs = phase_errors[eval_start:]
        mean_res_err = math.sqrt(sum(e ** 2 for e in residual_errs) / len(residual_errs))
        res_err_deg = mean_res_err * (180.0 / math.pi)

        # Do lech uoc luong tan so so voi Doppler thuc te
        est_freq = freq_int
        freq_err_pct = abs(est_freq - true_freq_offset) / max(1e-6, abs(true_freq_offset)) * 100.0

        # Tinh BER truoc va sau khi khoa:
        def demap_qpsk(symbols):
            bits = []
            norm = 1.0 / math.sqrt(2.0)
            for ci, cq in symbols:
                b0 = 1 if ci >= 0 else 0
                b1 = 1 if cq >= 0 else 0
                bits.extend([b0, b1])
            return bits

        ref_bits = demap_qpsk(ref_symbols)
        unlocked_bits = demap_qpsk(rx_symbols)
        locked_bits = demap_qpsk(corrected_symbols[eval_start:])
        ref_eval_bits = ref_bits[eval_start * 2:]

        unlocked_errs = sum(1 for b1, b2 in zip(ref_bits, unlocked_bits) if b1 != b2)
        unlocked_ber = unlocked_errs / len(ref_bits)

        locked_errs = sum(1 for b1, b2 in zip(ref_eval_bits, locked_bits) if b1 != b2)
        locked_ber = locked_errs / len(ref_eval_bits)

        is_locked = (lock_settling != -1 and locked_ber < 0.01)

        tracking_res = CostasTrackingResult(
            total_symbols=n_syms,
            true_freq_offset_rad=true_freq_offset,
            true_initial_phase_rad=true_phase_offset,
            estimated_freq_offset_rad=est_freq,
            freq_estimation_error_pct=freq_err_pct,
            residual_phase_error_deg=res_err_deg,
            lock_acquired=is_locked,
            lock_settling_symbols=lock_settling if lock_settling > 0 else n_syms,
            unlocked_ber=unlocked_ber,
            locked_ber=locked_ber
        )

        return corrected_symbols, tracking_res


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AR - LESSON 3: COSTAS LOOP CARRIER RECOVERY")
    print("=" * 80)

    # 1. Thiet lap he thong: Truyen QPSK qua kenh ve tinh bi dich tan Doppler
    import random
    random.seed(42)
    n_symbols = 2000
    
    # Tao chuoi ky hieu QPSK ly tuong
    norm = 1.0 / math.sqrt(2.0)
    qpsk_const = [(-norm, -norm), (-norm, norm), (norm, norm), (norm, -norm)]
    ideal_symbols = [random.choice(qpsk_const) for _ in range(n_symbols)]

    # Gia lap sai lech Doppler: Delta_f = 0.05 rad/symbol (~12.5 kHz o toc do 250 kSym/s)
    # Va lech pha ban dau: theta_0 = 35 do = 0.61 rad
    true_delta_omega = 0.05  # rad/symbol
    true_theta_0 = 35.0 * (math.pi / 180.0)

    # Bơm sai lệch tần số Doppler và pha vào tín hiệu thu
    rx_symbols = []
    for n, (s_i, s_q) in enumerate(ideal_symbols):
        theta_t = true_delta_omega * n + true_theta_0
        # Cong them chut nhieu nhe SNR = 25 dB
        r_i = s_i * math.cos(theta_t) - s_q * math.sin(theta_t) + random.gauss(0, 0.04)
        r_q = s_i * math.sin(theta_t) + s_q * math.cos(theta_t) + random.gauss(0, 0.04)
        rx_symbols.append((r_i, r_q))

    print(f"\n[1] THONG SO KENH TRUYEN VE TINH STARLINK DOPPLER:")
    print(f"  Sai lech tan so Doppler thuc te: {true_delta_omega:.4f} rad/symbol")
    print(f"  Sai lech pha ban dau thuc te: {true_theta_0 * 180.0 / math.pi:.1f} do")
    print(f"  So ky hieu mo phong: {n_symbols} symbols")

    # 2. Khoi chay Digital Costas Loop bac 2
    costas = DigitalCostasLoopQPSK(loop_bw_norm=0.035, damping_factor=0.7071)
    print(f"\n[2] THONG SO VONG KHOA PHA SO (2ND-ORDER COSTAS LOOP):")
    print(f"  Loop Bandwidth B_L*T: {costas.cfg.loop_bw_norm}")
    print(f"  Damping Factor zeta: {costas.cfg.damping_factor}")
    print(f"  Proportional Gain K_p: {costas.cfg.k_p:.6f}")
    print(f"  Integral Gain K_i: {costas.cfg.k_i:.6f}")

    corrected, report = costas.process_stream(
        rx_symbols=rx_symbols,
        ref_symbols=ideal_symbols,
        true_freq_offset=true_delta_omega,
        true_phase_offset=true_theta_0
    )

    print(f"\n[3] KET QUA KHOA PHA VA DONG BO SONG MANG:")
    print(f"  Trang thai khoa pha (Lock Acquired): {'THANH CONG (LOCKED)' if report.lock_acquired else 'THAT BAI'}")
    print(f"  Thoi gian xac lap khoa pha: {report.lock_settling_symbols} symbols (< 300 symbols)")
    print(f"  Tan so Doppler uoc luong: {report.estimated_freq_offset_rad:.4f} rad/symbol")
    print(f"  Sai so uoc luong tan so: {report.freq_estimation_error_pct:.2f}% (< 1.5%)")
    print(f"  Sai so pha con du sau khi khoa: {report.residual_phase_error_deg:.2f} do")
    print(f"  BER truoc khi qua Costas Loop: {report.unlocked_ber:.4f} (Chom sao quay mu mat)")
    print(f"  BER sau khi Costas Loop khoa: {report.locked_ber:.6f} (Khong loi bit!)")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Vong phai khoa thanh cong 100%
    assert report.lock_acquired, "Costas Loop phai khoa pha thanh cong"

    # 2. Thoi gian xac lap phai duoi 300 ky hieu
    assert report.lock_settling_symbols < 300, (
        f"Thoi gian xac lap phai < 300 symbols, thuc te={report.lock_settling_symbols}"
    )

    # 3. Sai so uoc luong tan so Doppler phai duoi 1.5%
    assert report.freq_estimation_error_pct < 1.5, (
        f"Sai so uoc luong tan so phai < 1.5%, thuc te={report.freq_estimation_error_pct:.2f}%"
    )

    # 4. BER sau khi khoa phai bang 0.0 (hoac < 1e-4)
    assert report.locked_ber < 1e-4, f"BER sau khi khoa phai < 1e-4, thuc te={report.locked_ber}"

    # 5. BER truoc khi khoa phai rat cao (> 0.40) vi bi quay chom sao lien tuc
    assert report.unlocked_ber > 0.40, f"Truoc khi khoa BER phai > 0.40, thuc te={report.unlocked_ber}"

    print("\n>> [PASSED] TEST SUITE 100% SUCCESSFUL: COSTAS LOOP CARRIER RECOVERY VERIFIED!")


if __name__ == "__main__":
    main()
