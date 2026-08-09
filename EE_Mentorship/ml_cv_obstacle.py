"""
================================================================================
          MODULE C: COMPUTER VISION & DEEP LEARNING (OPENCV)
              MILESTONE C.2: TỰ THIẾT KẾ BỘ PHÁT HIỆN VẬT CẢN DRONE
================================================================================

TỰ ÁP DỤNG QUY TRÌNH 5 BƯỚC THIẾT KẾ BỘ LỌC VISION TỪ CON SỐ 0:

Bài toán:
Camera Drone 100x100 chụp được một Vật cản màu Xanh Lá (Green Obstacle) ở phía trước.

Nhiệm vụ của trò trong hàm `detect_obstacle_size_and_position(bgr_image)`:
1. Lấy kênh màu Green (Cột thứ 2 trong BGR): `green_channel = bgr_image[:, :, 1]`
2. Lọc Thresholding ép các Pixel Xanh lá > 180 thành màu Trắng (255), nền Đen (0)
   bằng `cv2.threshold(green_channel, 180, 255, cv2.THRESH_BINARY)`
3. Tìm các tọa độ Pixel màu trắng bằng `np.where(mask == 255)`
4. Tính:
   - `area` = Số lượng Pixel màu trắng
   - `center_x` = Trung bình các vị trí X
   - `is_dangerous` = True nếu `area > 400` (Vật cản quá to/gần!), ngược lại False
5. Trả về: `area, center_x, is_dangerous`
"""

import numpy as np
import cv2

def create_synthetic_obstacle_frame():
    """Tạo bức ảnh giả lập Vật cản Xanh Lá (Green) lớn trước mặt Drone"""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Vẽ một vật cản chữ nhật màu Xanh lá (Blue=0, Green=255, Red=0) tại X=30..70, Y=40..80
    cv2.rectangle(img, (30, 40), (70, 80), color=(0, 255, 0), thickness=-1)
    return img

def detect_obstacle_size_and_position(bgr_image):
    """
    Trò tự tay vận dụng Quy trình 5 bước để lập trình hàm này (KHÔNG CÓ GỢI Ý CÚ PHÁP CHUYÊN SÂU):
    - Tách kênh Green
    - Lọc Threshold
    - Tìm tọa độ Pixel màu trắng
    - Tính diện tích area, tâm center_x, và cờ nguy hiểm is_dangerous
    - Trả về: area, center_x, is_dangerous
    """
    green_channel = bgr_image[:, :, 1]
    _, mask = cv2.threshold(green_channel, 180, 255, cv2.THRESH_BINARY)
    y_indices, x_indices = np.where(mask == 255)
    area = len(x_indices)
    center_x = np.mean(x_indices)
    center_y = np.mean(y_indices)
    is_dangerous = area > 400
    return area, center_x, is_dangerous


if __name__ == "__main__":
    print("=========================================================")
    print("   COMPUTER VISION: AUTOMATIC OBSTACLE AVOIDANCE SYSTEM")
    print("=========================================================\n")
    
    frame = create_synthetic_obstacle_frame()
    
    result = detect_obstacle_size_and_position(frame)
    
    if result is not None:
        area, cx, is_dangerous = result
        print(f"1. THÔNG SỐ VẬT CẢN BỊ COMPUTER VISION PHÁT HIỆN:")
        print(f"   -> Diện tích Vật cản (Area) : {area} Pixels")
        print(f"   -> Vị trí Tâm ngang (Center X): {cx:.1f}")
        
        status_text = "🚨 NGUY HIỂM: NÉ VẬT CẢN KHẨN CẤP!" if is_dangerous else "AN TOÀN 🟢"
        print(f"   -> Trạng thái Hệ thống    : {status_text}")
        
        # Kiểm tra tính chính xác
        assert area > 400 and is_dangerous == True, "Lỗi cảnh báo nguy hiểm!"
        assert abs(cx - 50.0) < 2, "Lỗi tính tâm X vật cản!"
        
        print("\n[THÀNH CÔNG] TRÒ ĐÃ TỰ TAY THIẾT KẾ BỘ LỌC TỰ ĐỘNG NÉ VẬT CẢN CHO DRONE!")
