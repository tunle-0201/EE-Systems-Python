"""
================================================================================
          MODULE I: EDGE AI REAL-TIME OBJECT DETECTION & ANCHORS
              MILESTONE I.2: THUẬT TOÁN KHỬ TRÙNG LẶP KHUNG NMS (NON-MAX SUPPRESSION)
================================================================================

TẠI SAO CẦN NMS TRONG MẠNG OBJECT DETECTION (YOLO / SSD)?
Khi AI quét 1 con Drone, nó phát hiện hàng chục khung Bounding Box chèn lên nhau.
Thuật toán **Non-Maximum Suppression (NMS)** giúp:
1. Giữ lại khung có Độ tin cậy (Confidence score) cao nhất.
2. Sàng lọc loại bỏ tất cả các khung xung quanh có IoU > threshold.
"""

from cv_edge_iou_calculator import compute_bounding_box_iou
import numpy as np

def apply_non_max_suppression(boxes, scores, iou_threshold=0.5):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ NMS từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Sort danh sách khung theo score từ cao xuống thấp
    - Lặp qua từng khung: Giữ lại khung cao nhất, xóa các khung có IoU > iou_threshold
    - Trả về: keep_boxes
    """
    idxs = np.argsort(scores)[::-1]
    keep = []
    
    while len(idxs) > 0:
        current = idxs[0]
        keep.append(current)
        
        remaining = []
        for i in range(1, len(idxs)):
            iou = compute_bounding_box_iou(boxes[current], boxes[idxs[i]])
            if iou < iou_threshold:
                remaining.append(idxs[i])
        idxs = np.array(remaining)
        
    return [boxes[k] for k in keep]


if __name__ == "__main__":
    print("=========================================================")
    print("   EDGE AI VISION: NON-MAXIMUM SUPPRESSION (NMS) ENGINE")
    print("=========================================================\n")
    
    box_list = [
        [50, 50, 150, 150],
        [52, 51, 149, 151], # Trùng 99% với khung 1
        [300, 300, 400, 400] # Khung vật thể khác
    ]
    score_list = [0.95, 0.80, 0.90]
    
    filtered_boxes = apply_non_max_suppression(box_list, score_list, iou_threshold=0.5)
    
    print("1. KET QUA KHU TRUNG LAP KHUNG BOUNDING BOX REAL-TIME:")
    print(f"   -> So khung ban dau: {len(box_list)}")
    print(f"   -> So khung sau NMS: {len(filtered_boxes)} (Khu sach trung lap!)")
    
    assert len(filtered_boxes) == 2, "Loi NMS Engine!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN NMS LOC NHO HIEU QUA CHO AI DETECTOR!")
