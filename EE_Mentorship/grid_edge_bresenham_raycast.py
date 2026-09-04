"""
================================================================================
          MODULE X: HARDWARE-ACCELERATED OCCUPANCY GRID & RAY-TRACING
              MILESTONE X.1: THUẬT TOÁN BẮN TIA KHÔNG GIAN (BRESENHAM 2D/3D RAY-CASTING)
================================================================================

TẠI SAO CÁC XE TESLA FSD VÀ DRONE CẦN THUẬT TOÁN BẮN TIA RAY-CASTING SIÊU TỐC?
Cảm biến LiDAR / Radar đo khoảng cách từ Drone đến vật cản:
- Mọi ô lưới (Grid Cell) nằm giữa Drone và vật cản là VÙNG KHÔNG GIAN TRỐNG (Free Space).
- Ô lưới tại điểm va chạm là VÙNG BỊ CHIẾM CHỖ (Occupied Space).
- Thuật toán Bresenham: Chỉ dùng phép cộng và trừ số nguyên (Integer Only),
  tốc độ cực nhanh trên vi xử lý nhúng mà không tốn phép chia số thực!
"""

def bresenham_raycast_2d(x0: int, y0: int, x1: int, y1: int):
    """
    Trò đóng vai Kỹ sư Xử lý Bản đồ Xe tự hành:
    - Bắn tia từ tọa độ Drone (x0, y0) tới điểm phản xạ (x1, y1)
    - Trả về danh sách các ô trống (free_cells) và ô vật cản (hit_cell)
    """
    cells = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    curr_x, curr_y = x0, y0
    while True:
        cells.append((curr_x, curr_y))
        if curr_x == x1 and curr_y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            curr_x += sx
        if e2 < dx:
            err += dx
            curr_y += sy

    free_cells = cells[:-1]  # Các ô trống giữa đường
    hit_cell = cells[-1]     # Ô va chạm vật cản
    return free_cells, hit_cell


if __name__ == "__main__":
    print("=========================================================")
    print("   OCCUPANCY MAPPING: BRESENHAM INTEGER RAY-CASTING")
    print("=========================================================\n")

    # Drone ở tọa độ (0, 0), chùm tia LiDAR bắn trúng bức tường ở (4, 2)
    free, hit = bresenham_raycast_2d(0, 0, 4, 2)

    print("1. KET QUA BAN TIA KHONG GIAN BRESENHAM TREN BAN DO LUOI:")
    print(f"   -> Toa do Drone xuat phat : (0, 0)")
    print(f"   -> Diem va cham vat can   : {hit}")
    print(f"   -> Cac o khong gian trong : {free}")
    print(f"   -> So o trong duoc xac nhan: {len(free)} cells")

    assert hit == (4, 2) and (0, 0) in free and len(free) >= 4, "Loi Bresenham Raycast!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN BAN TIA KHONG GIAN INTEGER BRESENHAM!")
