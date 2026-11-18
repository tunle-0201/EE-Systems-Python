"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 5: HƯỚNG ĐỐI TƯỢNG (OOP)
             MILESTONE 5.2: TÍNH KẾ THỪA VÀ ĐIỀU RỘNG XUNG (PWM)
================================================================================

Chào trò! Mạch điều khiển Smart Home cơ bản đã thông suốt.
Bây giờ, chúng ta nâng cấp hệ thống bằng một khái niệm cực mạnh trong OOP: **Tính Kế Thừa (Inheritance)**.

Tình huống thực tế (Tư duy EE):
*   Một cái đèn LED thông thường chỉ có 2 trạng thái: ON/OFF.
*   Nhưng trò muốn dùng một chiếc **Đèn LED điều chỉnh độ sáng (Dimmable LED)**.
    Trong kỹ thuật điện, để đổi độ sáng đèn, ta dùng phương pháp **PWM (Pulse Width Modulation - Điều rộng xung)**
    bằng cách thay đổi Duty Cycle (chu kỳ hoạt động) từ 0% đến 100%.

Thay vì viết lại một Class mới từ đầu, ta sẽ tạo Class `DimmableLED` **kế thừa** mọi thuộc tính 
của `IoTDevice` (như name, pin, status), và chỉ cần bổ sung thêm các tính năng điều xung PWM.

Nhiệm vụ của trò trong file này:
1. Hoàn thành phương thức khởi tạo `__init__` của `DimmableLED`:
   - Sử dụng lệnh `super().__init__(...)` để gọi hàm khởi tạo của Class cha (`IoTDevice`), 
     giúp trò không phải gõ lại việc lưu `name` và `pin`.
   - Khởi tạo thêm một biến thực thể mới lưu trong RAM: `self.brightness` (độ sáng) mặc định là `0` (%).
2. Hoàn thành phương thức `set_brightness(level)`:
   - Nhận vào `level` (số nguyên từ 0 đến 100).
   - Dùng hàm kẹp biên `max()` và `min()` để đảm bảo `level` luôn nằm trong khoảng `[0, 100]`.
   - Ghi đè trạng thái `self.status`: nếu độ sáng > 0 thì tự động chuyển thành "ON", nếu độ sáng = 0 thì tự động chuyển thành "OFF".
3. Hoàn thành ghi đè (override) phương thức `get_info()` để in ra thêm thông số độ sáng của đèn.
4. Chạy file bằng lệnh: `python EE_Mentorship/smart_home_inheritance.py`
"""

class IoTDevice:
    """Class Cha (Base Class) đại diện cho thiết bị ON/OFF cơ bản"""
    def __init__(self, name: str, pin: int):
        self.name = name
        self.pin = pin
        self.status = "OFF"

    def get_info(self) -> str:
        return f"Thiết bị: {self.name} | Pin: {self.pin} | Trạng thái: {self.status}"

    def toggle(self):
        if self.status == "OFF":
            self.status = "ON"
        else:
            self.status = "OFF"
        print(f"[HỆ THỐNG] Đã chuyển {self.name} sang {self.status}")


# ================================================================================
# CLASS CON (Subclass) - KẾ THỪA TỪ IoTDevice
# ================================================================================
class DimmableLED(IoTDevice):
    def __init__(self, name: str, pin: int):
        super().__init__(name, pin)
        self.brightness = 0

    def set_brightness(self, level: int):
        self.brightness = max(0, min(level, 100))
        if self.brightness > 0:
            self.status = "ON"
        elif self.brightness == 0:
            self.status = "OFF"
        print(f"[PWM] Đèn {self.name} set độ sáng: {self.brightness}% (Trạng thái: {self.status})")
  

    def get_info(self) -> str:
        parent_info = super().get_info() 
        return parent_info + f" | Độ sáng: {self.brightness}%" 


if __name__ == "__main__":
    print("--- KHỞI TẠO ĐÈN LED ĐIỀU XUNG (PWM) ---")
    
    # Tạo thực thể đèn ngủ có điều chỉnh độ sáng cắm pin 15
    dim_led = DimmableLED("Đèn Ngủ Dimmable", 15)
    print(dim_led.get_info())  # Ban đầu phải là 0% độ sáng và OFF
    
    print("\n--- ĐIỀU CHỈNH ĐỘ SÁNG ---")
    dim_led.set_brightness(50)  # Bật sáng 50%
    print(dim_led.get_info())
    
    dim_led.set_brightness(150) # Thử chỉnh quá lố 150% -> hệ thống phải tự kẹp về 100%
    print(dim_led.get_info())
    
    dim_led.set_brightness(0)   # Tắt hẳn về 0%
    print(dim_led.get_info())
