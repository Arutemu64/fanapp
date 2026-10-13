// The build-time public env (see docs/frontend.md §1). Vite inlines every
// `PUBLIC_*` variable (`envPrefix` in vite.config.ts) into the bundle, and the
// config fails the build when one declared in `PUBLIC_ENV_KEYS` is missing, so
// each read below is a string — possibly empty, never undefined.
//
// Adding a variable means registering it in the places docs/frontend.md lists,
// including `PUBLIC_ENV_KEYS` in vite.config.ts and the typing in env.d.ts.
export const PUBLIC_SENTRY_DSN = import.meta.env.PUBLIC_SENTRY_DSN;
export const PUBLIC_SENTRY_ENVIRONMENT = import.meta.env.PUBLIC_SENTRY_ENVIRONMENT;
export const PUBLIC_SENTRY_TRACES_SAMPLE_RATE = import.meta.env.PUBLIC_SENTRY_TRACES_SAMPLE_RATE;
export const PUBLIC_API_URL = import.meta.env.PUBLIC_API_URL;
export const PUBLIC_VAPID_KEY = import.meta.env.PUBLIC_VAPID_KEY;
export const PUBLIC_VK_GROUP_ID = import.meta.env.PUBLIC_VK_GROUP_ID;
export const PUBLIC_TIMEZONE = import.meta.env.PUBLIC_TIMEZONE;
export const PUBLIC_SMARTCAPTCHA_CLIENT_KEY = import.meta.env.PUBLIC_SMARTCAPTCHA_CLIENT_KEY;
