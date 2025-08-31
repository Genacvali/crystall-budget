'use client';
import * as React from 'react';

type Props = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  fullWidth?: boolean;
};

export default function Input({ label, fullWidth, className = '', ...rest }: Props) {
  return (
    <label className={fullWidth ? 'block w-full' : 'inline-block'}>
      {label && <span className="block text-sm mb-1 text-gray-700">{label}</span>}
      <input
        className={[
          'rounded-xl border border-gray-300 bg-white px-4 py-3 outline-none',
          'focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
          fullWidth ? 'w-full' : '',
          className || ''
        ].join(' ')}
        {...rest}
      />
    </label>
  );
}