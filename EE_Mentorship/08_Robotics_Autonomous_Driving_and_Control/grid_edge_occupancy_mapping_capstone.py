"""
================================================================================
          MODULE X CAPSTONE FINALE: HỆ THỐNG BẢN ĐỒ LƯỚI TỰ HÀNH CHO XE TESLA/DRONE
================================================================================

TÍCH HỢP TOÀN BỘ OCCUPANCY GRID STACK: BRESENHAM RAYCAST + LOG-ODDS + FRONTIER DETECT
"""

from grid_edge_bresenham_raycast import bresenham_raycast_2d
from grid_edge_log_odds_update import update_cell_log_odds, log_odds_to_probability
from grid_edge_frontier_exploration import detect_frontier_cells
import numpy as np

def run_occupancy_grid_mapping_engine():
    # 1. Khởi tạo bản đồ Log-Odds 5x5
    log_odds_map = np.zeros((5, 5), dtype=np.float32)

    # 2. Drone ở (0, 0) bắn tia trúng vật cản ở (3, 0)
    free_cells, hit_cell = bresenham_raycast_2d(0, 0, 3, 0)

    # 3. Cập nhật Log-Odds cho các ô trống
    for r, c in free_cells:
        log_odds_map[r, c] = update_cell_log_odds(log_odds_map[r, c], is_occupied_observation=False)

    # 4. Cập nhật Log-Odds cho ô va chạm
    log_odds_map[hit_cell[0], hit_cell[1]] = update_cell_log_odds(
        log_odds_map[hit_cell[0], hit_cell[1]], is_occupied_observation=True
    )

    # 5. Phân loại trạng thái ô để tìm Frontier
    state_grid = np.full((5, 5), -1, dtype=np.int32)
    for r in range(5):
        for c in range(5):
            prob = log_odds_to_probability(log_odds_map[r, c])
            if prob > 0.6:
                state_grid[r, c] = 1   # Occupied
            elif prob < 0.45:
                state_grid[r, c] = 0   # Free

    frontiers = detect_frontier_cells(state_grid)
    return len(free_cells), frontiers


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE X CAPSTONE: FULL OCCUPANCY GRID MAPPING ENGINE")
    print("=========================================================\n")

    num_free, frontiers = run_occupancy_grid_mapping_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI OCCUPANCY GRID ENGINE:")
    print(f"   -> So o trong duoc giai phong  : {num_free} cells")
    print(f"   -> So diem bien gioi can kham pha: {len(frontiers)} frontiers")
    print(f"   -> Toa do bien gioi dau tien      : {frontiers[0]}")

    assert num_free == 3 and len(frontiers) > 0, "Loi Capstone Occupancy Mapping!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP MODULE X: OCCUPANCY GRID MAPPING!")
    print("=========================================================")
