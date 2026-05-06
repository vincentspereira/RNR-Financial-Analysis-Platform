import { DarkTheme as NavDarkTheme, Theme } from '@react-navigation/native';
import { ColorSchemeName } from 'react-native';

const colors = {
  primary: '#3b82f6',
  primaryDark: '#2563eb',
  accent: '#10b981',
  danger: '#ef4444',
  warning: '#f59e0b',
  background: '#0f172a',
  surface: '#1e293b',
  surfaceLight: '#334155',
  text: '#f8fafc',
  textMuted: '#94a3b8',
  border: '#334155',
  chart: {
    green: '#10b981',
    red: '#ef4444',
    blue: '#3b82f6',
    purple: '#8b5cf6',
    orange: '#f97316',
    teal: '#14b8a6',
  },
};

const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

const typography = {
  heading: { fontSize: 24, fontWeight: '700' as const },
  subheading: { fontSize: 18, fontWeight: '600' as const },
  body: { fontSize: 16, fontWeight: '400' as const },
  caption: { fontSize: 12, fontWeight: '400' as const },
  mono: { fontSize: 14, fontFamily: 'monospace' as const },
};

export const theme: Theme = {
  ...NavDarkTheme,
  colors: {
    ...NavDarkTheme.colors,
    primary: colors.primary,
    background: colors.background,
    card: colors.surface,
    text: colors.text,
    border: colors.border,
    notification: colors.danger,
  },
};

export { colors, spacing, typography };
