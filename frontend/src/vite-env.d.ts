/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_EPHEMERAL_DEMO?: string;
  readonly VITE_OTEL_EXPORTER_OTLP_ENDPOINT?: string;
  readonly VITE_SAVORLOOP_ENVIRONMENT?: string;
  readonly VITE_SAVORLOOP_VERSION?: string;
}
