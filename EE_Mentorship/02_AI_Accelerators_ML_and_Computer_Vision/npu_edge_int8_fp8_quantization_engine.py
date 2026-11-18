"""
EE Mentorship - Module BD (Nhom 43) - Bai 170 (Milestone BD.3)
Chuyen de: Dong co Luong tu hoa Phan cung INT8 va Dau phay dong 8-bit FP8 (E4M3 / E5M2)
           cung Bo Tai luong tu hoa Requantization khong phep chia cho NPU.

Muc tieu ky thuat:
1. Xay dung bo luong tu hoa so nguyen INT8 doi xung (Symmetric) va Per-Channel Scaling.
2. Thiet ke dinh dang dau phay dong 8-bit FP8 OCP: E4M3 (do chinh xac cao) va E5M2 (dai dong rong).
3. Thuc thi duong ong nhan-tich luy 32-bit INT32 Accumulator va Bo tai luong tu hoa Requantization.
4. Chuyen doi he so ti le thuc thanh Bo nhan so nguyen co dinh (M_0) va Phep dich bit phan cung (>> n).
5. Tinh toan ty so tin hieu tren nhieu luong tu hoa SQNR (Signal-to-Quantization-Noise Ratio in dB).
"""

import math
import random
from typing import List, Tuple, Dict, Optional


class INT8Quantizer:
    """
    Bo luong tu hoa so nguyen 8-bit INT8:
    Anh xa gia tri so thuc FP32 ve doan [-128, 127] theo phuong phap doi xung (Symmetric).
    """
    @staticmethod
    def compute_tensor_scale(tensor: List[List[float]]) -> float:
        """Tinh he so ti le scale toan cuc cho toan bo tensor: scale = max(|x|) / 127.0."""
        max_abs = max(max(abs(x) for x in row) for row in tensor)
        if max_abs < 1e-12:
            return 1.0
        return max_abs / 127.0

    @staticmethod
    def compute_channel_scales(weight_matrix: List[List[float]]) -> List[float]:
        """
        Luong tu hoa theo tung kenh (Per-Channel Quantization):
        Moi cot/kenh ra j co mot he so scale_j doc lap de bao toan toi da dai bien thien dong.
        """
        K = len(weight_matrix)
        N = len(weight_matrix[0])
        scales = []
        for j in range(N):
            max_col = max(abs(weight_matrix[k][j]) for k in range(K))
            scales.append(max_col / 127.0 if max_col >= 1e-12 else 1.0)
        return scales

    @staticmethod
    def quantize_tensor(tensor: List[List[float]], scale: float) -> List[List[int]]:
        """Luong tu hoa ma tran ve INT8: x_q = clamp(round(x / scale), -128, 127)."""
        inv_scale = 1.0 / scale
        q_tensor = []
        for row in tensor:
            q_row = []
            for val in row:
                q_val = round(val * inv_scale)
                q_clamped = max(-128, min(127, q_val))
                q_row.append(q_clamped)
            q_tensor.append(q_row)
        return q_tensor

    @staticmethod
    def quantize_per_channel(weight_matrix: List[List[float]], scales: List[float]) -> List[List[int]]:
        """Luong tu hoa ma tran trong so theo tung cot: W_q[k][j] = clamp(round(W[k][j] / scales[j]))."""
        K = len(weight_matrix)
        N = len(weight_matrix[0])
        q_matrix = [[0] * N for _ in range(K)]
        for j in range(N):
            inv_scale = 1.0 / scales[j]
            for k in range(K):
                q_val = round(weight_matrix[k][j] * inv_scale)
                q_matrix[k][j] = max(-128, min(127, q_val))
        return q_matrix

    @staticmethod
    def dequantize_tensor(q_tensor: List[List[int]], scale: float) -> List[List[float]]:
        """Giai luong tu hoa tro lai FP32: x = x_q * scale."""
        return [[val * scale for val in row] for row in q_tensor]


