# SƯ MÔN EE MENTORSHIP: BẢN TRA CỨU TÂM PHÁP PYTHON (LOW-LEVEL CHEAT SHEET)

Chào trò! Cảm giác hoang mang là rất tốt. Nó chứng tỏ não bộ của trò đang phải "tái cấu trúc" lại để chuyển từ việc code theo bản năng sang hiểu rõ từng khối lệnh hoạt động ra sao. 

Bản tra cứu này giải thích chính xác các quy luật, cú pháp và các hàm trò đang dùng trong các bài tập. Hãy mở nó song song trên IDE để tra cứu bất cứ lúc nào!

---

## 1. PHÂN BIỆT 3 CẤU TRÚC DỮ LIỆU CƠ BẢN (Trong RAM)

### A. LIST (Mảng liên tục) - Ký hiệu: `[]`
*   **Bản chất:** Các ô nhớ nằm sát sườn nhau trong RAM.
*   **Quy luật:** Truy cập bằng chỉ số số nguyên (index).
*   **Ví dụ:** `board = ["A", "B", "C"]`
    *   `board[0]` -> Trả về `"A"`
    *   `board[1] = "X"` -> Thay thế phần tử thứ hai bằng `"X"`
    *   `len(board)` -> Trả về độ dài mảng (`3`)

### B. DICTIONARY (Bảng băm / Hash Map) - Ký hiệu: `{}`
*   **Bản chất:** Lưu dữ liệu dạng cặp `Khóa (Key) : Giá trị (Value)`. Không có thứ tự, CPU tìm kiếm bằng cách băm từ khóa ra địa chỉ RAM.
*   **Ví dụ:** `players = { "127.0.0.1": {"name": "Tuan", "x": 0} }`
    *   **Truy cập:** `players["127.0.0.1"]` -> Trả về `{"name": "Tuan", "x": 0}`
    *   **Thêm/Sửa:** `players["127.0.0.1"]["x"] = 2` -> Sửa tọa độ x của Tuan thành `2`.
    *   **Quy luật duyệt vòng lặp:**
        *   `dict.keys()`: Chỉ lấy danh sách các Khóa.
        *   `dict.values()`: Chỉ lấy danh sách các Giá trị.
        *   `dict.items()`: Lấy cả cặp `(Khóa, Giá trị)` đóng gói trong một **Tuple** (Cặp ngoặc tròn).
        *   *Ví dụ duyệt items:* `for key, val in dict.items():` (Bắt buộc phải khai báo 2 biến để rã bọc Tuple).

### C. TUPLE (Chuỗi không thể sửa đổi) - Ký hiệu: `()`
*   **Bản chất:** Giống List nhưng khi đã tạo ra thì **không được phép thêm, bớt hay sửa đổi**. Dùng để lưu các hằng số hoặc tọa độ cố định.
*   **Ví dụ:** `addr = ("127.0.0.1", 9999)`
    *   `addr[0]` -> Trả về `"127.0.0.1"`
    *   `addr[1] = 8888` -> **BÁO LỖI NGAY** (Vì Tuple là Read-only).

---

## 2. TRUYỀN THÔNG MẠNG (Chữ viết vs Xung điện)

*   **String (Chuỗi chữ):** Dùng cho con người đọc. Ví dụ: `msg = "HELLO"`.
*   **Bytes (Dãy số nguyên 0-255):** Dùng để truyền qua dây cáp mạng dưới dạng xung điện nhị phân. Ví dụ: `data = b"HELLO"`.

### Quy luật chuyển đổi:
*   **Mã hóa (Gửi đi):** `String` -> `.encode("utf-8")` -> `Bytes`
    ```python
    xung_dien = "HELLO".encode("utf-8") # Gửi qua Socket
    ```
*   **Giải mã (Nhận về):** `Bytes` -> `.decode("utf-8")` -> `String`
    ```python
    chu_viet = xung_dien.decode("utf-8") # In ra màn hình
    ```

---

## 3. BẤT ĐỒNG BỘ & ĐA NHIỆM (Async/Await)

*   **`async def my_func():`**
    Khai báo đây là một hàm bất đồng bộ (Coroutine). Khi gọi `my_func()`, nó không chạy ngay mà trả về một "phiếu chờ".
*   **`await my_func()`**
    Kích hoạt chạy hàm và **nhường CPU** cho Event Loop quản lý trong lúc hàm này đang chờ đợi I/O phần cứng.
*   **`asyncio.gather(tác_vụ_1, tác_vụ_2)`**
    Gom nhiều tác vụ bất đồng bộ lại để Event Loop chạy chúng **song song** (con chip đa nhiệm).
*   **`writer.write(data)`**
    Đổ dữ liệu bytes vào bộ đệm của socket.
*   **`await writer.drain()`**
    Bắt buộc phải có `await`, lệnh này ép CPU đẩy sạch dữ liệu từ bộ đệm xuống card mạng để bắn đi qua dây đồng.

---

## 4. QUY LUẬT TOÁN HỌC GIỚI HẠN BIÊN (Clamping)

Để giữ một con số nằm trong khoảng từ `MIN` đến `MAX` mà không cần viết nhiều lệnh `if/else` dài dòng:
```python
# Giữ giá trị value luôn nằm trong khoảng từ 0 đến 4
value = max(0, min(value, 4))
```
*   `min(value, 4)`: Đảm bảo con số không vượt quá `4`.
*   `max(0, ...)`: Đảm bảo con số không tụt xuống dưới `0`.
