"""
EE Mentorship - Module BD (Nhom 43) - Bai 168 (Milestone BD.1)
Chuyen de: Mang luoi Mang Tam thu 2D Systolic Array Processing Elements (PE)
           cho Bo tang toc Tri tue Nhan tao NPU (Apple Neural Engine / Tesla FSD).

Muc tieu ky thuat:
1. Xay dung kien truc phan cung mang luoi tam thu 2D Systolic Array Processing Elements (M x N).
2. Thiet ke khoi can le dong thoi Wavefront Skewing cho ma tran kich hoat (A) va trong so (B).
3. Mo phong chu ky xung nhip Cycle-Accurate: Nhan-cong MAC khong tre va truyen du lieu ngang/doc.
4. Triet tieu bot chu ky (Zero-Bubble Pipelining) khi nap lien tuc cac khoi ma tran Tiling.
5. Do luong cac chi so phan cung: So chu ky thuc thi, hieu suat tan dung PE (PE Utilization %), va Throughput MACs/cycle.
"""

import time
from typing import List, Tuple, Dict, Optional


class ProcessingElement:
    """
    Khoi xu ly co ban Processing Element (PE) trong mang tam thu 2D.
    Moi PE gom:
      - Thanh ghi truyen ngang reg_a (Activation tu West -> East)
      - Thanh ghi truyen doc reg_b (Weight tu North -> South)
      - Bo nhan va tich luy Accumulator 32-bit (MAC unit)
    """
    def __init__(self, row_idx: int, col_idx: int):
        self.row = row_idx
        self.col = col_idx
        self.reg_a = 0
        self.reg_b = 0
        self.accumulator = 0
        self.active_cycles = 0

    def reset_accumulator(self):
        """Xoa thanh ghi tich luy cho phep tinh moi."""
        self.accumulator = 0

    def compute_cycle(self, in_a: int, in_b: int) -> Tuple[int, int]:
        """
        Thuc thi 1 chu ky xung nhip:
        Tinh toan MAC: acc = acc + in_a * in_b.
        Tra ve gia tri (reg_a, reg_b) de truyen sang cac PE lan can tai suon xung tiep theo.
        """
        if in_a != 0 and in_b != 0:
            self.active_cycles += 1
        self.accumulator += in_a * in_b
        return in_a, in_b


