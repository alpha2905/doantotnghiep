# -*- coding: utf-8 -*-
"""
forecaster.py — Hybrid Forecast Engine (LSTM + Baseline)

Mục tiêu (theo góp ý hội đồng + docs/REWRITE_PLAN.md):
1. Không "giấu" số liệu: mọi phương pháp (LSTM, Naive, Moving Average, Hybrid) đều được
   đánh giá trên CÙNG một giao thức rolling-origin backtest (nhân quả, chỉ dùng quá khứ).
2. Chọn phương pháp dự báo theo bằng chứng định lượng trên chính chuỗi giá của sản phẩm
   (model selection), thay vì luôn dùng LSTM kể cả khi baseline tốt hơn.
3. Trả về dải tin cậy (confidence band) từ độ lệch chuẩn phần dư của phương pháp được chọn.

Lý do thiết kế: với dữ liệu giá TMĐT Việt Nam (nhiều ngày giữ nguyên giá, chuỗi ngắn),
baseline Naive thường đạt MAPE < 1% trong khi LSTM đạt ~12% (xem
backend/results/lstm_temporal_results.json). Hybrid Engine công khai so sánh và chọn
phương pháp tốt nhất, đồng thời ghi lại lý do chọn để hiển thị trên giao diện.
"""
import os
import re
import sys
from datetime import datetime, timedelta

import numpy as np

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import metrics  # noqa: E402  (thư viện metric chuẩn của project)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "forecast_config.yaml")

# Cấu hình mặc định (dùng khi không đọc được file YAML)
DEFAULT_CONFIG = {
    "look_back": 5,
    "min_points_for_lstm": 5,
    "min_backtest_samples": 2,
    "band_z": 1.28,
    "flat_ratio_threshold": 0.6,
    "cv_threshold": 0.01,
    "blend_deviation_threshold": 0.25,
    "blend_weight_lstm": 0.5,
    "chart_max_days": 30,
    "default_chart_days": 7,
}

_config_cache = None


def load_config(force=False):
    """Đọc config/forecast_config.yaml (mỗi key có 'value' + 'rationale')."""
    global _config_cache
    if _config_cache is not None and not force:
        return _config_cache

    cfg = dict(DEFAULT_CONFIG)
    if yaml is not None:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            for key, item in (raw.get("forecast") or {}).items():
                if isinstance(item, dict) and "value" in item:
                    cfg[key] = item["value"]
                elif not isinstance(item, dict):
                    cfg[key] = item
        except FileNotFoundError:
            print(f"[forecaster] Không thấy {CONFIG_PATH} -> dùng cấu hình mặc định")
        except Exception as e:
            print(f"[forecaster] Lỗi đọc config ({e}) -> dùng cấu hình mặc định")
    _config_cache = cfg
    return cfg


def get_config_rationale():
    """Trả về rationale của từng tham số (dùng cho dashboard / Chương 4)."""
    out = {}
    if yaml is None:
        return out
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        for key, item in (raw.get("forecast") or {}).items():
            if isinstance(item, dict):
                out[key] = {"value": item.get("value"), "rationale": item.get("rationale", "")}
    except Exception:
        return {}
    return out


# ============================================================
# 1. TIỀN XỬ LÝ CHUỖI GIÁ
# ============================================================
def parse_price(price):
    """Chuyển '29.990.000₫' -> 29990000.

    (Bản sao có chủ đích của main.parse_price để module này không phụ thuộc vòng vào main.py)
    """
    if not price:
        return 0
    digits = re.sub(r"[^\d]", "", str(price))
    if not digits:
        return 0
    try:
        return int(digits)
    except ValueError:
        return 0


def to_date_str(value):
    """Chuẩn hoá scraped_at (datetime | str) -> 'YYYY-MM-DD'."""
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def daily_price_map(price_history):
    """Gom lịch sử giá thô -> {ngày: giá} (ngày trùng thì lấy mốc mới nhất)."""
    prices = {}
    for h in price_history or []:
        if not isinstance(h, dict):
            continue
        value = parse_price(h.get("price") or h.get("price_number") or h.get("price_value") or "")
        if value <= 0:
            continue
        date_str = to_date_str(h.get("scraped_at") or h.get("date"))
        if not date_str:
            continue
        prices[date_str] = value
    return prices


def distinct_prices(price_history):
    """Danh sách giá theo thứ tự thời gian (mỗi ngày 1 mốc) — dùng cho LSTM."""
    prices = daily_price_map(price_history)
    return [prices[d] for d in sorted(prices.keys())]


