/// <reference types="vite/client" />
/// <reference types="vite-imagetools/client" />
/// <reference types="unplugin-icons/types/vue" />

interface ImportMetaEnv {
	readonly PUBLIC_SENTRY_DSN: string;
	readonly PUBLIC_SENTRY_ENVIRONMENT: string;
	readonly PUBLIC_SENTRY_TRACES_SAMPLE_RATE: string;
	readonly PUBLIC_API_URL: string;
	readonly PUBLIC_VAPID_KEY: string;
	readonly PUBLIC_VK_GROUP_ID: string;
	readonly PUBLIC_TIMEZONE: string;
	readonly PUBLIC_SMARTCAPTCHA_CLIENT_KEY: string;
	readonly PUBLIC_SITE_URL: string;
}

/** Release number from backend/pyproject.toml; empty when the build had none. Set by vite.config.ts `define`. */
declare const __APP_VERSION__: string;
/** Commit SHA of the build; empty when the build had none. Set by vite.config.ts `define`. */
declare const __APP_BUILD__: string;
/**
 * Identity of this exact build — the commit SHA when known, else a build timestamp —
 * so it changes on every deploy. Busts the persisted query cache and revisions the
 * service worker's precache. Set by vite.config.ts `define`.
 */
declare const __BUILD_ID__: string;
