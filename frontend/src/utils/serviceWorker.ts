/**
 * Service Worker registration and management
 */

const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
  window.location.hostname === '[::1]' ||
  window.location.hostname.match(
    /^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/
  )
);

interface ServiceWorkerConfig {
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
  onOffline?: () => void;
  onOnline?: () => void;
}

export function register(config?: ServiceWorkerConfig) {
  if ('serviceWorker' in navigator) {
    const publicUrl = new URL(process.env.PUBLIC_URL || '', window.location.href);
    if (publicUrl.origin !== window.location.origin) {
      return;
    }

    window.addEventListener('load', () => {
      const swUrl = `${process.env.PUBLIC_URL}/sw.js`;

      if (isLocalhost) {
        checkValidServiceWorker(swUrl, config);
        navigator.serviceWorker.ready.then(() => {
          console.log(
            'This web app is being served cache-first by a service worker.'
          );
        });
      } else {
        registerValidSW(swUrl, config);
      }

      // Listen for online/offline events
      window.addEventListener('online', () => {
        console.log('App is online');
        config?.onOnline?.();
      });

      window.addEventListener('offline', () => {
        console.log('App is offline');
        config?.onOffline?.();
      });
    });
  }
}

async function registerValidSW(swUrl: string, config?: ServiceWorkerConfig) {
  try {
    const registration = await navigator.serviceWorker.register(swUrl);
    
    registration.onupdatefound = () => {
      const installingWorker = registration.installing;
      if (installingWorker == null) {
        return;
      }

      installingWorker.onstatechange = () => {
        if (installingWorker.state === 'installed') {
          if (navigator.serviceWorker.controller) {
            console.log(
              'New content is available and will be used when all tabs for this page are closed.'
            );
            config?.onUpdate?.(registration);
          } else {
            console.log('Content is cached for offline use.');
            config?.onSuccess?.(registration);
          }
        }
      };
    };
  } catch (error) {
    console.error('Error during service worker registration:', error);
  }
}

async function checkValidServiceWorker(swUrl: string, config?: ServiceWorkerConfig) {
  try {
    const response = await fetch(swUrl, {
      headers: { 'Service-Worker': 'script' },
    });

    const contentType = response.headers.get('content-type');
    if (
      response.status === 404 ||
      (contentType != null && contentType.indexOf('javascript') === -1)
    ) {
      const registration = await navigator.serviceWorker.ready;
      await registration.unregister();
      window.location.reload();
    } else {
      registerValidSW(swUrl, config);
    }
  } catch {
    console.log('No internet connection found. App is running in offline mode.');
    config?.onOffline?.();
  }
}

export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister();
      })
      .catch((error) => {
        console.error(error.message);
      });
  }
}

export async function updateServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.ready;
      await registration.update();
      console.log('Service worker updated');
    } catch (error) {
      console.error('Failed to update service worker:', error);
    }
  }
}

export function skipWaiting() {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
  }
}

export function invalidateCache(pattern: string) {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({
      type: 'CACHE_INVALIDATE',
      pattern: pattern
    });
  }
}

// Cache management utilities
export class CacheManager {
  static async getCacheSize(): Promise<number> {
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      let totalSize = 0;

      for (const cacheName of cacheNames) {
        const cache = await caches.open(cacheName);
        const requests = await cache.keys();
        
        for (const request of requests) {
          const response = await cache.match(request);
          if (response) {
            const blob = await response.blob();
            totalSize += blob.size;
          }
        }
      }

      return totalSize;
    }
    return 0;
  }

  static async clearAllCaches(): Promise<void> {
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(cacheName => caches.delete(cacheName)));
      console.log('All caches cleared');
    }
  }

  static async clearApiCache(): Promise<void> {
    if ('caches' in window) {
      await caches.delete('financial-analysis-api-v1');
      console.log('API cache cleared');
    }
  }

  static formatBytes(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}

// Offline detection
export class OfflineManager {
  private static listeners: Array<(online: boolean) => void> = [];

  static isOnline(): boolean {
    return navigator.onLine;
  }

  static addListener(callback: (online: boolean) => void): void {
    this.listeners.push(callback);
  }

  static removeListener(callback: (online: boolean) => void): void {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  static init(): void {
    window.addEventListener('online', () => {
      this.listeners.forEach(callback => callback(true));
    });

    window.addEventListener('offline', () => {
      this.listeners.forEach(callback => callback(false));
    });
  }
}

// Background sync for offline actions
export class BackgroundSync {
  static async registerSync(tag: string): Promise<void> {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      try {
        const registration = await navigator.serviceWorker.ready;
        await registration.sync.register(tag);
        console.log('Background sync registered:', tag);
      } catch (error) {
        console.error('Background sync registration failed:', error);
      }
    }
  }

  static async addPendingAction(action: any): Promise<void> {
    // Store in IndexedDB or localStorage for background sync
    const pendingActions = JSON.parse(localStorage.getItem('pendingActions') || '[]');
    pendingActions.push({
      id: Date.now().toString(),
      ...action,
      timestamp: Date.now()
    });
    localStorage.setItem('pendingActions', JSON.stringify(pendingActions));
    
    await this.registerSync('background-sync');
  }
}

// Push notification management
export class NotificationManager {
  static async requestPermission(): Promise<NotificationPermission> {
    if ('Notification' in window) {
      return await Notification.requestPermission();
    }
    return 'denied';
  }

  static async subscribeToPush(): Promise<PushSubscription | null> {
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: process.env.REACT_APP_VAPID_PUBLIC_KEY
        });
        return subscription;
      } catch (error) {
        console.error('Push subscription failed:', error);
        return null;
      }
    }
    return null;
  }

  static async unsubscribeFromPush(): Promise<boolean> {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        if (subscription) {
          return await subscription.unsubscribe();
        }
      } catch (error) {
        console.error('Push unsubscription failed:', error);
      }
    }
    return false;
  }
}