def build_daily_series(price_history, days=None, end_date=None, cfg=None):
    """Chuỗi giá liên tục `days` ngày gần nhất (mặc định lấy từ config).

    Trả về đầy đủ cờ để giao diện KHÔNG vẽ dữ liệu giả như thật:
    - observed[i] = True -> ngày đó có mốc giá thật
    - filled[i]   = True -> ngày đó chưa có mốc giá, phải kế thừa giá trước đó
    """
    cfg = cfg or load_config()
    if days is None:
        days = int(cfg.get("chart_max_days", 30))
    days = max(1, int(days))

    prices = daily_price_map(price_history)
    if end_date is None:
        end_dt = datetime.now()
    elif isinstance(end_date, str):
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = end_date

    date_list = [(end_dt - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(days - 1, -1, -1)]

    dates, values, observed, filled = [], [], [], []
    # Khởi tạo last_valid bằng giá mới nhất trước cửa sổ (nếu có)
    last_valid = None
    sorted_dates = sorted(prices.keys())
    if sorted_dates:
        # Tìm giá gần nhất trước hoặc bằng ngày bắt đầu cửa sổ
        window_start = date_list[-1]  # ngày cũ nhất trong cửa sổ
        for d in sorted_dates:
            if d <= window_start:
                last_valid = prices[d]
            else:
                break
    # Fallback: nếu vẫn null, dùng giá mới nhất toàn bộ
    if last_valid is None and sorted_dates:
        last_valid = prices[sorted_dates[-1]]

    for d in date_list:
        value = prices.get(d)
        if value and value > 0:
            last_valid = value
            dates.append(d)
            values.append(value)
            observed.append(True)
            filled.append(False)
        else:
            dates.append(d)
            values.append(last_valid)
            observed.append(False)
            filled.append(True)

    trailing = [v for v in values if v is not None]
    sorted_dates = sorted(prices.keys())
    return {
        "dates": dates,
        "labels": [f"{d[8:10]}/{d[5:7]}" for d in dates],
        "prices": values,
        "observed": observed,
        "filled": filled,
        "trailing": trailing,            # chuỗi liên tục (đã bù) dùng cho model
        "distinct_points": len(prices),   # số mốc giá THẬT trong toàn bộ lịch sử
        "window_points": int(sum(observed)),  # số mốc giá THẬT trong cửa sổ hiển thị
        "last_observed_date": (sorted_dates[-1] if sorted_dates else None),
    }


def profile_series(series):
    """Đặc trưng thống kê chuỗi giá: độ biến động, độ phẳng, xu hướng."""
    values = [float(v) for v in (series or []) if v is not None]
    n = len(values)
    if n == 0:
        return {
            "points": 0, "mean": 0, "std": 0, "cv": 0.0, "flat_ratio": 1.0,
            "slope_per_day": 0, "slope_pct_per_day": 0.0, "level": "không đủ dữ liệu",
        }

    arr = np.asarray(values, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    cv = (std / mean) if mean else 0.0
    diffs = np.diff(arr)
    flat_ratio = float(np.mean(diffs == 0)) if len(diffs) else 1.0
    slope = float(np.polyfit(np.arange(n, dtype=float), arr, 1)[0]) if n >= 2 else 0.0
    slope_pct = (slope / mean * 100) if mean else 0.0

    if cv <= 0.01:
        level = "rất ổn định"
    elif cv <= 0.03:
        level = "ổn định"
    elif cv <= 0.08:
        level = "biến động vừa"
    else:
        level = "biến động mạnh"

    return {
        "points": n,
        "mean": round(mean),
        "std": round(std),
        "cv": round(cv, 4),
        "flat_ratio": round(flat_ratio, 3),
        "slope_per_day": round(slope),
        "slope_pct_per_day": round(slope_pct, 3),
        "level": level,
    }


# ============================================================
# 2. CÁC PHƯƠNG PHÁP DỰ BÁO (1 bước, dùng cửa sổ quá khứ)
# ============================================================
BASELINE_KEYS = ["naive", "moving_avg_3", "moving_avg_7", "expanding_mean"]
ALL_METHOD_KEYS = ["lstm", "hybrid"] + BASELINE_KEYS

METHOD_NAMES = {
    "lstm": "LSTM 2 lớp",
    "hybrid": "Hybrid (LSTM + baseline)",
    "naive": "Naive (giá hôm qua)",
    "moving_avg_3": "Trung bình trượt 3 ngày",
    "moving_avg_7": "Trung bình trượt 7 ngày",
    "expanding_mean": "Trung bình tích luỹ",
}

# Thứ tự ưu tiên khi MAPE gần bằng nhau (Occam's razor: model đơn giản hơn được ưu tiên)
METHOD_RANK = {
    "naive": 0,
    "moving_avg_3": 1,
    "moving_avg_7": 2,
    "expanding_mean": 3,
    "hybrid": 4,
    "lstm": 5,
}


def baseline_value(key, window, history=None):
    """Giá trị dự báo của baseline cho bước tiếp theo."""
    if not window:
        return None
    if key == "naive":
        return int(window[-1])
    if key == "moving_avg_3":
        tail = window[-3:]
        return int(round(sum(tail) / len(tail)))
    if key == "moving_avg_7":
        tail = window[-7:]
        return int(round(sum(tail) / len(tail)))
    if key == "expanding_mean":
        src = history if history else window
        return int(round(sum(src) / len(src))) if src else None
    return None


def lstm_value(lstm_model, scaler, window, look_back):
    """Suy luận LSTM 1 bước. Trả về None nếu model/scaler không sẵn sàng hoặc lỗi."""
    if lstm_model is None or scaler is None:
        return None
    if not window or len(window) < look_back:
        return None
    try:
        X_input = np.array(window[-look_back:], dtype=float).reshape(-1, 1)
        X_scaled = scaler.transform(X_input)
        pred = lstm_model.predict(X_scaled.reshape(1, look_back, 1), verbose=0)
        value = int(round(float(scaler.inverse_transform(pred)[0][0])))
        return value if value > 0 else None
    except Exception as e:
        print(f"[forecaster] Lỗi suy luận LSTM: {e}")
        return None


def hybrid_value(lstm_pred, baseline_pred, window, cfg=None):
    """Hybrid Engine: chọn giữa LSTM và baseline theo đặc trưng CỦA QUÁ KHỨ (nhân quả).

    Quy tắc:
    - Chuỗi phẳng (nhiều ngày giữ nguyên giá) -> baseline (LSTM chỉ thêm nhiễu).
    - LSTM lệch baseline quá `blend_deviation_threshold` -> blend để tránh outlier.
    - Ngược lại -> dùng LSTM.
    """
    cfg = cfg or load_config()
    prof = profile_series(window)
    if lstm_pred is None:
        return baseline_pred, "lstm_unavailable", prof
    if baseline_pred is None:
        return lstm_pred, "baseline_unavailable", prof

    is_flat = (prof["flat_ratio"] >= float(cfg["flat_ratio_threshold"])) or \
              (prof["cv"] <= float(cfg["cv_threshold"]))
    if is_flat:
        return baseline_pred, "baseline_flat_series", prof

    deviation = abs(lstm_pred - baseline_pred) / baseline_pred if baseline_pred else 0.0
    if deviation > float(cfg["blend_deviation_threshold"]):
        w = float(cfg["blend_weight_lstm"])
        blended = int(round(w * lstm_pred + (1 - w) * baseline_pred))
        return blended, "blend_outlier", prof

    return lstm_pred, "lstm_selected", prof


def rolling_backtest(series, lstm_model=None, scaler=None, cfg=None, max_samples=120):
    """Rolling-origin backtest: mỗi bước i dùng cửa sổ quá khứ để dự báo giá[i].

    Mọi phương pháp (LSTM, Hybrid, Naive, MA3, MA7, Trung bình tích luỹ) dùng CHUNG
    một giao thức => so sánh công bằng, không có lookahead bias.
    """
    cfg = cfg or load_config()
    look_back = int(cfg["look_back"])
    arr = [int(v) for v in (series or []) if v is not None and v > 0]
    n = len(arr)

    out = {
        "protocol": "rolling_origin_backtest",
        "look_back": look_back,
        "series_points": n,
        "samples": 0,
        "models": [],
        "residual_std": {},
    }
    if n < look_back + 1:
        return out

    start = max(look_back, n - int(max_samples)) if max_samples else look_back
    pairs = {k: [] for k in ALL_METHOD_KEYS}
    hybrid_modes = {}

    for i in range(start, n):
        window = arr[i - look_back:i]
        history = arr[:i]
        true_next = arr[i]

        lstm_pred = lstm_value(lstm_model, scaler, window, look_back)
        naive_pred = baseline_value("naive", window)
        hybrid_pred, mode, _ = hybrid_value(lstm_pred, naive_pred, window, cfg)
        hybrid_modes[mode] = hybrid_modes.get(mode, 0) + 1

        candidates = {
            "lstm": lstm_pred,
            "hybrid": hybrid_pred,
            "naive": naive_pred,
            "moving_avg_3": baseline_value("moving_avg_3", window),
            "moving_avg_7": baseline_value("moving_avg_7", window),
            "expanding_mean": baseline_value("expanding_mean", window, history),
        }
        for key, pred in candidates.items():
            if pred is not None and pred > 0:
                pairs[key].append((true_next, pred))

    out["samples"] = len(pairs["naive"])
    out["hybrid_modes"] = hybrid_modes

    for key in ALL_METHOD_KEYS:
        plist = pairs[key]
        if not plist:
            continue
        y_true = np.asarray([a for a, _ in plist], dtype=float)
        y_pred = np.asarray([p for _, p in plist], dtype=float)
        m = metrics.compute_all(y_true, y_pred, prefix="m")
        out["models"].append({
            "key": key,
            "name": METHOD_NAMES.get(key, key),
            "samples": len(plist),
            "mae": round(m["m_mae"]),
            "rmse": round(m["m_rmse"]),
            "mape": round(m["m_mape"], 3),
            "smape": round(m["m_smape"], 3),
            "direction_accuracy": round(m["m_direction_accuracy"] * 100, 1),
            "selected": False,
        })
        out["residual_std"][key] = float(np.std(y_true - y_pred))

    out["models"].sort(key=lambda x: x["mape"])
    return out


# ============================================================
# 3. MODEL SELECTION + DỰ BÁO 1 BƯỚC (PUBLIC API)
# ============================================================
HYBRID_MODE_NOTES = {
    "baseline_flat_series": "Giá các ngày gần đây gần như không đổi -> baseline Naive đủ tốt, LSTM chỉ thêm nhiễu.",
    "blend_outlier": "LSTM lệch baseline quá ngưỡng an toàn -> trộn 50/50 để giảm rủi ro outlier.",
    "lstm_selected": "Chuỗi giá có biến động và LSTM nằm trong ngưỡng hợp lý -> dùng LSTM.",
    "lstm_unavailable": "Không nạp được model LSTM -> dùng baseline.",
    "baseline_unavailable": "Không tính được baseline -> dùng LSTM.",
}

# MAPE chênh lệch dưới ngưỡng này được coi là "tương đương" -> ưu tiên model đơn giản hơn
MAPE_TIE_EPS = 0.05


def select_method(backtest, profile, cfg=None):
    """Chọn phương pháp dự báo dựa trên rolling backtest (min MAPE, Occam's razor)."""
    cfg = cfg or load_config()
    models = backtest.get("models") or []
    samples = int(backtest.get("samples") or 0)

    is_flat = (profile.get("flat_ratio", 1.0) >= float(cfg["flat_ratio_threshold"])) or \
              (profile.get("cv", 1.0) <= float(cfg["cv_threshold"]))

    if samples < int(cfg["min_backtest_samples"]) or not models:
        if is_flat:
            return "naive", (
                f"Chỉ có {samples} mẫu backtest (chưa đủ {int(cfg['min_backtest_samples'])} mẫu) "
                "và chuỗi giá gần như không đổi -> dùng baseline Naive (giá hôm qua)."
            ), None
        return "hybrid", (
            f"Chỉ có {samples} mẫu backtest (chưa đủ để so sánh thống kê) "
            "nhưng chuỗi giá có biến động -> dùng Hybrid Engine (LSTM + baseline)."
        ), None

    best = models[0]
    tied = [m for m in models if (m["mape"] - best["mape"]) <= MAPE_TIE_EPS]
    tied.sort(key=lambda m: (METHOD_RANK.get(m["key"], 9), m["mape"]))
    chosen = tied[0]

    reason = (
        f"Rolling-origin backtest trên {chosen['samples']} mẫu: "
        f"{chosen['name']} đạt MAPE thấp nhất ({chosen['mape']}%), "
        f"MAE {chosen['mae']:,}đ, đúng hướng {chosen['direction_accuracy']}%."
    )
    if chosen["key"] != best["key"]:
        reason += (
            f" (Chênh lệch MAPE so với {best['name']} < {MAPE_TIE_EPS} điểm % "
            "nên ưu tiên model đơn giản hơn.)"
        )
    return chosen["key"], reason, chosen


def forecast_next(series, lstm_model=None, scaler=None, cfg=None, max_backtest_samples=120):
    """Dự báo giá 1 bước kế tiếp + bảng so sánh phương pháp (JSON-serializable)."""
    cfg = cfg or load_config()
    look_back = int(cfg["look_back"])
    band_z = float(cfg["band_z"])
    arr = [int(v) for v in (series or []) if v is not None and v > 0]
    n = len(arr)
    profile = profile_series(arr)

    payload = {
        "look_back": look_back,
        "profile": profile,
        "models_compared": [],
        "hybrid_mode": None,
        "hybrid_note": None,
        "is_lstm_used": False,
        "eval_protocol": "rolling_origin_backtest",
        "eval_note": (
            "Chỉ số được tính bằng rolling-origin backtest trên chính chuỗi giá của sản phẩm "
            "(mỗi bước chỉ dùng dữ liệu quá khứ), áp dụng giống nhau cho mọi phương pháp."
        ),
    }

    # ---- Chưa đủ lịch sử để chạy LSTM ----
    if n < look_back:
        last_price = int(arr[-1]) if n else None
        std = float(profile.get("std") or 0)
        payload.update({
            "forecast": last_price,
            "method": "insufficient_history",
            "method_name": "Chưa đủ lịch sử — dùng baseline (giá hôm qua)",
            "reason": (
                f"Sản phẩm chỉ có {n}/{look_back} mốc giá nên không tạo được cửa sổ đầu vào cho LSTM. "
                "Hệ thống trả về baseline Naive (giá hôm qua) và gắn cờ insufficient_history."
            ),
            "insufficient_history": True,
            "band": {
                "low": int(max(0, (last_price or 0) - band_z * std)),
                "high": int((last_price or 0) + band_z * std),
                "z": band_z,
                "residual_std": round(std),
                "confidence": 80,
            },
            "sample_size": 0,
        })
        return payload

    # ---- Backtest tất cả phương pháp trên cùng giao thức ----
    backtest = rolling_backtest(arr, lstm_model, scaler, cfg, max_samples=max_backtest_samples)
    method, reason, chosen = select_method(backtest, profile, cfg)

    window = arr[-look_back:]
    lstm_pred = lstm_value(lstm_model, scaler, window, look_back)
    naive_pred = baseline_value("naive", window)
    hybrid_pred, hybrid_mode, _ = hybrid_value(lstm_pred, naive_pred, window, cfg)

    candidates = {
        "lstm": lstm_pred,
        "hybrid": hybrid_pred,
        "naive": naive_pred,
        "moving_avg_3": baseline_value("moving_avg_3", window),
        "moving_avg_7": baseline_value("moving_avg_7", window),
        "expanding_mean": baseline_value("expanding_mean", window, arr),
    }

    forecast = candidates.get(method)
    if forecast is None or forecast <= 0:
        fallback_note = f"Không tính được giá trị của {METHOD_NAMES.get(method, method)} ở bước hiện tại"
        method = "naive" if naive_pred else "insufficient_history"
        forecast = naive_pred or arr[-1]
        reason = f"{fallback_note} -> dùng baseline Naive (giá hôm qua)."

    for m in backtest.get("models", []):
        m["selected"] = (m["key"] == method)

    residual_std = float(backtest.get("residual_std", {}).get(method) or 0.0)
    if residual_std <= 0:
        residual_std = float(profile.get("std") or 0)

    payload.update({
        "forecast": int(forecast),
        "method": method,
        "method_name": METHOD_NAMES.get(method, method) + (" (tham chiếu)" if chosen is None else ""),
        "reason": reason,
        "insufficient_history": False,
        "is_lstm_used": bool(lstm_pred is not None and method in ("lstm", "hybrid")),
        "hybrid_mode": hybrid_mode,
        "hybrid_note": HYBRID_MODE_NOTES.get(hybrid_mode),
        "band": {
            "low": int(max(0, forecast - band_z * residual_std)),
            "high": int(forecast + band_z * residual_std),
            "z": band_z,
            "residual_std": round(residual_std),
            "confidence": 80,
        },
        "models_compared": backtest.get("models", []),
        "sample_size": int(backtest.get("samples") or 0),
    })
    return payload


