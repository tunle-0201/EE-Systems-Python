"""
================================================================================
          MODULE C: COMPUTER VISION & DEEP LEARNING (OPENCV)
              MILESTONE C.7: PHÉP TOÁN HÌNH THÁI HỌC BÀO MÒN & NỞ RỘNG (ERODE & DILATE)
================================================================================

TẠI SAO CẦN PHÉP TOÁN HÌNH THÁI HỌC (MORPHOLOGICAL OPERATIONS)?
Sau khi qua lọc HSV hay Threshold, bức ảnh nhị phân `mask` thường gặp 2 căn bệnh:
1. Bị dính các hạt rác ti ti (Noise points) nát vụn xung quanh.
2. Vật thể chính bị lủng lỗ rỗng rách ở giữa (Holes).

KỸ SƯ AI DÙNG BỘ ĐÔI HÌNH THÁI HỌC ĐỂ TẨY RÁC & VÁ LỖ:
- `cv2.erode(mask, kernel)`: Bào mòn tẩy sạch 100% các đốm rác hạt bụi vụn ti ti.
- `cv2.dilate(eroded, kernel)`: Nở rộng lấp kín 100% các lỗ hổng rách trong lòng vật thể.

BÀI TOÁN THỰC TẾ:
Camera Drone phát hiện 1 Vật cản chính (bị lủng vài lỗ ở giữa) và 5 đốm rác vụn ti ti.

Nhiệm vụ của Kỹ sư trưởng trong hàm `clean_mask_morphology(mask_image)`:
1. Tạo ma trận Kernel 5x5: `kernel = np.ones((5, 5), dtype=np.uint8)`
2. Bào mòn tẩy rác: `eroded = cv2.erode(mask_image, kernel, iterations=1)`
3. Nở rộng vá lỗ: `clean_mask = cv2.dilate(eroded, kernel, iterations=1)`
4. Trích xuất Contours của clean_mask bằng `cv2.findContours()`
5. Tính Bounding Box `(x, y, w, h)` của contours[0] (Vật cản chính sau khi đã tẩy sạch rác và vá lỗ!)
6. Trả về: `(x, y, w, h)`
"""

import numpy as np
import cv2

def create_noisy_and_holed_drone_frame():
    """Tạo bức ảnh nhị phân giả lập gồm 5 đốm rác vụn và 1 Vật cản chính bị lủng lỗ"""
    mask = np.zeros((100, 100), dtype=np.uint8)
    
    # 1. 5 đốm rác hạt ti ti (1x1 pixels)
    mask[10, 10] = 255
    mask[15, 80] = 255
    mask[85, 20] = 255
    mask[90, 90] = 255
    mask[5, 50] = 255
    
    # 2. Vật cản chính tại X=30..70, Y=40..80
    mask[40:80, 30:70] = 255
    # Tạo lỗ hổng lủng ở giữa vật cản chính (X=45..55, Y=55..65)
    mask[55:65, 45:55] = 0
    return mask

def clean_mask_morphology(mask_image):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Morphology từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Tạo kernel ma trận np.ones((5, 5), dtype=np.uint8)
    - Tẩy rác bằng cv2.erode()
    - Vá lỗ bằng cv2.dilate()
    - Trích xuất Contours bằng cv2.findContours()
    - Tính (x, y, w, h) của contours[0]
    - Trả về: (x, y, w, h)
    """
    kernel = np.ones((5, 5), dtype=np.uint8)
    eroded = cv2.erode(mask_image, kernel, iterations=1)
    clean_mask = cv2.dilate(eroded, kernel, iterations=1)
    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = contours[0]
    x, y, w, h = cv2.boundingRect(c)
    return x, y, w, h


if __name__ == "__main__":
    print("=========================================================")
    print("   COMPUTER VISION: MORPHOLOGY NOISE & HOLE CLEANING")
    print("=========================================================\n")
    
    dirty_mask = create_noisy_and_holed_drone_frame()
    
    bbox = clean_mask_morphology(dirty_mask)
    
    if bbox is not None:
        x, y, w, h = bbox
        print("1. KET QUA TAY RAC VA VA LO BANG PHEOP TOAN HINH THAI HOC:")
        print(f"   -> Toa do Vat can chinh (X, Y)   : ({x}, {y})")
        print(f"   -> Kich thuoc (Rong x Cao)       : {w} x {h} Pixels")
        
        # Kiểm tra tính chính xác (Vật cản chính: X=30, Y=40, W=40, H=40)
        assert abs(x - 30) <= 1 and abs(y - 40) <= 1, "Loi chua tay sach rac hat!"
        assert abs(w - 40) <= 1 and abs(h - 40) <= 1, "Loi chua va kin lo lung vat the!"
        
        print("\n[THANH CONG] HE THONG DA TAY SACH RAC HAT VA VA KIN LO LUNG VAT THE!")
