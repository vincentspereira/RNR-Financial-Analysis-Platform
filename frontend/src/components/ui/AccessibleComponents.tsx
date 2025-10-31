/**
 * Accessible UI components compliant with WCAG 2.1 AA
 */
import React, { useState, useRef, useEffect, forwardRef } from 'react';
import { cn } from '@/utils/cn';
import { useFocusTrap, useAnnouncer, useKeyboardNavigation } from '@/utils/accessibility';

// Accessible Button Component
export interface AccessibleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  loadingText?: string;
  children: React.ReactNode;
}

export const AccessibleButton = forwardRef<HTMLButtonElement, AccessibleButtonProps>(
  ({ 
    variant = 'primary', 
    size = 'md', 
    loading = false, 
    loadingText = 'Loading...', 
    children, 
    className, 
    disabled,
    ...props 
  }, ref) => {
    const baseClasses = 'inline-flex items-center justify-center font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors';
    
    const variantClasses = {
      primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 disabled:bg-blue-300',
      secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500 disabled:bg-gray-100',
      danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 disabled:bg-red-300',
      ghost: 'text-gray-700 hover:bg-gray-100 focus:ring-gray-500 disabled:text-gray-400',
    };
    
    const sizeClasses = {
      sm: 'px-3 py-2 text-sm min-h-[36px]',
      md: 'px-4 py-2 text-base min-h-[44px]',
      lg: 'px-6 py-3 text-lg min-h-[52px]',
    };
    
    return (
      <button
        ref={ref}
        className={cn(baseClasses, variantClasses[variant], sizeClasses[size], className)}
        disabled={disabled || loading}
        aria-disabled={disabled || loading}
        aria-describedby={loading ? `${props.id}-loading` : undefined}
        {...props}
      >
        {loading && (
          <>
            <svg
              className="animate-spin -ml-1 mr-2 h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="sr-only" id={`${props.id}-loading`}>
              {loadingText}
            </span>
          </>
        )}
        {loading ? loadingText : children}
      </button>
    );
  }
);

AccessibleButton.displayName = 'AccessibleButton';

// Accessible Modal Component
export interface AccessibleModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
}

export const AccessibleModal: React.FC<AccessibleModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = 'md',
  closeOnOverlayClick = true,
  closeOnEscape = true,
}) => {
  const modalRef = useFocusTrap(isOpen);
  const { announce } = useAnnouncer();
  const titleId = `modal-title-${React.useId()}`;
  const descriptionId = `modal-description-${React.useId()}`;
  
  useEffect(() => {
    if (isOpen) {
      announce(`Modal opened: ${title}`, 'polite');
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, title, announce]);
  
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && closeOnEscape) {
        onClose();
      }
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, closeOnEscape, onClose]);
  
  if (!isOpen) return null;
  
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };
  
  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={closeOnOverlayClick ? onClose : undefined}
        aria-hidden="true"
      />
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          ref={modalRef}
          className={cn(
            'relative bg-white rounded-lg shadow-xl w-full transform transition-all',
            sizeClasses[size]
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h2 id={titleId} className="text-lg font-semibold text-gray-900">
              {title}
            </h2>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close modal"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Description */}
          {description && (
            <div className="px-6 py-2">
              <p id={descriptionId} className="text-sm text-gray-600">
                {description}
              </p>
            </div>
          )}
          
          {/* Content */}
          <div className="px-6 py-4">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};

// Accessible Form Input Component
export interface AccessibleInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  helperText?: string;
  required?: boolean;
}

