import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	PUBLIC_SENTRY_DSN: { public: true, static: true },
	PUBLIC_SENTRY_ENVIRONMENT: { public: true, static: true },
	PUBLIC_SENTRY_TRACES_SAMPLE_RATE: { public: true, static: true },
	PUBLIC_API_URL: { public: true, static: true },
	PUBLIC_APP_VERSION: { public: true, static: true },
	PUBLIC_VAPID_KEY: { public: true, static: true },
	PUBLIC_VK_GROUP_ID: { public: true, static: true },
	PUBLIC_TIMEZONE: { public: true, static: true },
	PUBLIC_SMARTCAPTCHA_CLIENT_KEY: { public: true, static: true },
	// Only read by the %sveltekit.env.PUBLIC_SITE_URL% placeholders in app.html.
	PUBLIC_SITE_URL: { public: true, static: true }
});
