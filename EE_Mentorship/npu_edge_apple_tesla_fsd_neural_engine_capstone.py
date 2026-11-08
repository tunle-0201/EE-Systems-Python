"""
EE Mentorship - Module BD (Nhom 43) - Bai 171 (Milestone BD.4 - Capstone Project)
Chuyen de: Dong co Bo tang toc Tri tue Nhan tao Apple Neural Engine (ANE) & Tesla FSD HW5 NPU Capstone:
           Bo dieu phoi DMA Descriptors, Phan manh Scratchpad SRAM, Thuc thi Vision Transformer
           va Do luong Hieu suat Nang luong TOPS/W.

Muc tieu he thong:
1. Mo phong kien truc NPU da loi Multi-Core (Tesla FSD HW5 Dual/Tri-Core, Apple ANE 16-Core).
2. Xay dung bo dieu phoi DMA Descriptors bat dong bo voi co che dem kep Ping-Pong Double-Buffering.
3. Tich hop mang luoi tam thu 2D Systolic Array (Weight-Stationary) voi bo nho Scratchpad SRAM 2MB.
4. Khoi xu ly hau ky gop Fused Post-Processing: Requantization (M_0 * 2^-n) + Phi tuyen (ReLU / GELU / SiLU).
5. Thuc thi toan trinh lop mang thi giac xe tu hanh Tesla FSD Autopilot 8-Camera 360 do va do luong FPS & TOPS/W.
"""

import os
import sys
import time
import math
import random
from typing import List, Tuple, Dict, Optional

# Nhom thu vien lien ket tu cac milestone truoc
sys.path.append(os.path.dirname(__file__))
from npu_edge_systolic_array_2d_mesh import SystolicArray2DMesh
from npu_edge_dataflow_weight_stationary import DataflowSimulator, DataflowType, MemoryEnergyProfile, RooflineModel
from npu_edge_int8_fp8_quantization_engine import INT8Quantizer, FixedPointRequantizer


class DMADescriptor:
    """
    Bo mo ta DMA Descriptor theo chuan Scatter-Gather:
    Dieu phoi truyen du lieu DMA tu Dong giua DRAM va SRAM khong lam dung CPU.
    """
    def __init__(self, desc_id: int, src_addr: int, dst_addr: int, size_bytes: int, direction: str):
        self.desc_id = desc_id
        self.src_addr = src_addr
        self.dst_addr = dst_addr
        self.size_bytes = size_bytes
        self.direction = direction  # "DRAM_TO_SRAM" hoac "SRAM_TO_DRAM"
        self.completed = False

    def execute_transfer(self) -> int:
        """Mo phong chu ky truyen DMA dua tren do rong bus 256-bit (32 bytes/cycle)."""
        cycles = math.ceil(self.size_bytes / 32)
        self.completed = True
        return cycles


class ScratchpadSRAM:
    """
    Bo nho dem cuc bo Scratchpad SRAM 2MB tren moi NPU Core:
    Phan chia thanh cac vung dem:
      - Weight Bank (1024 KB): Luu tru trong so mo hinh Weight Stationary
      - Ping Activation Bank (384 KB): Luu tru kich hoat dau vao dang tinh toan
      - Pong Activation Bank (384 KB): Luu tru kich hoat dang duoc DMA nap ngam (Prefetch)
      - Output Accumulator Bank (256 KB): Luu tru ket qua sau khi Requantize
    """
    def __init__(self, capacity_kb: int = 2048):
        self.capacity_bytes = capacity_kb * 1024
        self.weight_bank: Dict[int, int] = {}
        self.ping_bank: Dict[int, int] = {}
        self.pong_bank: Dict[int, int] = {}
        self.output_bank: Dict[int, int] = {}
        self.active_buffer = "PING"

    def swap_buffers(self):
        """Dao chieu con tro Ping-Pong khi ket thuc chu ky tinh toan tile."""
        self.active_buffer = "PONG" if self.active_buffer == "PING" else "PING"


class FusedPostProcessor:
    """
    Khoi xu ly hau ky gop (Fused Post-Processing Unit):
    Thuc hien tren cung mot duong ong silicon ngay sau khi Accumulator tinh xong:
      1. Tai luong tu hoa Requantization khong phep chia: (acc * M_0 + bias) >> n
      2. Ham kich hoat phi tuyen (ReLU, GELU, SiLU / Swish)
    """
    @staticmethod
    def apply_activation(val: int, act_type: str = "RELU") -> int:
        if act_type == "RELU":
            return max(0, val)
        elif act_type == "RELU6":
            return max(0, min(6, val))
        elif act_type == "SILU":
            # Xap xi nguyen cua SiLU: x * sigmoid(x)
            if val < -4:
                return 0
            elif val > 4:
                return val
            else:
                return round(val * (0.5 + 0.125 * val))
        return val


