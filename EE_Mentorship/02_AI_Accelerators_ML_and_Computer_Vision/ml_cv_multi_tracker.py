"""
================================================================================
          MODULE C: COMPUTER VISION & DEEP LEARNING (OPENCV)
              MILESTONE C.4: LỌC NHIỄU VÀ THEO DÕI NHIỀU VẬT CẢN (MULTI-TARGET)
================================================================================

Tình huống thực tế của Camera Drone ngoài trời:
1. Ảnh bị NHIỄU HẠT (Dust/Sensor Noise): Nhiều đốm nhỏ lấm chấm xuất hiện.
   -> Cần dùng Mạch lọc mờ **Gaussian Blur (`cv2.GaussianBlur`)** để triệt tiêu nhiễu trước khi Threshold!
2. Có NHIỀU VẬT CẢN CÙNG LÚC trên màn hình:
   -> Cần lọc bỏ các vết đốm nhỏ (Diện tích < 100 pixels).
   -> Tìm ra **VẬT CẢN LỚN NHẤT** để điều khiển Drone né tránh!

Bài toán:
Camera Drone chụp được bức ảnh chứa 3 vết sáng (2 đốm rác nhỏ và 1 Vật cản chính lớn).

Nhiệm vụ của trò trong hàm `track_largest_obstacle(bgr_image)`:
1. Lấy kênh màu Green: `bgr_image[:, :, 1]`
2. Đưa qua mạch lọc mờ Gaussian Blur kích thước 5x5 để khử nhiễu: `cv2.GaussianBlur(green, (5, 5), 0)`
3. Lọc Threshold nhị phân với ngưỡng 180
4. Trích xuất danh sách các đường viền Contours bằng `cv2.findContours()`
5. Lặp qua tất cả các contours để tìm ra contour có Diện tích lớn nhất bằng `cv2.contourArea(c)`
6. Tính Bounding Box `(x, y, w, h)` của contour lớn nhất đó!
7. Trả về: `(x, y, w, h, max_area)`
"""

import numpy as np
import cv2

def create_synthetic_multi_obstacle_frame():
    """Tạo bức ảnh giả lập gồm 2 đốm rác nhỏ và 1 Vật cản chính lớn"""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # 2 đốm rác nhiễu nhỏ (Diện tích < 50 pixels)
    cv2.circle(img, (15, 15), radius=2, color=(0, 255, 0), thickness=-1)
    cv2.circle(img, (85, 20), radius=3, color=(0, 255, 0), thickness=-1)
    
    # 1 Vật cản chính lớn tại X=40..70, Y=50..80 (Diện tích > 500 pixels)
    cv2.rectangle(img, (40, 50), (70, 80), color=(0, 255, 0), thickness=-1)
    return img

def track_largest_obstacle(bgr_image):
    """
    Trò tự tay vận dụng tư duy Kỹ sư lập trình hàm này (KHÔNG CÓ GỢI Ý CÚ PHÁP TRONG COMMENT):
    - Tách kênh Green
    - Lọc mờ khử nhiễu bằng cv2.GaussianBlur()
    - Lọc Threshold bằng cv2.threshold()
    - Trích xuất Contours bằng cv2.findContours()
    - Tìm contour có diện tích lớn nhất (dùng cv2.contourArea)
    - Tính x, y, w, h của contour lớn nhất (dùng cv2.boundingRect)
    - Trả về: x, y, w, h, max_area
    """
    green_channel = bgr_image[:, :, 1]
    blurred = cv2.GaussianBlur(green_channel, (5, 5), 0)
    _, mask = cv2.threshold(blurred, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    x, y, w, h = cv2.boundingRect(contours[0])
    max_area = cv2.contourArea(contours[0])
    return x, y, w, h, max_area


if __name__ == "__main__":
    print("=========================================================")
    print("   COMPUTER VISION: MULTI-TARGET & NOISE FILTERING SYSTEM")
    print("=========================================================\n")
    
    frame = create_synthetic_multi_obstacle_frame()
    
    result = track_largest_obstacle(frame)
    
    if result is not None:
        x, y, w, h, max_area = result
        print(f"1. KẾT QUẢ LỌC NHIỄU VÀ THEO DÕI VẬT CẢN LỚN NHẤT:")
        print(f"   -> Tọa độ Hộp bao Bounding Box (X, Y) : ({x}, {y})")
        print(f"   -> Chiều rộng x Chiều cao (W x H)    : {w} x {h} Pixels")
        print(f"   -> Diện tích Vật cản chính (Area)   : {max_area:.0f} Pixels (Đã lọc sạch đốm rác!)")
        
        # Kiểm tra tính chính xác (Vật cản chính: X=40, Y=50, W=31, H=31)
        assert abs(x - 40) <= 1 and abs(y - 50) <= 1, "Lỗi định vị góc vật cản chính!"
        assert max_area > 500, "Lỗi tính diện tích vật cản chính!"
        
        print("\n[THÀNH CÔNG] DRONE ĐÃ LỌC SẠCH RÁC VÀ THEO DÕI ĐÚNG MỤC TIÊU LỚN NHẤT!")
