import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sentrySvelteKit } from '@sentry/sveltekit/vite';
import adapter from '@sveltejs/adapter-static';
import { enhancedImages } from '@sveltejs/enhanced-img';
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteDevtools } from '@sveltejs/vite-devtools-svelte';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { mdsvex } from 'mdsvex';
import { fileURLToPath } from 'node:url';
import Icons from 'unplugin-icons/vite';
import { type ConfigEnv, loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

const rootDir = fileURLToPath(new URL('..', import.meta.url));

function svelteDevtoolsEnabled({ command, isPreview }: ConfigEnv, setting: string | undefined) {
	return command === 'serve' && !isPreview && !process.env.VITEST && setting === '1';
}

export default defineConfig((config) => {
	const { mode } = config;
	const env = loadEnv(mode, rootDir, '');
	const enableSvelteDevtools = svelteDevtoolsEnabled(config, env.SVELTE_DEVTOOLS);

	const sentryUpload = {
		org: env.SENTRY_ORG,
		project: env.SENTRY_PROJECT,
		sentryUrl: env.SENTRY_URL,
		authToken: env.SENTRY_AUTH_TOKEN
	};
	const canUploadSourceMaps = Object.values(sentryUpload).every(Boolean);

	return {
		envDir: rootDir,
		define: {
			__APP_VERSION__: JSON.stringify(env.APP_VERSION ?? ''),
			__APP_BUILD__: JSON.stringify(env.APP_BUILD ?? '')
		},
		plugins: [
			sentrySvelteKit({
				...sentryUpload,
				autoUploadSourceMaps: canUploadSourceMaps,
				release: {
					name: env.APP_BUILD || undefined
				}
			}),
			tailwindcss(),
			paraglideVitePlugin({
				project: './project.inlang',
				outdir: './src/lib/paraglide',
				strategy: ['baseLocale'],
				emitTsDeclarations: true
			}),
			enhancedImages(),
			mdsvex({ extensions: ['.md'] }),
			enableSvelteDevtools && svelteDevtools(),
			sveltekit({
				preprocess: vitePreprocess(),
				env: { dir: '..' },
				adapter: adapter({ fallback: '200.html' }),
				serviceWorker: { register: false }
			}),
			Icons({
				compiler: 'svelte'
			})
		],
		optimizeDeps: {
			include: [
				'workbox-core',
				'workbox-expiration',
				'workbox-precaching',
				'workbox-routing',
				'workbox-strategies'
			]
		},
		test: {
			include: ['src/**/*.test.ts'],
			environment: 'node',
			restoreMocks: true,
			unstubGlobals: true,
			unstubEnvs: true,
			fsModuleCache: true
		},
		resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
		server: {
			host: enableSvelteDevtools ? '127.0.0.1' : true,
			allowedHosts: enableSvelteDevtools ? undefined : true,
			port: Number(env.FRONTEND_PORT ?? 3000),
			strictPort: true,
			proxy: {
				'/api': {
					target: env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
					changeOrigin: true,
					rewrite: (path) => path.replace(/^\/api/, '')
				}
			}
		}
	};
});
