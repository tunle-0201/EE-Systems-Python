"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 4: TÍCH HỢP AI & JSON THÔ
             MILESTONE 4.1: QUÁI VẬT HẦM NGỤC GEMINI XUẤT HIỆN!
================================================================================

Chúc mừng trò đã hoàn thành thông mạch Multiplayer! 
Bây giờ, chúng ta sẽ đưa "Trí tuệ nhân tạo (AI)" vào thế giới này.

Kịch bản Game:
1. Sư phụ đã đặt thêm một con Boss Hầm Ngục kí hiệu là 'B' cố định tại tọa độ (2, 2).
2. Khi người chơi đứng cạnh Boss (khoảng cách 1 ô), họ có thể dùng lệnh:
   - "talk:tin_nhắn" (Ví dụ: "talk:Ngươi là ai?")
3. Máy chủ (Server) sẽ tự động đóng gói tin nhắn đó vào định dạng JSON,
   gửi một yêu cầu mạng HTTP POST trực tiếp lên API của Google Gemini,
   nhận kết quả JSON trả về, bóc tách câu trả lời của Boss, và phát loa cho cả phòng.

*Tư duy EE:*
Để gọi API, ta dùng thư viện chuẩn `urllib.request` của Python để tự tay đóng gói
gói tin HTTP mà KHÔNG dùng các SDK cao cấp (được coi là hộp đen - black-box).
Vì yêu cầu mạng này rất chậm (mất khoảng 1-2 giây), nếu ta gọi trực tiếp,
nó sẽ làm đứng hình (block) toàn bộ game loop! 
Do đó, sư phụ dùng `asyncio.to_thread` để đẩy luồng HTTP này sang Thread phụ của OS.

Nhiệm vụ của trò trong file này:
1. Hoàn thành TODO 1: Sử dụng thư viện `json` để biến đổi Dictionary trong Python
   thành chuỗi định dạng JSON (Mã hóa JSON - Serialization).
2. Hoàn thành TODO 2: Sử dụng thư viện `json` để phân tích chuỗi JSON nhận từ Google Gemini
   và bóc tách chính xác câu trả lời của Boss (Giải mã JSON - Deserialization).
