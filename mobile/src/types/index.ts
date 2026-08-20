export interface User {
  id: string;
  email: string;
  full_name: string;
  favorites: FavoriteItem[];
  created_at: string | null;
}

export interface FavoriteItem {
  platform: string;
  name: string;
  current_price: number;
  forecast: number;
  image: string;
  link: string;
  added_pqs: number | null;
  added_at: string;
}

export interface Product {
  platform: string;
  name: string;
  current_price: number;
  forecast: number;
  last_crawl_date: string;
  image: string;
  sentiment: SentimentData;
  chart: ChartData;
  link: string;
  pqs: number;
  pqs_label: PqsLabel;
  price_stats: PriceStats | null;
  price_trend: PriceTrend;
  buy_recommendation: BuyRecommendation;
  lstm_metrics: LstmMetrics | null;
}

export interface SentimentData {
  pos: number;
  neu: number;
  neg: number;
  list: CommentItem[];
}

export interface CommentItem {
  text: string;
  label: string;
  aspect: string;
  rqs: number;
}

export interface ChartData {
  labels: string[];
  data: number[];
}

export interface PqsLabel {
  label: string;
  color: string;
}

export interface PriceStats {
  min: number;
  avg: number;
  max: number;
  current: number;
}

export interface PriceTrend {
  trend: string;
  change_percent: number;
  icon: string;
}

export interface BuyRecommendation {
  action: string;
  reason: string;
  color: string;
  icon: string;
}

export interface LstmMetrics {
  mae: number;
  rmse: number;
  mape: number;
  accuracy: number;
  direction_accuracy: number;
  sample_size: number;
  eval_method: string;
}

export interface NotificationItem {
  key: string;
  read: boolean;
  type: string;
  icon: string;
  title: string;
  message: string;
  product: FavoriteItem;
  current_price: number;
  created_at: string;
}

export interface SearchFallback {
  found: boolean;
  message: string;
  search_term: string;
  suggestions: FallbackSuggestion[];
}

export interface FallbackSuggestion {
  platform: string;
  name: string;
  current_price: number;
  image: string;
  link: string;
}
