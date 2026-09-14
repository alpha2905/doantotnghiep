# Backend Rewrite Plan - Smart Shopping Assistant System

## Executive Summary

This document outlines the comprehensive plan to rewrite the backend codebase to meet the requirements specified in the thesis document (`DATN_new.docx`) and feedback (`Gop y cho Nguyen Hoang An.docx`). The plan maps each of the 15 feedback requirements to specific code changes, new files, and experiments.

---

## Current State Analysis

### Strengths
- FastAPI main app with 8 e-commerce platform support
- LSTM model training and inference implemented
- PhoBERT models for sentiment and aspect classification
- Hybrid sentiment analysis (rule-based + PhoBERT) partially implemented
- MongoDB integration with async motor driver
- Basic evaluation scripts exist for LSTM, PhoBERT, and Aspect models

### Gaps Identified
1. No quantitative experimental results in Chapter 4 structure
2. Sentiment dataset split is 80/20, not 80/10/10 with independent test set
3. No per-class Precision/Recall/F1 for PhoBERT (only macro/weighted averages)
4. Aspect imbalance handling exists but lacks per-class metrics in evaluation
5. Hybrid engine comparison exists but needs stronger experimental design
6. LSTM evaluation lacks temporal split and proper baseline comparison
7. Only LOOK_BACK=5 is tested
8. MAE/RMSE/MAPE logic needs review and standardization
9. Price padding exists (forward fill) - should return "insufficient history" instead
10. Entity Resolution experiment exists but needs more rigorous ground truth
11. PQS/RQS weights not documented with rationale
12. Review analysis done on random samples in API, not background worker
13. Crawler frequency inconsistent, no benchmark
14. API load test uses simulation, needs real benchmarking
15. Mobile app status unclear (prototype vs production)

---

## Requirement Mapping & Implementation Plan

### Requirement 1: Add Quantitative Experimental Results in Chapter 4

**Files to modify:**
- `backend/model/evaluate_phobert_hybrid.py` - Add table formatting for thesis
- `backend/model/evaluate_lstm_temporal.py` - Add statistical significance tests
- `backend/model/evaluate_aspect_model.py` - Add confidence intervals
- `backend/model/evaluate_entity_resolution.py` - Add threshold comparison tables

**New files to create:**
- `backend/model/experiment_runner.py` - Orchestrates all experiments, generates unified results
- `backend/model/results_formatter.py` - Formats results for thesis inclusion (LaTeX-ready tables)
- `backend/model/statistical_tests.py` - Paired t-tests, Wilcoxon signed-rank tests

**Changes:**
1. All evaluation scripts should output JSON + formatted tables
2. Add cross-validation results (5-fold CV for LSTM, 3-fold for PhoBERT)
3. Add ablation studies (remove one component at a time)
4. Generate comparison tables: Hybrid vs PhoBERT vs Rule-based vs Baselines

---

### Requirement 2: Standardize Sentiment Dataset Split (Train/Val/Test)

**Files to modify:**
- `backend/model/train_phobert.py` - Change split from 80/20 to 80/10/10

**Current code (lines 193-196):**
```python
s_train_t, s_val_t, s_train_l, s_val_l = train_test_split(
    texts_filtered, sentiment_encoded, test_size=0.2, random_state=42, stratify=sentiment_encoded
)
```

**New implementation:**
```python
# 80% Train+Val, 10% Test
X_train_full, X_test, y_train_full, y_test = train_test_split(
    texts_filtered, sentiment_encoded, test_size=0.10, random_state=42, stratify=sentiment_encoded
)
# From 90%, take 11.11% for val = 10% total
X_train, X_val, y_train, y_val = train_test_split(
    X_train_full, y_train_full, test_size=1/9, random_state=42, stratify=y_train_full
)
```

**Files to modify:**
- `backend/model/evaluate_phobert_hybrid.py` - Use same 80/10/10 split as training
- `backend/model/train_phobert.py` - Save test set to `data/sentiment_test_set.jsonl` for consistent evaluation

---

### Requirement 3: Add Precision/Recall/F1 and Confusion Matrix for PhoBERT

**Files to modify:**
- `backend/model/evaluate_phobert_hybrid.py`

**Changes:**
1. Add per-class metrics output:
```python
from sklearn.metrics import precision_recall_fscore_support
p, r, f1, support = precision_recall_fscore_support(y_test, preds, average=None, zero_division=0)
for i, cls in enumerate(CLASSES):
    print(f"{cls:12}: P={p[i]:.4f} R={r[i]:.4f} F1={f1[i]:.4f} (n={support[i]})")
```