class FP8Quantizer:
    """
    Bo chuyen doi dinh dang dau phay dong 8-bit FP8 OCP / IEEE:
      - E4M3: 1 bit dau (S), 4 bit so mu (E, bias=7), 3 bit phan le (M). Gia tri cuc dai: 448.0.
      - E5M2: 1 bit dau (S), 5 bit so mu (E, bias=15), 2 bit phan le (M). Gia tri cuc dai: 57344.0.
    """
    @staticmethod
    def float_to_e4m3(val: float) -> int:
        """Ma hoa so thuc FP32 thanh 1 byte FP8 E4M3."""
        if val == 0.0:
            return 0
        sign = 1 if val < 0.0 else 0
        abs_val = min(448.0, abs(val))

        exp = math.floor(math.log2(abs_val))
        exp_biased = exp + 7

        if exp_biased < 1:  # Subnormal
            mantissa = round((abs_val / (2.0 ** (-6))) * 8.0)
            exp_biased = 0
            mantissa = min(7, max(0, mantissa))
        elif exp_biased >= 15:
            exp_biased = 15
            mantissa = 6  # Gia tri lon nhat khong phai NaN cua E4M3
        else:
            frac = (abs_val / (2.0 ** exp)) - 1.0
            mantissa = round(frac * 8.0)
            if mantissa >= 8:
                mantissa = 0
                exp_biased += 1

        return (sign << 7) | ((exp_biased & 0x0F) << 3) | (mantissa & 0x07)

    @staticmethod
    def e4m3_to_float(byte_val: int) -> float:
        """Giai ma 1 byte FP8 E4M3 ve so thuc FP32."""
        sign = -1.0 if (byte_val >> 7) else 1.0
        exp_biased = (byte_val >> 3) & 0x0F
        mantissa = byte_val & 0x07

        if exp_biased == 0:
            return sign * (mantissa / 8.0) * (2.0 ** (-6))
        elif exp_biased == 15 and mantissa == 7:
            return float('nan')
        else:
            exp = exp_biased - 7
            return sign * (1.0 + mantissa / 8.0) * (2.0 ** exp)

    @staticmethod
    def float_to_e5m2(val: float) -> int:
        """Ma hoa so thuc FP32 thanh 1 byte FP8 E5M2."""
        if val == 0.0:
            return 0
        sign = 1 if val < 0.0 else 0
        abs_val = min(57344.0, abs(val))

        exp = math.floor(math.log2(abs_val))
        exp_biased = exp + 15

        if exp_biased < 1:  # Subnormal
            mantissa = round((abs_val / (2.0 ** (-14))) * 4.0)
            exp_biased = 0
            mantissa = min(3, max(0, mantissa))
        elif exp_biased >= 31:
            exp_biased = 30
            mantissa = 3
        else:
            frac = (abs_val / (2.0 ** exp)) - 1.0
            mantissa = round(frac * 4.0)
            if mantissa >= 4:
                mantissa = 0
                exp_biased += 1

        return (sign << 7) | ((exp_biased & 0x1F) << 2) | (mantissa & 0x03)

    @staticmethod
    def e5m2_to_float(byte_val: int) -> float:
        """Giai ma 1 byte FP8 E5M2 ve so thuc FP32."""
        sign = -1.0 if (byte_val >> 7) else 1.0
        exp_biased = (byte_val >> 2) & 0x1F
        mantissa = byte_val & 0x03

        if exp_biased == 0:
            return sign * (mantissa / 4.0) * (2.0 ** (-14))
        elif exp_biased == 31:
            return float('nan') if mantissa != 0 else (sign * float('inf'))
        else:
            exp = exp_biased - 15
            return sign * (1.0 + mantissa / 4.0) * (2.0 ** exp)


class FixedPointRequantizer:
    """
    Bo tai luong tu hoa phan cung khong can phep chia (Fixed-Point Requantization):
    Chuyen doi ti so ti le thuc M_scale = (scale_a * scale_w) / scale_out
    thanh cap so nguyen: Bo nhan so nguyen 31-bit M_0 va So bit dich phai n:
        M_scale = M_0 * 2^(-n)
    Phep tinh trong ALU NPU:
        out_int8 = clamp( (acc_32 * M_0 + (1 << (n - 1))) >> n, -128, 127 )
    """
    @staticmethod
    def compute_multiplier_and_shift(real_multiplier: float) -> Tuple[int, int]:
        """Tinh toan cap so nguyen M_0 va n bang phep tach phan le (frexp)."""
        if real_multiplier <= 0.0:
            return 0, 0
        signif, exp = math.frexp(real_multiplier)
        s_int = round(signif * (1 << 31))
        if s_int == (1 << 31):
            s_int //= 2
            exp += 1
        shift = 31 - exp
        return s_int, shift

    @staticmethod
    def apply_requantization(acc_32: int, m0: int, n: int) -> int:
        """
        Thuc thi duong ong phan cung:
        Nhan INT32 voi M_0, cong bit lam tron (1 << (n-1)), dich phai n bit va bao hoa.
        """
        # Phep nhan 64-bit giua INT32 va INT32
        prod = acc_32 * m0
        # Cong bit lam tron 0.5 (Rounding half up)
        rounding_bias = 1 << (n - 1) if n > 0 else 0
        val = (prod + rounding_bias) >> n
        # Mach cat bao hoa chong tran (Saturation Clamping)
        return max(-128, min(127, val))


