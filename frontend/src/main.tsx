/**
 * Main entry point for the React application
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { register as registerSW, OfflineManager } from './utils/serviceWorker'
import { performanceManager } from './utils/performance'
import { MobileUtils } from './utils/touchGestures'
import { initializeAccessibility } from './utils/accessibility'

// Initialize performance monitoring
performanceManager.startPerformanceMonitoring()

// Initialize mobile optimizations
if (MobileUtils.isMobile()) {
  MobileUtils.optimizeForMobile()
}

// Initialize accessibility features
initializeAccessibility()

// Initialize offline manager
OfflineManager.init()

// Register service worker
registerSW({
  onSuccess: () => {
    console.log('Service worker registered successfully')
  },
  onUpdate: () => {
    console.log('New content available, please refresh')
    // Show update notification
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('App Update Available', {
        body: 'A new version is available. Refresh to update.',
        icon: '/icons/icon-192x192.png',
        tag: 'app-update'
      })
    }
  },
  onOffline: () => {
    console.log('App is running in offline mode')
  },
  onOnline: () => {
    console.log('App is back online')
  }
})

// Remove loading screen
const loadingElement = document.querySelector('.loading-spinner')
if (loadingElement) {
  loadingElement.remove()
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);