import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, Pressable } from 'react-native';
import { colors, spacing, typography } from '../theme';
import { analyticsApi, sentimentApi } from '../services/api';

export default function ResearchScreen() {
  const [symbol, setSymbol] = useState('');

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Research</Text>

      <TextInput
        style={styles.input}
        placeholder="Enter symbol (e.g. AAPL)"
        placeholderTextColor={colors.textMuted}
        value={symbol}
        onChangeText={setSymbol.toUpperCase()}
        autoCapitalize="characters"
      />

      {/* AI Prediction */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Deep Learning Prediction</Text>
        <Text style={styles.cardSubtext}>LSTM price prediction will appear here</Text>
      </View>

      {/* Sentiment */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>News Sentiment</Text>
        <Text style={styles.cardSubtext}>NLP-analyzed sentiment data</Text>
      </View>

      {/* Risk Assessment */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Risk Assessment</Text>
        <Text style={styles.cardSubtext}>ML-based risk analysis</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md },
  title: { ...typography.heading, color: colors.text, marginBottom: spacing.lg },
  input: {
    backgroundColor: colors.surface,
    borderRadius: 8,
    padding: spacing.md,
    color: colors.text,
    ...typography.mono,
    marginBottom: spacing.lg,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  cardTitle: { ...typography.subheading, color: colors.text },
  cardSubtext: { ...typography.caption, color: colors.textMuted, marginTop: spacing.xs },
});
