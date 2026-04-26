# Graph Report - .  (2026-04-26)

## Corpus Check
- Corpus is ~47,822 words - fits in a single context window. You may not need a graph.

## Summary
- 431 nodes · 542 edges · 42 communities detected
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Service Worker & Caching|Service Worker & Caching]]
- [[_COMMUNITY_Admin & Analytics Dashboard|Admin & Analytics Dashboard]]
- [[_COMMUNITY_WebSocket Client|WebSocket Client]]
- [[_COMMUNITY_Performance Monitoring|Performance Monitoring]]
- [[_COMMUNITY_Accessibility Testing|Accessibility Testing]]
- [[_COMMUNITY_App Entry & PWA Config|App Entry & PWA Config]]
- [[_COMMUNITY_API Service Layer|API Service Layer]]
- [[_COMMUNITY_PWA Network & Offline|PWA Network & Offline]]
- [[_COMMUNITY_Touch Gesture Recognition|Touch Gesture Recognition]]
- [[_COMMUNITY_Mobile Layout & Utils|Mobile Layout & Utils]]
- [[_COMMUNITY_Screen Reader & ARIA|Screen Reader & ARIA]]
- [[_COMMUNITY_Auth Context & Layout|Auth Context & Layout]]
- [[_COMMUNITY_Report Generation UI|Report Generation UI]]
- [[_COMMUNITY_Data Management UI|Data Management UI]]
- [[_COMMUNITY_Offline Storage Manager|Offline Storage Manager]]
- [[_COMMUNITY_ML Models Dashboard|ML Models Dashboard]]
- [[_COMMUNITY_Optimized Image Loading|Optimized Image Loading]]
- [[_COMMUNITY_Alert Manager UI|Alert Manager UI]]
- [[_COMMUNITY_Stock Screener UI|Stock Screener UI]]
- [[_COMMUNITY_Predictive Analytics UI|Predictive Analytics UI]]
- [[_COMMUNITY_Portfolio Management UI|Portfolio Management UI]]
- [[_COMMUNITY_Accessibility Provider|Accessibility Provider]]
- [[_COMMUNITY_Test Setup & Mocks|Test Setup & Mocks]]
- [[_COMMUNITY_Financial Chart Component|Financial Chart Component]]
- [[_COMMUNITY_Financial Ratios Display|Financial Ratios Display]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]

## God Nodes (most connected - your core abstractions)
1. `WebSocketClient` - 30 edges
2. `ApiService` - 20 edges
3. `React App Entry Point (index.html)` - 19 edges
4. `TouchGestureRecognizer` - 17 edges
5. `PWAManager` - 10 edges
6. `OfflineStorageManager` - 10 edges
7. `MobileUtils` - 9 edges
8. `KeyboardNavigationManager` - 7 edges
9. `WebVitalsMonitor` - 7 edges
10. `NetworkStatusManager` - 7 edges

## Surprising Connections (you probably didn't know these)
- `ProtectedRoute()` --calls--> `useAuth()`  [INFERRED]
  src\components\auth\ProtectedRoute.tsx → src\contexts\AuthContext.tsx
- `DashboardLayout()` --calls--> `useAuth()`  [INFERRED]
  src\components\layout\DashboardLayout.tsx → src\contexts\AuthContext.tsx
- `Analysis()` --calls--> `useAuth()`  [INFERRED]
  src\pages\Analysis.tsx → src\contexts\AuthContext.tsx

## Communities

### Community 0 - "Service Worker & Caching"
Cohesion: 0.08
Nodes (20): BackgroundSync, CacheManager, checkValidServiceWorker(), NotificationManager, OfflineManager, register(), registerValidSW(), unregister() (+12 more)

### Community 1 - "Admin & Analytics Dashboard"
Cohesion: 0.07
Nodes (20): loadTabData(), updateUser(), cn(), fetchOptimization(), fetchPredictions(), fetchRiskData(), fetchSignals(), getRiskLevel() (+12 more)

### Community 2 - "WebSocket Client"
Cohesion: 0.1
Nodes (1): WebSocketClient

### Community 3 - "Performance Monitoring"
Cohesion: 0.09
Nodes (6): BundleAnalyzer, MemoryMonitor, PerformanceBudget, PerformanceManager, ResourceMonitor, WebVitalsMonitor

