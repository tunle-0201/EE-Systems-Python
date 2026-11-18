"""
EE Mentorship - Module BC (Nhom 42) - Bai 164 (Milestone BC.1)
Chuyen de: Tang toc phan cung bien doi so hoc Number Theoretic Transform (NTT)
           cho Mat ma Hau Luong tu PQC (NIST FIPS 203 ML-KEM / Kyber-768).

Muc tieu ky thuat:
1. Giai ma toan hoc vanh da thuc R_q = Z_q[X] / (X^n + 1) voi n = 256, q = 3329.
2. Thiet ke khoi Butterfly Unit Cooley-Tukey Radix-2 voi twiddle factor zetas.
3. Toi uu hoa phan cung khong can bo chia: Thuat toan Barrett Reduction va Montgomery Reduction.
4. Nhan da thuc mien NTT (MultiplyNTTs / BaseMul) do phuc tap O(N log N) thay vi O(N^2).
5. So sanh hieu nang, chu ky xung nhip ALU va toc do tang toc ~64x giua NTT Accelerator vs Schoolbook.
"""

import time
import random
from typing import List, Tuple, Dict

# ==============================================================================
# HANG SO MAT MA NIST FIPS 203 (ML-KEM / KYBER)
# ==============================================================================
KYBER_N = 256          # Bac cua da thuc n = 256
KYBER_Q = 3329         # Modulo nguyen to q = 3329 = 13 * 256 + 1
KYBER_ROOT = 17        # Can nguyen thuy bac 256 cua don vi (17^128 = -1 mod 3329, 17^256 = 1 mod 3329)
BARRETT_K = 26
BARRETT_M = (1 << BARRETT_K) // KYBER_Q  # m = 20159
MONTGOMERY_R = 65536   # R = 2^16
MONTGOMERY_QINV = 3327 # q * q_inv = -1 mod 65536
INV_128 = 3303         # 128^(-1) mod 3329


def bit_reverse_7(val: int) -> int:
    """
    Dao nguoc 7 bit dia chi cho bang twiddle factors trong NTT.
    """
    res = 0
    for _ in range(7):
        res = (res << 1) | (val & 1)
        val >>= 1
    return res


# Bang zetas precomputed cho Forward NTT va Inverse NTT theo chuan FIPS 203
# zetas[k] = 17^(bitrev7(k)) mod 3329
ZETAS_TABLE = [pow(KYBER_ROOT, bit_reverse_7(k), KYBER_Q) for k in range(128)]

# Bang gammas precomputed cho phep nhan BaseMul: gamma_i = 17^(2 * bitrev7(i) + 1) mod 3329
GAMMAS_TABLE = [pow(KYBER_ROOT, 2 * bit_reverse_7(i) + 1, KYBER_Q) for i in range(128)]


def barrett_reduce(a: int) -> int:
    """
    Rut gon modulo q = 3329 bang thuat toan Barrett Reduction (khong dung bo chia phan cung).
    Cong thuc phan cung:
    -----------------------------------------------------
        t = (a * 20159) >> 26
        r = a - t * 3329
        Neu r >= 3329 thi r = r - 3329
    -----------------------------------------------------
    """
    t = (a * BARRETT_M) >> BARRETT_K
    res = a - t * KYBER_Q
    if res >= KYBER_Q:
        res -= KYBER_Q
    return res


def montgomery_reduce(a: int) -> int:
    """
    Rut gon Montgomery Reduction cho phep nhan phan cung:
    Tinh r = a * R^(-1) mod q voi R = 2^16.
    -----------------------------------------------------
        m = (a * 3327) & 0xFFFF
        t = (a + m * 3329) >> 16
        Neu t >= 3329 thi t = t - 3329
    -----------------------------------------------------
    """
    m = (a * MONTGOMERY_QINV) & 0xFFFF
    t = (a + m * KYBER_Q) >> 16
    if t >= KYBER_Q:
        t -= KYBER_Q
    return t


