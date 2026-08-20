"""
================================================================================
          MODULE I: EDGE AI REAL-TIME OBJECT DETECTION & ANCHORS
              MILESTONE I.1: THUẬT TOÁN ĐO TỶ LỆ GIAO NHAU IOU (INTERSECTION OVER UNION)
================================================================================

TẠI SAO CẦN THUẬT TOÁN IOU TRONG KHAI THÁC AI THỊ GIÁC (YOLO / DETECTOR)?
Khi AI vẽ 2 khung hình chữ nhật Bounding Box xung quanh vật thể:
- Làm sao biết 2 khung đó có đang đè lên cùng 1 vật thể hay không?
- Ta dùng chỉ số **Intersection over Union (IoU)**:
  IoU = Diện tích Phần Giao nhau (Intersection) / Diện tích Phần Hợp nhất (Union)
  (Nếu IoU > 0.5 -> 2 khung đè lên cùng 1 mục tiêu!).
"""

import numpy as np

def compute_bounding_box_iou(boxA, boxB):
    """
    box = [x1, y1, x2, y2]
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ IoU từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - xA = max(boxA[0], boxB[0])
    - yA = max(boxA[1], boxB[1])
    - xB = min(boxA[2], boxB[2])
    - yB = min(boxA[3], boxB[3])
    - interArea = max(0, xB - xA) * max(0, yB - yA)
    - boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    - boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    - iou = interArea / float(boxAArea + boxBArea - interArea)
    - Trả về: iou
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    
    iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
    return iou


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI VISION: INTERSECTION OVER UNION (IOU) ENGINE")
    print("=========================================================\n")
    
    bA = [50, 50, 150, 150]
    bB = [100, 100, 200, 200] # Giao nhau ô 50x50 ở giữa
    
    iou_score = compute_bounding_box_iou(bA, bB)
    
    print("1. KET QUA DO DAC TY LE GIAO NHAU IOU REAL-TIME:")
    print(f"   -> Khung Box A       : {bA}")
    print(f"   -> Khung Box B       : {bB}")
    print(f"   -> Chi so Overlap IoU: {iou_score:.4f} ({iou_score*100:.1f}%)")
    
    assert abs(iou_score - 0.1428) < 0.01, "Loi tinh IoU!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN IOU DO CHINH XAC CHUAN XAC KHUNG ANCHOR!")