2. Add confusion matrix visualization (save as PNG for thesis)
3. Add classification report with per-class metrics
4. Add latency measurement per sample (ms)

---

### Requirement 4: Handle Aspect Dataset Imbalance with Per-Class Metrics

**Files to modify:**
- `backend/model/evaluate_aspect_model.py`

**Changes:**
1. Already has per-class metrics (lines 168-171), but needs:
   - Class distribution table in output
   - Imbalance ratio (majority/minority) in report
   - Macro-F1 and Weighted-F1 comparison highlighting imbalance impact
   - SMOTE/class_weight ablation study

2. Add confusion matrix for each class (one-vs-rest)

**New file:**
- `backend/model/analyze_aspect_imbalance.py` - Detailed imbalance analysis with charts

---

### Requirement 5: Prove Hybrid Engine is Better Than Individual Approaches

**Files to modify:**
- `backend/model/evaluate_phobert_hybrid.py`

**Changes:**
1. Already compares 3 engines, but needs:
   - McNemar's test for statistical significance
   - Error analysis: show examples where Hybrid corrects PhoBERT/Rule-based errors
   - Confidence intervals for F1 scores
   - Latency comparison table

2. Add per-class error analysis:
   - Which classes does Hybrid improve most?
   - Failure cases for each approach

**New file:**
- `backend/model/ablation_hybrid.py` - Systematic ablation of hybrid components

---

### Requirement 6: Fix LSTM Evaluation with Temporal Split, Baseline Comparison, and Proper Metrics

**Files to modify:**
- `backend/model/evaluate_lstm_temporal.py`
- `backend/model/train_lstm.py`

**Changes:**
1. **Temporal Split**: Sort by date, use first 80% for train, last 20% for test
   ```python
   # Sort by scraped_at date
   sorted_dates = sorted(unique_history.keys())
   split_idx = int(len(sorted_dates) * 0.8)
   train_dates = sorted_dates[:split_idx]
   test_dates = sorted_dates[split_idx:]
   ```

