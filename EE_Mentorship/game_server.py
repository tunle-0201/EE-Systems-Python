"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 3: TẦNG SOCKET & BYTES
             MILESTONE 3.3: DỰ ÁN GAME MULTIPLAYER "DUNGEON CRAWLER"
                       PART 1: GAME SERVER (MÁY CHỦ)
================================================================================

Chào mừng trò đến với Đấu Trường Hầm Ngục (Dungeon Arena)!
Chúng ta sẽ viết một máy chủ chạy Game Online bằng TCP Socket. 

Nguyên lý hoạt động:
1. Nhiều người chơi (Clients) kết nối tới Server.
2. Bản đồ game là một lưới tọa độ 2D kích thước 5x5.
3. Người chơi gửi các lệnh di chuyển dưới dạng Bytes:
   - "join:tên" (Ví dụ: "join:Tuan")
   - "move:w" (đi lên), "move:s" (đi xuống), "move:a" (sang trái), "move:d" (sang phải)
4. Mỗi khi có ai di chuyển, Server sẽ cập nhật vị trí của họ trong RAM (sử dụng Dict),
   vẽ lại bản đồ dạng text, và "bắn" (broadcast) bản đồ mới này đến TẤT CẢ người chơi đang online.

Nhiệm vụ của trò trong file này:
1. Hoàn thành TODO 1: Hàm `broadcast` - gửi một chuỗi tin nhắn tới tất cả người chơi.
2. Hoàn thành TODO 2: Cập nhật tọa độ (x, y) của người chơi trong hàm `process_move` 
   dựa trên các phím w, a, s, d và giới hạn lưới từ 0 đến 4 (không cho đi ra ngoài map).
3. Chạy Server: `python EE_Mentorship/game_server.py`
"""

import asyncio

HOST = "127.0.0.1"
PORT = 9999

# Bản đồ 5x5
MAP_SIZE = 5

# Quản lý người chơi trong RAM (State)
# Cấu trúc: { client_address: { "name": "Tuan", "x": 0, "y": 0, "char": "T", "writer": writer } }
players = {}

async def broadcast(message: str):
    """
    TODO 1: Gửi tin nhắn tới tất cả người chơi đang online.
    Cách làm: 
    1. Duyệt qua danh sách người chơi trong dict `players`.
    2. Với mỗi player, lấy đối tượng `writer` (dùng để gửi dữ liệu về socket).
    3. Chuyển `message` thành bytes (encode) và ghi vào `writer` bằng `writer.write(...)`.
    4. Gọi `await writer.drain()` để đẩy dữ liệu đi qua cáp mạng.
    
    Hãy viết logic này thay thế cho pass dưới đây.
    """
    for adr, player in players.items():
        writer = player['writer']
        writer.write(message.encode())
        await writer.drain()
        

def render_map() -> str:
    """Vẽ bản đồ dạng text gửi cho người chơi"""
    # Khởi tạo bản đồ trống với các dấu chấm đại diện cho đất cát "."
    grid = [["." for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
    
    # Đặt ký tự của người chơi vào tọa độ tương ứng trên lưới
    for addr, player in players.items():
        x, y = player["x"], player["y"]
        grid[y][x] = player["char"]  # y đại diện cho hàng (row), x đại diện cho cột (col)
        
    # Nối lưới thành chuỗi văn bản
    map_str = "\n--- DUNGEON MAP ---\n"
    for row in grid:
        map_str += " ".join(row) + "\n"
    map_str += "-------------------\n"
    return map_str

def process_move(addr: tuple, direction: str):
    """
    TODO 2: Cập nhật tọa độ (x, y) của người chơi dựa trên hướng di chuyển.
    Tọa độ gốc (0, 0) nằm ở góc TRÊN CÙNG BÊN TRÁI bản đồ.
    - Hướng 'w' (Lên): giảm y đi 1 đơn vị.
    - Hướng 's' (Xuống): tăng y lên 1 đơn vị.
    - Hướng 'a' (Trái): giảm x đi 1 đơn vị.
    - Hướng 'd' (Phải): tăng x lên 1 đơn vị.
    
    Yêu cầu:
    1. Thay đổi y và x của `players[addr]["x"]` và `players[addr]["y"]` tương ứng.
    2. Sử dụng hàm `max()` và `min()` để đảm bảo tọa độ luôn nằm trong khoảng [0, MAP_SIZE - 1] (0 đến 4).
       Không cho người chơi đi xuyên tường ra khỏi bản đồ!
       Ví dụ giữ x trong biên: new_x = max(0, min(current_x + delta, MAP_SIZE - 1))
    
    Hãy viết logic này thay thế cho pass dưới đây.
    """
    player = players[addr]
    current_x = player["x"]
    current_y = player["y"]
    new_x = current_x
    new_y = current_y
    if direction == "w":
        new_y = current_y - 1
    elif direction == "s":
        new_y = current_y + 1
    elif direction == "a":
        new_x = current_x - 1
    elif direction == "d":
        new_x = current_x + 1
    
    player["x"] = max(0, min(new_x, MAP_SIZE - 1))
    player["y"] = max(0, min(new_y, MAP_SIZE - 1))

async def handle_player(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    print(f"[SYSTEM] Kết nối mới từ địa chỉ vật lý: {addr}")
    
    try:
        # Gửi lời chào khi người chơi mới kết nối
        welcome_msg = "WELCOME: Nhập lệnh 'join:Tên_Của_Bạn' để tham gia chiến trường!\n"
        writer.write(welcome_msg.encode())
        await writer.drain()
        
        while True:
            # Chờ nhận lệnh từ người chơi
            data = await reader.read(1024)
            if not data:
                break  # Người chơi tắt kết nối
                
            command = data.decode().strip()
            
            # Xử lý lệnh đăng ký tham gia game: "join:Tên"
            if command.startswith("join:") and addr not in players:
                name = command.split(":")[1][:10] # Lấy tên, giới hạn 10 ký tự
                char = name[0].upper() # Lấy chữ cái đầu làm ký tự đại diện trên map
                
                # Cấp phát bộ nhớ cho người chơi mới tại tọa độ (0, 0)
                players[addr] = {
                    "name": name,
                    "x": 0,
                    "y": 0,
                    "char": char,
                    "writer": writer
                }
                
                join_announcement = f"\n[GAME] Anh hùng {name} ({char}) đã bước vào hầm ngục!\n"
                await broadcast(join_announcement + render_map())
                
            # Xử lý lệnh di chuyển: "move:hướng" (w/a/s/d)
            elif command.startswith("move:") and addr in players:
                direction = command.split(":")[1].lower()
                player_name = players[addr]["name"]
                
                # Tính toán tọa độ mới
                process_move(addr, direction)
                
                move_announcement = f"\n[GAME] {player_name} di chuyển hướng '{direction}'\n"
                await broadcast(move_announcement + render_map())
                
    except Exception as e:
        print(f"[ERR] Lỗi khi xử lý người chơi {addr}: {e}")
    finally:
        # Dọn dẹp bộ nhớ khi người chơi thoát game
        if addr in players:
            name = players[addr]["name"]
            del players[addr]
            print(f"[SYSTEM] Người chơi {name} ({addr}) đã ngắt kết nối.")
            await broadcast(f"\n[GAME] Anh hùng {name} đã rút lui khỏi hầm ngục.\n" + render_map())
            
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_player, HOST, PORT)
    print(f"[SYSTEM] GAME SERVER ĐÃ KHỞI CHẠY TẠI {HOST}:{PORT}")
    print("[SYSTEM] Đang chờ các game thủ kết nối...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Đã tắt Game Server.")
