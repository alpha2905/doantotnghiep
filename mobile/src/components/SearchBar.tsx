import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Search } from 'lucide-react-native';
import { COLORS, SIZES, POPULAR_SEARCHES } from '../constants/theme';

interface Props {
  value: string;
  onChange: (text: string) => void;
  onSubmit: () => void;
  loading?: boolean;
}

const SearchBar: React.FC<Props> = ({ value, onChange, onSubmit, loading = false }) => {
  const [showSuggestions, setShowSuggestions] = useState(false);

  const filtered = POPULAR_SEARCHES.filter((s) =>
    s.toLowerCase().includes(value.toLowerCase())
  );

  return (
    <View style={styles.wrap}>
      <View style={styles.inputWrap}>
        <Search size={18} color={COLORS.textMuted} />
        <TextInput
          style={styles.input}
          placeholder="Tìm sản phẩm... (VD: iPhone 15 Pro Max)"
          placeholderTextColor={COLORS.textMuted}
          value={value}
          onChangeText={onChange}
          onSubmitEditing={onSubmit}
          returnKeyType="search"
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
        />
        {loading && <ActivityIndicator size="small" color={COLORS.primary} />}
      </View>
      <TouchableOpacity
        style={[styles.btn, loading && styles.btnDisabled]}
        onPress={onSubmit}
        disabled={loading}
      >
        <Text style={styles.btnText}>{loading ? 'Đang tìm...' : 'Tìm kiếm'}</Text>
      </TouchableOpacity>
      {showSuggestions && value.length > 0 && filtered.length > 0 && (
        <View style={styles.suggestions}>
          {filtered.map((s, i) => (
            <TouchableOpacity
              key={i}
              style={styles.suggestion}
              onPress={() => {
                onChange(s);
                onSubmit();
              }}
            >
              <Search size={14} color={COLORS.textMuted} />
              <Text style={styles.suggestionText}>{s}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    position: 'relative',
    zIndex: 10,
  },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    paddingHorizontal: SIZES.padding,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
    gap: 10,
  },
  input: {
    flex: 1,
    fontSize: SIZES.md,
    color: COLORS.text,
  },
  btn: {
    marginTop: 10,
    backgroundColor: COLORS.primary,
    paddingVertical: 12,
    borderRadius: SIZES.radius,
    alignItems: 'center',
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnText: {
    color: COLORS.surface,
    fontSize: SIZES.md,
    fontWeight: '700',
  },
  suggestions: {
    position: 'absolute',
    top: 52,
    left: 0,
    right: 0,
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    borderWidth: 1,
    borderColor: COLORS.border,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
    zIndex: 20,
    overflow: 'hidden',
  },
  suggestion: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  suggestionText: {
    fontSize: SIZES.sm,
    color: COLORS.text,
  },
});

export default SearchBar;
