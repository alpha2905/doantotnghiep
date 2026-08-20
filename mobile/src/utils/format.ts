import { API_URL } from '../constants/theme';

export const formatPrice = (price: number): string => {
  if (!price) return '0';
  return price.toLocaleString('vi-VN');
};

export const formatDate = (dateStr: string): string => {
  if (!dateStr) return 'N/A';
  return dateStr;
};

export const getPlatformColor = (platform: string): string => {
  const colors: Record<string, string> = {
    'FPT Shop': '#e91e63',
    'Thế Giới Di Động': '#2196f3',
    'CellphoneS': '#ff9800',
    'Hoàng Hà Mobile': '#9c27b0',
    'Di Động Việt': '#00bcd4',
    'Viettel Store': '#f44336',
    'Clickbuy': '#4caf50',
    'MobileCity': '#ff5722',
  };
  return colors[platform] || '#6366f1';
};
