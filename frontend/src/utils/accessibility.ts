/**
 * Accessibility utilities for WCAG 2.1 AA compliance
 */
import React, { useEffect, useRef, useState } from 'react';

// ARIA live region manager
export class AriaLiveRegionManager {
  private politeRegion: HTMLElement | null = null;
  private assertiveRegion: HTMLElement | null = null;
  
  constructor() {
    this.createLiveRegions();
  }
  
  private createLiveRegions(): void {
    // Create polite live region
    this.politeRegion = document.createElement('div');
    this.politeRegion.setAttribute('aria-live', 'polite');
    this.politeRegion.setAttribute('aria-atomic', 'true');
    this.politeRegion.className = 'sr-only';
    document.body.appendChild(this.politeRegion);
    
    // Create assertive live region
    this.assertiveRegion = document.createElement('div');
    this.assertiveRegion.setAttribute('aria-live', 'assertive');
    this.assertiveRegion.setAttribute('aria-atomic', 'true');
    this.assertiveRegion.className = 'sr-only';
    document.body.appendChild(this.assertiveRegion);
  }
  
  public announce(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
    const region = priority === 'assertive' ? this.assertiveRegion : this.politeRegion;
    
    if (region) {
      // Clear previous message
      region.textContent = '';
      
      // Add new message after a brief delay to ensure screen readers pick it up
      setTimeout(() => {
        region.textContent = message;
      }, 100);
      
      // Clear message after 5 seconds
      setTimeout(() => {
        region.textContent = '';
      }, 5000);
    }
  }
  
  public destroy(): void {
    if (this.politeRegion) {
      document.body.removeChild(this.politeRegion);
      this.politeRegion = null;
    }
    
    if (this.assertiveRegion) {
      document.body.removeChild(this.assertiveRegion);
      this.assertiveRegion = null;
    }
  }
}

// Focus management utilities
export class FocusManager {
  private focusStack: HTMLElement[] = [];
  
  public trapFocus(container: HTMLElement): () => void {
    const focusableElements = this.getFocusableElements(container);
    
    if (focusableElements.length === 0) return () => {};
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    // Store current focus
    const previouslyFocused = document.activeElement as HTMLElement;
    this.focusStack.push(previouslyFocused);
    
    // Focus first element
    firstElement.focus();
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          // Shift + Tab
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          // Tab
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
      
      if (e.key === 'Escape') {
        this.restoreFocus();
      }
    };
    
    container.addEventListener('keydown', handleKeyDown);
    
    // Return cleanup function
    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      this.restoreFocus();
    };
  }
  
  public restoreFocus(): void {
    const previousElement = this.focusStack.pop();
    if (previousElement && document.contains(previousElement)) {
      previousElement.focus();
    }
  }
  
  public getFocusableElements(container: HTMLElement): HTMLElement[] {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(', ');
    
    return Array.from(container.querySelectorAll(focusableSelectors))
      .filter((element) => {
        const el = element as HTMLElement;
        return el.offsetWidth > 0 && el.offsetHeight > 0 && !el.hidden;
      }) as HTMLElement[];
  }
  
  public moveFocusToNext(currentElement: HTMLElement): void {
    const focusableElements = this.getFocusableElements(document.body);
    const currentIndex = focusableElements.indexOf(currentElement);
    
    if (currentIndex !== -1 && currentIndex < focusableElements.length - 1) {
      focusableElements[currentIndex + 1].focus();
    }
  }
  
  public moveFocusToPrevious(currentElement: HTMLElement): void {
    const focusableElements = this.getFocusableElements(document.body);
    const currentIndex = focusableElements.indexOf(currentElement);
    
    if (currentIndex > 0) {
      focusableElements[currentIndex - 1].focus();
    }
  }
}

// Keyboard navigation utilities
export class KeyboardNavigationManager {
  private shortcuts: Map<string, () => void> = new Map();
  
  constructor() {
    this.setupGlobalKeyboardHandlers();
  }
  
  private setupGlobalKeyboardHandlers(): void {
    document.addEventListener('keydown', (e) => {
      // Skip navigation
      if (e.key === 'Tab' && e.altKey) {
        e.preventDefault();
        this.handleSkipNavigation();
      }
      
      // Global shortcuts
      const shortcutKey = this.getShortcutKey(e);
      const handler = this.shortcuts.get(shortcutKey);
      
      if (handler) {
        e.preventDefault();
        handler();
      }
    });
  }
  
  private getShortcutKey(e: KeyboardEvent): string {
    const modifiers = [];
    if (e.ctrlKey) modifiers.push('ctrl');
    if (e.altKey) modifiers.push('alt');
    if (e.shiftKey) modifiers.push('shift');
    if (e.metaKey) modifiers.push('meta');
    
    return [...modifiers, e.key.toLowerCase()].join('+');
  }
  
