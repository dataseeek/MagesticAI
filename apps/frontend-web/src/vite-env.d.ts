/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly DEV: boolean;
  readonly PROD: boolean;
  readonly MODE: string;
  // Remote access configuration
  readonly VITE_API_BASE_URL?: string;  // e.g., "http://192.168.1.100:8000/api"
  readonly VITE_WS_BASE_URL?: string;   // e.g., "ws://192.168.1.100:8000"
  readonly VITE_API_URL?: string;       // Backend URL for Vite proxy (dev only)
  readonly VITE_WS_URL?: string;        // WebSocket URL for Vite proxy (dev only)
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