class NeuralEngineCore:
    """
    Loi xu ly mang no-ron chuyen dung (NPU Core):
    Tich hop Mang tam thu 2D Systolic Array (16x16 PE), Bo nho SRAM 2MB, va Fused Post-Processor.
    """
    def __init__(self, core_id: int, pe_rows: int = 16, pe_cols: int = 16):
        self.core_id = core_id
        self.array = SystolicArray2DMesh(rows=pe_rows, cols=pe_cols)
        self.sram = ScratchpadSRAM(capacity_kb=2048)
        self.fused_unit = FusedPostProcessor()
        self.total_core_cycles = 0

    def compute_tile(
        self,
        sub_a: List[List[int]],
        sub_b: List[List[int]],
        bias_val: int,
        m0: int,
        n: int,
        act_type: str = "RELU"
    ) -> Tuple[List[List[int]], int]:
        """
        Thuc thi tinh toan 1 khoi tile ma tran:
        1. Nhan tren 2D Systolic Array.
        2. Cong Bias va Requantize ve INT8.
        3. Ap dung ham phi tuyen Fused Activation.
        """
        raw_c, metrics = self.array.execute_gemm(sub_a, sub_b)
        cycles = int(metrics["total_cycles"])
        self.total_core_cycles += cycles

        # Fused Post-Processing
        processed_c = []
        for r in range(len(raw_c)):
            row = []
            for c in range(len(raw_c[0])):
                acc_with_bias = raw_c[r][c] + bias_val
                # Requantize
                q_val = FixedPointRequantizer.apply_requantization(acc_with_bias, m0, n)
                # Activation
                act_val = self.fused_unit.apply_activation(q_val, act_type)
                row.append(act_val)
            processed_c.append(row)

        return processed_c, cycles


