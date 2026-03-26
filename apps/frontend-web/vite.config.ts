import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';
import os from 'os';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '');

  // Resolve SSL certs from the shared data directory
  const sslDir = path.join(os.homedir(), '.magestic-ai', 'ssl');
  const certFile = path.join(sslDir, 'cert.pem');
  const keyFile = path.join(sslDir, 'key.pem');
  const hasSSL = fs.existsSync(certFile) && fs.existsSync(keyFile);

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@lib': path.resolve(__dirname, './src/lib'),
        '@stores': path.resolve(__dirname, './src/stores'),
        '@pages': path.resolve(__dirname, './src/pages'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
      },
    },
    server: {
      port: 3100,
      host: true, // Listen on all network interfaces for remote access
      allowedHosts: ['dev.example.com'],
      ...(hasSSL && {
        https: {
          cert: fs.readFileSync(certFile),
          key: fs.readFileSync(keyFile),
        },
      }),
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:3101',
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: env.VITE_WS_URL || 'ws://localhost:3101',
          ws: true,
          secure: false,
        },
      },
    },
    build: {
      outDir: '../web-server/static',
      emptyOutDir: true,
    },
  };
});
