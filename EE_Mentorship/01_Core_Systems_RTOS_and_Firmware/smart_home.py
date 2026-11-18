"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 5: HƯỚNG ĐỐI TƯỢNG (OOP)
             MILESTONE 5.1: BỘ ĐIỀU KHIỂN THIẾT BỊ ĐIỆN (SMART IOT)
================================================================================

Chào trò! Trò đã nắm vững lý thuyết về Class và Instance trong RAM.
Giờ là lúc áp dụng lý thuyết đó để thiết kế một hệ thống điều khiển Smart Home thực tế.

Bài toán:
Trò cần quản lý 3 thiết bị điện trong nhà:
1. Đèn Phòng Khách (LED) - Cắm pin số 14
2. Đèn Phòng Ngủ (LED) - Cắm pin số 15
3. Quạt Thông Gió (Motor) - Cắm pin số 18

Nếu viết code tuần tự, trò sẽ phải quản lý rất nhiều biến rời rạc.
Thay vào đó, trò sẽ dùng 1 Class duy nhất tên là `IoTDevice` làm bản vẽ thiết kế chung.

Nhiệm vụ của trò trong file này:
1. Hoàn thành phương thức khởi tạo `__init__` để lưu tên, số chân pin, và trạng thái mặc định (OFF) vào RAM của từng thiết bị.
2. Hoàn thành phương thức `toggle` để bật/tắt thiết bị (nếu đang OFF thì bật thành ON, nếu ON thì tắt thành OFF).
3. Chạy file bằng lệnh: `python EE_Mentorship/smart_home.py`
"""

class IoTDevice:
    # Biến Class (nằm chung ở Master Blueprint trong RAM)
    device_count = 0 

    def __init__(self, name: str, pin: int):
        self.name = name
        self.pin = pin
        self.status = "OFF"
        IoTDevice.device_count += 1

    def get_info(self) -> str:
        """Hàm đọc thông tin từ RAM của thiết bị"""
        return f"Thiết bị: {self.name} | Chân Pin: {self.pin} | Trạng thái: {self.status}"

    def toggle(self):

        if self.status == "OFF":
            self.status = "ON"
        elif self.status == "ON":
            self.status = "OFF"
        print(f"[HỆ THỐNG] Đã chuyển {self.name} sang {self.status}")



if __name__ == "__main__":
    print("--- BẮT ĐẦU KHỞI TẠO HỆ THỐNG SMART HOME ---")
    
    # Bước 1: Sản xuất 3 linh kiện từ bản vẽ IoTDevice
    device1 = IoTDevice("Đèn Phòng Khách", 14)
    device2 = IoTDevice("Đèn Phòng Ngủ", 15)
    device3 = IoTDevice("Quạt Thông Gió", 18)
    
    # In thông tin ban đầu trong RAM
    print(device1.get_info())
    print(device2.get_info())
    print(device3.get_info())
    print(f"Tổng số thiết bị đang online: {IoTDevice.device_count}\n")
    
    print("--- MÔ PHỎNG ĐIỀU KHIỂN ---")
    # Bước 2: Bật Đèn Phòng Khách và Quạt
    device1.toggle()
    device3.toggle()
    
    # In lại thông tin để kiểm tra sự thay đổi trong RAM
    print("\n--- TRẠNG THÁI SAU KHI ĐIỀU KHIỂN ---")
    print(device1.get_info())
    print(device2.get_info()) # Đèn phòng ngủ không được bấm nên phải giữ nguyên OFF
    print(device3.get_info())