class SystolicArray2DMesh:
    """
    Mang luoi tam thu 2D kich thuoc M x N Processing Elements.
    Dong du lieu luu chuyen theo nhip tim (Systolic Wavefront):
      - Dong ma tran A di tu bien Trai (West) sang Phai (East).
      - Dong ma tran B di tu bien Tren (North) sang Duoi (South).
      - Moi hang r cua A duoc tre r chu ky (Skewing).
      - Moi cot c cua B duoc tre c chu ky (Skewing).
    """
    def __init__(self, rows: int = 8, cols: int = 8):
        self.rows = rows
        self.cols = cols
        self.grid = [[ProcessingElement(r, c) for c in range(cols)] for r in range(rows)]
        self.total_clock_cycles = 0

    def reset_array(self):
        """Reset toan bo thanh ghi va bo tich luy trong mang PE."""
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c].reset_accumulator()
                self.grid[r][c].reg_a = 0
                self.grid[r][c].reg_b = 0
                self.grid[r][c].active_cycles = 0
        self.total_clock_cycles = 0

    def execute_gemm(self, matrix_a: List[List[int]], matrix_b: List[List[int]]) -> Tuple[List[List[int]], Dict[str, float]]:
        """
        Thuc thi phep nhan ma tran GEMM: C = A * B tren mang tam thu 2D.
        Kich thuoc A: M x K, Kich thuoc B: K x N.
        Yeu cau: M <= rows, N <= cols.
        """
        M = len(matrix_a)
        K = len(matrix_a[0])
        N = len(matrix_b[0])

        assert M <= self.rows, f"Kich thuoc M={M} vuot qua so hang cua PE array ({self.rows})"
        assert N <= self.cols, f"Kich thuoc N={N} vuot qua so cot cua PE array ({self.cols})"
        assert len(matrix_b) == K, f"Kich thuoc K khong khop: A co K={K}, B co hang={len(matrix_b)}"

        self.reset_array()

        # Tong so chu ky de toan bo song du lieu Wavefront quet qua mang
        # Chu ky = (M - 1) + (N - 1) + K
        total_steps = (M - 1) + (N - 1) + K + 1
        
        # Bang thanh ghi luu trang thai truyen giua cac PE
        reg_a = [[0] * self.cols for _ in range(self.rows)]
        reg_b = [[0] * self.cols for _ in range(self.rows)]

        for t in range(total_steps):
            self.total_clock_cycles += 1

            # 1. Tinh toan tin hieu dau vao cho moi PE tai chu ky t
            in_a = [[0] * self.cols for _ in range(self.rows)]
            in_b = [[0] * self.cols for _ in range(self.rows)]

            for r in range(M):
                for c in range(N):
                    # Kiem tra Wavefront Skewing bien Trai (West boundary):
                    # Hang r cua ma tran A duoc dua vao tu chu ky t = r
                    if c == 0:
                        k_idx_a = t - r
                        in_a[r][0] = matrix_a[r][k_idx_a] if (0 <= k_idx_a < K) else 0
                    else:
                        in_a[r][c] = reg_a[r][c - 1]

                    # Kiem tra Wavefront Skewing bien Tren (North boundary):
                    # Cot c cua ma tran B duoc dua vao tu chu ky t = c
                    if r == 0:
                        k_idx_b = t - c
                        in_b[0][c] = matrix_b[k_idx_b][c] if (0 <= k_idx_b < K) else 0
                    else:
                        in_b[r][c] = reg_b[r - 1][c]

                    # Thuc thi tinh toan MAC trong PE
                    self.grid[r][c].compute_cycle(in_a[r][c], in_b[r][c])

            # 2. Chot thanh ghi tai suon duong xung nhip (Flip-Flop latch)
            for r in range(M):
                for c in range(N):
                    reg_a[r][c] = in_a[r][c]
                    reg_b[r][c] = in_b[r][c]

        # Thu hoach ket qua tu cac thanh ghi Accumulator cua PE
        result_c = [[self.grid[r][c].accumulator for c in range(N)] for r in range(M)]

        # Tinh toan cac chi so hieu nang phan cung (Hardware Performance Metrics)
        total_mac_ops = M * N * K
        theoretical_cycles = total_steps
        pe_count = M * N
        total_pe_cycles = total_steps * pe_count
        active_pe_cycles = sum(self.grid[r][c].active_cycles for r in range(M) for c in range(N))
        pe_utilization = (active_pe_cycles / total_pe_cycles) * 100.0 if total_pe_cycles > 0 else 0.0
        macs_per_cycle = total_mac_ops / theoretical_cycles if theoretical_cycles > 0 else 0.0

        metrics = {
            "total_cycles": float(theoretical_cycles),
            "total_mac_ops": float(total_mac_ops),
            "pe_utilization_percent": pe_utilization,
            "macs_per_cycle": macs_per_cycle,
            "wavefront_skew_latency": float((M - 1) + (N - 1))
        }

        return result_c, metrics

    def execute_tiled_gemm(self, big_a: List[List[int]], big_b: List[List[int]]) -> Tuple[List[List[int]], Dict[str, float]]:
        """
        Thuc thi phep nhan ma tran lon bang ky thuat phan manh khoi Tiling:
        Chia ma tran thanh cac khoi kich thuoc (rows x cols) va nap vao Systolic Array.
        """
        M = len(big_a)
        K = len(big_a[0])
        N = len(big_b[0])

        tile_m = self.rows
        tile_n = self.cols
        tile_k = min(self.rows, self.cols)

        # Ma tran ket qua C kich thuoc M x N
        c_matrix = [[0] * N for _ in range(M)]
        total_tiled_cycles = 0
        total_macs = M * N * K

        # Quet qua tung khoi tile
        for i_tile in range(0, M, tile_m):
            i_end = min(i_tile + tile_m, M)
            for j_tile in range(0, N, tile_n):
                j_end = min(j_tile + tile_n, N)
                for k_tile in range(0, K, tile_k):
                    k_end = min(k_tile + tile_k, K)

                    # Trich xuat ma tran con sub_A va sub_B
                    sub_a = [[big_a[r][k] for k in range(k_tile, k_end)] for r in range(i_tile, i_end)]
                    sub_b = [[big_b[k][c] for c in range(j_tile, j_end)] for k in range(k_tile, k_end)]

                    sub_c, sub_metrics = self.execute_gemm(sub_a, sub_b)
                    total_tiled_cycles += int(sub_metrics["total_cycles"])

                    # Tich luy vao ma tran tong C
                    for r_idx in range(len(sub_c)):
                        for c_idx in range(len(sub_c[0])):
                            c_matrix[i_tile + r_idx][j_tile + c_idx] += sub_c[r_idx][c_idx]

        metrics = {
            "total_cycles": float(total_tiled_cycles),
            "total_mac_ops": float(total_macs),
            "throughput_macs_cycle": float(total_macs / total_tiled_cycles) if total_tiled_cycles > 0 else 0.0
        }
        return c_matrix, metrics


