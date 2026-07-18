"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 5: ĐA LUỒNG & ĐA TIẾN TRÌNH
                    MILESTONE 5.2: KHỞI TẠO CÔNG NHÂN (THREAD)
================================================================================

Chào trò! Trò đã hiểu lý thuyết về Thread (Luồng dùng chung RAM).
Giờ chúng ta sẽ tự tay khởi tạo các Luồng chạy song song thực tế trong OS.

Chúng ta sẽ dùng thư viện chuẩn `threading` của Python.
Cách tạo một luồng:
```python
import threading
t = threading.Thread(target=tên_hàm, args=(tham_số_1,))
t.start()  # Ra lệnh cho OS kích hoạt luồng
```

Bài toán:
Trò có 2 cảm biến:
1. Cảm biến Nhiệt độ: 2 giây gửi dữ liệu 1 lần.
2. Cảm biến Độ ẩm: 3 giây gửi dữ liệu 1 lần.
Chúng ta muốn chạy song song cả 2 cảm biến này để ghi dữ liệu vào chung 1 danh sách
`sensor_data = []` trong RAM.

Nhiệm vụ của trò trong file này:
1. Hoàn thành TODO 1: Khởi tạo và kích hoạt 2 luồng độc lập chạy song song 
   cho 2 hàm `read_temp` và `read_humid`.
2. Trả lời câu hỏi lý thuyết về xung đột bộ nhớ ở cuối file.
3. Chạy file bằng lệnh: 
   $env:PYTHONIOENCODING="utf-8"; python EE_Mentorship/milestone_5_2_thread.py
"""

import threading
import time

# Kho dữ liệu dùng chung trong RAM (Shared Memory)
sensor_data = []

# Khóa bảo vệ bộ nhớ (Lock) để tránh 2 luồng ghi đè vào RAM cùng 1 lúc
data_lock = threading.Lock()

def read_temp():
    """Luồng giả lập đọc cảm biến nhiệt độ"""
    for i in range(1000):
        #time.sleep(2)  # Chờ 2 giây (giả lập I/O cảm biến phản hồi)
        val = 25.0 + i
        
        # Dùng khóa để bảo vệ RAM trước khi ghi dữ liệu
        #with data_lock:
        sensor_data.append(f"TEMP: {val}C")
        print(f"\n[TEMP THREAD] Đã ghi TEMP: {val}C vào RAM")

def read_humid():
    """Luồng giả lập đọc cảm biến độ ẩm"""
    for i in range(1000):
       # time.sleep(3)  # Chờ 3 giây (giả lập I/O cảm biến phản hồi)
        val = 60.0 + i * 2
        
        # Dùng khóa để bảo vệ RAM trước khi ghi dữ liệu
        #with data_lock:
        sensor_data.append(f"HUMID: {val}%")
        print(f"\n[HUMID THREAD] Đã ghi HUMID: {val}% vào RAM")


if __name__ == "__main__":
    print("[SYSTEM] Bắt đầu kích hoạt hệ thống đa luồng...")
    start_time = time.time()

    # TODO 1: Khởi tạo 2 luồng riêng biệt trỏ tới 2 hàm trên
    # 1. Tạo thread_1 trỏ tới mục tiêu (target) là hàm read_temp
    # 2. Tạo thread_2 trỏ tới mục tiêu (target) là hàm read_humid
    # 3. Kích hoạt cả 2 luồng bằng phương thức .start()
    thread_1 = threading.Thread(target=read_temp)
    thread_2 = threading.Thread(target=read_humid)
    thread_1.start()
    thread_2.start()
    
    # [BẮT BUỘC] Lệnh .join() bắt Luồng chính (Main Thread) phải đứng đợi
    # cho đến khi 2 luồng phụ hoàn thành nhiệm vụ thì mới chạy tiếp code bên dưới.
    print("[SYSTEM] Đang đợi các luồng hoàn thành...")
    thread_1.join()
    thread_2.join()
    print(len(sensor_data))
    print("\n[SYSTEM] Tất cả các luồng đã hoàn thành!")
    print(f"Tổng thời gian chạy: {time.time() - start_time:.2f} giây")
    print(f"Dữ liệu cuối cùng lưu trong RAM: {sensor_data}")
    print(f"Tổng số dữ liệu: {len(sensor_data)}")
# ================================================================================
# CÂU HỎI LÝ THUYẾT SINH TỬ (Trò hãy gõ câu trả lời vào bên dưới):
#
# Hỏi: Trò hãy chú ý biến `data_lock = threading.Lock()`. Tại sao khi các luồng dùng
#      chung một vùng nhớ RAM (danh sách `sensor_data`), ta lại cần dùng khối lệnh 
#      `with data_lock:` trước khi gọi lệnh `.append()`? 
#      Chuyện gì sẽ xảy ra nếu 2 luồng cùng ghi dữ liệu vào đúng 1 ô nhớ RAM ở cùng 
#      một phần triệu giây (Microsecond)? (Hiện tượng này gọi là Race Condition).
#
# Trả lời của trò:
# > [vì bội của 2 và 3 sẽ còn nhiều lần gặp nhau, bởi vậy khả năng 2 thông tin được đè lên một địa chỉ trên RAM là có thể xảy ra, dẫn đến mất dữ liệu]
# ================================================================================
