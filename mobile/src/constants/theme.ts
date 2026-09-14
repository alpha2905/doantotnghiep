import Constants from 'expo-constants';

export const COLORS = {
  primary: '#6366f1',
  primaryDark: '#4f46e5',
  primaryLight: '#818cf8',
  secondary: '#10b981',
  accent: '#f59e0b',
  danger: '#ef4444',
  background: '#f8fafc',
  surface: '#ffffff',
  text: '#1e293b',
  textSecondary: '#64748b',
  textMuted: '#94a3b8',
  border: '#e2e8f0',
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#ef4444',
  green: '#22c55e',
  yellow: '#eab308',
  orange: '#f97316',
  red: '#ef4444',
  chartGrid: '#e2e8f0',
  chartText: '#64748b',
  tooltipBg: '#ffffff',
  shadow: 'rgba(0,0,0,0.1)',
};

export const SIZES = {
  xs: 10,
  sm: 12,
  md: 14,
  lg: 16,
  xl: 18,
  xxl: 20,
  xxxl: 24,
  padding: 16,
  radius: 12,
  radiusSm: 8,
  radiusLg: 16,
};

export const FONTS = {
  regular: 'System',
  medium: 'System',
  bold: 'System',
};

export const PLATFORMS = [
  'FPT Shop',
  'Thế Giới Di Động',
  'CellphoneS',
  'Hoàng Hà Mobile',
  'Di Động Việt',
  'Viettel Store',
  'Clickbuy',
  'MobileCity',
];

// Ưu tiên biến môi trường EXPO_PUBLIC_API_URL (build EAS / CI),
// fallback về extra.apiUrl trong app.json, cuối cùng là LAN dev.
// ⚠️ Khi build production: eas build -- ... hoặc set EXPO_PUBLIC_API_URL
// trỏ tới URL public của backend (Render/Railway), KHÔNG để IP LAN.
export const API_URL: string =
  process.env.EXPO_PUBLIC_API_URL ??
  (Constants.expoConfig?.extra as { apiUrl?: string } | undefined)?.apiUrl ??
  'http://192.168.1.100:8000';

export const POPULAR_SEARCHES = [
  'iPhone 15 Pro Max',
  'Samsung Galaxy S24',
  'Xiaomi 14',
  'iPad',
  'MacBook',
  'AirPods',
];
