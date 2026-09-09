"""
================================================================================
          MODULE AC: MULTI-TARGET KALMAN TRACKING & RADAR FUSION
              MILESTONE AC.3: GHÉP CẶP ĐA MỤC TIÊU (HUNGARIAN DATA ASSOCIATION)
================================================================================

LÀM SAO ĐỂ RADAR BIẾT ĐIỂM ĐO NÀO THUỘC VỀ CON DRONE NÀO?
Khi có N quỹ đạo (Tracks) và M điểm đo mới (Detections):
- Phải ghép cặp sao cho TỔNG SAI SỐ KHOẢNG CÁCH TOÀN HỆ THỐNG LÀ NHỎ NHẤT!
- Xây dựng ma trận chi phí khoảng cách Cost Matrix C[i, j] = dist(Track_i, Detection_j).
- Thuật toán Ghép cặp tối ưu (Global Nearest Neighbor / Greedy Assignment):
  + Chọn cặp có khoảng cách nhỏ nhất trước.
  + Đảm bảo mỗi Track chỉ nhận tối đa 1 Detection, và mỗi Detection chỉ thuộc về 1 Track!
"""

import numpy as np

def assign_tracks_to_detections(tracks: list, detections: list, max_dist_threshold: float = 10.0):
    """
    Trò đóng vai Kỹ sư Ghép cặp Dữ liệu Đa Mục tiêu:
    - Tính ma trận khoảng cách Cost Matrix giữa từng track và detection
    - Dùng thuật toán Greedy GNN ghép cặp có chi phí nhỏ nhất
    - Trả về: danh sách các cặp ghép (track_idx, det_idx)
    """
    matches = []
    unmatched_tracks = set(range(len(tracks)))
    unmatched_dets = set(range(len(detections)))

    pairs = []
    for t_idx, t_pos in enumerate(tracks):
        for d_idx, d_pos in enumerate(detections):
            dist = np.linalg.norm(np.array(t_pos) - np.array(d_pos))
            if dist <= max_dist_threshold:
                pairs.append((dist, t_idx, d_idx))

    # Sắp xếp theo thứ tự khoảng cách từ nhỏ đến lớn
    pairs.sort(key=lambda x: x[0])

    for dist, t_idx, d_idx in pairs:
        if t_idx in unmatched_tracks and d_idx in unmatched_dets:
            matches.append((t_idx, d_idx))
            unmatched_tracks.remove(t_idx)
            unmatched_dets.remove(d_idx)

    return matches


if __name__ == "__main__":
    print("=========================================================")
    print("   RADAR TRACKING: MULTI-TARGET DATA ASSOCIATION")
    print("=========================================================\n")

    # 2 Drone đang bay: Drone 0 tại (10, 10), Drone 1 tại (50, 50)
    current_tracks = [(10.0, 10.0), (50.0, 50.0)]

    # Radar quét được 2 điểm đo mới: Điểm 0 tại (51.0, 49.5), Điểm 1 tại (10.5, 10.2)
    new_detections = [(51.0, 49.5), (10.5, 10.2)]

    matched_pairs = assign_tracks_to_detections(current_tracks, new_detections)

    print("1. KET QUA GHEP CAP QUY DAO VA DIEM DO RADAR:")
    for t, d in matched_pairs:
        print(f"   -> Track {t} (vi tri {current_tracks[t]}) ===> Detection {d} (vi tri {new_detections[d]})")

    # Track 0 phải ghép với Detection 1 (cùng ở tọa độ ~10, 10)
    # Track 1 phải ghép với Detection 0 (cùng ở tọa độ ~50, 50)
    assert (0, 1) in matched_pairs and (1, 0) in matched_pairs, "Loi Data Association!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN GHEP CAP DA MUC TIEU TOI UU CHO RADAR!")