  private handleSkipNavigation(): void {
    const skipLinks = document.querySelectorAll('[data-skip-link]');
    if (skipLinks.length > 0) {
      (skipLinks[0] as HTMLElement).focus();
    }
  }
  
  public registerShortcut(keys: string, handler: () => void): () => void {
    this.shortcuts.set(keys.toLowerCase(), handler);
    
    return () => {
      this.shortcuts.delete(keys.toLowerCase());
    };
  }
  
  public handleArrowNavigation(
    e: KeyboardEvent,
    items: HTMLElement[],
    currentIndex: number,
    orientation: 'horizontal' | 'vertical' | 'both' = 'both'
  ): number {
    let newIndex = currentIndex;
    
    switch (e.key) {
      case 'ArrowUp':
        if (orientation === 'vertical' || orientation === 'both') {
          e.preventDefault();
          newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        }
        break;
      case 'ArrowDown':
        if (orientation === 'vertical' || orientation === 'both') {
          e.preventDefault();
          newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        }
        break;
      case 'ArrowLeft':
        if (orientation === 'horizontal' || orientation === 'both') {
          e.preventDefault();
          newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        }
        break;
      case 'ArrowRight':
        if (orientation === 'horizontal' || orientation === 'both') {
          e.preventDefault();
          newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        }
        break;
      case 'Home':
        e.preventDefault();
        newIndex = 0;
        break;
      case 'End':
        e.preventDefault();
        newIndex = items.length - 1;
        break;
    }
    
    if (newIndex !== currentIndex && items[newIndex]) {
      items[newIndex].focus();
    }
    
    return newIndex;
  }
}

// Color contrast utilities
export class ColorContrastChecker {
  public static calculateLuminance(r: number, g: number, b: number): number {
    const [rs, gs, bs] = [r, g, b].map(c => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  }
  
  public static calculateContrastRatio(color1: string, color2: string): number {
    const rgb1 = this.hexToRgb(color1);
    const rgb2 = this.hexToRgb(color2);
    
    if (!rgb1 || !rgb2) return 0;
    
    const lum1 = this.calculateLuminance(rgb1.r, rgb1.g, rgb1.b);
    const lum2 = this.calculateLuminance(rgb2.r, rgb2.g, rgb2.b);
    
    const brightest = Math.max(lum1, lum2);
    const darkest = Math.min(lum1, lum2);
    
    return (brightest + 0.05) / (darkest + 0.05);
  }
  
  private static hexToRgb(hex: string): { r: number; g: number; b: number } | null {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  }
  
  public static meetsWCAGAA(foreground: string, background: string, isLargeText: boolean = false): boolean {
    const ratio = this.calculateContrastRatio(foreground, background);
    return isLargeText ? ratio >= 3 : ratio >= 4.5;
  }
  
  public static meetsWCAGAAA(foreground: string, background: string, isLargeText: boolean = false): boolean {
    const ratio = this.calculateContrastRatio(foreground, background);
    return isLargeText ? ratio >= 4.5 : ratio >= 7;
  }
}

// Screen reader utilities
export class ScreenReaderUtils {
  public static announcePageChange(title: string): void {
    ariaLiveRegionManager.announce(`Navigated to ${title}`, 'polite');
  }
  
  public static announceFormError(fieldName: string, error: string): void {
    ariaLiveRegionManager.announce(`Error in ${fieldName}: ${error}`, 'assertive');
  }
  
  public static announceSuccess(message: string): void {
    ariaLiveRegionManager.announce(`Success: ${message}`, 'polite');
  }
  
  public static announceLoading(message: string = 'Loading'): void {
    ariaLiveRegionManager.announce(message, 'polite');
  }
  
  public static announceLoadingComplete(message: string = 'Loading complete'): void {
    ariaLiveRegionManager.announce(message, 'polite');
  }
}

// React hooks for accessibility
export const useAnnouncer = () => {
  return {
    announce: (message: string, priority: 'polite' | 'assertive' = 'polite') => {
      ariaLiveRegionManager.announce(message, priority);
    },
    announcePageChange: ScreenReaderUtils.announcePageChange,
    announceFormError: ScreenReaderUtils.announceFormError,
    announceSuccess: ScreenReaderUtils.announceSuccess,
    announceLoading: ScreenReaderUtils.announceLoading,
    announceLoadingComplete: ScreenReaderUtils.announceLoadingComplete,
  };
};

export const useFocusTrap = (isActive: boolean) => {
  const containerRef = useRef<HTMLElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  
  useEffect(() => {
    if (isActive && containerRef.current) {
      cleanupRef.current = focusManager.trapFocus(containerRef.current);
    } else if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
    };
  }, [isActive]);
  
