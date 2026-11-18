# SƯ MÔN EE MENTORSHIP: OẮN TẬP TỔNG KẾT MODULE 5
## LẬP TRÌNH HƯỚNG ĐỐI TƯỢNG (OOP) & KIẾN TRÚC XỬ LÝ ĐA NHÂN (MULTITHREADING/MULTIPROCESSING)

---

## 📌 PHẦN 1: LẬP TRÌNH HƯỚNG ĐỐI TƯỢNG (OOP) DƯỚI GÓC NHÌN RAM

### 1. Bản vẽ (Class) vs Linh kiện vật lý (Instance/Object)
*   **Class (Lớp):** Là bản thiết kế mạch in (PCB Layout). Nằm tĩnh trên bộ nhớ mã nguồn, chưa chiếm dung lượng dữ liệu trên Heap và chưa có dòng điện chạy qua.
*   **Instance (Thực thể):** Là linh kiện thật được sản xuất từ bản vẽ. Mỗi Instance khi khởi tạo (`Device()`) sẽ được Hệ điều hành cắt riêng một khối nhớ vật lý trên vùng **Heap** của RAM.

### 2. Từ khóa `self` là gì?
*   **Bản chất:** `self` chính là **địa chỉ con trỏ vật lý (pointer)** trỏ vào chính khối nhớ RAM của thực thể đó.
*   Khi gọi `device_A.toggle()`, Python thực chất chạy lệnh `IoTDevice.toggle(self=device_A)`. CPU nhìn vào địa chỉ `self` để biết chính xác phải đổi trạng thái của ô nhớ `device_A` chứ không đụng chạm tới `device_B`.

### 3. Tính Kế thừa (Inheritance) & `super()`
*   Class con (`DimmableLED`) kế thừa Class cha (`IoTDevice`) sẽ sở hữu một khối RAM mở rộng chứa cả thuộc tính của Cha lẫn Con.
*   Lệnh `super().__init__(name, pin)` gọi hàm khởi tạo của Cha để tô vẽ các thuộc tính chung (`name`, `pin`, `status`) lên khối nhớ của Con trước, rồi Con mới vẽ tiếp thuộc tính riêng (`brightness`).
*   **Ứng dụng EE:** Giả lập điều rộng xung **PWM (Pulse Width Modulation)** để thay đổi Duty Cycle từ 0% đến 100%, kẹp biên bằng `max(0, min(level, 100))`.

---

## 📌 PHẦN 2: MULTI-THREADING (ĐA LUỒNG) - NHIỀU CÔNG NHÂN TRONG 1 NHÀ MÁY

```
 ┌───────────────────────────────────────────────────────────┐
 │ PROCESS (Nhà máy) - Bộ nhớ RAM Heap dùng chung            │
 │                                                           │
 │ ┌──────────────────────┐         ┌──────────────────────┐ │
 │ │ Thread 1 (Công nhân) ├──┐   ┌──┤ Thread 2 (Công nhân) │ │
 │ └──────────────────────┘  │   │  └──────────────────────┘ │
 │                           ▼   ▼                           │
 │                 [ sensor_data = [] ]                      │
 └───────────────────────────────────────────────────────────┘
```

*   **Bản chất:** Các Luồng (Threads) chạy song song bên trong **cùng một Tiến trình (Process)**.
*   **Bộ nhớ:** Dùng chung toàn bộ vùng nhớ Heap. Truy cập và chia sẻ dữ liệu cực kỳ nhanh thông qua các con trỏ biến chung.
*   **Hiện tượng Tranh chấp (Race Condition):** Khi nhiều Luồng cùng ghi/sửa một ô nhớ RAM tại cùng một microsecond, dữ liệu sẽ bị ghi đè và hư hại.
*   **Giải pháp:** Dùng **`threading.Lock()` (Bộ khóa Mutex)**. Luồng nào muốn ghi phải giật khóa (`with data_lock:`), bắt các luồng khác dừng lại chờ (Blocked) cho tới khi ghi xong nhả khóa.
*   **Trường hợp sử dụng:** Thích hợp cho các tác vụ **I/O-bound** (chờ cảm biến phản hồi, đọc ghi file, tải dữ liệu mạng).

---

## 📌 PHẦN 3: MULTI-PROCESSING (ĐA TIẾN TRÌNH) - NHIỀU NHÀ MÁY ĐỘC LẬP

```
 ┌─────────────────────────────┐           ┌─────────────────────────────┐
 │    PROCESS 1 (Nhà máy 1)    │           │    PROCESS 2 (Nhà máy 2)    │
 │ - Nhân CPU 1                │           │ - Nhân CPU 2                │
 │ - RAM Heap riêng            │           │ - RAM Heap riêng            │
 └──────────────┬──────────────┘           └──────────────┬──────────────┘
                │                                         │
                └──────────────► [ Queue ] ───────────────┘
                              (Hộp thư IPC)
```

*   **Bản chất:** Mỗi Tiến trình (Process) là một cỗ máy độc lập, có không gian RAM cô lập完全 và chạy trên một **Nhân CPU vật lý (Core) riêng biệt**.
*   **Phá vỡ xích khóa GIL của Python:** Vì mỗi Process có một trình biên dịch Python và khóa GIL riêng, nó cho phép vắt kiệt 100% công suất của toàn bộ các Nhân CPU cùng lúc.
*   **Tính cô lập an toàn (Fault Isolation):** Process 1 nổ tung (crash), Process 2 vẫn trơ trơ sống sót và hoạt động bình thường.
*   **Truyền thông IPC (Inter-Process Communication):** Do RAM bị cô lập, các Process không thể đọc biến của nhau. Chúng trao đổi dữ liệu qua **`multiprocessing.Queue()`** (Hộp thư trung chuyển). 
    *   Process 1 nhét dữ liệu vào: `queue.put(data)`
    *   Process 2 đứng chờ rút thư ra: `data = queue.get()`
*   **Trường hợp sử dụng:** Thích hợp cho các tác vụ **CPU-bound** (tính toán toán học ma trận nặng, đồ họa 3D, xử lý ảnh camera, AI).

---

## 🎯 BẢNG SO SÁNH BẢN CHẤT KỸ THUẬT

| Tiêu chí | Multi-threading (Đa luồng) | Multi-processing (Đa tiến trình) |
| :--- | :--- | :--- |
| **Hình ảnh thực tế** | Nhiều công nhân chung 1 nhà máy | Nhiều nhà máy riêng biệt |
| **Bộ nhớ RAM** | Dùng chung vùng nhớ Heap | Cô lập hoàn toàn |
| **Chia sẻ dữ liệu** | Rất dễ (dùng biến chung + Lock) | Phải dùng Hộp thư IPC (Queue/Pipe) |
| **Khóa GIL Python** | Bị giới hạn (chỉ 1 luồng chạy code Python/thời điểm) | Phá vỡ hoàn toàn (mỗi nhân 1 Process) |
| **Độ an toàn** | 1 Luồng lỗi có thể kéo cả Process sập | 1 Process sập không ảnh hưởng Process khác |
| **Tác vụ tối ưu** | I/O-bound (Mạng, Cảm biến, File) | CPU-bound (Xử lý ảnh, AI, Toán ma trận) |
