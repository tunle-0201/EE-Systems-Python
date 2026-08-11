"""
================================================================================
          MODULE C CAPSTONE FINALE: HỆ THỐNG THỊ GIÁC MÁY TÍNH DRONE HOÀN CHỈNH
================================================================================

TÍCH HỢP TẤT CẢ VŨ KHÍ OPENCV HÔM NAY VÀO DỰ ÁN TRẠM MẶT ĐẤT DRONE:

Quy trình 5 bước của Kỹ sư Thị giác máy tính (Computer Vision Engineer):
1. Chuyển BGR sang HSV: `cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)`
2. Lọc dải màu Xanh lá: `cv2.inRange(hsv, lower_green, upper_green)`
3. Tẩy rác & vá lỗ nhị phân bằng Morphology:
   - `eroded = cv2.erode(mask, kernel)`
   - `clean_mask = cv2.dilate(eroded, kernel)`
4. Trích xuất Contours của clean_mask bằng `cv2.findContours()`
5. Duyệt contours, áp dụng bộ lọc phòng vệ Aspect Ratio ($1.2 <= W/H <= 3.5$)
   để trả về Bounding Box `(x, y, w, h)` của Điểm đáp Landing Zone thực sự!

Nhiệm vụ chót của Kỹ sư trưởng (ĐẮT GIÁ NHẤT HÔM NAY):
Hoàn thành hàm `drone_autonomous_landing_vision_pipeline(bgr_image)`!
"""

import numpy as np
import cv2

def create_realworld_outdoor_drone_frame():
    """Tạo bức ảnh giả lập không khí ngoài trời phức tạp: Vết bẩn kính + Rác ti ti + Lỗ hổng bóng râm"""
    img = np.zeros((150, 250, 3), dtype=np.uint8)
    
    # 1. Vết bẩn nhòe dính trên kính (X=10..210, Y=10..15 -> Rộng 200, Cao 5 -> AR = 40.0)
    cv2.rectangle(img, (10, 10), (210, 15), color=(0, 220, 0), thickness=-1)
    
    # 2. 3 Đốm rác vụn ti ti ngoài trời
    cv2.circle(img, (15, 120), radius=1, color=(0, 255, 0), thickness=-1)
    cv2.circle(img, (230, 40), radius=1, color=(0, 255, 0), thickness=-1)
    
    # 3. Điểm đáp Landing Zone thật Xanh Lá (X=60..110, Y=50..90 -> Rộng 50, Cao 40 -> AR = 1.25)
    cv2.rectangle(img, (60, 50), (110, 90), color=(0, 255, 0), thickness=-1)
    # Lột lỗ hổng bóng râm ở giữa Điểm đáp (X=75..85, Y=65..75)
    cv2.rectangle(img, (75, 65), (85, 75), color=(0, 0, 0), thickness=-1)
    
    return img

def drone_autonomous_landing_vision_pipeline(bgr_image):
    """
    Trò tự tay vận dụng toàn bộ Hộp Công Cụ OpenCV hôm nay để lập trình hàm Capstone này từ con số 0:
    - Đổi BGR sang HSV
    - Lọc inRange màu Xanh lá ([35, 50, 50] đến [85, 255, 255])
    - Tẩy rác & vá lỗ bằng cv2.erode và cv2.dilate (kernel 5x5)
    - Trích xuất Contours bằng cv2.findContours
    - Lọc Bounding Box có area > 300 và (1.0 <= aspect_ratio <= 3.5)
    - Trả về: (x, y, w, h)
    """
    green_hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    lower = np.array([35, 50, 50])
    upper = np.array([85, 255, 255])
    mask = cv2.inRange(green_hsv, lower, upper)
    kernel = np.ones((5, 5), dtype=np.uint8)
    eroded = cv2.erode(mask, kernel, iterations=1)
    clean_mask = cv2.dilate(eroded, kernel, iterations=1)
    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        area = cv2.contourArea(c)
        if area > 300:
            x, y, w, h = cv2.boundingRect(c)
            ar = w/h
            if 1.0 <= ar <= 3.5:
                return x, y, w, h
    


if __name__ == "__main__":
    print("=========================================================")
    print("   DRONE CAPSTONE FINALE: AUTONOMOUS LANDING VISION SYSTEM")
    print("=========================================================\n")
    
    outdoor_frame = create_realworld_outdoor_drone_frame()
    
    landing_bbox = drone_autonomous_landing_vision_pipeline(outdoor_frame)
    
    if landing_bbox is not None:
        x, y, w, h = landing_bbox
        ar = w / h
        print("1. KET QUA PHAN TICH PIPELINE THI GIAC DRONE MẶT ĐẤT:")
        print(f"   -> Toa do Diem dap Landing Zone (X, Y) : ({x}, {y})")
        print(f"   -> Kich thuoc Khung bao (Rong x Cao) : {w} x {h} Pixels")
        print(f"   -> Ty le Khung hinh Aspect Ratio    : {ar:.2f}")
        
        # Kiểm tra tính chính xác (Landing Zone: X=60, Y=50, W=51, H=41)
        assert abs(x - 60) <= 1 and abs(y - 50) <= 1, "Loi dinh vi sai Landing Zone!"
        assert 1.0 <= ar <= 3.5, "Loi chua loc duoc vet ban kinh va rac hat!"
        
        print("\n=========================================================")
        print("🎉 CHUC MUNG TRO DA TOT NGHIEP MODULE C: COMPUTER VISION!")
        print("=========================================================")
