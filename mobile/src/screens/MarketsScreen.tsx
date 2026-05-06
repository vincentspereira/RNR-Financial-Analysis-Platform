import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, FlatList, Pressable } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { colors, spacing, typography } from '../theme';
import { marketApi } from '../services/api';

export default function MarketsScreen() {
  const [search, setSearch] = useState('');

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.search}
        placeholder="Search symbol or company..."
        placeholderTextColor={colors.textMuted}
        value={search}
        onChangeText={setSearch}
      />
      <ScrollView style={styles.list}>
        <Text style={styles.emptyText}>
          Search for a stock symbol to view market data
        </Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.md },
  search: {
    backgroundColor: colors.surface,
    borderRadius: 8,
    padding: spacing.md,
    color: colors.text,
    ...typography.body,
    marginBottom: spacing.md,
  },
  list: { flex: 1 },
  emptyText: { ...typography.body, color: colors.textMuted, textAlign: 'center', marginTop: spacing.xl },
});
