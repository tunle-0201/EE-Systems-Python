"""
================================================================================
          MODULE I: EDGE AI REAL-TIME OBJECT DETECTION & ANCHORS
              MILESTONE I.3: TẠO LƯỚI KHUNG NEO ANCHOR BOX GRID ENGINE
================================================================================

TẠI SAO CẦN LƯỚI KHUNG NEO ANCHOR BOXES TRONG YOLO / SSD?
Thuật toán AI chia khung hình thành lưới Grid (ví dụ $7 \times 7$ hoặc $13 \times 13$):
- Tại mỗi ô lưới, AI chuẩn bị sẵn 3 hoặc 5 khung mẫu (Anchor Boxes) với các tỷ lệ Aspect Ratio khác nhau ($1:1, 1:2, 2:1$).
- AI chỉ cần dự đoán độ lệch $\Delta x, \Delta y, \Delta w, \Delta h$ so với Anchor Box mẫu!
"""

import numpy as np

def generate_grid_anchor_boxes(grid_size=3, image_dim=300):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Anchor Grid từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - stride = image_dim / grid_size
    - Lặp cx từ 0..grid_size, cy từ 0..grid_size:
      + x_ctr = (cx + 0.5) * stride
      + y_ctr = (cy + 0.5) * stride
      + anchors.append([x_ctr - 25, y_ctr - 25, x_ctr + 25, y_ctr + 25])
    - Trả về: anchors
    """
    stride = image_dim / grid_size
    anchors = []
    for cy in range(grid_size):
        for cx in range(grid_size):
            x_ctr = (cx + 0.5) * stride
            y_ctr = (cy + 0.5) * stride
            anchors.append([x_ctr - 25, y_ctr - 25, x_ctr + 25, y_ctr + 25])
    return np.array(anchors)


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI VISION: ANCHOR BOX GRID GENERATOR ENGINE")
    print("=========================================================\n")
    
    anchors_grid = generate_grid_anchor_boxes(grid_size=3, image_dim=300)
    
    print("1. KET QUA TAO LUOI KHUNG NEO ANCHOR BOXES:")
    print(f"   -> Tong so Anchor Boxes tao ra: {len(anchors_grid)}")
    print(f"   -> Toa do Khung Neo 1 (Center) : {anchors_grid[0]}")
    
    assert len(anchors_grid) == 9, "Loi Anchor Box Generator!"
    print("\n[THANH CONG] DA TAO THONG SUOT LUOI ANCHOR BOXES DANG CHUAN YOLO!")
