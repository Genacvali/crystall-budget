// next.config.js (CommonJS)
const path = require('path');

const withPWA = require('next-pwa')({
  dest: 'public',
  disable: process.env.NODE_ENV !== 'production',
  register: true,
  scope: '/',
  sw: 'sw.js',
  runtimeCaching: [
    {
      urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
      handler: 'CacheFirst',
      options: {
        cacheName: 'google-fonts',
        expiration: {
          maxEntries: 4,
          maxAgeSeconds: 365 * 24 * 60 * 60, // 1 year
        },
      },
    },
    {
      urlPattern: /\.(?:png|jpg|jpeg|svg|gif)$/i,
      handler: 'StaleWhileRevalidate',
      options: {
        cacheName: 'images',
        expiration: {
          maxEntries: 60,
          maxAgeSeconds: 30 * 24 * 60 * 60, // 1 month
        },
      },
    },
  ],
});

module.exports = withPWA({
  reactStrictMode: true,
  output: 'standalone',
  experimental: {
    serverActions: { 
      allowedOrigins: [process.env.NEXTAUTH_URL?.replace('https://', '').replace('http://', '')].filter(Boolean)
    },
    // важно: этот пакет остаётся внешним для серверных компонентов/роутов
    serverComponentsExternalPackages: ['@node-rs/argon2'],
  },
  images: {
    domains: [],
    formats: ['image/webp', 'image/avif'],
  },
  webpack: (config, { isServer }) => {
    config.resolve.alias['@'] = path.resolve(__dirname, 'src');

    if (isServer) {
      // не пытайся парсить бинарь .node → оставь модуль внешним
      if (!config.externals) config.externals = [];
      config.externals.push('@node-rs/argon2');
    }

    return config;
  },
});