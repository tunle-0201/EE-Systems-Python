"""
================================================================================
          MODULE K: EMBEDDED REAL-TIME OS (FREERTOS) & MULTI-TASKING
              MILESTONE K.3: HÀNG ĐỢI THÔNG ĐIỆP LIÊN TÁC VỤ (INTER-TASK MESSAGE QUEUE)
================================================================================

TẠI SAO CẦN MESSAGE QUEUE GIỮA LUỒNG AI VÀ LUỒNG ĐIỀU KHIỂN BAY?
Để truyền lệnh từ Bộ não AI sang Motor mà không làm nghẽn CPU:
- FreeRTOS Message Queue là một hàng đợi FIFO an toàn luồng (Thread-Safe FIFO).
- Luồng AI đẩy lệnh né vật cản `send(msg)` vào hàng đợi.
- Luồng Motor rút lệnh `receive()` ra xử lý ngay lập tức!
"""

class FreeRTOSMessageQueue:
    def __init__(self, max_size=10):
        self.max_size = max_size
        self.queue = []
    
    def send(self, message: dict) -> bool:
        if len(self.queue) < self.max_size:
            self.queue.append(message)
            return True
        return False # Hàng đợi đầy
    
    def receive(self) -> dict:
        if len(self.queue) > 0:
            return self.queue.pop(0) # Rút phần tử đầu tiên FIFO
        return None


if __name__ == "__main__":
    print("=========================================================")
    print("   FREERTOS EMBEDDED: INTER-TASK MESSAGE QUEUE FIFO")
    print("=========================================================\n")
    
    cmd_queue = FreeRTOSMessageQueue(max_size=5)
    
    # AI Vision Task gửi lệnh né vật cản sang Motor Task
    cmd_queue.send({'cmd': 'AVOID_OBSTACLE', 'pitch_deg': -15.0})
    received_cmd = cmd_queue.receive()
    
    print("1. KET QUA TRUYEN THONG TIN NHAN INTER-TASK QUEUE:")
    print(f"   -> Lenh nhan duoc tu Queue : {received_cmd}")
    
    assert received_cmd['cmd'] == 'AVOID_OBSTACLE', "Loi FreeRTOS Message Queue!"
    print("\n[THANH CONG] DA TRUYEN THONG AN TOAN GIUA CAC TAC VU BANG FREERTOS MESSAGE QUEUE!")
