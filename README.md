# 🚀 EE Systems Engineering & Pure Python Architecture

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Domain](https://img.shields.io/badge/Domain-Electrical%20Engineering%20%26%20Systems-green.svg)
![Status](https://img.shields.io/badge/Architecture-From%20Scratch-orange.svg)

Hồ sơ dự án kỹ thuật nền tảng, tập trung vào **Quản lý bộ nhớ RAM**, **Kiến trúc luồng xử lý CPU**, **Lập trình mạng tầng Socket thô**, và **Đa xử lý đa nhân (Concurrency & Parallelism)**.

Tất cả các module được xây dựng thuần bằng **Pure Python** (không sử dụng thư viện black-box cao cấp) để làm chủ bản chất vật lý của hệ thống máy tính.

---

## 🛠️ CẤU TRÚC HỆ THỐNG MODULES

```text
OneDrive/Python Mastering/
├── EE_Mentorship/
│   ├── milestone_2_4_async.py        # Module 2: Event-Driven & Asyncio Event Loop
│   ├── milestone_3_1_socket.py       # Module 3: Bytes Encoding & Physical Signals
│   ├── milestone_3_2_tcp.py          # Module 3: Low-Level TCP Client/Server Socket
│   ├── game_server.py                # Module 3: Multiplayer Engine (RAM State & Broadcasting)
│   ├── game_client.py                # Module 3: Async Terminal Game Client
│   ├── game_server_ai.py             # Module 4: Raw HTTP REST API & JSON Serialization
│   ├── smart_home.py                 # Module 5: OOP Hardware Abstraction & State
│   ├── smart_home_inheritance.py     # Module 5: OOP Inheritance & PWM Duty-Cycle Control
│   ├── milestone_5_2_thread.py       # Module 5: Multithreading, Shared Heap & Mutex Locks
│   └── milestone_5_3_process.py      # Module 5: Multiprocessing, CPU Cores & IPC Queues
├── flight_recorder.py                # Milestone Project: Closed-Loop System Architecture
├── .gitignore                        # Git Shield Configuration
└── README.md                         # Portfolio Documentation
```

---

## 🔬 TÓM TẮT NĂNG LỰC KỸ THUẬT (TECHNICAL COMPETENCIES)

### 1. Quản Lý Bộ Nhớ & Con Trỏ (RAM & Pointers)
*   **Heap Allocation & Pointers:** Hiểu bản chất biến là con trỏ lưu địa chỉ ô nhớ vật lý (`0x1000`). Phân biệt tác động giữa **Shallow Copy** (`copy()`) và **Deep Copy** (`deepcopy()`) trên cấu trúc dữ liệu lồng nhau.
*   **Hash Maps & Collisions:** Giải mã cơ chế băm dữ liệu trong Dictionary và thuật toán xử lý chập ô nhớ **Open Addressing (Linear Probing)**.

### 2. Lập Trình Bất Đồng Bộ & Luồng Sự Kiện (Event-Driven & Async)
*   **CPU Clock Cycles & Non-blocking:** Loại bỏ cái chết ngắt luồng (`time.sleep`) bằng tư duy đếm xung nhịp và **Event Loop**.
*   **Coroutine & `async/await`:** Giải phóng CPU nhường quyền (`Yield`) cho các tác vụ khác trong lúc chờ I/O thiết bị ngoại vi.

### 3. Giao Tiếp Mạng Tầng Socket (Low-Level Networking)
*   **Bytes & Encoding:** Mã hóa văn bản thành dãy Bytes thô (ASCII/UTF-8) đại diện cho xung điện High (+3.3V) / Low (0V).
*   **TCP/IP Socket Engine:** Tự phát triển máy chủ Multiplayer Real-time sử dụng địa chỉ IP vật lý và phân luồng Cổng mạng (PORT).

### 4. Thiết Kế Hướng Đối Tượng (Hardware OOP & Abstraction)
*   **Class vs Instance:** Phân bổ vùng nhớ RAM giữa bản thiết kế chung (Class) và đối tượng vật lý (Instance).
*   **PWM Duty Cycle Control:** Kế thừa Class và mô phỏng tín hiệu **Điều rộng xung (Pulse Width Modulation)** kiểm soát công suất thiết bị điện.

### 5. Xử Lý Song Song & Đa Nhân (Concurrency & Parallelism)
*   **Multithreading & Mutex Locks:** Quản lý nhiều công nhân dùng chung bộ nhớ Heap, sử dụng `threading.Lock()` triệt tiêu thảm họa tranh chấp RAM **Race Condition**.
*   **Multiprocessing & IPC Queues:** Bẻ gãy xích khóa GIL của Python để vắt kiệt 100% sức mạnh đa nhân CPU, truyền thông điệp liên tiến trình qua **IPC (Inter-Process Communication)**.

---

## ⚡ HƯỚNG DẪN KHỞI CHẠY (QUICK START)

### 1. Khởi tạo môi trường ảo (Virtual Environment)
```bash
python -m venv .venv
# Trên Windows PowerShell:
.\.venv\Scripts\Activate.ps1
```

### 2. Chạy thử nghiệm Game Server Multiplayer & AI Boss
```bash
# Khởi động Game Server
python EE_Mentorship/game_server_ai.py

# Mở cửa sổ Terminal mới để kết nối Client vào chơi
python EE_Mentorship/game_client.py
```

---

## 👤 AUTHOR
*   **Lê Đắc Anh Tuấn** - Student of Electrical Engineering (EE)
