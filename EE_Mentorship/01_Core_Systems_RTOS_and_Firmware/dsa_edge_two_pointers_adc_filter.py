"""
================================================================================
          MODULE AK: HARDWARE DATA STRUCTURES & SYSTEMS ALGORITHMS
              MILESTONE AK.1: GIẢI THUẬT 2 CON TRỎ (TWO POINTERS) & CỬA SỔ TRƯỢT O(1)
================================================================================

TẠI SAO KỸ SƯ PHẦN CỨNG NHÚNG PHẢI THUẦN THỤC GIẢI THUẬT 2 CON TRỎ?
Trong vi điều khiển (ARM Cortex-M0/M4 với chỉ 32KB RAM):
- Không được phép cấp phát động (malloc / new) vì gây phân mảnh bộ nhớ RAM Heap!
- Mọi phép lọc dữ liệu, loại bỏ nhiễu giật (glitch) phải thực thi TẠI CHỖ (In-Place)
  với bộ nhớ phụ O(1) và thời gian O(N).

1. KỸ THUẬT 2 CON TRỎ ĐỌC-GHI (FAST-SLOW READ-WRITE POINTERS):
   - Con trỏ Đọc (fast_ptr): Quét qua toàn bộ mảng mẫu ADC đầu vào.
   - Con trỏ Ghi (slow_ptr): Chỉ ghi lại các mẫu hợp lệ (loại bỏ nhiễu kẹt bit Stuck-At Fault).
   - Độ phức tạp: Thời gian O(N), Bộ nhớ phụ O(1) RAM!

2. KỸ THUẬT CỬA SỔ TRƯỢT O(1) MỖI MẪU (O(1) SLIDING WINDOW):
   Thay vì lặp lại K phần tử để tính trung bình tốn O(K*N) chu kỳ clock:
   
          Sum_new = Sum_old - X_ra + X_vao
          
                     Sum_new
          Mean_new = ───────
                        K
   Mỗi mẫu ADC mới chỉ tốn đúng 1 phép trừ và 1 phép cộng: O(1) chu kỳ xung nhịp!
"""

import numpy as np

class TwoPointersADCFilter:
    """
    Bộ xử lý tín hiệu cảm biến thời gian thực bằng giải thuật 2 con trỏ
    """
    def __init__(self, window_size: int = 5):
        self.k = window_size

    def in_place_remove_sensor_glitches(self, samples: list, max_repeat: int = 2) -> int:
        """
        Thuật toán 2 con trỏ Fast-Slow:
        Loại bỏ các mẫu bị kẹt cứng cảm biến (stuck-at sensor) lặp lại quá max_repeat lần.
        Thực thi in-place trực tiếp trên mảng gốc, không cấp phát thêm RAM!
        Trả về: Số lượng phần tử hợp lệ mới (valid_len)
        """
        n = len(samples)
        if n <= max_repeat:
            return n

        slow_ptr = max_repeat
        for fast_ptr in range(max_repeat, n):
            # So sánh với phần tử cách đó max_repeat vị trí tại con trỏ chậm
            if samples[fast_ptr] != samples[slow_ptr - max_repeat]:
                samples[slow_ptr] = samples[fast_ptr]
                slow_ptr += 1

        return slow_ptr

    def two_pointers_symmetric_check(self, waveform: list) -> bool:
        """
        Thuật toán 2 con trỏ Đối xứng (Left-Right Pointers):
        Kiểm tra tính đối xứng của sóng sin/tam giác để phát hiện méo hài bán kỳ.
        Con trỏ Left đi từ đầu (0), con trỏ Right đi từ cuối (n-1) dồn về giữa.
        Độ phức tạp: O(N/2) = O(N) thời gian, O(1) bộ nhớ RAM.
        """
        left = 0
        right = len(waveform) - 1

        while left < right:
            if abs(waveform[left] - waveform[right]) > 1e-4:
                return False
            left += 1
            right -= 1

        return True


