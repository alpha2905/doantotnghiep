import React from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  ScrollView,
} from 'react-native';
import { Heart, ExternalLink, TrendingUp, TrendingDown, Minus, ShoppingCart, Clock, AlertTriangle, CheckCircle2, Zap } from 'lucide-react-native';
import { LineChart, PieChart } from 'react-native-chart-kit';
import { Product, PqsLabel } from '../types';
import { COLORS, SIZES } from '../constants/theme';

const { width } = Dimensions.get('window');

interface Props {
  product: Product;
  index: number;
  isCheapest?: boolean;
  isFavorite?: boolean;
  onToggleFavorite?: (product: Product) => void;
  onPress?: (product: Product) => void;
  requireLogin?: () => void;
  showActions?: boolean;
}

const getPqsColor = (color: string) => {
  const map: Record<string, string> = {
    green: COLORS.green,
    yellow: COLORS.yellow,
    orange: COLORS.orange,
    red: COLORS.red,
  };
  return map[color] || COLORS.green;
};

const formatPrice = (price: number) => {
  if (!price) return '0';
  return price.toLocaleString('vi-VN');
};

const ProductCard: React.FC<Props> = ({
  product,
  index,
  isCheapest = false,
  isFavorite = false,
  onToggleFavorite,
  onPress,
  requireLogin,
  showActions = true,
}) => {
  const sentiment = product.sentiment || { pos: 0, neu: 0, neg: 0, list: [] };
  const priceStats = product.price_stats;
  const priceTrend = product.price_trend || { trend: 'Ổn định', change_percent: 0, icon: '➡️' };
  const buyRec = product.buy_recommendation || { action: 'Cân nhắc', reason: '', color: 'orange', icon: '🤔' };
  const lstmMetrics = product.lstm_metrics;
  const pqsLabel = product.pqs_label || { label: 'Chất lượng trung bình', color: 'orange' };

  const chartData = {
    labels: product.chart?.labels || [],
    datasets: [
      {
        data: product.chart?.data || [],
        color: () => COLORS.primary,
        strokeWidth: 2,
      },
    ],
  };

  const TrendIcon = priceTrend.trend.includes('Giảm')
    ? TrendingDown
    : priceTrend.trend.includes('Tăng')
    ? TrendingUp
    : Minus;

  const RecIcon = buyRec.action === 'Nên mua ngay'
    ? CheckCircle2
    : buyRec.action === 'Nên mua'
    ? ShoppingCart
    : buyRec.action === 'Nên chờ'
    ? Clock
    : AlertTriangle;

  const sentimentData = [
    { name: 'Tích cực', population: sentiment.pos, color: COLORS.green, legendFontColor: COLORS.text },
    { name: 'Trung tính', population: sentiment.neu, color: COLORS.textMuted, legendFontColor: COLORS.text },
    { name: 'Tiêu cực', population: sentiment.neg, color: COLORS.red, legendFontColor: COLORS.text },
  ];

  return (
    <View style={[styles.card, isCheapest && styles.cheapestCard]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.platformBadge}>{product.platform}</Text>
          <Text style={styles.dateBadge}>📅 {product.last_crawl_date}</Text>
        </View>
        {isCheapest && (
          <View style={styles.cheapestBadge}>
            <Zap size={12} color="#fff" />
            <Text style={styles.cheapestText}>Rẻ nhất</Text>
          </View>
        )}
      </View>

      {/* Product Image */}
      <TouchableOpacity onPress={() => onPress?.(product)} activeOpacity={0.9}>
        <View style={styles.imageWrap}>
          {product.image ? (
            <Image
              source={{ uri: product.image }}
              style={styles.productImage}
              resizeMode="contain"
            />
          ) : (
            <View style={styles.noImage}>
              <Text style={styles.noImageText}>📱</Text>
            </View>
          )}
          {priceStats && priceStats.min < product.current_price && (
            <View style={styles.discountBadge}>
              <Text style={styles.discountText}>
                -{Math.round((1 - priceStats.min / product.current_price) * 100)}%
              </Text>
            </View>
          )}
          {onToggleFavorite && (
            <TouchableOpacity
              style={styles.favoriteBtn}
              onPress={() => {
                if (requireLogin) {
                  requireLogin();
                  return;
                }
                onToggleFavorite(product);
              }}
            >
              <Heart
                size={20}
                color={isFavorite ? COLORS.danger : COLORS.textMuted}
                fill={isFavorite ? COLORS.danger : 'transparent'}
              />
            </TouchableOpacity>
          )}
        </View>

        {/* Name */}
        <Text style={styles.productName} numberOfLines={2}>
          {product.name}
        </Text>

        {/* Price */}
        <View style={styles.priceRow}>
          <Text style={styles.priceCurrency}>₫</Text>
          <Text style={styles.priceValue}>{formatPrice(product.current_price)}</Text>
        </View>
      </TouchableOpacity>

      {/* PQS */}
      <View style={styles.pqsSection}>
        <View style={styles.pqsHeader}>
          <Text style={styles.pqsLabel}>⭐ Product Quality Score</Text>
          <Text style={[styles.pqsScore, { color: getPqsColor(pqsLabel.color) }]}>
            {product.pqs}/100
          </Text>
        </View>
        <View style={styles.pqsBar}>
          <View
            style={[
              styles.pqsBarFill,
              {
                width: `${Math.min(product.pqs || 0, 100)}%`,
                backgroundColor: getPqsColor(pqsLabel.color),
              },
            ]}
          />
        </View>
        <Text style={[styles.pqsStatus, { color: getPqsColor(pqsLabel.color) }]}>
          {pqsLabel.label}
        </Text>
      </View>

      {/* Buy Recommendation */}
      <View style={[styles.recBox, { backgroundColor: buyRec.color === 'green' ? '#dcfce7' : buyRec.color === 'yellow' ? '#fef3c7' : '#fee2e2' }]}>
        <RecIcon size={18} color={buyRec.color === 'green' ? COLORS.green : buyRec.color === 'yellow' ? COLORS.yellow : COLORS.red} />
        <View style={{ marginLeft: 8, flex: 1 }}>
          <Text style={[styles.recAction, { color: buyRec.color === 'green' ? COLORS.green : buyRec.color === 'yellow' ? COLORS.yellow : COLORS.red }]}>
            {buyRec.action}
          </Text>
          <Text style={styles.recReason}>{buyRec.reason}</Text>
        </View>
      </View>

      {/* Price Trend */}
      <View style={styles.trendRow}>
        <Text style={styles.trendLabel}>📊 Xu hướng giá</Text>
        <View style={styles.trendValue}>
          <TrendIcon size={14} color={priceTrend.trend.includes('Giảm') ? COLORS.green : priceTrend.trend.includes('Tăng') ? COLORS.red : COLORS.textMuted} />
          <Text style={[
            styles.trendText,
            { color: priceTrend.trend.includes('Giảm') ? COLORS.green : priceTrend.trend.includes('Tăng') ? COLORS.red : COLORS.textMuted }
          ]}>
            {priceTrend.trend} ({priceTrend.change_percent > 0 ? '+' : ''}{priceTrend.change_percent}%)
          </Text>
        </View>
      </View>

      {/* Price Stats */}
      {priceStats && (
        <View style={styles.statsGrid}>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>Giá thấp nhất</Text>
            <Text style={[styles.statValue, { color: COLORS.green }]}>{formatPrice(priceStats.min)}</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>Giá trung bình</Text>
            <Text style={[styles.statValue, { color: COLORS.primary }]}>{formatPrice(priceStats.avg)}</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>Giá cao nhất</Text>
            <Text style={[styles.statValue, { color: COLORS.red }]}>{formatPrice(priceStats.max)}</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>Giá dự báo</Text>
            <Text style={[styles.statValue, { color: '#a855f7' }]}>{formatPrice(product.forecast)}</Text>
          </View>
        </View>
      )}

      {/* Price Chart */}
      {chartData.labels.length > 0 && (
        <View style={styles.chartSection}>
          <View style={styles.chartHeader}>
            <Text style={styles.chartTitle}>🔮 Dự báo giá LSTM</Text>
            <Text style={styles.chartSubtitle}>
              {lstmMetrics ? `Chính xác: ${lstmMetrics.accuracy}%` : ''} • Giá dự báo: {formatPrice(product.forecast)}
            </Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <LineChart
              data={chartData}
              width={Math.max(chartData.labels.length * 60, width - 100)}
              height={180}
              chartConfig={{
                backgroundColor: COLORS.surface,
                backgroundGradientFrom: COLORS.surface,
                backgroundGradientTo: COLORS.surface,
                decimalPlaces: 0,
                color: () => COLORS.primary,
                labelColor: () => COLORS.textSecondary,
                style: { borderRadius: 16 },
                propsForDots: { r: '3', strokeWidth: '2', stroke: COLORS.primary },
                propsForBackgroundLines: { strokeDasharray: '', stroke: COLORS.border, strokeWidth: 1 },
              }}
              bezier
              style={styles.chart}
              formatYLabel={(value) => `${(Number(value) / 1000000).toFixed(1)}tr`}
            />
          </ScrollView>
        </View>
      )}

      {/* LSTM Metrics */}
      {lstmMetrics && (
        <View style={styles.lstmSection}>
          <Text style={styles.lstmTitle}>📈 Đánh giá độ chính xác LSTM</Text>
          <View style={styles.lstmGrid}>
            <View style={styles.lstmItem}>
              <Text style={styles.lstmLabel}>MAE</Text>
              <Text style={styles.lstmValue}>{((lstmMetrics.mae / (product.current_price || 1)) * 100).toFixed(2)}%</Text>
            </View>
            <View style={styles.lstmItem}>
              <Text style={styles.lstmLabel}>RMSE</Text>
              <Text style={styles.lstmValue}>{((lstmMetrics.rmse / (product.current_price || 1)) * 100).toFixed(2)}%</Text>
            </View>
            <View style={styles.lstmItem}>
              <Text style={styles.lstmLabel}>MAPE</Text>
              <Text style={styles.lstmValue}>{lstmMetrics.mape}%</Text>
            </View>
            <View style={styles.lstmItem}>
              <Text style={styles.lstmLabel}>Đúng hướng</Text>
              <Text style={styles.lstmValue}>{lstmMetrics.direction_accuracy}%</Text>
            </View>
          </View>
        </View>
      )}

      {/* Sentiment */}
      <View style={styles.sentimentSection}>
        <Text style={styles.sentimentTitle}>
          <View style={styles.dot} /> Bình luận khách hàng
        </Text>
        <Text style={styles.commentsCount}>{sentiment.list.length} bình luận</Text>

        <View style={styles.sentimentPieWrap}>
          <PieChart
            data={sentimentData}
            width={140}
            height={140}
            chartConfig={{
              color: () => COLORS.text,
            }}
            accessor="population"
            backgroundColor="transparent"
            paddingLeft="15"
            absolute
            style={styles.pieChart}
          />
          <View style={styles.sentimentLegend}>
            <View style={styles.legendRow}>
              <View style={[styles.legendDot, { backgroundColor: COLORS.green }]} />
              <Text style={styles.legendText}>Tích cực</Text>
              <Text style={styles.legendValue}>{sentiment.pos}%</Text>
            </View>
            <View style={styles.legendRow}>
              <View style={[styles.legendDot, { backgroundColor: COLORS.textMuted }]} />
              <Text style={styles.legendText}>Trung tính</Text>
              <Text style={styles.legendValue}>{sentiment.neu}%</Text>
            </View>
            <View style={styles.legendRow}>
              <View style={[styles.legendDot, { backgroundColor: COLORS.red }]} />
              <Text style={styles.legendText}>Tiêu cực</Text>
              <Text style={styles.legendValue}>{sentiment.neg}%</Text>
            </View>
          </View>
        </View>

        {/* Comments List */}
        {sentiment.list.length > 0 ? (
          <View style={styles.commentsList}>
            {sentiment.list.slice(0, 10).map((cmt, idx) => {
              const labelColor =
                cmt.label === 'POSITIVE'
                  ? COLORS.green
                  : cmt.label === 'NEGATIVE'
                  ? COLORS.red
                  : COLORS.textMuted;
              return (
                <View key={idx} style={styles.commentItem}>
                  <Text style={styles.commentText} numberOfLines={3}>
                    {cmt.text}
                  </Text>
                  <View style={styles.commentFooter}>
                    <Text style={styles.commentAspect}>#{cmt.aspect || 'khác'}</Text>
                    <View style={styles.commentBadges}>
                      <Text style={[styles.rqsBadge, { color: cmt.rqs >= 4 ? COLORS.green : cmt.rqs >= 3 ? COLORS.yellow : COLORS.red }]}>
                        ⭐ {cmt.rqs}/5
                      </Text>
                      <View style={[styles.sentimentBadge, { backgroundColor: labelColor + '20' }]}>
                        <Text style={[styles.sentimentBadgeText, { color: labelColor }]}>
                          {cmt.label}
                        </Text>
                      </View>
                    </View>
                  </View>
                </View>
              );
            })}
          </View>
        ) : (
          <Text style={styles.noComments}>Chưa có bình luận cho sản phẩm này</Text>
        )}
      </View>

      {/* Actions */}
      {showActions && (
        <View style={styles.actionsRow}>
          <TouchableOpacity
            style={styles.viewStoreBtn}
            onPress={() => {
              if (product.link && product.link !== '#') {
                // In a real app, use Linking.openURL(product.link)
              }
            }}
          >
            <ExternalLink size={16} color={COLORS.surface} />
            <Text style={styles.viewStoreText}>Xem trên {product.platform}</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radiusLg,
    padding: SIZES.padding,
    marginBottom: SIZES.padding,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  cheapestCard: {
    borderWidth: 2,
    borderColor: COLORS.primary,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.padding,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  platformBadge: {
    backgroundColor: COLORS.primary + '15',
    color: COLORS.primary,
    fontSize: SIZES.sm,
    fontWeight: '700',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },
  dateBadge: {
    fontSize: SIZES.xs,
    color: COLORS.textSecondary,
  },
  cheapestBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.primary,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 4,
  },
  cheapestText: {
    color: '#fff',
    fontSize: SIZES.xs,
    fontWeight: '700',
  },
  imageWrap: {
    alignItems: 'center',
    marginBottom: SIZES.padding,
    position: 'relative',
  },
  productImage: {
    width: 120,
    height: 120,
  },
  noImage: {
    width: 120,
    height: 120,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
  },
  noImageText: {
    fontSize: 48,
  },
  discountBadge: {
    position: 'absolute',
    top: -8,
    right: 0,
    backgroundColor: COLORS.danger,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
  },
  discountText: {
    color: '#fff',
    fontSize: SIZES.xs,
    fontWeight: '700',
  },
  favoriteBtn: {
    position: 'absolute',
    top: -8,
    left: 0,
    backgroundColor: COLORS.surface,
    borderRadius: 20,
    padding: 6,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  productName: {
    fontSize: SIZES.lg,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 8,
    textAlign: 'center',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'center',
    marginBottom: SIZES.padding,
  },
  priceCurrency: {
    fontSize: SIZES.md,
    fontWeight: '600',
    color: COLORS.primary,
    marginRight: 2,
  },
  priceValue: {
    fontSize: SIZES.xxl,
    fontWeight: '800',
    color: COLORS.primary,
  },
  pqsSection: {
    marginBottom: SIZES.padding,
  },
  pqsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  pqsLabel: {
    fontSize: SIZES.sm,
    color: COLORS.textSecondary,
    fontWeight: '600',
  },
  pqsScore: {
    fontSize: SIZES.lg,
    fontWeight: '800',
  },
  pqsBar: {
    height: 8,
    backgroundColor: COLORS.border,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 4,
  },
  pqsBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  pqsStatus: {
    fontSize: SIZES.xs,
    fontWeight: '600',
  },
  recBox: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SIZES.padding,
    borderRadius: SIZES.radius,
    marginBottom: SIZES.padding,
    gap: 10,
  },
  recAction: {
    fontSize: SIZES.md,
    fontWeight: '700',
  },
  recReason: {
    fontSize: SIZES.xs,
    color: COLORS.textSecondary,
    marginTop: 2,
  },
  trendRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.padding,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  trendLabel: {
    fontSize: SIZES.sm,
    color: COLORS.textSecondary,
    fontWeight: '600',
  },
  trendValue: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  trendText: {
    fontSize: SIZES.sm,
    fontWeight: '600',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: SIZES.padding,
  },
  statBox: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: COLORS.background,
    padding: 10,
    borderRadius: SIZES.radiusSm,
  },
  statLabel: {
    fontSize: SIZES.xs,
    color: COLORS.textSecondary,
    marginBottom: 4,
  },
  statValue: {
    fontSize: SIZES.md,
    fontWeight: '700',
  },
  chartSection: {
    marginBottom: SIZES.padding,
  },
  chartHeader: {
    marginBottom: 8,
  },
  chartTitle: {
    fontSize: SIZES.sm,
    fontWeight: '700',
    color: COLORS.text,
  },
  chartSubtitle: {
    fontSize: SIZES.xs,
    color: COLORS.textSecondary,
    marginTop: 2,
  },
  chart: {
    borderRadius: SIZES.radius,
  },
  lstmSection: {
    backgroundColor: COLORS.background,
    padding: SIZES.padding,
    borderRadius: SIZES.radius,
    marginBottom: SIZES.padding,
  },
  lstmTitle: {
    fontSize: SIZES.sm,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 10,
  },
  lstmGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  lstmItem: {
    flex: 1,
    minWidth: '45%',
  },
  lstmLabel: {
    fontSize: SIZES.xs,
    color: COLORS.textSecondary,
  },
  lstmValue: {
    fontSize: SIZES.md,
    fontWeight: '700',
    color: COLORS.primary,
  },
  sentimentSection: {
    marginBottom: SIZES.padding,
  },
  sentimentTitle: {
    flexDirection: 'row',
    alignItems: 'center',
    fontSize: SIZES.sm,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 4,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.primary,
    marginRight: 8,
  },
  commentsCount: {
    fontSize: SIZES.xs,
    color: COLORS.textSecondary,
    marginBottom: SIZES.padding,
  },
  sentimentPieWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.padding,
  },
  pieChart: {},
  sentimentLegend: {
    flex: 1,
    marginLeft: SIZES.padding,
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 8,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendText: {
    fontSize: SIZES.sm,
    color: COLORS.textSecondary,
    flex: 1,
  },
  legendValue: {
    fontSize: SIZES.sm,
    fontWeight: '700',
    color: COLORS.text,
  },
  commentsList: {
    gap: 8,
  },
  commentItem: {
    backgroundColor: COLORS.background,
    padding: 10,
    borderRadius: SIZES.radiusSm,
  },
  commentText: {
    fontSize: SIZES.sm,
    color: COLORS.text,
    marginBottom: 6,
  },
  commentFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  commentAspect: {
    fontSize: SIZES.xs,
    color: COLORS.primary,
    fontWeight: '600',
  },
  commentBadges: {
    flexDirection: 'row',
    gap: 8,
  },
  rqsBadge: {
    fontSize: SIZES.xs,
    fontWeight: '700',
  },
  sentimentBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  sentimentBadgeText: {
    fontSize: SIZES.xs,
    fontWeight: '700',
  },
  noComments: {
    textAlign: 'center',
    color: COLORS.textMuted,
    fontSize: SIZES.sm,
    paddingVertical: 20,
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  viewStoreBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.primary,
    paddingVertical: 12,
    borderRadius: SIZES.radius,
    gap: 8,
  },
  viewStoreText: {
    color: COLORS.surface,
    fontSize: SIZES.md,
    fontWeight: '700',
  },
});

export default ProductCard;