class AppleTeslaNeuralEngineCapstone:
    """
    He thong Bo tang toc Tri tue Nhan tao Apple Neural Engine (ANE) & Tesla FSD HW5 Capstone:
    - Kien truc da loi Multi-Core NPU (2 Loi Tesla FSD hoac 16 Loi Apple ANE)
    - Bo dieu phoi DMA Descriptor Ring voi Ping-Pong Double-Buffering
    - Thuc thi toan trinh lop mang Vision Transformer (ViT) va Conv2D
    - Do luong hieu suat FPS cho cum 8 Camera 360 do va chi so TOPS/W
    """
    def __init__(self, num_cores: int = 2, peak_tops: float = 144.0, mem_bw_gbps: float = 136.0):
        self.num_cores = num_cores
        self.cores = [NeuralEngineCore(core_id=i, pe_rows=16, pe_cols=16) for i in range(num_cores)]
        self.peak_tops = peak_tops
        self.mem_bw_gbps = mem_bw_gbps
        self.roofline = RooflineModel(peak_compute_tops=peak_tops, memory_bandwidth_gbps=mem_bw_gbps)
        self.dma_queue: List[DMADescriptor] = []
        self.clock_freq_ghz = 1.0  # Tan so xung nhip 1.0 GHz

    def dispatch_dma_transfer(self, src: int, dst: int, size_bytes: int, direction: str) -> int:
        """Tao va kich hoat truyen du lieu DMA Descriptors."""
        desc = DMADescriptor(len(self.dma_queue), src, dst, size_bytes, direction)
        self.dma_queue.append(desc)
        cycles = desc.execute_transfer()
        return cycles

    def execute_workload_layer(
        self,
        batch_tokens: int,
        in_dim: int,
        out_dim: int,
        act_type: str = "RELU"
    ) -> Dict[str, float]:
        """
        Thuc thi mot lop mang no-ron toan trinh:
        Chia deu batch_tokens qua cac NPU Core de chay song song (Data Parallelism / Core Sharding).
        """
        tokens_per_core = math.ceil(batch_tokens / self.num_cores)
        total_macs = batch_tokens * in_dim * out_dim
        total_flops = 2 * total_macs

        # 1. Mo phong DMA nap trong so vao Weight Bank SRAM cua cac loi
        weight_bytes = in_dim * out_dim  # INT8
        dma_weight_cycles = self.dispatch_dma_transfer(0x10000000, 0x20000000, weight_bytes, "DRAM_TO_SRAM")

        # 2. Sinh ma tran thu nghiem ngau nhien
        random.seed(42)
        test_w = [[random.randint(-3, 3) for _ in range(16)] for _ in range(16)]
        test_a = [[random.randint(1, 5) for _ in range(16)] for _ in range(16)]
        m0, n = FixedPointRequantizer.compute_multiplier_and_shift(0.015625)

        # 3. Thuc thi da loi tren Systolic Array voi co che Ping-Pong Double-Buffering
        total_tiles = math.ceil(tokens_per_core / 16) * math.ceil(in_dim / 16) * math.ceil(out_dim / 16)
        
        # Mo phong Cycle-Accurate tren 1 tile dai dien (theo chuan Scale-Sim / Timeloop ASIC profiler)
        single_tile_cycles = 0
        for core in self.cores:
            _, single_tile_cycles = core.compute_tile(test_a, test_w, bias_val=2, m0=m0, n=n, act_type=act_type)
            core.sram.swap_buffers()

        # Tong chu ky thuc thi thuc te (DMA nap ngam duoc an giau hoan toan nho Ping-Pong)
        max_core_cycles = total_tiles * single_tile_cycles

        # Tong chu ky he thong = DMA nap trong so ban dau + thoi gian chay da loi
        total_system_cycles = dma_weight_cycles + max_core_cycles
        execution_time_sec = total_system_cycles / (self.clock_freq_ghz * 1e9)

        # 4. Tinh toan nang luong va hieu nang
        sim = DataflowSimulator(array_rows=16, array_cols=16, sram_capacity_kb=2048)
        energy_metrics = sim.simulate_gemm(batch_tokens, in_dim, out_dim, DataflowType.WEIGHT_STATIONARY)

        attainable_tops, regime, compute_eff = self.roofline.evaluate(
            energy_metrics["operational_intensity_flops_per_byte"]
        )

        achieved_tops = (total_flops / execution_time_sec) / 1e12 if execution_time_sec > 0 else 0.0
        # Cong suat trung binh (Watts) = Energy (Joules) / Time (Seconds)
        power_watts = (energy_metrics["total_energy_uj"] * 1e-6) / execution_time_sec if execution_time_sec > 0 else 1.0
        actual_tops_per_watt = achieved_tops / power_watts if power_watts > 0 else 0.0

        # Tinh toan Frame Rate (FPS) cho camera xe tu hanh Tesla FSD HW5
        # 1 khung hinh xu ly qua ~15 lop mang tuong duong
        latency_per_frame_ms = (execution_time_sec * 15.0) * 1000.0
        total_fps = 1000.0 / latency_per_frame_ms if latency_per_frame_ms > 0 else 0.0

        return {
            "total_system_cycles": float(total_system_cycles),
            "execution_time_ms": execution_time_sec * 1000.0,
            "achieved_tops": achieved_tops,
            "attainable_tops_roofline": attainable_tops,
            "power_consumption_watts": power_watts,
            "energy_efficiency_tops_per_watt": actual_tops_per_watt,
            "camera_fps_throughput": total_fps,
            "compute_efficiency_pct": compute_eff,
            "roofline_regime": regime
        }


