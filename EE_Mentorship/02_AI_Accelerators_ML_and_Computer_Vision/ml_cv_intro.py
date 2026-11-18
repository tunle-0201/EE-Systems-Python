"""
================================================================================
          MODULE C: COMPUTER VISION & DEEP LEARNING (OPENCV)
              MILESTONE C.1: XỬ LÝ ẢNH CAMERA DRONE DẠNG MA TRẬN 3D
================================================================================

Bản chất của Hình ảnh / Camera dưới thanh RAM:
Một bức ảnh KHÔNG PHẢI là phép thuật. Nó là một Ma trận NumPy 3 chiều (3D Tensor):
- Chiều 1: Chiều cao (Height - số lượng Pixel hàng)
- Chiều 2: Chiều rộng (Width - số lượng Pixel cột)
- Chiều 3: 3 Màu (Color Channels: BGR - Blue, Green, Red trong OpenCV)

Mỗi Pixel chứa giá trị từ 0 (Tối thui) đến 255 (Sáng cực đại).

Bài toán:
Máy bay Drone chụp được một bức ảnh Camera 100x100 Pixels.
Trong ảnh có một **Điểm đápLanding Pad màu đỏ sáng** (High Red Intensity).

Nhiệm vụ của trò:
1. Chuyển đổi bức ảnh BGR 3D thành Ảnh xám Grayscale 2D bằng `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)`.
2. Tạo Mạch lọc Thresholding để lọc ra các Pixel có độ sáng > 200 bằng `cv2.threshold()`.
3. Tìm tọa độ Tâm (X, Y) của Điểm đáp Landing Pad!
"""

import numpy as np
import cv2

def create_synthetic_drone_camera_frame():
    """Tạo bức ảnh giả lập 100x100 Pixels từ Camera Drone trong RAM"""
    # Khởi tạo ảnh màu đen (100x100x3 bytes)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Vẽ một Landing Pad tròn màu đỏ sáng tại tọa độ Tâm (X=70, Y=30)
    # Trong OpenCV màu đỏ là (Blue=0, Green=0, Red=255)
    cv2.circle(img, (70, 30), radius=10, color=(0, 0, 255), thickness=-1)
    return img

def detect_landing_pad_center(bgr_image):
    """
    Trò tự tay viết 3 dòng code Computer Vision:
    1. Chuyển bgr_image thành ảnh xám bằng cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    2. Lọc Threshold: _, mask = cv2.threshold(gray_img, 200, 255, cv2.THRESH_BINARY)
    3. Tìm tọa độ các Pixel màu trắng: y_indices, x_indices = np.where(mask == 255)
    - Trả về: center_x, center_y (Lấy trung bình của x_indices và y_indices)
    """
    bgr_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(bgr_image, 200, 255, cv2.THRESH_BINARY)
    y_indices, x_indices = np.where(mask == 255)
    center_x = np.mean(x_indices)
    center_y = np.mean(y_indices)
    return center_x, center_y



if __name__ == "__main__":
    print("=========================================================")
    print("   COMPUTER VISION: DRONE CAMERA LANDING PAD DETECTOR")
    print("=========================================================\n")
    
    frame = create_synthetic_drone_camera_frame()
    
    print(f"1. Kích thước bức ảnh Camera RAM (Shape): {frame.shape}")
    print(f"   -> 100 Pixels Cao x 100 Pixels Rộng x 3 Kênh màu BGR\n")
    
    center = detect_landing_pad_center(frame)
    
    if center is not None:
        cx, cy = center
        print(f"2. KẾT QUẢ COMPUTER VISION QUAN SÁT TỪ TRÊN CAO:")
        print(f"   -> Đã phát hiện Landing Pad tại Tọa độ Camera: X = {cx:.1f}, Y = {cy:.1f}")
        
        # Kiểm tra tính chính xác (Tâm thực tế là X=70, Y=30)
        assert abs(cx - 70) < 2 and abs(cy - 30) < 2, "Lỗi định vị tọa độ!"
        print("\n[THÀNH CÔNG] DRONE ĐÃ ĐỊNH VỊ CHÍNH XÁC ĐIỂM ĐÁP THÔNG QUA AI VISION!")
