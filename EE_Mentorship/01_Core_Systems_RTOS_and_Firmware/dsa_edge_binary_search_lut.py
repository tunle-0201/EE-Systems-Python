"""
================================================================================
          MODULE AK: HARDWARE DATA STRUCTURES & SYSTEMS ALGORITHMS
              MILESTONE AK.2: TÌM KIẾM NHỊ PHÂN O(log N) VÀ BẢNG TRA CỨU FLASH (LUT)
================================================================================

TẠI SAO PHẢI DÙNG BINARY SEARCH ĐỂ TRA CỨU BẢNG (LOOK-UP TABLE - LUT) TRÊN XE Ô TÔ?
Khi điều khiển động cơ điện BLDC hoặc đo dung lượng pin xe điện (BMS Battery SOC):
- Đường cong xả áp của pin là phi tuyến.
- Vi điều khiển không thể giải phương trình vi phân phức tạp trong vòng ngắt 100 us!
- Thay vào đó, 1024 điểm đo được lưu sẵn vào bộ nhớ Flash ROM thành bảng tra cứu (LUT).

SO SÁNH HIỆU NĂNG THỜI GIAN THỰC (BIG-O COMPLEXITY):
1. Tìm kiếm tuần tự (Linear Search):
   - Duyệt từng phần tử từ đầu đến cuối: O(N) so sánh.
   - Với N = 1024 điểm: Tốn tối đa 1024 chu kỳ xung nhịp CPU -> Nguy cơ trễ chu kỳ ngắt!
2. Tìm kiếm nhị phân (Binary Search O(log N)):
   - Chia đôi không gian tìm kiếm mỗi bước: O(log2 N) so sánh.
   - Với N = 1024 điểm: Chỉ tốn tối đa 10 phép so sánh! Nhanh gấp 100 lần!

CÔNG THỨC NỘI SUY TUYẾN TÍNH (ASCII TEXT BLOCK):
Sau khi Binary Search tìm được 2 điểm chặn kẹp [x_low, x_high]:

                                 x - x_low
    y = y_low + (y_high - y_low) * ──────────────
                                 x_high - x_low
"""

import numpy as np

class BinarySearchLUT:
    """
    Bảng tra cứu Look-Up Table tối ưu hóa bằng thuật toán Tìm kiếm nhị phân O(log N)
    """
    def __init__(self, x_table: list, y_table: list):
        assert len(x_table) == len(y_table), "Kich thuoc 2 bang LUT phai bang nhau!"
        self.x_lut = list(x_table)
        self.y_lut = list(y_table)
        self.n = len(x_table)

    def binary_search_bounds(self, target_x: float) -> tuple:
        """
        Tìm kiếm nhị phân O(log N) xác định 2 chỉ số [low_idx, high_idx] kẹp giữa target_x:
        Trả về: (low_idx, high_idx, num_comparisons)
        """
        # Biên dưới và biên trên
        if target_x <= self.x_lut[0]:
            return 0, 0, 1
        if target_x >= self.x_lut[-1]:
            return self.n - 1, self.n - 1, 1

        low = 0
        high = self.n - 1
        comparisons = 0

        while low <= high:
            comparisons += 1
            mid = (low + high) // 2

            if self.x_lut[mid] == target_x:
                return mid, mid, comparisons
            elif self.x_lut[mid] < target_x:
                low = mid + 1
            else:
                high = mid - 1

        # Khi vòng lặp kết thúc: high chính là cận dưới, low chính là cận trên
        return high, low, comparisons

    def interpolate(self, target_x: float) -> tuple:
        """
        Tra cứu và nội suy tuyến tính giá trị y = f(x):
        Trả về: (y_interpolated, comparisons_count)
        """
        idx_low, idx_high, steps = self.binary_search_bounds(target_x)

        if idx_low == idx_high:
            return float(self.y_lut[idx_low]), steps

        x0, x1 = self.x_lut[idx_low], self.x_lut[idx_high]
        y0, y1 = self.y_lut[idx_low], self.y_lut[idx_high]

        # Phép nội suy tuyến tính: y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        slope = (y1 - y0) / (x1 - x0)
        y_interp = y0 + slope * (target_x - x0)

        return float(y_interp), steps


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DSA: BINARY SEARCH O(log N) & FLASH LUT")
    print("=========================================================\n")

    # Giả lập bảng tra cứu đường cong xả điện áp pin Lithium (BMS Battery SOC)
    # Điện áp cell (V) -> Dung lượng pin còn lại (SOC %)
    # Bảng 1024 điểm đo thực tế
    lut_size = 1024
    voltages = np.linspace(3.0, 4.2, lut_size).tolist()
    # Đường cong phi tuyến giả lập (dốc nhanh ở 3.0-3.3V và 4.0-4.2V, phẳng ở giữa)
    soc_curve = [float(100.0 * (1.0 / (1.0 + np.exp(-10.0 * (v - 3.6))))) for v in voltages]

    bms_lut = BinarySearchLUT(x_table=voltages, y_table=soc_curve)

    print("1. THONG SO BANG TRA CUU PHAN CUNG:")
    print(f"   -> So luong diem du lieu trong Flash ROM : {lut_size} points")
    print(f"   -> Gioi han so sanh toi da cua O(log2 N) : {int(np.ceil(np.log2(lut_size)))} comparisons\n")

    # Kiểm tra tra cứu tại các mức điện áp bất kỳ
    test_voltages = [3.25, 3.60, 3.85, 4.15]

    print("2. KET QUA TRA CUU VA NOI SUY PIN O(log N):")
    for v_query in test_voltages:
        soc_est, comps = bms_lut.interpolate(v_query)
        print(f"   -> Dien ap V = {v_query:.3f}V  |  Dung luong SOC = {soc_est:5.1f}%  |  So phep so sanh: {comps:2d} buoc")
        assert comps <= 11, f"Binary Search vuot qua nguong O(log N): {comps} > 11!"

    # So sánh với Linear Search để thấy rõ ưu thế tốc độ
    linear_steps = 0
    for v in voltages:
        linear_steps += 1
        if v >= 3.85:
            break
    print(f"\n3. SO SANH HIEU SUAT VOI LINEAR SEARCH:")
    print(f"   -> Linear Search tai 3.85V : ton {linear_steps} chu ky CPU")
    print(f"   -> Binary Search tai 3.85V : ton 10 chu ky CPU (Nhanh hon {linear_steps // 10} lan!)")

    print("\n[THANH CONG] GIAI THUAT BINARY SEARCH LUT O(log N) HOAN TAT XUAT SAC!")
