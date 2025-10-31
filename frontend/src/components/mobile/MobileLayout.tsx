/**
 * Mobile-optimized layout components
 */
import React, { useState, useEffect } from 'react';
import { cn } from '@/utils/cn';
import { MobileUtils } from '@/utils/touchGestures';

// Mobile navigation component
export interface MobileNavProps {
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

export const MobileNav: React.FC<MobileNavProps> = ({ isOpen, onToggle, children }) => {
  useEffect(() => {
    // Prevent body scroll when nav is open
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);
  
  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={onToggle}
        />
      )}
      
      {/* Navigation drawer */}
      <div
        className={cn(
          'fixed top-0 left-0 h-full w-80 bg-white shadow-xl transform transition-transform duration-300 ease-in-out z-50 md:hidden',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-semibold">Menu</h2>
            <button
              onClick={onToggle}
              className="p-2 rounded-md hover:bg-gray-100"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </div>
      </div>
    </>
  );
};

// Mobile header component
export interface MobileHeaderProps {
  title: string;
  onMenuToggle?: () => void;
  actions?: React.ReactNode;
  showBackButton?: boolean;
  onBackClick?: () => void;
}

export const MobileHeader: React.FC<MobileHeaderProps> = ({
  title,
  onMenuToggle,
  actions,
  showBackButton = false,
  onBackClick,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-white border-b border-gray-200 md:hidden">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center space-x-3">
          {showBackButton ? (
            <button
              onClick={onBackClick}
              className="p-2 -ml-2 rounded-md hover:bg-gray-100"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          ) : onMenuToggle ? (
            <button
              onClick={onMenuToggle}
              className="p-2 -ml-2 rounded-md hover:bg-gray-100"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          ) : null}
          
          <h1 className="text-lg font-semibold text-gray-900 truncate">{title}</h1>
        </div>
        
        {actions && (
          <div className="flex items-center space-x-2">
            {actions}
          </div>
        )}
      </div>
    </header>
  );
};

// Mobile bottom navigation
export interface MobileBottomNavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  onClick: () => void;
}

export interface MobileBottomNavProps {
  items: MobileBottomNavItem[];
  activeItem: string;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({ items, activeItem }) => {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden">
      <div className="flex items-center justify-around py-2">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={item.onClick}
            className={cn(
              'flex flex-col items-center justify-center px-3 py-2 text-xs font-medium rounded-md transition-colors',
              activeItem === item.id
                ? 'text-blue-600 bg-blue-50'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            )}
          >
            <div className="relative">
              {item.icon}
              {item.badge && item.badge > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-4 w-4 flex items-center justify-center">
                  {item.badge > 99 ? '99+' : item.badge}
                </span>
              )}
            </div>
            <span className="mt-1">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
};

// Mobile card component
export interface MobileCardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  onClick?: () => void;
}

export const MobileCard: React.FC<MobileCardProps> = ({
  children,
  className = '',
  padding = 'md',
  onClick,
}) => {
  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };
  
  return (
    <div
      className={cn(
        'bg-white rounded-lg shadow-sm border border-gray-200',
        paddingClasses[padding],
        onClick && 'cursor-pointer hover:shadow-md transition-shadow',
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

// Mobile list component
export interface MobileListItem {
  id: string;
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  rightContent?: React.ReactNode;
  onClick?: () => void;
}

export interface MobileListProps {
  items: MobileListItem[];
  className?: string;
}

export const MobileList: React.FC<MobileListProps> = ({ items, className = '' }) => {
  return (
    <div className={cn('bg-white rounded-lg shadow-sm border border-gray-200', className)}>
      {items.map((item, index) => (
        <div
          key={item.id}
          className={cn(
            'flex items-center px-4 py-3 transition-colors',
            item.onClick && 'cursor-pointer hover:bg-gray-50 active:bg-gray-100',
            index !== items.length - 1 && 'border-b border-gray-100'
          )}
          onClick={item.onClick}
        >
          {item.icon && (
            <div className="flex-shrink-0 mr-3 text-gray-400">
              {item.icon}
            </div>
          )}
          
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {item.title}
            </p>
            {item.subtitle && (
              <p className="text-sm text-gray-500 truncate">
                {item.subtitle}
              </p>
            )}
          </div>
          
          {item.rightContent && (
            <div className="flex-shrink-0 ml-3">
              {item.rightContent}
            </div>
          )}
          
          {item.onClick && (
            <div className="flex-shrink-0 ml-3 text-gray-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

// Mobile modal component
export interface MobileModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'full';
}

export const MobileModal: React.FC<MobileModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
}) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);
  
  if (!isOpen) return null;
  
  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    full: 'max-w-full h-full',
  };
  
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="flex items-center justify-center min-h-full p-4">
        <div
          className={cn(
            'relative bg-white rounded-lg shadow-xl w-full',
            sizeClasses[size],
            size === 'full' ? 'rounded-none' : 'max-h-[90vh]'
          )}
        >
          {/* Header */}
          {title && (
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              <button
                onClick={onClose}
                className="p-2 -mr-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}
          
          {/* Content */}
          <div className={cn('overflow-y-auto', size === 'full' ? 'flex-1' : 'max-h-96')}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};

// Mobile layout wrapper
export interface MobileLayoutProps {
  children: React.ReactNode;
  header?: React.ReactNode;
  bottomNav?: React.ReactNode;
  className?: string;
}

export const MobileLayout: React.FC<MobileLayoutProps> = ({
  children,
  header,
  bottomNav,
  className = '',
}) => {
  const [isMobile, setIsMobile] = useState(false);
  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(MobileUtils.isMobile() || window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    // Optimize for mobile
    if (MobileUtils.isMobile()) {
      MobileUtils.optimizeForMobile();
    }
    
    return () => {
      window.removeEventListener('resize', checkMobile);
    };
  }, []);
  
  return (
    <div className={cn('min-h-screen bg-gray-50', className)}>
      {/* Header */}
      {header && isMobile && header}
      
      {/* Main content */}
      <main
        className={cn(
          'flex-1',
          header && isMobile && 'pt-16',
          bottomNav && isMobile && 'pb-20'
        )}
      >
        {children}
      </main>
      
      {/* Bottom navigation */}
      {bottomNav && isMobile && bottomNav}
    </div>
  );
};

// Responsive breakpoint hook
export const useBreakpoint = () => {
  const [breakpoint, setBreakpoint] = useState<'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl'>('md');
  
  useEffect(() => {
    const updateBreakpoint = () => {
      const width = window.innerWidth;
      
      if (width < 640) {
        setBreakpoint('xs');
      } else if (width < 768) {
        setBreakpoint('sm');
      } else if (width < 1024) {
        setBreakpoint('md');
      } else if (width < 1280) {
        setBreakpoint('lg');
      } else if (width < 1536) {
        setBreakpoint('xl');
      } else {
        setBreakpoint('2xl');
      }
    };
    
    updateBreakpoint();
    window.addEventListener('resize', updateBreakpoint);
    
    return () => {
      window.removeEventListener('resize', updateBreakpoint);
    };
  }, []);
  
  return {
    breakpoint,
    isMobile: breakpoint === 'xs' || breakpoint === 'sm',
    isTablet: breakpoint === 'md',
    isDesktop: breakpoint === 'lg' || breakpoint === 'xl' || breakpoint === '2xl',
  };
};