export const AccessibleInput = forwardRef<HTMLInputElement, AccessibleInputProps>(
  ({ label, error, helperText, required, className, id, ...props }, ref) => {
    const inputId = id || `input-${React.useId()}`;
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;
    
    return (
      <div className="space-y-1">
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-gray-700"
        >
          {label}
          {required && (
            <span className="text-red-500 ml-1" aria-label="required">
              *
            </span>
          )}
        </label>
        
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            error && 'border-red-300 focus:ring-red-500 focus:border-red-500',
            className
          )}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={cn(
            error && errorId,
            helperText && helperId
          )}
          required={required}
          {...props}
        />
        
        {helperText && (
          <p id={helperId} className="text-sm text-gray-600">
            {helperText}
          </p>
        )}
        
        {error && (
          <p id={errorId} className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);

AccessibleInput.displayName = 'AccessibleInput';

// Accessible Dropdown/Select Component
export interface AccessibleSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: Array<{ value: string; label: string; disabled?: boolean }>;
  error?: string;
  helperText?: string;
  placeholder?: string;
}

export const AccessibleSelect = forwardRef<HTMLSelectElement, AccessibleSelectProps>(
  ({ label, options, error, helperText, placeholder, className, id, required, ...props }, ref) => {
    const selectId = id || `select-${React.useId()}`;
    const errorId = `${selectId}-error`;
    const helperId = `${selectId}-helper`;
    
    return (
      <div className="space-y-1">
        <label
          htmlFor={selectId}
          className="block text-sm font-medium text-gray-700"
        >
          {label}
          {required && (
            <span className="text-red-500 ml-1" aria-label="required">
              *
            </span>
          )}
        </label>
        
        <select
          ref={ref}
          id={selectId}
          className={cn(
            'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            error && 'border-red-300 focus:ring-red-500 focus:border-red-500',
            className
          )}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={cn(
            error && errorId,
            helperText && helperId
          )}
          required={required}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>
        
        {helperText && (
          <p id={helperId} className="text-sm text-gray-600">
            {helperText}
          </p>
        )}
        
        {error && (
          <p id={errorId} className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);

AccessibleSelect.displayName = 'AccessibleSelect';

// Accessible Tab Component
export interface Tab {
  id: string;
  label: string;
  content: React.ReactNode;
  disabled?: boolean;
}

export interface AccessibleTabsProps {
  tabs: Tab[];
  defaultActiveTab?: string;
  onTabChange?: (tabId: string) => void;
  orientation?: 'horizontal' | 'vertical';
}

export const AccessibleTabs: React.FC<AccessibleTabsProps> = ({
  tabs,
  defaultActiveTab,
  onTabChange,
  orientation = 'horizontal',
}) => {
  const [activeTab, setActiveTab] = useState(defaultActiveTab || tabs[0]?.id);
  const tabListRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  
  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    onTabChange?.(tabId);
  };
  
  const handleKeyDown = (e: KeyboardEvent, index: number) => {
    const enabledTabs = tabs.filter(tab => !tab.disabled);
    const currentIndex = enabledTabs.findIndex(tab => tab.id === activeTab);
    let newIndex = currentIndex;
    
    switch (e.key) {
      case 'ArrowRight':
      case 'ArrowDown':
        e.preventDefault();
        newIndex = (currentIndex + 1) % enabledTabs.length;
        break;
      case 'ArrowLeft':
      case 'ArrowUp':
        e.preventDefault();
        newIndex = (currentIndex - 1 + enabledTabs.length) % enabledTabs.length;
        break;
      case 'Home':
        e.preventDefault();
        newIndex = 0;
        break;
      case 'End':
        e.preventDefault();
        newIndex = enabledTabs.length - 1;
        break;
      default:
        return;
    }
    
    const newTab = enabledTabs[newIndex];
    if (newTab) {
      handleTabChange(newTab.id);
      const tabIndex = tabs.findIndex(tab => tab.id === newTab.id);
      tabRefs.current[tabIndex]?.focus();
    }
  };
  
  const activeTabContent = tabs.find(tab => tab.id === activeTab)?.content;
  
  return (
    <div className="w-full">
      {/* Tab List */}
      <div
        ref={tabListRef}
        role="tablist"
        aria-orientation={orientation}
        className={cn(
          'flex border-b border-gray-200',
          orientation === 'vertical' && 'flex-col border-b-0 border-r'
        )}
      >
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            ref={(el) => (tabRefs.current[index] = el)}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            id={`tab-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            disabled={tab.disabled}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              tab.disabled && 'opacity-50 cursor-not-allowed',
              orientation === 'vertical' && 'border-b-0 border-r-2 text-left'
            )}
            onClick={() => !tab.disabled && handleTabChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e.nativeEvent, index)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Tab Panel */}
      <div
        role="tabpanel"
        id={`tabpanel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        className="mt-4 focus:outline-none"
        tabIndex={0}
      >
        {activeTabContent}
      </div>
    </div>
  );
};

// Accessible Alert Component
export interface AccessibleAlertProps {
  type: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  children: React.ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
}

export const AccessibleAlert: React.FC<AccessibleAlertProps> = ({
  type,
  title,
  children,
  dismissible = false,
  onDismiss,
}) => {
  const { announce } = useAnnouncer();
  
  useEffect(() => {
    if (type === 'error') {
      announce(`Error: ${title || 'An error occurred'}`, 'assertive');
    } else if (type === 'success') {
      announce(`Success: ${title || 'Operation completed'}`, 'polite');
    }
  }, [type, title, announce]);
  
  const typeStyles = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    error: 'bg-red-50 border-red-200 text-red-800',
  };
  
  const iconMap = {
    info: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
      </svg>
    ),
    success: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    ),
  };
  
  return (
    <div
      role="alert"
      className={cn(
        'border rounded-md p-4',
        typeStyles[type]
      )}
    >
      <div className="flex">
        <div className="flex-shrink-0">
          {iconMap[type]}
        </div>
        <div className="ml-3 flex-1">
          {title && (
            <h3 className="text-sm font-medium mb-1">
              {title}
            </h3>
          )}
          <div className="text-sm">
            {children}
          </div>
        </div>
        {dismissible && (
          <div className="ml-auto pl-3">
            <button
              onClick={onDismiss}
              className="inline-flex rounded-md p-1.5 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent focus:ring-current"
              aria-label="Dismiss alert"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};