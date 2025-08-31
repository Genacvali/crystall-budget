const path = require('path');

module.exports = {
  output: 'standalone',
  experimental: {
    serverComponentsExternalPackages: ['@node-rs/argon2']
  },
  webpack: (config, { isServer }) => {
    config.resolve.alias['@'] = path.resolve(__dirname, 'src');
    
    if (isServer) {
      // Исключаем native модули из webpack bundling
      if (!config.externals) config.externals = [];
      config.externals.push('@node-rs/argon2');
    }
    
    return config;
  },
};