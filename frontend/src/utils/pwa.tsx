/**
 * PWA (Progressive Web App) utilities
 */
import React, { useState, useEffect } from 'react';

export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

export interface PWAInstallationState {
  canInstall: boolean;
  isInstalled: boolean;
  isStandalone: boolean;
  installPrompt: BeforeInstallPromptEvent | null;
}

export class PWAManager {
  private installPrompt: BeforeInstallPromptEvent | null = null;
  private listeners: Array<(state: PWAInstallationState) => void> = [];
  
  constructor() {
    this.setupEventListeners();
  }
  
  private setupEventListeners(): void {
    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.installPrompt = e as BeforeInstallPromptEvent;
      this.notifyListeners();
    });
    
    // Listen for app installed
    window.addEventListener('appinstalled', () => {
      this.installPrompt = null;
      this.notifyListeners();
    });
    
    // Listen for standalone mode changes
    window.addEventListener('resize', () => {
      this.notifyListeners();
    });
  }
  
  private notifyListeners(): void {
    const state = this.getInstallationState();
    this.listeners.forEach(listener => listener(state));
  }
  
  public getInstallationState(): PWAInstallationState {
    return {
      canInstall: this.installPrompt !== null,
      isInstalled: this.isInstalled(),
      isStandalone: this.isStandalone(),
      installPrompt: this.installPrompt,
    };
  }
  
  public isInstalled(): boolean {
    // Check if app is installed (various methods)
    return (
      this.isStandalone() ||
      document.referrer.includes('android-app://') ||
      window.navigator.standalone === true ||
      window.matchMedia('(display-mode: standalone)').matches
    );
  }
  
  public isStandalone(): boolean {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true ||
      document.referrer.includes('android-app://')
    );
  }
  
  public async promptInstall(): Promise<{ outcome: 'accepted' | 'dismissed'; platform: string } | null> {
    if (!this.installPrompt) {
      return null;
    }
    
    try {
      await this.installPrompt.prompt();
      const choiceResult = await this.installPrompt.userChoice;
      
      if (choiceResult.outcome === 'accepted') {
        this.installPrompt = null;
        this.notifyListeners();
      }
      
      return choiceResult;
    } catch (error) {
      console.error('Error prompting for install:', error);
      return null;
    }
  }
  
  public addListener(listener: (state: PWAInstallationState) => void): () => void {
    this.listeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }
  
  public getAppInfo(): {
    name: string;
    shortName: string;
    version: string;
    buildTime: string;
  } {
    return {
      name: 'RNR Financial Analysis Platform',
      shortName: 'FinAnalysis',
      version: (globalThis as any).__APP_VERSION__ || '1.0.0',
      buildTime: (globalThis as any).__BUILD_TIME__ || new Date().toISOString(),
    };
  }
}

// React hook for PWA functionality
export const usePWA = () => {
  const [pwaManager] = useState(() => new PWAManager());
  const [installationState, setInstallationState] = useState<PWAInstallationState>(
    pwaManager.getInstallationState()
  );
  
  useEffect(() => {
    const unsubscribe = pwaManager.addListener(setInstallationState);
    return unsubscribe;
  }, [pwaManager]);
  
  return {
    ...installationState,
    promptInstall: () => pwaManager.promptInstall(),
    appInfo: pwaManager.getAppInfo(),
  };
};

// Offline storage manager
export class OfflineStorageManager {
  private dbName = 'RNRFinancialAnalysisPlatform';
  private dbVersion = 1;
  private db: IDBDatabase | null = null;
  
  async initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };
      
      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        
        // Create object stores
        if (!db.objectStoreNames.contains('portfolios')) {
          db.createObjectStore('portfolios', { keyPath: 'id' });
        }
        
        if (!db.objectStoreNames.contains('marketData')) {
          const marketStore = db.createObjectStore('marketData', { keyPath: 'symbol' });
          marketStore.createIndex('timestamp', 'timestamp');
        }
        
        if (!db.objectStoreNames.contains('userPreferences')) {
          db.createObjectStore('userPreferences', { keyPath: 'key' });
        }
        
        if (!db.objectStoreNames.contains('offlineActions')) {
          const actionsStore = db.createObjectStore('offlineActions', { keyPath: 'id', autoIncrement: true });
          actionsStore.createIndex('timestamp', 'timestamp');
        }
      };
    });
  }
  
  async storeData(storeName: string, data: any): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.put(data);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }
  
  async getData(storeName: string, key: string): Promise<any> {
    if (!this.db) throw new Error('Database not initialized');
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const request = store.get(key);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }
  
  async getAllData(storeName: string): Promise<any[]> {
    if (!this.db) throw new Error('Database not initialized');
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const request = store.getAll();
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }
  
  async deleteData(storeName: string, key: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.delete(key);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }
  
  async clearStore(storeName: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');
    
    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.clear();
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }
  
  // Offline actions queue
  async queueOfflineAction(action: {
    type: string;
    url: string;
    method: string;
    data?: any;
    headers?: Record<string, string>;
  }): Promise<void> {
    const offlineAction = {
      ...action,
      timestamp: Date.now(),
      retryCount: 0,
    };
    
    await this.storeData('offlineActions', offlineAction);
  }
  
  async getOfflineActions(): Promise<any[]> {
    return this.getAllData('offlineActions');
  }
  
  async removeOfflineAction(id: number): Promise<void> {
    await this.deleteData('offlineActions', id.toString());
  }
}