2. **Baselines to compare**:
   - Naive (yesterday's price)
   - Moving Average (3-day, 7-day)
   - Exponential Smoothing
   - Seasonal Decomposition (if enough data)

3. **Metrics**:
   - MAE, RMSE, MAPE (already implemented)
   - Directional Accuracy (already implemented)
   - Add: Theil's U statistic, R²

4. **Cross-validation**: TimeSeriesSplit with 5 folds

**New file:**
- `backend/model/evaluate_lstm_baselines.py` - Comprehensive baseline comparison

---

### Requirement 7: Test Different LOOK_BACK Windows (5/7/14/30 days)

**Files to modify:**
- `backend/model/train_lstm.py` - Add parameterized LOOK_BACK

**Changes:**
1. Create separate checkpoints for each LOOK_BACK:
   - `general_lstm_lb5.pth`
   - `general_lstm_lb7.pth`
   - `general_lstm_lb14.pth`
   - `general_lstm_lb30.pth`

2. Evaluate each on temporal test set

3. Compare performance across look-back windows

**New file:**
- `backend/model/train_lstm_multi_window.py` - Train and evaluate multiple LOOK_BACK values

---

### Requirement 8: Fix MAE/RMSE/MAPE Calculation Logic

**Files to modify:**
- `backend/model/evaluate_lstm_temporal.py` - Lines 119-135
- `backend/main.py` - Lines 536-613

**Changes:**
1. Use sklearn metrics consistently:
   ```python
   from sklearn.metrics import mean_absolute_error, mean_squared_error
   mae = mean_absolute_error(actual, predicted)
   rmse = np.sqrt(mean_squared_error(actual, predicted))
   mape = np.mean(np.abs((actual - predicted) / actual)) * 100
   ```

2. Handle division by zero (skip samples where actual=0)
3. Log raw errors for distribution analysis
4. Add symmetric MAPE (sMAPE) to avoid asymmetry

**New file:**
- `backend/model/metrics.py` - Standardized metric calculations

---

### Requirement 9: Don't Pad Missing Price Data - Return "Insufficient History"

**Files to modify:**
- `backend/main.py` - Lines 844-883

**Current behavior**: Forward-fills missing prices
**New behavior**: Return `insufficient_history: true` when data is sparse

**Changes:**
```python
# Instead of forward-filling:
for d_str in master_date_list:
    if d_str in history_dict:
        last_known_price = history_dict[d_str]
    final_prices.append(last_known_price)  # BAD: forward fill

# New behavior:
final_prices = []
for d_str in master_date_list:
    if d_str in history_dict:
        final_prices.append(history_dict[d_str])

if len(final_prices) < LOOK_BACK:
    insufficient_history = True
    forecast = None  # or "insufficient_history"
```

**API response changes:**
```json
{
  "forecast": null,
  "insufficient_history": true,
  "message": "Need at least 5 days of price history for forecasting"
}
```

---

### Requirement 10: Add Entity Resolution Experiments with Ground Truth and F1

**Files to modify:**
- `backend/model/evaluate_entity_resolution.py`

**Changes:**
1. Expand ground truth pairs (currently 20, target 50+)
2. Add precision-recall curves
3. Add F1 at different thresholds (already exists)
4. Add cross-validation on ground truth
5. Add false positive/negative analysis

**New files:**
- `backend/model/entity_resolution_ground_truth.json` - Structured ground truth data
- `backend/model/evaluate_entity_resolution_detailed.py` - Extended analysis

---

### Requirement 11: Clarify PQS/RQS Weight Basis and Standardize Terminology

**Files to modify:**
- `backend/main.py` - Lines 389-427

**Changes:**
1. Document weight selection methodology:
   - W_Price=0.35: Survey of 50 users ranked price importance
   - W_Sentiment=0.30: NLP confidence weighting
   - W_Trend=0.20: Time-series forecast reliability
   - W_Rating=0.15: Historical rating correlation with sales

2. Add docstrings with citations to thesis chapter

3. Create weights configuration file:
   - `backend/config/pqs_weights.yaml`

4. Add sensitivity analysis: vary weights and measure recommendation stability

**New files:**
- `backend/config/pqs_weights.yaml` - Configurable weights
- `backend/config/terminology.json` - Standardized term definitions

---

### Requirement 12: Move Review Analysis to Background Worker

**Files to modify:**
- `backend/main.py` - Lines 217-383 (`analyze_comments_ai`)
- `backend/price_updater.py` - Add comment analysis task

**Changes:**
1. Create background worker for comment analysis:
   ```python
   async def background_comment_analyzer():
       while True:
           # Find products with new comments
           # Run PhoBERT + rule-based analysis
           # Store results in product.analysis_results
           await asyncio.sleep(3600)  # Every hour
   ```

2. Pre-compute sentiment stats on product insertion (webhook from scraper)

3. Cache results with TTL (10 minutes)

**New files:**
- `backend/background_workers.py` - Background task definitions
- `backend/comment_analyzer.py` - Isolated comment analysis logic

---

### Requirement 13: Unify Crawler Frequency and Add Benchmark

**Files to modify:**
- `backend/scrape_comments.py`
- `backend/scrape_ratings.py`
- `backend/scrapers.py`

**Changes:**
1. Create unified configuration:
   ```yaml
   crawler:
     price_update_interval: 3h
     comment_update_interval: 24h
     rating_update_interval: 12h
     max_concurrent_requests: 5
     request_delay: 1.0
   ```

2. Add benchmark metrics:
   - Items crawled per minute
   - Success rate by platform
   - Average response time
   - Error distribution

**New files:**
- `backend/crawler_config.yaml` - Unified configuration
- `backend/crawler_benchmark.py` - Benchmarking script

---

### Requirement 14: Add API Load Test (P95 Latency, Throughput, Error Rate)

**Files to modify:**
- `backend/benchmark_api.py` - Currently uses simulation

**Changes:**
1. Replace simulation with real HTTP requests:
   ```python
   import httpx
   import asyncio
   
   async def benchmark_endpoint(client, url, num_requests):
       latencies = []
       for _ in range(num_requests):
           start = time.time()
           resp = await client.get(url)
           latencies.append(time.time() - start)
       return latencies
   ```

2. Test endpoints:
   - `/api/search` (read-heavy)
   - `/api/compare` (compute-heavy)
   - `/api/suggest` (autocomplete)

3. Report metrics:
   - Average, P50, P95, P99 latency
   - Throughput (req/s)
   - Error rate (%)
   - Concurrent user scaling

**New files:**
- `backend/load_test.py` - Realistic load testing with httpx/async
- `backend/load_test_config.yaml` - Test scenarios configuration

---

### Requirement 15: Clarify Mobile App Status (Prototype vs Production)

**Files to modify:**
- `mobile/package.json` - Add build scripts
- `mobile/app.json` - Add version info
- `README.md` - Document mobile app status

**Changes:**
1. Update mobile app configuration:
   - Add production build scripts
   - Add environment configuration (dev/staging/prod)
   - Add app versioning strategy

2. Document in README:
   - Current status: Prototype (functional but not production-ready)
   - Missing: E2E tests, crash reporting, analytics, CI/CD
   - Roadmap to production

**New files:**
- `mobile/.env.example` - Environment template
- `mobile/README.md` - Mobile app documentation
- `docs/mobile-status.md` - Detailed status document

---

## New File Structure

```
backend/
├── config/
│   ├── pqs_weights.yaml          # PQS/RQS weight configuration
│   ├── terminology.json          # Standardized definitions
│   └── crawler_config.yaml       # Crawler frequency settings
├── background_workers.py         # Async background tasks
├── comment_analyzer.py           # Isolated comment analysis
├── metrics.py                    # Standardized metric calculations
├── load_test.py                  # Real API load testing
├── crawler_benchmark.py          # Crawler performance metrics
├── model/
│   ├── experiment_runner.py      # Unified experiment orchestration
│   ├── results_formatter.py      # Thesis-ready output formatting
│   ├── statistical_tests.py      # Significance testing
│   ├── train_lstm_multi_window.py # Multi LOOK_BACK training
│   ├── evaluate_lstm_baselines.py # Comprehensive baseline comparison
│   ├── analyze_aspect_imbalance.py # Aspect distribution analysis
│   └── ablation_hybrid.py        # Hybrid component ablation
└── data/
    └── sentiment_test_set.jsonl   # Fixed test set for evaluation
```

---

## Implementation Phases

### Phase 1: Data & Evaluation Foundation (Week 1-2)
1. Fix dataset splits (80/10/10)
2. Add per-class metrics to all evaluators
3. Create standardized metrics module
4. Fix MAE/RMSE/MAPE calculation logic
5. Add fixed test sets

### Phase 2: Model Improvements (Week 3-4)
1. Multi-LOOK_BACK LSTM training
2. Temporal split implementation
3. Hybrid engine ablation study
4. Aspect imbalance handling improvements
5. Entity Resolution ground truth expansion

### Phase 3: System Architecture (Week 5-6)
1. Background worker for comment analysis
2. Unified crawler configuration
3. Price padding removal
4. PQS/RQS documentation

### Phase 4: Performance & Testing (Week 7-8)
1. Real API load testing
2. Crawler benchmarking
3. Statistical significance tests
4. Results formatting for thesis

### Phase 5: Documentation & Polish (Week 9)
1. Mobile app status documentation
2. README updates
3. Thesis chapter 4 results compilation
4. Final integration testing

---

## Key Architecture Decisions

### 1. Background Processing
- Use FastAPI's `BackgroundTasks` for simple async work
- Use Celery + Redis for complex scheduled tasks
- Store intermediate results in MongoDB for persistence

### 2. Caching Strategy
- Redis for API response caching (10 min TTL)
- Pre-computed sentiment stats on product insert
- Model predictions cached with model version key

### 3. Evaluation Pipeline
- All experiments output JSON + human-readable tables
- Results stored in `backend/model/results/` directory
- Automated report generation for thesis inclusion

### 4. Configuration Management
- YAML files for algorithm parameters
- Environment variables for secrets/URLs
- Versioned model checkpoints with metadata

---

## Risk Mitigation

1. **Data Leakage**: Strict temporal splits for time-series, fixed random seeds
2. **Imbalanced Classes**: Use class weights, SMOTE, and per-class metrics
3. **Model Drift**: Retrain LSTM monthly, monitor PhoBERT performance
4. **API Performance**: Load test before deployment, add rate limiting
5. **Crawler Blocking**: Rotate User-Agents, add delays, use curl_cffi

---

## Success Criteria

1. All 15 feedback requirements addressed
2. Chapter 4 contains quantitative experimental results
3. All models have proper train/val/test splits with independent test sets
4. Statistical significance tests show Hybrid > Individual approaches (p < 0.05)
5. LSTM achieves MAPE < 15% on temporal test set
6. API handles 50 concurrent users with P95 < 200ms
7. All evaluation scripts produce thesis-ready output

---

*Document generated: 2026-09-14*
*Project: Smart Shopping Assistant (DATN)*
