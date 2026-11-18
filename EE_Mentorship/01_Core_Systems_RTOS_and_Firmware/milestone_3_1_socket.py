"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 3: TẦNG SOCKET & BYTES
                   MILESTONE 3.1: ĐÓNG GÓI XUNG ĐIỆN (BYTES)
================================================================================

Chào trò! Chúng ta bắt đầu chạm vào phần "Mạng vật lý".

Khi truyền dữ liệu qua Internet/Wifi, chip mạng không biết "chữ viết" hay "chuỗi (string)"
là gì. Tất cả phải được băm nhỏ thành các Bytes (mỗi byte = 8 bits), và phần cứng sẽ
biến đổi các bit 1 và 0 này thành xung điện (Voltage levels: High/Low) để bắn đi qua dây cáp.

Trong Python, Socket (cổng mạng) TUYỆT ĐỐI không nhận kiểu dữ liệu String.
Nếu trò viết: socket.send("TEMP: 25"), chương trình sẽ lập tức nổ tung (crash).
Trò bắt buộc phải "Mã hóa" (Encode) chuỗi chữ thành dạng Bytes vật lý trước khi gửi.

Nhiệm vụ của trò trong file này:
1. Hoàn thành hàm `pack_data_to_bytes` để mã hóa chuỗi chữ thành dãy bytes.
2. Hoàn thành hàm `unpack_bytes_to_string` để dịch ngược dãy bytes nhận về thành chữ đọc được.
3. Trả lời câu hỏi lý thuyết về điện áp ở phần cuối.
4. Chạy file bằng lệnh: `python EE_Mentorship/milestone_3_1_socket.py`
5. Khi hoàn thành và chạy thử thành công, hãy ping Sư phụ!
"""

def pack_data_to_bytes(text_data: str) -> bytes:
    return text_data.encode("utf-8")

def unpack_bytes_to_string(byte_data: bytes) -> str:
    return byte_data.decode("utf-8")

if __name__ == "__main__":
    # Mô phỏng dữ liệu đọc từ cảm biến nhiệt độ
    original_signal = "TEMP: 25.4 C | STATUS: OK"
    print(f"[1. Giao diện người dùng] Dữ liệu gốc (String): {original_signal}")
    print(f"   -> Kiểu dữ liệu trong RAM: {type(original_signal)}")
    
    # Bước 1: Đóng gói thành xung điện (Bytes)
    electrical_packet = pack_data_to_bytes(original_signal)
    print(f"\n[2. Tầng Vật Lý] Dữ liệu đã đóng gói để gửi qua cáp đồng (Bytes):")
    print(f"   -> Giá trị bytes hiển thị: {electrical_packet}")
    print(f"   -> Kiểu dữ liệu thực tế: {type(electrical_packet)}")
    print(f"   -> Danh sách các con số nguyên (0-255) trong từng ô nhớ RAM:")
    print(f"      {list(electrical_packet)}")
    
    # Bước 2: Nhận dữ liệu ở đầu thu và giải mã
    received_signal = unpack_bytes_to_string(electrical_packet)
    print(f"\n[3. Đầu Thu] Giải mã thành công về dạng String cho con người đọc:")
    print(f"   -> Kết quả: {received_signal}")
    
    # Kiểm tra tính toàn vẹn dữ liệu
    assert original_signal == received_signal, "Lỗi! Dữ liệu giải mã bị sai lệch!"
    print("\n[HỆ THỐNG] Chúc mừng trò! Kiểm tra toàn vẹn dữ liệu ĐẠT 100%.")

# ================================================================================
# CÂU HỎI LÝ THUYẾT VẬT LÝ (Trò hãy điền câu trả lời vào bên dưới):
#
# Hỏi: Khi danh sách các con số nguyên của gói tin bytes được gửi qua cáp Ethernet đồng,
#      ví dụ như con số 84 (mã ASCII của chữ 'T', nhị phân là 01010100):
#      Các bit 0 và 1 này sẽ được card mạng (PHY chip) biến đổi thành tín hiệu vật lý 
#      gì cụ thể trên sợi dây điện để truyền đến máy tính bên kia?
#
# Trả lời của trò:
# > High and Low?
# ================================================================================
