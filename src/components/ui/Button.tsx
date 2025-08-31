'use client';
import * as React from 'react';

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  fullWidth?: boolean;
  loading?: boolean;
};

export default function Button({ fullWidth, loading, className = '', disabled, children, ...rest }: Props) {
  const isDisabled = disabled || loading;
  return (
    <button
      disabled={isDisabled}
      className={[
        'rounded-2xl px-4 py-3 font-medium shadow-sm transition',
        fullWidth ? 'w-full' : '',
        isDisabled ? 'bg-gray-300 text-gray-600 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700',
        className || ''
      ].join(' ')}
      {...rest}
    >
      {loading ? 'Загрузка…' : children}
    </button>
  );
}