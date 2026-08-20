import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine,
  PieChart, Pie, Cell
} from 'recharts'
import { Search, TrendingUp, TrendingDown, Minus, ShoppingCart, Clock, AlertTriangle, CheckCircle2, Sparkles, Zap, ExternalLink, RefreshCw, Heart, LogIn, LogOut, Bell, User, X, Moon, Sun, ArrowUp, Scale, Check } from 'lucide-react'
import {
  PLATFORM_LOGOS, formatPrice, formatDate, getRandomComments, fillMissingDates,
  PQS_COLORS, REC_COLORS, SENTIMENT_CONFIG, getRqsColor
} from './utils/format'
import { requestFcmToken, onForegroundMessage } from './firebase'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const TREND_ICONS = {
  'Giảm mạnh': <TrendingDown size={14} />,
  'Giảm nhẹ': <TrendingDown size={14} />,
  'Ổn định': <Minus size={14} />,
  'Tăng nhẹ': <TrendingUp size={14} />,
  'Tăng mạnh': <TrendingUp size={14} />
}

const REC_ICONS = {
  'Nên mua ngay': <CheckCircle2 size={18} />,
  'Nên mua': <ShoppingCart size={18} />,
  'Nên chờ': <Clock size={18} />,
  'Cân nhắc': <AlertTriangle size={18} />,
  'Không khuyến nghị': <AlertTriangle size={18} />
}

const POPULAR_SEARCHES = ['iPhone 15 Pro Max', 'Samsung Galaxy S24', 'Xiaomi 14', 'iPad', 'MacBook', 'AirPods', 'Tivi Sony', 'Loa Bluetooth']

function getPqsColor(color) {
  return PQS_COLORS[color] || PQS_COLORS.green
}

function getTrendColor(trend) {
  if (trend.includes('Giảm')) return 'var(--green-600)'
  if (trend.includes('Tăng')) return 'var(--red-600)'
  return 'var(--slate-500)'
}

function getRecClass(color) {
  return REC_COLORS[color] || REC_COLORS.orange
}

function getSentimentConfig(label) {
  return SENTIMENT_CONFIG[label] || SENTIMENT_CONFIG.NEUTRAL
}