3. Trả lời câu hỏi lý thuyết ở cuối file.
4. Chạy game: `python EE_Mentorship/game_server_ai.py`
"""

import asyncio
import json
import urllib.request
import urllib.error
import os

HOST = "127.0.0.1"
PORT = 9999
MAP_SIZE = 5

# Quản lý người chơi
players = {}

# Tọa độ của Boss 'B'
BOSS_X = 2
BOSS_Y = 2

# Nhập API key của trò ở đây nếu có (hoặc set biến môi trường GEMINI_API_KEY).
# Nếu không có, hệ thống sẽ tự động dùng "MOCK BOSS" (Boss giả lập) để trò vẫn test được game!
API_KEY = os.environ.get("GEMINI_API_KEY", "")

def call_gemini_api(prompt: str) -> str:
    """
    Hàm gọi API Google Gemini bằng HTTP Request thô.
    Hàm này chạy đồng bộ (blocking) và sẽ được chạy trong Thread phụ.
    """
    if not API_KEY:
        # Chế độ mô phỏng Boss nếu trò không có API Key
        return f"[MOCK BOSS] GÀOOO! Ta là quái vật bóng đêm! Ngươi vừa nói: '{prompt}'? Hãy biến đi trước khi ta nổi giận!"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    # Cấu trúc JSON chuẩn yêu cầu bởi Google Gemini API
    payload_dict = {
        "contents": [{
            "parts": [{
                "text": f"Bạn là một con quái vật hung dữ, canh giữ hầm ngục Dungeon trong game RPG. Hãy trả lời cực kỳ ngắn gọn (dưới 20 từ), mang giọng điệu đe dọa, cục cằn. Người chơi vừa nói với bạn: '{prompt}'"
            }]
        }]
    }
    
    try:
        # TODO 1: Biến đổi `payload_dict` (Dictionary Python) thành chuỗi JSON
        # Gợi ý: Dùng hàm json.dumps(...)
        # Viết code thay thế cho pass dưới đây:
        json_data = json.dumps(payload_dict)
        
        # Đóng gói dữ liệu thành bytes để truyền qua mạng
        body = json_data.encode("utf-8")
        
        # Tạo request HTTP POST thô
        req = urllib.request.Request(
            url, 
            data=body, 
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        # Gửi request và nhận response (Blocking I/O)
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            
            # TODO 2: Phân tích cú pháp JSON nhận về và trích xuất câu trả lời.
            # Cấu trúc JSON trả về của Gemini như sau:
            # {
            #   "candidates": [
            #     {
            #       "content": {
            #         "parts": [
            #           { "text": "Câu trả lời của Boss nằm ở đây" }
            #         ]
            #       }
            #     }
            #   ]
            # }
            #
            # Hướng dẫn:
            # 1. Dùng json.loads(res_body) để chuyển chuỗi JSON thành Dict của Python.
            # 2. Truy cập sâu vào các tầng Dict và List của structure trên để lấy text.
            #
            # Viết code thay thế cho pass dưới đây (trả về chuỗi text):
            res_dict = json.loads(res_body)
            boss_text = res_dict["candidates"][0]["content"]["parts"][0]["text"]
            return boss_text
            
    except Exception as e:
        return f"[BOSS] GÀOOO! (Mất sóng kết nối thần linh: {e})"

async def broadcast(message: str):
    """Gửi tin nhắn tới tất cả người chơi (Đã hoàn thành ở bài trước)"""
    for addr, player in players.values(): # Sư phụ dùng .values() để tối ưu
        writer = player["writer"]
        try:
            writer.write(message.encode())
            await writer.drain()
        except:
            pass

def render_map() -> str:
    """Vẽ bản đồ 5x5 có Boss 'B' và các người chơi"""
    grid = [["." for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
    
    # Vẽ Boss 'B'
    grid[BOSS_Y][BOSS_X] = "B"
    
    # Vẽ người chơi
    for addr, player in players.items():
        x, y = player["x"], player["y"]
        # Nếu đè lên Boss thì hiện ký tự người chơi
        grid[y][x] = player["char"]
        
    map_str = "\n--- DUNGEON MAP ---\n"
    for row in grid:
        map_str += " ".join(row) + "\n"
    map_str += "-------------------\n"
    return map_str

def process_move(addr: tuple, direction: str):
    """Tính toán di chuyển kẹp biên (Đã hoàn thành ở bài trước)"""
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
    print(f"[SYSTEM] Kết nối mới: {addr}")
    
    try:
        welcome_msg = "WELCOME: Nhập 'join:Tên' để chơi. Nhập 'talk:nội_dung' khi đứng cạnh Boss 'B'.\n"
        writer.write(welcome_msg.encode())
        await writer.drain()
        
        while True:
            data = await reader.read(1024)
            if not data:
                break
                
            command = data.decode().strip()
            
            # Đăng ký tham gia
            if command.startswith("join:") and addr not in players:
                name = command.split(":")[1][:10]
                char = name[0].upper()
                players[addr] = {"name": name, "x": 0, "y": 0, "char": char, "writer": writer}
                await broadcast(f"\n[GAME] Anh hùng {name} ({char}) đã vào hầm ngục!\n" + render_map())
                
            # Di chuyển
            elif command.startswith("move:") and addr in players:
                direction = command.split(":")[1].lower()
                process_move(addr, direction)
                await broadcast(f"\n[GAME] {players[addr]['name']} di chuyển '{direction}'\n" + render_map())
                
            # Nói chuyện với Boss
            elif command.startswith("talk:") and addr in players:
                message = command.split(":")[1]
                player_name = players[addr]["name"]
                px, py = players[addr]["x"], players[addr]["y"]
                
                # Kiểm tra khoảng cách Euclid/Manhattan: Người chơi có đứng cạnh Boss không?
                # Đứng cạnh nghĩa là khoảng cách x cách tối đa 1 ô, y cách tối đa 1 ô.
                if abs(px - BOSS_X) <= 1 and abs(py - BOSS_Y) <= 1:
                    await broadcast(f"\n[TRÒ CHUYỆN] {player_name} nói với Boss: '{message}'\n")
                    await broadcast("[SYSTEM] Boss Gemini đang suy nghĩ chiêu thức...\n")
                    
                    # Gọi API bất đồng bộ bằng cách đẩy hàm blocking call_gemini_api sang Thread phụ
                    boss_reply = await asyncio.to_thread(call_gemini_api, message)
                    
                    await broadcast(f"\n[BOSS GEMINI]: \"{boss_reply}\"\n")
                else:
                    writer.write("[SYSTEM] Trò đứng quá xa! Hãy tiến lại gần Boss (chữ B) ở trung tâm bản đồ.\n".encode())
                    await writer.drain()
                    
    except Exception as e:
        print(f"[ERR] Lỗi xử lý {addr}: {e}")
    finally:
        if addr in players:
            name = players[addr]["name"]
            del players[addr]
            await broadcast(f"\n[GAME] {name} đã rút lui khỏi hầm ngục.\n" + render_map())
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_player, HOST, PORT)
    print(f"[SYSTEM] GAME SERVER TÍCH HỢP AI CHẠY TẠI {HOST}:{PORT}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Đã tắt Game Server.")

# ================================================================================
# CÂU HỎI LÝ THUYẾT (Trò hãy điền câu trả lời vào bên dưới):
#
# Hỏi: Tại sao khi giao tiếp với các máy chủ web (như Google API), người ta lại chọn
#      định dạng dữ liệu JSON mà không dùng định dạng text thông thường? 
#      Đặc điểm của JSON giúp ích gì cho các hệ thống phần mềm viết bằng các ngôn ngữ
#      khác nhau (ví dụ: Python gửi JSON, Server Google viết bằng C++/Java nhận JSON)?
#
# Trả lời của trò:
# > Vi dinh dang JSON de truyen thong du lieu giua cac he thong voi nhau, vi du nhu may cua tro viet bang ngon ngu Python may cua su phu C++ thi van co the hieu duoc code cua may tro
# ================================================================================
