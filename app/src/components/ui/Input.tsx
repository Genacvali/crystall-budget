'use client';

import { InputHTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  fullWidth?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, fullWidth = false, className, ...props }, ref) => {
    const inputId = props.id || `input-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className={clsx('space-y-1', fullWidth && 'w-full')}>
        {label && (
          <label 
            htmlFor={inputId} 
            className="block text-sm font-medium text-gray-700"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={clsx(
            'block w-full rounded-md border-gray-300 shadow-sm transition-colors',
            'focus:border-primary-500 focus:ring-primary-500',
            'disabled:bg-gray-50 disabled:text-gray-500',
            'text-base', // iOS zoom prevention
            error && 'border-danger-300 focus:border-danger-500 focus:ring-danger-500',
            className
          )}
          {...props}
        />
        {error && (
          <p className="text-sm text-danger-600">{error}</p>
        )}
        {helperText && !error && (
          <p className="text-sm text-gray-500">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;