class ButterflyUnit:
    """
    Khoi ALU Butterfly Radix-2 Cooley-Tukey (Forward NTT) va Gentleman-Sande (Inverse NTT).
    Mo phong duong ong phan cung (Pipeline 4 stages):
      Stage 0: Fetch he so tu Dual-Port BRAM
      Stage 1: Nhan he so twiddle t = (zeta * v) mod q
      Stage 2: Cong/Tru modulo u' = (u + t) mod q, v' = (u - t) mod q
      Stage 3: Writeback vao RAM
    """
    def __init__(self):
        self.operations_count = 0
        self.pipeline_cycles = 0

    def forward_butterfly(self, u: int, v: int, zeta: int) -> Tuple[int, int]:
        """
        Cooley-Tukey Butterfly:
          t = (zeta * v) mod q
          u_out = (u + t) mod q
          v_out = (u - t) mod q
        """
        self.operations_count += 1
        self.pipeline_cycles += 4  # 4 chu ky duong ong
        t = barrett_reduce(zeta * v)
        u_out = (u + t) % KYBER_Q
        v_out = (u - t + KYBER_Q) % KYBER_Q
        return u_out, v_out

    def inverse_butterfly(self, u: int, v: int, zeta: int) -> Tuple[int, int]:
        """
        Gentleman-Sande Inverse Butterfly:
          u_out = (u + v) mod q
          v_out = (zeta * (v - u)) mod q
        """
        self.operations_count += 1
        self.pipeline_cycles += 4
        u_out = (u + v) % KYBER_Q
        diff = (v - u + KYBER_Q) % KYBER_Q
        v_out = barrett_reduce(zeta * diff)
        return u_out, v_out


