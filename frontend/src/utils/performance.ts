/**
 * Frontend Performance Monitoring Utilities
 */

// Performance metrics interface
interface PerformanceMetrics {
  loadTime: number;
  domContentLoaded: number;
  firstContentfulPaint: number;
  largestContentfulPaint: number;
  firstInputDelay: number;
  cumulativeLayoutShift: number;
  timeToInteractive: number;
}

// Performance observer for Core Web Vitals
class WebVitalsMonitor {
  private metrics: Partial<PerformanceMetrics> = {};
  private observers: PerformanceObserver[] = [];

  constructor() {
    this.initializeObservers();
  }

  private initializeObservers(): void {
    // Largest Contentful Paint (LCP)
    if ('PerformanceObserver' in window) {
      try {
        const lcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1] as any;
          this.metrics.largestContentfulPaint = lastEntry.startTime;
          this.reportMetric('LCP', lastEntry.startTime);
        });
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
        this.observers.push(lcpObserver);
      } catch (e) {
        console.warn('LCP observer not supported');
      }

      // First Input Delay (FID)
      try {
        const fidObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry: any) => {
            this.metrics.firstInputDelay = entry.processingStart - entry.startTime;
            this.reportMetric('FID', entry.processingStart - entry.startTime);
          });
        });
        fidObserver.observe({ entryTypes: ['first-input'] });
        this.observers.push(fidObserver);
      } catch (e) {
        console.warn('FID observer not supported');
      }

      // Cumulative Layout Shift (CLS)
      try {
        let clsValue = 0;
        const clsObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry: any) => {
            if (!entry.hadRecentInput) {
              clsValue += entry.value;
            }
          });
          this.metrics.cumulativeLayoutShift = clsValue;
          this.reportMetric('CLS', clsValue);
        });
        clsObserver.observe({ entryTypes: ['layout-shift'] });
        this.observers.push(clsObserver);
      } catch (e) {
        console.warn('CLS observer not supported');
      }

      // First Contentful Paint (FCP)
      try {
        const fcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry: any) => {
            if (entry.name === 'first-contentful-paint') {
              this.metrics.firstContentfulPaint = entry.startTime;
              this.reportMetric('FCP', entry.startTime);
            }
          });
        });
        fcpObserver.observe({ entryTypes: ['paint'] });
        this.observers.push(fcpObserver);
      } catch (e) {
        console.warn('FCP observer not supported');
      }
    }

    // Navigation timing
    this.measureNavigationTiming();
  }

  private measureNavigationTiming(): void {
    if ('performance' in window && 'timing' in performance) {
      window.addEventListener('load', () => {
        const timing = performance.timing;
        this.metrics.loadTime = timing.loadEventEnd - timing.navigationStart;
        this.metrics.domContentLoaded = timing.domContentLoadedEventEnd - timing.navigationStart;
        
        this.reportMetric('Load Time', this.metrics.loadTime);
        this.reportMetric('DOM Content Loaded', this.metrics.domContentLoaded);
      });
    }
  }

  private reportMetric(name: string, value: number): void {
    // Send to analytics service
    if (typeof gtag !== 'undefined') {
      gtag('event', 'web_vitals', {
        metric_name: name,
        metric_value: Math.round(value),
        custom_parameter: value,
      });
    }

    // Log for development
    if (process.env.NODE_ENV === 'development') {
      console.log(`Performance Metric - ${name}: ${Math.round(value)}ms`);
    }
  }

  public getMetrics(): Partial<PerformanceMetrics> {
    return { ...this.metrics };
  }

  public disconnect(): void {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
  }
}

// Resource loading performance monitor
class ResourceMonitor {
  private resourceMetrics: Map<string, number> = new Map();

  constructor() {
    this.initializeResourceObserver();
  }

  private initializeResourceObserver(): void {
    if ('PerformanceObserver' in window) {
      try {
        const resourceObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry: any) => {
            const duration = entry.responseEnd - entry.startTime;
            this.resourceMetrics.set(entry.name, duration);
            
            // Report slow resources
            if (duration > 1000) { // Resources taking more than 1 second
              console.warn(`Slow resource: ${entry.name} took ${Math.round(duration)}ms`);
              
              if (typeof gtag !== 'undefined') {
                gtag('event', 'slow_resource', {
                  resource_url: entry.name,
                  load_time: Math.round(duration),
                  resource_type: entry.initiatorType,
                });
              }
            }
          });
        });
        
        resourceObserver.observe({ entryTypes: ['resource'] });
      } catch (e) {
        console.warn('Resource observer not supported');
      }
    }
  }

  public getSlowResources(threshold: number = 1000): Array<{ url: string; duration: number }> {
    const slowResources: Array<{ url: string; duration: number }> = [];
    
    this.resourceMetrics.forEach((duration, url) => {
      if (duration > threshold) {
        slowResources.push({ url, duration });
      }
    });
    
    return slowResources.sort((a, b) => b.duration - a.duration);
  }
}

// Memory usage monitor
class MemoryMonitor {
  private memoryMetrics: Array<{ timestamp: number; usedJSHeapSize: number }> = [];

  constructor() {
    this.startMonitoring();
  }

  private startMonitoring(): void {
    if ('memory' in performance) {
      setInterval(() => {
        const memory = (performance as any).memory;
        this.memoryMetrics.push({
          timestamp: Date.now(),
          usedJSHeapSize: memory.usedJSHeapSize,
        });

        // Keep only last 100 measurements
        if (this.memoryMetrics.length > 100) {
          this.memoryMetrics = this.memoryMetrics.slice(-100);
        }

        // Alert on high memory usage
        const usedMB = memory.usedJSHeapSize / 1024 / 1024;
        if (usedMB > 100) { // Alert if using more than 100MB
          console.warn(`High memory usage: ${Math.round(usedMB)}MB`);
        }
      }, 10000); // Check every 10 seconds
    }
  }