### Community 4 - "Accessibility Testing"
Cohesion: 0.1
Nodes (5): AccessibilityTester, ColorContrastChecker, FocusManager, initializeAccessibility(), KeyboardNavigationManager

### Community 5 - "App Entry & PWA Config"
Cohesion: 0.12
Nodes (24): Accessibility Support (reduced-motion, high-contrast), Apple PWA Meta Tags, Critical Inline CSS, Content Security Policy, Dark Mode Support (prefers-color-scheme), DNS Prefetch for External Resources, Financial Analysis Platform, Google Fonts (fonts.googleapis.com, fonts.gstatic.com) (+16 more)

### Community 6 - "API Service Layer"
Cohesion: 0.12
Nodes (3): ApiService, loadDashboardData(), onSubmit()

### Community 7 - "PWA Network & Offline"
Cohesion: 0.14
Nodes (6): NetworkStatusManager, OfflineIndicator(), PWAInstallBanner(), PWAManager, useNetworkStatus(), usePWA()

### Community 8 - "Touch Gesture Recognition"
Cohesion: 0.18
Nodes (1): TouchGestureRecognizer

### Community 9 - "Mobile Layout & Utils"
Cohesion: 0.19
Nodes (5): checkMobile(), MobileUtils, PullToRefresh(), SwipeNavigation(), useTouchGestures()

### Community 10 - "Screen Reader & ARIA"
Cohesion: 0.27
Nodes (2): AriaLiveRegionManager, ScreenReaderUtils

### Community 11 - "Auth Context & Layout"
Cohesion: 0.2
Nodes (4): Analysis(), useAuth(), DashboardLayout(), ProtectedRoute()

### Community 12 - "Report Generation UI"
Cohesion: 0.2
Nodes (1): loadReports()

### Community 13 - "Data Management UI"
Cohesion: 0.2
Nodes (1): loadDataManagement()

### Community 14 - "Offline Storage Manager"
Cohesion: 0.27
Nodes (1): OfflineStorageManager

### Community 15 - "ML Models Dashboard"
Cohesion: 0.22
Nodes (1): loadMLModels()

### Community 16 - "Optimized Image Loading"
Cohesion: 0.28
Nodes (4): getOptimalImageFormat(), ImagePerformanceMonitor, supportsAVIF(), supportsWebP()

### Community 17 - "Alert Manager UI"
Cohesion: 0.22
Nodes (1): loadAlerts()

### Community 18 - "Stock Screener UI"
Cohesion: 0.25
Nodes (2): runPreset(), runScreener()

### Community 19 - "Predictive Analytics UI"
Cohesion: 0.29
Nodes (1): loadPredictiveAnalytics()

### Community 20 - "Portfolio Management UI"
Cohesion: 0.29
Nodes (1): loadPortfolio()

### Community 21 - "Accessibility Provider"
Cohesion: 0.33
Nodes (0): 

### Community 22 - "Test Setup & Mocks"
Cohesion: 0.33
Nodes (0): 

### Community 23 - "Financial Chart Component"
Cohesion: 0.4
Nodes (0): 

### Community 24 - "Financial Ratios Display"
Cohesion: 0.4
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 0.4
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 0.67
Nodes (2): handleKeyDown(), handleTabChange()

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 0.67
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 0.67
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 0.67
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 0.67
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **7 isolated node(s):** `Vite Bundler`, `Dark Mode Support (prefers-color-scheme)`, `Accessibility Support (reduced-motion, high-contrast)`, `Performance Monitoring (Core Web Vitals)`, `Inter Variable Font (inter-var.woff2)` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 33`** (2 nodes): `Watchlist.tsx`, `WatchlistPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (2 nodes): `cn()`, `cn.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `LoginForm.test.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Analytics.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `analytics.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `auth.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `financial.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `watchlist.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `initializeAccessibility()` connect `Accessibility Testing` to `Service Worker & Caching`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `ApiService` connect `API Service Layer` to `Admin & Analytics Dashboard`, `Data Management UI`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `WebSocketClient` connect `WebSocket Client` to `Service Worker & Caching`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **What connects `Vite Bundler`, `Dark Mode Support (prefers-color-scheme)`, `Accessibility Support (reduced-motion, high-contrast)` to the rest of the system?**
  _7 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Service Worker & Caching` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `Admin & Analytics Dashboard` be split into smaller, more focused modules?**
  _Cohesion score 0.07 - nodes in this community are weakly interconnected._
- **Should `WebSocket Client` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._