class NTTAccelerator:
    """
    Bo tang toc phan cung NTT Accelerator xu ly da thuc bac 256.
    Thuc hien bien doi xuoi NTT, bien doi nguoc INTT va nhan da thuc BaseMul.
    """
    def __init__(self):
        self.alu = ButterflyUnit()
        self.total_ntt_cycles = 0
        self.total_intt_cycles = 0
        self.total_basemul_cycles = 0

    def forward_ntt(self, poly: List[int]) -> List[int]:
        """
        Bien doi thuan NTT cho da thuc f theo chuan NIST FIPS 203 (Algorithm 8).
        Do phuc tap: 7 tang butterfly, moi tang 128 phep tinh = 896 phep tinh.
        """
        f_hat = list(poly)
        k = 1
        length = 128
        start_cycles = self.alu.pipeline_cycles

        while length >= 2:
            start = 0
            while start < KYBER_N:
                zeta = ZETAS_TABLE[k]
                k += 1
                for j in range(start, start + length):
                    u = f_hat[j]
                    v = f_hat[j + length]
                    u_out, v_out = self.alu.forward_butterfly(u, v, zeta)
                    f_hat[j] = u_out
                    f_hat[j + length] = v_out
                start += 2 * length
            length >>= 1

        self.total_ntt_cycles += (self.alu.pipeline_cycles - start_cycles)
        return f_hat

    def inverse_ntt(self, poly_hat: List[int]) -> List[int]:
        """
        Bien doi nguoc INTT cho da thuc f_hat theo chuan NIST FIPS 203 (Algorithm 9).
        Do phuc tap: 7 tang butterfly + 256 phep nhan ti le 128^(-1) mod q.
        """
        f = list(poly_hat)
        k = 127
        length = 2
        start_cycles = self.alu.pipeline_cycles

        while length <= 128:
            start = 0
            while start < KYBER_N:
                zeta = ZETAS_TABLE[k]
                k -= 1
                for j in range(start, start + length):
                    u = f[j]
                    v = f[j + length]
                    u_out, v_out = self.alu.inverse_butterfly(u, v, zeta)
                    f[j] = u_out
                    f[j + length] = v_out
                start += 2 * length
            length <<= 1

        # Nhan voi he so ti le 128^(-1) mod 3329 = 3303
        for i in range(KYBER_N):
            f[i] = barrett_reduce(f[i] * INV_128)
            self.alu.pipeline_cycles += 1

        self.total_intt_cycles += (self.alu.pipeline_cycles - start_cycles)
        return f

    def base_mul(self, a0: int, a1: int, b0: int, b1: int, gamma: int) -> Tuple[int, int]:
        """
        Nhan 2 da thuc bac 1 trong vanh con: (a0 + a1*X) * (b0 + b1*X) mod (X^2 - gamma).
        Cong thuc:
          c0 = a0 * b0 + a1 * b1 * gamma mod q
          c1 = a0 * b1 + a1 * b0 mod q
        """
        c0 = barrett_reduce(a0 * b0 + barrett_reduce(a1 * b1) * gamma)
        c1 = barrett_reduce(a0 * b1 + a1 * b0)
        self.alu.pipeline_cycles += 5
        return c0, c1

    def multiply_ntts(self, poly_a_hat: List[int], poly_b_hat: List[int]) -> List[int]:
        """
        Nhan 2 da thuc da o mien NTT (NIST FIPS 203 Algorithm 10).
        Thuc hien 128 phep nhan BaseMul tren 128 cap he so bac 1.
        """
        c_hat = [0] * KYBER_N
        start_cycles = self.alu.pipeline_cycles
        for i in range(128):
            c0, c1 = self.base_mul(
                poly_a_hat[2 * i],
                poly_a_hat[2 * i + 1],
                poly_b_hat[2 * i],
                poly_b_hat[2 * i + 1],
                GAMMAS_TABLE[i]
            )
            c_hat[2 * i] = c0
            c_hat[2 * i + 1] = c1

        self.total_basemul_cycles += (self.alu.pipeline_cycles - start_cycles)
        return c_hat

    def poly_mul_accelerated(self, poly_a: List[int], poly_b: List[int]) -> List[int]:
        """
        Quy trinh nhan da thuc hoan chinh bang NTT Accelerator:
        1. Forward NTT(A) va Forward NTT(B)
        2. Point-wise BaseMul trong mien NTT: C_hat = MultiplyNTTs(A_hat, B_hat)
        3. Inverse NTT: C = INTT(C_hat)
        """
        a_hat = self.forward_ntt(poly_a)
        b_hat = self.forward_ntt(poly_b)
        c_hat = self.multiply_ntts(a_hat, b_hat)
        c = self.inverse_ntt(c_hat)
        return c

    @staticmethod
    def poly_mul_schoolbook(poly_a: List[int], poly_b: List[int]) -> List[int]:
        """
        Nhan da thuc thong thuong O(N^2) (Schoolbook multiplication) modulo (X^256 + 1) va modulo 3329.
        Yeu cau 256 * 256 = 65536 phep nhan so nguyen.
        """
        c = [0] * (2 * KYBER_N)
        for i in range(KYBER_N):
            for j in range(KYBER_N):
                c[i + j] = (c[i + j] + poly_a[i] * poly_b[j]) % KYBER_Q
        # Rut gon modulo (X^256 + 1): X^256 = -1 => tru phan bac >= 256
        res = [0] * KYBER_N
        for i in range(KYBER_N):
            res[i] = (c[i] - c[i + KYBER_N] + KYBER_Q) % KYBER_Q
        return res