  public getCurrentMemoryUsage(): number {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize / 1024 / 1024; // MB
    }
    return 0;
  }

  public getMemoryTrend(): Array<{ timestamp: number; usedJSHeapSize: number }> {
    return [...this.memoryMetrics];
  }
}

// Bundle size analyzer
class BundleAnalyzer {
  public static analyzeBundleSize(): void {
    if ('performance' in window && 'getEntriesByType' in performance) {
      const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      
      let totalJSSize = 0;
      let totalCSSSize = 0;
      let totalImageSize = 0;
      
      resources.forEach((resource) => {
        const size = resource.transferSize || 0;
        
        if (resource.name.includes('.js')) {
          totalJSSize += size;
        } else if (resource.name.includes('.css')) {
          totalCSSSize += size;
        } else if (resource.name.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i)) {
          totalImageSize += size;
        }
      });
      
      const analysis = {
        totalJS: Math.round(totalJSSize / 1024), // KB
        totalCSS: Math.round(totalCSSSize / 1024), // KB
        totalImages: Math.round(totalImageSize / 1024), // KB
        total: Math.round((totalJSSize + totalCSSSize + totalImageSize) / 1024), // KB
      };
      
      console.log('Bundle Analysis:', analysis);
      
      // Report to analytics
      if (typeof gtag !== 'undefined') {
        gtag('event', 'bundle_analysis', {
          js_size_kb: analysis.totalJS,
          css_size_kb: analysis.totalCSS,
          images_size_kb: analysis.totalImages,
          total_size_kb: analysis.total,
        });
      }
      
      return analysis;
    }
  }
}

// Performance budget checker
class PerformanceBudget {
  private budgets = {
    loadTime: 3000, // 3 seconds
    firstContentfulPaint: 1500, // 1.5 seconds
    largestContentfulPaint: 2500, // 2.5 seconds
    firstInputDelay: 100, // 100ms
    cumulativeLayoutShift: 0.1, // 0.1
    bundleSize: 500, // 500KB
  };

  public checkBudgets(metrics: Partial<PerformanceMetrics>): Array<{ metric: string; actual: number; budget: number; passed: boolean }> {
    const results: Array<{ metric: string; actual: number; budget: number; passed: boolean }> = [];
    
    Object.entries(this.budgets).forEach(([metric, budget]) => {
      const actual = metrics[metric as keyof PerformanceMetrics];
      if (actual !== undefined) {
        const passed = actual <= budget;
        results.push({ metric, actual, budget, passed });
        
        if (!passed) {
          console.warn(`Performance budget exceeded for ${metric}: ${actual} > ${budget}`);
        }
      }
    });
    
    return results;
  }

  public setBudget(metric: keyof typeof this.budgets, value: number): void {
    this.budgets[metric] = value;
  }
}

// Main performance manager
export class PerformanceManager {
  private webVitalsMonitor: WebVitalsMonitor;
  private resourceMonitor: ResourceMonitor;
  private memoryMonitor: MemoryMonitor;
  private performanceBudget: PerformanceBudget;

  constructor() {
    this.webVitalsMonitor = new WebVitalsMonitor();
    this.resourceMonitor = new ResourceMonitor();
    this.memoryMonitor = new MemoryMonitor();
    this.performanceBudget = new PerformanceBudget();
  }

  public getPerformanceReport(): {
    metrics: Partial<PerformanceMetrics>;
    slowResources: Array<{ url: string; duration: number }>;
    memoryUsage: number;
    budgetResults: Array<{ metric: string; actual: number; budget: number; passed: boolean }>;
  } {
    const metrics = this.webVitalsMonitor.getMetrics();
    const slowResources = this.resourceMonitor.getSlowResources();
    const memoryUsage = this.memoryMonitor.getCurrentMemoryUsage();
    const budgetResults = this.performanceBudget.checkBudgets(metrics);

    return {
      metrics,
      slowResources,
      memoryUsage,
      budgetResults,
    };
  }

  public startPerformanceMonitoring(): void {
    // Already started in constructors
    console.log('Performance monitoring started');
  }

  public stopPerformanceMonitoring(): void {
    this.webVitalsMonitor.disconnect();
    console.log('Performance monitoring stopped');
  }
}

// Utility functions
export const measureFunction = <T extends (...args: any[]) => any>(
  fn: T,
  name?: string
): T => {
  return ((...args: any[]) => {
    const start = performance.now();
    const result = fn(...args);
    const end = performance.now();
    
    console.log(`Function ${name || fn.name} took ${Math.round(end - start)}ms`);
    
    return result;
  }) as T;
};

export const measureAsyncFunction = <T extends (...args: any[]) => Promise<any>>(
  fn: T,
  name?: string
): T => {
  return (async (...args: any[]) => {
    const start = performance.now();
    const result = await fn(...args);
    const end = performance.now();
    
    console.log(`Async function ${name || fn.name} took ${Math.round(end - start)}ms`);
    
    return result;
  }) as T;
};

// React hook for performance monitoring
export const usePerformanceMonitoring = () => {
  const [performanceData, setPerformanceData] = React.useState<any>(null);
  
  React.useEffect(() => {
    const manager = new PerformanceManager();
    manager.startPerformanceMonitoring();
    
    // Get performance report after 5 seconds
    const timer = setTimeout(() => {
      setPerformanceData(manager.getPerformanceReport());
    }, 5000);
    
    return () => {
      clearTimeout(timer);
      manager.stopPerformanceMonitoring();
    };
  }, []);
  
  return performanceData;
};

// Global performance manager instance
export const performanceManager = new PerformanceManager();