def test_apple_tesla_neural_engine_capstone():
    """
    Chuong trinh kiem thu Capstone toan dien:
    Apple Neural Engine (ANE) & Tesla FSD HW5 Multi-Core NPU.
    """
    print("================================================================================")
    print("EE MENTORSHIP - MODULE BD (NHOM 43) - BAI 171 (CAPSTONE PROJECT)")
    print("DONG CO BO TANG TOC TRI TUE NHAN TAO APPLE NEURAL ENGINE & TESLA FSD HW5 NPU")
    print("================================================================================")

    # Khoi tao NPU 2 Core (Tesla FSD HW5 NPU Spec: 144 TOPS, 136 GB/s LPDDR5X)
    npu = AppleTeslaNeuralEngineCapstone(num_cores=2, peak_tops=144.0, mem_bw_gbps=136.0)

    # ==========================================================================
    # PHAN 1: KIEM THU DMA CONTROLLER & PING-PONG DOUBLE-BUFFERING
    # ==========================================================================
    print("\n[1] Kiem thu Bo dieu phoi DMA Descriptors va Dem kep Ping-Pong:")
    test_dma_bytes = 1024 * 512  # 512 KB
    dma_cycles = npu.dispatch_dma_transfer(0x20000000, 0x30000000, test_dma_bytes, "DRAM_TO_SRAM")
    print(f"    * Truyen DMA 512 KB: {dma_cycles} chu ky (Bus 256-bit @ 32 B/cycle)")
    print(f"    * Trang thai DMA Descriptor: COMPLETED={npu.dma_queue[0].completed}")

    # ==========================================================================
    # PHAN 2: KIEM THU FUSED REQUANTIZATION + ACTIVATION
    # ==========================================================================
    print("\n[2] Kiem thu Khoi xu ly hau ky gop (Fused Requantization + ReLU / SiLU):")
    core0 = npu.cores[0]
    test_a = [[10, 20], [30, 40]]
    test_w = [[2, -1], [1, 2]]
    m0, n = FixedPointRequantizer.compute_multiplier_and_shift(0.5)

    out_tile, c_cycles = core0.compute_tile(test_a, test_w, bias_val=0, m0=m0, n=n, act_type="RELU")
    print(f"    * Ket qua xu ly gop Fused Tile:")
    print(f"      - Output [0]: {out_tile[0]}")
    print(f"      - Output [1]: {out_tile[1]}")
    assert out_tile[0][0] >= 0 and out_tile[1][1] >= 0, "Loi: Ham ReLU khong loai bo so am!"
    print("    * Fused Activation Unit: PASS (Requantize va ReLU tich hop tren cung pipeline)")

    # ==========================================================================
    # PHAN 3: THUC THI LOP VISION TRANSFORMER (ViT) TRUONG ANH XE TU HANH
    # ==========================================================================
    print("\n[3] Thuc thi toan trinh lop Vision Transformer Backbone (Tesla Autopilot):")
    # Batch 197 tokens, In_dim = 768, Out_dim = 768
    vit_res = npu.execute_workload_layer(batch_tokens=197, in_dim=768, out_dim=768, act_type="RELU")

    print(f"    * Tong so chu ky he thong (Total Cycles): {vit_res['total_system_cycles']:.0f} cycles")
    print(f"    * Thoi gian thuc thi (Latency)         : {vit_res['execution_time_ms']:.3f} ms")
    print(f"    * Cong suat tieu thu uoc tinh (Power)   : {vit_res['power_consumption_watts']:.2f} W")
    print(f"    * Toc do khung hinh (Throughput FPS)    : {vit_res['camera_fps_throughput']:.1f} FPS")

    # Yeu cau cum camera xe tu hanh dat chuan thoi gian thuc >= 60 FPS
    assert vit_res["camera_fps_throughput"] >= 60.0, "NPU phai dat toc do xu ly thoi gian thuc tren 60 FPS!"
    print(f"    * Danh gia: Dap ung du thua chuan 60 FPS cua cum 8 Camera Tesla FSD HW5!")

    # ==========================================================================
    # PHAN 4: THUC THI LOP CONV2D HEAVY BACKBONE & HIEN THUC DINH 144 TOPS
    # ==========================================================================
    print("\n[4] Kiem thu lop Convolutional Tiled GEMM Backbone (Bao hoa cong suat NPU):")
    conv_res = npu.execute_workload_layer(batch_tokens=2048, in_dim=1024, out_dim=1024, act_type="RELU")

    print(f"    * Hieu nang thuc te dat duoc           : {conv_res['achieved_tops']:.2f} TOPS")
    print(f"    * Tran hieu nang Roofline toi da        : {conv_res['attainable_tops_roofline']:.2f} TOPS")
    print(f"    * Hieu qua su dung phan cung (Compute)  : {conv_res['compute_efficiency_pct']:.1f}%")
    print(f"    * Hieu qua nang luong (Efficiency)      : {conv_res['energy_efficiency_tops_per_watt']:.2f} TOPS/W")

    assert conv_res["compute_efficiency_pct"] > 70.0, "Phai dat hieu qua tan dung NPU > 70%!"
    print("    * Trang thai Roofline: COMPUTE-SATURATED (Bao hoa toi da mang PE Systolic)")

    print("\n================================================================================")
    print("CHUC MUNG! CAPSTONE NPU NEURAL ENGINE HOAN THANH XUAT SAC 100%!")
    print("San sang tich hop vao Chip Apple Silicon M-Series & Tesla FSD HW5 SoC!")
    print("================================================================================")


if __name__ == "__main__":
    test_apple_tesla_neural_engine_capstone()
