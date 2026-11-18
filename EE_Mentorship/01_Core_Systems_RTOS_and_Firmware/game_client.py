"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 3: TẦNG SOCKET & BYTES
             MILESTONE 3.3: DỰ ÁN GAME MULTIPLAYER "DUNGEON CRAWLER"
                       PART 2: GAME CLIENT (MÁY TRẠM)
================================================================================

Chào trò! Đây là bộ điều khiển Game của người chơi.
File này đã được Sư phụ viết hoàn chỉnh để trò sử dụng kết nối vào Server.

Cơ chế hoạt động của Client:
1. Nó mở kết nối TCP tới Server tại cổng 9999.
2. Nó dùng cơ chế Đa nhiệm (Multitasking) của Asyncio để chạy song song 2 tác vụ:
   - Tác vụ 1: Lắng nghe liên tục dữ liệu Server gửi về (bản đồ, tin nhắn của người khác) và in ra màn hình.
   - Tác vụ 2: Lắng nghe bàn phím của trò (qua hàm nhập lệnh) và gửi lệnh lên Server.
   
*Lưu ý nâng cao:* Vì hàm `input()` mặc định của Python là hàm chặn (blocking),
sư phụ đã dùng `asyncio.to_thread(input)` để đẩy nó sang một luồng (thread) phụ của Hệ điều hành,
giúp luồng chính của Event Loop vẫn chạy mượt mà để nhận bản đồ khi có người chơi khác di chuyển!

Cách chơi:
- Chạy client: `python EE_Mentorship/game_client.py`
- Lệnh 1: Nhập `join:Tên_Của_Trò` để vào game (Ví dụ: `join:Tuan`).
- Lệnh 2: Nhập `move:w`, `move:s`, `move:a`, `move:d` để di chuyển ký tự của mình.
- Lệnh 3: Nhấn `Ctrl + C` để thoát game.
"""

import asyncio
import sys

HOST = "127.0.0.1"
PORT = 9999

async def listen_to_server(reader: asyncio.StreamReader):
    """Liên tục lắng nghe bản đồ và sự kiện từ Server gửi về"""
    try:
        while True:
            data = await reader.read(4096)  # Đọc tối đa 4KB dữ liệu
            if not data:
                print("\n[HỆ THỐNG] Mất kết nối tới Server.")
                break
            # In dữ liệu giải mã trực tiếp ra màn hình
            sys.stdout.write(data.decode())
            sys.stdout.flush()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"\n[ERR] Lỗi khi đọc dữ liệu từ server: {e}")

async def send_commands(writer: asyncio.StreamWriter):
    """Liên tục nhận phím bấm của người dùng và bắn lên Server"""
    try:
        print("[HỆ THỐNG] Đang kết nối... Nhập lệnh vào đây.")
        while True:
            # Chuyển hàm input() chặn luồng sang Thread phụ của OS để không treo game loop
            user_input = await asyncio.to_thread(input, "")
            
            if not user_input.strip():
                continue
                
            # Mã hóa và gửi qua Socket
            writer.write(user_input.encode())
            await writer.drain()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"\n[ERR] Lỗi khi gửi lệnh: {e}")

async def main():
    try:
        reader, writer = await asyncio.open_connection(HOST, PORT)
        
        # Chạy song song 2 luồng sự kiện Nhận và Gửi
        listener_task = asyncio.create_task(listen_to_server(reader))
        sender_task = asyncio.create_task(send_commands(writer))
        
        # Chờ cho đến khi một trong 2 tác vụ bị dừng (ví dụ mất kết nối)
        done, pending = await asyncio.wait(
            [listener_task, sender_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Dọn dẹp tác vụ còn lại
        for task in pending:
            task.cancel()
            
    except ConnectionRefusedError:
        print("[ERR] Không thể kết nối tới Server. Trò đã chạy file game_server.py chưa?")
    except Exception as e:
        print(f"[ERR] Lỗi kết nối: {e}")

if __name__ == "__main__":
    try:
        # Thiết lập encoding UTF-8 cho terminal để in bản đồ không lỗi
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[HỆ THỐNG] Đã thoát game.")
