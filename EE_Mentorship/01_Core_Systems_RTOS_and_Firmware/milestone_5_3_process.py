"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 5: ĐA LUỒNG & ĐA TIẾN TRÌNH
                  MILESTONE 5.3: MULTI-PROCESSING (ĐA TIẾN TRÌNH)
================================================================================

Chào trò! Trong bài này, chúng ta sẽ tạo ra 2 Tiến trình (Processes) hoàn toàn
độc lập chạy trên 2 Nhân CPU vật lý khác nhau.

Vì RAM của 2 Process bị cô lập hoàn toàn, ta sử dụng `multiprocessing.Queue` 
làm "Hộp thư trung chuyển" để gửi dữ liệu giữa các Process.

Nhiệm vụ của trò trong file này:
1. Hoàn thành TODO 1: Khởi tạo 2 Process độc lập chạy 2 nhiệm vụ:
   - Process 1: Xử lý tính toán nặng (CPU-bound)
   - Process 2: Lấy kết quả từ Hộp thư Queue và in ra màn hình.
2. Trả lời câu hỏi lý thuyết ở cuối file.
3. Chạy file bằng lệnh: 
   $env:PYTHONIOENCODING="utf-8"; python EE_Mentorship/milestone_5_3_process.py
"""

import multiprocessing
import time

def heavy_calculation_process(queue: multiprocessing.Queue):
    """
    Process 1: Giả lập tính toán ma trận toán học nặng (Vắt kiệt 1 nhân CPU)
    """
    print("[PROCESS 1] Đang chạy tính toán nặng trên Nhân CPU riêng...")
    total = 0
    for i in range(10_000_000): # Chạy 10 triệu vòng lặp toán học
        total += i
    
    # Nhét kết quả vào Hộp thư Queue để gửi sang Process 2
    queue.put(f"KẾT QUẢ TÍNH TOÁN: {total}")
    print("[PROCESS 1] Đã hoàn thành và gửi thư vào Queue!")

def logger_process(queue: multiprocessing.Queue):
    """
    Process 2: Đứng ở Hộp thư chờ nhận kết quả từ Process 1
    """
    print("[PROCESS 2] Đang đứng ở Hộp thư Queue chờ dữ liệu...")
    # Lệnh queue.get() sẽ đứng chờ (blocking) cho tới khi có dữ liệu trong Queue
    msg = queue.get()
    print(f"[PROCESS 2] Đã nhận được thư từ Process 1 qua IPC: {msg}")


if __name__ == "__main__":
    # Lưu ý: Trên Windows, code Multi-processing BẮT BUỘC phải nằm dưới if __name__ == '__main__':
    # để tránh việc OS nhân bản vòng lặp khởi tạo vô hạn (Fork bomb).
    
    print("[SYSTEM] Bắt đầu khởi tạo hệ thống Đa Tiến Trình (Multi-processing)...")
    start_time = time.time()

    # 1. Tạo Hộp thư trung chuyển chung (Shared Queue)
    communication_queue = multiprocessing.Queue()

    # TODO 1: Khởi tạo 2 Process độc lập
    # Cú pháp tạo Process giống hệt Thread:
    # p1 = multiprocessing.Process(target=hàm_mục_tiêu, args=(tham_số_1,))
    p1 = multiprocessing.Process(target=heavy_calculation_process, args=(communication_queue,))
    p2 = multiprocessing.Process(target=logger_process, args=(communication_queue,))
    # Nhiệm vụ:
    # - Tạo p1 trỏ tới hàm `heavy_calculation_process`, truyền tham số `communication_queue` vào `args` (dạng tuple: (communication_queue,))
    # - Tạo p2 trỏ tới hàm `logger_process`, truyền tham số `communication_queue` vào `args`
    # - Kích hoạt cả 2 Process bằng phương thức `.start()`
    p1.start()
    p2.start()

    # Bắt Main Process phải đứng đợi p1 và p2 hoàn thành
    p1.join()
    p2.join()

    print(f"\n[SYSTEM] Hoàn thành toàn bộ hệ thống! Thời gian: {time.time() - start_time:.2f} giây")

# ================================================================================
# CÂU HỎI LÝ THUYẾT TƯ DUY (Trò hãy điền câu trả lời vào bên dưới):
#
# Hỏi: Tại sao trong Multi-processing, nếu ở Process 1 ta khai báo một biến `x = 100`,
#      sau đó ở Process 2 ta gọi `print(x)` thì chương trình lại báo lỗi biến `x` không
#      tồn tại? Bản chất vùng nhớ RAM giữa 2 Process này khác gì với 2 Thread ở bài trước?
#
# Trả lời của trò:
# > [Vì có thể vòng lặp chưa chạy xong hết 10000000 lần, nên giá trị chưa được bỏ vào queue, mà queue lại chặn dữ liệu qua Process 2, bởi vậy nên biến x chưa được khai báo ở Process 2 đâm ra lỗi]
# ================================================================================