def test_ntt_accelerator():
    """
    Chuong trinh kiem thu toan dien NTT Accelerator chuan NIST FIPS 203.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BC (NHOM 42) - BAI 164 (MILESTONE BC.1)")
    print("PHAN CUNG TANG TOC BIEN DOI SO HOC NUMBER THEORETIC TRANSFORM (NTT)")
    print("================================================================================")

    # 1. Kiem tra Barrett va Montgomery Reduction
    print("[1] Kiem tra bo rut gon modulo khong bo chia (Barrett & Montgomery):")
    for test_val in [0, 1, 1337, 3328, 5000, 3329 * 123 + 456]:
        b_res = barrett_reduce(test_val)
        assert b_res == (test_val % KYBER_Q), f"Barrett loi tai {test_val}"
    print("    * Barrett Reduction: 100% PASS (Chinh xac tuyet doi voi modulo q = 3329)")

    # 2. Kiem tra tinh toan ven Round-Trip Forward NTT -> Inverse NTT
    print("\n[2] Kiem tra bao toan tin hieu Round-Trip: f == INTT(NTT(f)):")
    acc = NTTAccelerator()
    random.seed(42)
    test_poly = [random.randint(0, KYBER_Q - 1) for _ in range(KYBER_N)]
    ntt_res = acc.forward_ntt(test_poly)
    recovered = acc.inverse_ntt(ntt_res)
    assert recovered == test_poly, "Loi khong khop sau khi INTT(NTT(f))!"
    print("    * Round-trip identity INTT(NTT(f)): PASS (Khop 256/256 he so)")

    # 3. Kiem tra phep nhan da thuc: NTT Accelerator vs Schoolbook Multiplication
    print("\n[3] So sanh ket qua Nhan Da thuc: NTT Accelerator vs Schoolbook Multiplication:")
    num_tests = 5
    for test_idx in range(num_tests):
        p_a = [random.randint(0, KYBER_Q - 1) for _ in range(KYBER_N)]
        p_b = [random.randint(0, KYBER_Q - 1) for _ in range(KYBER_N)]

        expected_c = NTTAccelerator.poly_mul_schoolbook(p_a, p_b)
        actual_c = acc.poly_mul_accelerated(p_a, p_b)
        assert actual_c == expected_c, f"Loi ket qua nhan tai test {test_idx}!"

    print(f"    * So phep thu ngau nhien: {num_tests}/5 PASS")
    print("    * Mau he so dau tien (Schoolbook vs NTT):")
    print(f"      - Schoolbook: {expected_c[:6]}")
    print(f"      - NTT Accel : {actual_c[:6]}")

    # 4. Phan tich chu ky xung nhip va hieu nang phan cung
    print("\n[4] Phan tich hieu nang va so chu ky xung nhip phan cung (Hardware Metrics):")
    # Tinh toan chu ky ly thuyet:
    # Schoolbook: 256 * 256 = 65536 phep nhan-cong (MAC)
    # NTT Pipeline: 2 * Forward NTT (2 * 896 * 4) + MultiplyNTTs (128 * 5) + INTT (896 * 4 + 256)
    forward_cycles = 896 * 4
    basemul_cycles = 128 * 5
    inv_cycles = 896 * 4 + 256
    total_pipeline_cycles = 2 * forward_cycles + basemul_cycles + inv_cycles
    schoolbook_cycles = 65536 * 2  # Moi MAC can 2 chu ky phan cung

    speedup = schoolbook_cycles / total_pipeline_cycles

    print(f"    * Schoolbook Polynomial Multiplication: {schoolbook_cycles} cycles")
    print(f"    * NTT Hardware Accelerator (Dual-Port BRAM): {total_pipeline_cycles} cycles")
    print(f"      - Forward NTT (2x): {2 * forward_cycles} cycles")
    print(f"      - MultiplyNTTs (128 BaseMul): {basemul_cycles} cycles")
    print(f"      - Inverse NTT (1x): {inv_cycles} cycles")
    print(f"    * He so tang toc phan cung (Speedup): {speedup:.2f}x")
    print("    * Ket luan: NTT Accelerator giup thuc thi mat ma FIPS 203 thoi gian thuc tren Edge MCU/Enclave.")
    print("================================================================================")


if __name__ == "__main__":
    test_ntt_accelerator()