function ProductCard({ product, index, user, token, onToggleFavorite, onRequireLogin, isCheapest, onCompare }) {
  const [expandedComments, setExpandedComments] = useState({})
  const [showAllComments, setShowAllComments] = useState(false)
  const isFavorite = user?.favorites?.some(f => f.name === product.name && f.platform === product.platform)

  const sentiment = product.sentiment || { pos: 0, neu: 0, neg: 0, list: [] }
  const chart = product.chart || { labels: [], data: [] }
  const priceStats = product.price_stats
  const priceTrend = product.price_trend || { trend: 'Ổn định', change_percent: 0, icon: '➡️' }
  const buyRec = product.buy_recommendation || { action: 'Cân nhắc', reason: '', color: 'orange', icon: '🤔' }
  const lstmMetrics = product.lstm_metrics
  const pqsLabel = product.pqs_label || { label: '', color: 'green' }

  const filledChart = fillMissingDates(chart.labels, chart.data)
  const chartData = filledChart.labels.map((label, i) => ({
    name: label,
    price: filledChart.data[i]
  }))

  const comments = getRandomComments(sentiment.list, showAllComments ? 20 : 10)
  const totalComments = sentiment.list.length

  const toggleComment = (idx) => {
    setExpandedComments(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  return (
    <div className={`product-card ${isCheapest ? 'cheapest' : ''}`} style={{ animationDelay: `${index * 0.08}s` }}>
      {/* Header */}
      <div className="card-header">
        <img
          src={PLATFORM_LOGOS[product.platform] || PLATFORM_LOGOS.FPT}
          alt={product.platform}
          className="platform-logo"
          onError={(e) => { e.target.style.display = 'none' }}
        />
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span className="platform-badge">{product.platform}</span>
          <span className="date-badge">📅 {formatDate(product.last_crawl_date)}</span>
        </div>
      </div>

      {/* Image */}
      <div className="product-image-wrap">
        {product.image ? (
          <img src={product.image} alt={product.name} className="product-image" onError={(e) => { e.target.style.display = 'none' }} />
        ) : (
          <div style={{ fontSize: '3rem', color: 'var(--slate-300)' }}>📱</div>
        )}

        {/* Discount badge */}
        {priceStats && priceStats.min < product.current_price && (
          <span className="discount-badge">
            -{Math.round((1 - priceStats.min / product.current_price) * 100)}%
          </span>
        )}

        {/* Cheapest badge */}
        {isCheapest && (
          <span className="cheapest-badge">
            <Zap size={12} /> Rẻ nhất
          </span>
        )}

        {/* Favorite button overlay */}
        <button
          className={`favorite-btn ${isFavorite ? 'active' : ''}`}
          onClick={() => {
            if (!token) {
              onRequireLogin()
              return
            }
            onToggleFavorite(product, isFavorite)
          }}
          title={isFavorite ? 'Bỏ yêu thích' : 'Thêm vào yêu thích'}
          aria-label={isFavorite ? 'Bỏ yêu thích' : 'Thêm vào yêu thích'}
        >
          <Heart
            size={20}
            fill={isFavorite ? 'var(--red-500)' : 'none'}
            color={isFavorite ? 'var(--red-500)' : 'var(--slate-500)'}
            className={isFavorite ? 'heart-pop' : ''}
          />
        </button>
      </div>

      {/* Name */}
      <h3 className="product-name" title={product.name}>{product.name}</h3>

      {/* Price */}
      <div className="product-price">
        <span className="price-currency">₫</span>
        {formatPrice(product.current_price)}
      </div>

      {/* PQS */}
      <div className="pqs-section">
        <div className="pqs-header">
          <span className="pqs-label">⭐ Product Quality Score</span>
          <span className="pqs-score" style={{ color: getPqsColor(pqsLabel.color) }}>
            {product.pqs}/100
          </span>
        </div>
        <div className="pqs-bar">
          <div
            className="pqs-bar-fill"
            style={{
              width: `${product.pqs || 0}%`,
              background: `linear-gradient(90deg, ${getPqsColor(pqsLabel.color)}, ${getPqsColor(pqsLabel.color)}cc)`
            }}
          />
        </div>
        <div className="pqs-status" style={{ color: getPqsColor(pqsLabel.color) }}>
          {pqsLabel.label}
        </div>
      </div>

      {/* Buy Recommendation */}
      <div className={`buy-recommendation ${getRecClass(buyRec.color)}`}>
        <span className="rec-icon">{REC_ICONS[buyRec.action] || buyRec.icon}</span>
        <div>
          <div className="rec-action">{buyRec.action}</div>
          <div className="rec-reason">{buyRec.reason}</div>
        </div>
      </div>

      {/* Price Trend */}
      <div className="price-trend">
        <span className="trend-label">📊 Xu hướng giá</span>
        <span className="trend-value" style={{ color: getTrendColor(priceTrend.trend) }}>
          {TREND_ICONS[priceTrend.trend]} {priceTrend.trend} ({priceTrend.change_percent > 0 ? '+' : ''}{priceTrend.change_percent}%)
        </span>
      </div>

      {/* Price Stats */}
      {priceStats && (
        <div className="price-stats">
          <div className="price-stat">
            <div className="price-stat-label">Giá thấp nhất</div>
            <div className="price-stat-value" style={{ color: 'var(--green-600)' }}>{formatPrice(priceStats.min)}</div>
          </div>
          <div className="price-stat">
            <div className="price-stat-label">Giá trung bình</div>
            <div className="price-stat-value" style={{ color: 'var(--blue-600)' }}>{formatPrice(priceStats.avg)}</div>
          </div>
          <div className="price-stat">
            <div className="price-stat-label">Giá cao nhất</div>
            <div className="price-stat-value" style={{ color: 'var(--red-600)' }}>{formatPrice(priceStats.max)}</div>
          </div>
          <div className="price-stat">
            <div className="price-stat-label">Giá dự báo</div>
            <div className="price-stat-value" style={{ color: 'var(--purple-600)' }}>{formatPrice(product.forecast)}</div>
          </div>
        </div>
      )}

      {/* Forecast Chart */}
      <div className="forecast-section">
        <div className="forecast-header">
          <span>🔮 Dự báo giá LSTM</span>
          <span className="forecast-price">
            {lstmMetrics ? `Chính xác dự báo: ${lstmMetrics.accuracy}%` : ''} • Giá dự báo: {formatPrice(product.forecast)}
          </span>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 0, left: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis hide />
              <YAxis
                tick={{ fontSize: 9, fill: 'var(--chart-text)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${(v / 1000000).toFixed(1)}tr`}
                domain={['auto', 'auto']}
                width={40}
              />
              <Tooltip
                formatter={(value) => [formatPrice(value), 'Giá']}
                labelFormatter={() => ''}
                contentStyle={{ borderRadius: 12, border: '1px solid var(--chart-border)', fontSize: 12, background: 'var(--tooltip-bg)', color: 'var(--text-primary)' }}
              />
              <ReferenceLine
                y={priceStats?.max}
                stroke="var(--red-600)"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: 'Cao nhất', position: 'insideTopRight', fontSize: 9, fill: 'var(--red-600)' }}
              />
              <ReferenceLine
                y={priceStats?.avg}
                stroke="var(--blue-600)"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: 'Trung bình', position: 'insideTopRight', fontSize: 9, fill: 'var(--blue-600)' }}
              />
              <ReferenceLine
                y={priceStats?.min}
                stroke="var(--green-600)"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: 'Thấp nhất', position: 'insideTopRight', fontSize: 9, fill: 'var(--green-600)' }}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="var(--primary)"
                strokeWidth={2.5}
                dot={{ r: 3, fill: 'var(--primary)', strokeWidth: 0 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* LSTM Metrics */}
      {lstmMetrics && (
        <div className="lstm-metrics">
          <div className="lstm-title">📈 Đánh giá độ chính xác LSTM</div>
          <div className="lstm-grid">
            <div className="lstm-item lstm-mae">
              <div className="lstm-item-label">MAE</div>
              <div className="lstm-item-value">{((lstmMetrics.mae / (product.current_price || 1)) * 100).toFixed(2)}%</div>
            </div>
            <div className="lstm-item lstm-rmse">
              <div className="lstm-item-label">RMSE</div>
              <div className="lstm-item-value">{((lstmMetrics.rmse / (product.current_price || 1)) * 100).toFixed(2)}%</div>
            </div>
            <div className="lstm-item lstm-mape">
              <div className="lstm-item-label">MAPE</div>
              <div className="lstm-item-value">{lstmMetrics.mape}%</div>
            </div>
            <div className="lstm-item lstm-dir">
              <div className="lstm-item-label">Đúng hướng</div>
              <div className="lstm-item-value">{lstmMetrics.direction_accuracy}%</div>
            </div>
          </div>
        </div>
      )}

      {/* Comments */}
      <div className="comments-section">
        <div className="comments-header">
          <span className="comments-title">
            <span className="dot" /> Bình luận khách hàng
          </span>
          <span className="comments-count">{totalComments} bình luận</span>
        </div>

        {/* Sentiment Analytics Dashboard */}
        <div className="sentiment-dashboard">
          <div className="sentiment-pie">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={[
                    { name: 'Tích cực', value: sentiment.pos, color: 'var(--green-500)' },
                    { name: 'Trung tính', value: sentiment.neu, color: 'var(--slate-400)' },
                    { name: 'Tiêu cực', value: sentiment.neg, color: 'var(--red-500)' }
                  ]}
                  cx="50%"
                  cy="50%"
                  innerRadius={28}
                  outerRadius={42}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {[
                    { name: 'Tích cực', value: sentiment.pos, color: 'var(--green-500)' },
                    { name: 'Trung tính', value: sentiment.neu, color: 'var(--slate-400)' },
                    { name: 'Tiêu cực', value: sentiment.neg, color: 'var(--red-500)' }
                  ].map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [`${v}%`, 'Tỷ lệ']} contentStyle={{ borderRadius: 12, fontSize: 12, background: 'var(--tooltip-bg)', color: 'var(--text-primary)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="sentiment-pie-legend">
            <div className="sentiment-legend-row">
              <span className="legend-dot" style={{ background: 'var(--green-500)' }} />
              <span className="sentiment-pos">Tích cực</span>
              <span className="legend-value">{sentiment.pos}%</span>
            </div>
            <div className="sentiment-legend-row">
              <span className="legend-dot" style={{ background: 'var(--slate-400)' }} />
              <span className="sentiment-neu">Trung tính</span>
              <span className="legend-value">{sentiment.neu}%</span>
            </div>
            <div className="sentiment-legend-row">
              <span className="legend-dot" style={{ background: 'var(--red-500)' }} />
              <span className="sentiment-neg">Tiêu cực</span>
              <span className="legend-value">{sentiment.neg}%</span>
            </div>
          </div>
        </div>

        {/* Sentiment Bar */}
        <div className="sentiment-bar">
          <div style={{ width: `${sentiment.pos}%`, background: 'var(--green-500)' }} />
          <div style={{ width: `${sentiment.neu}%`, background: 'var(--slate-400)' }} />
          <div style={{ width: `${sentiment.neg}%`, background: 'var(--red-500)' }} />
        </div>
        <div className="sentiment-legend">
          <span className="sentiment-pos">😊 Tích cực {sentiment.pos}%</span>
          <span className="sentiment-neu">😐 Trung tính {sentiment.neu}%</span>
          <span className="sentiment-neg">😞 Tiêu cực {sentiment.neg}%</span>
        </div>

        {/* Comments List */}
        {comments.length > 0 ? (
          <>
            <div className="comments-list">
              {comments.map((cmt, idx) => {
                const cfg = getSentimentConfig(cmt.label)
                const isExpanded = expandedComments[idx]
                return (
                  <div key={idx} className={`comment-item ${cfg.cls}`}>
                    <div
                      className={`comment-text ${isExpanded ? 'expanded' : ''}`}
                      onClick={() => toggleComment(idx)}
                    >
                      {cmt.text}
                    </div>
                    <div className="comment-footer">
                      <span className="comment-aspect">#{cmt.aspect || 'khác'}</span>
                      <div className="comment-badges">
                        <span className="rqs-badge" style={{ color: getRqsColor(cmt.rqs) }}>
                          ⭐ {cmt.rqs}/5
                        </span>
                        <span className={`sentiment-badge ${cfg.badge}`}>{cfg.label}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
            {totalComments > 10 && (
              <button
                className="search-btn"
                style={{ width: '100%', marginTop: '0.75rem', padding: '0.5rem', fontSize: '0.7rem' }}
                onClick={() => setShowAllComments(!showAllComments)}
              >
                {showAllComments ? 'Thu gọn' : `Xem thêm bình luận (${totalComments})`}
              </button>
            )}
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            Chưa có bình luận cho sản phẩm này
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="card-actions">
        <a
          href={product.link}
          target="_blank"
          rel="noopener noreferrer"
          className="search-btn"
          style={{ textAlign: 'center', textDecoration: 'none', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
        >
          Xem trên {product.platform} <ExternalLink size={14} />
        </a>
        <button className="compare-btn" onClick={() => onCompare(product)} title="So sánh giá">
          <Scale size={16} />
        </button>
      </div>
    </div>
  )
}

function EmptyProductCard({ platform }) {
  return (
    <div className="empty-product-card">
      <div className="card-header">
        <span className="platform-badge">{platform}</span>
      </div>
      <div className="empty-product-icon">🔍</div>
      <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600 }}>
        Không tìm thấy sản phẩm trên {platform}
      </div>
    </div>
  )
}

function AuthModal({ mode, onClose, onLogin, onRegister, onSwitchMode }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    const result = mode === 'login'
      ? await onLogin(email, password)
      : await onRegister(email, password, fullName)
    if (!result.ok) {
      setError(result.error)
      setLoading(false)
    }
  }

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <button className="auth-modal-close" onClick={onClose}><X size={18} /></button>
        <div className="auth-modal-title">
          {mode === 'login' ? '🔐 Đăng nhập' : '📝 Đăng ký tài khoản'}
        </div>
        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <input
              className="auth-input"
              placeholder="Họ và tên"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}
          <input
            className="auth-input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="auth-input"
            type="password"
            placeholder="Mật khẩu (tối thiểu 6 ký tự)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <div className="auth-error">{error}</div>}
          <button className="search-btn" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
            {loading ? 'Đang xử lý...' : mode === 'login' ? 'Đăng nhập' : 'Đăng ký'}
          </button>
        </form>
        <div className="auth-switch">
          {mode === 'login' ? (
            <>Chưa có tài khoản? <button onClick={() => onSwitchMode('register')}>Đăng ký ngay</button></>
          ) : (
            <>Đã có tài khoản? <button onClick={() => onSwitchMode('login')}>Đăng nhập</button></>
          )}
        </div>
      </div>
    </div>
  )
}

function CompareModal({ products, onClose }) {
  if (!products || products.length < 2) return null

  const [p1, p2] = products

  const rows = [
    { label: 'Giá hiện tại', val1: formatPrice(p1.current_price), val2: formatPrice(p2.current_price) },
    { label: 'Giá dự báo', val1: formatPrice(p1.forecast), val2: formatPrice(p2.forecast) },
    { label: 'PQS', val1: `${p1.pqs}/100`, val2: `${p2.pqs}/100` },
    { label: 'Khuyến nghị', val1: p1.buy_recommendation?.action || 'Cân nhắc', val2: p2.buy_recommendation?.action || 'Cân nhắc' },
    { label: 'Xu hướng', val1: p1.price_trend?.trend || 'Ổn định', val2: p2.price_trend?.trend || 'Ổn định' }
  ]

  const bestPrice = Math.min(p1.current_price, p2.current_price)

  return (
    <div className="compare-overlay" onClick={onClose}>
      <div className="compare-modal" onClick={(e) => e.stopPropagation()}>
        <button className="auth-modal-close" onClick={onClose}><X size={18} /></button>
        <div className="compare-title">⚖️ So sánh giá</div>
        <div className="compare-grid">
          <div className="compare-col">
            <img src={p1.image} alt={p1.name} className="compare-img" onError={(e) => { e.target.style.display = 'none' }} />
            <div className="compare-platform">{p1.platform}</div>
            <div className="compare-name">{p1.name}</div>
            {p1.current_price === bestPrice && <div className="compare-best"><Zap size={12} /> Giá tốt nhất</div>}
          </div>
          <div className="compare-col">
            <img src={p2.image} alt={p2.name} className="compare-img" onError={(e) => { e.target.style.display = 'none' }} />
            <div className="compare-platform">{p2.platform}</div>
            <div className="compare-name">{p2.name}</div>
            {p2.current_price === bestPrice && <div className="compare-best"><Zap size={12} /> Giá tốt nhất</div>}
          </div>
        </div>
        <div className="compare-rows">
          {rows.map((row, i) => (
            <div key={i} className="compare-row">
              <div className="compare-label">{row.label}</div>
              <div className="compare-value">{row.val1}</div>
              <div className="compare-value">{row.val2}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Toast({ toasts }) {
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          {t.type === 'success' ? <Check size={16} /> : t.type === 'error' ? <AlertTriangle size={16} /> : <Bell size={16} />}
          {t.message}
        </div>
      ))}
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="product-card skeleton-card">
      <div className="skeleton skeleton-line" style={{ width: '40%', height: '28px' }} />
      <div className="skeleton skeleton-img" />
      <div className="skeleton skeleton-line" style={{ width: '90%', height: '16px' }} />
      <div className="skeleton skeleton-line" style={{ width: '40%', height: '24px' }} />
      <div className="skeleton skeleton-block" />
      <div className="skeleton skeleton-block" />
      <div className="skeleton skeleton-block" />
    </div>
  )
}

function NotificationPanel({ notifications, onClose, onMarkAllRead }) {
  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div className="notif-panel">
      <div className="notif-panel-header">
        <span>🔔 Thông báo</span>
        <div className="notif-header-actions">
          {unreadCount > 0 && (
            <button className="notif-mark-all" onClick={onMarkAllRead}>
              Đánh dấu đã đọc
            </button>
          )}
          <button className="notif-close" onClick={onClose}><X size={16} /></button>
        </div>
      </div>
      {notifications.length > 0 ? (
        <div className="notif-list">
          {notifications.map((n, i) => (
            <div key={i} className={`notif-item ${n.read ? 'read' : 'unread'}`}>
              <div className="notif-icon">{n.icon || '🔔'}</div>
              <div className="notif-content">
                <div className="notif-title">{n.title}</div>
                <div className="notif-message">{n.message}</div>
                <div className="notif-meta">
                  <span className="notif-platform">{n.product?.platform}</span>
                  {n.current_price && <span className="notif-price">{formatPrice(n.current_price)}</span>}
                </div>
              </div>
              {!n.read && <span className="notif-dot" />}
            </div>
          ))}
        </div>
      ) : (
        <div className="notif-empty">
          <div className="notif-empty-icon">🔕</div>
          <div>Chưa có thông báo nào</div>
          <div className="notif-empty-sub">Thêm sản phẩm vào yêu thích để nhận cảnh báo giá</div>
        </div>
      )}
    </div>
  )
}

function App() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searched, setSearched] = useState(false)
  const [lastQuery, setLastQuery] = useState('')
  const [fallback, setFallback] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token') || null)
  const [user, setUser] = useState(null)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [showFavorites, setShowFavorites] = useState(false)
  const [showCompare, setShowCompare] = useState(null)
  const [toasts, setToasts] = useState([])
  const [notifications, setNotifications] = useState([])
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifLoading, setNotifLoading] = useState(false)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark')
  const [scrolled, setScrolled] = useState(false)
  const [showScrollTop, setShowScrollTop] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const searchInputRef = useRef(null)

  // Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
    localStorage.setItem('theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  // Scroll effects
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
      setShowScrollTop(window.scrollY > 400)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const addToast = useCallback((message, type = 'success') => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3000)
  }, [])

  const handleSearch = useCallback(async (searchQuery) => {
    const q = (searchQuery || query).trim()
    if (!q) {
      setError('Vui lòng nhập tên sản phẩm cần tìm kiếm')
      return
    }

    setLoading(true)
    setError(null)
    setSearched(true)
    setLastQuery(q)
    setFallback(null)
    setShowSuggestions(false)

    try {
      const searchResponse = await axios.get(`${API_URL}/api/search`, {
        params: { name: q },
        timeout: 30000
      })

      if (!searchResponse.data.found) {
        setResults([])
        setFallback(searchResponse.data)
        return
      }

      const response = await axios.get(`${API_URL}/api/compare`, {
        params: { name: q },
        timeout: 60000
      })
      setResults(response.data.results || [])
    } catch (err) {
      console.error('Search error:', err)
      setError(err.response?.data?.detail || 'Không thể kết nối đến server. Vui lòng kiểm tra backend đang chạy.')
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [query])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch()
  }

  const handleLogin = async (email, password) => {
    try {
      const res = await axios.post(`${API_URL}/api/auth/login`, { email, password })
      localStorage.setItem('token', res.data.access_token)
      setToken(res.data.access_token)
      setUser(res.data.user)
      setShowAuthModal(false)
      addToast('Đăng nhập thành công!')
      return { ok: true }
    } catch (err) {
      return { ok: false, error: err.response?.data?.detail || 'Đăng nhập thất bại' }
    }
  }

  const handleRegister = async (email, password, fullName) => {
    try {
      const res = await axios.post(`${API_URL}/api/auth/register`, { email, password, full_name: fullName })
      localStorage.setItem('token', res.data.access_token)
      setToken(res.data.access_token)
      setUser(res.data.user)
      setShowAuthModal(false)
      addToast('Đăng ký thành công! Chào mừng bạn!')
      return { ok: true }
    } catch (err) {
      return { ok: false, error: err.response?.data?.detail || 'Đăng ký thất bại' }
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    addToast('Đã đăng xuất', 'info')
  }

  const fetchNotifications = useCallback(async () => {
    if (!token) return
    try {
      const res = await axios.get(`${API_URL}/api/notifications`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotifications(res.data.notifications || [])
    } catch (err) {
      console.error('Fetch notifications error:', err)
    }
  }, [token])

  const markAllRead = async () => {
    if (!token) return
    try {
      await axios.post(`${API_URL}/api/notifications/mark-read`, { all: true }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    } catch (err) {
      console.error('Mark read error:', err)
    }
  }

  // Auto-poll notifications every 60s when logged in
  useEffect(() => {
    if (!token) {
      setNotifications([])
      return
    }
    fetchNotifications()
    const interval = setInterval(fetchNotifications, 60000)
    return () => clearInterval(interval)
  }, [token, fetchNotifications])

  // ===== FIREBASE PUSH NOTIFICATION =====
  // Đăng ký service worker + lấy FCM token khi đăng nhập
  useEffect(() => {
    if (!token) return

    let cancelled = false

    const setupFirebase = async () => {
      try {
        // Đăng ký service worker
        if ('serviceWorker' in navigator) {
          const reg = await navigator.serviceWorker.register('/firebase-messaging-sw.js')
          console.log('✅ Service Worker registered:', reg.scope)
        }

        // Yêu cầu quyền thông báo
        const permission = await Notification.requestPermission()
        if (permission !== 'granted') {
          console.log('❌ Notification permission denied')
          return
        }

        // Lấy FCM token
        const fcmToken = await requestFcmToken()
        if (!fcmToken || cancelled) return

        // Gửi token lên backend
        await axios.post(`${API_URL}/api/fcm-token`, { token: fcmToken }, {
          headers: { Authorization: `Bearer ${token}` }
        })
        console.log('✅ FCM token registered')
      } catch (err) {
        console.error('Firebase setup error:', err)
      }
    }

    setupFirebase()

    // Lắng nghe thông báo khi app đang mở (foreground)
    const unsubscribe = onForegroundMessage((payload) => {
      const title = payload.notification?.title || 'Thông báo mới'
      const body = payload.notification?.body || ''
      addToast(`${title}: ${body}`, 'info')
      fetchNotifications()
    })

    return () => {
      cancelled = true
      if (unsubscribe) unsubscribe()
    }
  }, [token, addToast, fetchNotifications])

  const handleToggleFavorite = async (product, isFavorite) => {
    try {
      if (isFavorite) {
        await axios.delete(`${API_URL}/api/favorites`, {
          params: { name: product.name, platform: product.platform },
          headers: { Authorization: `Bearer ${token}` }
        })
        addToast('Đã bỏ yêu thích', 'info')
      } else {
        await axios.post(`${API_URL}/api/favorites`, {
          platform: product.platform,
          name: product.name,
          current_price: product.current_price,
          forecast: product.forecast,
          image: product.image,
          link: product.link,
          pqs: product.pqs
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })
        addToast('Đã thêm vào yêu thích!')
      }
      const me = await axios.get(`${API_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUser(me.data)
    } catch (err) {
      console.error('Favorite error:', err)
      addToast(err.response?.data?.detail || 'Có lỗi xảy ra', 'error')
    }
  }

  // Load user on mount if token exists
  useEffect(() => {
    if (token) {
      axios.get(`${API_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      }).then(res => setUser(res.data)).catch(() => {
        localStorage.removeItem('token')
        setToken(null)
      })
    }
  }, [token])

  useEffect(() => {
    searchInputRef.current?.focus()
  }, [])

  const platforms = ['FPT Shop', 'Thế Giới Di Động', 'CellphoneS', 'Hoàng Hà Mobile', 'Di Động Việt', 'Viettel Store', 'Clickbuy', 'MobileCity']
  const foundPlatforms = results.map(r => r.platform)

  const cheapestPrice = results.length > 0 ? Math.min(...results.map(r => r.current_price)) : null

  const handleCompare = (product) => {
    if (!showCompare) {
      setShowCompare([product])
      addToast('Chọn sản phẩm thứ 2 để so sánh', 'info')
    } else if (showCompare.length === 1 && showCompare[0].platform !== product.platform) {
      setShowCompare([...showCompare, product])
    } else {
      addToast('Hai sản phẩm phải khác sàn', 'error')
    }
  }

  const filteredSuggestions = POPULAR_SEARCHES.filter(s => s.toLowerCase().includes(query.toLowerCase()))

  return (
    <div>
      {/* Header */}
      <header className={`app-header ${scrolled ? 'scrolled' : ''}`}>
        <div className="header-inner">
          <div className="logo">
            <div className="logo-icon"><Sparkles size={20} /></div>
            <div className="logo-text">Smart<span>Shopping</span></div>
            <span className="logo-badge">AI</span>
          </div>

          <div className="search-container">
            <div className="search-input-wrap">
              <span className="search-icon"><Search size={16} /></span>
              <input
                ref={searchInputRef}
                className="search-input"
                placeholder="Tìm kiếm sản phẩm... (VD: iPhone 15 Pro Max, Samsung Galaxy S24...)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              />
              {showSuggestions && query && filteredSuggestions.length > 0 && (
                <div className="search-suggestions">
                  {filteredSuggestions.map((s, i) => (
                    <button key={i} className="suggestion-item" onClick={() => { setQuery(s); handleSearch(s) }}>
                      <Search size={14} /> {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button className="search-btn" onClick={() => handleSearch()} disabled={loading}>
              {loading ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />}
              {loading ? 'Đang tìm...' : 'Tìm kiếm'}
            </button>
          </div>

          <div className="auth-buttons">
            <button className="auth-btn theme-toggle" onClick={() => setDarkMode(!darkMode)} title={darkMode ? 'Chế độ sáng' : 'Chế độ tối'}>
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            {user ? (
              <>
                <button className="auth-btn notif-btn" onClick={() => { setShowNotifications(!showNotifications); if (!showNotifications) fetchNotifications() }} title="Thông báo">
                  <Bell size={16} />
                  {notifications.filter(n => !n.read).length > 0 && (
                    <span className="auth-badge">{notifications.filter(n => !n.read).length}</span>
                  )}
                </button>
                <button className="auth-btn" onClick={() => setShowFavorites(!showFavorites)} title="Sản phẩm yêu thích">
                  <Heart size={16} fill={user.favorites?.length > 0 ? 'var(--red-500)' : 'none'} color={user.favorites?.length > 0 ? 'var(--red-500)' : 'var(--slate-400)'} />
                  {user.favorites?.length > 0 && <span className="auth-badge">{user.favorites.length}</span>}
                </button>
                <div className="user-info">
                  <User size={14} />
                  <span>{user.full_name || user.email}</span>
                </div>
                <button className="auth-btn" onClick={handleLogout} title="Đăng xuất">
                  <LogOut size={16} />
                </button>
              </>
            ) : (
              <button className="auth-btn" onClick={() => { setAuthMode('login'); setShowAuthModal(true) }}>
                <LogIn size={16} />
                Đăng nhập
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Hero Banner */}
      <div className="hero-banner">
        <div className="hero-content">
          <div className="hero-flex">
            <div>
              <div className="hero-title">Mua sắm thông minh, tiết kiệm tối đa</div>
              <div className="hero-subtitle">
                So sánh giá 8 sàn FPT Shop, Thế Giới Di Động, CellphoneS, Hoàng Hà Mobile, Di Động Việt, Viettel Store, Clickbuy, MobileCity • Phân tích cảm xúc bình luận bằng PhoBERT • Dự báo giá bằng LSTM
              </div>
              <div className="hero-stats">
                <div className="hero-stat">
                  <div className="hero-stat-value">8</div>
                  <div className="hero-stat-label">Sàn TMĐT</div>
                </div>
                <div className="hero-stat">
                  <div className="hero-stat-value">1000+</div>
                  <div className="hero-stat-label">Sản phẩm</div>
                </div>
                <div className="hero-stat">
                  <div className="hero-stat-value">95%</div>
                  <div className="hero-stat-label">Độ chính xác AI</div>
                </div>
              </div>
            </div>
            <div className="hero-right">
              <div className="hero-badge">🤖 AI-Powered Shopping Assistant</div>
              <div className="hero-chips">
                <div className="hero-chip" style={{ animationDelay: '0.2s' }}>
                  <Zap size={14} /> Giá rẻ nhất
                </div>
                <div className="hero-chip" style={{ animationDelay: '0.4s' }}>
                  <Sparkles size={14} /> PhoBERT
                </div>
                <div className="hero-chip" style={{ animationDelay: '0.6s' }}>
                  <TrendingUp size={14} /> LSTM Forecast
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Popular searches */}
      <div className="popular-searches">
        <span className="popular-label">🔥 Tìm kiếm nhanh:</span>
        {POPULAR_SEARCHES.slice(0, 6).map((s, i) => (
          <button key={i} className="popular-chip" onClick={() => { setQuery(s); handleSearch(s) }}>
            {s}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <main className="main-container">
        {error && (
          <div className="error-state">
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⚠️</div>
            {error}
          </div>
        )}

        {loading && (
          <div className="loading-state">
            <div className="loading-text">Đang phân tích dữ liệu với AI...</div>
            <div className="skeleton-grid">
              {[0, 1, 2, 3, 4, 5].map(i => <SkeletonCard key={i} />)}
            </div>
          </div>
        )}

        {!loading && !error && !searched && (
          <div className="empty-state">
            <div className="empty-state-icon">🛍️</div>
            <div className="empty-state-title">Tìm kiếm sản phẩm để bắt đầu</div>
            <div className="empty-state-sub">
              Nhập tên sản phẩm ở trên để so sánh giá, phân tích chất lượng và dự báo xu hướng giá
            </div>
          </div>
        )}

        {!loading && !error && fallback && (
          <div className="fallback-state">
            <div className="fallback-icon">🔍</div>
            <div className="fallback-title">Không tìm thấy "{lastQuery}" trong hệ thống</div>
            <div className="fallback-message">
              {fallback.message}
            </div>
            <div className="fallback-note">
              ⚡ Hệ thống sẽ tự động thu thập dữ liệu từ 8 sàn và lưu vào MongoDB.
              Vui lòng thử lại sau ít phút.
            </div>

            {fallback.suggestions && fallback.suggestions.length > 0 && (
              <div className="fallback-suggestions">
                <div className="fallback-suggestions-title">💡 Sản phẩm gợi ý</div>
                <div className="suggestions-grid">
                  {fallback.suggestions.map((s, i) => (
                    <div key={i} className="suggestion-card">
                      <div className="suggestion-platform">{s.platform}</div>
                      <div className="suggestion-name" title={s.name}>{s.name}</div>
                      <div className="suggestion-price">{s.current_price ? formatPrice(s.current_price) : 'Liên hệ'}</div>
                      {s.link && s.link !== '#' && (
                        <a
                          href={s.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: '0.65rem', color: 'var(--primary)', fontWeight: 700, textDecoration: 'none' }}
                        >
                          Xem chi tiết →
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!loading && !error && !fallback && searched && results.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-title">Không tìm thấy sản phẩm "{lastQuery}"</div>
            <div className="empty-state-sub">
              Thử tìm kiếm với tên sản phẩm khác
            </div>
          </div>
        )}

        {!loading && !error && results.length > 0 && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  Kết quả tìm kiếm: <span style={{ color: 'var(--primary)' }}>"{lastQuery}"</span>
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  Tìm thấy {results.length} sản phẩm trên {platforms.length} sàn thương mại điện tử
                </p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {platforms.map(p => (
                  <span
                    key={p}
                    style={{
                      padding: '0.4rem 0.9rem',
                      borderRadius: 999,
                      fontSize: '0.7rem',
                      fontWeight: 800,
                      background: foundPlatforms.includes(p) ? 'var(--success-bg)' : 'var(--chip-bg)',
                      color: foundPlatforms.includes(p) ? 'var(--success-text)' : 'var(--text-muted)'
                    }}
                  >
                    {p} {foundPlatforms.includes(p) ? '✓' : '✗'}
                  </span>
                ))}
              </div>
            </div>

            <div className="results-grid">
              {results.map((product, idx) => (
                <ProductCard
                  key={`${product.platform}-${idx}`}
                  product={product}
                  index={idx}
                  user={user}
                  token={token}
                  onToggleFavorite={handleToggleFavorite}
                  onRequireLogin={() => { setAuthMode('login'); setShowAuthModal(true) }}
                  isCheapest={product.current_price === cheapestPrice}
                  onCompare={handleCompare}
                />
              ))}
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer style={{ textAlign: 'center', padding: '2rem 1.5rem', color: 'var(--text-muted)', fontSize: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
        <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>
          Smart Shopping Assistant — Đồ án tốt nghiệp
        </div>
        <div>
          Nguyễn Hoàng An (22050040) • PhoBERT Sentiment Analysis • LSTM Price Forecast • Product Quality Score
        </div>
      </footer>

      {/* Scroll to top */}
      {showScrollTop && (
        <button className="scroll-top-btn" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} title="Lên đầu trang">
          <ArrowUp size={20} />
        </button>
      )}

      {/* Toast */}
      <Toast toasts={toasts} />

      {showAuthModal && (
        <AuthModal
          mode={authMode}
          onClose={() => setShowAuthModal(false)}
          onLogin={handleLogin}
          onRegister={handleRegister}
          onSwitchMode={setAuthMode}
        />
      )}

      {showCompare && showCompare.length === 2 && (
        <CompareModal products={showCompare} onClose={() => setShowCompare(null)} />
      )}

      {showNotifications && user && (
        <NotificationPanel
          notifications={notifications}
          onClose={() => setShowNotifications(false)}
          onMarkAllRead={markAllRead}
        />
      )}

      {showFavorites && user && (
        <div className="favorites-panel">
          <div className="favorites-panel-header">
            <span>❤️ Sản phẩm yêu thích</span>
            <button onClick={() => setShowFavorites(false)}><X size={16} /></button>
          </div>
          {user.favorites?.length > 0 ? (
            <div className="favorites-list">
              {user.favorites.map((fav, i) => (
                <div key={i} className="favorite-item">
                  <img src={fav.image} alt={fav.name} onError={(e) => { e.target.style.display = 'none' }} />
                  <div className="favorite-info">
                    <div className="favorite-name">{fav.name}</div>
                    <div className="favorite-platform">{fav.platform}</div>
                    <div className="favorite-price">{formatPrice(fav.current_price)}</div>
                  </div>
                  <a href={fav.link} target="_blank" rel="noopener noreferrer" className="favorite-link">
                    <ExternalLink size={14} />
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <div className="favorites-empty">Chưa có sản phẩm yêu thích</div>
          )}
        </div>
      )}
    </div>
  )
}

export default App