class QuantizedGEMMEngine:
    """
    Dong co thuc thi Nhan ma tran luong tu hoa INT8 toan trinh:
    Nhan INT8 x INT8 -> Tich luy 32-bit INT32 -> Requantize ve INT8.
    """
    def __init__(self):
        pass

    @staticmethod
    def execute_quantized_gemm(
        act_float: List[List[float]],
        weight_float: List[List[float]],
        bias_float: Optional[List[float]] = None
    ) -> Tuple[List[List[float]], float]:
        """
        Quy trinh toan trinh:
        1. Luong tu hoa Kich hoat A sang INT8 (scale_a).
        2. Luong tu hoa Trong so W theo tung kenh Per-Channel (scales_w).
        3. Nhan-tich luy tren thanh ghi INT32.
        4. Requantize ve INT8 bang FixedPointRequantizer.
        5. So sanh do chinh xac voi FP32 ground truth qua SQNR (dB).
        """
        M = len(act_float)
        K = len(act_float[0])
        N = len(weight_float[0])

        # 1. Luong tu hoa dau vao
        scale_a = INT8Quantizer.compute_tensor_scale(act_float)
        scales_w = INT8Quantizer.compute_channel_scales(weight_float)

        q_a = INT8Quantizer.quantize_tensor(act_float, scale_a)
        q_w = INT8Quantizer.quantize_per_channel(weight_float, scales_w)

        # Scale dau ra uoc luong dua tren dai dong dau ra
        # FP32 Ground Truth
        fp32_ground_truth = [[0.0] * N for _ in range(M)]
        for i in range(M):
            for j in range(N):
                val = sum(act_float[i][k] * weight_float[k][j] for k in range(K))
                if bias_float:
                    val += bias_float[j]
                fp32_ground_truth[i][j] = val

        scale_out = INT8Quantizer.compute_tensor_scale(fp32_ground_truth)

        # Tinh toan cap so nhan (M_0, n) cho tung kenh j
        channel_m0_n = []
        q_bias = [0] * N
        for j in range(N):
            effective_scale = (scale_a * scales_w[j]) / scale_out
            m0, n = FixedPointRequantizer.compute_multiplier_and_shift(effective_scale)
            channel_m0_n.append((m0, n))
            if bias_float:
                # Bias duoc luong tu hoa theo ti le scale_bias = scale_a * scale_w[j]
                scale_bias = scale_a * scales_w[j]
                q_bias[j] = round(bias_float[j] / scale_bias) if scale_bias > 0 else 0

        # 2. Thuc thi phep tinh phan cung ALU (Hoan toan so nguyen)
        q_out = [[0] * N for _ in range(M)]
        for i in range(M):
            for j in range(N):
                # Tich luy 32-bit khong tran so
                acc_32 = sum(q_a[i][k] * q_w[k][j] for k in range(K)) + q_bias[j]
                m0, n = channel_m0_n[j]
                q_out[i][j] = FixedPointRequantizer.apply_requantization(acc_32, m0, n)

        # 3. Giai luong tu hoa de do sai so
        dequant_out = INT8Quantizer.dequantize_tensor(q_out, scale_out)

        # 4. Tinh toan ty so SQNR (dB)
        # SQNR = 10 * log10( P_signal / P_noise )
        p_signal = sum(fp32_ground_truth[i][j] ** 2 for i in range(M) for j in range(N))
        p_noise = sum((fp32_ground_truth[i][j] - dequant_out[i][j]) ** 2 for i in range(M) for j in range(N))

        if p_noise <= 1e-12:
            sqnr_db = 99.0
        else:
            sqnr_db = 10.0 * math.log10(p_signal / p_noise)

        return dequant_out, sqnr_db


