/**
 * Loading Spinner Component
 */
import React from 'react';
import { cn } from '@/utils/cn';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  className?: string;
  color?: 'primary' | 'secondary' | 'white';
}

const sizeClasses = {
  small: 'h-4 w-4',
  medium: 'h-8 w-8',
  large: 'h-12 w-12',
};

const colorClasses = {
  primary: 'text-indigo-600',
  secondary: 'text-gray-600',
  white: 'text-white',
};

export function LoadingSpinner({ 
  size = 'medium', 
  className,
  color = 'primary' 
}: LoadingSpinnerProps) {
  return (
    <div className={cn('flex items-center justify-center', className)}>
      <svg
        className={cn(
          'animate-spin',
          sizeClasses[size],
          colorClasses[color]
        )}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
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
    </div>
  );
}

export function LoadingSpinnerWithText({ 
  text = 'Loading...', 
  size = 'medium',
  className 
}: LoadingSpinnerProps & { text?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center space-y-2', className)}>
      <LoadingSpinner size={size} />
      <p className="text-sm text-gray-600">{text}</p>
    </div>
  );
}