def test_systolic_array_2d():
    """
    Kiem thu toan dien mang luoi tam thu 2D Systolic Array.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BD (NHOM 43) - BAI 168 (MILESTONE BD.1)")
    print("MANG LUOI MANG TAM THU 2D SYSTOLIC ARRAY PROCESSING ELEMENTS (PE)")
    print("================================================================================")

    # 1. Kiem thu GEMM tren mang 4x4
    print("[1] Kiem thu phep nhan ma tran GEMM tren mang PE 4x4 (Wavefront Skewing):")
    array_4x4 = SystolicArray2DMesh(rows=4, cols=4)

    mat_a = [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12],
        [13, 14, 15, 16]
    ]

    mat_b = [
        [1, 0, 2, 0],
        [0, 1, 0, 2],
        [2, 0, 1, 0],
        [0, 2, 0, 1]
    ]

    # Ket qua phan mem chuan (Ground Truth)
    ground_truth = [
        [sum(mat_a[i][k] * mat_b[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]

    res_c, metrics = array_4x4.execute_gemm(mat_a, mat_b)

    assert res_c == ground_truth, "Loi: Ket qua Systolic Array khong khop Ground Truth!"
    print("    * Ground Truth C[0]:", ground_truth[0])
    print("    * Systolic C[0]    :", res_c[0])
    print("    * Ground Truth C[3]:", ground_truth[3])
    print("    * Systolic C[3]    :", res_c[3])
    print("    * Trang thai: 100% BIT-EXACT MATCH (Chinh xac tuyet doi!)")

    # 2. Phan tich chi so chu ky va luu thong du lieu
    print("\n[2] Phan tich hieu nang va chi so phan cung (Hardware Metrics):")
    print(f"    * Tong so chu ky thuc thi (Total Cycles)       : {metrics['total_cycles']:.0f} cycles")
    print(f"    * Do tre can le Wavefront (Skewing Latency)    : {metrics['wavefront_skew_latency']:.0f} cycles")
    print(f"    * Tong so phep nhan-cong MAC (Total MAC Ops)   : {metrics['total_mac_ops']:.0f} ops")
    print(f"    * Thong luong tinh toan (Throughput)           : {metrics['macs_per_cycle']:.2f} MACs/cycle")
    print(f"    * Hieu suat tan dung PE (PE Utilization)       : {metrics['pe_utilization_percent']:.1f}%")

    # 3. Kiem thu mang 8x8 voi ma tran ngau nhien
    print("\n[3] Kiem thu mang 8x8 PE voi du lieu ngau nhien (M=8, K=12, N=8):")
    array_8x8 = SystolicArray2DMesh(rows=8, cols=8)
    import random
    random.seed(42)
    rand_a = [[random.randint(-10, 10) for _ in range(12)] for _ in range(8)]
    rand_b = [[random.randint(-10, 10) for _ in range(8)] for _ in range(12)]

    expected_8x8 = [
        [sum(rand_a[i][k] * rand_b[k][j] for k in range(12)) for j in range(8)]
        for i in range(8)
    ]

    actual_8x8, metrics_8x8 = array_8x8.execute_gemm(rand_a, rand_b)
    assert actual_8x8 == expected_8x8, "Loi khong khop tai mang 8x8!"
    print(f"    * Ma tran 8x12 nhan 12x8: PASS (Khop 64/64 phan tu)")
    print(f"    * So chu ky thuc thi     : {metrics_8x8['total_cycles']:.0f} cycles")
    print(f"    * Thong luong trung binh : {metrics_8x8['macs_per_cycle']:.2f} MACs/cycle")

    # 4. Kiem thu Tiling phan manh ma tran lon (16x16 tren core 8x8)
    print("\n[4] Kiem thu phan manh Tiling ma tran lon (16x16 tren mang 8x8):")
    big_a = [[random.randint(1, 5) for _ in range(16)] for _ in range(16)]
    big_b = [[random.randint(1, 5) for _ in range(16)] for _ in range(16)]
    expected_big = [
        [sum(big_a[i][k] * big_b[k][j] for k in range(16)) for j in range(16)]
        for i in range(16)
    ]

    tiled_res, tiled_metrics = array_8x8.execute_tiled_gemm(big_a, big_b)
    assert tiled_res == expected_big, "Loi khong khop tai phep nhan Tiled GEMM!"
    print(f"    * Tiled GEMM 16x16: PASS 100%")
    print(f"    * Tong chu ky Tiled: {tiled_metrics['total_cycles']:.0f} cycles cho 4096 MACs")
    print("================================================================================")


if __name__ == "__main__":
    test_systolic_array_2d()
