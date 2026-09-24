import os

path = 'e:/22050040 - Nguyen Hoang An/Code/ecommerce-price-comparison/design_analysis.svg'
os.makedirs(os.path.dirname(path), exist_ok=True)

svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1200" font-family="Segoe UI, Arial, sans-serif">
  <rect width="100%" height="100%" fill="#f8fafc"/>

  <!-- Header -->
  <text x="20" y="28" font-size="20" font-weight="bold" fill="#0f172a">Smart Shopping Assistant — Sơ đồ phân tích thiết kế hệ thống</text>
  <text x="20" y="48" font-size="13" fill="#475569">Nguyễn Hoàng An — 22050040 — GVHD: ThS. Dương Anh Tuấn</text>
  <text x="20" y="66" font-size="12" fill="#64748b">FastAPI + MongoDB Atlas + AI (PhoBERT/LSTM) + React Web + Expo Mobile</text>
  <line x1="20" y1="78" x2="1580" y2="78" stroke="#cbd5e1" stroke-width="1.5"/>

  <!-- ====== USER LAYER ====== -->
  <rect x="20" y="100" width="1560" height="110" rx="10" fill="#eff6ff" stroke="#93c5fd" stroke-width="1.5"/>
  <text x="40" y="125" font-size="15" font-weight="bold" fill="#1e40af">NGƯỜI DÙNG (User Layer)</text>
  <rect x="60" y="145" width="280" height="55" rx="6" fill="#ffffff" stroke="#bfdbfe" stroke-width="1"/>
  <text x="100" y="168" font-size="13" font-weight="bold" fill="#1e3a8a">🌐 Web App</text>
  <text x="100" y="186" font-size="11" fill="#475569">React 18 + Vite 5</text>
  <text x="100" y="200" font-size="11" fill="#475569">Recharts, Axios, Lucide</text>

  <rect x="370" y="145" width="280" height="55" rx="6" fill="#ffffff" stroke="#bfdbfe" stroke-width="1"/>
  <text x="410" y="168" font-size="13" font-weight="bold" fill="#1e3a8a">📱 Mobile App</text>
  <text x="410" y="186" font-size="11" fill="#475569">Expo / React Native 0.76</text>
  <text x="410" y="200" font-size="11" fill="#475569">React Navigation + Chart Kit</text>

  <rect x="680" y="145" width="280" height="55" rx="6" fill="#ffffff" stroke="#bfdbfe" stroke-width="1"/>
  <text x="720" y="168" font-size="13" font-weight="bold" fill="#1e3a8a">🤖 AI/NLP Engine</text>
  <text x="720" y="186" font-size="11" fill="#475569">PhoBERT + PyTorch LSTM</text>
  <text x="720" y="200" font-size="11" fill="#475569">Sentiment + Aspect + Forecast</text>

  <rect x="990" y="145" width="280" height="55" rx="6" fill="#ffffff" stroke="#bfdbfe" stroke-width="1"/>
  <text x="1030" y="168" font-size="13" font-weight="bold" fill="#1e3a8a">🕷️ Data Crawler</text>
  <text x="1030" y="186" font-size="11" fill="#475569">Playwright + BS4</text>
  <text x="1030" y="200" font-size="11" fill="#475569">8 E-commerce Platforms</text>

  <rect x="1300" y="145" width="240" height="55" rx="6" fill="#ffffff" stroke="#bfdbfe" stroke-width="1"/>
  <text x="1340" y="168" font-size="13" font-weight="bold" fill="#1e3a8a">🔔 Push Notify</text>
  <text x="1340" y="186" font-size="11" fill="#475569">Firebase + Expo Push</text>
  <text x="1340" y="200" font-size="11" fill="#475569">6 notification types</text>

  <!-- ====== PRESENTATION LAYER ====== -->
  <rect x="20" y="240" width="1560" height="180" rx="10" fill="#fefce8" stroke="#fde047" stroke-width="1.5"/>
  <text x="40" y="265" font-size="15" font-weight="bold" fill="#854d0e">LAYER TRÌNH DIỄN (Presentation Layer)</text>
  <rect x="60" y="285" width="470" height="120" rx="6" fill="#ffffff" stroke="#fde68a" stroke-width="1"/>
  <text x="80" y="308" font-size="13" font-weight="bold" fill="#78350f">🖥️ Web Frontend</text>
  <text x="80" y="326" font-size="11" fill="#475569">Header: Search + Dark/Light theme + Auth</text>
  <text x="80" y="340" font-size="11" fill="#475569">Hero Banner: Branding + Stats + AI chips</text>
  <text x="80" y="354" font-size="11" fill="#475569">Search Results: ProductCard grid (PQS, trend, LSTM chart, sentiment pie)</text>
  <text x="80" y="368" font-size="11" fill="#475569">Compare Modal: Side-by-side 2 products</text>
  <text x="80" y="382" font-size="11" fill="#475569">Panels: Favorites + Notifications + Auth Modal</text>

  <rect x="560" y="285" width="470" height="120" rx="6" fill="#ffffff" stroke="#fde68a" stroke-width="1"/>
  <text x="580" y="308" font-size="13" font-weight="bold" fill="#78350f">📲 Mobile App</text>
  <text x="580" y="326" font-size="11" fill="#475569">Native Stack: ProductDetail, Login</text>
  <text x="580" y="340" font-size="11" fill="#475569">Bottom Tabs: Home | Favorites | Notifications | Profile</text>
  <text x="580" y="354" font-size="11" fill="#475569">HomeScreen: Search + Pull-to-refresh + Popular chips</text>
  <text x="580" y="368" font-size="11" fill="#475569">ProductDetail: Price chart + Sentiment + LSTM metrics + Comments</text>
  <text x="580" y="382" font-size="11" fill="#475569">SecureStore JWT + Axios interceptor</text>

  <rect x="1060" y="285" width="480" height="120" rx="6" fill="#ffffff" stroke="#fde68a" stroke-width="1"/>
  <text x="1080" y="308" font-size="13" font-weight="bold" fill="#78350f">🔔 Notification UI</text>
  <text x="1080" y="326" font-size="11" fill="#475569">In-app notification list (6 types)</text>
  <text x="1080" y="340" font-size="11" fill="#475569">Foreground FCM toast (Web)</text>
  <text x="1080" y="354" font-size="11" fill="#475569">Expo Push (Mobile background)</text>
  <text x="1080" y="368" font-size="11" fill="#475569">Mark-all-read + deduplication by key</text>
  <text x="1080" y="382" font-size="11" fill="#475569">Service Worker (Web push)</text>

  <!-- ====== APPLICATION LAYER ====== -->
  <rect x="20" y="450" width="1560" height="200" rx="10" fill="#f0fdf4" stroke="#86efac" stroke-width="1.5"/>
  <text x="40" y="475" font-size="15" font-weight="bold" fill="#166534">LAYER ỨNG DỤNG (Application Layer — FastAPI Backend)</text>

  <rect x="60" y="495" width="380" height="145" rx="6" fill="#ffffff" stroke="#bbf7d0" stroke-width="1"/>
  <text x="80" y="518" font-size="13" font-weight="bold" fill="#14532d">🔍 Search & Compare</text>
  <text x="80" y="536" font-size="11" fill="#475569">GET /api/search — Regex 8 collections</text>
  <text x="80" y="550" font-size="11" fill="#475569">GET /api/suggest — Autocomplete (300ms)</text>
  <text x="80" y="564" font-size="11" fill="#475569">GET /api/compare — Full comparison</text>
  <text x="80" y="578" font-size="11" fill="#475569">Entity resolution + Model base match</text>
  <text x="80" y="592" font-size="11" fill="#475569">Cache TTL 600s by brand:name</text>

  <rect x="470" y="495" width="380" height="145" rx="6" fill="#ffffff" stroke="#bbf7d0" stroke-width="1"/>
  <text x="490" y="518" font-size="13" font-weight="bold" fill="#14532d">⭐ Scoring Engines</text>
  <text x="490" y="536" font-size="11" fill="#475569">PQS (0-100): rating×0.25 + sentiment×0.30</text>
  <text x="490" y="550" font-size="11" fill="#475569">RQS (0-5): per-comment quality</text>
  <text x="490" y="564" font-size="11" fill="#475569">calculate_price_stats() — min/avg/max</text>
  <text x="490" y="578" font-size="11" fill="#475569">get_buy_recommendation() — buy/wait/reject</text>
  <text x="490" y="592" font-size="11" fill="#475569">get_price_trend() — 5-level trend</text>

  <rect x="880" y="495" width="380" height="145" rx="6" fill="#ffffff" stroke="#bbf7d0" stroke-width="1"/>
  <text x="900" y="518" font-size="13" font-weight="bold" fill="#14532d">🔮 LSTM Forecast</text>
  <text x="900" y="536" font-size="11" fill="#475569">2-layer PyTorch LSTM (64→32 hidden)</text>
  <text x="900" y="550" font-size="11" fill="#475569">LOOK_BACK=5 days, dropout=0.2</text>
  <text x="900" y="564" font-size="11" fill="#475569">Off-by-one backtest: MAE/RMSE/MAPE</text>
  <text x="900" y="578" font-size="11" fill="#475569">Direction Accuracy metric</text>
  <text x="900" y="592" font-size="11" fill="#475569">Suppressed if history &lt; 5 days</text>

  <rect x="1290" y="495" width="290" height="145" rx="6" fill="#ffffff" stroke="#bbf7d0" stroke-width="1"/>
  <text x="1310" y="518" font-size="13" font-weight="bold" fill="#14532d">🔐 Auth & Admin</text>
  <text x="1310" y="536" font-size="11" fill="#475569">POST /api/auth/register</text>
  <text x="1310" y="550" font-size="11" fill="#475569">POST /api/auth/login → JWT</text>
  <text x="1310" y="564" font-size="11" fill="#475569">Favorites CRUD (JWT)</text>
  <text x="1310" y="578" font-size="11" fill="#475569">Notifications engine (6 types)</text>
  <text x="1310" y="592" font-size="11" fill="#475569">Admin: price update + stats</text>

  <!-- ====== DATA LAYER ====== -->
  <rect x="20" y="680" width="1560" height="150" rx="10" fill="#fdf2f8" stroke="#f9a8d4" stroke-width="1.5"/>
  <text x="40" y="705" font-size="15" font-weight="bold" fill="#831843">LAYER DỮ LIỆU (Data Layer — MongoDB Atlas)</text>
  <rect x="60" y="725" width="260" height="90" rx="6" fill="#ffffff" stroke="#fbcfe8" stroke-width="1"/>
  <text x="80" y="748" font-size="12" font-weight="bold" fill="#831843">8 Platform Collections</text>
  <text x="80" y="764" font-size="10" fill="#475569">fpt, tgdd, cellphones,</text>
  <text x="80" y="776" font-size="10" fill="#475569">hoangha, didongviet,</text>
  <text x="80" y="788" font-size="10" fill="#475569">viettelstore, clickbuy,</text>
  <text x="80" y="800" font-size="10" fill="#475569">mobilecity</text>

  <rect x="350" y="725" width="260" height="90" rx="6" fill="#ffffff" stroke="#fbcfe8" stroke-width="1"/>
  <text x="370" y="748" font-size="12" font-weight="bold" fill="#831843">users</text>
  <text x="370" y="764" font-size="10" fill="#475569">email, password_hash</text>
  <text x="370" y="776" font-size="10" fill="#475569">favorites[], fcm_tokens[]</text>
  <text x="370" y="788" font-size="10" fill="#475569">full_name, created_at</text>
  <text x="370" y="800" font-size="10" fill="#475569">JWT auth + SecureStore</text>

  <rect x="640" y="725" width="260" height="90" rx="6" fill="#ffffff" stroke="#fbcfe8" stroke-width="1"/>
  <text x="660" y="748" font-size="12" font-weight="bold" fill="#831843">notifications</text>
  <text x="660" y="764" font-size="10" fill="#475569">user_id, key (dedup)</text>
  <text x="660" y="776" font-size="10" fill="#475569">type: price_drop | deep_drop</text>
  <text x="660" y="788" font-size="10" fill="#475569">read: bool, created_at</text>
  <text x="660" y="800" font-size="10" fill="#475569">6 trigger types</text>

  <rect x="930" y="725" width="260" height="90" rx="6" fill="#ffffff" stroke="#fbcfe8" stroke-width="1"/>
  <text x="950" y="748" font-size="12" font-weight="bold" fill="#831843">Products Schema</text>
  <text x="950" y="764" font-size="10" fill="#475569">platform, brand, name</text>
  <text x="950" y="776" font-size="10" fill="#475569">model_base (entity res.)</text>
  <text x="950" y="788" font-size="10" fill="#475569">price_number, rating, sold_volume</text>
  <text x="950" y="800" font-size="10" fill="#475569">comments[], price_history[]</text>

  <rect x="1220" y="725" width="320" height="90" rx="6" fill="#ffffff" stroke="#fbcfe8" stroke-width="1"/>
  <text x="1240" y="748" font-size="12" font-weight="bold" fill="#831843">AI Models Storage</text>
  <text x="1240" y="764" font-size="10" fill="#475569">phobert_models/ (sentiment, aspect)</text>
  <text x="1240" y="776" font-size="10" fill="#475569">general_lstm_best.pth</text>
  <text x="1240" y="788" font-size="10" fill="#475569">general_scaler.pkl (joblib)</text>
  <text x="1240" y="800" font-size="10" fill="#475569">pqs_weights.yaml (config)</text>

  <!-- ====== AI ANALYSIS LAYER ====== -->
  <rect x="20" y="860" width="1560" height="160" rx="10" fill="#fae8ff" stroke="#e879f9" stroke-width="1.5"/>
  <text x="40" y="885" font-size="15" font-weight="bold" fill="#701a75">MODULE PHÂN TÍCH AI (AI Analysis Module)</text>
  <rect x="60" y="905" width="370" height="100" rx="6" fill="#ffffff" stroke="#f5d0fe" stroke-width="1"/>
  <text x="80" y="928" font-size="12" font-weight="bold" fill="#701a75">Hybrid Sentiment Engine</text>
  <text x="80" y="944" font-size="10" fill="#475569">analyze_comments_ai()</text>
  <text x="80" y="958" font-size="10" fill="#475569">Priority 1: Rule-based (~80 rules)</text>
  <text x="80" y="972" font-size="10" fill="#475569">Priority 2: PhoBERT fallback</text>
  <text x="80" y="986" font-size="10" fill="#475569">3-class: POSITIVE / NEUTRAL / NEGATIVE</text>

  <rect x="460" y="905" width="370" height="100" rx="6" fill="#ffffff" stroke="#f5d0fe" stroke-width="1"/>
  <text x="480" y="928" font-size="12" font-weight="bold" fill="#701a75">Aspect Classification</text>
  <text x="480" y="944" font-size="10" fill="#475569">PhoBERT 10-class aspect</text>
  <text x="480" y="958" font-size="10" fill="#475569">bảo_mật, camera, giá, hiệu_năng...</text>
  <text x="480" y="972" font-size="10" fill="#475569">RobertaForSequenceClassification</text>
  <text x="480" y="986" font-size="10" fill="#475569">Per-aspect sentiment aggregation</text>

  <rect x="860" y="905" width="370" height="100" rx="6" fill="#ffffff" stroke="#f5d0fe" stroke-width="1"/>
  <text x="880" y="928" font-size="12" font-weight="bold" fill="#701a75">LSTM Price Forecaster</text>
  <text x="880" y="944" font-size="10" fill="#475569">PyTorch 2-layer LSTM</text>
  <text x="880" y="958" font-size="10" fill="#475569">Input: 5-day price window</text>
  <text x="880" y="972" font-size="10" fill="#475569">Output: next-day price forecast</text>
  <text x="880" y="986" font-size="10" fill="#475569">Backtest: MAE, RMSE, MAPE, DirAcc</text>

  <rect x="1260" y="905" width="320" height="100" rx="6" fill="#ffffff" stroke="#f5d0fe" stroke-width="1"/>
  <text x="1280" y="928" font-size="12" font-weight="bold" fill="#701a75">Evaluation & Metrics</text>
  <text x="1280" y="944" font-size="10" fill="#475569">calculate_lstm_metrics()</text>
  <text x="1280" y="958" font-size="10" fill="#475569">standardized metrics.py</text>
  <text x="1280" y="972" font-size="10" fill="#475569">MAE / RMSE / MAPE / sMAPE</text>
  <text x="1280" y="986" font-size="10" fill="#475569">Direction Accuracy</text>

  <!-- ====== FLOW DIAGRAM ====== -->
  <rect x="20" y="1050" width="1560" height="130" rx="10" fill="#fff7ed" stroke="#fdba74" stroke-width="1.5"/>
  <text x="40" y="1075" font-size="15" font-weight="bold" fill="#7c2d12">LUỒNG DỮ LIỆU (Data Flow)</text>

  <!-- Flow boxes -->
  <rect x="60" y="1090" width="180" height="70" rx="6" fill="#ffffff" stroke="#fed7aa" stroke-width="1"/>
  <text x="80" y="1112" font-size="12" font-weight="bold" fill="#7c2d12">1. Crawler</text>
  <text x="80" y="1126" font-size="10" fill="#475569">Playwright scrapes 8</text>
  <text x="80" y="1140" font-size="10" fill="#475569">platforms → MongoDB</text>

  <rect x="280" y="1090" width="180" height="70" rx="6" fill="#ffffff" stroke="#fed7aa" stroke-width="1"/>
  <text x="300" y="1112" font-size="12" font-weight="bold" fill="#7c2d12">2. Search/Compare</text>
  <text x="300" y="1126" font-size="10" fill="#475569">User queries → API</text>
  <text x="300" y="1140" font-size="10" fill="#475569">Entity resolution</text>

  <rect x="500" y="1090" width="180" height="70" rx="6" fill="#ffffff" stroke="#fed7aa" stroke-width="1"/>
  <text x="520" y="1112" font-size="12" font-weight="bold" fill="#7c2d12">3. AI Analysis</text>
  <text x="520" y="1126" font-size="10" fill="#475569">PhoBERT + LSTM</text>
  <text x="520" y="1140" font-size="10" fill="#475569">inference on comments</text>

  <rect x="720" y="1090" width="180" height="70" rx="6" fill="#ffffff" stroke="#fed7aa" stroke-width="1"/>
  <text x="740" y="1112" font-size="12" font-weight="bold" fill="#7c2d12">4. Scoring</text>
  <text x="740" y="1126" font-size="10" fill="#475569">PQS + RQS + trend</text>
  <text x="740" y="1140" font-size="10" fill="#475569">Buy recommendation</text>

  <rect x="940" y="1090" width="200" height="70" rx="6" fill="#ffffff" stroke="#fed7aa" stroke-width="1"/>
  <text x="960" y="1112" font-size="12" font-weight="bold" fill="#7c2d12">5. Cache & Response</text>
  <text x="960" y="1126" font-size="10" fill="#475569">Cache result TTL=600s</text>
  <text x="960" y="1140" font-size="10" fill="#475569">Rank top 3 cheapest</text>

  <rect x="1180" y="1090" width="180" height="70" rx="6" fill="#ffffff" stroke="#fed7aa" stroke-width="1"/>
  <text x="1200" y="1112" font-size="12" font-weight="bold" fill="#7c2d12">6. Notify</text>
  <text x="1200" y="1126" font-size="10" fill="#475569">6 trigger types</text>
  <text x="1200" y="1140" font-size="10" fill="#475569">FCM + Expo Push</text>

  <!-- Arrows -->
  <line x1="240" y1="1125" x2="280" y2="1125" stroke="#f97316" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="460" y1="1125" x2="500" y2="1125" stroke="#f97316" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="680" y1="1125" x2="720" y2="1125" stroke="#f97316" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="900" y1="1125" x2="940" y2="1125" stroke="#f97316" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="1140" y1="1125" x2="1180" y2="1125" stroke="#f97316" stroke-width="2" marker-end="url(#arrowhead)"/>

  <!-- Arrow marker -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#f97316"/>
    </marker>
  </defs>

  <!-- Footer note -->
  <text x="20" y="1195" font-size="10" fill="#94a3b8">Lưu đồ được tạo tự động bởi create_svg.py | Dự án: Smart Shopping Assistant — So sánh giá sản phẩm thông minh</text>
</svg>'''

with open(path, 'w', encoding='utf-8') as f:
    f.write(svg)
print('Done:', path)
