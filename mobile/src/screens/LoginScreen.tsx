import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { UserPlus, LogIn } from 'lucide-react-native';
import { authApi, storage } from '../services/api';
import { COLORS, SIZES } from '../constants/theme';

const LoginScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!email || !password) {
      Alert.alert('Lỗi', 'Vui lòng nhập email và mật khẩu');
      return;
    }
    if (mode === 'register' && !fullName.trim()) {
      Alert.alert('Lỗi', 'Vui lòng nhập họ và tên');
      return;
    }

    setLoading(true);
    try {
      const data =
        mode === 'login'
          ? await authApi.login(email, password)
          : await authApi.register(email, password, fullName);

      await storage.setToken(data.access_token);
      Alert.alert('Thành công', mode === 'login' ? 'Đăng nhập thành công!' : 'Đăng ký thành công!');
      navigation.goBack();
    } catch (err: any) {
      Alert.alert('Lỗi', err.response?.data?.detail || 'Có lỗi xảy ra');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          {mode === 'login' ? '🔐 Đăng nhập' : '📝 Đăng ký'}
        </Text>
        <Text style={styles.headerSub}>
          {mode === 'login' ? 'Chào mừng trở lại!' : 'Tạo tài khoản mới'}
        </Text>
      </View>

      <View style={styles.form}>
        {mode === 'register' && (
          <View style={styles.inputWrap}>
            <Text style={styles.inputLabel}>Họ và tên</Text>
            <TextInput
              style={styles.input}
              placeholder="Nguyễn Văn A"
              placeholderTextColor={COLORS.textMuted}
              value={fullName}
              onChangeText={setFullName}
            />
          </View>
        )}
        <View style={styles.inputWrap}>
          <Text style={styles.inputLabel}>Email</Text>
          <TextInput
            style={styles.input}
            placeholder="email@example.com"
            placeholderTextColor={COLORS.textMuted}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
          />
        </View>
        <View style={styles.inputWrap}>
          <Text style={styles.inputLabel}>Mật khẩu</Text>
          <TextInput
            style={styles.input}
            placeholder="Tối thiểu 6 ký tự"
            placeholderTextColor={COLORS.textMuted}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
        </View>

        <TouchableOpacity
          style={[styles.submitBtn, loading && styles.submitBtnDisabled]}
          onPress={handleSubmit}
          disabled={loading}
        >
          {loading ? (
            <Text style={styles.submitText}>Đang xử lý...</Text>
          ) : (
            <>
              {mode === 'login' ? <LogIn size={20} color={COLORS.surface} /> : <UserPlus size={20} color={COLORS.surface} />}
              <Text style={styles.submitText}>
                {mode === 'login' ? 'Đăng nhập' : 'Đăng ký'}
              </Text>
            </>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.switchBtn}
          onPress={() => setMode(mode === 'login' ? 'register' : 'login')}
        >
          <Text style={styles.switchText}>
            {mode === 'login'
              ? 'Chưa có tài khoản? Đăng ký ngay'
              : 'Đã có tài khoản? Đăng nhập'}
          </Text>
        </TouchableOpacity>
      </View>
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
    paddingVertical: 24,
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
    marginTop: 4,
  },
  form: {
    padding: SIZES.padding,
    marginTop: SIZES.padding,
  },
  inputWrap: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: SIZES.sm,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 6,
  },
  input: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: SIZES.md,
    color: COLORS.text,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  submitBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.primary,
    paddingVertical: 16,
    borderRadius: SIZES.radius,
    gap: 10,
    marginTop: 8,
  },
  submitBtnDisabled: {
    opacity: 0.6,
  },
  submitText: {
    color: COLORS.surface,
    fontSize: SIZES.md,
    fontWeight: '700',
  },
  switchBtn: {
    marginTop: 16,
    alignItems: 'center',
  },
  switchText: {
    color: COLORS.primary,
    fontSize: SIZES.sm,
    fontWeight: '600',
  },
});

export default LoginScreen;
