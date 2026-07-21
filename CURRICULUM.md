# 📜 LỘ TRÌNH ĐÀO TẠO KỸ SƯ EE & CHUẨN SƯ PHẠM (CURRICULUM SYLLABUS)

## 🎯 4 BƯỚC QUY TRÌNH GIẢNG DẠY CHUẨN KHOA HỌC (4-STEP TEACHING PROTOCOL)

Để đảm bảo kiến thức luôn được **thấu hiểu tận gốc – thực hành thành thạo – ghi nhớ lâu dài**, mỗi Module từ nay sẽ tuân thủ nghiêm ngặt quy trình 4 bước:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ BƯỚC 1: LÝ THUYẾT BẢN CHẤT (Low-level Hardware & Mental Model)           │
│ - Giảng giải cơ chế phần cứng (RAM, CPU, Bus, Registers)                 │
│ - Kết thúc bằng 1-2 câu hỏi Socratic kiểm tra tư duy trước khi code.     │
├──────────────────────────────────────────────────────────────────────────┤
│ BƯỚC 2: THỰC HÀNH TỪNG NẤC THANG (Guided Milestone Coding)               │
│ - Viết code thực tế trực tiếp trên IDE với các file bài tập chi tiết.    │
│ - Tự tay chạy thử, đọc log phần cứng và fix bug.                         │
├──────────────────────────────────────────────────────────────────────────┤
│ BƯỚC 3: TỔNG KẾT & HỆ THỐNG HÓA (Module Summary & Cheatsheet)            │
│ - Biên soạn file tài liệu ôn tập tóm tắt các nguyên lý cốt lõi.           │
├──────────────────────────────────────────────────────────────────────────┤
│ BƯỚC 4: GIT PUSH & QUẢN LÝ DỰ ÁN PRO (Version Control & Portfolio)        │
│ - Đóng gói commit chuẩn conventional commit (`feat:`, `fix:`).            │
│ - Push lên GitHub để liên tục nâng cấp Portfolio cá nhân.                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ LỘ TRÌNH KHÓA HỌC TỔNG THỂ (COMPLETE ROADMAP)

### PHASE 1: NỀN TẢNG HỆ THỐNG VÀ BỘ NHỚ (COMPLETED ✅)
*   [x] **Module 1: Bản chất Dữ liệu & RAM** (Pointer, Heap, List vs Dict, Hash Collisions).
*   [x] **Module 2: Thời gian & Bất đồng bộ** (CPU Cycles, Non-blocking, Asyncio Event Loop).
*   [x] **Module 3: Giao tiếp Mạng Tầng Socket** (Bytes, Encoding, TCP Client/Server, Multiplayer Engine).
*   [x] **Module 4: Tích hợp REST API & JSON** (Raw HTTP Requests, Serialization, Gemini AI Boss).
*   [x] **Module 5: OOP & Đa xử lý Đa Nhân** (Hardware Abstraction, PWM, Mutex Locks, Multiprocessing IPC).

---

### PHASE 2: TRUYỀN THÔNG PHẦN CỨNG VÀ CHUẨN CHUYÊN NGHIỆP (CURRENT 🚀)
*   [ ] **Module 6: Đóng gói Dữ liệu Nhị phân & Đệm Thanh ghi (Binary Structs & Endianness)**
    *   *Lý thuyết:* Little-Endian vs Big-Endian, Memory Alignment trên chip vi điều khiển, C-Structs trong thanh RAM.
    *   *Thực hành:* Dùng module `struct` của Python mã hóa và giải mã các gói tin cảm biến telemetry thô (Battery Voltage, Temperature, Gyroscope).
*   [ ] **Module 7: Tự động hóa Kiểm thử & CI/CD (Pytest & GitHub Actions)**
    *   *Lý thuyết:* Nguyên lý Unit Testing, Mocking I/O phần cứng, đường ống tự động hóa (CI/CD Pipeline).
    *   *Thực hành:* Viết bộ test tự động kiểm tra toàn bộ hệ thống code bằng `pytest` và thiết lập GitHub Actions tự động chạy test mỗi khi `git push`.

---

### PHASE 3: DỰ ÁN TỔNG HỢP CAPSTONE (FINAL MASTER DIPLOMA 🎓)
*   [ ] **Module 8: Trạm Giám sát & Điều khiển Vệ tinh / Drone (Autonomous Satellite Ground Station)**
    *   Xây dựng một hệ thống hoàn chỉnh kết hợp **TẤT CẢ** 7 Module:
        *   Tầng dưới: Đọc gói tin nhị phân cảm biến (Module 6).
        *   Tầng xử lý: Đa luồng/Đa nhân tính toán quỹ đạo (Module 5).
        *   Tầng mạng: Bắn dữ liệu telemetry qua TCP Socket tới client (Module 3).
        *   Tầng kiểm thử: Tự động test toàn bộ hệ thống trên GitHub Actions (Module 7).
