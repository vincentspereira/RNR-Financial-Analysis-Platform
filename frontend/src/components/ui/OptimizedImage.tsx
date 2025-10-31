/**
 * Optimized Image Component with lazy loading and responsive images
 */
import React, { useState, useRef, useEffect } from 'react';
import { cn } from '@/utils/cn';

interface OptimizedImageProps {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
  sizes?: string;
  priority?: boolean;
  placeholder?: 'blur' | 'empty';
  blurDataURL?: string;
  onLoad?: () => void;
  onError?: () => void;
  loading?: 'lazy' | 'eager';
  quality?: number;
  responsive?: boolean;
}

export const OptimizedImage: React.FC<OptimizedImageProps> = ({
  src,
  alt,
  className,
  width,
  height,
  sizes,
  priority = false,
  placeholder = 'empty',
  blurDataURL,
  onLoad,
  onError,
  loading = 'lazy',
  quality = 75,
  responsive = true,
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isInView, setIsInView] = useState(priority);
  const imgRef = useRef<HTMLImageElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Intersection Observer for lazy loading
  useEffect(() => {
    if (priority || loading === 'eager') {
      setIsInView(true);
      return;
    }

    if (!imgRef.current) return;

    observerRef.current = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observerRef.current?.disconnect();
        }
      },
      {
        rootMargin: '50px', // Start loading 50px before the image comes into view
        threshold: 0.1,
      }
    );

    observerRef.current.observe(imgRef.current);

    return () => {
      observerRef.current?.disconnect();
    };
  }, [priority, loading]);

  // Generate responsive image URLs
  const generateSrcSet = (baseSrc: string) => {
    const sizes = [640, 768, 1024, 1280, 1536];
    return sizes
      .map(size => `${baseSrc}?w=${size}&q=${quality} ${size}w`)
      .join(', ');
  };

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  // Placeholder component
  const Placeholder = () => (
    <div
      className={cn(
        'bg-gray-200 animate-pulse flex items-center justify-center',
        className
      )}
      style={{ width, height }}
    >
      <svg
        className="w-8 h-8 text-gray-400"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
          clipRule="evenodd"
        />
      </svg>
    </div>
  );

  // Error component
  const ErrorFallback = () => (
    <div
      className={cn(
        'bg-gray-100 border-2 border-dashed border-gray-300 flex items-center justify-center',
        className
      )}
      style={{ width, height }}
    >
      <div className="text-center text-gray-500">
        <svg
          className="w-8 h-8 mx-auto mb-2"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
        <p className="text-sm">Failed to load image</p>
      </div>
    </div>
  );

  if (hasError) {
    return <ErrorFallback />;
  }

  return (
    <div className="relative overflow-hidden">
      {/* Blur placeholder */}
      {placeholder === 'blur' && blurDataURL && !isLoaded && (
        <img
          src={blurDataURL}
          alt=""
          className={cn(
            'absolute inset-0 w-full h-full object-cover filter blur-sm scale-110',
            className
          )}
          aria-hidden="true"
        />
      )}

      {/* Loading placeholder */}
      {placeholder === 'empty' && !isLoaded && <Placeholder />}

      {/* Main image */}
      {isInView && (
        <img
          ref={imgRef}
          src={src}
          alt={alt}
          width={width}
          height={height}
          sizes={sizes}
          srcSet={responsive ? generateSrcSet(src) : undefined}
          className={cn(
            'transition-opacity duration-300',
            isLoaded ? 'opacity-100' : 'opacity-0',
            responsive && 'w-full h-auto',
            className
          )}
          onLoad={handleLoad}
          onError={handleError}
          loading={loading}
          decoding="async"
        />
      )}
    </div>
  );
};

// Progressive image loading hook
export const useProgressiveImage = (src: string, placeholder?: string) => {
  const [currentSrc, setCurrentSrc] = useState(placeholder || '');
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      setCurrentSrc(src);
      setIsLoaded(true);
    };
    img.src = src;
  }, [src]);

  return { src: currentSrc, isLoaded };
};

// Image preloader utility
export class ImagePreloader {
  private static cache = new Set<string>();

  static preload(src: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.cache.has(src)) {
        resolve();
        return;
      }

      const img = new Image();
      img.onload = () => {
        this.cache.add(src);
        resolve();
      };
      img.onerror = reject;
      img.src = src;
    });
  }

  static preloadMultiple(sources: string[]): Promise<void[]> {
    return Promise.all(sources.map(src => this.preload(src)));
  }

  static clearCache(): void {
    this.cache.clear();
  }

  static getCacheSize(): number {
    return this.cache.size;
  }
}

// WebP support detection
export const supportsWebP = (): Promise<boolean> => {
  return new Promise((resolve) => {
    const webP = new Image();
    webP.onload = webP.onerror = () => {
      resolve(webP.height === 2);
    };
    webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
  });
};

// AVIF support detection
export const supportsAVIF = (): Promise<boolean> => {
  return new Promise((resolve) => {
    const avif = new Image();
    avif.onload = avif.onerror = () => {
      resolve(avif.height === 2);
    };
    avif.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADybWV0YQAAAAAAAAAoaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAGxpYmF2aWYAAAAADnBpdG0AAAAAAAEAAAAeaWxvYwAAAABEAAABAAEAAAABAAABGgAAAB0AAAAoaWluZgAAAAAAAQAAABppbmZlAgAAAAABAABhdjAxQ29sb3IAAAAAamlwcnAAAABLaXBjbwAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAAAxhdjFDgQ0MAAAAABNjb2xybmNseAACAAIAAYAAAAAXaXBtYQAAAAAAAAABAAEEAQKDBAAAACVtZGF0EgAKCBgABogQEAwgMg8f8D///8WfhwB8+ErK42A=';
  });
};

// Image format optimizer
export const getOptimalImageFormat = async (originalSrc: string): Promise<string> => {
  const [webpSupported, avifSupported] = await Promise.all([
    supportsWebP(),
    supportsAVIF(),
  ]);

  if (avifSupported) {
    return originalSrc.replace(/\.(jpg|jpeg|png)$/i, '.avif');
  } else if (webpSupported) {
    return originalSrc.replace(/\.(jpg|jpeg|png)$/i, '.webp');
  }

  return originalSrc;
};

// Performance monitoring for images
export class ImagePerformanceMonitor {
  private static metrics: Map<string, number> = new Map();

  static startLoad(src: string): void {
    this.metrics.set(src, performance.now());
  }

  static endLoad(src: string): number {
    const startTime = this.metrics.get(src);
    if (!startTime) return 0;

    const loadTime = performance.now() - startTime;
    this.metrics.delete(src);

    // Send to analytics
    if ('gtag' in window) {
      (window as any).gtag('event', 'image_load_time', {
        custom_parameter: loadTime,
        image_src: src,
      });
    }

    return loadTime;
  }

  static getAverageLoadTime(): number {
    const times = Array.from(this.metrics.values());
    return times.length > 0 ? times.reduce((a, b) => a + b, 0) / times.length : 0;
  }
}