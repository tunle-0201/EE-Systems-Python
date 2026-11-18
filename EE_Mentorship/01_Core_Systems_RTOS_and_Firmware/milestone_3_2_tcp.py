"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 3: TẦNG SOCKET & BYTES
             MILESTONE 3.2: KẾT NỐI KHÔNG DÂY (TCP CLIENT & SERVER)
================================================================================

Chào trò! Trò đã biết đóng gói Bytes. Giờ là lúc bắn dãy Bytes đó đi qua mạng.

Chúng ta sẽ sử dụng giao thức TCP/IP - xương sống của Internet.
TCP (Transmission Control Protocol) đảm bảo dữ liệu truyền đi không bị mất mát hay lệch thứ tự.
Nó giống như một đường ống dẫn nước (Stream), ta bơm bytes vào đầu này, nó sẽ chảy ra đầu kia.

Trong file này, trò sẽ tự tay hoàn thiện một hệ thống gồm cả SERVER (Trạm thu nhận)
và CLIENT (Thiết bị IoT gửi tin) chạy song song bất đồng bộ bằng `asyncio`.

Nhiệm vụ của trò trong file này:
1. Hoàn thành TODO 1 trong hàm `handle_client`: Server nhận bytes thô, hãy DỊCH NGƯỢC thành String và in ra.
2. Hoàn thành TODO 2 trong hàm `send_sensor_data`: Client hãy MÃ HÓA dữ liệu nhiệt độ thành Bytes rồi gửi đi.
3. Trả lời câu hỏi ở phần cuối.
4. Chạy file bằng lệnh: `python EE_Mentorship/milestone_3_2_tcp.py`
5. Khi hoàn thành và chạy thử thành công, hãy ping Sư phụ!
"""

import asyncio

# Địa chỉ IP nội bộ (localhost) và Cổng mạng (Port)
HOST = "127.0.0.1"
PORT = 8888

# ================================================================================
# TÁC VỤ 1: TCP SERVER (Trạm nhận dữ liệu trung tâm)
# ================================================================================
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    # Đọc dữ liệu thô gửi lên từ client (tối đa 1024 bytes)
    raw_bytes = await reader.read(1024)
    
    # TODO 1: Dịch ngược raw_bytes thành chuỗi string (sử dụng decode)
    # Viết code gán vào biến dec_message
    dec_message = raw_bytes.decode()
    
    print(f"[SERVER] Đã nhận tín hiệu: {dec_message}")
    
    # Gửi phản hồi xác nhận (ACK) về cho Client
    response = "SERVER_ACK: RECEIVED_OK".encode()
    writer.write(response)
    await writer.drain()
    
    # Đóng kết nối
    writer.close()
    await writer.wait_closed()

async def run_server():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    print(f"[SYSTEM] Server đang lắng nghe xung điện tại {HOST}:{PORT}...")
    async with server:
        await server.serve_forever()

# ================================================================================
# TÁC VỤ 2: TCP CLIENT (Thiết bị cảm biến IoT)
# ================================================================================
async def send_sensor_data():
    # Chờ 1 giây để đảm bảo Server đã khởi động xong
    await asyncio.sleep(1)
    
    print(f"[CLIENT] Đang cắm cáp kết nối tới Trạm trung tâm {HOST}:{PORT}...")
    reader, writer = await asyncio.open_connection(HOST, PORT)
    
    # Chuỗi dữ liệu cảm biến
    sensor_str = "SENSOR_VAL: 42.5 C"
    
    # TODO 2: Mã hóa chuỗi sensor_str thành bytes (sử dụng encode)
    # Viết code gán vào biến byte_packet
    byte_packet = sensor_str.encode()
    
    print(f"[CLIENT] Đang bắn packet bytes xuống cáp mạng...")
    writer.write(byte_packet)
    await writer.drain()
    
    # Đọc phản hồi xác nhận từ Server
    ack_bytes = await reader.read(1024)
    print(f"[CLIENT] Trạm phản hồi: {ack_bytes.decode()}")
    
    # Đóng kết nối
    writer.close()
    await writer.wait_closed()

# ================================================================================
# ĐIỂM KHỞI ĐỘNG HỆ THỐNG
# ================================================================================
async def main():
    # Chạy song song cả Server lắng nghe và Client gửi dữ liệu
    server_task = asyncio.create_task(run_server())
    client_task = asyncio.create_task(send_sensor_data())
    
    # Chờ Client gửi xong dữ liệu
    await client_task
    # Dừng server sau khi hoàn thành kết nối
    server_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[ERR] Có lỗi xảy ra: {e}")

# ================================================================================
# CÂU HỎI LÝ THUYẾT (Trò hãy điền câu trả lời vào bên dưới):
#
# Hỏi: Tại sao trong truyền thông Socket, ta bắt buộc phải có một địa chỉ IP (HOST)
#      và một cổng mạng (PORT)? Vai trò của PORT khác gì với IP ở tầng phần cứng/OS?
#      (Gợi ý liên tưởng: IP giống như địa chỉ của một tòa nhà chung cư, vậy PORT là gì?)
#
# Trả lời của trò:
# PORT là địa chỉ của từng căn hộ trong tòa nhà. IP giống như địa chỉ của tòa nhà, còn PORT là địa chỉ của từng căn hộ trong tòa nhà.
# ================================================================================
