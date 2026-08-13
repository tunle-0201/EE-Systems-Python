"""
================================================================================
          MODULE D: DEEP LEARNING & NEURAL NETWORKS (PYTORCH)
              MILESTONE D.8: PYTORCH TENSORS VÀ TỰ ĐỘNG LẤY ĐẠO HÀM (AUTOGRAD)
================================================================================

BƯỚC 1: TRANG BỊ HỘP CÔNG CỤ PYTORCH AUTOGRAD (TOOLBOX MASTERY)

TẠI SAO KỸ SƯ AI DÙNG PYTORCH THAY VÌ TÍNH ĐẠO HÀM TAY BẰNG NUMPY?
Trong Mạng AI sâu 100 lớp, tính đạo hàm bằng tay là điều không thể.
PyTorch cung cấp tính năng **Autograd (Automatic Differentiation)**:

1. Tạo Tensor yêu cầu theo dõi Đạo hàm:
   `W = torch.tensor([1.0], requires_grad=True)`
2. Tính toán Forward Pass tạo Đồ thị tính toán (Computational Graph):
   `y_pred = X * W`
   `loss = (y_pred - y) ** 2`
3. Kích hoạt Đạo hàm tự động bằng 1 dòng lệnh thần thánh:
   `loss.backward()`
4. Rút kết quả đạo hàm dL/dW ra khỏi RAM:
   `gradient = W.grad`

BÀI TOÁN THỰC TẾ:
Cho X = torch.tensor([2.0]), y_true = torch.tensor([10.0]).
Cho Trọng số W = torch.tensor([1.0], requires_grad=True).

Nhiệm vụ của Kỹ sư trưởng trong hàm `compute_pytorch_autograd(X, y, W)`:
1. y_pred = X * W
2. loss = (y_pred - y) ** 2
3. loss.backward()
4. Trả về: loss.item(), W.grad.item()
"""

import numpy as np

# Mô phỏng thuật toán Autograd của PyTorch bằng Python thuần khi chưa cài PyTorch
class SimpleTensor:
    def __init__(self, data, requires_grad=False):
        self.data = float(data)
        self.requires_grad = requires_grad
        self.grad = 0.0

def compute_pytorch_autograd(X_val, y_val, W_val):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Autograd từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Tính y_pred = X_val * W_val
    - Tính loss = (y_pred - y_val) ** 2
    - Tính dL_dW = 2 * (y_pred - y_val) * X_val (Mô phỏng loss.backward())
    - Trả về: loss, dL_dW
    """
    y_pred = X_val * W_val
    loss = (y_pred - y_val) ** 2
    gradient = 2 * (y_pred - y_val) * X_val
    return loss, gradient


if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: PYTORCH AUTOGRAD & COMPUTATIONAL GRAPH")
    print("=========================================================\n")
    
    X_in = 2.0
    y_target = 10.0
    W_weight = 1.0
    
    loss_val, grad_val = compute_pytorch_autograd(X_in, y_target, W_weight)
    
    if loss_val is not None:
        print(f"1. KẾT QUẢ TỰ ĐỘNG TÍNH ĐẠO HÀM AUTOGRAD (COMPUTATIONAL GRAPH):")
        print(f"   -> Giá trị Sai số (Loss)            : {loss_val:.2f}")
        print(f"   -> Đạo hàm Autograd (W.grad / dL_dW): {grad_val:.2f}")
        
        # Kiểm tra tính chính xác (Loss = (2 - 10)^2 = 64, Grad = 2*(2-10)*2 = -32)
        assert abs(loss_val - 64.0) < 1e-5, "Lỗi tính Loss Autograd!"
        assert abs(grad_val - (-32.0)) < 1e-5, "Lỗi tính Gradient Autograd!"
        
        print("\n[THÀNH CÔNG] TRÒ ĐÃ LÀM CHỦ NGUYÊN LÝ TỰ ĐỘNG LẤY ĐẠO HÀM AUTOGRAD CỦA PYTORCH!")
