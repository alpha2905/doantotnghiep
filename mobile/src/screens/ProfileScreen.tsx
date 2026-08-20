import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { User, LogOut, Heart, Bell, ChevronRight } from 'lucide-react-native';
import { User as UserType } from '../types';
import { authApi, storage } from '../services/api';
import { COLORS, SIZES } from '../constants/theme';

const ProfileScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const [user, setUser] = useState<UserType | null>(null);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const data = await authApi.me();
      setUser(data);
    } catch (err) {
      setUser(null);
    }
  };

  const handleLogout = async () => {
    await storage.removeToken();
    setUser(null);
    Alert.alert('Đã đăng xuất', 'Bạn đã đăng xuất thành công');
  };

  const menuItems = [
    {
      icon: Heart,
      label: 'Sản phẩm yêu thích',
      onPress: () => navigation.navigate('Favorites'),
      badge: user?.favorites?.length,
    },
    {
      icon: Bell,
      label: 'Thông báo',
      onPress: () => navigation.navigate('Notifications'),
    },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <View style={styles.avatar}>
          <User size={32} color={COLORS.surface} />
        </View>
        {user ? (
          <View>
            <Text style={styles.name}>{user.full_name || user.email}</Text>
            <Text style={styles.email}>{user.email}</Text>
          </View>
        ) : (
          <TouchableOpacity onPress={() => navigation.navigate('Login')}>
            <Text style={styles.loginPrompt}>Đăng nhập để sử dụng đầy đủ tính năng</Text>
          </TouchableOpacity>
        )}
      </View>

      <ScrollView style={styles.content}>
        {user && (
          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>{user.favorites?.length || 0}</Text>
              <Text style={styles.statLabel}>Yêu thích</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statValue}>0</Text>
              <Text style={styles.statLabel}>Thông báo</Text>
            </View>
          </View>
        )}

        <View style={styles.menuSection}>
          {menuItems.map((item, idx) => (
            <TouchableOpacity key={idx} style={styles.menuItem} onPress={item.onPress}>
              <View style={styles.menuLeft}>
                <item.icon size={20} color={COLORS.primary} />
                <Text style={styles.menuLabel}>{item.label}</Text>
              </View>
              <View style={styles.menuRight}>
                {item.badge !== undefined && item.badge > 0 && (
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>{item.badge}</Text>
                  </View>
                )}
                <ChevronRight size={18} color={COLORS.textMuted} />
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {user && (
          <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
            <LogOut size={20} color={COLORS.danger} />
            <Text style={styles.logoutText}>Đăng xuất</Text>
          </TouchableOpacity>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SIZES.padding,
    paddingVertical: 20,
    backgroundColor: COLORS.primary,
    gap: 16,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORS.primaryDark,
    justifyContent: 'center',
    alignItems: 'center',
  },
  name: {
    fontSize: SIZES.xl,
    fontWeight: '800',
    color: COLORS.surface,
  },
  email: {
    fontSize: SIZES.sm,
    color: COLORS.surface + 'cc',
    marginTop: 2,
  },
  loginPrompt: {
    fontSize: SIZES.md,
    color: COLORS.surface,
    fontWeight: '600',
  },
  content: {
    flex: 1,
    paddingHorizontal: SIZES.padding,
    paddingTop: SIZES.padding,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: SIZES.padding,
  },
  statBox: {
    flex: 1,
    backgroundColor: COLORS.surface,
    padding: 16,
    borderRadius: SIZES.radius,
    alignItems: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  statValue: {
    fontSize: SIZES.xxl,
    fontWeight: '800',
    color: COLORS.primary,
  },
  statLabel: {
    fontSize: SIZES.xs,
    color: COLORS.textSecondary,
    marginTop: 4,
  },
  menuSection: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    overflow: 'hidden',
    marginBottom: SIZES.padding,
  },
  menuItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  menuLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  menuLabel: {
    fontSize: SIZES.md,
    color: COLORS.text,
    fontWeight: '600',
  },
  menuRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  badge: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  badgeText: {
    color: COLORS.surface,
    fontSize: SIZES.xs,
    fontWeight: '700',
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.surface,
    padding: 16,
    borderRadius: SIZES.radius,
    gap: 10,
    marginBottom: 20,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  logoutText: {
    fontSize: SIZES.md,
    color: COLORS.danger,
    fontWeight: '700',
  },
});

export default ProfileScreen;
