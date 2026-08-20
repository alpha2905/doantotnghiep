import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Heart, ExternalLink, Trash2 } from 'lucide-react-native';
import { FavoriteItem } from '../types';
import { favoriteApi, authApi, storage } from '../services/api';
import { COLORS, SIZES } from '../constants/theme';

const FavoritesScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadFavorites = useCallback(async () => {
    try {
      const data = await favoriteApi.getFavorites();
      setFavorites(data.favorites || []);
    } catch (err) {
      console.error('Load favorites error:', err);
      Alert.alert('Lỗi', 'Không thể tải danh sách yêu thích');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  const handleRemove = async (item: FavoriteItem) => {
    try {
      await favoriteApi.removeFavorite(item.name, item.platform);
      setFavorites((prev) => prev.filter((f) => f.name !== item.name || f.platform !== item.platform));
    } catch (err) {
      Alert.alert('Lỗi', 'Không thể xóa sản phẩm yêu thích');
    }
  };

  const renderItem = ({ item, index }: { item: FavoriteItem; index: number }) => (
    <View style={styles.card}>
      <View style={styles.cardBody}>
        <Text style={styles.platform}>{item.platform}</Text>
        <Text style={styles.name} numberOfLines={2}>{item.name}</Text>
        <Text style={styles.price}>{item.current_price ? item.current_price.toLocaleString('vi-VN') : 'Liên hệ'}₫</Text>
        <View style={styles.actions}>
          {item.link && item.link !== '#' && (
            <TouchableOpacity style={styles.actionBtn}>
              <ExternalLink size={16} color={COLORS.primary} />
            </TouchableOpacity>
          )}
          <TouchableOpacity style={styles.actionBtn} onPress={() => handleRemove(item)}>
            <Trash2 size={16} color={COLORS.danger} />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );

  const renderEmpty = () => (
    <View style={styles.centerBox}>
      <Text style={styles.emptyIcon}>❤️</Text>
      <Text style={styles.emptyTitle}>Chưa có sản phẩm yêu thích</Text>
      <Text style={styles.emptySub}>
        Thêm sản phẩm vào danh sách yêu thích để nhận cảnh báo giá
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>❤️ Yêu thích</Text>
      </View>
      <FlatList
        data={favorites}
        renderItem={renderItem}
        keyExtractor={(item, idx) => `${item.platform}-${item.name}-${idx}`}
        contentContainerStyle={[styles.listContent, favorites.length === 0 && styles.emptyList]}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadFavorites(); }} colors={[COLORS.primary]} />
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
  headerTitle: {
    fontSize: SIZES.xxl,
    fontWeight: '800',
    color: COLORS.surface,
  },
  listContent: {
    paddingHorizontal: SIZES.padding,
    paddingBottom: 20,
  },
  emptyList: {
    flex: 1,
  },
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    marginBottom: SIZES.padding,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  cardBody: {
    flex: 1,
  },
  platform: {
    fontSize: SIZES.xs,
    color: COLORS.primary,
    fontWeight: '600',
    marginBottom: 4,
  },
  name: {
    fontSize: SIZES.md,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 8,
  },
  price: {
    fontSize: SIZES.lg,
    fontWeight: '800',
    color: COLORS.green,
    marginBottom: 10,
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
  },
  actionBtn: {
    padding: 8,
    borderRadius: SIZES.radiusSm,
    backgroundColor: COLORS.background,
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

export default FavoritesScreen;
