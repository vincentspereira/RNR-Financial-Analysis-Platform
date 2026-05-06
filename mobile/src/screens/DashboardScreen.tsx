import React from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { colors, spacing, typography } from '../theme';
import { useAuth } from '../hooks/useAuth';

export default function DashboardScreen() {
  const { user } = useAuth();

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.greeting}>
        Good morning, {user?.first_name || 'Trader'}
      </Text>

      {/* Portfolio Summary Card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Portfolio Value</Text>
        <Text style={styles.cardValue}>$0.00</Text>
        <Text style={styles.cardSubtext}>Connect your portfolio to get started</Text>
      </View>

      {/* Market Overview */}
      <Text style={styles.sectionTitle}>Market Overview</Text>
      <View style={styles.card}>
        <Text style={styles.cardSubtext}>Loading market data...</Text>
      </View>

      {/* AI Insights */}
      <Text style={styles.sectionTitle}>AI Insights</Text>
      <View style={styles.card}>
        <Text style={styles.cardSubtext}>AI predictions loading after market data</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md },
  greeting: { ...typography.heading, color: colors.text, marginBottom: spacing.lg },
  sectionTitle: { ...typography.subheading, color: colors.text, marginTop: spacing.lg, marginBottom: spacing.sm },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  cardTitle: { ...typography.caption, color: colors.textMuted },
  cardValue: { ...typography.heading, color: colors.text, marginTop: spacing.xs },
  cardSubtext: { ...typography.caption, color: colors.textMuted, marginTop: spacing.xs },
});
