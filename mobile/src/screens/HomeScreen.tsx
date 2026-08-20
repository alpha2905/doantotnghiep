import React, { useState, useCallback, useEffect } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import SearchBar from '../components/SearchBar';
import ProductCard from '../components/ProductCard';
import { Product, SearchFallback } from '../types';
import { searchApi } from '../services/api';
import { COLORS, SIZES, POPULAR_SEARCHES } from '../constants/theme';

const HomeScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [fallback, setFallback] = useState<SearchFallback | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const handleSearch = useCallback(async (searchQuery: string) => {
    const q = (searchQuery || query).trim();
    if (!q) {
      setError('Vui lòng nhập tên sản phẩm cần tìm kiếm');
      return;
    }

    setLoading(true);
    setError(null);
    setSearched(true);
    setFallback(null);

    try {
      const searchData = await searchApi.search(q);
      if (!searchData.found) {
        setResults([]);
        setFallback(searchData);
        setLoading(false);
        return;
      }

      const compareData = await searchApi.compare(q);
      setResults(compareData.results || []);
    } catch (err: any) {
      console.error('Search error:', err);
      setError(err.response?.data?.detail || 'Không thể kết nối đến server');
      setResults([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [query]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    if (searched && query) {
      await handleSearch(query);
    }
    setRefreshing(false);
  }, [searched, query, handleSearch]);

  const cheapestPrice = results.length > 0
    ? Math.min(...results.map((r) => r.current_price).filter((p) => p > 0))
    : null;

  const renderEmpty = () => {
    if (loading) return null;
    if (error) {
      return (
        <View style={styles.centerBox}>
          <Text style={styles.emptyIcon}>⚠️</Text>
          <Text style={styles.emptySub}>{error}</Text>
        </View>
      );
    }
    if (fallback) {
      return (
        <View style={styles.centerBox}>
          <Text style={styles.emptyIcon}>🔍</Text>
          <Text style={styles.emptyTitle}>Không tìm thấy "{query}" trong hệ thống</Text>
          <Text style={styles.emptySub}>{fallback.message}</Text>
          <Text style={styles.emptyNote}>
            Hệ thống sẽ tự động thu thập dữ liệu. Vui lòng thử lại sau.
          </Text>
          {fallback.suggestions && fallback.suggestions.length > 0 && (
            <View style={styles.suggestionsGrid}>
              {fallback.suggestions.map((s, i) => (
                <View key={i} style={styles.suggestionCard}>
                  <Text style={styles.suggestionPlatform}>{s.platform}</Text>
                  <Text style={styles.suggestionName} numberOfLines={2}>{s.name}</Text>
                  <Text style={styles.suggestionPrice}>{s.current_price ? s.current_price.toLocaleString('vi-VN') : 'Liên hệ'}</Text>
                </View>
              ))}
            </View>
          )}
        </View>
      );
    }
    if (!searched) {
      return (
        <View style={styles.centerBox}>
          <Text style={styles.emptyIcon}>🛍️</Text>
          <Text style={styles.emptyTitle}>Tìm kiếm sản phẩm để bắt đầu</Text>
          <Text style={styles.emptySub}>
            Nhập tên sản phẩm để so sánh giá, phân tích chất lượng và dự báo xu hướng giá
          </Text>
          <View style={styles.popularRow}>
            {POPULAR_SEARCHES.slice(0, 4).map((s, i) => (
              <TouchableOpacity
                key={i}
                style={styles.popularChip}
                onPress={() => {
                  setQuery(s);
                  handleSearch(s);
                }}
              >
                <Text style={styles.popularText}>{s}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      );
    }
    return (
      <View style={styles.centerBox}>
        <Text style={styles.emptyIcon}>🔍</Text>
        <Text style={styles.emptyTitle}>Không tìm thấy sản phẩm "{query}"</Text>
        <Text style={styles.emptySub}>Thử tìm kiếm với tên sản phẩm khác</Text>
      </View>
    );
  };

  const renderResult = ({ item, index }: { item: Product; index: number }) => (
    <ProductCard
      product={item}
      index={index}
      isCheapest={item.current_price === cheapestPrice}
      onPress={(product) => {
        navigation.navigate('ProductDetail', { product });
      }}
    />
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Smart Shopping</Text>
        <Text style={styles.headerSub}>So sánh giá thông minh</Text>
      </View>
      <View style={styles.searchArea}>
        <SearchBar value={query} onChange={setQuery} onSubmit={() => handleSearch(query)} loading={loading} />
      </View>
      <FlatList
        data={results}
        renderItem={renderResult}
        keyExtractor={(item, idx) => `${item.platform}-${idx}`}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[COLORS.primary]} />
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
  headerSub: {
    fontSize: SIZES.sm,
    color: COLORS.surface + 'cc',
    marginTop: 2,
  },
  searchArea: {
    paddingHorizontal: SIZES.padding,
    paddingVertical: 12,
    backgroundColor: COLORS.background,
  },
  listContent: {
    paddingHorizontal: SIZES.padding,
    paddingBottom: 20,
  },
  centerBox: {
    alignItems: 'center',
    paddingVertical: 40,
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
    textAlign: 'center',
    marginBottom: 8,
  },
  emptySub: {
    fontSize: SIZES.sm,
    color: COLORS.textSecondary,
    textAlign: 'center',
    marginBottom: 8,
  },
  emptyNote: {
    fontSize: SIZES.xs,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginBottom: 16,
  },
  popularRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    justifyContent: 'center',
  },
  popularChip: {
    backgroundColor: COLORS.primary + '15',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
  },
  popularText: {
    fontSize: SIZES.xs,
    color: COLORS.primary,
    fontWeight: '600',
  },
  suggestionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginTop: 16,
  },
  suggestionCard: {
    backgroundColor: COLORS.surface,
    padding: 12,
    borderRadius: SIZES.radius,
    width: '48%',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  suggestionPlatform: {
    fontSize: SIZES.xs,
    color: COLORS.primary,
    fontWeight: '600',
    marginBottom: 4,
  },
  suggestionName: {
    fontSize: SIZES.sm,
    color: COLORS.text,
    marginBottom: 4,
  },
  suggestionPrice: {
    fontSize: SIZES.md,
    fontWeight: '700',
    color: COLORS.green,
  },
});

export default HomeScreen;
