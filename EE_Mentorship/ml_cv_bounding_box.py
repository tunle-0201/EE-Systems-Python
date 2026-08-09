"""
================================================================================
          MODULE C: COMPUTER VISION & DEEP LEARNING (OPENCV)
              MILESTONE C.3: TÌM ĐƯỜNG VIỀN CONTOUR & VẼ HỘP BOUNDING BOX
================================================================================

Trong Kỹ thuật Robotics & Xe tự lái, để theo dõi một vật thể, ta không chỉ tính
diện tích mà ta phải vẽ một **Hộp khung bao quanh (Bounding Box)** mang thông số:
- `(x, y)`: Tọa độ góc trên bên trái của Hộp
- `w`     : Chiều rộng (Width) của Hộp
- `h`     : Chiều cao (Height) của Hộp

OpenCV cung cấp hàm thần thánh: `cv2.findContours()` và `cv2.boundingRect()`

Bài toán:
Camera Drone phát hiện 1 Vật cản. Trò hãy tìm Bounding Box `(x, y, w, h)` của nó!

Nhiệm vụ của trò trong hàm `extract_obstacle_bounding_box(bgr_image)`:
1. Lấy kênh màu Green: `green = bgr_image[:, :, 1]`
2. Lọc Threshold: `_, mask = cv2.threshold(green, 180, 255, cv2.THRESH_BINARY)`
3. Trích xuất đường viền Contours: `contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)`
4. Tìm Bounding Box của đường viền lớn nhất:
   `x, y, w, h = cv2.boundingRect(contours[0])`
5. Trả về: `(x, y, w, h)`
"""

import numpy as np
import cv2

def create_synthetic_target_frame():
    """Tạo bức ảnh giả lập Mục tiêu Xanh Lá tại vị trí X=25, Y=35, Width=40, Height=30"""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Vẽ mục tiêu từ góc (25, 35) rộng 40 cao 30
    cv2.rectangle(img, (25, 35), (25 + 40, 35 + 30), color=(0, 255, 0), thickness=-1)
    return img

def extract_obstacle_bounding_box(bgr_image):
    """
    Trò tự tay lập trình hàm này (KHÔNG GỢI Ý CÚ PHÁP CHUYÊN SÂU):
    - Tách kênh Green
    - Lọc Threshold
    - Tìm Contours bằng cv2.findContours()
    - Tính Bounding Box bằng cv2.boundingRect()
    - Trả về: x, y, w, h
    """
    green_channel = bgr_image[:, :, 1]
    _, mask = cv2.threshold(green_channel, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    x, y, w, h = cv2.boundingRect(contours[0])
    return x, y, w, h


if __name__ == "__main__":
    print("=========================================================")
    print("   COMPUTER VISION: TARGET TRACKING & BOUNDING BOX DETECTOR")
    print("=========================================================\n")
    
    frame = create_synthetic_target_frame()
    
    bbox = extract_obstacle_bounding_box(frame)
    
    if bbox is not None:
        x, y, w, h = bbox
        print(f"1. THÔNG SỐ KHUNG BAO VẬT THỂ (BOUNDING BOX):")
        print(f"   -> Tọa độ góc trên bên trái (X, Y) : ({x}, {y})")
        print(f"   -> Chiều rộng x Chiều cao (W x H): {w} x {h} Pixels")
        
        # Thử nghiệm vẽ Hộp khung bao màu Xanh Dương (Blue) lên ảnh Camera UI
        annotated_frame = frame.copy()
        cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), color=(255, 0, 0), thickness=2)
        
        # Kiểm tra độ chính xác (Vị trí gốc: X=25, Y=35, W=40, H=30)
        assert abs(x - 25) <= 1 and abs(y - 35) <= 1, "Lỗi tọa độ góc Hộp!"
        assert abs(w - 41) <= 1 and abs(h - 31) <= 1, "Lỗi kích thước Hộp!"
        
        print("\n[THÀNH CÔNG] TRÒ ĐÃ TRÍCH XUẤT VÀ VẼ HỘP BOUNDING BOX THEO DÕI MỤC TIÊU!")
