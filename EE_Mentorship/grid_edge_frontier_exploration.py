"""
================================================================================
          MODULE X: HARDWARE-ACCELERATED OCCUPANCY GRID & RAY-TRACING
              MILESTONE X.3: KHÁM PHÁ KHÔNG GIAN TỰ ĐỘNG (FRONTIER EXPLORATION)
================================================================================

LÀM SAO ĐỂ DRONE TỰ TÌM ĐƯỜNG KHÁM PHÁ CĂN NHÀ ĐỔ NÁT TRONG NHIỆM VỤ CỨU HỘ?
Thuật toán Frontier Exploration:
- Bản đồ chia làm 3 loại ô:
  + FREE (0): Đã đi qua, an toàn.
  + OCCUPIED (1): Bức tường, vật cản.
  + UNKNOWN (-1): Vùng tối bí ẩn chưa từng được cảm biến quét tới.
- Điểm Biên Giới (Frontier Point): Là ô FREE nằm tiếp giáp ngay cạnh ô UNKNOWN.
- Drone liên tục bay về phía Frontier gần nhất để mở rộng bản đồ cứu trợ!
"""

import numpy as np

def detect_frontier_cells(grid_map: np.ndarray):
    """
    grid_map: Ma trận 2D với các giá trị: 0 (Free), 1 (Occupied), -1 (Unknown)
    Trò đóng vai Kỹ sư Cứu hộ Robotics:
    - Tìm các ô có giá trị bằng 0 (Free)
    - Kiểm tra 4 hướng lân cận (Lên, Xuống, Trái, Phải).
    - Nếu có ít nhất 1 ô lân cận là -1 (Unknown) -> Đây chính là Frontier Cell!
    - Trả về danh sách tọa độ: [(r, c), ...]
    """
    rows, cols = grid_map.shape
    frontiers = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for r in range(rows):
        for c in range(cols):
            if grid_map[r, c] == 0:  # O Free
                for dr, dc in directions:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if grid_map[nr, nc] == -1:  # Tiep giap o chua biet
                            frontiers.append((r, c))
                            break
    return frontiers


if __name__ == "__main__":
    print("=========================================================")
    print("   OCCUPANCY MAPPING: AUTONOMOUS FRONTIER EXPLORATION")
    print("=========================================================\n")

    # Bản đồ 4x4:
    # 0 = Free, 1 = Wall, -1 = Unknown
    test_grid = np.array([
        [ 0,  0, -1, -1],
        [ 0,  1, -1, -1],
        [-1, -1, -1, -1],
        [-1, -1, -1, -1]
    ], dtype=np.int32)

    frontier_points = detect_frontier_cells(test_grid)

    print("1. KET QUA PHAT HIEN BIEN GIOI KHAM PHA (FRONTIER):")
    print(f"   -> Danh sach cac toa do bien gioi : {frontier_points}")
    print(f"   -> So luong diem bien gioi phat hien: {len(frontier_points)}")

    assert (0, 1) in frontier_points and len(frontier_points) >= 2, "Loi Frontier Detection!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN TU DONG TIM BIEN GIOI KHAM PHA CHO DRONE!")
