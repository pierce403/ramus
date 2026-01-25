/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_XMTP_ENV?: string;
  readonly VITE_XMTP_BOT_ADDRESS?: string;
  readonly VITE_XMTP_APP_ID?: string;
  readonly VITE_STATUS_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