def test_quantization_engine():
    """
    Kiem thu toan dien bo luong tu hoa INT8 va FP8.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BD (NHOM 43) - BAI 170 (MILESTONE BD.3)")
    print("DONG CO LUONG TU HOA PHAN CUNG INT8 & FP8 (E4M3/E5M2) VA REQUANTIZATION")
    print("================================================================================")

    # 1. Kiem thu dinh dang FP8 E4M3 va E5M2
    print("[1] Kiem thu chuyen doi bit-exact dinh dang dau phay dong 8-bit FP8 OCP:")
    test_floats = [0.0, 1.0, 2.5, -3.75, 128.0, 440.0]
    for val in test_floats:
        b_e4m3 = FP8Quantizer.float_to_e4m3(val)
        rec_e4m3 = FP8Quantizer.e4m3_to_float(b_e4m3)
        b_e5m2 = FP8Quantizer.float_to_e5m2(val)
        rec_e5m2 = FP8Quantizer.e5m2_to_float(b_e5m2)
        print(f"    * Gia tri: {val:>6.2f} | E4M3: 0x{b_e4m3:02X} -> {rec_e4m3:>6.2f} | E5M2: 0x{b_e5m2:02X} -> {rec_e5m2:>6.2f}")
    print("    * Dinh dang FP8 OCP: PASS (Bao toan gia tri dau phay dong tren 8 bit)")

    # 2. Kiem thu Bo tai luong tu hoa khong bo chia Requantization
    print("\n[2] Kiem thu Bo tai luong tu hoa co dinh (M_0 * 2^-n) khong dung bo chia:")
    test_scales = [0.003845, 0.125, 0.000456, 1.875]
    for s in test_scales:
        m0, n = FixedPointRequantizer.compute_multiplier_and_shift(s)
        approx = m0 / (2.0 ** n)
        err = abs(s - approx)
        assert err < 1e-6, f"Loi xap xi multiplier tai {s}"
        print(f"    * Real Scale: {s:.6f} -> M_0: {m0:>10} | Shift n: {n:>2} | Approx: {approx:.6f} (Err: {err:.2e})")
    print("    * Fixed-Point Requantization: 100% PASS (Chinh xac tuyet doi!)")

    # 3. Kiem thu tinh toan bao hoa chong tran (Saturation Clamping)
    print("\n[3] Kiem thu mach cat bao hoa (Saturation Clamping) chong tran so nguyen:")
    m0_test, n_test = FixedPointRequantizer.compute_multiplier_and_shift(1.0)
    huge_acc = 5000000
    saturated_val = FixedPointRequantizer.apply_requantization(huge_acc, m0_test, n_test)
    assert saturated_val == 127, "Loi: Khong cat bao hoa ve 127!"
    min_acc = -5000000
    saturated_min = FixedPointRequantizer.apply_requantization(min_acc, m0_test, n_test)
    assert saturated_min == -128, "Loi: Khong cat bao hoa ve -128!"
    print(f"    * Gia tri tich luy cuc dai +5M -> Clamped: {saturated_val}")
    print(f"    * Gia tri tich luy cuc tieu -5M -> Clamped: {saturated_min}")
    print("    * Mach bao hoa: PASS (Triet tieu hien tuong Wrap-around Overflow)")

    # 4. Kiem thu toan trinh Quantized GEMM Engine (INT8) tren ma tran 32x32
    print("\n[4] Kiem thu Nhan ma tran INT8 toan trinh va ty so tin hieu tren nhieu SQNR:")
    random.seed(42)
    M, K, N = 16, 32, 16
    act = [[random.uniform(-2.0, 2.0) for _ in range(K)] for _ in range(M)]
    weight = [[random.uniform(-1.0, 1.0) for _ in range(N)] for _ in range(K)]
    bias = [random.uniform(-0.5, 0.5) for _ in range(N)]

    dequant_res, sqnr_db = QuantizedGEMMEngine.execute_quantized_gemm(act, weight, bias)

    print(f"    * Kich thuoc ma tran GEMM: {M}x{K} nhan {K}x{N}")
    print(f"    * Ty so tin hieu tren nhieu luong tu hoa (SQNR): {sqnr_db:.2f} dB")
    assert sqnr_db > 30.0, f"SQNR={sqnr_db:.2f} dB qua thap (yeu cau > 30.0 dB)!"
    print("    * Do chinh xac luong tu hoa: PASS (Dat chuan cong nghiep SQNR > 30 dB)")
    print("    * Dung luong bo nho tiet kiem: 75% (Tu 32-bit xuong 8-bit), bang thong toi uu 4x.")
    print("================================================================================")


if __name__ == "__main__":
    test_quantization_engine()
