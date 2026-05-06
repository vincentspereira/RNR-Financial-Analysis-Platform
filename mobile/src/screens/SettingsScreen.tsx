import React from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable } from 'react-native';
import { colors, spacing, typography } from '../theme';
import { useAuth } from '../hooks/useAuth';

export default function SettingsScreen() {
  const { user, logout } = useAuth();

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Settings</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Account</Text>
        <Text style={styles.cardSubtext}>{user?.email || 'Not signed in'}</Text>
        <Text style={styles.cardSubtext}>Tier: {user?.subscription_tier || 'Free'}</Text>
      </View>

      <Pressable style={styles.logoutBtn} onPress={logout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </Pressable>

      <Text style={styles.version}>FinAnalytica v1.0.0</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md },
  title: { ...typography.heading, color: colors.text, marginBottom: spacing.lg },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  cardTitle: { ...typography.subheading, color: colors.text },
  cardSubtext: { ...typography.caption, color: colors.textMuted, marginTop: spacing.xs },
  logoutBtn: {
    backgroundColor: colors.danger,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
    marginTop: spacing.xl,
  },
  logoutText: { ...typography.body, color: '#fff', fontWeight: '600' },
  version: { ...typography.caption, color: colors.textMuted, textAlign: 'center', marginTop: spacing.xl },
});
