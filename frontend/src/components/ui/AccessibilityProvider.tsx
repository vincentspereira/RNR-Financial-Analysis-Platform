/**
 * Accessibility Provider Component
 */
import React, { createContext, useContext, useEffect, useState } from 'react';

interface AccessibilityContextType {
  highContrast: boolean;
  reducedMotion: boolean;
  fontSize: 'small' | 'medium' | 'large';
  screenReader: boolean;
  keyboardNavigation: boolean;
  toggleHighContrast: () => void;
  toggleReducedMotion: () => void;
  setFontSize: (size: 'small' | 'medium' | 'large') => void;
  announceToScreenReader: (message: string) => void;
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

interface AccessibilityProviderProps {
  children: React.ReactNode;
}

export function AccessibilityProvider({ children }: AccessibilityProviderProps) {
  const [highContrast, setHighContrast] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>('medium');
  const [screenReader, setScreenReader] = useState(false);
  const [keyboardNavigation, setKeyboardNavigation] = useState(false);

  // Detect system preferences
  useEffect(() => {
    // Check for reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // Detect screen reader usage
  useEffect(() => {
    const detectScreenReader = () => {
      // Check for common screen reader indicators
      const hasAriaLive = document.querySelector('[aria-live]');
      const hasScreenReaderText = document.querySelector('.sr-only');
      const userAgent = navigator.userAgent.toLowerCase();
      
      // Check for screen reader user agents
      const screenReaderIndicators = [
        'nvda', 'jaws', 'dragon', 'zoomtext', 'fusion', 'hal', 'supernova'
      ];
      
      const hasScreenReaderUA = screenReaderIndicators.some(indicator => 
        userAgent.includes(indicator)
      );

      setScreenReader(hasAriaLive !== null || hasScreenReaderText !== null || hasScreenReaderUA);
    };

    detectScreenReader();
  }, []);

  // Detect keyboard navigation
  useEffect(() => {
    let keyboardUsed = false;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        keyboardUsed = true;
        setKeyboardNavigation(true);
        document.body.classList.add('keyboard-navigation');
      }
    };

    const handleMouseDown = () => {
      if (keyboardUsed) {
        keyboardUsed = false;
        setKeyboardNavigation(false);
        document.body.classList.remove('keyboard-navigation');
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleMouseDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleMouseDown);
    };
  }, []);

  // Apply accessibility settings to document
  useEffect(() => {
    const root = document.documentElement;
    
    // High contrast mode
    if (highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }

    // Reduced motion
    if (reducedMotion) {
      root.classList.add('reduced-motion');
    } else {
      root.classList.remove('reduced-motion');
    }

    // Font size
    root.classList.remove('font-small', 'font-medium', 'font-large');
    root.classList.add(`font-${fontSize}`);

  }, [highContrast, reducedMotion, fontSize]);

  // Load saved preferences
  useEffect(() => {
    const savedPreferences = localStorage.getItem('accessibility-preferences');
    if (savedPreferences) {
      try {
        const preferences = JSON.parse(savedPreferences);
        setHighContrast(preferences.highContrast || false);
        setFontSize(preferences.fontSize || 'medium');
      } catch (error) {
        console.error('Failed to load accessibility preferences:', error);
      }
    }
  }, []);

  // Save preferences
  const savePreferences = (newPreferences: Partial<AccessibilityContextType>) => {
    const currentPreferences = {
      highContrast,
      fontSize,
      ...newPreferences
    };
    
    localStorage.setItem('accessibility-preferences', JSON.stringify(currentPreferences));
  };

  const toggleHighContrast = () => {
    const newValue = !highContrast;
    setHighContrast(newValue);
    savePreferences({ highContrast: newValue });
    announceToScreenReader(`High contrast mode ${newValue ? 'enabled' : 'disabled'}`);
  };

  const toggleReducedMotion = () => {
    const newValue = !reducedMotion;
    setReducedMotion(newValue);
    announceToScreenReader(`Reduced motion ${newValue ? 'enabled' : 'disabled'}`);
  };

  const handleSetFontSize = (size: 'small' | 'medium' | 'large') => {
    setFontSize(size);
    savePreferences({ fontSize: size });
    announceToScreenReader(`Font size changed to ${size}`);
  };

  const announceToScreenReader = (message: string) => {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    // Remove after announcement
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  };

  const value: AccessibilityContextType = {
    highContrast,
    reducedMotion,
    fontSize,
    screenReader,
    keyboardNavigation,
    toggleHighContrast,
    toggleReducedMotion,
    setFontSize: handleSetFontSize,
    announceToScreenReader,
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
      
      {/* Screen reader only announcements */}
      <div id="sr-announcements" aria-live="polite" aria-atomic="true" className="sr-only" />
      
      {/* Skip to main content link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-indigo-600 focus:text-white focus:rounded-md focus:shadow-lg"
      >
        Skip to main content
      </a>
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext);
  if (context === undefined) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
}

// Accessibility utility components
export function ScreenReaderOnly({ children }: { children: React.ReactNode }) {
  return <span className="sr-only">{children}</span>;
}

export function VisuallyHidden({ children }: { children: React.ReactNode }) {
  return (
    <span className="absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0">
      {children}
    </span>
  );
}

// Focus trap for modals and dialogs
export function FocusTrap({ children, active }: { children: React.ReactNode; active: boolean }) {
  const trapRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active || !trapRef.current) return;

    const focusableElements = trapRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement?.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement?.focus();
          e.preventDefault();
        }
      }
    };

    document.addEventListener('keydown', handleTabKey);
    firstElement?.focus();

    return () => {
      document.removeEventListener('keydown', handleTabKey);
    };
  }, [active]);

  return <div ref={trapRef}>{children}</div>;
}