class O1SlidingWindowFilter:
    """
    Mạch lọc cửa sổ trượt O(1) chu kỳ CPU cho dòng dữ liệu liên tục từ ADC
    """
    def __init__(self, window_size: int = 5):
        self.k = window_size
        self.buffer = [0.0] * window_size
        self.head = 0
        self.current_sum = 0.0
        self.count = 0

    def process_sample(self, new_val: float) -> float:
        """
        Thuật toán Cửa sổ trượt O(1):
        1. Trừ giá trị cũ nhất rơi khỏi cửa sổ: current_sum -= buffer[head]
        2. Ghi đè giá trị mới vào buffer vòng: buffer[head] = new_val
        3. Cộng giá trị mới vào tổng: current_sum += new_val
        4. Tịnh tiến con trỏ đầu vòng: head = (head + 1) % K
        5. Trả về giá trị trung bình: current_sum / K
        Độ phức tạp: Đúng 2 phép toán số học O(1) CPU!
        """
        # 1. Trừ mẫu cũ
        old_val = self.buffer[self.head]
        self.current_sum -= old_val

        # 2. Lưu mẫu mới
        self.buffer[self.head] = new_val
        self.current_sum += new_val

        # 3. Tịnh tiến con trỏ vòng đệm
        self.head = (self.head + 1) % self.k

        if self.count < self.k:
            self.count += 1

        return float(self.current_sum / self.count)


if __name__ == "__main__":
    print("=========================================================")
    print("   HARDWARE DSA: TWO POINTERS & O(1) SLIDING WINDOW")
    print("=========================================================\n")

    filter_engine = TwoPointersADCFilter(window_size=5)

    # 1. Thuật toán 2 con trỏ Fast-Slow loại bỏ nhiễu kẹt cảm biến In-Place
    # Dữ liệu ADC có hiện tượng kẹt áp: 1.2V lặp 4 lần, 3.3V lặp 3 lần
    adc_raw = [1.2, 1.2, 1.2, 1.2, 2.5, 3.3, 3.3, 3.3, 4.1]
    print(f"1. DU LIEU ADC BAN DAU ({len(adc_raw)} phan tu) : {adc_raw}")

    valid_count = filter_engine.in_place_remove_sensor_glitches(adc_raw, max_repeat=2)
    compact_data = adc_raw[:valid_count]
    print(f"   -> Sau Two-Pointers In-Place O(1) RAM : {compact_data}")
    print(f"   -> So mau hop le sau loc              : {valid_count}")
    assert compact_data == [1.2, 1.2, 2.5, 3.3, 3.3, 4.1], "Loi giai thuat Fast-Slow Pointers!"

    # 2. Thuật toán 2 con trỏ Left-Right kiểm tra đối xứng sóng xung điện
    sym_wave = [0.1, 0.8, 1.5, 2.0, 1.5, 0.8, 0.1]
    asym_wave = [0.1, 0.8, 1.5, 2.0, 1.4, 0.8, 0.1]
    print(f"\n2. KIEM TRA DOI XUNG SONG (LEFT-RIGHT TWO POINTERS):")
    print(f"   -> Song 1 doi xung hoan hao : {filter_engine.two_pointers_symmetric_check(sym_wave)}")
    print(f"   -> Song 2 meo lech bien do  : {filter_engine.two_pointers_symmetric_check(asym_wave)}")
    assert filter_engine.two_pointers_symmetric_check(sym_wave) is True
    assert filter_engine.two_pointers_symmetric_check(asym_wave) is False

    # 3. Thuật toán Cửa sổ trượt O(1) CPU
    sliding = O1SlidingWindowFilter(window_size=4)
    stream = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    filtered_outs = [sliding.process_sample(v) for v in stream]
    print(f"\n3. LOC CUA SO TRUOT O(1) CHU KY XUNG NHIP CPU:")
    print(f"   -> Dong mau dau vao : {stream}")
    print(f"   -> Dau ra sau loc   : {[round(x, 2) for x in filtered_outs]}")
    # Sau khi cửa sổ đầy 4 mẫu [20, 30, 40, 50] -> trung bình = 140 / 4 = 35.0
    assert abs(filtered_outs[4] - 35.0) < 1e-4, "Loi cua so truot O(1)!"

    print("\n[THANH CONG] GIAI THUAT TWO POINTERS VA O(1) SLIDING WINDOW HOAN TAT CHUAN XAC!")