// Network status manager
export class NetworkStatusManager {
  private listeners: Array<(isOnline: boolean) => void> = [];
  private isOnline = navigator.onLine;
  
  constructor() {
    this.setupEventListeners();
  }
  
  private setupEventListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.notifyListeners();
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.notifyListeners();
    });
  }
  
  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.isOnline));
  }
  
  public getNetworkStatus(): boolean {
    return this.isOnline;
  }
  
  public addListener(listener: (isOnline: boolean) => void): () => void {
    this.listeners.push(listener);
    
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }
  
  public async checkConnectivity(): Promise<boolean> {
    try {
      const response = await fetch('/api/v1/health', {
        method: 'HEAD',
        cache: 'no-cache',
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}

// React hook for network status
export const useNetworkStatus = () => {
  const [networkManager] = useState(() => new NetworkStatusManager());
  const [isOnline, setIsOnline] = useState(networkManager.getNetworkStatus());
  
  useEffect(() => {
    const unsubscribe = networkManager.addListener(setIsOnline);
    return unsubscribe;
  }, [networkManager]);
  
  return {
    isOnline,
    checkConnectivity: () => networkManager.checkConnectivity(),
  };
};

// PWA install banner component
export interface PWAInstallBannerProps {
  onInstall?: () => void;
  onDismiss?: () => void;
}

export const PWAInstallBanner: React.FC<PWAInstallBannerProps> = ({
  onInstall,
  onDismiss,
}) => {
  const { canInstall, isInstalled, promptInstall } = usePWA();
  const [isDismissed, setIsDismissed] = useState(false);
  
  useEffect(() => {
    // Check if banner was previously dismissed
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    setIsDismissed(dismissed === 'true');
  }, []);
  
  const handleInstall = async () => {
    const result = await promptInstall();
    if (result?.outcome === 'accepted') {
      onInstall?.();
    }
  };
  
  const handleDismiss = () => {
    setIsDismissed(true);
    localStorage.setItem('pwa-install-dismissed', 'true');
    onDismiss?.();
  };
  
  if (!canInstall || isInstalled || isDismissed) {
    return null;
  }
  
  return (
    <div className="fixed bottom-4 left-4 right-4 bg-blue-600 text-white rounded-lg shadow-lg p-4 z-50 md:max-w-sm md:left-auto">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
        
        <div className="flex-1">
          <h3 className="text-sm font-medium">Install App</h3>
          <p className="text-sm opacity-90 mt-1">
            Add RNR Financial Analysis Platform to your home screen for quick access.
          </p>
          
          <div className="flex space-x-2 mt-3">
            <button
              onClick={handleInstall}
              className="bg-white text-blue-600 px-3 py-1 rounded text-sm font-medium hover:bg-gray-100"
            >
              Install
            </button>
            <button
              onClick={handleDismiss}
              className="text-white opacity-75 hover:opacity-100 px-3 py-1 rounded text-sm"
            >
              Not now
            </button>
          </div>
        </div>
        
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 text-white opacity-75 hover:opacity-100"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};

// Offline indicator component
export const OfflineIndicator: React.FC = () => {
  const { isOnline } = useNetworkStatus();
  
  if (isOnline) return null;
  
  return (
    <div className="fixed top-0 left-0 right-0 bg-red-600 text-white text-center py-2 text-sm z-50">
      <div className="flex items-center justify-center space-x-2">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192L5.636 18.364M12 2.25a9.75 9.75 0 11-9.75 9.75 9.75 9.75 0 019.75-9.75z" />
        </svg>
        <span>You're offline. Some features may be limited.</span>
      </div>
    </div>
  );
};

// Global instances
export const pwaManager = new PWAManager();
export const offlineStorageManager = new OfflineStorageManager();
export const networkStatusManager = new NetworkStatusManager();

// Initialize offline storage
offlineStorageManager.initialize().catch(console.error);