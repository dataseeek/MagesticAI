import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '');

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
      port: 5173,
      host: true, // Listen on all network interfaces for remote access
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: env.VITE_WS_URL || 'ws://localhost:8000',
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
