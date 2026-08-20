import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRoute, RouteProp } from '@react-navigation/native';
import ProductCard from '../components/ProductCard';
import { Product } from '../types';
import { COLORS, SIZES } from '../constants/theme';
import { ChevronLeft } from 'lucide-react-native';

type RouteParams = {
  ProductDetail: { product: Product };
};

const ProductDetailScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const route = useRoute<RouteProp<RouteParams, 'ProductDetail'>>();
  const { product } = route.params;
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    navigation.setOptions({
      headerTitle: 'Chi tiết sản phẩm',
      headerLeft: () => (
        <TouchableOpacity onPress={() => navigation.goBack()} style={{ marginLeft: 8 }}>
          <ChevronLeft size={24} color={COLORS.text} />
        </TouchableOpacity>
      ),
    });
  }, [navigation]);

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {loading ? (
          <View style={styles.centerBox}>
            <ActivityIndicator size="large" color={COLORS.primary} />
          </View>
        ) : (
          <ProductCard
            product={product}
            index={0}
            isCheapest={false}
            showActions={true}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollContent: {
    padding: SIZES.padding,
    paddingBottom: 40,
  },
  centerBox: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
});

export default ProductDetailScreen;
