"""
================================================================================
          MODULE I CAPSTONE FINALE: BỘ NÃO DETECTOR NHẬN DIỆN MỤC TIÊU CHO DRONE
================================================================================

TÍCH HỢP TOÀN BỘ HỆ THỐNG ANCHORS + IOU + NMS FILTERING:
Tích hợp Anchor Boxes + IoU + Non-Maximum Suppression (NMS) thành Detector hoàn chỉnh.

Sơ đồ khối toàn chuỗi kiến trúc Drone YOLO Detector:

  Ảnh Camera Drone (300x300 px)
              │
              ▼
  ┌──────────────────────────────────────────────┐
  │ 1. Lưới Khung Neo (Anchor Grid Generator)    │ ──> Sinh 9 Anchor Boxes tại lưới 3x3 Grid
  └──────────────────────────────────────────────┘
              │
              ▼
  ┌──────────────────────────────────────────────┐
  │ 2. Dự đoán xác suất (Confidence Scoring)     │ ──> Gán điểm xác suất cho từng Anchor Box
  └──────────────────────────────────────────────┘
              │
              ▼
  ┌──────────────────────────────────────────────┐
  │ 3. Khử trùng lặp (IoU + NMS Suppression)     │ ──> Triệt tiêu khung đè nhau (IoU > 0.3)
  └──────────────────────────────────────────────┘
              │
              ▼
  Danh sách Mục tiêu Bounding Boxes chuẩn xác gửi tới Flight Controller điều hướng né tránh!
"""

from cv_edge_anchor_box_generator import generate_grid_anchor_boxes
from cv_edge_non_max_suppression import apply_non_max_suppression
import numpy as np

def run_yolo_drone_detector(image_dim=300):
    # 1. Tạo lưới Anchor Boxes mẫu
    anchors = generate_grid_anchor_boxes(grid_size=3, image_dim=image_dim)
    
    # 2. Giả lập kết quả dự đoán Confidence score từ mô hình AI
    scores = np.array([0.1, 0.2, 0.92, 0.15, 0.88, 0.1, 0.05, 0.02, 0.12])
    
    # 3. Lọc NMS loại bỏ khung đè nhau
    final_targets = apply_non_max_suppression(anchors.tolist(), scores.tolist(), iou_threshold=0.3)
    return len(final_targets), final_targets


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE I CAPSTONE: YOLO DRONE TARGET DETECTOR ENGINE")
    print("=========================================================\n")
    
    n_targets, targets = run_yolo_drone_detector()
    
    print("1. KET QUA HOAT DONG TOAN CHUOI DRONE TARGET DETECTOR:")
    print(f"   -> So luong Muc tieu Phat hien (Targets): {n_targets}")
    print(f"   -> Khung Target 1                      : {targets[0]}")
    
    assert n_targets >= 1, "Loi Capstone YOLO Detector Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE I: YOLO DETECTOR!")
    print("=========================================================")
