import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Bell, Check } from 'lucide-react-native';
import { NotificationItem } from '../types';
import { notificationApi } from '../services/api';
import { COLORS, SIZES } from '../constants/theme';

const NotificationsScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadNotifications = useCallback(async () => {
    try {
      const data = await notificationApi.getNotifications();
      setNotifications(data.notifications || []);
    } catch (err) {
      console.error('Load notifications error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 60000);
    return () => clearInterval(interval);
  }, [loadNotifications]);

  const markAllRead = async () => {
    try {
      await notificationApi.markRead({ all: true });
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch (err) {
      Alert.alert('Lỗi', 'Không thể đánh dấu đã đọc');
    }
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const renderItem = ({ item }: { item: NotificationItem }) => (
    <View style={[styles.card, !item.read && styles.unreadCard]}>
      <View style={styles.iconWrap}>
        <Text style={styles.icon}>{item.icon || '🔔'}</Text>
        {!item.read && <View style={styles.unreadDot} />}
      </View>
      <View style={styles.content}>
        <Text style={styles.title}>{item.title}</Text>
        <Text style={styles.message}>{item.message}</Text>
        <View style={styles.meta}>
          <Text style={styles.platform}>{item.product?.platform}</Text>
          {item.current_price ? (
            <Text style={styles.price}>{item.current_price.toLocaleString('vi-VN')}₫</Text>
          ) : null}
        </View>
      </View>
    </View>
  );

  const renderEmpty = () => (
    <View style={styles.centerBox}>
      <Text style={styles.emptyIcon}>🔕</Text>
      <Text style={styles.emptyTitle}>Chưa có thông báo nào</Text>
      <Text style={styles.emptySub}>
        Thêm sản phẩm vào yêu thích để nhận cảnh báo giá
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <Text style={styles.headerTitle}>🔔 Thông báo</Text>
          {unreadCount > 0 && (
            <TouchableOpacity style={styles.markAllBtn} onPress={markAllRead}>
              <Check size={16} color={COLORS.surface} />
              <Text style={styles.markAllText}>Đánh dấu đã đọc</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
      <FlatList
        data={notifications}
        renderItem={renderItem}
        keyExtractor={(item, idx) => `${item.key}-${idx}`}
        contentContainerStyle={[styles.listContent, notifications.length === 0 && styles.emptyList]}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadNotifications(); }} colors={[COLORS.primary]} />
        }
        ListEmptyComponent={renderEmpty}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    paddingHorizontal: SIZES.padding,
    paddingVertical: 16,
    backgroundColor: COLORS.primary,
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: SIZES.xxl,
    fontWeight: '800',
    color: COLORS.surface,
  },
  markAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.surface + '20',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 6,
  },
  markAllText: {
    color: COLORS.surface,
    fontSize: SIZES.xs,
    fontWeight: '600',
  },
  listContent: {
    paddingHorizontal: SIZES.padding,
    paddingBottom: 20,
  },
  emptyList: {
    flex: 1,
  },
  card: {
    flexDirection: 'row',
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    marginBottom: SIZES.padding,
    gap: 12,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  unreadCard: {
    borderLeftWidth: 3,
    borderLeftColor: COLORS.primary,
  },
  iconWrap: {
    position: 'relative',
  },
  icon: {
    fontSize: 24,
  },
  unreadDot: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.danger,
  },
  content: {
    flex: 1,
  },
  title: {
    fontSize: SIZES.md,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 4,
  },
  message: {
    fontSize: SIZES.sm,
    color: COLORS.textSecondary,
    marginBottom: 6,
  },
  meta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  platform: {
    fontSize: SIZES.xs,
    color: COLORS.primary,
    fontWeight: '600',
  },
  price: {
    fontSize: SIZES.sm,
    fontWeight: '700',
    color: COLORS.green,
  },
  centerBox: {
    alignItems: 'center',
    paddingVertical: 60,
    paddingHorizontal: SIZES.padding,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: SIZES.lg,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 8,
  },
  emptySub: {
    fontSize: SIZES.sm,
    color: COLORS.textSecondary,
    textAlign: 'center',
  },
});

export default NotificationsScreen;
