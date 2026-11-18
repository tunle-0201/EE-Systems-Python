"""
================================================================================
          SƯ MÔN EE MENTORSHIP - MODULE 2: EVENT-DRIVEN & ASYNC
                       MILESTONE 2.4 CHÀO SÂN IDE
================================================================================

Chào trò! Từ nay đây là chiến trường thực sự của trò. 

Nhiệm vụ của trò trong file này:
1. Hoàn thành code chạy song song LED nháy (0.5s) và Sensor đọc (3s) dùng `asyncio`.
2. Trả lời câu hỏi lý thuyết ở phần dưới bằng cách sửa nội dung CHÚ THÍCH (comments).
3. Chạy thử file này trên máy của trò: `python milestone_2_4_async.py` để xem kết quả.
4. Khi đã sẵn sàng, hãy gọi Sư phụ trong khung chat để ta chấm bài!
"""

import asyncio

async def blink_led():
    while True:
        print("LED nháy đỏ!")
        await asyncio.sleep(0.5)

async def read_sensor():
    while True:
        print("Đọc cảm biến: 25 độ C")
        await asyncio.sleep(3)

async def main():
    await asyncio.gather(blink_led(), read_sensor())

if __name__ == "__main__":
    # Điểm kích hoạt Event Loop của chương trình
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[HỆ THỐNG] Đã ngắt vi điều khiển an toàn.")

# ================================================================================
# CÂU HỎI LÝ THUYẾT SINH TỬ (Trò hãy gõ câu trả lời vào bên dưới):
#
# Hỏi: Nếu trò vô tình quên gõ chữ `await` trước lệnh `asyncio.sleep(3)` trong hàm 
#      read_sensor, chuyện gì sẽ xảy ra về mặt LOGIC và hiệu năng CPU? 
#      (Python có crash báo lỗi đỏ lòm không? Vòng lặp while True sẽ chạy thế nào?)
#
# Trả lời của trò:
# CPU Không đỏ lòm mà vẫn sẽ tiếp tục chạy, vòng lặp while True thì bị bỏ qua ngay lặp tức, trò vẫn chưa hiểu lắm sư phụ vẽ cái mindmap giúp trò được không?
# ================================================================================
