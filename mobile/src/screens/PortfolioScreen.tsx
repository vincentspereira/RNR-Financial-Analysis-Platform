import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { colors, spacing, typography } from '../theme';

export default function PortfolioScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Portfolio</Text>
      <View style={styles.card}>
        <Text style={styles.emptyText}>No portfolios yet. Create one to start tracking.</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md },
  title: { ...typography.heading, color: colors.text, marginBottom: spacing.lg },
  card: { backgroundColor: colors.surface, borderRadius: 12, padding: spacing.xl, alignItems: 'center' },
  emptyText: { ...typography.body, color: colors.textMuted, textAlign: 'center' },
});