  return containerRef;
};

export const useKeyboardNavigation = (
  items: HTMLElement[],
  orientation: 'horizontal' | 'vertical' | 'both' = 'both'
) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  
  const handleKeyDown = (e: KeyboardEvent) => {
    const newIndex = keyboardNavigationManager.handleArrowNavigation(
      e,
      items,
      currentIndex,
      orientation
    );
    setCurrentIndex(newIndex);
  };
  
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [items, currentIndex, orientation]);
  
  return { currentIndex, setCurrentIndex };
};

export const useReducedMotion = () => {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);
  
  return prefersReducedMotion;
};

export const useHighContrast = () => {
  const [prefersHighContrast, setPrefersHighContrast] = useState(false);
  
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: high)');
    setPrefersHighContrast(mediaQuery.matches);
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersHighContrast(e.matches);
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);
  
  return prefersHighContrast;
};

// Accessibility testing utilities
export class AccessibilityTester {
  public static async runBasicTests(): Promise<{
    issues: Array<{ type: string; message: string; element?: HTMLElement }>;
    score: number;
  }> {
    const issues: Array<{ type: string; message: string; element?: HTMLElement }> = [];
    
    // Check for missing alt text on images
    const images = document.querySelectorAll('img');
    images.forEach((img) => {
      if (!img.alt && !img.getAttribute('aria-label')) {
        issues.push({
          type: 'missing-alt-text',
          message: 'Image missing alt text',
          element: img as HTMLElement,
        });
      }
    });
    
    // Check for missing form labels
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach((input) => {
      const hasLabel = input.id && document.querySelector(`label[for="${input.id}"]`);
      const hasAriaLabel = input.getAttribute('aria-label') || input.getAttribute('aria-labelledby');
      
      if (!hasLabel && !hasAriaLabel) {
        issues.push({
          type: 'missing-form-label',
          message: 'Form control missing label',
          element: input as HTMLElement,
        });
      }
    });
    
    // Check for missing headings hierarchy
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    let previousLevel = 0;
    headings.forEach((heading) => {
      const level = parseInt(heading.tagName.charAt(1));
      if (level > previousLevel + 1) {
        issues.push({
          type: 'heading-hierarchy',
          message: `Heading level ${level} follows level ${previousLevel}, skipping levels`,
          element: heading as HTMLElement,
        });
      }
      previousLevel = level;
    });
    
    // Check for low contrast
    const textElements = document.querySelectorAll('p, span, div, a, button, label');
    textElements.forEach((element) => {
      const styles = window.getComputedStyle(element);
      const color = styles.color;
      const backgroundColor = styles.backgroundColor;
      
      if (color && backgroundColor && color !== backgroundColor) {
        // This is a simplified check - in practice, you'd need more sophisticated color parsing
        const isLowContrast = color === 'rgb(128, 128, 128)' && backgroundColor === 'rgb(255, 255, 255)';
        if (isLowContrast) {
          issues.push({
            type: 'low-contrast',
            message: 'Text may have insufficient contrast',
            element: element as HTMLElement,
          });
        }
      }
    });
    
    // Calculate score (100 - number of issues)
    const score = Math.max(0, 100 - issues.length * 5);
    
    return { issues, score };
  }
}

// Global instances
export const ariaLiveRegionManager = new AriaLiveRegionManager();
export const focusManager = new FocusManager();
export const keyboardNavigationManager = new KeyboardNavigationManager();

// Initialize accessibility features
export const initializeAccessibility = () => {
  // Add skip links
  const skipLink = document.createElement('a');
  skipLink.href = '#main-content';
  skipLink.textContent = 'Skip to main content';
  skipLink.className = 'sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 bg-blue-600 text-white p-2 z-50';
  skipLink.setAttribute('data-skip-link', 'true');
  document.body.insertBefore(skipLink, document.body.firstChild);
  
  // Register global keyboard shortcuts
  keyboardNavigationManager.registerShortcut('alt+1', () => {
    const mainContent = document.getElementById('main-content');
    if (mainContent) mainContent.focus();
  });
  
  keyboardNavigationManager.registerShortcut('alt+2', () => {
    const navigation = document.querySelector('[role="navigation"]') as HTMLElement;
    if (navigation) navigation.focus();
  });
  
  // Add ARIA landmarks if missing
  const main = document.querySelector('main');
  if (main && !main.getAttribute('role')) {
    main.setAttribute('role', 'main');
    main.id = main.id || 'main-content';
  }
  
  console.log('Accessibility features initialized');
};