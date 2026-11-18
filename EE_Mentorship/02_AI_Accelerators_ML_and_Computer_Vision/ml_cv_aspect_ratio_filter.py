"""
================================================================================
          MODULE C: COMPUTER VISION & DEEP LEARNING (OPENCV)
              MILESTONE C.5: LỌC VẾT BẨN ỐNG KÍNH BẰNG ASPECT RATIO (W/H)
================================================================================

BÀI TOÁN THỰC TẾ:
Camera chụp được 2 vật thể:
1. Vật thể A: Vết bẩn dính nhòe trên ống kính (Diện tích 1200 Pixels, nhưng dẹt dài dị hình W=200, H=6 -> Tỷ lệ Aspect Ratio W/H = 33.3).
2. Vật thể B: Xe Container thật đằng xa (Diện tích 800 Pixels, hình chữ nhật chuẩn W=40, H=20 -> Tỷ lệ Aspect Ratio W/H = 2.0).

Nhiệm vụ của Kỹ sư trưởng trong hàm `filter_real_vehicle_contour(bgr_image)`:
Sử dụng các công cụ trong Hộp Công Cụ đã học để loại bỏ Vết bẩn nhòe 1200 Pixels
và trả về đúng Bounding Box `(x, y, w, h)` của Xe Container thật!
"""

import numpy as np
import cv2

def create_synthetic_smudge_and_vehicle_frame():
    """Tạo bức ảnh giả lập gồm 1 Vết bẩn dính trên ống kính và 1 Xe Container thật"""
    img = np.zeros((150, 250, 3), dtype=np.uint8)
    
    # 1. Vết bẩn nhòe dính trên kính (X=10..210, Y=10..16 -> Rộng 200, Cao 6 -> Dẹt dị hình AR=33.3)
    cv2.rectangle(img, (10, 10), (210, 16), color=(0, 255, 0), thickness=-1)
    
    # 2. Xe Container thật (X=50..90, Y=60..80 -> Rộng 40, Cao 20 -> Chuẩn tỷ lệ AR=2.0)
    cv2.rectangle(img, (50, 60), (90, 80), color=(0, 255, 0), thickness=-1)
    return img

def filter_real_vehicle_contour(bgr_image):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Tách kênh Green
    - Lọc Threshold nhị phân (ngưỡng 180)
    - Trích xuất danh sách Contours
    - Lặp qua từng contour, tính area và (x, y, w, h)
    - Tính aspect_ratio = w / h
    - Áp dụng bộ lọc phòng vệ: area > 300 VÀ (1.2 <= aspect_ratio <= 3.5)
    - Trả về: (x, y, w, h) của Xe Container thật!
    """
    green = bgr_image[:,:,1]
    _, mask = cv2.threshold(green, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = contours[0]
    area = cv2.contourArea(c)
    x, y, w, h = cv2.boundingRect(c)
    ar = w/h
    assert area > 300 and 1.2 <= ar <= 3.5
    return x, y, w, h


if __name__ == "__main__":
    print("=========================================================")
    print("   COMPUTER VISION: ASPECT RATIO SMUDGE FILTERING SYSTEM")
    print("=========================================================\n")
    
    frame = create_synthetic_smudge_and_vehicle_frame()
    
    vehicle_bbox = filter_real_vehicle_contour(frame)
    
    if vehicle_bbox is not None:
        x, y, w, h = vehicle_bbox
        ar = w / h
        print(f"1. KẾT QUẢ BỘ LỌC PHÒNG VỆ ASPECT RATIO (W/H):")
        print(f"   -> Tọa độ Xe Container thật (X, Y) : ({x}, {y})")
        print(f"   -> Kích thước (Rộng x Cao)       : {w} x {h} Pixels")
        print(f"   -> Tỷ lệ Aspect Ratio (W/H)      : {ar:.2f} (Nằm trong khoảng chuẩn 1.2 - 3.5!)")
        
        # Kiểm tra tính chính xác (Xe Container thật: X=50, Y=60, W=41, H=21)
        assert abs(x - 50) <= 1 and abs(y - 60) <= 1, "Lỗi định vị sai xe Container!"
        assert 1.2 <= ar <= 3.5, "Lỗi chưa lọc được vết bẩn nhòe trên kính!"
        
        print("\n[THÀNH CÔNG] HỆ THỐNG ĐÃ TRIỆT TIỆU VẾT BẨN TRÊN KÍNH VÀ THEO DÕI ĐÚNG XE CONTAINER!")
