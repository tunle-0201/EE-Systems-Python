"""
================================================================================
          MODULE C: COMPUTER VISION & DEEP LEARNING (OPENCV)
              MILESTONE C.6: BỘ LỌC MÀU SẮC TRONG KHÔNG GIAN MÀU HSV (HSV RANGE)
================================================================================

TẠI SAO BGR LẠI THẤT BẠI KHI BAY NGOÀI TRỜI KHÔNG KHÍ THỰC TẾ?
Khi Drone bay ngoài trời, nắng gắt hoặc bóng râm làm cho các giá trị RGB bị thay đổi hoàn toàn.
Do đó Kỹ sư AI dùng không gian màu **HSV (Hue - Saturation - Value)**:
- H (Hue - Tông màu): Độc lập hoàn toàn với ánh sáng nắng/bóng râm!
  * Tông màu Xanh Lá (Green) nằm trong khoảng: H từ 35 đến 85.
- S (Saturation - Độ đậm màu): Từ 50 đến 255 (loại bỏ màu xám đục).
- V (Value - Độ sáng): Từ 50 đến 255 (loại bỏ bóng tối đen thui).

BÀI TOÁN THỰC TẾ:
Camera Drone bay qua một cánh đồng có bóng râm nghiêng.
Cần lọc ra đúng **Mục tiêu Xanh Lá (Green Landing Zone)** nằm trong không gian màu HSV!

Nhiệm vụ của Kỹ sư trưởng trong hàm `extract_green_target_hsv(bgr_image)`:
1. Chuyển ảnh BGR sang HSV bằng `cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)`
2. Định nghĩa ngưỡng HSV Xanh lá:
   - `lower_green = np.array([35, 50, 50])`
   - `upper_green = np.array([85, 255, 255])`
3. Lọc mặt nạ nhị phân bằng `mask = cv2.inRange(hsv_img, lower_green, upper_green)`
4. Trích xuất Contours bằng `cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)`
5. Tìm Bounding Box `(x, y, w, h)` của mục tiêu đầu tiên `contours[0]`
6. Trả về: `(x, y, w, h)`
"""

import numpy as np
import cv2

def create_synthetic_hsv_drone_frame():
    """Tạo bức ảnh giả lập Mục tiêu Xanh Lá ngoài trời"""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Vẽ mục tiêu Xanh lá (BGR: 0, 200, 0) tại X=30..70, Y=20..60 (Rộng 40, Cao 40)
    cv2.rectangle(img, (30, 20), (70, 60), color=(0, 200, 0), thickness=-1)
    return img

def extract_green_target_hsv(bgr_image):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ từ Hộp Công Cụ HSV để lập trình hàm này từ con số 0:
    - Đổi BGR sang HSV (dùng cv2.cvtColor với cv2.COLOR_BGR2HSV)
    - Tạo mảng lower_green [35, 50, 50] và upper_green [85, 255, 255]
    - Tạo mask nhị phân bằng cv2.inRange()
    - Trích xuất Contours bằng cv2.findContours()
    - Tính (x, y, w, h) của contours[0]
    - Trả về: (x, y, w, h)
    """
    
    green_hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(green_hsv, lower_green, upper_green)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area = cv2.contourArea(contours[0])
    x, y, w, h = cv2.boundingRect(contours[0])
    ar = w/h
    return x, y, w, h


if __name__ == "__main__":
    print("=========================================================")
    print("   COMPUTER VISION: HSV COLOR SPACE TARGET DETECTOR")
    print("=========================================================\n")
    
    frame = create_synthetic_hsv_drone_frame()
    
    bbox = extract_green_target_hsv(frame)
    
    if bbox is not None:
        x, y, w, h = bbox
        print(f"1. KẾT QUẢ ĐỊNH VỊ MỤC TIÊU BẰNG KHÔNG GIAN MÀU HSV:")
        print(f"   -> Tọa độ Mục tiêu (X, Y)       : ({x}, {y})")
        print(f"   -> Kích thước (Rộng x Cao)       : {w} x {h} Pixels")
        
        # Kiểm tra tính chính xác (Mục tiêu: X=30, Y=20, W=41, H=41)
        assert abs(x - 30) <= 1 and abs(y - 20) <= 1, "Lỗi định vị sai mục tiêu HSV!"
        assert abs(w - 41) <= 1 and abs(h - 41) <= 1, "Lỗi kích thước mục tiêu HSV!"
        
        print("\n[THÀNH CÔNG] HỆ THỐNG ĐÃ ĐỊNH VỊ CHÍNH XÁC MỤC TIÊU BẰNG KHÔNG GIAN MÀU HSV!")
