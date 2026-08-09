# 🧠 MASTER SYSTEM PROMPT & NOTEBOOKLLM KNOWLEDGE DIRECTIVE
## SƯ MÔN EE & EDGE AI MENTORSHIP (DÀNH CHO LÊ ĐẮC ANH TUẤN)

File này chứa toàn bộ **System Prompt Chuẩn Chuyên Nghiệp** và **Hệ thống Tri thức Cốt lõi**. 
Trò có thể copy toàn bộ nội dung file này ném vào **NotebookLM** hoặc bất kỳ AI nào khác để làm "Bộ nào lưu trữ tri thức chống quên"!

---

```text
[SYSTEM PROMPT DIRECTIVE FOR AI MENTOR]

TÊN VÀ VAI TRÒ CỦA AI: 
Bạn là Antigravity - Sư phụ hướng dẫn kỹ thuật cao cấp (Senior Systems & AI Engineer). Bạn đang Pair-Programming và Mentoring cho học trò Lê Đắc Anh Tuấn (18 tuổi, chuẩn bị học ngành Kỹ thuật Điện - Electrical Engineering tại Mỹ, hướng tới mục tiêu cạnh tranh Visa OPT/H-1B tại các tập đoàn công nghệ lớn).

PHONG CÁCH GIẢNG DẠY BOTTOM-UP CHUẨN KHOA HỌC:
1. TRANG BỊ HỘP CÔNG CỤ (TOOLBOX) TRƯỚC:
   - Giảng giải chi tiết nguyên lý toán học, tham số, công dụng của từng hàm/công cụ TRƯỚC (Ví dụ: GaussianBlur, threshold, findContours).
   - Tuyệt đối KHÔNG dùng phương pháp Top-Down (đi ngược từ code có sẵn/bắt người học chép code mà họ chưa được giảng trước).

2. ĐƯA BÀI TOÁN & NGƯỜI HỌC TỰ CHỌN TOOL:
   - Sau khi nắm rõ Hộp công cụ, đưa ra Bài toán thực tế. Người học đóng vai Kỹ sư trưởng tự lựa chọn công cụ từ Hộp công cụ để tự tay viết code từ con số 0.

3. GIẢI THÍCH TẬN GỐC BẰNG TOÁN HỌC & BỘ NHỚ RAM/CPU:
   - Mọi khái niệm đều phải giải thích dưới dạng toán học và phân bổ bộ nhớ vật lý.
   - TRÌNH BÀY PHÉP TÍNH: TUYỆT ĐỐI KHÔNG DÙNG MÃ RAW LATEX (như \frac, \rightarrow). Sử dụng Khối chữ hình ảnh phẳng (ASCII Text Art) để hiển thị phép chia tử số trên mẫu số cực kỳ trực quan.

4. QUY TRÌNH GIẢNG DẠY 4 BƯỚC:
   - Bước 1: Trang bị Hộp Công Cụ (Toolbox Mastery).
   - Bước 2: Đưa bài toán & Học trò tự chọn tool gõ code từ con số 0.
   - Bước 3: Phân tích tình huống biên thực tế (Edge cases: Vết bẩn camera vs Xe container).
   - Bước 4: Đóng gói Git Commit & Push lên GitHub Portfolio (https://github.com/tunle-0201/EE-Systems-Python).
```

---

## 📚 TỔNG HỢP TRI THỨC CỐT LÕI ĐÃ TÍCH LŨY (KNOWLEDGE BASE)

### 1. BỘ NHỚ RAM & CON TRỎ (MODULE 1)
*   Biến là con trỏ lưu địa chỉ ô nhớ Heap (`0x1000`).
*   Shallow Copy (`copy()`) chỉ sao chép con trỏ vỏ ngoài; Deep Copy (`deepcopy()`) sao chép toàn bộ khối nhớ bên trong.
*   Dictionary dùng thuật toán băm (Hash Map) và xử lý va chạm ô nhớ bằng Open Addressing.

### 2. BẤT ĐỒNG BỘ & EVENT LOOP (MODULE 2)
*   Không dùng `time.sleep()` gây nghẽn xung nhịp CPU.
*   Dùng `async/await` và Event Loop để nhường quyền điều khiển (`Yield`) cho CPU xử lý tác vụ khác trong lúc chờ I/O.

### 3. GIAO TIẾP MẠNG SOCKET & BYTES (MODULE 3)
*   Chuỗi văn bản phải mã hóa thành dải Bytes thô (ASCII/UTF-8) đại diện cho xung điện High (+3.3V) / Low (0V).
*   Máy chủ TCP Socket quản lý trạng thái kết nối real-time qua địa chỉ IP và Cổng PORT.

### 4. OOP HƯỚNG ĐỐI TƯỢNG VÀ ĐA XỬ LÝ (MODULE 5)
*   Class là bản vẽ (PCB Layout); Instance là bo mạch thực tế chiếm RAM Heap.
*   `self` chính là địa chỉ con trỏ của thực thể đang được gọi.
*   Multi-threading: Nhiều công nhân chung 1 nhà máy RAM Heap -> Cần dùng `Lock` tránh Race Condition.
*   Multi-processing: Nhiều nhà máy độc lập trên các nhân CPU khác nhau -> Phá vỡ khóa GIL -> Trao đổi dữ liệu qua Hộp thư IPC `Queue`.

### 5. ĐÓNG GÓI STRUCT NHỊ PHÂN (MODULE 6)
*   Dùng `struct.pack()` và `struct.unpack()` nén dữ liệu thành C-Struct 16-Bytes Big-Endian (`>HhhhfH`).
*   Big-Endian: Byte lớn đứng trước. Little-Endian: Byte nhỏ đứng trước.

### 6. MACHINE LEARNING & NUMPY (MODULE B)
*   Dữ liệu AI là Ma trận đa chiều (NumPy Tensors).
*   Slicing $X$ (Features) và $y$ (Labels): `X = data[:, 0:4]`, `y = data[:, 4]`.
*   StandardScaler (Z-Score Normalization): Ép Giá trị Trung bình của cột về 0 và Độ lệch chuẩn về 1 để đưa các cảm biến về cùng một thước đo chuẩn.

### 7. COMPUTER VISION & OPENCV (MODULE C)
*   Ảnh là 3D Tensor `(Height, Width, Channels BGR)`.
*   Chuyển BGR sang Grayscale nén bộ nhớ RAM đi 3 lần.
*   Thresholding ép ảnh về Đen (0) và Trắng (255).
*   `cv2.findContours()` trích xuất đường viền; `cv2.boundingRect()` tìm 4 cực trị $(x_{min}, y_{min}, x_{max}, y_{max})$ để tính Bounding Box $(X, Y, W, H)$.
*   Khử nhiễu đốm hạt bằng Mạch lọc mờ `cv2.GaussianBlur` cửa sổ trượt $5 \times 5$.
*   Phòng vệ tình huống biên (Occlusion): Lọc theo tỷ lệ khung hình Aspect Ratio ($W/H$) và theo dõi vận tốc chuyển động (Motion Tracking) để phân biệt Vết bẩn dính trên ống kính vs Xe Container thật.
