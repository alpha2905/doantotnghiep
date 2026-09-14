# -*- coding: utf-8 -*-
"""
Standardized metrics cho đánh giá mô hình dự báo giá.
MAE, RMSE, MAPE, sMAPE, Direction Accuracy.
"""
import numpy as np
from typing import Dict, Tuple, Optional


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error (%).
    Tránh chia cho 0: bỏ qua các giá trị thực tế = 0.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not np.any(mask):
        return float('inf')
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Symmetric Mean Absolute Percentage Error (%).
    Xử lý tốt hơn MAPE khi có giá trị thực tế gần 0.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    mask = denom != 0
    if not np.any(mask):
        return float('inf')
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask]) / denom[mask]) * 100)


def direction_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Direction Accuracy: tỷ lệ dự đoán đúng chiều biến động giá.
    1.0 = dự đoán đúng 100% chiều tăng/giảm.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) < 2:
        return 0.0
    true_diff = np.diff(y_true)
    pred_diff = np.diff(y_pred)
    true_dir = np.sign(true_diff)
    pred_dir = np.sign(pred_diff)
    mask = true_dir != 0
    if not np.any(mask):
        return 0.0
    return float(np.mean(true_dir[mask] == pred_dir[mask]))


def compute_all(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    prefix: str = ""
) -> Dict[str, float]:
    """Tính toán tất cả metrics trả về dict."""
    sep = "_" if prefix else ""
    return {
        f"{prefix}{sep}mae": mae(y_true, y_pred),
        f"{prefix}{sep}rmse": rmse(y_true, y_pred),
        f"{prefix}{sep}mape": mape(y_true, y_pred),
        f"{prefix}{sep}smape": smape(y_true, y_pred),
        f"{prefix}{sep}direction_accuracy": direction_accuracy(y_true, y_pred),
    }


def baseline_naive(y_true: np.ndarray) -> np.ndarray:
    """Naive Forecast: giá ngày mai = giá hôm nay."""
    y_true = np.asarray(y_true, dtype=float)
    return np.roll(y_true, -1)


def baseline_ma(y_true: np.ndarray, window: int = 3) -> np.ndarray:
    """Moving Average: giá ngày mai = trung bình window ngày cuối."""
    y_true = np.asarray(y_true, dtype=float)
    preds = np.zeros_like(y_true)
    for i in range(len(y_true)):
        if i < window:
            preds[i] = np.mean(y_true[:max(1, i+1)])
        else:
            preds[i] = np.mean(y_true[i-window:i])
    return preds


def baseline_last_value(y_true: np.ndarray) -> np.ndarray:
    """Last Value: giá ngày mai = giá cuối cùng trong lịch sử."""
    y_true = np.asarray(y_true, dtype=float)
    return np.full_like(y_true, y_true[-1] if len(y_true) > 0 else 0)


def evaluate_baselines(y_true: np.ndarray) -> Dict[str, Dict[str, float]]:
    """Đánh giá các baseline models."""
    results = {}
    baselines = {
        "naive": baseline_naive(y_true),
        "moving_avg_3": baseline_ma(y_true, window=3),
        "moving_avg_7": baseline_ma(y_true, window=7),
        "last_value": baseline_last_value(y_true),
    }
    for name, preds in baselines.items():
        results[name] = compute_all(y_true, preds, prefix=name)
    return results


def format_metrics(metrics: Dict[str, float], indent: str = "  ") -> str:
    """Format metrics thành string để in ra console."""
    lines = []
    for k, v in metrics.items():
        if v == float('inf'):
            lines.append(f"{indent}{k}: inf")
        else:
            lines.append(f"{indent}{k}: {v:.4f}")
    return "\n".join(lines)
