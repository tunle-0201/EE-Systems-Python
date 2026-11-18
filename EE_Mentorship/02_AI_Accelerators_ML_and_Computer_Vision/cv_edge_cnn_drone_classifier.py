"""
================================================================================
          MODULE H CAPSTONE FINALE: BỘ NÃO NƠ-RON AI CNN NHẬN DIỆN VẬT CẢN DRONE
================================================================================

TÍCH HỢP TOÀN BỘ CHUỖI MẠNG NƠ-RON AI CONVOLUTIONAL NEURAL NETWORK (CNN):
Tích hợp 2D Convolution + Max Pooling + Softmax thành Mạng CNN hoàn chỉnh.
"""

from cv_edge_convolution_2d import apply_2d_convolution
from cv_edge_max_pooling import apply_2x2_max_pooling
from cv_edge_soft_max import compute_softmax_probabilities
import numpy as np

def run_cnn_drone_obstacle_classifier(camera_frame_5x5, kernel_3x3, dense_weights):
    # 1. Convolution 2D Layer
    fmap = apply_2d_convolution(camera_frame_5x5, kernel_3x3)
    
    # 2. Max Pooling Layer (Biến 3x3 thành 1x1 bằng max)
    pooled_val = np.max(fmap)
    
    # 3. Dense Classification Layer
    logits = dense_weights * pooled_val
    
    # 4. Softmax Probability Layer
    probs = compute_softmax_probabilities(logits)
    predicted_class = np.argmax(probs)
    return predicted_class, probs


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE H CAPSTONE: REAL-TIME CNN DRONE OBSTACLE ENGINE")
    print("=========================================================\n")
    
    frame = np.ones((5, 5), dtype=np.float32) * 10.0
    k = np.ones((3, 3), dtype=np.float32)
    weights = np.array([3.0, 1.0, 0.5]) # Lớp 0 (Vật cản) có trọng số cao nhất
    
    pred_cls, probabilities = run_cnn_drone_obstacle_classifier(frame, k, weights)
    
    print("1. KET QUA HOAT DONG BO NAO MANG NO-RON AI CNN REAL-TIME:")
    print(f"   -> Lop vat the du doan (Class) : {pred_cls} (0: Vat can nguy hiem!)")
    print(f"   -> Mua xac suat % (Softmax)    : {probabilities * 100.0}")
    
    assert pred_cls == 0, "Loi Capstone CNN Engine!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE H: EMBEDDED CNN VISION!")
    print("=========================================================")
