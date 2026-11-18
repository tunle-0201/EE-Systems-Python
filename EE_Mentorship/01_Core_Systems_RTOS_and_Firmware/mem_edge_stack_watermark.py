"""
================================================================================
          MODULE V: EMBEDDED MEMORY MANAGEMENT & AVIONICS HEAP
              MILESTONE V.2: BẢO VỆ TRÀN STACK & MỰC NƯỚC (STACK WATERMARK GUARD)
================================================================================

TẠI SAO TRÀN NGĂN XẾP (STACK OVERFLOW) LÀ NGUYÊN NHÂN SỐ 1 GÂY CRASH VI ĐIỀU KHIỂN?
Trong FreeRTOS:
- Mỗi Task được cấp một vùng nhớ Stack riêng (ví dụ: 512 bytes).
- Khi hàm lồng nhau hoặc khai báo mảng lớn, con trỏ Stack Pointer (SP) tràn qua biên phá hủy dữ liệu khác.
- Kỹ thuật **Stack Watermarking & Canary Pattern**:
  + Khi khởi tạo, toàn bộ Stack được phủ đầy mẫu byte 0xA5 (165).
  + Con chim hoàng yến (Canary Guard) đặt ở đáy Stack: nếu byte này bị ghi đè khác 0xA5 -> Kích hoạt Failsafe khẩn cấp!
  + Đo lượng byte 0xA5 còn lại để biết "Mực nước Stack dư thừa" (High Watermark).
"""

class TaskStackGuard:
    CANARY_BYTE = 0xA5

    def __init__(self, stack_size_words: int = 16):
        self.stack_size = stack_size_words
        # Phủ đầy Stack bằng mẫu Canary 0xA5
        self.stack = [self.CANARY_BYTE] * stack_size_words

    def simulate_stack_usage(self, used_words: int):
        """Giả lập Task sử dụng ngăn xếp từ đỉnh xuống (chỉ số cao xuống thấp)."""
        used_words = min(used_words, self.stack_size)
        for i in range(self.stack_size - used_words, self.stack_size):
            self.stack[i] = 0x11  # Ghi đè dữ liệu thực

    def check_stack_overflow(self) -> bool:
        """
        Trò đóng vai Kỹ sư An toàn Bộ nhớ:
        - Kiểm tra byte đầu tiên ở đáy Stack (index 0).
        - Nếu self.stack[0] != CANARY_BYTE -> Đã bị tràn Stack -> Trả về True
        - Ngược lại: Trả về False (An toàn)
        """
        return self.stack[0] != self.CANARY_BYTE

    def get_high_watermark(self) -> int:
        """Đếm số words chưa bao giờ bị chạm tới từ đáy lên."""
        count = 0
        for val in self.stack:
            if val == self.CANARY_BYTE:
                count += 1
            else:
                break
        return count


if __name__ == "__main__":
    print("=========================================================")
    print("   AVIONICS MEMORY: STACK WATERMARK & CANARY GUARD")
    print("=========================================================\n")

    guard = TaskStackGuard(stack_size_words=10)
    
    # Task sử dụng 7 words
    guard.simulate_stack_usage(used_words=7)

    is_overflow = guard.check_stack_overflow()
    watermark = guard.get_high_watermark()

    print("1. KET QUA GIAM SAT NGAN XEP TASK REAL-TIME:")
    print(f"   -> Phat hien tran Stack (Overflow) : {is_overflow}")
    print(f"   -> Muc nuoc Stack con an toan      : {watermark} words (30% du phong)")

    assert is_overflow == False and watermark == 3, "Loi Stack Watermark Guard!"
    print("\n[THANH CONG] DA HOAN THANH CO CHE CANARY BAO VE NGAN XEP TASK CHO HE DIEU HANH RTOS!")
